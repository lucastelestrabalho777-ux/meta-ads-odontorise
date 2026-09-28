#!/usr/bin/env python3
"""
meta-ads-odontorise: leitura de resultados (insights) das contas de anúncio.

Só leitura na Meta (GET). Métrica principal da casa: mensagens iniciadas no
WhatsApp (action_type onsite_conversion.messaging_conversation_started_7d) e o
custo por mensagem. CPL e lead de formulário nunca são a métrica principal.

Subcomandos:
  account          --account act_X | --cliente X       insights da conta (padrão: last_7d)
  campaign         --id ID                              insights de uma campanha
  adset            --id ID                              insights de um conjunto
  ad               --id ID                              insights de um anúncio
  resultado        --account | --cliente [--level campaign|adset|ad] [--date-preset | --since/--until] [--limit 50]
                   gasto, mensagens iniciadas e custo por mensagem por objeto, ordenado por gasto, com totais
  comparar-janelas --account | --cliente [--level ad|adset|campaign] [--limit 50] [--so-ativos]
                   30, 14 e 7 dias lado a lado por objeto: pré-requisito para pausar qualquer coisa

Saída sempre em JSON no stdout; mensagens humanas no stderr.
Códigos de saída: 0 ok · 2 data ou limite inválidos · 1 demais erros (Meta, ambiente, JSON de argumento, conta ausente)

Molde: skill meta-ads-ratos (insights.py). Adaptações: --account/--cliente do cadastro
local, last_7d como padrão, campos padrão da casa, atribuição unificada só com flag,
--raw, --limit valendo dentro da paginação e os subcomandos resultado e comparar-janelas.
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib.pagination import collect_cursor  # noqa: E402

# Ação que conta como resultado nas campanhas de conversa no WhatsApp.
ACAO_MENSAGEM = "onsite_conversion.messaging_conversation_started_7d"

# Campos padrão dos subcomandos genéricos (a Meta ignora os nomes que não valem no nível pedido).
CAMPOS_PADRAO = [
    "campaign_name", "adset_name", "ad_name", "objective",
    "spend", "impressions", "reach", "frequency", "cpm", "ctr", "clicks", "actions",
]

# Identificação de cada objeto conforme o nível.
CAMPOS_POR_NIVEL = {
    "campaign": ["campaign_id", "campaign_name", "objective"],
    "adset": ["campaign_id", "campaign_name", "adset_id", "adset_name", "objective"],
    "ad": ["campaign_id", "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name", "objective"],
}

# Métricas lidas pelos subcomandos resultado e comparar-janelas.
CAMPOS_METRICA = ["spend", "impressions", "reach", "frequency", "cpm", "ctr", "clicks", "actions"]

DATE_PRESETS = [
    "today", "yesterday", "this_month", "last_month", "this_quarter",
    "last_3d", "last_7d", "last_14d", "last_28d", "last_30d", "last_90d", "maximum",
]

# Janelas do cruzamento antes de pausar, em dias.
JANELAS = (30, 14, 7)

# Tamanho máximo de página aceito pela Meta nos insights.
PAGINA_MAXIMA = 500

# Ids por chamada ao completar uma janela truncada (filtro <nivel>.id IN [...]).
LOTE_IDS = 50


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _sair(msg, code=2):
    """Erro de uso: mensagem no stderr e saída com o código informado."""
    lib.print_error(msg)
    sys.exit(code)


def _sdk():
    """Classes do SDK, importadas só quando a biblioteca já foi conferida."""
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.campaign import Campaign
    return {"account": AdAccount, "campaign": Campaign, "adset": AdSet, "ad": Ad}


def _num(valor, casas=2):
    """Texto numérico da Meta vira número arredondado; None se vazio ou inválido."""
    if valor is None or valor == "":
        return None
    try:
        f = float(valor)
    except (TypeError, ValueError):
        return None
    return int(round(f)) if casas == 0 else round(f, casas)


def _mensagens(actions):
    """Soma das mensagens iniciadas dentro da lista de ações."""
    total = 0.0
    for acao in actions or []:
        if isinstance(acao, dict) and acao.get("action_type") == ACAO_MENSAGEM:
            total += _num(acao.get("value"), 4) or 0
    return int(round(total))


def _custo(gasto, quantidade):
    """Custo por unidade; None quando não houve resultado (nunca divide por zero)."""
    if not quantidade:
        return None
    return round((gasto or 0) / quantidade, 2)


def _data(texto, nome):
    """Valida YYYY-MM-DD e devolve a data em texto normalizado."""
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        _sair(f"{nome} precisa estar no formato YYYY-MM-DD (recebi '{texto}')")


def _faixa(since, until):
    """time_range a partir de --since/--until; --until vazio vira hoje."""
    if not since:
        _sair("informe --since junto com --until (formato YYYY-MM-DD)")
    ini = _data(since, "--since")
    fim = _data(until, "--until") if until else date.today().isoformat()
    if ini > fim:
        _sair("--since não pode ser depois de --until")
    return {"since": ini, "until": fim}


def _limite(valor, nome="--limit"):
    """Limite obrigatório e positivo nos subcomandos que listam objetos."""
    if valor is None or valor <= 0:
        _sair(f"{nome} precisa ser maior que zero")
    return valor


def _pagina(limite):
    """Tamanho da página pedido à Meta: o próprio limite, até o máximo aceito."""
    if not limite:
        return 100
    return min(limite, PAGINA_MAXIMA)


def _filtro_ativos(nivel):
    """Filtro de insights que deixa só objetos em veiculação no nível pedido."""
    return {"field": f"{nivel}.effective_status", "operator": "IN", "value": ["ACTIVE"]}


def _periodo_lido(rows, params):
    """Período efetivo: datas das linhas quando existem, senão o que foi pedido."""
    out = {}
    if "date_preset" in params:
        out["date_preset"] = params["date_preset"]
    if rows and isinstance(rows[0], dict):
        out["since"] = rows[0].get("date_start")
        out["until"] = rows[0].get("date_stop")
    elif "time_range" in params:
        out.update(params["time_range"])
    return out


# ---------------------------------------------------------------------------
# Camada de acesso dos subcomandos genéricos
# ---------------------------------------------------------------------------

def _add_insights_args(p):
    """Argumentos comuns de insights (tempo, segmentação, atribuição, filtro, saída)."""
    lib.add_fields_arg(p)
    p.add_argument("--date-preset", default="last_7d", choices=DATE_PRESETS,
                   help="Período relativo (padrão: last_7d)")
    p.add_argument("--time-range", help='JSON: {"since":"2026-09-01","until":"2026-09-30"} (tem prioridade sobre --date-preset)')
    p.add_argument("--time-ranges", help='JSON com vários períodos para comparar: [{"since":...,"until":...},{...}]')
    p.add_argument("--since", help="Data inicial YYYY-MM-DD (vira time_range; --until vazio = hoje)")
    p.add_argument("--until", help="Data final YYYY-MM-DD (exige --since)")
    p.add_argument("--time-increment", default="all_days",
                   help="Granularidade: 1 a 90 (dias), monthly ou all_days (padrão). Valor numérico exige --limit maior que zero")
    p.add_argument("--breakdowns",
                   help="Segmentar por: age,gender,country,region,publisher_platform,platform_position,device_platform,impression_device")
    p.add_argument("--level", choices=["account", "campaign", "adset", "ad"], help="Nível de agregação")
    p.add_argument("--action-breakdowns", help="Segmentar ações: action_type,action_device,action_destination")
    p.add_argument("--action-report-time", choices=["impression", "conversion", "mixed"],
                   help="Quando a ação conta: impression, conversion ou mixed")
    p.add_argument("--action-attribution-windows",
                   help="Janelas de atribuição separadas por vírgula: 1d_view,7d_click,28d_click,dda,default")
    p.add_argument("--use-account-attribution", action="store_true",
                   help="Usar a atribuição configurada na conta")
    p.add_argument("--use-unified-attribution", action="store_true",
                   help="Usar atribuição unificada (padrão: desligada)")
    p.add_argument("--filtering", help='JSON: [{"field":"spend","operator":"GREATER_THAN","value":50}]')
    p.add_argument("--sort", help="Ordenação: spend_descending, impressions_ascending etc.")
    p.add_argument("--limit", type=int, default=25,
                   help="Máximo de linhas devolvidas (padrão: 25; 0 = todas, exceto com --time-increment numérico)")
    p.add_argument("--raw", action="store_true",
                   help="Resposta da Meta como veio: ações redundantes mantidas e números como texto")


def _build_insights_params(args):
    """
    Monta os parâmetros da chamada. Prioridade de tempo:
    --time-ranges > --time-range > --since/--until > --date-preset.
    """
    params = {}
    time_ranges = getattr(args, "time_ranges", None)
    time_range = getattr(args, "time_range", None)
    since = getattr(args, "since", None)
    until = getattr(args, "until", None)
    if time_ranges:
        params["time_ranges"] = lib.parse_json_arg(time_ranges, "time-ranges")
    elif time_range:
        params["time_range"] = lib.parse_json_arg(time_range, "time-range")
    elif since or until:
        params["time_range"] = _faixa(since, until)
    else:
        params["date_preset"] = args.date_preset

    incremento = getattr(args, "time_increment", None)
    if incremento:
        if str(incremento).isdigit() and not args.limit:
            _sair("--time-increment numérico multiplica as linhas por dia; informe --limit maior que zero")
        params["time_increment"] = incremento

    if args.breakdowns:
        params["breakdowns"] = [b.strip() for b in args.breakdowns.split(",") if b.strip()]
    if args.level:
        params["level"] = args.level
    if args.action_breakdowns:
        params["action_breakdowns"] = [b.strip() for b in args.action_breakdowns.split(",") if b.strip()]

    if getattr(args, "action_report_time", None):
        params["action_report_time"] = args.action_report_time
    if getattr(args, "action_attribution_windows", None):
        params["action_attribution_windows"] = [w.strip() for w in args.action_attribution_windows.split(",") if w.strip()]
    if getattr(args, "use_account_attribution", False):
        params["use_account_attribution_setting"] = True
    if getattr(args, "use_unified_attribution", False):
        params["use_unified_attribution_setting"] = True

    if args.filtering:
        params["filtering"] = lib.parse_json_arg(args.filtering, "filtering")
    if args.sort:
        params["sort"] = [args.sort]

    if args.limit is not None and args.limit < 0:
        _sair("--limit não pode ser negativo")
    params["limit"] = _pagina(args.limit)
    return params


def _campos(args):
    """Campos pedidos em --fields ou os padrão da casa."""
    escolhidos = lib.parse_fields(getattr(args, "fields", None))
    return escolhidos or list(CAMPOS_PADRAO)


# ---------------------------------------------------------------------------
# Compactação (modo padrão) e formatação numérica
# ---------------------------------------------------------------------------

# A Meta devolve a mesma ação com vários prefixos; fica só a forma canônica.
_PREFIXOS_REDUNDANTES = (
    "omni_", "onsite_web_app_", "onsite_web_", "onsite_app_",
    "web_app_in_store_", "offsite_conversion.fb_pixel_",
)
_CAMPOS_ACAO = ("actions", "cost_per_action_type", "action_values", "conversions", "cost_per_conversion")
_CAMPOS_2_CASAS = (
    "spend", "cpc", "cpm", "cpp", "ctr", "frequency", "cost_per_inline_link_click",
    "cost_per_unique_click", "inline_link_click_ctr", "unique_ctr", "social_spend",
)
_CAMPOS_INTEIROS = ("impressions", "reach", "clicks", "unique_clicks", "inline_link_clicks")
# Campos de orçamento vêm em centavos quando aparecem.
_CAMPOS_CENTAVOS = ("daily_budget", "lifetime_budget", "budget_remaining", "spend_cap", "amount_spent", "balance")


def _acao_redundante(action_type):
    """Ação de mensagem nunca é descartada; as demais seguem a lista de prefixos."""
    tipo = str(action_type or "")
    if "messaging" in tipo:
        return False
    return any(tipo.startswith(p) for p in _PREFIXOS_REDUNDANTES)


def _compactar(rows):
    """Remove ações redundantes e converte texto numérico em número."""
    for row in rows:
        if not isinstance(row, dict):
            continue
        for campo in _CAMPOS_ACAO:
            acoes = row.get(campo)
            if not isinstance(acoes, list):
                continue
            limpas = []
            for acao in acoes:
                if not isinstance(acao, dict) or _acao_redundante(acao.get("action_type")):
                    continue
                acao = dict(acao)
                if "value" in acao:
                    v = _num(acao["value"], 4)
                    acao["value"] = int(v) if v is not None and float(v).is_integer() else v
                limpas.append(acao)
            row[campo] = limpas
        for campo in _CAMPOS_2_CASAS:
            if campo in row:
                row[campo] = _num(row[campo], 2)
        for campo in _CAMPOS_INTEIROS:
            if campo in row:
                row[campo] = _num(row[campo], 0)
        for campo in _CAMPOS_CENTAVOS:
            if campo in row and _num(row[campo]) is not None:
                row[campo] = round(_num(row[campo]) / 100, 2)
    return rows


# ---------------------------------------------------------------------------
# Leitura da casa: identificação e métricas de cada objeto
# ---------------------------------------------------------------------------

def _identidade(row, nivel):
    """Id, nome e hierarquia do objeto conforme o nível."""
    out = {"id": row.get(f"{nivel}_id"), "nome": row.get(f"{nivel}_name")}
    if nivel in ("adset", "ad"):
        out["campanha"] = row.get("campaign_name")
    if nivel == "ad":
        out["conjunto"] = row.get("adset_name")
    out["objetivo"] = row.get("objective")
    return out


def _metricas(row):
    """Métricas da casa a partir de uma linha de insights (None = linha ausente)."""
    row = row or {}
    gasto = _num(row.get("spend"), 2) or 0.0
    msgs = _mensagens(row.get("actions"))
    return {
        "gasto": gasto,
        "mensagens_iniciadas": msgs,
        "custo_por_mensagem": _custo(gasto, msgs),
        "ctr": _num(row.get("ctr"), 2),
        "cpm": _num(row.get("cpm"), 2),
        "alcance": _num(row.get("reach"), 0),
        "impressoes": _num(row.get("impressions"), 0) or 0,
        "frequencia": _num(row.get("frequency"), 2),
        "cliques": _num(row.get("clicks"), 0) or 0,
    }


def _totais(linhas):
    """Soma das métricas aditivas; ctr e cpm recalculados. Alcance não soma entre objetos."""
    gasto = round(sum(l.get("gasto") or 0 for l in linhas), 2)
    msgs = sum(l.get("mensagens_iniciadas") or 0 for l in linhas)
    imp = sum(l.get("impressoes") or 0 for l in linhas)
    cli = sum(l.get("cliques") or 0 for l in linhas)
    return {
        "objetos": len(linhas),
        "gasto": gasto,
        "mensagens_iniciadas": msgs,
        "custo_por_mensagem": _custo(gasto, msgs),
        "impressoes": imp,
        "cliques": cli,
        "ctr": round(cli / imp * 100, 2) if imp else None,
        "cpm": round(gasto / imp * 1000, 2) if imp else None,
    }


def _ler_nivel(acct, nivel, params, limite):
    """Uma chamada de insights na conta, com limite valendo dentro da paginação."""
    AdAccount = _sdk()["account"]
    fields = CAMPOS_POR_NIVEL[nivel] + CAMPOS_METRICA
    cursor = lib.retry_call(lambda: AdAccount(acct).get_insights(fields=fields, params=params))
    return collect_cursor(cursor, limite)


# ---------------------------------------------------------------------------
# Subcomandos genéricos
# ---------------------------------------------------------------------------

def _rodar_generico(args, objeto):
    """Executa get_insights no objeto do SDK e imprime as linhas (compactas ou cruas)."""
    fields = _campos(args)
    params = _build_insights_params(args)
    cursor = lib.retry_call(lambda: objeto.get_insights(fields=fields, params=params))
    rows = collect_cursor(cursor, args.limit or None)
    lib.print_json(rows if args.raw else _compactar(rows))


@lib.handle_fb_error
def cmd_account(args):
    """Insights da conta."""
    lib.init_api(quiet=True)
    acct = lib.resolve_target(args)
    _rodar_generico(args, _sdk()["account"](acct))


@lib.handle_fb_error
def cmd_campaign(args):
    """Insights de uma campanha."""
    lib.init_api(quiet=True)
    _rodar_generico(args, _sdk()["campaign"](args.id))


@lib.handle_fb_error
def cmd_adset(args):
    """Insights de um conjunto."""
    lib.init_api(quiet=True)
    _rodar_generico(args, _sdk()["adset"](args.id))


@lib.handle_fb_error
def cmd_ad(args):
    """Insights de um anúncio."""
    lib.init_api(quiet=True)
    _rodar_generico(args, _sdk()["ad"](args.id))


# ---------------------------------------------------------------------------
# resultado: gasto, mensagens e custo por mensagem por objeto
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_resultado(args):
    """Resultado por objeto no período, ordenado por gasto, com totais."""
    lib.init_api(quiet=True)
    acct = lib.resolve_target(args)
    limite = _limite(args.limit)
    params = {"level": args.level, "sort": ["spend_descending"], "limit": _pagina(limite)}
    if args.since or args.until:
        params["time_range"] = _faixa(args.since, args.until)
    else:
        params["date_preset"] = args.date_preset
    if args.so_ativos:
        params["filtering"] = [_filtro_ativos(args.level)]

    rows = _ler_nivel(acct, args.level, params, limite)
    objetos = [{**_identidade(r, args.level), **_metricas(r)} for r in rows]
    out = {
        "conta": acct,
        "nivel": args.level,
        "so_ativos": bool(args.so_ativos),
        "periodo": _periodo_lido(rows, params),
        "metrica_principal": f"mensagens_iniciadas = {ACAO_MENSAGEM}",
        "quantidade": len(objetos),
        "objetos": objetos,
        "totais": _totais(objetos),
    }
    if len(rows) >= limite:
        out["aviso"] = f"a lista parou no limite de {limite} objetos; os de menor gasto ficaram de fora dos totais (aumente --limit)"
    lib.print_json(out)


# ---------------------------------------------------------------------------
# comparar-janelas: 30, 14 e 7 dias lado a lado
# ---------------------------------------------------------------------------

def _params_janela(args, faixa, limite):
    """Parâmetros de uma janela: nível, período, ordem por gasto e filtro de ativos."""
    params = {"level": args.level, "time_range": faixa, "sort": ["spend_descending"], "limit": _pagina(limite)}
    if args.so_ativos:
        params["filtering"] = [_filtro_ativos(args.level)]
    return params


def _hoje_da_conta(acct):
    """Data de hoje no fuso da conta de anúncio (a Meta fecha o dia nesse fuso), com fallback local."""
    try:
        from zoneinfo import ZoneInfo
        ok, d = lib.graph_get(acct, params={"fields": "timezone_name"})
        if ok and d.get("timezone_name"):
            return datetime.now(ZoneInfo(d["timezone_name"])).date()
    except Exception:
        pass
    return date.today()


def _guardar(achados, rows, nivel, rotulo):
    """Guarda as métricas de cada linha no objeto certo, sob o rótulo da janela."""
    for r in rows:
        ident = _identidade(r, nivel)
        registro = achados.setdefault(ident["id"], {"ident": ident, "janelas": {}})
        registro["janelas"][rotulo] = _metricas(r)


@lib.handle_fb_error
def cmd_comparar_janelas(args):
    """As três janelas por objeto: base da regra de cruzar 30/14/7 antes de pausar."""
    lib.init_api(quiet=True)
    acct = lib.resolve_target(args)
    limite = _limite(args.limit)
    hoje = _hoje_da_conta(acct)
    ontem = hoje - timedelta(days=1)
    janelas = {f"{n}d": {"since": (hoje - timedelta(days=n)).isoformat(), "until": ontem.isoformat()} for n in JANELAS}

    achados = {}
    truncadas = []
    for rotulo, faixa in janelas.items():
        params = _params_janela(args, faixa, limite)
        rows = _ler_nivel(acct, args.level, params, limite)
        if len(rows) >= limite:
            truncadas.append(rotulo)
        _guardar(achados, rows, args.level, rotulo)

    # Janela truncada: objeto fora do top N ainda pode ter gasto nela. Busca por id
    # para não mostrar zero no lugar de um número real.
    for rotulo in truncadas:
        faltam = [i for i, reg in achados.items() if i and rotulo not in reg["janelas"]]
        for inicio in range(0, len(faltam), LOTE_IDS):
            lote = faltam[inicio:inicio + LOTE_IDS]
            params = _params_janela(args, janelas[rotulo], len(lote))
            params["filtering"] = params.get("filtering", []) + [
                {"field": f"{args.level}.id", "operator": "IN", "value": lote}
            ]
            _guardar(achados, _ler_nivel(acct, args.level, params, len(lote)), args.level, rotulo)

    objetos = []
    for reg in achados.values():
        obj = dict(reg["ident"])
        for rotulo in janelas:
            obj[rotulo] = reg["janelas"].get(rotulo) or _metricas(None)
        objetos.append(obj)
    objetos.sort(key=lambda o: tuple(-(o[r]["gasto"] or 0) for r in janelas))

    out = {
        "conta": acct,
        "nivel": args.level,
        "so_ativos": bool(args.so_ativos),
        "janelas": janelas,
        "nota": "cada janela termina ontem, igual aos presets last_30d/last_14d/last_7d da Meta; objeto sem entrega na janela aparece zerado",
        "metrica_principal": f"mensagens_iniciadas = {ACAO_MENSAGEM}",
        "quantidade": len(objetos),
        "objetos": objetos,
        "totais": {rotulo: _totais([o[rotulo] for o in objetos]) for rotulo in janelas},
    }
    if truncadas:
        out["aviso"] = (f"janela(s) {', '.join(truncadas)} pararam no limite de {limite} objetos; "
                        "os listados foram completados por id, mas outros de menor gasto podem estar de fora (aumente --limit)")
    lib.print_json(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_periodo_simples(p):
    p.add_argument("--date-preset", default="last_7d", choices=DATE_PRESETS, help="Período relativo (padrão: last_7d)")
    p.add_argument("--since", help="Data inicial YYYY-MM-DD (tem prioridade sobre --date-preset; --until vazio = hoje)")
    p.add_argument("--until", help="Data final YYYY-MM-DD (exige --since)")


def main():
    parser = argparse.ArgumentParser(
        description="Leitura de resultados (insights) das contas Meta. Só leitura.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("account", help="Insights da conta")
    lib.add_target_args(s)
    _add_insights_args(s)
    s.set_defaults(fn=cmd_account)

    for nome, fn, rotulo in (("campaign", cmd_campaign, "campanha"), ("adset", cmd_adset, "conjunto"), ("ad", cmd_ad, "anúncio")):
        s = sub.add_parser(nome, help=f"Insights de um(a) {rotulo}")
        s.add_argument("--id", required=True, help=f"Id do(a) {rotulo}")
        _add_insights_args(s)
        s.set_defaults(fn=fn)

    s = sub.add_parser("resultado", help="Gasto, mensagens iniciadas e custo por mensagem por objeto, ordenado por gasto")
    lib.add_target_args(s)
    s.add_argument("--level", default="campaign", choices=["campaign", "adset", "ad"], help="Nível (padrão: campaign)")
    _add_periodo_simples(s)
    s.add_argument("--limit", type=int, default=50, help="Máximo de objetos (padrão: 50)")
    s.add_argument("--so-ativos", action="store_true", help="Só objetos em veiculação (padrão: todos com entrega no período)")
    s.set_defaults(fn=cmd_resultado)

    s = sub.add_parser("comparar-janelas", help="30, 14 e 7 dias lado a lado por objeto (cruzar antes de pausar)")
    lib.add_target_args(s)
    s.add_argument("--level", default="ad", choices=["ad", "adset", "campaign"], help="Nível (padrão: ad)")
    s.add_argument("--limit", type=int, default=50, help="Máximo de objetos por janela (padrão: 50)")
    s.add_argument("--so-ativos", action=argparse.BooleanOptionalAction, default=True,
                   help="Só objetos em veiculação (padrão: ligado; --no-so-ativos inclui pausados)")
    s.set_defaults(fn=cmd_comparar_janelas)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
