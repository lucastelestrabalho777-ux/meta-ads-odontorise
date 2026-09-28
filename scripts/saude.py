#!/usr/bin/env python3
"""
meta-ads-odontorise: saúde da conta de anúncio.

Quatro sinais, cada um com status ok, atencao ou critico e uma explicação curta:
  1. saldo_pagamento      status da conta, forma de pagamento e dias de saldo (pré-paga)
  2. anuncios_problema    anúncios reprovados (DISAPPROVED) ou com problema (WITH_ISSUES)
  3. gasto_sem_resultado  campanhas ativas gastando sem mensagem iniciada nos últimos 7 dias
                          e custo por mensagem de 7 dias contra os 7 dias anteriores
  4. recencia             dias desde a última alteração feita por uma pessoa no log da conta

Subcomandos:
  conta  --account act_X | --cliente X   [--gasto-minimo 15000]
  todas  [--limite-contas N] [--gasto-minimo 15000]     percorre o cadastro local

Só leitura (GET). JSON no stdout; um bloco humano curto por conta no stderr.
Códigos de saída: 0 análise feita (mesmo com sinal crítico) · 1 conta inacessível,
argumento errado ou erro interno
"""

import argparse
import json
import os
import sys
import time

# Campanhas cujo resultado é mensagem no WhatsApp. Tráfego, alcance, seguidores e leads de
# formulário não entram na regra "gastou e não gerou mensagem".
OBJETIVOS_DE_MENSAGEM = {"OUTCOME_SALES", "OUTCOME_ENGAGEMENT", "MESSAGES", "CONVERSIONS"}
from datetime import datetime, timedelta, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import watchlist  # noqa: E402

# ---------------------------------------------------------------------------
# Limiares e constantes
# ---------------------------------------------------------------------------

JANELA_DIAS = 7                    # tamanho de cada janela comparada (atual e anterior)
DIAS_SALDO_ATENCAO = 5             # pré-paga: menos que isso de saldo = atenção
DIAS_SALDO_CRITICO = 2             # pré-paga: menos que isso de saldo = crítico
GASTO_MINIMO_CENTAVOS = 15000      # R$150 em 7d: a partir daqui, zero mensagem é problema
CUSTO_MSG_ATENCAO_PCT = 30         # custo por mensagem subiu 30% ou mais = atenção
CUSTO_MSG_CRITICO_PCT = 60         # custo por mensagem subiu 60% ou mais = crítico
RECENCIA_ATENCAO_DIAS = 10         # dias sem alteração humana = atenção
RECENCIA_CRITICO_DIAS = 18         # dias sem alteração humana = crítico
LOG_JANELA_DIAS = 45               # quanto do log da conta é lido
LOG_ATOR_AUTOMATICO = "Meta"       # evento com esse trecho em actor_name é do sistema, não de pessoa
ACAO_MENSAGEM = "onsite_conversion.messaging_conversation_started_7d"

PAGINA_LISTA = 100                 # itens por página em /ads
PAGINA_INSIGHTS = 200              # itens por página em /insights
PAGINA_LOG = 500                   # itens por página em /activities
MAX_ANUNCIOS_PROBLEMA = 500        # teto de anúncios com problema listados
MAX_PAGINAS_INSIGHTS = 10          # teto de páginas de insights por campanha
MAX_PAGINAS_LOG = 30               # teto de páginas do log (45 dias de conta grande cabe em ~11)
RATE_LIMIT_ESPERA = 60             # segundos de espera quando a Meta limita chamadas
RATE_LIMIT_TENTATIVAS = 2

