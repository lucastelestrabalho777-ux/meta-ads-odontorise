#!/usr/bin/env python3
"""
meta-ads-odontorise: leitura da conta (20 subcomandos, só GET).

Nada aqui cria, edita, pausa, ativa ou apaga. Toda saída é JSON no stdout;
mensagens para pessoas vão no stderr. Erros da Meta viram JSON com dica
(ver lib.handle_fb_error). Nenhuma saída carrega token.

Conta alvo: --account act_X ou --cliente <nome, #código ou slug do cadastro local>.

Subcomandos:
  accounts                  contas de anúncio que o token enxerga
  account-details           dados de uma conta (saldo, gasto, moeda, status)
  campaigns                 campanhas da conta (padrão: só ACTIVE; --status ALL para todas)
  campaign                  uma campanha por id
  adsets                    conjuntos da conta (padrão: só ACTIVE)
  adsets-by-campaign        conjuntos de uma campanha
  adset                     um conjunto por id
  adsets-by-ids             vários conjuntos por id
  ads                       anúncios da conta (padrão: só ACTIVE)
  ads-by-campaign           anúncios de uma campanha
  ads-by-adset              anúncios de um conjunto
  ad                        um anúncio por id
  creative                  um criativo por id
  creatives-by-ad           criativos de um anúncio
  preview                   HTML de prévia de um criativo (--format all para todos)
  images                    imagens da conta
  videos                    vídeos da conta
  activities                histórico de alterações da conta (--dias, --so-humanas)
  activities-by-adset       histórico de alterações de um conjunto
  custom-audiences          públicos personalizados
  lookalike-audiences       públicos semelhantes

Orçamentos vêm em centavos da Meta; cada campo ganha um irmão *_reais (original mantido).
--limit vale dentro da paginação: o script para de baixar ao atingir o limite.

Molde: skill meta-ads-ratos (read.py). Adaptações: --cliente do cadastro local,
status padrão ACTIVE, effective_status nos anúncios, orçamento em reais,
activities com janela de dias e filtro de eventos humanos, preview registra
erro por formato, sem o subcomando paginate (a URL de paginação carrega token).
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib.pagination import collect_cursor  # noqa: E402

PAGE_SIZE = 100

# Campos que a Meta devolve em centavos.
_BUDGET_FIELDS = (
    "daily_budget", "lifetime_budget", "budget_remaining",
    "spend_cap", "amount_spent", "balance",
)

PREVIEW_FORMATS = [
    "DESKTOP_FEED_STANDARD",
    "RIGHT_COLUMN_STANDARD",
    "MOBILE_FEED_STANDARD",
    "MOBILE_FEED_BASIC",
    "INSTAGRAM_STANDARD",
    "INSTAGRAM_STORY",
    "INSTAGRAM_REELS",
    "MARKETPLACE_MOBILE",
    "AUDIENCE_NETWORK_OUTSTREAM_VIDEO",
    "INSTANT_ARTICLE_STANDARD",
    "MESSENGER_MOBILE_INBOX_MEDIA",
]


# ---------------------------------------------------------------------------
# SDK (import tardio: só carrega quando um comando roda)
# ---------------------------------------------------------------------------

def _sdk():
    """Classes do SDK da Meta, importadas só na hora de usar."""
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.adcreative import AdCreative
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.user import User
    return {
        "AdAccount": AdAccount, "Campaign": Campaign, "AdSet": AdSet,
        "Ad": Ad, "AdCreative": AdCreative, "User": User,
    }


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def _add_status_arg(parser):
    """--status com padrão ACTIVE; ALL desliga o filtro."""
    parser.add_argument(
        "--status", default="ACTIVE",
        help="Filtro por effective_status, separado por vírgula (ex: ACTIVE,PAUSED). "
             "Padrão: ACTIVE. Use ALL para trazer tudo.",
    )


def _status_filter(args):
    """Lista de status para o filtro, ou None quando é ALL / vazio."""
    statuses = lib.parse_status_filter(getattr(args, "status", None))
    if not statuses or "ALL" in statuses:
        return None
    return statuses


def _build_params(args, include_status=True):
    """Parâmetros comuns de listagem: tamanho de página, cursores e filtro de status."""
    params = {"limit": PAGE_SIZE}
    limit = getattr(args, "limit", None)
    if limit:
        params["limit"] = min(limit, PAGE_SIZE)
    if getattr(args, "after", None):
        params["after"] = args.after
    if getattr(args, "before", None):
        params["before"] = args.before
    if include_status:
        statuses = _status_filter(args)
        if statuses:
            params["effective_status"] = statuses
    return params


def _collect(cursor, limit=None, keep=None):
    """
    Percorre o cursor parando ao atingir o limite. Com `keep`, só conta os itens
    aceitos pelo filtro, então o limite vale para o resultado final.
    """
    if keep is None:
        return collect_cursor(cursor, limit)
    results = []
    for item in cursor:
        row = item.export_all_data() if hasattr(item, "export_all_data") else item
        if not keep(row):
            continue
        results.append(row)
        if limit and len(results) >= limit:
            break
    return results


def _to_dict(obj):
    """Objeto do SDK vira dict comum (mantém dict como está)."""
    if hasattr(obj, "export_all_data"):
        return obj.export_all_data()
    return obj


def _com_reais(row):
    """Adiciona <campo>_reais para cada campo em centavos presente. Original fica."""
    row = _to_dict(row)
    if not isinstance(row, dict):
        return row
    for field in _BUDGET_FIELDS:
        val = row.get(field)
        if val is None or val == "":
            continue
        try:
            row[f"{field}_reais"] = round(int(val) / 100, 2)
        except (ValueError, TypeError):
            pass
    return row


def _lista_com_reais(rows):
    return [_com_reais(r) for r in rows]


def _janela(dias):
    """(since, until) em ISO 8601 UTC para os últimos `dias` dias."""
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(days=dias)
    fmt = "%Y-%m-%dT%H:%M:%S%z"
    return inicio.strftime(fmt), agora.strftime(fmt)


def _so_humanas(row):
    """Mantém só eventos de pessoas: remove os cujo actor_name contém 'Meta'."""
    ator = str(row.get("actor_name") or "")
    return "Meta" not in ator


def _activity_params(args):
    params = {"limit": PAGE_SIZE}
    if args.limit:
        params["limit"] = min(args.limit, PAGE_SIZE)
    if getattr(args, "after", None):
        params["after"] = args.after
    if getattr(args, "before", None):
        params["before"] = args.before
    if args.dias and args.dias > 0:
        params["since"], params["until"] = _janela(args.dias)
    return params


_ACTIVITY_FIELDS = [
    "event_type", "event_time", "actor_name", "object_name", "object_id",
    "extra_data", "translated_event_type",
]

_CREATIVE_FIELDS = [
    "id", "name", "status", "url_tags", "link_url", "object_story_spec",
    "effective_object_story_id", "thumbnail_url", "body", "title",
    "call_to_action_type", "instagram_permalink_url",
]


# ---------------------------------------------------------------------------
# 1. accounts
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_accounts(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or ["account_id", "name", "account_status", "currency"]
    params = {"limit": PAGE_SIZE}
    if args.limit:
        params["limit"] = min(args.limit, PAGE_SIZE)
    cursor = lib.retry_call(lambda: S["User"]("me").get_ad_accounts(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 2. account-details
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_account_details(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or [
        "id", "name", "business_name", "account_status", "disable_reason",
        "balance", "amount_spent", "spend_cap", "currency", "timezone_name",
        "created_time", "funding_source_details",
    ]
    conta = lib.retry_call(lambda: S["AdAccount"](acct).api_get(fields=fields))
    lib.print_json(_com_reais(conta))


# ---------------------------------------------------------------------------
# 3. campaigns
# ---------------------------------------------------------------------------

_CAMPAIGN_FIELDS = [
    "id", "name", "status", "effective_status", "objective",
    "daily_budget", "lifetime_budget", "created_time", "updated_time",
]


@lib.handle_fb_error
def cmd_campaigns(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or _CAMPAIGN_FIELDS
    params = _build_params(args)
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_campaigns(fields=fields, params=params))
    lib.print_json(_lista_com_reais(_collect(cursor, args.limit)))


# ---------------------------------------------------------------------------
# 4. campaign
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_campaign(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _CAMPAIGN_FIELDS + [
        "buying_type", "bid_strategy", "special_ad_categories", "start_time", "stop_time",
    ]
    campanha = lib.retry_call(lambda: S["Campaign"](args.id).api_get(fields=fields))
    lib.print_json(_com_reais(campanha))


# ---------------------------------------------------------------------------
# 5. adsets
# ---------------------------------------------------------------------------

_ADSET_LIST_FIELDS = [
    "id", "name", "status", "effective_status", "campaign_id",
    "daily_budget", "lifetime_budget", "optimization_goal", "bid_strategy",
    "start_time", "end_time",
]

_ADSET_FIELDS = _ADSET_LIST_FIELDS + [
    "targeting", "promoted_object", "destination_type", "billing_event",
    "created_time", "updated_time",
]


@lib.handle_fb_error
def cmd_adsets(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or _ADSET_LIST_FIELDS
    params = _build_params(args)
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_ad_sets(fields=fields, params=params))
    lib.print_json(_lista_com_reais(_collect(cursor, args.limit)))


# ---------------------------------------------------------------------------
# 6. adsets-by-campaign
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_adsets_by_campaign(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _ADSET_LIST_FIELDS + ["targeting"]
    params = _build_params(args)
    cursor = lib.retry_call(lambda: S["Campaign"](args.campaign).get_ad_sets(fields=fields, params=params))
    lib.print_json(_lista_com_reais(_collect(cursor, args.limit)))


# ---------------------------------------------------------------------------
# 7. adset
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_adset(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _ADSET_FIELDS
    conjunto = lib.retry_call(lambda: S["AdSet"](args.id).api_get(fields=fields))
    lib.print_json(_com_reais(conjunto))


# ---------------------------------------------------------------------------
# 8. adsets-by-ids
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_adsets_by_ids(args):
    lib.init_api(quiet=True)
    S = _sdk()
    ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    if not ids:
        lib.print_error("nenhum id em --ids")
        sys.exit(1)
    fields = lib.parse_fields(args.fields) or _ADSET_FIELDS
    resultados = []
    for adset_id in ids:
        conjunto = lib.retry_call(lambda: S["AdSet"](adset_id).api_get(fields=fields))
        resultados.append(_com_reais(conjunto))
    lib.print_json(resultados)


# ---------------------------------------------------------------------------
# 9. ads
# ---------------------------------------------------------------------------

_AD_LIST_FIELDS = [
    "id", "name", "status", "effective_status", "adset_id", "campaign_id", "creative",
]

_AD_FIELDS = _AD_LIST_FIELDS + [
    "issues_info", "created_time", "updated_time",
]


@lib.handle_fb_error
def cmd_ads(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or _AD_LIST_FIELDS
    params = _build_params(args)
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_ads(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 10. ads-by-campaign
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_ads_by_campaign(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _AD_LIST_FIELDS
    params = _build_params(args)
    cursor = lib.retry_call(lambda: S["Campaign"](args.campaign).get_ads(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 11. ads-by-adset
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_ads_by_adset(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _AD_LIST_FIELDS
    params = _build_params(args)
    cursor = lib.retry_call(lambda: S["AdSet"](args.adset).get_ads(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 12. ad
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_ad(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _AD_FIELDS
    anuncio = lib.retry_call(lambda: S["Ad"](args.id).api_get(fields=fields))
    lib.print_json(anuncio)


# ---------------------------------------------------------------------------
# 13. creative
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_creative(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _CREATIVE_FIELDS
    criativo = lib.retry_call(lambda: S["AdCreative"](args.id).api_get(fields=fields))
    lib.print_json(criativo)


# ---------------------------------------------------------------------------
# 14. creatives-by-ad
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_creatives_by_ad(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _CREATIVE_FIELDS
    params = _build_params(args, include_status=False)
    cursor = lib.retry_call(lambda: S["Ad"](args.ad).get_ad_creatives(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 15. preview
# ---------------------------------------------------------------------------

def _preview_formato(S, creative_id, fmt):
    """Prévia em um formato. Devolve lista de dicts; em erro, um dict com o erro."""
    from facebook_business.exceptions import FacebookRequestError
    try:
        cursor = lib.retry_call(lambda: S["AdCreative"](creative_id).get_previews(params={"ad_format": fmt}))
        itens = []
        for p in _collect(cursor):
            p["_format"] = fmt
            itens.append(p)
        if not itens:
            itens.append({"_format": fmt, "body": None, "aviso": "a Meta não devolveu prévia neste formato"})
        return itens
    except FacebookRequestError as e:
        return [{
            "_format": fmt,
            "erro": lib.redigir(e.api_error_message()),
            "code": e.api_error_code(),
            "subcode": e.api_error_subcode(),
        }]
    except Exception as e:  # nunca str(e): pode carregar URL com token
        return [{"_format": fmt, "erro": f"falha inesperada ({type(e).__name__})", "code": None}]


@lib.handle_fb_error
def cmd_preview(args):
    lib.init_api(quiet=True)
    S = _sdk()
    if args.format.lower() == "all":
        todos = []
        for fmt in PREVIEW_FORMATS:
            todos.extend(_preview_formato(S, args.creative, fmt))
        lib.print_json(todos)
        return
    fmt = args.format.upper()
    cursor = lib.retry_call(lambda: S["AdCreative"](args.creative).get_previews(params={"ad_format": fmt}))
    itens = _collect(cursor)
    for p in itens:
        p["_format"] = fmt
    lib.print_json(itens)


# ---------------------------------------------------------------------------
# 16. images
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_images(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or [
        "id", "name", "hash", "url", "url_128", "width", "height", "status", "created_time",
    ]
    params = _build_params(args, include_status=False)
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_ad_images(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 17. videos
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_videos(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or [
        "id", "title", "description", "length", "source", "picture",
        "status", "created_time", "updated_time",
    ]
    params = _build_params(args, include_status=False)
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_ad_videos(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 18. activities
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_activities(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or _ACTIVITY_FIELDS
    params = _activity_params(args)
    keep = _so_humanas if args.so_humanas else None
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_activities(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit, keep=keep))


# ---------------------------------------------------------------------------
# 19. activities-by-adset
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_activities_by_adset(args):
    lib.init_api(quiet=True)
    S = _sdk()
    fields = lib.parse_fields(args.fields) or _ACTIVITY_FIELDS
    params = _activity_params(args)
    keep = _so_humanas if args.so_humanas else None
    cursor = lib.retry_call(lambda: S["AdSet"](args.adset).get_activities(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit, keep=keep))


# ---------------------------------------------------------------------------
# 20. custom-audiences
# ---------------------------------------------------------------------------

_AUDIENCE_FIELDS = [
    "id", "name", "subtype", "description", "approximate_count_lower_bound",
    "approximate_count_upper_bound", "data_source", "delivery_status",
    "operation_status", "time_created", "time_updated",
]


@lib.handle_fb_error
def cmd_custom_audiences(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or _AUDIENCE_FIELDS
    params = _build_params(args, include_status=False)
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_custom_audiences(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# 21. lookalike-audiences
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_lookalike_audiences(args):
    lib.init_api(quiet=True)
    S = _sdk()
    acct = lib.resolve_target(args)
    fields = lib.parse_fields(args.fields) or _AUDIENCE_FIELDS + ["lookalike_spec"]
    params = _build_params(args, include_status=False)
    params["filtering"] = [{"field": "subtype", "operator": "EQUAL", "value": "LOOKALIKE"}]
    cursor = lib.retry_call(lambda: S["AdAccount"](acct).get_custom_audiences(fields=fields, params=params))
    lib.print_json(_collect(cursor, args.limit))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _lista(sub, nome, ajuda, fn, alvo=True, status=True, limit_default=None):
    """Subparser de listagem com os argumentos comuns."""
    p = sub.add_parser(nome, help=ajuda)
    if alvo:
        lib.add_target_args(p)
    lib.add_fields_arg(p)
    if status:
        _add_status_arg(p)
    lib.add_pagination_args(p)
    if limit_default is not None:
        p.set_defaults(limit=limit_default)
    p.set_defaults(func=fn)
    return p


def _um(sub, nome, ajuda, fn, arg="--id", arg_help="Id"):
    """Subparser de leitura de um objeto por id."""
    p = sub.add_parser(nome, help=ajuda)
    p.add_argument(arg, required=True, help=arg_help)
    lib.add_fields_arg(p)
    p.set_defaults(func=fn)
    return p


def _activity_args(p):
    p.add_argument("--dias", type=int, default=30, help="Janela em dias, contada de hoje para trás (padrão: 30; 0 = sem janela)")
    p.add_argument("--so-humanas", action="store_true", help="Só eventos de pessoas: remove os feitos pela Meta (actor_name contém 'Meta')")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Leitura de contas Meta Ads (OdontoRise). Só GET; nada é alterado.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. accounts
    p = sub.add_parser("accounts", help="Contas de anúncio que o token enxerga")
    lib.add_fields_arg(p)
    p.add_argument("--limit", type=int, default=None, help="Máximo de contas (padrão: todas)")
    p.set_defaults(func=cmd_accounts)

    # 2. account-details
    p = sub.add_parser("account-details", help="Dados de uma conta de anúncio")
    lib.add_target_args(p)
    lib.add_fields_arg(p)
    p.set_defaults(func=cmd_account_details)

    # 3 e 4. campanhas
    _lista(sub, "campaigns", "Campanhas da conta (padrão: só ACTIVE)", cmd_campaigns)
    _um(sub, "campaign", "Uma campanha por id", cmd_campaign, arg_help="Id da campanha")

    # 5 a 8. conjuntos
    _lista(sub, "adsets", "Conjuntos da conta (padrão: só ACTIVE)", cmd_adsets)
    p = _lista(sub, "adsets-by-campaign", "Conjuntos de uma campanha (padrão: só ACTIVE)", cmd_adsets_by_campaign, alvo=False)
    p.add_argument("--campaign", required=True, help="Id da campanha")
    _um(sub, "adset", "Um conjunto por id", cmd_adset, arg_help="Id do conjunto")
    p = sub.add_parser("adsets-by-ids", help="Vários conjuntos por id")
    p.add_argument("--ids", required=True, help="Ids dos conjuntos separados por vírgula")
    lib.add_fields_arg(p)
    p.set_defaults(func=cmd_adsets_by_ids)

    # 9 a 12. anúncios
    _lista(sub, "ads", "Anúncios da conta (padrão: só ACTIVE)", cmd_ads)
    p = _lista(sub, "ads-by-campaign", "Anúncios de uma campanha (padrão: só ACTIVE)", cmd_ads_by_campaign, alvo=False)
    p.add_argument("--campaign", required=True, help="Id da campanha")
    p = _lista(sub, "ads-by-adset", "Anúncios de um conjunto (padrão: só ACTIVE)", cmd_ads_by_adset, alvo=False)
    p.add_argument("--adset", required=True, help="Id do conjunto")
    _um(sub, "ad", "Um anúncio por id", cmd_ad, arg_help="Id do anúncio")

    # 13 a 15. criativos
    _um(sub, "creative", "Um criativo por id", cmd_creative, arg_help="Id do criativo")
    p = _lista(sub, "creatives-by-ad", "Criativos de um anúncio", cmd_creatives_by_ad, alvo=False, status=False, limit_default=25)
    p.add_argument("--ad", required=True, help="Id do anúncio")
    p = sub.add_parser("preview", help="HTML de prévia de um criativo")
    p.add_argument("--creative", required=True, help="Id do criativo")
    p.add_argument("--format", default="MOBILE_FEED_STANDARD",
                   help="Formato (" + ", ".join(PREVIEW_FORMATS) + ") ou all para todos. Padrão: MOBILE_FEED_STANDARD")
    p.set_defaults(func=cmd_preview)

    # 16 e 17. mídia
    _lista(sub, "images", "Imagens da conta", cmd_images, status=False, limit_default=25)
    _lista(sub, "videos", "Vídeos da conta", cmd_videos, status=False, limit_default=25)

    # 18 e 19. histórico
    p = _lista(sub, "activities", "Histórico de alterações da conta", cmd_activities, status=False, limit_default=25)
    _activity_args(p)
    p = _lista(sub, "activities-by-adset", "Histórico de alterações de um conjunto", cmd_activities_by_adset, alvo=False, status=False, limit_default=25)
    p.add_argument("--adset", required=True, help="Id do conjunto")
    _activity_args(p)

    # 20 e 21. públicos
    _lista(sub, "custom-audiences", "Públicos personalizados da conta", cmd_custom_audiences, status=False, limit_default=25)
    _lista(sub, "lookalike-audiences", "Públicos semelhantes da conta", cmd_lookalike_audiences, status=False, limit_default=25)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
