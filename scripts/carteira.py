#!/usr/bin/env python3
"""
meta-ads-odontorise: carteira por gestor.

Cruza a ficha do cliente no ClickUp (Perfil de Clientes: gestor, produto, fase, satisfação,
data de entrada, ticket) com a saúde da conta Meta (saude.py: saldo, anúncios, gasto sem
mensagem, criativos, recência) e classifica cada cliente: recente, bom, melhor, com problema.
Base da skill /carteira-gestor. Só leitura na Meta e no ClickUp.

Quem entra: os perfis do ClickUp no escopo (--gestor NOME para o head, ou os clientes do dono
do token). A conta Meta de cada um vem do cadastro local (~/OdontoRise/meta-ads/contas-odontorise.json,
o mesmo de clientes.py); cliente sem cadastro aparece na tabela como "sem cadastro" e a conta
dele não é lida. A credencial é a de sempre (lib); conta que ela não enxerga sai como "sem leitura".

Ticket e datas vêm do ClickUp na hora e não são gravados: a análise salva em
~/OdontoRise/meta-ads/carteira/ sai sem ticket e sem verba.

Subcomandos:
  analisar [--gestor NOME ...] [--todos] [--paralelo 4] [--inativos] [--so-ficha] [--gasto-minimo N]
  tabela [ARQUIVO]      reimprime as tabelas de uma análise salva (padrão: a última)

JSON no stdout; tabelas em markdown no stderr. Códigos de saída: 0 análise feita · 1 erro.
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import lib  # noqa: E402
from lib import clickup, watchlist  # noqa: E402
import saude as _saude  # noqa: E402

# ---------------------------------------------------------------------------
# Limiares e caminhos
# ---------------------------------------------------------------------------

RECENTE_DIAS = 30                                     # entrou há 30 dias ou menos = recente
BOM_CUSTO_MAX = _saude.CUSTO_MSG_TETO_CENTAVOS / 100  # abaixo do teto de R$35 com mensagem = bom
MELHOR_MSGS_MIN = 20                                  # melhor: 20 mensagens ou mais em 7 dias...
MELHOR_CUSTO_MAX = 30.0                               # ...a menos de R$30 cada, e ficha não insatisfeita
OUTRO_OBJETIVO_ATENCAO = 50.0                         # tráfego/alcance/formulário gastando R$50+ em 7d vira nota
TICKET_SUSPEITO = 8000.0                              # ticket mensal acima disso costuma ser o valor do contrato na ficha
STATUS_EXCLUIDOS = {"inativo", "churn", "encerrado", "cancelado", "finalizado"}
FASES_ENTRANDO = {"onb1", "onb2", "setup", "onboarding"}

HISTORICO_DIR = os.path.expanduser(os.environ.get("ODR_CARTEIRA_HISTORICO", "~/OdontoRise/meta-ads/carteira"))

CAMPOS_FICHA = {
    "Código do Cliente": "codigo", "Produto": "produto", "Fase Global": "fase", "Status do Projeto": "satisfacao",
    "Health Score": "health_score", "Cidade": "cidade", "Estado": "estado",
    "Especialidade Odontologica": "especialidade",
}
CAMPOS_DATA = {
    "Data de Fechamento": "data_fechamento", "Data do Primeiro pagamento (vigência)": "data_1o_pagamento",
    "Data de Entrada": "data_entrada", "Data da 1ª Campanha": "data_1a_campanha",
    "Data de Finalização do Onboarding": "data_fim_onboarding", "Data de Pedido de Saída": "data_pedido_saida",
    "Data de saída": "data_saida",
}
CAMPOS_VALOR = {"Valor Recorrente Mensal (Ticket)": "ticket", "Investimento Mensal em Mídia (Verba)": "verba_mensal"}
CAMPOS_NAO_SALVOS = ("ticket", "verba_mensal")        # ficam fora do arquivo salvo em disco
ORDEM_ENTRADA = ("data_fechamento", "data_1o_pagamento", "data_entrada", "criado")

SATISFACAO_CURTA = {
    "muito insatisfeito critico": "Crítico", "insatisfeito alerta": "Alerta", "neutro": "Neutro",
    "satisfeito": "Satisfeito", "muito satisfeito promotor": "Promotor", "embaixador": "Embaixador",
}
PESO_PECA = {"critico": 2, "atencao": 1}


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def falha(msg, acao=None, code=1):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(code)


def brl(v, casas=2):
    if not isinstance(v, (int, float)):
        return str(v)
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$" + s


def _data_ms(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return None


def _num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def nome_curto(nome):
    """'DRA. PATRÍCIA ROCHA' -> 'Patrícia Rocha'; nome de clínica fica como está, só com caixa normal."""
    t = re.sub(r"\s*\(.*?\)\s*", " ", str(nome or "")).strip()
    t = re.sub(r"^(dra?\.?\s+)+", "", t, flags=re.I).strip().rstrip(".,;:")
    minusculas = {"de", "da", "do", "das", "dos", "e"}
    palavras = []
    for i, p in enumerate(t.split()):
        if p.isupper() and len(p) <= 2:      # sigla (ZM, MK) fica como está; ERY vira Ery
            palavras.append(p)
            continue
        pl = p.lower()
        palavras.append(pl if (pl in minusculas and i > 0) else pl.capitalize())
    return " ".join(palavras)


def primeiro_nome(gestor):
    return (gestor or "sem gestor").split()[0]


def erro_curto(erro, code=None):
    """Erro da Meta em poucas palavras para a tabela; o texto inteiro fica no JSON."""
    if code == 200 or "(#200)" in str(erro or ""):
        return "#200: conta fora da BM ou sem ads_read"
    t = re.sub(r"\s+", " ", str(erro or "sem detalhe")).strip()
    t = re.sub(r",?\s*refer to https?://\S+.*$", "", t)
    return t if len(t) <= 80 else t[:77] + "..."


def _dias(v):
    if not isinstance(v, (int, float)):
        return f"{v}d"
    return f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "d"


def satisfacao_curta(v):
    if not v:
        return "sem"
    k = re.sub(r"\s+", " ", clickup.normalizar(v))
    if k in SATISFACAO_CURTA:
        return SATISFACAO_CURTA[k]
    m = re.search(r"\(([^)]+)\)", str(v))
    return m.group(1) if m else str(v)


def _d(iso):
    return date.fromisoformat(iso) if iso else None


def fmt_data(iso, hoje):
    d = _d(iso)
    if not d:
        return "sem data"
    return d.strftime("%d/%m") if d.year == hoje.year else d.strftime("%d/%m/%y")


# ---------------------------------------------------------------------------
# ClickUp: fichas do escopo
# ---------------------------------------------------------------------------

def ficha(t):
    """Só o que serve para a tabela. Dados pessoais, de contrato e endereço ficam no ClickUp."""
    r = {"clickup_task_id": t.get("id"), "nome": t.get("name"), "status": (t.get("status") or {}).get("status"),
         "criado": _data_ms(t.get("date_created"))}
    for c in t.get("custom_fields", []):
        n = c.get("name")
        if n in CAMPOS_FICHA:
            r[CAMPOS_FICHA[n]] = clickup._valor_campo(c)
        elif n in CAMPOS_DATA:
            r[CAMPOS_DATA[n]] = _data_ms(clickup._valor_campo(c))
        elif n in CAMPOS_VALOR:
            r[CAMPOS_VALOR[n]] = _num(clickup._valor_campo(c))
    g = clickup.valor(t, "Gestor") or []
    r["gestor"] = [u.get("nome") for u in g] if isinstance(g, list) else [str(g)]
    if isinstance(r.get("produto"), list):
        r["produto"] = ", ".join(str(p) for p in r["produto"])
    return r


def selecionar(perfis, gestores=None, todos=False):
    """Escopo: --todos (carteira inteira), --gestor NOME (head) ou os clientes do dono do token."""
    if todos:
        return list(perfis), "carteira inteira"
    if gestores:
        alvos = [clickup.normalizar(g) for g in gestores]
        sel = []
        for t in perfis:
            nomes = [clickup.normalizar(u.get("nome")) for u in (clickup.valor(t, "Gestor") or [])]
            if any(a in n for a in alvos for n in nomes):
                sel.append(t)
        return sel, "gestor " + ", ".join(gestores)
    uid, nome = clickup.quem_sou()
    if not uid:
        falha("não consegui identificar o dono do token do ClickUp", "conferir o token (passo 8)")
    return [t for t in perfis if uid in clickup.gestor_ids(t)], f"meus clientes ({nome})"


def ler_fichas(gestores, todos):
    ok, perfis = clickup.perfis(include_closed=True)
    if not ok:
        falha(perfis.get("erro"), "conferir a internet e o token do ClickUp (passo 8)")
    sel, escopo = selecionar(perfis, gestores, todos)
    return [ficha(t) for t in sel], escopo


# ---------------------------------------------------------------------------
# Saúde das contas (saude.analisar_conta em threads, mesma credencial de sempre)
# ---------------------------------------------------------------------------

def ler_contas(fichas, paralelo, gasto_minimo):
    """{act_id: resultado do saude.py} para as fichas com conta no cadastro."""
    alvos = [f for f in fichas if f.get("act_id")]
    if not alvos:
        return {}
    lib.init_api(quiet=True)
    n = max(1, min(paralelo, len(alvos)))

    def uma(f):
        try:
            return f["act_id"], _saude.analisar_conta(f["act_id"], gasto_minimo, f.get("nome"))
        except Exception as e:  # uma conta com erro não derruba a carteira
            return f["act_id"], {"ok": False, "act_id": f["act_id"], "cliente": f.get("nome"),
                                 "erro": f"erro interno ({type(e).__name__}): {lib.redigir(e)}", "code": None}

    out = {}
    with ThreadPoolExecutor(max_workers=n) as ex:
        for act, r in ex.map(uma, alvos):
            out[act] = r
            print(("✅" if r.get("ok") and r["resumo"]["status"] == "ok" else "🔴" if r.get("ok") and r["resumo"]["status"] == "critico"
                   else "🟠" if r.get("ok") else "⚠️") + f" {r.get('cliente')} ({act})" + ("" if r.get("ok") else f": {r.get('erro')}"), file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# Classificação
# ---------------------------------------------------------------------------

def data_entrada(f):
    for k in ORDEM_ENTRADA:
        if f.get(k):
            return f[k], k
    return None, None


def pecas_da_conta(s):
    """Lista de (status, texto curto) a partir dos cinco sinais do saude.py, na ordem de urgência."""
    pecas = []
    sa = s.get("saldo_pagamento") or {}
    if sa.get("status") in PESO_PECA:
        st = sa["status"]
        if sa.get("status_conta") and sa["status_conta"] != "ATIVA":
            txt = f"conta {sa['status_conta']}"
            if (sa.get("valor_pendente_cobranca") or 0) > 0:
                txt += f" ({brl(sa['valor_pendente_cobranca'])} pendente)"
        elif sa.get("saldo_restante") is not None and sa["saldo_restante"] <= 0:
            txt = "saldo R$0 (parada)"
        elif sa.get("dias_de_saldo") is not None:
            txt = f"saldo {_dias(sa['dias_de_saldo'])} ({brl(sa.get('saldo_restante'))})"
        elif sa.get("limite_gasto_restante") is not None and sa["limite_gasto_restante"] <= 0:
            txt = "limite de gasto atingido"
        elif sa.get("dias_ate_limite") is not None:
            txt = f"limite de gasto em {_dias(sa['dias_ate_limite'])}"
        else:
            txt = sa.get("explicacao") or "saldo"
        pecas.append((st, txt))
    an = s.get("anuncios_problema") or {}
    if an.get("reprovados_em_campanha_ativa"):
        pecas.append(("critico", f"{an['reprovados_em_campanha_ativa']} reprovado(s) em campanha ativa"))
    elif an.get("com_problema_em_campanha_ativa"):
        pecas.append(("atencao", f"{an['com_problema_em_campanha_ativa']} anúncio(s) com problema"))
    g = s.get("gasto_sem_resultado") or {}
    if g.get("status") != "erro" and g.get("conta_7d"):
        atual = g["conta_7d"]
        if g.get("campanhas_sem_resultado"):
            total = round(sum(c.get("gasto_7d") or 0 for c in g["campanhas_sem_resultado"]), 2)
            pecas.append(("critico", f"{len(g['campanhas_sem_resultado'])} campanha(s) {brl(total)} sem msg"))
        elif g.get("status") == "critico" and atual.get("mensagens") == 0:
            pecas.append(("critico", f"{brl(atual.get('gasto'))} sem msg"))
        elif g.get("custo_acima_do_teto"):
            pecas.append(("critico", f"custo {brl(atual.get('custo_por_mensagem'))}"))
        elif g.get("status") in PESO_PECA and (g.get("variacao_custo_mensagem_pct") or 0) >= _saude.CUSTO_MSG_ATENCAO_PCT:
            pecas.append((g["status"], f"custo +{round(g['variacao_custo_mensagem_pct'])}%"))
        if g.get("campanhas_ativas") == 0:
            pecas.append(("critico", "0 campanhas ativas"))
        elif (atual.get("gasto") or 0) <= 0:
            pecas.append(("atencao", "sem gasto 7d"))
        outro = round(sum((c.get("atual") or {}).get("gasto") or 0 for c in g.get("campanhas") or [] if not c.get("mede_mensagem")), 2)
        if outro >= OUTRO_OBJETIVO_ATENCAO:
            pecas.append(("atencao", f"outro objetivo {brl(outro)} sem msg"))
    cr = s.get("criativos_sem_resultado") or {}
    if cr.get("sem_resultado"):
        total = round(sum(a.get("gasto_7d") or 0 for a in cr.get("anuncios_sem_resultado") or []), 2)
        pecas.append((cr.get("status") if cr.get("status") in PESO_PECA else "atencao",
                      f"{cr['sem_resultado']} anúncio(s) {brl(total)} sem msg"))
    rc = s.get("recencia") or {}
    if rc.get("status") in PESO_PECA:
        dias = rc.get("dias_sem_alteracao")
        if dias is None:
            pecas.append(("critico", f"sem alteração humana em {rc.get('janela_dias', 45)}d"))
        elif rc["status"] == "critico":
            pecas.append(("critico", f"{dias}d parada"))
        else:
            pecas.append(("atencao", f"{dias}d sem mexer"))
    return pecas


def classificar(f, r, hoje):
    """Uma linha da tabela: ficha do ClickUp + resultado do saude.py (ou None) -> classe, marcadores, situação."""
    entrada, fonte = data_entrada(f)
    dias = (hoje - _d(entrada)).days if entrada else None
    sat = f.get("satisfacao")
    linha = {
        "codigo": f.get("codigo"), "nome": f.get("nome"), "nome_curto": nome_curto(f.get("nome")),
        "clickup_task_id": f.get("clickup_task_id"), "gestor": f.get("gestor") or [],
        "status": f.get("status"), "fase": f.get("fase"), "produto": f.get("produto"), "ticket": f.get("ticket"),
        "satisfacao": sat, "satisfacao_curta": satisfacao_curta(sat),
        "cidade": f.get("cidade"), "especialidade": f.get("especialidade"),
        "entrou": entrada, "entrou_fonte": fonte, "dias_na_casa": dias,
        "recente": dias is not None and dias <= RECENTE_DIAS,
        "data_1a_campanha": f.get("data_1a_campanha"),
        "cadastrado": bool(f.get("cadastrado")), "act_id": f.get("act_id"), "act_nome": None,
        "leitura": None, "erro": None, "code": None,
        "msgs_7d": None, "custo_7d": None, "gasto_7d": None, "msgs_7d_anteriores": None, "custo_7d_anteriores": None,
        "campanhas_ativas": None, "dias_sem_alteracao": None, "saldo_restante": None, "dias_de_saldo": None,
        "classe": None, "marcadores": [], "pecas": [], "situacao": "",
    }
    insatisfeito = "insatisf" in clickup.normalizar(sat)
    pecas = []
    if not f.get("cadastrado"):
        linha["leitura"] = "sem_cadastro"
        linha["classe"] = "sem_conta"
    elif not f.get("act_id"):
        linha["leitura"] = "sem_conta"
        linha["classe"] = "sem_conta"
    elif r is None:
        linha["leitura"] = "nao_lida"
        linha["classe"] = "sem_leitura"
    elif not r.get("ok"):
        linha["leitura"] = "erro"
        linha["classe"] = "sem_leitura"
        linha["erro"], linha["code"] = r.get("erro"), r.get("code")
    else:
        linha["leitura"] = "ok"
        linha["act_nome"] = (r.get("conta") or {}).get("nome")
        s = r.get("sinais") or {}
        g = s.get("gasto_sem_resultado") or {}
        atual, ant = g.get("conta_7d") or {}, g.get("conta_7d_anteriores") or {}
        msgs, custo, gasto = atual.get("mensagens") or 0, atual.get("custo_por_mensagem"), atual.get("gasto") or 0
        linha.update({"msgs_7d": msgs, "custo_7d": custo, "gasto_7d": gasto,
                      "msgs_7d_anteriores": ant.get("mensagens"), "custo_7d_anteriores": ant.get("custo_por_mensagem"),
                      "campanhas_ativas": g.get("campanhas_ativas"),
                      "dias_sem_alteracao": (s.get("recencia") or {}).get("dias_sem_alteracao"),
                      "saldo_restante": (s.get("saldo_pagamento") or {}).get("saldo_restante"),
                      "dias_de_saldo": (s.get("saldo_pagamento") or {}).get("dias_de_saldo")})
        if g.get("status") == "erro":
            linha["classe"] = "sem_leitura"
            linha["erro"] = g.get("explicacao")
        elif gasto <= 0:
            linha["classe"] = "sem_gasto"
        elif msgs == 0:
            linha["classe"] = "sem_mensagem"
        elif custo is not None and custo >= BOM_CUSTO_MAX:
            linha["classe"] = "ruim"
        elif msgs >= MELHOR_MSGS_MIN and custo is not None and custo < MELHOR_CUSTO_MAX and not insatisfeito:
            linha["classe"] = "melhor"
        else:
            linha["classe"] = "bom"
        pecas = pecas_da_conta(s)
        if linha["classe"] == "sem_mensagem" and not any("sem msg" in t for _, t in pecas):
            pecas.append(("atencao", f"{brl(gasto)} sem msg"))

    # ficha: fase de entrada e status fora do ativo também contam
    fase = clickup.normalizar(f.get("fase"))
    if fase in FASES_ENTRANDO:
        pecas.append(("info", str(f.get("fase"))))
    if f.get("status") and f["status"] != "ativo":
        pecas.append(("info", str(f["status"])))
    if linha["leitura"] == "sem_cadastro":
        pecas.append(("info", "sem cadastro local"))
    elif linha["leitura"] == "sem_conta":
        pecas.append(("info", "sem conta ainda" if (fase in FASES_ENTRANDO or linha["recente"]) else "sem conta Meta no cadastro"))
    elif linha["leitura"] == "erro":
        pecas.append(("erro", f"sem leitura ({erro_curto(linha['erro'], linha['code'])})"))

    marc = []
    if linha["recente"]:
        marc.append("🆕")
    if linha["classe"] == "melhor":
        marc.append("⭐")
    elif linha["classe"] == "bom":
        marc.append("✅")
    crit = [t for st, t in pecas if st == "critico"]
    aten = [t for st, t in pecas if st == "atencao"]
    info = [t for st, t in pecas if st == "info"]
    erro = [t for st, t in pecas if st == "erro"]
    if crit:
        marc.append("🔴")
    elif aten:
        marc.append("🟡")
    if erro:
        marc.append("⚠️")
    partes = []
    if "⭐" in marc:
        partes.append("⭐")
    elif "✅" in marc:
        partes.append("✅")
    if crit:
        partes.append("🔴 " + "; ".join(crit))
    if aten:
        partes.append("🟡 " + "; ".join(aten))
    if erro:
        partes.append("⚠️ " + "; ".join(erro))
    if info:
        partes.append("; ".join(info))
    linha["marcadores"] = marc
    linha["pecas"] = [{"status": st, "texto": t} for st, t in pecas]
    linha["situacao"] = " · ".join(partes)
    return linha


# ---------------------------------------------------------------------------
# Tabela em markdown
# ---------------------------------------------------------------------------

def _col_produto(l):
    prod = l.get("produto") or "sem produto"
    t = l.get("ticket")
    if not t:
        return f"{prod} (sem ticket)"
    return f"{prod} {brl(t, 0)}" + (" (conferir: parece valor do contrato)" if t >= TICKET_SUSPEITO else "")


def _col_7d(l):
    if l["leitura"] in ("sem_cadastro", "sem_conta"):
        return "sem conta"
    if l["leitura"] == "erro":
        return f"sem leitura (#{l.get('code')})" if l.get("code") else "sem leitura"
    if l["leitura"] != "ok" or l["classe"] == "sem_leitura":
        return "sem leitura"
    if (l.get("gasto_7d") or 0) <= 0:
        return "sem gasto"
    if not l.get("msgs_7d"):
        return f"0 · {brl(l['gasto_7d'])} gastos"
    return f"{l['msgs_7d']} · {brl(l['custo_7d'])}"


def _ordem(l):
    return (l.get("entrou") or "0000-00-00", l.get("codigo") or "")


def tabela_gestor(nome, linhas, hoje):
    linhas = sorted(linhas, key=_ordem, reverse=True)
    ativos = [l for l in linhas if l.get("status") == "ativo"]
    outros = len(linhas) - len(ativos)
    cab = f"## {nome} ({len(ativos)} ativos" + (f" + {outros} fora do ativo" if outros else "") + ")"
    out = [cab, "", "| # | Cliente | Produto · ticket | Entrou | Satisfação | 7d: msgs · custo | Situação |",
           "|---|---|---|---|---|---|---|"]
    for l in linhas:
        cod = (l.get("codigo") or "").lstrip("#") or "?"
        entrou = fmt_data(l.get("entrou"), hoje) + (" 🆕" if l.get("recente") else "")
        out.append(f"| {cod} | {l['nome_curto']} | {_col_produto(l)} | {entrou} | {l['satisfacao_curta']} | {_col_7d(l)} | {l['situacao']} |")
    rec = [l for l in linhas if l.get("recente")]
    bons = [l for l in linhas if l["classe"] == "bom"]
    melhores = sorted([l for l in linhas if l["classe"] == "melhor"], key=lambda l: -(l.get("msgs_7d") or 0))
    crit = [l for l in linhas if "🔴" in l["marcadores"]]
    sem = [l for l in linhas if l["leitura"] == "erro"]
    sem_cad = [l for l in linhas if l["leitura"] == "sem_cadastro"]
    out.append("")
    out.append("- 🆕 **Recentes (até 30 dias)**: " + (", ".join(f"{l['nome_curto']} ({fmt_data(l['entrou'], hoje)}, {_col_7d(l)})" for l in rec) or "nenhum"))
    out.append("- ✅ **Bons**: " + (", ".join(f"{l['nome_curto']} ({_col_7d(l)})" for l in bons) or "nenhum"))
    out.append("- ⭐ **Melhores**: " + (", ".join(f"{l['nome_curto']} ({_col_7d(l)}, {l['satisfacao_curta']})" for l in melhores) or "nenhum"))
    out.append(f"- 🔴 **Com problema**: {len(crit)}" + (" (" + ", ".join(l["nome_curto"] for l in crit) + ")" if crit else ""))
    if sem:
        out.append("- ⚠️ **Sem leitura**: " + ", ".join(f"{l['nome_curto']} ({erro_curto(l.get('erro'), l.get('code'))})" for l in sem))
    if sem_cad:
        out.append("- 📋 **Sem cadastro local** (conta não lida): " + ", ".join(l["nome_curto"] for l in sem_cad))
    return "\n".join(out)


def alertas_relacionamento(linhas):
    """Ficha e conta em desacordo: quem está bem na conta mas crítico na ficha, e o contrário."""
    out = []
    for l in linhas:
        sat = clickup.normalizar(l.get("satisfacao"))
        ruim_ficha = "insatisf" in sat
        boa_ficha = "promotor" in sat or sat == "satisfeito" or "embaixador" in sat
        conta_bem = l["classe"] in ("bom", "melhor")
        conta_mal = "🔴" in l["marcadores"]
        if ruim_ficha and conta_mal:
            out.append({"tipo": "ficha_critica_conta_mal", "cliente": l["nome_curto"], "gestor": l["gestor"],
                        "nota": f"{l['satisfacao_curta']} na ficha e {l['situacao']}"})
        elif ruim_ficha and conta_bem:
            out.append({"tipo": "ficha_critica_conta_bem", "cliente": l["nome_curto"], "gestor": l["gestor"],
                        "nota": f"{l['satisfacao_curta']} na ficha, conta a {_col_7d(l)}"})
        elif boa_ficha and conta_mal:
            out.append({"tipo": "ficha_boa_conta_mal", "cliente": l["nome_curto"], "gestor": l["gestor"],
                        "nota": f"{l['satisfacao_curta']} na ficha, mas {l['situacao']}"})
    return out


def dinheiro(resultados):
    """Mesmo fechamento do /contas-criticas: gasto sem mensagem em 7d e contas parando por saldo."""
    sem_msg, param = 0.0, []
    for r in resultados.values():
        if not r.get("ok"):
            continue
        s = r["sinais"]
        g = s.get("gasto_sem_resultado") or {}
        sem_msg += sum(c.get("gasto_7d") or 0 for c in g.get("campanhas_sem_resultado") or [])
        cr = s.get("criativos_sem_resultado") or {}
        sem_msg += sum(a.get("gasto_7d") or 0 for a in cr.get("anuncios_sem_resultado") or [])
        sa = s.get("saldo_pagamento") or {}
        if sa.get("status") == "critico" and sa.get("saldo_restante") is not None:
            param.append({"cliente": r.get("cliente"), "saldo_restante": sa.get("saldo_restante"),
                          "dias_de_saldo": sa.get("dias_de_saldo"), "gasto_medio_dia_7d": sa.get("gasto_medio_dia_7d")})
    return {"gasto_7d_sem_mensagem": round(sem_msg, 2), "contas_parando_por_saldo": param}


def imprimir_tabelas(analise, dest=sys.stderr):
    hoje = _d(analise.get("data")) or date.today()
    j = analise.get("janela") or {}
    print(f"Carteira em {hoje.strftime('%d/%m/%Y')} · 7d = {j.get('desde', '?')} a {j.get('ate', '?')} · {analise.get('escopo', '')}", file=dest)
    print("Legenda: 🆕 entrou há 30 dias ou menos · ✅ bom (mensagem abaixo de R$35) · ⭐ melhor (20+ msgs a menos de R$30, ficha não insatisfeita) · 🔴 crítico · 🟡 atenção · ⚠️ sem leitura", file=dest)
    print("", file=dest)
    for g in analise.get("gestores", []):
        print(tabela_gestor(g["gestor"], g["clientes"], hoje), file=dest)
        print("", file=dest)
    if analise.get("alertas_relacionamento"):
        print("**Alertas de relacionamento (ficha x conta):**", file=dest)
        for a in analise["alertas_relacionamento"]:
            print(f"- {a['cliente']} ({primeiro_nome((a.get('gestor') or [None])[0])}): {a['nota']}", file=dest)
        print("", file=dest)
    if analise.get("sem_cadastro"):
        print(f"**Sem cadastro local ({len(analise['sem_cadastro'])})**, conta não lida; o head cadastra com "
              "`clientes.py cadastrar --nome X --carteira` e confirma a conta com `definir-conta`: "
              + ", ".join(p["nome_curto"] for p in analise["sem_cadastro"]), file=dest)
        print("", file=dest)
    d = analise.get("dinheiro") or {}
    if d:
        print(f"💰 Gasto em 7 dias sem mensagem (campanhas e anúncios): {brl(d.get('gasto_7d_sem_mensagem', 0))} · contas parando por saldo: {len(d.get('contas_parando_por_saldo') or [])}", file=dest)


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

def montar_analise(fichas, resultados, hoje, escopo, so_ficha):
    linhas = [classificar(f, resultados.get(f.get("act_id")) if f.get("act_id") else None, hoje) for f in fichas]
    por_gestor = {}
    for l in linhas:
        por_gestor.setdefault(primeiro_nome((l.get("gestor") or [None])[0]), []).append(l)
    gestores = []
    for nome, ls in sorted(por_gestor.items()):
        gestores.append({"gestor": nome, "gestor_completo": (ls[0].get("gestor") or [None])[0], "total": len(ls),
                         "ativos": sum(1 for l in ls if l.get("status") == "ativo"),
                         "recentes": [l["nome_curto"] for l in ls if l["recente"]],
                         "bons": [l["nome_curto"] for l in ls if l["classe"] == "bom"],
                         "melhores": [l["nome_curto"] for l in sorted(ls, key=lambda l: -(l.get("msgs_7d") or 0)) if l["classe"] == "melhor"],
                         "com_problema": [l["nome_curto"] for l in ls if "🔴" in l["marcadores"]],
                         "sem_leitura": [l["nome_curto"] for l in ls if l["leitura"] == "erro"],
                         "sem_cadastro": [l["nome_curto"] for l in ls if l["leitura"] == "sem_cadastro"],
                         "clientes": sorted(ls, key=_ordem, reverse=True)})
    janela = next((r["janelas"]["atual"] for r in resultados.values() if r.get("ok") and r.get("janelas")), None)
    return {"ok": True, "data": hoje.isoformat(), "escopo": escopo, "janela": janela, "so_ficha": so_ficha,
            "total": len(linhas), "lidas": sum(1 for l in linhas if l["leitura"] == "ok"),
            "gestores": gestores,
            "sem_cadastro": [{"codigo": l["codigo"], "nome": l["nome"], "nome_curto": l["nome_curto"], "gestor": l["gestor"],
                              "fase": l["fase"], "status": l["status"]} for l in linhas if l["leitura"] == "sem_cadastro"],
            "sem_conta": [{"codigo": l["codigo"], "nome": l["nome"], "nome_curto": l["nome_curto"], "gestor": l["gestor"],
                           "fase": l["fase"], "status": l["status"]} for l in linhas if l["leitura"] == "sem_conta"],
            "sem_leitura": [{"codigo": l["codigo"], "nome_curto": l["nome_curto"], "act_id": l["act_id"], "erro": l["erro"], "code": l["code"],
                             "acao": (resultados.get(l["act_id"]) or {}).get("acao")} for l in linhas if l["leitura"] == "erro"],
            "alertas_relacionamento": alertas_relacionamento(linhas),
            "dinheiro": dinheiro(resultados) if resultados else None,
            "cadastro": watchlist.CADASTRO_PATH}


def cmd_analisar(a):
    hoje = date.today()
    fichas, escopo = ler_fichas(a.gestor, a.todos)
    cadastro = watchlist.carregar()
    por_task = {c.get("clickup_task_id"): c for c in cadastro.get("clientes", []) if c.get("clickup_task_id")}
    por_cod = {c.get("codigo"): c for c in cadastro.get("clientes", []) if c.get("codigo")}
    if not a.inativos:
        fichas = [f for f in fichas if (f.get("status") or "") not in STATUS_EXCLUIDOS]
    for f in fichas:
        c = por_task.get(f.get("clickup_task_id")) or por_cod.get(f.get("codigo"))
        f["cadastrado"] = bool(c)
        if c and c.get("act_id"):
            f["act_id"], f["act_nome"] = c["act_id"], c.get("act_nome")
    resultados = {}
    if not a.so_ficha:
        alvos = [f for f in fichas if f.get("act_id")]
        print(f"Escopo {escopo}: {len(fichas)} perfis, {len(alvos)} com conta no cadastro. Lendo em até {a.paralelo} threads...", file=sys.stderr)
        resultados = ler_contas(fichas, a.paralelo, a.gasto_minimo)
    analise = montar_analise(fichas, resultados, hoje, escopo, a.so_ficha)
    imprimir_tabelas(analise)
    analise["salvo_em"] = salvar_analise(analise)
    lib.print_json(analise)


def salvar_analise(analise):
    """Guarda a análise do dia sem ticket nem verba (dado de contrato não fica em arquivo)."""
    try:
        os.makedirs(HISTORICO_DIR, exist_ok=True)
        copia = json.loads(json.dumps(analise, ensure_ascii=False))
        for g in copia.get("gestores", []):
            for l in g.get("clientes", []):
                for k in CAMPOS_NAO_SALVOS:
                    l.pop(k, None)
        path = os.path.join(HISTORICO_DIR, f"analise-{analise['data']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(copia, f, ensure_ascii=False, indent=1)
        os.chmod(path, 0o600)
        return path
    except OSError as e:
        print(f"aviso: não consegui salvar a análise ({type(e).__name__})", file=sys.stderr)
        return None


def cmd_tabela(a):
    path = a.arquivo
    if not path:
        arquivos = sorted(x for x in (os.listdir(HISTORICO_DIR) if os.path.isdir(HISTORICO_DIR) else [])
                          if x.startswith("analise-") and x.endswith(".json"))
        if not arquivos:
            falha("nenhuma análise salva ainda", "rodar: carteira.py analisar --gestor NOME")
        path = os.path.join(HISTORICO_DIR, arquivos[-1])
    with open(path, encoding="utf-8") as f:
        analise = json.load(f)
    imprimir_tabelas(analise, dest=sys.stdout)


def main():
    p = argparse.ArgumentParser(description="Carteira por gestor: ficha do ClickUp + saúde da conta Meta (só leitura)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("analisar", help="tabela por gestor: recentes, bons, melhores e problemas")
    s.add_argument("--gestor", action="append", help="nome (ou trecho) do gestor; repetir para mais de um. Só o head")
    s.add_argument("--todos", action="store_true", help="carteira inteira (só o head)")
    s.add_argument("--paralelo", type=int, default=4, help="contas lidas ao mesmo tempo (padrão 4)")
    s.add_argument("--inativos", action="store_true", help="incluir clientes com status inativo/churn")
    s.add_argument("--so-ficha", action="store_true", help="só o ClickUp, sem ler as contas Meta")
    s.add_argument("--gasto-minimo", type=int, default=_saude.GASTO_MINIMO_CENTAVOS, help="repassado ao saude.py (centavos)")
    s.set_defaults(fn=cmd_analisar)
    s = sub.add_parser("tabela", help="reimprime as tabelas de uma análise salva")
    s.add_argument("arquivo", nargs="?")
    s.set_defaults(fn=cmd_tabela)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:  # nunca imprimir str(e) cru
        falha(f"erro interno ({type(e).__name__}): {lib.redigir(e)}", code=2)


if __name__ == "__main__":
    main()