TIPO_PAGAMENTO_PREPAGO = 20        # funding_source_details.type do "Saldo disponível"
STATUS_CONTA = {1: "ATIVA", 2: "DESATIVADA", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW", 8: "PENDING_SETTLEMENT",
                9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE", 101: "FECHADA"}
MOTIVO_DESATIVACAO = {1: "política de integridade de anúncios", 2: "revisão de IP", 3: "risco de pagamento",
                      4: "conta cinza encerrada", 5: "revisão AFC", 6: "integridade do negócio",
                      7: "encerramento permanente", 8: "conta de revenda sem uso", 9: "conta sem uso",
                      10: "conta guarda-chuva", 11: "política de integridade da BM", 12: "conta com informação falsa",
                      13: "entidade legal desvinculada", 14: "revisão de conversa", 15: "conta comprometida"}

CAMPOS_CONTA = ("name,currency,account_status,disable_reason,is_prepay_account,balance,amount_spent,"
                "spend_cap,funding_source_details,timezone_name")
CAMPOS_LOG = "event_type,event_time,actor_name,translated_event_type,object_name"

PESO = {"ok": 0, "erro": 1, "atencao": 1, "critico": 2}
ICONE = {"ok": "✅", "atencao": "🟠", "critico": "🔴", "erro": "⚠️"}
SINAIS = (("saldo_pagamento", "saldo"), ("anuncios_problema", "anúncios"),
          ("gasto_sem_resultado", "gasto"), ("recencia", "recência"))


# ---------------------------------------------------------------------------
# Chamadas e utilitários
# ---------------------------------------------------------------------------

def _get(path, params=None):
    """GET com espera curta se a Meta limitar chamadas. Devolve (ok, dado) como lib.graph_get."""
    ok, d = lib.graph_get(path, params=params)
    tentativa = 1
    while not ok and d.get("code") in lib.RATE_LIMIT_CODES and tentativa < RATE_LIMIT_TENTATIVAS:
        print(f"Limite de chamadas: aguardando {RATE_LIMIT_ESPERA}s (tentativa {tentativa} de {RATE_LIMIT_TENTATIVAS})", file=sys.stderr)
        time.sleep(RATE_LIMIT_ESPERA)
        tentativa += 1
        ok, d = lib.graph_get(path, params=params)
    return ok, d


def _coletar(path, params, maximo=None, max_paginas=None, parar_em=None):
    """
    Percorre as páginas de uma listagem pelo cursor `after`. Para dentro do laço ao
    atingir `maximo` itens, `max_paginas` páginas ou quando parar_em(item) for True.
    Devolve dict: ok, itens, erro, paginas, achou (parar_em disparou).
    """
    itens, after, paginas = [], None, 0
    while True:
        p = dict(params)
        if after:
            p["after"] = after
        ok, d = _get(path, p)
        if not ok:
            return {"ok": False, "itens": itens, "erro": d, "paginas": paginas, "achou": False}
        paginas += 1
        for item in d.get("data", []):
            itens.append(item)
            if parar_em and parar_em(item):
                return {"ok": True, "itens": itens, "erro": None, "paginas": paginas, "achou": True}
            if maximo and len(itens) >= maximo:
                return {"ok": True, "itens": itens, "erro": None, "paginas": paginas, "achou": False}
        paging = d.get("paging", {})
        after = paging.get("cursors", {}).get("after")
        if not after or "next" not in paging or (max_paginas and paginas >= max_paginas):
            return {"ok": True, "itens": itens, "erro": None, "paginas": paginas, "achou": False}


def _cent(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _reais(centavos):
    return None if centavos is None else round(centavos / 100, 2)


def _brl(reais):
    """Formata em reais no padrão brasileiro: R$1.234,56."""
    if reais is None:
        return "?"
    s = f"{abs(reais):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if reais < 0 else "") + "R$" + s


def _num(v, casas=1):
    return f"{v:.{casas}f}".replace(".", ",")


def _variacao_pct(antes, depois):
    if not antes or depois is None:
        return None
    return round((depois - antes) / antes * 100, 1)


def _janelas(fuso_nome):
    """Janela atual (últimos 7 dias fechados) e anterior, no fuso da conta."""
    try:
        from zoneinfo import ZoneInfo
        agora = datetime.now(ZoneInfo(fuso_nome)) if fuso_nome else datetime.now().astimezone()
    except Exception:
        agora = datetime.now().astimezone()
    hoje = agora.date()
    return {
        "atual": {"desde": (hoje - timedelta(days=JANELA_DIAS)).isoformat(), "ate": (hoje - timedelta(days=1)).isoformat()},
        "anterior": {"desde": (hoje - timedelta(days=2 * JANELA_DIAS)).isoformat(),
                     "ate": (hoje - timedelta(days=JANELA_DIAS + 1)).isoformat()},
    }


def _time_ranges(janelas):
    return json.dumps([{"since": j["desde"], "until": j["ate"]} for j in (janelas["anterior"], janelas["atual"])])


def _qual_janela(linha, janelas):
    for nome, j in janelas.items():
        if linha.get("date_start") == j["desde"] and linha.get("date_stop") == j["ate"]:
            return nome
    return None


def _gasto(linha):
    try:
        return float(linha.get("spend") or 0)
    except (TypeError, ValueError):
        return 0.0


def _mensagens(linha):
    for a in linha.get("actions") or []:
        if a.get("action_type") == ACAO_MENSAGEM:
            try:
                return int(float(a.get("value") or 0))
            except (TypeError, ValueError):
                return 0
    return 0


def _janela_vazia():
    return {"gasto": 0.0, "mensagens": 0, "custo_por_mensagem": None}


def _fechar_janela(j):
    j["gasto"] = round(j["gasto"], 2)
    j["custo_por_mensagem"] = round(j["gasto"] / j["mensagens"], 2) if j["mensagens"] else None
    return j


# ---------------------------------------------------------------------------
# Sinal 1: saldo e pagamento
# ---------------------------------------------------------------------------

def sinal_saldo(conta, gasto_7d):
    status_num = conta.get("account_status")
    status_txt = STATUS_CONTA.get(status_num, f"status {status_num}")
    fonte = conta.get("funding_source_details") or {}
    prepaga = bool(conta.get("is_prepay_account")) or fonte.get("type") == TIPO_PAGAMENTO_PREPAGO
    gasto_total = _cent(conta.get("amount_spent"))
    teto = _cent(conta.get("spend_cap"))
    pendente = _cent(conta.get("balance"))
    media_dia = round(gasto_7d / JANELA_DIAS, 2)
    out = {"status_conta": status_txt, "pre_paga": prepaga,
           "pagamento": {"forma": fonte.get("display_string"), "tipo": fonte.get("type")},
           "valor_pendente_cobranca": _reais(pendente), "gasto_medio_dia_7d": media_dia}

    if status_num != 1:
        motivo = MOTIVO_DESATIVACAO.get(conta.get("disable_reason"))
        exp = f"conta {status_txt}" + (f" ({motivo})" if motivo else "") + ": nada veicula até regularizar"
        return {"status": "critico", "explicacao": exp, **out}

    restante = teto - gasto_total if (teto and gasto_total is not None) else None

    if prepaga:
        if restante is None:
            return {"status": "atencao", "explicacao": "conta pré-paga sem spend_cap ou amount_spent legíveis: conferir o saldo no Gerenciador", **out}
        out["saldo_restante"] = _reais(restante)
        if restante <= 0:
            return {"status": "critico", "explicacao": "saldo zerado: a conta parou de veicular, precisa de recarga", **out}
        if media_dia <= 0:
            out["dias_de_saldo"] = None
            return {"status": "ok", "explicacao": f"saldo de {_brl(_reais(restante))} e sem gasto nos últimos {JANELA_DIAS} dias", **out}
        dias = round(_reais(restante) / media_dia, 1)
        out["dias_de_saldo"] = dias
        exp = f"saldo de {_brl(_reais(restante))} dura ~{_num(dias)} dia(s) no ritmo de {_brl(media_dia)}/dia"
        if dias < DIAS_SALDO_CRITICO:
            return {"status": "critico", "explicacao": exp + ": recarregar hoje", **out}
        if dias < DIAS_SALDO_ATENCAO:
            return {"status": "atencao", "explicacao": exp + ": programar a recarga", **out}
        return {"status": "ok", "explicacao": exp, **out}

    # Pós-paga (cartão, boleto): não há saldo a esgotar, só o limite de gasto da conta, se houver.
    if restante is not None:
        out["limite_gasto_restante"] = _reais(restante)
        if restante <= 0:
            return {"status": "critico", "explicacao": "limite de gasto da conta atingido: a conta parou de veicular", **out}
        if media_dia > 0:
            dias = round(_reais(restante) / media_dia, 1)
            out["dias_ate_limite"] = dias
            exp = f"limite de gasto da conta acaba em ~{_num(dias)} dia(s) ({_brl(_reais(restante))} restantes)"
            if dias < DIAS_SALDO_CRITICO:
                return {"status": "critico", "explicacao": exp, **out}
            if dias < DIAS_SALDO_ATENCAO:
                return {"status": "atencao", "explicacao": exp, **out}
    forma = fonte.get("display_string") or "forma de pagamento não informada"
    return {"status": "ok", "explicacao": f"conta ativa, {forma}, {_brl(_reais(pendente))} pendente de cobrança", **out}


# ---------------------------------------------------------------------------
# Sinal 2: anúncios reprovados ou com problema
# ---------------------------------------------------------------------------

def sinal_anuncios(acct):
    params = {"fields": "id,name,effective_status,issues_info,campaign{name,effective_status}",
              "effective_status": json.dumps(["DISAPPROVED", "WITH_ISSUES"]), "limit": PAGINA_LISTA}
    r = _coletar(f"{acct}/ads", params, maximo=MAX_ANUNCIOS_PROBLEMA)
    if not r["ok"]:
        return {"status": "erro", "explicacao": f"não consegui listar os anúncios ({r['erro'].get('erro')})"}
    reprovados, com_problema = [], []
    for ad in r["itens"]:
        issues = ad.get("issues_info") or []
        camp = ad.get("campaign") or {}
        item = {"id": ad.get("id"), "nome": ad.get("name"), "status": ad.get("effective_status"),
                "campanha": camp.get("name"), "campanha_status": camp.get("effective_status"),
                "motivo": issues[0].get("error_summary") if issues else None}
        (reprovados if item["status"] == "DISAPPROVED" else com_problema).append(item)
    todos = reprovados + com_problema
    em_ativas = sum(1 for a in todos if a["campanha_status"] == "ACTIVE")
    out = {"reprovados": len(reprovados), "com_problema": len(com_problema), "em_campanha_ativa": em_ativas,
           "lista_truncada": len(r["itens"]) >= MAX_ANUNCIOS_PROBLEMA, "anuncios": todos}
    if reprovados:
        exp = f"{len(reprovados)} anúncio(s) reprovado(s)" + (f" e {len(com_problema)} com problema" if com_problema else "")
        return {"status": "critico", "explicacao": exp + f" ({em_ativas} em campanha ativa)", **out}
    if com_problema:
        return {"status": "atencao", "explicacao": f"{len(com_problema)} anúncio(s) com problema ({em_ativas} em campanha ativa)", **out}
    return {"status": "ok", "explicacao": "nenhum anúncio reprovado ou com problema", **out}


# ---------------------------------------------------------------------------
# Sinal 3: gasto sem resultado
# ---------------------------------------------------------------------------

def insights_conta(acct, janelas):
    """Gasto e mensagens iniciadas da conta inteira nas duas janelas. Devolve (erro_ou_None, atual, anterior)."""
    ok, d = _get(f"{acct}/insights", {"fields": "spend,actions", "time_ranges": _time_ranges(janelas)})
    atual, anterior = _janela_vazia(), _janela_vazia()
    if not ok:
        return d.get("erro"), atual, anterior
    for linha in d.get("data", []):
        alvo = {"atual": atual, "anterior": anterior}.get(_qual_janela(linha, janelas))
        if alvo is not None:
            alvo["gasto"] += _gasto(linha)
            alvo["mensagens"] += _mensagens(linha)
    return None, _fechar_janela(atual), _fechar_janela(anterior)


def sinal_gasto(acct, janelas, atual, anterior, erro_conta, gasto_minimo):
    if erro_conta:
        return {"status": "erro", "explicacao": f"não consegui ler os insights da conta ({erro_conta})"}
    params = {"level": "campaign", "fields": "campaign_id,campaign_name,objective,spend,actions",
              "time_ranges": _time_ranges(janelas), "limit": PAGINA_INSIGHTS,
              "filtering": json.dumps([{"field": "campaign.effective_status", "operator": "IN", "value": ["ACTIVE"]}])}
    r = _coletar(f"{acct}/insights", params, max_paginas=MAX_PAGINAS_INSIGHTS)
    if not r["ok"]:
        return {"status": "erro", "explicacao": f"não consegui ler os insights por campanha ({r['erro'].get('erro')})"}

    por_campanha = {}
    for linha in r["itens"]:
        nome_janela = _qual_janela(linha, janelas)
        if not nome_janela:
            continue
        c = por_campanha.setdefault(linha.get("campaign_id"), {
            "id": linha.get("campaign_id"), "nome": linha.get("campaign_name"), "objetivo": linha.get("objective"),
            "mede_mensagem": (linha.get("objective") or "") in OBJETIVOS_DE_MENSAGEM,
            "atual": _janela_vazia(), "anterior": _janela_vazia()})
        c[nome_janela]["gasto"] += _gasto(linha)
        c[nome_janela]["mensagens"] += _mensagens(linha)

    campanhas, sem_resultado = [], []
    for c in por_campanha.values():
        _fechar_janela(c["atual"])
        _fechar_janela(c["anterior"])
        c["variacao_custo_pct"] = _variacao_pct(c["anterior"]["custo_por_mensagem"], c["atual"]["custo_por_mensagem"])
        campanhas.append(c)
        if c["mede_mensagem"] and c["atual"]["gasto"] * 100 > gasto_minimo and c["atual"]["mensagens"] == 0:
            sem_resultado.append(c)
    campanhas.sort(key=lambda c: -c["atual"]["gasto"])

    variacao = _variacao_pct(anterior["custo_por_mensagem"], atual["custo_por_mensagem"])
    gasto_conversa = round(sum(c["atual"]["gasto"] for c in campanhas if c["mede_mensagem"]), 2)
    outro_objetivo = [c["nome"] for c in campanhas if not c["mede_mensagem"]]
    out = {"gasto_minimo": _reais(gasto_minimo), "conta_7d": atual, "conta_7d_anteriores": anterior,
           "gasto_7d_campanhas_de_mensagem": gasto_conversa, "campanhas_outro_objetivo": outro_objetivo,
           "variacao_custo_mensagem_pct": variacao, "campanhas_ativas": len(campanhas),
           "campanhas_sem_resultado": [{"id": c["id"], "nome": c["nome"], "gasto_7d": c["atual"]["gasto"]} for c in sem_resultado],
           "campanhas": campanhas}

    if sem_resultado:
        total = round(sum(c["atual"]["gasto"] for c in sem_resultado), 2)
        return {"status": "critico", "explicacao": f"{len(sem_resultado)} campanha(s) ativa(s) gastaram {_brl(total)} em {JANELA_DIAS} dias sem nenhuma mensagem iniciada", **out}
    if gasto_conversa * 100 > gasto_minimo and atual["mensagens"] == 0:
        return {"status": "critico", "explicacao": f"{_brl(gasto_conversa)} gastos em {JANELA_DIAS} dias em campanhas de mensagem sem nenhuma mensagem iniciada", **out}
    if atual["gasto"] <= 0:
        return {"status": "atencao", "explicacao": f"sem gasto nos últimos {JANELA_DIAS} dias: conferir se é intencional", **out}
    if atual["mensagens"] == 0:
        return {"status": "ok", "explicacao": f"{_brl(atual['gasto'])} gastos em {JANELA_DIAS} dias, abaixo do mínimo de {_brl(_reais(gasto_minimo))}, sem mensagem iniciada", **out}
    base = f"{atual['mensagens']} mensagem(ns) a {_brl(atual['custo_por_mensagem'])}"
    if variacao is None:
        return {"status": "ok", "explicacao": base + f" (sem base de comparação nos {JANELA_DIAS} dias anteriores)", **out}
    comp = f" (antes {_brl(anterior['custo_por_mensagem'])}, {'+' if variacao >= 0 else ''}{_num(variacao, 0)}%)"
    if variacao >= CUSTO_MSG_CRITICO_PCT:
        return {"status": "critico", "explicacao": f"custo por mensagem subiu {_num(variacao, 0)}%: " + base + comp, **out}
    if variacao >= CUSTO_MSG_ATENCAO_PCT:
        return {"status": "atencao", "explicacao": f"custo por mensagem subiu {_num(variacao, 0)}%: " + base + comp, **out}
    return {"status": "ok", "explicacao": base + comp, **out}


# ---------------------------------------------------------------------------
# Sinal 4: recência da última alteração humana
# ---------------------------------------------------------------------------

def _e_humano(evento):
    return LOG_ATOR_AUTOMATICO not in (evento.get("actor_name") or "")


def sinal_recencia(acct):
    desde = int(time.time()) - LOG_JANELA_DIAS * 86400
    params = {"fields": CAMPOS_LOG, "since": desde, "limit": PAGINA_LOG}
    r = _coletar(f"{acct}/activities", params, max_paginas=MAX_PAGINAS_LOG, parar_em=_e_humano)
    if not r["ok"]:
        return {"status": "erro", "explicacao": f"não consegui ler o log da conta ({r['erro'].get('erro')})"}
    out = {"janela_dias": LOG_JANELA_DIAS, "eventos_lidos": len(r["itens"]), "paginas_lidas": r["paginas"]}
    if not r["achou"]:
        exp = f"nenhuma alteração humana nos últimos {LOG_JANELA_DIAS} dias do log"
        if r["paginas"] >= MAX_PAGINAS_LOG:
            exp += " (leitura parou no teto de páginas)"
        return {"status": "critico", "explicacao": exp, "dias_sem_alteracao": None, **out}

    ev = r["itens"][-1]
    try:
        quando = datetime.strptime(ev.get("event_time", ""), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return {"status": "erro", "explicacao": "data do último evento humano em formato inesperado", **out}
    dias = int((datetime.now(timezone.utc) - quando).total_seconds() // 86400)
    o_que = ev.get("translated_event_type") or ev.get("event_type")
    out.update({"dias_sem_alteracao": dias,
                "ultima_alteracao": {"quando": quando.astimezone().strftime("%d/%m/%Y %H:%M"), "quem": ev.get("actor_name"),
                                     "o_que": o_que, "objeto": ev.get("object_name")}})
    exp = f"última alteração humana há {dias} dia(s) ({ev.get('actor_name')}: {o_que})"
    if dias >= RECENCIA_CRITICO_DIAS:
        return {"status": "critico", "explicacao": exp + ": conta abandonada, revisar hoje", **out}
    if dias >= RECENCIA_ATENCAO_DIAS:
        return {"status": "atencao", "explicacao": exp + ": agendar uma revisão", **out}
    return {"status": "ok", "explicacao": exp, **out}


# ---------------------------------------------------------------------------
# Análise de uma conta e apresentação
# ---------------------------------------------------------------------------

def _resumo(sinais):
    pior = max(sinais.values(), key=lambda s: PESO.get(s["status"], 1))["status"]
    return {"status": pior,
            "critico": [k for k, s in sinais.items() if s["status"] == "critico"],
            "atencao": [k for k, s in sinais.items() if s["status"] == "atencao"],
            "erro": [k for k, s in sinais.items() if s["status"] == "erro"]}


def analisar_conta(acct, gasto_minimo, cliente=None):
    ok, conta = _get(acct, {"fields": CAMPOS_CONTA})
    if not ok:
        r = {"ok": False, "act_id": acct, "cliente": cliente, "erro": conta.get("erro"), "code": conta.get("code")}
        if conta.get("code") in lib.RATE_LIMIT_CODES:
            r["acao"] = "limite de chamadas: aguardar 60 segundos e rodar de novo"
        elif conta.get("code") in (200, 10, 190):
            r["acao"] = "conferir se a conta está atribuída a você na BM e se o token está válido (setup.py)"
        return r
    janelas = _janelas(conta.get("timezone_name"))
    erro_ins, atual, anterior = insights_conta(acct, janelas)
    sinais = {
        "saldo_pagamento": sinal_saldo(conta, atual["gasto"]),
        "anuncios_problema": sinal_anuncios(acct),
        "gasto_sem_resultado": sinal_gasto(acct, janelas, atual, anterior, erro_ins, gasto_minimo),
        "recencia": sinal_recencia(acct),
    }
    return {"ok": True, "cliente": cliente,
            "conta": {"act_id": conta.get("id", acct), "nome": conta.get("name"), "moeda": conta.get("currency"),
                      "fuso": conta.get("timezone_name")},
            "janelas": janelas, "resumo": _resumo(sinais), "sinais": sinais}


def bloco_humano(r):
    """Bloco curto no stderr: uma linha por sinal."""
    if not r.get("ok"):
        print(f"{ICONE['erro']} {r.get('cliente') or r['act_id']} ({r['act_id']}): {r.get('erro')}", file=sys.stderr)
        return
    st = r["resumo"]["status"]
    titulo = r["conta"]["nome"] or r["conta"]["act_id"]
    if r.get("cliente") and r["cliente"] != titulo:
        titulo = f"{r['cliente']} · {titulo}"
    print(f"{ICONE[st]} {titulo} ({r['conta']['act_id']}) · {st.upper()}", file=sys.stderr)
    for chave, rotulo in SINAIS:
        s = r["sinais"][chave]
        print(f"   {ICONE[s['status']]} {rotulo}: {s['explicacao']}", file=sys.stderr)


def _cliente_do_cadastro(acct):
    """Nome do cliente no cadastro local para esta conta, se houver."""
    try:
        c = watchlist.resolver(watchlist.carregar(), acct)
        return c.get("nome") if c else None
    except (ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_conta(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    r = analisar_conta(acct, a.gasto_minimo, _cliente_do_cadastro(acct))
    bloco_humano(r)
    lib.print_json(r)
    sys.exit(0 if r.get("ok") else 1)


@lib.handle_fb_error
def cmd_todas(a):
    lib.init_api(quiet=True)
    dados = watchlist.carregar()
    com_conta = [c for c in dados.get("clientes", []) if c.get("act_id")]
    sem_conta = [c.get("nome") for c in dados.get("clientes", []) if not c.get("act_id")]
    if not com_conta:
        lib.print_json({"ok": False, "erro": "nenhum cliente com conta Meta no cadastro local",
                        "cadastro": watchlist.CADASTRO_PATH, "sem_conta_meta": sem_conta,
                        "acao": "cadastrar com clientes.py cadastrar --nome <nome> e definir a conta com definir-conta"})
        sys.exit(1)

    resultados = []
    for c in com_conta:
        if a.limite_contas and len(resultados) >= a.limite_contas:
            break
        r = analisar_conta(c["act_id"], a.gasto_minimo, c.get("nome"))
        bloco_humano(r)
        resultados.append(r)

    def chave(r):
        if not r.get("ok"):
            return (-PESO["erro"], 0, 0)
        return (-PESO[r["resumo"]["status"]], -len(r["resumo"]["critico"]), -len(r["resumo"]["atencao"]))
    resultados.sort(key=chave)

    contagem = {"critico": 0, "atencao": 0, "ok": 0, "erro": 0}
    for r in resultados:
        contagem[r["resumo"]["status"] if r.get("ok") else "erro"] += 1
    lib.print_json({"ok": True, "quantidade": len(resultados), "no_cadastro_com_conta": len(com_conta),
                    "sem_conta_meta": sem_conta, "cadastro": watchlist.CADASTRO_PATH,
                    "contagem": contagem, "contas": resultados})


def _add_gasto_minimo(parser):
    parser.add_argument("--gasto-minimo", type=int, default=GASTO_MINIMO_CENTAVOS,
                        help=f"gasto em centavos nos últimos {JANELA_DIAS} dias a partir do qual zero mensagem vira problema (padrão {GASTO_MINIMO_CENTAVOS} = R$150)")


def main():
    p = argparse.ArgumentParser(description="Saúde de contas de anúncio em 4 sinais (só leitura)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("conta", help="uma conta: --account act_X ou --cliente <nome, #código ou slug>")
    lib.add_target_args(s)
    _add_gasto_minimo(s)
    s.set_defaults(fn=cmd_conta)
    s = sub.add_parser("todas", help="todas as contas do cadastro local (só clientes com conta Meta)")
    s.add_argument("--limite-contas", type=int, default=None, help="Analisar no máximo N contas (padrão: todas)")
    _add_gasto_minimo(s)
    s.set_defaults(fn=cmd_todas)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:  # nunca imprimir str(e): pode carregar URL com token
        print(json.dumps({"ok": False, "erro": f"erro interno ({type(e).__name__})"}, ensure_ascii=False, indent=2))
        sys.exit(2)


if __name__ == "__main__":
    main()
