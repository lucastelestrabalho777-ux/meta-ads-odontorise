#!/usr/bin/env python3
"""
meta-ads-odontorise: segmentação (só leitura).

Busca cidades, bairros, regiões, interesses, comportamentos e dados demográficos
na Meta; valida, descreve e estima o público de uma segmentação; e audita o
targeting de um conjunto existente contra as regras da casa. Nada é criado,
editado, pausado nem apagado.

Subcomandos:
  interests             --q X [--limit N] [--locale pt_BR]
  interest-suggestions  --nomes "Bancos,Beleza" [--limit N] [--locale pt_BR]
  behaviors             [--q X] [--limit N] [--locale pt_BR]
  demographics          [--q X] [--limit N] [--locale pt_BR]
  geolocations          --q X [--types city,neighborhood,region] [--country BR] [--limit N]
  validate              (--account|--cliente) (--spec JSON | --spec-file ARQ | --adset ID | --ids 1,2)
  reach                 (--account|--cliente) (--spec | --spec-file | --adset) [--optimization-goal]
  delivery              (--account|--cliente) (--spec | --spec-file | --adset) [--optimization-goal] [--daily-budget CENTAVOS]
  describe              (--account|--cliente) (--spec | --spec-file | --adset)
  auditar               --adset ID [--raio-maximo 10]

Com --adset a conta pode ser omitida: sai do próprio conjunto.
Saída em JSON no stdout; mensagens humanas no stderr. Erro da Meta vem em JSON com hint.

Molde: skill meta-ads-ratos (targeting.py). Adaptações: locale pt_BR, tipos e país
padrão em geolocations, validação por targeting_list, sugestões por nome (a Meta
ignora ids em interest_list), --spec-file e --adset como origem do spec, filtro local
em behaviors/demographics, aviso quando a busca vem vazia e o subcomando auditar.
"""

import argparse
import json
import os
import sys
import unicodedata

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib.pagination import collect_cursor  # noqa: E402

LOCALE_PADRAO = "pt_BR"
TIPOS_GEO_PADRAO = "city,neighborhood,region"
PAIS_PADRAO = "BR"
OBJETIVO_PADRAO = "CONVERSATIONS"      # campanhas de mensagem no WhatsApp
RAIO_MAXIMO_KM = 10.0
MILHA_EM_KM = 1.609344
PLATAFORMAS_FORA_DA_CASA = ("facebook", "audience_network", "messenger")
TIPO_GEO = {"custom_locations": "ponto no mapa", "cities": "cidade", "places": "lugar"}
CHAVES_GEO = ("countries", "regions", "cities", "zips", "neighborhoods", "subcities",
              "geo_markets", "places", "custom_locations")
AVISO_BUSCA_VAZIA = ("a Meta não devolveu interesse para esse termo. Termos de saúde e odontologia (implante, "
                     "dentista, clareamento, harmonização) foram retirados do direcionamento detalhado; a busca "
                     "funciona com termos amplos (estética, beleza, sorriso). Alternativa: localização, públicos "
                     "personalizados e semelhantes.")


# ---------------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------------

def _api():
    from facebook_business.api import FacebookAdsApi
    return FacebookAdsApi.get_default_api()


def _busca(params):
    """GET /search da Meta (TargetingSearch); devolve lista de dicts."""
    from facebook_business.adobjects.targetingsearch import TargetingSearch
    return [r.export_all_data() for r in TargetingSearch.search(params=params)]


def _normalizar(texto):
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()


def _filtrar_local(itens, q, limit):
    """
    Filtro por trecho (sem acento nem caixa) e corte em limit. Só para o /search de
    categorias (behaviors, demographics), que vem inteiro em uma resposta e ignora q e limit.
    """
    if q:
        qn = _normalizar(q)
        itens = [i for i in itens if qn in _normalizar(" ".join(
            [str(i.get("name", "")), str(i.get("description", "")), " ".join(map(str, i.get("path") or []))]))]
    if limit:
        itens = itens[:limit]
    return itens


def _lista(texto):
    return [t.strip() for t in str(texto or "").split(",") if t.strip()]


def _ler_adset(adset_id, campos):
    """GET do conjunto pelo id, com os campos pedidos. Erro da Meta sobe para o decorator."""
    return _api().call("GET", (str(adset_id).strip(),), params={"fields": ",".join(campos)}).json()


