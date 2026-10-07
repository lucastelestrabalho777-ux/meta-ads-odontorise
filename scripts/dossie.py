#!/usr/bin/env python3
"""
meta-ads-odontorise: dossiê do cliente novo para a Reunião de Onboarding (head). Só leitura.

Junta, numa chamada só, tudo o que o ClickUp tem sobre um cliente que está entrando:
  Perfil de Clientes (só campos operacionais), Formulário de Pré-Onboarding (campos "PO - ..."),
  Onboarding (tarefa-mãe + etapas), Reuniões com Clientes (onboarding marcado), anexos e comentários
  dessas tarefas, Demandas Comerciais com o nome do cliente e o link da pasta do Drive.

Subcomandos:
  proximas [--dias 7]              reuniões de onboarding marcadas nos próximos N dias (hoje incluso)
  cliente  --cliente "<nome | #código | id do perfil>"   dossiê completo em JSON
  anexo    --url <url do anexo> --pasta <pasta local>      baixa um anexo (Relatório Comercial em PDF vira .txt ao lado)

Dados pessoais (CPF, CNPJ, telefone, e-mail, endereço) e financeiros (valores de contrato) ficam no
ClickUp: não entram na saída. Nada é escrito no ClickUp.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, date, timedelta

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import clickup  # noqa: E402

LISTA_REUNIOES_ID = "901714773363"
LISTA_PRE_ONBOARDING_ID = "901716898751"
LISTA_DEMANDAS_COMERCIAIS_ID = "901716919659"

# Campos do Perfil que entram no dossiê (nome no ClickUp -> chave). O resto fica no ClickUp.
PERFIL_CAMPOS = {
    "Código do Cliente": "codigo",
    "Produto": "produto",
    "Fase Global": "fase",
    "Especialidade Odontologica": "especialidade",
    "Especialidade Secundária": "especialidade_2",
    "Objetivo Principal": "objetivo",
    "Canal de Aquisição": "canal_aquisicao",
    "Cidade": "cidade",
    "Estado": "estado",
    "Instagram": "instagram",
    "Drive Geral": "drive",
    "Link do Data Studio": "data_studio",
    "Faturamento Inicial": "faturamento_inicial_faixa",
    "Tempo de Contrato (Meses)": "contrato_meses",
    "Data de Fechamento": "fechamento",
    "Data do Primeiro pagamento (vigência)": "vigencia_inicio",
    "Status do Projeto": "status_projeto",
    "Health Score": "health_score",
    "Gestor": "gestor",
    "CS": "cs",
    "Liderança": "lideranca",
    "Comercial": "closer",
}
PERFIL_DATAS = {"fechamento", "vigencia_inicio"}

# Formulário de Pré-Onboarding: blocos na ordem da reunião (02. Reunião de Onboarding, 4.1 a 4.6).
PO_BLOCOS = [
    ("historia_e_momento", "História da clínica e momento atual", [
        "Faturamento mensal atual", "Variação de faturamento (12 meses)", "Evolução nos últimos 12 meses",
        "Meta de faturamento (6 meses)", "Meta de novos pacientes por mês", "Resultado esperado com a OdontoRise",
        "Principal desafio para crescer", "Existe sazonalidade", "Detalhes da sazonalidade"]),
    ("estrutura_e_capacidade", "Estrutura e capacidade de atendimento", [
        "Locais de atendimento", "Quantidade de locais de atendimento", "Endereço do local principal",
        "Dentistas no local", "Cadeiras disponíveis no local", "Capacidade para novos pacientes",
        "Dias e horários de atendimento", "Principal decisor da clínica", "Responsável Técnico e CRO"]),
    ("tratamento_e_oferta", "Tratamento prioritário e oferta", [
        "Tratamento prioritário", "Motivo da prioridade do tratamento", "Ticket médio do tratamento prioritário",
        "Formas de pagamento oferecidas", "Condições de pagamento mais usadas", "Tempo até o fechamento",
        "Tratamentos ou perfis a evitar"]),
    ("paciente_regiao_posicionamento", "Paciente, região e posicionamento", [
        "Perfil do paciente desejado", "Dores e desejos do paciente", "Objeções mais comuns", "Objeção (outro) - qual",
        "Regiões dos melhores pacientes", "Distância de deslocamento do paciente", "Diferencial percebido da clínica",
        "Referências de comunicação admiradas"]),
    ("marketing_e_historico", "Marketing e histórico de aquisição", [
        "Canais de chegada dos pacientes", "Já investiu em tráfego pago", "Plataformas já anunciadas",
        "Experiência com tráfego pago", "Investimento mensal anterior em anúncios", "Leads gerados por mês (histórico)",
        "Leads que viraram pacientes (histórico)", "Faturamento gerado pelas campanhas (histórico)",
        "Investimento mensal em mídia neste projeto", "Instagram principal", "Clínica possui site", "Endereço do site",
        "Clínica possui domínio próprio", "Domínio da clínica", "Pessoa que aparece nos vídeos",
        "Restrições para gravar vídeos", "Responsável por aprovar criativos"]),
    ("comercial_e_jornada_do_lead", "Processo comercial e jornada do lead", [
        "Responsável por atender os leads", "Dedicação do responsável comercial", "Canais de atendimento dos leads",
        "Tentativas de contato antes de desistir", "Rotina de follow-up", "Utiliza CRM", "Qual CRM utilizam",
        "Indicadores acompanhados hoje", "Conhece a taxa de conversão", "Conversão a cada 10 leads"]),
    ("outros", "Informações adicionais", ["Informações adicionais"]),
]
PO_PREFIXO = "PO - "
# Campos em moeda que o cliente costuma responder "em milhares" (3 = R$ 3.000).
PO_MOEDA = {"Faturamento mensal atual", "Meta de faturamento (6 meses)", "Ticket médio do tratamento prioritário",
            "Investimento mensal anterior em anúncios", "Investimento mensal em mídia neste projeto",
            "Faturamento gerado pelas campanhas (histórico)"}


def _data(ms, hora=False):
    if not ms:
        return None
    d = datetime.fromtimestamp(int(ms) / 1000)
    return d.strftime("%Y-%m-%d %H:%M") if hora else d.strftime("%Y-%m-%d")


def _nomes(v):
    if isinstance(v, list):
        return [x.get("nome") if isinstance(x, dict) else x for x in v]
    return v


def _limpa(v):
    if isinstance(v, str):
        v = re.sub(r"\s+\n", "\n", v).strip()
        return v or None
    return v


def _falha(msg, acao=None):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)


def _anexos(t):
    return [{"titulo": a.get("title"), "url": a.get("url"), "extensao": a.get("extension"), "em": t.get("name")}
            for a in (t.get("attachments") or [])]


def _comentarios(task_id, origem):
    """Comentários da tarefa. Anexo colado num comentário vem em 'anexos' (é assim que o Relatório Comercial costuma chegar)."""
    ok, c = clickup.get(f"task/{task_id}/comment")
    if not ok:
        return []
    out = []
    for x in c.get("comments", []):
        anexos = [{"titulo": (b.get("attachment") or {}).get("title"), "url": (b.get("attachment") or {}).get("url"),
                   "extensao": (b.get("attachment") or {}).get("extension"), "em": f"comentário ({origem})"}
                  for b in x.get("comment", []) if b.get("type") == "attachment" and b.get("attachment")]
        out.append({"origem": origem, "quem": x.get("user", {}).get("username"), "quando": _data(x.get("date"), hora=True),
                    "texto": (x.get("comment_text") or "")[:1500], "anexos": anexos})
    return out


def _relacao_ids(t, nome_campo):
    v = clickup.valor(t, nome_campo)
    if isinstance(v, list):
        return [x.get("id") for x in v if isinstance(x, dict) and x.get("id")]
    return []


# ---------------------------------------------------------------------------
# Perfil

def _achar_perfil(chave):
    ok, todos = clickup.perfis()
    if not ok:
        _falha(todos.get("erro"), "conferir a internet e o token do ClickUp (passo 8 do guia)")
    k = str(chave).strip()
    if re.fullmatch(r"#?\d{2,5}", k):
        cod = k if k.startswith("#") else f"#{k}"
        achados = [t for t in todos if (clickup.valor(t, "Código do Cliente") or "").strip() == cod]
    elif re.fullmatch(r"[a-z0-9]{7,12}", k) and not " " in k and any(ch.isdigit() for ch in k):
        achados = [t for t in todos if t.get("id") == k]
        if not achados:
            achados = [t for t in todos if clickup.normalizar(k) in clickup.normalizar(t.get("name"))]
    else:
        alvo = clickup.normalizar(k)
        achados = [t for t in todos if alvo and alvo in clickup.normalizar(t.get("name"))]
    if not achados:
        _falha(f"nenhum perfil no ClickUp com '{chave}'", "conferir o nome em Perfil de Clientes, ou usar o #código ou o id da task do perfil")
    if len(achados) > 1:
        print(json.dumps({"ok": False, "erro": "mais de um perfil encontrado; repita com o #código ou o id",
                          "perfis": [{"id": t["id"], "nome": t["name"], "codigo": clickup.valor(t, "Código do Cliente"),
                                      "status": t["status"]["status"]} for t in achados]}, ensure_ascii=False, indent=2))
        sys.exit(1)
    return achados[0]


def _resumo_perfil(t):
    r = {"id": t.get("id"), "nome": t.get("name"), "status": t.get("status", {}).get("status"), "url": t.get("url"),
         "criado_em": _data(t.get("date_created"))}
    for c in t.get("custom_fields", []):
        chave = PERFIL_CAMPOS.get(c.get("name"))
        if not chave:
            continue
        v = clickup._valor_campo(c)
        if v is None:
            continue
        if c.get("type") == "users":
            v = _nomes(v)
        elif chave in PERFIL_DATAS:
            v = _data(v)
        r[chave] = v
    return r


# ---------------------------------------------------------------------------
# Formulário de Pré-Onboarding

def _formulario(perfil_task):
    ids = _relacao_ids(perfil_task, "Pré-Onboarding | Respostas do Cliente")
    t = None
    if ids:
        ok, t = clickup.get(f"task/{ids[0]}")
        if not ok:
            t = None
    if t is None:  # fallback: procurar pelo nome na lista do formulário
        ok, ts = clickup.tarefas(LISTA_PRE_ONBOARDING_ID, include_closed=True)
        if ok:
            toks = {w for w in clickup.normalizar(perfil_task.get("name")).split() if len(w) >= 4 and w not in ("clinica", "odontologia")}
            cand = [x for x in ts if toks & set(clickup.normalizar(x.get("name")).split())]
            t = cand[0] if cand else None
    if t is None:
        return {"encontrado": False, "motivo": "nenhuma resposta do Formulário de Pré-Onboarding ligada a este perfil"}
    campos = {c["name"][len(PO_PREFIXO):]: (c.get("type"), _limpa(clickup._valor_campo(c)))
              for c in t.get("custom_fields", []) if c.get("name", "").startswith(PO_PREFIXO)}
    blocos, vistos, vazios = [], set(), []
    for chave, titulo, nomes in PO_BLOCOS:
        itens = []
        for n in nomes:
            vistos.add(n)
            tipo, v = campos.get(n, (None, None))
            if v is None:
                vazios.append(n)
                continue
            if tipo == "currency":
                v = _moeda(v)
            itens.append({"campo": n, "valor": v})
        blocos.append({"bloco": chave, "titulo": titulo, "respostas": itens})
    extras = [{"campo": n, "valor": v} for n, (tp, v) in campos.items() if n not in vistos and v is not None]
    if extras:
        blocos.append({"bloco": "nao_mapeados", "titulo": "Campos novos do formulário (fora dos blocos)", "respostas": extras})
    respondidos = sum(len(b["respostas"]) for b in blocos)
    return {"encontrado": True, "id": t.get("id"), "url": t.get("url"), "status": t.get("status", {}).get("status"),
            "respondido_em": _data(t.get("date_created"), hora=True), "responsavel_analise": [a.get("username") for a in t.get("assignees", [])],
            "respondidos": respondidos, "vazios": vazios, "blocos": blocos,
            "alertas_automaticos": _alertas(campos), "anexos": _anexos(t), "comentarios": _comentarios(t["id"], "formulário")}


def _moeda(v):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return v
    if n < 1000:
        return {"valor_digitado": n, "leitura_provavel": f"R$ {n:,.0f} mil".replace(",", "."), "confirmar": True}
    return {"valor_digitado": n, "leitura_provavel": f"R$ {n:,.0f}".replace(",", "."), "confirmar": False}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_dinheiro(txt):
    """'300k', '300 mil', 'R$ 300.000' -> 300000.0; sem número -> None."""
    if not txt:
        return None
    t = str(txt).lower().replace("r$", "").replace(".", "").replace(" ", "")
    m = re.search(r"(\d+(?:,\d+)?)(k|mil)?", t)
    if not m:
        return None
    n = float(m.group(1).replace(",", "."))
    return n * 1000 if m.group(2) else n


def _faixa(txt):
    """'Entre 10-30 mil' -> (10000, 30000); 'Acima de 100 mil' -> (100000, None); sem número -> None."""
    if not txt:
        return None
    nums = [float(x) for x in re.findall(r"\d+", str(txt))]
    if not nums:
        return None
    mult = 1000 if "mil" in str(txt).lower() else 1
    lo = nums[0] * mult
    hi = nums[1] * mult if len(nums) > 1 else None
    low = str(txt).lower()
    if "acima" in low or "mais de" in low:
        return (lo, None)
    if "até" in low or "abaixo" in low or "menos de" in low:
        return (0, lo)
    return (lo, hi)


def _alertas_perfil(perfil, campos):
    """Cruzamentos entre o perfil do ClickUp (preenchido pelo comercial) e o formulário (preenchido pelo cliente)."""
    al = []
    fx = _faixa(perfil.get("faturamento_inicial_faixa"))
    fat = _num(campos.get("Faturamento mensal atual", (None, None))[1])
    if fx and fat:
        f = fat * 1000 if fat < 1000 else fat
        lo, hi = fx
        if f < lo or (hi is not None and f > hi):
            al.append(f"Perfil (comercial) diz faturamento '{perfil.get('faturamento_inicial_faixa')}'; o formulário diz R$ {f:,.0f}/mês. Confirmar na reunião qual é o número real e de quem (clínica inteira ou a agenda do cliente).".replace(",", "."))
    esp = (perfil.get("especialidade") or "").lower()
    trat = (campos.get("Tratamento prioritário", (None, None))[1] or "").lower()
    if esp and trat and esp.split()[0][:4] not in trat:
        al.append(f"Especialidade no perfil ('{perfil.get('especialidade')}') e tratamento prioritário no formulário ('{trat.strip()}') não coincidem. Confirmar o que será anunciado.")
    ig_perfil = (perfil.get("instagram") or "").lower()
    ig_form = (campos.get("Instagram principal", (None, None))[1] or "").strip().lstrip("@").lower()
    if ig_perfil and ig_form and ig_form not in ig_perfil:
        al.append(f"Instagram do perfil ({ig_perfil}) e do formulário (@{ig_form}) são diferentes. Confirmar qual conta anuncia.")
    return al


def _alertas(campos):
    """Inconsistências mecânicas do formulário. A leitura de negócio é do head, não do script."""
    g = lambda n: campos.get(n, (None, None))[1]
    al = []
    for n in PO_MOEDA:
        x = _num(g(n))
        if x is not None and 0 < x < 1000:
            al.append(f"'{n}' veio como {x:g}: provavelmente em milhares (R$ {x:g} mil). Confirmar a unidade na reunião.")
    loc, qtd = g("Locais de atendimento"), _num(g("Quantidade de locais de atendimento"))
    if loc and qtd is not None and "mais de um" in loc.lower() and qtd <= 1:
        al.append(f"'Locais de atendimento' diz '{loc}' mas 'Quantidade de locais' = {qtd:g}. Confirmar quantos endereços e onde anunciar.")
    crm, qual = g("Utiliza CRM"), g("Qual CRM utilizam")
    if crm and crm.lower().startswith("sim") and (not qual or qual.strip().lower() in ("sim", "não", "nao")):
        al.append("Diz que usa CRM mas não nomeou qual. Perguntar o nome da ferramenta (o Select depende do CRM preenchido).")
    atende = g("Responsável por atender os leads") or ""
    if "crm" in atende.lower():
        al.append(f"'Responsável por atender os leads' = '{atende.strip()}': parece confundir CRM com pessoa. Perguntar quem (nome e função) responde o WhatsApp.")
    leads, pac = _num(g("Leads gerados por mês (histórico)")), _num(g("Leads que viraram pacientes (histórico)"))
    if leads and pac is not None:
        al.append(f"Histórico declarado: {pac:g} paciente(s) a cada {leads:g} leads/mês ({pac / leads:.0%} de conversão). Investigar o atendimento antes de culpar o lead.")
    conv10 = _num(g("Conversão a cada 10 leads"))
    if conv10 is not None and leads and pac is not None and abs(conv10 / 10 - pac / leads) > 0.15:
        al.append(f"'Conversão a cada 10 leads' ({conv10:g}) não bate com o histórico declarado ({pac:g} de {leads:g}).")
    fat, meta = _num(g("Faturamento mensal atual")), _num(g("Meta de faturamento (6 meses)"))
    tk, metap = _num(g("Ticket médio do tratamento prioritário")), _num(g("Meta de novos pacientes por mês"))
    inv = _num(g("Investimento mensal em mídia neste projeto"))
    if fat and meta and tk:
        mil = lambda x: x * 1000 if x < 1000 else x  # cada campo pode ter vindo em milhares
        f, m, t = mil(fat), mil(meta), mil(tk)
        delta = m - f
        if delta > 0:
            al.append(f"Para ir de R$ {f:,.0f} a R$ {m:,.0f} faltam R$ {delta:,.0f}/mês: cerca de {delta / t:.0f} paciente(s) novo(s) por mês do tratamento prioritário (ticket R$ {t:,.0f}).".replace(",", "."))
        elif delta <= 0:
            al.append("Meta de faturamento em 6 meses é igual ou menor que o faturamento atual. Confirmar o número.")
    if fat and meta and tk and metap:
        mil = lambda x: x * 1000 if x < 1000 else x
        precisa = (mil(meta) - mil(fat)) / mil(tk)
        if precisa > 0 and (metap > 2 * precisa or metap < precisa / 2):
            al.append(f"Meta de pacientes ({metap:g}/mês) não bate com o gap de faturamento ({precisa:.0f} paciente(s) de R$ {mil(tk):,.0f} fecham a meta). Perguntar qual meta vale (faturamento ou pacientes) e se os pacientes são todos do tratamento prioritário.".replace(",", "."))
    var = g("Variação de faturamento (12 meses)")
    anual = _parse_dinheiro(var)
    if anual and fat:
        mensal = anual / 12
        f = fat * 1000 if fat < 1000 else fat
        if mensal < f * 0.6 or mensal > f * 1.6:
            al.append(f"'Variação de faturamento (12 meses)' = '{var.strip()}' (R$ {anual:,.0f}/ano = R$ {mensal:,.0f}/mês) não bate com o faturamento mensal declarado (R$ {f:,.0f}). Confirmar o que é o 60 e o que é o anual: clínica inteira ou só a agenda dela?".replace(",", "."))
    if inv and metap:
        i = inv if inv >= 1000 else inv * 1000
        al.append(f"Investimento de R$ {i:,.0f}/mês para {metap:g} paciente(s) novo(s) = teto implícito de R$ {i / metap:,.0f} por paciente fechado.".replace(",", "."))
    exp = (g("Experiência com tráfego pago") or "").lower()
    if any(w in exp for w in ("péssim", "pessim", "ruim", "não funcionou", "nao funcionou", "horr")):
        al.append("Experiência anterior com tráfego foi ruim: entender o que exatamente deu errado (campanha, atendimento, oferta, verba, acompanhamento) antes de prometer.")
    cap, cad, dent = g("Capacidade para novos pacientes") or "", _num(g("Cadeiras disponíveis no local")), _num(g("Dentistas no local"))
    if "bastante" in cap.lower() and cad is not None and cad <= 2:
        al.append(f"Diz ter bastante capacidade com {cad:g} cadeira(s) e {dent:g} dentista(s): confirmar quantos pacientes novos por semana a agenda absorve de verdade.")
    dist = g("Distância de deslocamento do paciente") or ""
    reg = g("Regiões dos melhores pacientes") or ""
    if "20 km" in dist or "outras cidades" in dist.lower() or "100" in reg:
        al.append("Pacientes vêm de longe (outras cidades/raio grande): decidir na reunião o recorte geográfico sem ampliar raio por padrão; regra da casa é nunca ampliar raio.")
    return al


# ---------------------------------------------------------------------------
# Onboarding, reuniões, demandas

def _onboarding(perfil_task):
    ids = _relacao_ids(perfil_task, "Onboarding")
    ok, ts = clickup.tarefas(clickup.LISTA_ONBOARDING_ID, include_closed=True)
    if not ok:
        return {"encontrado": False, "motivo": ts.get("erro")}
    mae = None
    if ids:
        mae = next((t for t in ts if t.get("id") == ids[0]), None)
    if mae is None:
        cod = perfil_task.get("id")
        mae = next((t for t in ts if not t.get("parent") and cod and cod in t.get("name", "")), None)
    if mae is None:
        return {"encontrado": False, "motivo": "nenhuma tarefa de Onboarding ligada a este perfil"}
    subs = [t for t in ts if t.get("parent") == mae["id"]]

    def chave(t):
        e = clickup.valor(t, "Etapas do Onboarding") or ""
        m = re.match(r"\[ON(\d)\]\s*(\d+)", e)
        return (int(m.group(1)), int(m.group(2))) if m else (9, 99)
    subs.sort(key=chave)
    etapas = [{"id": t["id"], "etapa": clickup.valor(t, "Etapas do Onboarding") or t["name"], "status": t["status"]["status"],
               "concluida": t["status"]["type"] == "closed", "setor": clickup.valor(t, "Setor"),
               "responsaveis": [a["username"] for a in t.get("assignees", [])], "prazo": _data(t.get("due_date")),
               "concluida_em": _data(t.get("date_done") or t.get("date_closed"))} for t in subs]
    feitas = [e for e in etapas if e["concluida"]]
    # Roteiro da casa e checklists moram nas subtarefas: trazer a da reunião e as próximas pendentes.
    eh_reuniao = lambda e: "reuniao de onboarding" in clickup.normalizar(e["etapa"])
    detalhar = [e for e in etapas if eh_reuniao(e)] + [e for e in etapas if not e["concluida"] and not eh_reuniao(e)][:3]
    for e in detalhar:
        ok, t = clickup.get(f"task/{e['id']}")
        if not ok:
            continue
        e["descricao"] = (t.get("text_content") or "").strip()[:4000] or None
        e["checklist"] = [{"nome": c.get("name"), "itens": [{"item": i.get("name"), "feito": bool(i.get("resolved"))} for i in c.get("items", [])]} for c in t.get("checklists", [])] or None
        e["anexos"] = _anexos(t) or None
    prog = clickup.valor(mae, "Progresso Onboarding")
    return {"encontrado": True, "id": mae["id"], "url": mae.get("url"), "status": mae["status"]["status"], "fase": clickup.valor(mae, "Etapas do Onboarding"),
            "iniciado_em": _data(mae.get("date_created")), "progresso_pct": prog.get("percent_complete") if isinstance(prog, dict) else prog,
            "feitas": len(feitas), "total": len(etapas),
            "proximas_depois_da_reuniao": [e for e in etapas if not e["concluida"] and not eh_reuniao(e)][:4], "etapas": etapas,
            "anexos": _anexos(mae), "comentarios": _comentarios(mae["id"], "onboarding")}


def _reunioes(perfil_task):
    ids = _relacao_ids(perfil_task, "Reuniões com Clientes")
    out = []
    for i in ids:
        ok, t = clickup.get(f"task/{i}")
        if not ok:
            continue
        dur = (int(t["due_date"]) - int(t["start_date"])) / 60000 if t.get("start_date") and t.get("due_date") else None
        out.append({"id": t["id"], "url": t.get("url"), "nome": t["name"], "status": t["status"]["status"],
                    "tipo": clickup.valor(t, "Tipo de Reunião"), "inicio": _data(t.get("start_date"), hora=True),
                    "fim": _data(t.get("due_date"), hora=True), "duracao_min": dur,
                    "aviso_duracao": (f"slot de {dur:.0f} min; o Playbook prevê 50 a 60" if dur and dur < 50 else None),
                    "link": clickup.valor(t, "Link Reunião"), "link_tipo": "Calendly (abre o Meet)" if "calendly" in (clickup.valor(t, "Link Reunião") or "") else None,
                    "convidado": clickup.valor(t, "Nome do Convidado"), "responsaveis": [a["username"] for a in t.get("assignees", [])],
                    "anexos": _anexos(t), "comentarios": _comentarios(t["id"], "reunião")})
    out.sort(key=lambda r: r.get("inicio") or "")
    return out


def _demandas_comerciais(perfil_task):
    ok, ts = clickup.tarefas(LISTA_DEMANDAS_COMERCIAIS_ID, include_closed=True)
    if not ok:
        return []
    toks = {w for w in clickup.normalizar(perfil_task.get("name")).split() if len(w) >= 4 and w not in ("clinica", "odontologia", "odontologica")}
    out = []
    for t in ts:
        if toks & set(clickup.normalizar(t.get("name")).split()):
            out.append({"id": t["id"], "url": t.get("url"), "nome": t["name"], "status": t["status"]["status"],
                        "descricao": (t.get("text_content") or "")[:1500], "anexos": _anexos(t)})
    return out


# ---------------------------------------------------------------------------

def cmd_cliente(a):
    perfil_task = _achar_perfil(a.cliente)
    perfil = _resumo_perfil(perfil_task)
    form = _formulario(perfil_task)
    if form.get("encontrado"):
        campos_po = {c["name"][len(PO_PREFIXO):]: (c.get("type"), _limpa(clickup._valor_campo(c)))
                     for c in (clickup.get(f"task/{form['id']}")[1] or {}).get("custom_fields", []) if c.get("name", "").startswith(PO_PREFIXO)}
        form["alertas_automaticos"] = _alertas_perfil(perfil, campos_po) + form.get("alertas_automaticos", [])
    onb = _onboarding(perfil_task)
    reun = _reunioes(perfil_task)
    dem = _demandas_comerciais(perfil_task)
    comentarios = _comentarios(perfil_task["id"], "perfil") + form.get("comentarios", []) + onb.get("comentarios", []) + [x for r in reun for x in r["comentarios"]]
    anexos = (_anexos(perfil_task) + form.get("anexos", []) + onb.get("anexos", []) + [x for r in reun for x in r["anexos"]] + [x for d in dem for x in d["anexos"]]
              + [a for c in comentarios for a in c.get("anexos", [])] + [a for e in onb.get("etapas", []) for a in (e.get("anexos") or [])])
    vistos, unicos = set(), []
    for a in anexos:
        if a.get("url") not in vistos:
            vistos.add(a.get("url")); unicos.append(a)
    anexos = unicos
    faltando = []
    if not form.get("encontrado"):
        faltando.append("Formulário de Pré-Onboarding não respondido ou não ligado ao perfil")
    if not any("relat" in clickup.normalizar(x.get("titulo")) and ("comercial" in clickup.normalizar(x.get("titulo")) or "onboarding" in clickup.normalizar(x.get("titulo"))) for x in anexos):
        faltando.append("Relatório Comercial não está anexado no ClickUp (perfil, formulário, onboarding, reunião ou demanda comercial): procurar na pasta '1. Documentos' do Drive ou pedir ao Closer")
    if not perfil.get("instagram"):
        faltando.append("Instagram não preenchido no perfil")
    onb_reuniao = [r for r in reun if (r.get("tipo") or "").lower().startswith("reunião de onboarding") or "onboarding" in r["nome"].lower()]
    if not onb_reuniao:
        faltando.append("Reunião de Onboarding não aparece na lista Reuniões com Clientes")
    print(f"dossiê de {perfil['nome']}: formulário {'ok' if form.get('encontrado') else 'AUSENTE'}, onboarding {onb.get('feitas', 0)}/{onb.get('total', 0)} etapas, "
          f"{len(reun)} reunião(ões), {len(anexos)} anexo(s), {len(faltando)} pendência(s) de material", file=sys.stderr)
    lib.print_json({"ok": True, "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"), "perfil": perfil, "formulario": form,
                    "onboarding": onb, "reunioes": reun, "demandas_comerciais": dem, "anexos": anexos, "comentarios": comentarios,
                    "faltando": faltando})


def cmd_anexo(a):
    """Baixa um anexo do ClickUp (url pública assinada) para a pasta indicada; PDF ganha um .txt ao lado."""
    import subprocess
    os.makedirs(a.pasta, exist_ok=True)
    nome = re.sub(r"[^A-Za-z0-9._-]+", "_", a.url.rsplit("/", 1)[-1].split("?")[0]) or "anexo"
    dest = os.path.join(a.pasta, nome)
    r = subprocess.run(["curl", "-sL", "--max-time", "60", "-o", dest, a.url], capture_output=True)
    if r.returncode != 0 or not os.path.exists(dest) or os.path.getsize(dest) == 0:
        _falha("não consegui baixar o anexo", "abrir a url no navegador e salvar à mão")
    out = {"ok": True, "arquivo": dest, "bytes": os.path.getsize(dest), "texto": None}
    if dest.lower().endswith(".pdf"):
        txt = dest[:-4] + ".txt"
        try:
            subprocess.run(["pdftotext", "-layout", dest, txt], check=True, capture_output=True)
        except Exception:
            try:
                from pypdf import PdfReader
                with open(txt, "w", encoding="utf-8") as f:
                    f.write("\n".join((pg.extract_text() or "") for pg in PdfReader(dest).pages))
            except Exception:
                txt = None
        if txt and os.path.exists(txt):
            out["texto"] = txt
            out["linhas"] = sum(1 for _ in open(txt, encoding="utf-8", errors="replace"))
        else:
            out["aviso"] = "sem pdftotext nem pypdf: ler o PDF direto pela ferramenta de leitura de arquivos"
    lib.print_json(out)


def cmd_proximas(a):
    hoje = date.today()
    limite = hoje + timedelta(days=a.dias)
    ok, ts = clickup.tarefas(LISTA_REUNIOES_ID, include_closed=False)
    if not ok:
        _falha(ts.get("erro"))
    out = []
    for t in ts:
        tipo = (clickup.valor(t, "Tipo de Reunião") or "")
        if not (tipo.lower().startswith("reunião de onboarding") or "onboarding" in t["name"].lower()):
            continue
        ini = t.get("start_date") or t.get("due_date")
        if not ini:
            continue
        d = datetime.fromtimestamp(int(ini) / 1000).date()
        if hoje <= d <= limite:
            rel = clickup.valor(t, "Reunião - Clientes")
            cli = rel[0] if isinstance(rel, list) and rel else {}
            out.append({"id": t["id"], "url": t.get("url"), "nome": t["name"], "status": t["status"]["status"], "inicio": _data(ini, hora=True),
                        "link": clickup.valor(t, "Link Reunião"), "cliente": cli.get("name"), "perfil_id": cli.get("id")})
    out.sort(key=lambda r: r["inicio"])
    print(f"{len(out)} reunião(ões) de onboarding entre {hoje} e {limite}", file=sys.stderr)
    lib.print_json({"ok": True, "hoje": hoje.isoformat(), "ate": limite.isoformat(), "reunioes": out})


def main():
    p = argparse.ArgumentParser(description="Dossiê do cliente novo para a Reunião de Onboarding (só leitura)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("proximas"); s.add_argument("--dias", type=int, default=7); s.set_defaults(fn=cmd_proximas)
    s = sub.add_parser("cliente"); s.add_argument("--cliente", required=True, help="nome, #código ou id da task do perfil"); s.set_defaults(fn=cmd_cliente)
    s = sub.add_parser("anexo"); s.add_argument("--url", required=True); s.add_argument("--pasta", required=True, help="pasta local de destino (scratchpad)"); s.set_defaults(fn=cmd_anexo)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:
        _falha(f"erro interno ({type(e).__name__}): {lib.redigir(e)}")


if __name__ == "__main__":
    main()
