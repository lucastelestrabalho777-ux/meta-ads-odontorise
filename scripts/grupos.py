#!/usr/bin/env python3
"""
meta-ads-odontorise: leitura dos grupos de WhatsApp dos clientes para a CS. SOMENTE LEITURA.

Cruza os grupos do WhatsApp de Suporte (Uazapi) com os clientes ativos do ClickUp e devolve o que pede atenção.

Uso:
  grupos.py checar                 a instância está conectada? quantos grupos de cliente? quem conta como equipe?
  grupos.py varrer [--audios N]    os 4 blocos dos clientes ativos (base de /grupos-clientes):
                                     aguardando_resposta  a última mensagem é do cliente e passou do prazo em horário útil
                                     em_alerta            clientes com alerta aberto no ClickUp e o que o grupo mostra
                                     possivel_atrito      trechos do cliente com sinal de reclamação (o Claude confirma)
                                     sem_engajamento      nenhuma mensagem do cliente na janela
                                   --audios N transcreve até N áudios de cliente (padrão 20; 0 desliga)
  grupos.py cliente --cliente X    a conversa do grupo de um cliente (nome, parte do nome ou #código) na janela

Limites: a Uazapi guarda até 7 dias de mensagem, então a janela é de no máximo 7 dias. O grupo é ligado ao cliente
pelo código no nome do grupo (#123). Equipe = o próprio número de Suporte, quem está em muitos grupos de cliente e
quem tem o primeiro nome igual ao do gestor, da CS ou da liderança do cliente no ClickUp.

Nada é gravado em disco: os áudios vão para uma pasta temporária, apagada no fim. Telefone, e-mail, CPF, CNPJ, link
e valor saem mascarados dos trechos. Não envia mensagem, não marca como lida e não altera grupo.
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import cs  # noqa: E402  (carteira da CS no ClickUp, só leitura)
from lib import clickup, uazapi  # noqa: E402

PRAZO_RESPOSTA_MIN = 40          # minutos úteis sem resposta para o cliente entrar em aguardando_resposta
UTIL_INICIO, UTIL_FIM = 8, 18    # horário útil, segunda a sexta
EQUIPE_MIN_GRUPOS = 10           # quem está em tantos grupos de cliente é da equipe
JANELA_DIAS = 7                  # o que a Uazapi guarda
RE_CODIGO = re.compile(r"^\s*#\s*(\d+(?:\.\d+)?)")
IGNORAR = ("ReactionMessage", "ProtocolMessage", "PollUpdateMessage")
MIDIA = {"AudioMessage": "[áudio]", "ImageMessage": "[imagem]", "VideoMessage": "[vídeo]",
         "DocumentMessage": "[documento]", "StickerMessage": "[figurinha]", "ContactMessage": "[contato]",
         "LocationMessage": "[localização]"}

# Filtro largo de sinal de atrito. Só separa candidatos: quem decide se é reclamação é o Claude, lendo o trecho.
RE_ATRITO = re.compile(
    r"insatisf|decepcion|chatead|frustrad|desanim|preocupad|absurd|p[eé]ssim|horr[ií]vel|descaso|reclam"
    r"|cancel|rescis|rescind|encerrar|multa|quebra de contrato|sair da ag|trocar de ag|outra ag[eê]ncia"
    r"|pausar|parar (a|as|o|os) (campanha|an[uú]ncio)|n[aã]o vale|n[aã]o compensa|jogando dinheiro|preju[ií]zo"
    r"|sem resultado|resultado (ruim|fraco|baixo)|caiu muito|piorou|s[oó] piora"
    r"|n[aã]o (est[aá]|t[aá]|tem|tinha|teve) (chegando|vindo|entrando|dando|funcionando|rodando|aparecendo)"
    r"|nenhum (lead|leed|paciente|contato|agendamento|cliente|retorno)|zero (lead|paciente|contato)"
    r"|lead[s]? (ruim|ruins|fraco|fracos|desqualificad|curios)|s[oó] curioso|ningu[eé]m (respond|agend|fech|apare)"
    r"|sem retorno|sem resposta|at[eé] agora nada|ainda nada|ningu[eé]m me respond|cad[eê] |estou esperando"
    r"|j[aá] (faz|fazem|tem) \w+ (dia|semana)|desde (ontem|segunda|ter[cç]a|quarta|quinta|sexta|semana)"
    r"|demora(ndo)?\b|atras(o|ad)|divergen|errad|erro de|cobran[cç]a indevida|estorno|reembolso",
    re.I)


# Mensagem que só encerra a conversa (ok, obrigado, figurinha): não fica esperando resposta.
RE_ENCERRA = re.compile(r"^\W*(ok(ay)?|t[aá]( bom| [oó]timo| certo)?|beleza|blz|perfeito|[oó]timo|show|top|certo|combinado|fechado"
                        r"|entendi|pode ser|isso( mesmo)?|sim|am[eé]m|(muito )?obrigad[oa]|obg|valeu|vlw|boa|maravilha|joia"
                        r"|de nada|igualmente|bom dia|boa tarde|boa noite|[kK]{2,}|(ha){2,}|(rs)+)(\W+(ok|obrigad[oa]|ent[aã]o|gente"
                        r"|pessoal|meninos|meninas|querid[oa]s?|viu|t[aá]))*\W*$", re.I)


def _so_encerra(m):
    if m.get("_transcricao"):
        return False
    if m.get("messageType") == "StickerMessage":
        return True
    return m.get("messageType") not in MIDIA and bool(RE_ENCERRA.match((m.get("text") or "").strip()))


def _falha(msg, acao=None):
    out = {"ok": False, "erro": uazapi.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)


def _quando(ms):
    return datetime.fromtimestamp(ms / 1000)


def _dm(ms):
    return _quando(ms).strftime("%d/%m %H:%M")


def minutos_uteis(inicio, fim):
    """Minutos entre dois instantes contando só segunda a sexta, das UTIL_INICIO às UTIL_FIM."""
    if fim <= inicio:
        return 0
    total, dia = 0, inicio.date()
    while dia <= fim.date():
        if dia.weekday() < 5:
            a = datetime.combine(dia, datetime.min.time()) + timedelta(hours=UTIL_INICIO)
            b = datetime.combine(dia, datetime.min.time()) + timedelta(hours=UTIL_FIM)
            ini, f = max(a, inicio), min(b, fim)
            if f > ini:
                total += int((f - ini).total_seconds() // 60)
        dia += timedelta(days=1)
    return total


def _espera(minutos):
    h, m = divmod(minutos, 60)
    return f"{h} h {m:02d} min úteis" if h else f"{m} min úteis"


def _lid(valor):
    return str(valor or "").split(":")[0].split("@")[0]


def _primeiro(nome):
    return clickup.normalizar(str(nome or "").split()[0]) if str(nome or "").split() else ""


def _texto(m, n=220):
    t = m.get("_transcricao")
    if t:
        return "[áudio transcrito] " + cs._limpo(t, n + 180)
    tipo = m.get("messageType")
    corpo = cs._limpo(m.get("text") or "", n)
    if tipo in MIDIA:
        return (MIDIA[tipo] + " " + corpo).strip() if tipo != "ImageMessage" or len(corpo) < 120 else MIDIA[tipo]
    return corpo


class Leitura:
    """Grupos de cliente da instância, com quem é equipe."""

    def __init__(self):
        st = uazapi.status()
        if not st["conectada"]:
            raise uazapi.ErroUazapi("o WhatsApp de Suporte está desconectado na Uazapi",
                                    "pedir a quem administra a Uazapi para reconectar o número")
        self.status = st
        todos = uazapi.grupos()
        self.total_grupos = len(todos)
        self.por_codigo = collections.defaultdict(list)
        for g in todos:
            m = RE_CODIGO.match(g.get("Name") or "")
            if m:
                self.por_codigo[m.group(1)].append(g)
        conta = collections.Counter()
        for gs in self.por_codigo.values():
            for g in gs:
                for p in g.get("Participants") or []:
                    conta[_lid(p.get("LID") or p.get("JID"))] += 1
        self.equipe = {k for k, v in conta.items() if k and v >= EQUIPE_MIN_GRUPOS}
        self.nomes_equipe = set()

    def grupos_do(self, codigo):
        cod = str(codigo or "").lstrip("#").strip()
        return self.por_codigo.get(cod) or self.por_codigo.get(cod.split(".")[0]) or []

    def conversa(self, perfil):
        """Mensagens do(s) grupo(s) do cliente, cada uma marcada com _equipe."""
        internos = {_primeiro(n) for campo in ("gestor", "cs", "lideranca") for n in (perfil.get(campo) or [])}
        internos.discard("")
        msgs = []
        for g in self.grupos_do(perfil.get("codigo")):
            msgs += uazapi.mensagens(g["JID"])
        msgs = [m for m in msgs if m.get("messageType") not in IGNORAR]
        msgs.sort(key=lambda m: m.get("messageTimestamp") or 0)
        for m in msgs:
            m["_equipe"] = bool(m.get("fromMe") or _lid(m.get("sender_lid") or m.get("sender")) in self.equipe
                                or _primeiro(m.get("senderName")) in internos)
            if m["_equipe"] and m.get("senderName"):
                self.nomes_equipe.add(str(m["senderName"]).split()[0])
        return msgs


def _python_whisper():
    candidatos = [os.environ.get("ODR_WHISPER_PY"), "~/.cache/whisper-venv/bin/python",
                  "~/whisper-venv/Scripts/python.exe", "~/whisper-venv/bin/python"]
    for c in candidatos:
        if c and os.path.isfile(os.path.expanduser(c)):
            return os.path.expanduser(c)
    return None


def transcrever(msgs, limite):
    """Transcreve até `limite` áudios (os primeiros da lista) e grava em m['_transcricao']. Devolve o resumo."""
    alvo = msgs[:limite]
    resumo = {"audios_de_cliente": len(msgs), "transcritos": 0}
    if not alvo:
        return resumo
    py = _python_whisper()
    if not py:
        resumo["aviso"] = ("transcrição desligada: o Whisper não está instalado nesta máquina "
                           "(ver o cabeçalho de scripts/transcrever.py). Os áudios aparecem como [áudio].")
        return resumo
    pasta = tempfile.mkdtemp(prefix="odr-audios-")
    try:
        arquivos = {}
        for i, m in enumerate(alvo):
            try:
                arquivos[uazapi.baixar_audio(m["id"], os.path.join(pasta, f"a{i:03d}.mp3"))] = m
            except uazapi.ErroUazapi:
                continue
        if arquivos:
            print(f"transcrevendo {len(arquivos)} áudio(s) de cliente...", file=sys.stderr)
            r = subprocess.run([py, os.path.join(AQUI, "transcrever.py"), *arquivos, "--json"],
                               capture_output=True, text=True, timeout=1800)
            try:
                for item in json.loads(r.stdout):
                    m = arquivos.get(item.get("caminho"))
                    if m is not None and (item.get("texto") or "").strip():
                        m["_transcricao"] = item["texto"].strip()
                        resumo["transcritos"] += 1
            except ValueError:
                resumo["aviso"] = "a transcrição falhou; os áudios aparecem como [áudio]."
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    if len(msgs) > len(alvo):
        resumo["fora_do_limite"] = len(msgs) - len(alvo)
    return resumo


def _analisar(perfil, msgs, agora):
    """Números do grupo de um cliente na janela."""
    do_cliente = [m for m in msgs if not m["_equipe"]]
    da_equipe = [m for m in msgs if m["_equipe"]]
    a = {"mensagens_cliente": len(do_cliente), "mensagens_equipe": len(da_equipe),
         "ultima_do_cliente": _dm(do_cliente[-1]["messageTimestamp"]) if do_cliente else None,
         "ultima_da_equipe": _dm(da_equipe[-1]["messageTimestamp"]) if da_equipe else None}
    pendentes = []
    for m in reversed(msgs):
        if m["_equipe"]:
            break
        pendentes.append(m)
    pendentes.reverse()
    if all(_so_encerra(m) for m in pendentes):
        pendentes = []
    a["_pendentes"] = pendentes
    a["_espera_min"] = minutos_uteis(_quando(pendentes[0]["messageTimestamp"]), agora) if pendentes else 0
    a["_do_cliente"] = do_cliente
    return a


def _trechos(msgs, n, tamanho=220):
    return [f"{_dm(m['messageTimestamp'])} {str(m.get('senderName') or 'cliente').split()[0]}: {_texto(m, tamanho)}"
            for m in msgs[-n:] if _texto(m, tamanho)]


def cmd_checar(a):
    lt = Leitura()
    ativos = cs._montar_carteira()
    sem = [c["codigo"] for c in ativos if not lt.grupos_do(c.get("codigo"))]
    print(json.dumps({"ok": True, "instancia": lt.status, "grupos_na_instancia": lt.total_grupos,
                      "grupos_com_codigo_de_cliente": sum(len(v) for v in lt.por_codigo.values()),
                      "clientes_ativos": len(ativos), "ativos_sem_grupo_encontrado": sem,
                      "pessoas_que_contam_como_equipe": len(lt.equipe),
                      "regra_equipe": f"número de Suporte, quem está em {EQUIPE_MIN_GRUPOS} ou mais grupos de cliente "
                                      "e o gestor, a CS e a liderança do cliente no ClickUp (pelo primeiro nome)"},
                     ensure_ascii=False, indent=2))


def cmd_varrer(a):
    agora = datetime.now()
    lt = Leitura()
    ativos = cs._montar_carteira()
    print(f"{len(ativos)} clientes ativos; lendo os grupos (cerca de 2 minutos)...", file=sys.stderr)
    lidos, sem_grupo = [], []
    for c in ativos:
        if not lt.grupos_do(c.get("codigo")):
            sem_grupo.append(f"{c['nome']} ({c['codigo']})")
            continue
        msgs = lt.conversa(c)
        lidos.append((c, msgs, _analisar(c, msgs, agora)))

    # Áudios de cliente, na ordem de prioridade: os que estão esperando resposta, os de cliente em alerta, o resto.
    resumo_audio = {"audios_de_cliente": 0, "transcritos": 0}
    if a.audios > 0:
        fila, visto = [], set()

        def _por(ms):
            for m in sorted(ms, key=lambda m: -m["messageTimestamp"]):
                if m.get("messageType") == "AudioMessage" and m["id"] not in visto:
                    visto.add(m["id"])
                    fila.append(m)
        for c, msgs, an in lidos:
            if an["_espera_min"] >= PRAZO_RESPOSTA_MIN:
                _por(an["_pendentes"])
        for c, msgs, an in lidos:
            if c.get("alertas_abertos"):
                _por(an["_do_cliente"])
        resto = [m for c, msgs, an in lidos for m in an["_do_cliente"]]
        _por(resto)
        resumo_audio = transcrever(fila, a.audios)

    aguardando, alerta, atrito, sem_eng = [], [], [], []
    for c, msgs, an in lidos:
        base = {"cliente": c["nome"], "codigo": c["codigo"], "gestor": cs._primeiros(c.get("gestor"))}
        if an["_espera_min"] >= PRAZO_RESPOSTA_MIN:
            aguardando.append({**base, "_min": an["_espera_min"], "esperando": _espera(an["_espera_min"]),
                               "desde": _dm(an["_pendentes"][0]["messageTimestamp"]),
                               "mensagens_sem_resposta": len(an["_pendentes"]),
                               "trechos": _trechos(an["_pendentes"], 3, 160)})
        abertos = [x for x in (c.get("alertas_abertos") or []) if x.get("status") != "churn"]
        if abertos:
            alerta.append({**base, "lideranca": cs._primeiros(c.get("lideranca")),
                           "alertas": [{k: x.get(k) for k in ("motivo", "nivel", "status", "com_quem", "aberto_ha_dias")}
                                       for x in abertos],
                           "satisfacao": c.get("satisfacao"),
                           "grupo_7_dias": {k: an[k] for k in ("mensagens_cliente", "mensagens_equipe",
                                                               "ultima_do_cliente", "ultima_da_equipe")},
                           "esperando_resposta": _espera(an["_espera_min"]) if an["_espera_min"] >= PRAZO_RESPOSTA_MIN else None,
                           "ultimas_do_cliente": _trechos(an["_do_cliente"], 4, 160)})
        sinais = [m for m in an["_do_cliente"] if RE_ATRITO.search((m.get("_transcricao") or "") + " " + (m.get("text") or ""))]
        if sinais:
            atrito.append({**base, "satisfacao": c.get("satisfacao"),
                           "tem_alerta_aberto": True if abertos else None, "sinais": len(sinais),
                           "trechos": _trechos(sinais, 4, 200)})
        if not an["mensagens_cliente"]:
            sem_eng.append({**base, "mensagens_equipe": an["mensagens_equipe"], "ultima_da_equipe": an["ultima_da_equipe"],
                            "classe": c.get("classe"), "satisfacao": c.get("satisfacao"),
                            "reuniao_mensal": c.get("reuniao_mensal")})
    aguardando.sort(key=lambda x: -x.pop("_min"))
    alerta.sort(key=lambda x: -(max(al.get("aberto_ha_dias") or 0 for al in x["alertas"])))
    atrito.sort(key=lambda x: -x["sinais"])
    sem_eng.sort(key=lambda x: x["mensagens_equipe"])

    blocos = [("aguardando_resposta", aguardando), ("em_alerta", alerta), ("possivel_atrito", atrito),
              ("sem_engajamento", sem_eng)]
    cab = {"ok": True, "lido_em": agora.strftime("%d/%m/%Y %H:%M"), "fonte": "WhatsApp de Suporte (Uazapi) + ClickUp, só leitura",
           "janela": f"últimos {JANELA_DIAS} dias (é o que a Uazapi guarda)",
           "regras": {"aguardando_resposta": f"última mensagem é do cliente há {PRAZO_RESPOSTA_MIN} minutos úteis ou mais "
                                             f"(segunda a sexta, {UTIL_INICIO}h às {UTIL_FIM}h)",
                      "sem_engajamento": f"nenhuma mensagem do cliente em {JANELA_DIAS} dias",
                      "possivel_atrito": "filtro por palavras: são candidatos, confirmar lendo o trecho"},
           "resumo": {"clientes_ativos": len(ativos), "grupos_lidos": len(lidos),
                      **{nome: len(itens) for nome, itens in blocos}},
           "audios": resumo_audio, "equipe_reconhecida": sorted(lt.nomes_equipe),
           "ativos_sem_grupo_encontrado": sem_grupo,
           "aviso": "Leitura interna da CS. Trecho de cliente, alerta e satisfação nunca vão para o grupo nem para o ClickUp."}
    print(", ".join(f"{nome} {len(itens)}" for nome, itens in blocos), file=sys.stderr)
    saida = [json.dumps(cab, ensure_ascii=False)[:-1] + ","]
    for i, (nome, itens) in enumerate(blocos):
        itens = [{k: v for k, v in x.items() if v not in (None, [], "")} for x in itens]
        saida.append(f'"{nome}": [')
        saida += ["  " + json.dumps(x, ensure_ascii=False) + ("," if k < len(itens) - 1 else "") for k, x in enumerate(itens)]
        saida.append("]" + ("," if i < len(blocos) - 1 else ""))
    saida.append("}")
    texto = "\n".join(saida)
    if len(texto) > 40000:
        print(f"AVISO: saída com {len(texto)} caracteres; se o Claude cortar a leitura, rodar com --audios 0.", file=sys.stderr)
    print(texto)


def cmd_cliente(a):
    agora = datetime.now()
    perfil = cs._perfil(cs._resolver(a.cliente, cs._ler(clickup.LISTA_PERFIL_ID, fechadas=True)))
    lt = Leitura()
    grupos = lt.grupos_do(perfil.get("codigo"))
    if not grupos:
        _falha(f"nenhum grupo com o código {perfil.get('codigo')} no WhatsApp de Suporte")
    msgs = lt.conversa(perfil)
    an = _analisar(perfil, msgs, agora)
    audio = transcrever(sorted([m for m in an["_do_cliente"] if m.get("messageType") == "AudioMessage"],
                               key=lambda m: -m["messageTimestamp"]), a.audios) if a.audios > 0 else None
    linhas = [f"{_dm(m['messageTimestamp'])} {'EQUIPE' if m['_equipe'] else 'CLIENTE'} "
              f"{str(m.get('senderName') or '').split()[0] if m.get('senderName') else ''}: {_texto(m, 400)}"
              for m in msgs[-a.ultimas:] if _texto(m, 400)]
    print(json.dumps({"ok": True, "cliente": perfil["nome"], "codigo": perfil["codigo"],
                      "gestor": cs._primeiros(perfil.get("gestor")), "grupos": [g.get("Name") for g in grupos],
                      "janela": f"últimos {JANELA_DIAS} dias", "mensagens_na_janela": len(msgs),
                      "mensagens_cliente": an["mensagens_cliente"], "mensagens_equipe": an["mensagens_equipe"],
                      "esperando_resposta": _espera(an["_espera_min"]) if an["_espera_min"] >= PRAZO_RESPOSTA_MIN else None,
                      "audios": audio, "conversa": linhas,
                      "aviso": "Leitura interna da CS: não copiar para o ClickUp nem para outro grupo."},
                     ensure_ascii=False, indent=1))


def main():
    p = argparse.ArgumentParser(description="Grupos de WhatsApp dos clientes para a CS (só leitura).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("checar"); s.set_defaults(fn=cmd_checar)
    s = sub.add_parser("varrer"); s.add_argument("--audios", type=int, default=20); s.set_defaults(fn=cmd_varrer)
    s = sub.add_parser("cliente"); s.add_argument("--cliente", required=True)
    s.add_argument("--audios", type=int, default=5); s.add_argument("--ultimas", type=int, default=60)
    s.set_defaults(fn=cmd_cliente)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except uazapi.ErroUazapi as e:
        _falha(str(e), e.acao)
    except Exception as e:  # noqa: BLE001
        _falha(f"erro interno: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