def _ler_spec_arquivo(caminho):
    try:
        with open(os.path.expanduser(caminho), encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        lib.print_error(f"não consegui ler o spec em {caminho} ({type(e).__name__}); precisa ser um arquivo JSON válido")
        sys.exit(1)


def _conta_e_spec(args):
    """
    Devolve (conta, spec) a partir de --spec, --spec-file ou --adset (um só).
    Com --adset, a conta vem do próprio conjunto se --account/--cliente não forem dados.
    """
    fontes = [f for f in ("spec", "spec_file", "adset") if getattr(args, f, None)]
    if len(fontes) != 1:
        lib.print_error("informe exatamente uma origem da segmentação: --spec, --spec-file ou --adset")
        sys.exit(1)
    tem_conta = bool(getattr(args, "account", None) or getattr(args, "cliente", None))
    if fontes[0] == "adset":
        conta = lib.resolve_target(args) if tem_conta else None
        d = _ler_adset(args.adset, ["account_id", "targeting"])
        return conta or f"act_{d.get('account_id')}", d.get("targeting") or {}
    conta = lib.resolve_target(args)
    spec = lib.parse_json_arg(args.spec, "--spec") if fontes[0] == "spec" else _ler_spec_arquivo(args.spec_file)
    if not isinstance(spec, dict):
        lib.print_error("o spec precisa ser um objeto JSON (o targeting do conjunto), não lista nem texto")
        sys.exit(1)
    return conta, spec


def _erro_endpoint_antigo(e, endpoint, alternativa):
    """Erro da Meta em endpoint que ela pode ter descontinuado: JSON com a alternativa e sai com 1."""
    code = e.api_error_code()
    if code in lib.RATE_LIMIT_CODES:
        raise e
    print(json.dumps({
        "error": True,
        "message": lib.redigir(e.api_error_message()),
        "code": code,
        "subcode": e.api_error_subcode(),
        "fbtrace_id": lib._fbtrace(e),
        "hint": f"A Meta recusou o endpoint {endpoint} (pode ter sido descontinuado nesta versão da API). {alternativa}",
    }, indent=2, ensure_ascii=False, default=str))
    sys.exit(1)


def _linhas_texto(sentencelines):
    """Achata as linhas de descrição da Meta em 'Título: item; item'."""
    out = []
    for linha in sentencelines or []:
        if not isinstance(linha, dict):
            continue
        filhos = "; ".join(map(str, linha.get("children") or []))
        out.append(f"{linha.get('content', '')} {filhos}".strip())
    return out


def _primeiro(cursor):
    itens = collect_cursor(cursor, limit=1)
    return itens[0] if itens else {}


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_interests(args):
    """Busca interesses por palavra (o limit vai na chamada)."""
    lib.init_api(quiet=True)
    itens = _busca({"q": args.q, "type": "adinterest", "limit": args.limit, "locale": args.locale})
    saida = {"ok": True, "busca": args.q, "quantidade": len(itens), "resultados": itens}
    if not itens:
        saida["aviso"] = AVISO_BUSCA_VAZIA
    lib.print_json(saida)


@lib.handle_fb_error
def cmd_interest_suggestions(args):
    """Interesses parecidos com os nomes informados (a Meta só aceita nome em interest_list, não id)."""
    lib.init_api(quiet=True)
    nomes = [n for grupo in (args.nomes or []) for n in _lista(grupo)]
    if not nomes:
        lib.print_error("informe ao menos um nome em --nomes (ex: --nomes \"Bancos,Beleza\"); use o nome como a busca devolveu")
        sys.exit(1)
    itens = _busca({"type": "adinterestsuggestion", "interest_list": nomes, "limit": args.limit, "locale": args.locale})
    lib.print_json({"ok": True, "sementes": nomes, "quantidade": len(itens), "resultados": itens,
                    "aviso": "a Meta completa a lista com sugestões genéricas quando há poucas parecidas; conferir o caminho (path) de cada uma"})


@lib.handle_fb_error
def cmd_behaviors(args):
    """Comportamentos disponíveis (lista inteira da Meta; --q e --limit filtram localmente)."""
    lib.init_api(quiet=True)
    todos = _busca({"type": "adTargetingCategory", "class": "behaviors", "locale": args.locale})
    itens = _filtrar_local(todos, args.q, args.limit)
    lib.print_json({"ok": True, "busca": args.q, "total_na_meta": len(todos), "quantidade": len(itens), "resultados": itens})


@lib.handle_fb_error
def cmd_demographics(args):
    """Dados demográficos disponíveis (lista inteira da Meta; --q e --limit filtram localmente)."""
    lib.init_api(quiet=True)
    todos = _busca({"type": "adTargetingCategory", "class": "demographics", "locale": args.locale})
    itens = _filtrar_local(todos, args.q, args.limit)
    lib.print_json({"ok": True, "busca": args.q, "total_na_meta": len(todos), "quantidade": len(itens), "resultados": itens})


@lib.handle_fb_error
def cmd_geolocations(args):
    """Busca cidade, bairro, região etc. pelo nome (padrão: Brasil, tipos city,neighborhood,region)."""
    lib.init_api(quiet=True)
    tipos = _lista(args.types)
    params = {"q": args.q, "type": "adgeolocation", "limit": args.limit, "locale": args.locale}
    if tipos:
        params["location_types"] = tipos
    pais = (args.country or "").strip()
    if pais and pais.lower() not in ("todos", "all"):
        params["country_code"] = pais.upper()
    itens = _busca(params)
    lib.print_json({"ok": True, "busca": args.q, "tipos": tipos, "pais": params.get("country_code"),
                    "quantidade": len(itens), "resultados": itens})


# ---------------------------------------------------------------------------
# Validação, estimativa e descrição de um spec
# ---------------------------------------------------------------------------

def _itens_do_spec(spec):
    """Extrai {type, id} de flexible_spec, exclusions e das chaves soltas interests/behaviors."""
    itens, vistos = [], set()
    blocos = [b for b in (spec.get("flexible_spec") or []) if isinstance(b, dict)]
    if isinstance(spec.get("exclusions"), dict):
        blocos.append(spec["exclusions"])
    blocos.append({k: spec.get(k) for k in ("interests", "behaviors") if spec.get(k)})
    for bloco in blocos:
        for tipo, valores in bloco.items():
            if not isinstance(valores, list):
                continue
            for v in valores:
                if isinstance(v, dict) and v.get("id") is not None and (tipo, str(v["id"])) not in vistos:
                    vistos.add((tipo, str(v["id"])))
                    itens.append({"type": tipo, "id": str(v["id"])})
    return itens


@lib.handle_fb_error
def cmd_validate(args):
    """Confere na Meta se cada interesse ou comportamento do spec (ou de --ids) ainda existe."""
    lib.init_api(quiet=True)
    if args.ids:
        if args.spec or args.spec_file or args.adset:
            lib.print_error("use --ids sozinho ou uma origem de spec (--spec, --spec-file, --adset), não os dois")
            sys.exit(1)
        conta = lib.resolve_target(args)
        itens = [{"type": args.tipo, "id": i} for i in _lista(args.ids)]
    else:
        conta, spec = _conta_e_spec(args)
        itens = _itens_do_spec(spec)
    if not itens:
        lib.print_json({"ok": True, "conta": conta, "quantidade": 0, "todos_validos": True, "invalidos": [], "itens": [],
                        "aviso": "nada para validar: o spec não tem interesses nem comportamentos (localização e idade se conferem com describe)"})
        return
    r = _api().call("GET", (conta, "targetingvalidation"), params={"targeting_list": itens}).json()
    dados = r.get("data", []) if isinstance(r, dict) else []
    invalidos = [{"type": d.get("type"), "id": d.get("id")} for d in dados if not d.get("valid")]
    lib.print_json({"ok": True, "conta": conta, "quantidade": len(dados), "todos_validos": not invalidos,
                    "invalidos": invalidos, "itens": dados})


@lib.handle_fb_error
def cmd_reach(args):
    """Público estimado (reachestimate). Endpoint antigo: se a Meta recusar, usar delivery."""
    lib.init_api(quiet=True)
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.exceptions import FacebookRequestError
    conta, spec = _conta_e_spec(args)
    params = {"targeting_spec": spec}
    if args.optimization_goal:
        params["optimization_goal"] = args.optimization_goal
    try:
        est = _primeiro(AdAccount(conta).get_reach_estimate(params=params))
    except FacebookRequestError as e:
        _erro_endpoint_antigo(e, "reachestimate",
                              f"Use o subcomando delivery com o mesmo spec (--optimization-goal {OBJETIVO_PADRAO}): devolve o mesmo público em estimate_mau.")
    lib.print_json({"ok": True, "conta": conta,
                    "publico_estimado": {"minimo": est.get("users_lower_bound"), "maximo": est.get("users_upper_bound")},
                    "pronta": est.get("estimate_ready"), "estimativa": est,
                    "aviso": "reachestimate é um endpoint antigo da Meta; delivery devolve a mesma estimativa com curva por gasto"})


@lib.handle_fb_error
def cmd_delivery(args):
    """Estimativa de entrega (delivery_estimate): público mensal e diário e curva por gasto."""
    lib.init_api(quiet=True)
    from facebook_business.adobjects.adaccount import AdAccount
    conta, spec = _conta_e_spec(args)
    params = {"targeting_spec": spec, "optimization_goal": args.optimization_goal}
    if args.daily_budget:
        params["daily_budget"] = args.daily_budget
    if args.lifetime_budget:
        params["lifetime_budget"] = args.lifetime_budget
    est = _primeiro(AdAccount(conta).get_delivery_estimate(params=params))
    lib.print_json({"ok": True, "conta": conta, "objetivo": args.optimization_goal,
                    "publico_mensal": {"minimo": est.get("estimate_mau_lower_bound"), "maximo": est.get("estimate_mau_upper_bound")},
                    "publico_diario": est.get("estimate_dau"), "pronta": est.get("estimate_ready"), "estimativa": est})


@lib.handle_fb_error
def cmd_describe(args):
    """Descreve um spec em frases, como o Gerenciador mostra."""
    lib.init_api(quiet=True)
    from facebook_business.adobjects.adaccount import AdAccount
    conta, spec = _conta_e_spec(args)
    r = _primeiro(AdAccount(conta).get_targeting_sentence_lines(params={"targeting_spec": spec}))
    linhas = r.get("targetingsentencelines") or []
    lib.print_json({"ok": True, "conta": conta, "descricao": _linhas_texto(linhas), "linhas": linhas})


# ---------------------------------------------------------------------------
# Auditoria de um conjunto contra as regras da casa
# ---------------------------------------------------------------------------

def _raio_km(raio, unidade):
    r = float(raio)
    return round(r * MILHA_EM_KM, 2) if (unidade or "mile") == "mile" else round(r, 2)


def _raios(geo):
    """Cada localização com raio (custom_locations, cities, places), com o raio em km."""
    out = []
    for chave, tipo in TIPO_GEO.items():
        for loc in (geo or {}).get(chave) or []:
            if not isinstance(loc, dict) or loc.get("radius") in (None, "", 0, "0"):
                continue
            nome = loc.get("name") or loc.get("address_string")
            if not nome:
                nome = f"{loc.get('latitude')},{loc.get('longitude')}" if loc.get("latitude") is not None else str(loc.get("key"))
            out.append({"tipo": tipo, "nome": nome, "raio_km": _raio_km(loc["radius"], loc.get("distance_unit")),
                        "raio_original": f"{loc['radius']} {loc.get('distance_unit') or 'mile'}"})
    return out


def _nomes(lista):
    return [str(x.get("name") or x.get("key") or x.get("id")) for x in (lista or []) if isinstance(x, dict)]


def _inteiro(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _resumo_targeting(t):
    """Resumo legível do targeting: idade, gênero, locais, públicos, interesses, plataformas."""
    geo = t.get("geo_locations") or {}
    locais = []
    for chave in CHAVES_GEO:
        for loc in geo.get(chave) or []:
            nome = (loc.get("name") or loc.get("address_string") or loc.get("key")) if isinstance(loc, dict) else loc
            locais.append(f"{chave}: {nome}")
    interesses = []
    for bloco in t.get("flexible_spec") or []:
        for tipo, valores in (bloco or {}).items():
            interesses.extend(f"{tipo}: {n}" for n in _nomes(valores))
    for tipo in ("interests", "behaviors"):
        interesses.extend(f"{tipo}: {n}" for n in _nomes(t.get(tipo)))
    exclusoes = [f"{tipo}: {n}" for tipo, valores in (t.get("exclusions") or {}).items() for n in _nomes(valores)]
    exclusoes += [f"custom_audiences: {n}" for n in _nomes(t.get("excluded_custom_audiences"))]
    generos = sorted(_inteiro(g) for g in (t.get("genders") or []) if _inteiro(g))
    genero = {(): "todos", (1,): "homens", (2,): "mulheres"}.get(tuple(generos), "todos")
    ta = t.get("targeting_automation")
    return {
        "idade": f"{t.get('age_min', '?')} a {t.get('age_max', '?')}",
        "genero": genero,
        "localizacoes": locais,
        "tipos_de_presenca": geo.get("location_types"),
        "publicos_personalizados": _nomes(t.get("custom_audiences")),
        "interesses_e_comportamentos": interesses,
        "exclusoes": exclusoes,
        "plataformas": t.get("publisher_platforms") or "automaticas (todas)",
        "posicoes_instagram": t.get("instagram_positions"),
        "posicoes_facebook": t.get("facebook_positions"),
        "dispositivos": t.get("device_platforms"),
        "advantage_audience": ta.get("advantage_audience") if isinstance(ta, dict) else None,
    }


def _alertas_da_casa(t, raio_maximo):
    """Alertas (fogem da regra) e avisos (merecem olhar) sobre o targeting."""
    alertas, avisos = [], []
    plat = t.get("publisher_platforms")
    if not plat:
        alertas.append("Posicionamentos automáticos (publisher_platforms ausente): a entrega inclui Facebook, "
                       "Audience Network e Messenger. A casa entrega só no Instagram.")
    else:
        fora = [p for p in plat if p in PLATAFORMAS_FORA_DA_CASA]
        if fora:
            alertas.append(f"Entrega ligada em {', '.join(fora)} (publisher_platforms). A casa entrega só no Instagram.")
    raios = _raios(t.get("geo_locations"))
    for r in raios:
        if r["raio_km"] > raio_maximo:
            alertas.append(f"Raio de {r['raio_km']} km em {r['nome']} ({r['tipo']}) passa do máximo de {raio_maximo:g} km. Nunca ampliar raio.")
    ta = t.get("targeting_automation")
    adv = _inteiro(ta.get("advantage_audience")) if isinstance(ta, dict) else None
    if adv is None:
        alertas.append("targeting_automation.advantage_audience ausente: a Meta exige 0 ou 1 e, sem o campo, pode ligar o "
                       "público Advantage+ e entregar fora do público definido. Ao editar o conjunto via API, enviar o valor.")
    age_min = _inteiro(t.get("age_min"))
    if adv == 1 and age_min is not None and age_min > 25:
        avisos.append(f"age_min {age_min} com público Advantage+ ligado: a Meta trata a idade como sugestão e pode entregar abaixo de {age_min} anos.")
    return alertas, avisos, raios


@lib.handle_fb_error
def cmd_auditar(args):
    """Lê o targeting de um conjunto e aponta o que foge das regras da casa."""
    lib.init_api(quiet=True)
    d = _ler_adset(args.adset, ["id", "name", "effective_status", "account_id", "campaign_id", "optimization_goal",
                                "destination_type", "promoted_object", "targeting", "targetingsentencelines"])
    t = d.get("targeting") or {}
    alertas, avisos, raios = _alertas_da_casa(t, args.raio_maximo)
    linhas = (d.get("targetingsentencelines") or {}).get("targetingsentencelines") or []
    lib.print_json({
        "ok": True,
        "conjunto": {"id": d.get("id"), "nome": d.get("name"), "status": d.get("effective_status"),
                     "conta": f"act_{d.get('account_id')}", "campanha": d.get("campaign_id"),
                     "objetivo": d.get("optimization_goal"), "destino": d.get("destination_type"),
                     "promoted_object": d.get("promoted_object")},
        "alertas": alertas,
        "avisos": avisos,
        "raio_maximo_km": args.raio_maximo,
        "raios": raios,
        "resumo": _resumo_targeting(t),
        "descricao": _linhas_texto(linhas),
        "targeting": t,
    })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Segmentação Meta Ads (só leitura): busca, validação, estimativa e auditoria de público")
    sub = p.add_subparsers(dest="cmd", required=True)

    def locale(s):
        s.add_argument("--locale", default=LOCALE_PADRAO, help=f"Idioma dos nomes (padrão {LOCALE_PADRAO})")

    def limite(s, padrao, extra=""):
        s.add_argument("--limit", type=int, default=padrao, help=f"Máximo de resultados (padrão {padrao or 'todos'}){extra}")

    def origem_spec(s):
        lib.add_target_args(s)
        s.add_argument("--spec", help="Segmentação (targeting) em JSON")
        s.add_argument("--spec-file", help="Arquivo com a segmentação em JSON")
        s.add_argument("--adset", help="Id de um conjunto: usa o targeting dele (a conta pode ser omitida)")

    s = sub.add_parser("interests", help="Busca interesses por palavra")
    s.add_argument("--q", required=True, help="Palavra ou trecho (ex: implante dentário)")
    limite(s, 25)
    locale(s)
    s.set_defaults(fn=cmd_interests)

    s = sub.add_parser("interest-suggestions", help="Interesses parecidos com os nomes dados")
    s.add_argument("--nomes", action="append", required=True,
                   help="Nomes de interesse como a busca devolveu, separados por vírgula (pode repetir a opção)")
    limite(s, 25)
    locale(s)
    s.set_defaults(fn=cmd_interest_suggestions)

    s = sub.add_parser("behaviors", help="Comportamentos disponíveis")
    s.add_argument("--q", help="Filtra por trecho do nome, descrição ou caminho (local)")
    limite(s, None, " (corte local)")
    locale(s)
    s.set_defaults(fn=cmd_behaviors)

    s = sub.add_parser("demographics", help="Dados demográficos disponíveis")
    s.add_argument("--q", help="Filtra por trecho do nome, descrição ou caminho (local)")
    limite(s, None, " (corte local)")
    locale(s)
    s.set_defaults(fn=cmd_demographics)

    s = sub.add_parser("geolocations", help="Busca cidade, bairro, região, CEP etc.")
    s.add_argument("--q", required=True, help="Nome ou trecho (ex: São Carlos, Moema)")
    s.add_argument("--types", default=TIPOS_GEO_PADRAO,
                   help=f"Tipos separados por vírgula: country,region,city,neighborhood,subcity,zip,geo_market (padrão {TIPOS_GEO_PADRAO})")
    s.add_argument("--country", default=PAIS_PADRAO, help=f"País (padrão {PAIS_PADRAO}; 'todos' para não filtrar)")
    limite(s, 25)
    locale(s)
    s.set_defaults(fn=cmd_geolocations)

    s = sub.add_parser("validate", help="Confere se interesses e comportamentos de um spec ainda existem")
    origem_spec(s)
    s.add_argument("--ids", help="Alternativa ao spec: ids separados por vírgula")
    s.add_argument("--tipo", default="interests", help="Tipo dos ids de --ids (padrão interests; ex: behaviors)")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("reach", help="Público estimado de um spec (reachestimate, endpoint antigo)")
    origem_spec(s)
    s.add_argument("--optimization-goal", help="Objetivo de otimização (opcional)")
    s.set_defaults(fn=cmd_reach)

    s = sub.add_parser("delivery", help="Estimativa de entrega de um spec (delivery_estimate)")
    origem_spec(s)
    s.add_argument("--optimization-goal", default=OBJETIVO_PADRAO, help=f"Objetivo de otimização (padrão {OBJETIVO_PADRAO})")
    s.add_argument("--daily-budget", type=int, help="Orçamento diário em centavos (R$ 50 = 5000)")
    s.add_argument("--lifetime-budget", type=int, help="Orçamento total em centavos")
    s.set_defaults(fn=cmd_delivery)

    s = sub.add_parser("describe", help="Descreve um spec em frases, como no Gerenciador")
    origem_spec(s)
    s.set_defaults(fn=cmd_describe)

    s = sub.add_parser("auditar", help="Audita o targeting de um conjunto contra as regras da casa")
    s.add_argument("--adset", required=True, help="Id do conjunto de anúncios")
    s.add_argument("--raio-maximo", type=float, default=RAIO_MAXIMO_KM, help=f"Raio máximo aceito, em km (padrão {RAIO_MAXIMO_KM:g})")
    s.set_defaults(fn=cmd_auditar)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
