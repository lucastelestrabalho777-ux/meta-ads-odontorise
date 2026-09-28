#!/usr/bin/env python3
"""
meta-ads-odontorise: subir campanha de captação via WhatsApp (escrita com trava).

Tudo nasce PAUSED. Nenhum subcomando envia nada sem --confirmo, que o Claude só usa
depois do OK explícito do gestor. Sem --confirmo o script mostra o que enviaria (ensaio).
Toda escrita fica registrada em ~/OdontoRise/meta-ads/auditoria.jsonl.

Subcomandos:
  campanha       --cliente/--account --data DD/MM [--sufixo "texto"]
  conjunto       --cliente/--account --campanha ID --nome "..." --page-id ID --daily-budget CENTAVOS
                 --targeting '{...}' [--advantage-audience 0|1] [--raio-maximo 10] [--start "AAAA-MM-DD HH:MM"]
  criativo-post  --cliente/--account --nome "..." --media-id ID --instagram-user-id ID
                 (--welcome-from-creative ID | --welcome-json '{...}')
  anuncio        --cliente/--account --conjunto ID --criativo ID --nome "..."
  captacao       fluxo completo (campanha + conjunto + criativo de post + anúncio) com os mesmos argumentos

Padrão da casa: references/padroes-campanha.md. Regras: references/regras-da-casa.md.
"""

import argparse
import json
import os
import sys
from datetime import date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

PLATAFORMAS_PROIBIDAS = {"facebook", "audience_network", "messenger"}
POSICOES_IG = ["stream", "story", "reels", "explore", "explore_home"]
RECURSOS_OPT_OUT = ["advantage_plus_creative", "image_touchups", "carousel_to_video", "text_optimizations",
                    "inline_comment", "image_brightness_and_contrast", "enhance_cta", "image_templates",
                    "video_auto_crop", "add_text_overlay", "site_extensions", "image_uncrop", "adapt_to_placement"]
RAIO_PADRAO_KM = 10.0
MAX_CARTOES_CARROSSEL = 10
CTA_WHATSAPP = {"type": "WHATSAPP_MESSAGE", "value": {"app_destination": "WHATSAPP", "link": "https://api.whatsapp.com/send"}}
NOME_CAMPANHA = "[Odontorise] [Vendas] Captação de Leads - {data}"


def _quem():
    ok, d = lib.graph_get("me", params={"fields": "name"})
    return d.get("name") if ok else None


def _saida_ensaio(payloads):
    lib.print_json({"ok": False, "ensaio": True, "enviaria": payloads,
                    "acao": "nada foi enviado. Depois do OK do gestor, repetir com --confirmo"})
    sys.exit(1)


def _falha(msg, extra=None):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if extra:
        out.update(extra)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    sys.exit(1)


def _post(acct, endpoint, payload, acao, resumo, quem):
    ok, d = lib.graph_post(f"{acct}/{endpoint}", data=payload)
    if not ok:
        _falha(f"a Meta recusou {acao}: {d.get('erro')}", {"code": d.get("code"), "subcode": d.get("subcode"),
                                                          "hint": d.get("hint"), "detalhe": d.get("detalhe"), "fbtrace_id": d.get("fbtrace_id")})
    lib.auditar(acao, acct, resumo, ids={"id": d.get("id")}, quem=quem)
    return d


# ---------------------------------------------------------------------------
# Montagem dos payloads (sem enviar)
# ---------------------------------------------------------------------------

def payload_campanha(a):
    data = a.data or date.today().strftime("%d/%m")
    nome = NOME_CAMPANHA.format(data=data) + (f" {a.sufixo}" if a.sufixo else "")
    return {"name": nome, "objective": "OUTCOME_SALES", "status": "PAUSED", "special_ad_categories": [],
            "is_adset_budget_sharing_enabled": False}


def raio_em_uso(acct):
    """Maior raio (km) já usado nos conjuntos ativos da conta: é o teto da regra 'não ampliar'."""
    maior = 0.0
    ok, d = lib.graph_get(f"{acct}/adsets", params={"fields": "targeting", "effective_status": json.dumps(["ACTIVE"]), "limit": 100})
    if not ok:
        return None
    for s in d.get("data", []):
        g = (s.get("targeting") or {}).get("geo_locations") or {}
        for loc in g.get("custom_locations", []) + g.get("cities", []):
            r = loc.get("radius")
            if r is not None:
                maior = max(maior, float(r))
    return maior or None


def checar_targeting(t, raio_maximo, acct=None):
    """Aplica as guardas da casa ao targeting. Devolve (targeting ajustado, avisos)."""
    avisos = []
    if raio_maximo is None:
        raio_maximo = raio_em_uso(acct) if acct else None
        if raio_maximo is None:
            raio_maximo = RAIO_PADRAO_KM
            avisos.append(f"conta sem raio em uso: teto de {RAIO_PADRAO_KM:g} km")
        else:
            avisos.append(f"teto de raio = {raio_maximo:g} km, o maior que a conta já usa")
    plats = set(t.get("publisher_platforms") or [])
    proibidas = plats & PLATAFORMAS_PROIBIDAS
    if proibidas:
        _falha(f"targeting inclui posicionamento proibido pela casa: {sorted(proibidas)}. Só Instagram.")
    if not plats:
        t["publisher_platforms"] = ["instagram"]
        avisos.append("publisher_platforms ausente: definido como só Instagram")
    if "instagram_positions" not in t:
        t["instagram_positions"] = list(POSICOES_IG)
        avisos.append("instagram_positions ausente: feed, stories, reels, explore")
    pos = t.get("instagram_positions") or []
    if "explore_home" in pos and "explore" not in pos:
        pos.append("explore")
        avisos.append("explore incluído (explore_home exige explore)")
    for loc in (t.get("geo_locations") or {}).get("custom_locations", []) + (t.get("geo_locations") or {}).get("cities", []):
        r = loc.get("radius")
        if r is not None and float(r) > raio_maximo:
            _falha(f"raio de {r} km acima do máximo permitido ({raio_maximo} km). A casa não amplia raio.")
    if "targeting_automation" not in t:
        _falha("targeting sem targeting_automation.advantage_audience. Informe --advantage-audience 0 ou 1.")
    return t, avisos


def payload_conjunto(a, targeting):
    if a.daily_budget is None or a.daily_budget <= 0:
        _falha("--daily-budget em centavos é obrigatório (10000 = R$ 100,00)")
    p = {"name": a.nome, "campaign_id": a.campanha, "status": "PAUSED", "daily_budget": int(a.daily_budget),
         "billing_event": "IMPRESSIONS", "optimization_goal": "CONVERSATIONS", "destination_type": "WHATSAPP",
         "bid_strategy": "LOWEST_COST_WITHOUT_CAP", "promoted_object": {"page_id": a.page_id},
         "attribution_spec": [{"event_type": "CLICK_THROUGH", "window_days": 1}], "targeting": targeting}
    if a.start:
        p["start_time"] = a.start
    return p


def checar_post(media_id):
    """Post do Instagram: carrossel com mais de 10 cartões não vira anúncio (erro 105 da Meta)."""
    ok, d = lib.graph_get(media_id, params={"fields": "media_type,media_product_type"})
    if not ok:
        _falha(f"não consegui ler o post {media_id} ({d.get('erro')})", {"acao": "conferir o id da mídia e se a conta do Instagram é a do cliente"})
    if d.get("media_type") == "CAROUSEL_ALBUM":
        ok2, c = lib.graph_get(f"{media_id}/children", params={"fields": "id", "limit": 50})
        n = len(c.get("data", [])) if ok2 else None
        if n and n > MAX_CARTOES_CARROSSEL:
            _falha(f"o post é um carrossel com {n} cartões; a Meta aceita no máximo {MAX_CARTOES_CARROSSEL} num anúncio. Escolha outro post.")
    return d


def welcome_message(a):
    if a.welcome_json:
        return lib.parse_json_arg(a.welcome_json, "--welcome-json")
    if a.welcome_from_creative:
        ok, d = lib.graph_get(a.welcome_from_creative, params={"fields": "page_welcome_message"})
        if not ok or not d.get("page_welcome_message"):
            _falha(f"não consegui copiar a mensagem de boas-vindas do criativo {a.welcome_from_creative}")
        w = d["page_welcome_message"]
        return json.loads(w) if isinstance(w, str) else w
    return None


def payload_criativo_post(a, welcome):
    p = {"name": a.nome, "source_instagram_media_id": a.media_id, "instagram_user_id": a.instagram_user_id,
         "call_to_action": CTA_WHATSAPP,
         "degrees_of_freedom_spec": {"creative_features_spec": {r: {"enroll_status": "OPT_OUT"} for r in RECURSOS_OPT_OUT}}}
    if welcome:
        p["page_welcome_message"] = welcome
    return p


def payload_anuncio(a, conjunto_id, criativo_id):
    return {"name": a.nome, "adset_id": conjunto_id, "creative": {"creative_id": criativo_id}, "status": "PAUSED"}


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

@lib.handle_fb_error
def cmd_campanha(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    p = payload_campanha(a)
    if not a.confirmo:
        _saida_ensaio({"conta": acct, "campanha": p})
    quem = _quem()
    d = _post(acct, "campaigns", p, "criar campanha", p["name"], quem)
    lib.print_json({"ok": True, "conta": acct, "campanha_id": d.get("id"), "nome": p["name"], "status": "PAUSED"})


@lib.handle_fb_error
def cmd_conjunto(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    t = lib.parse_json_arg(a.targeting, "--targeting") or {}
    if a.advantage_audience is not None:
        t["targeting_automation"] = {"advantage_audience": int(a.advantage_audience)}
    t, avisos = checar_targeting(t, a.raio_maximo, acct)
    p = payload_conjunto(a, t)
    if not a.confirmo:
        _saida_ensaio({"conta": acct, "conjunto": p, "avisos": avisos})
    quem = _quem()
    d = _post(acct, "adsets", p, "criar conjunto", f"{p['name']} (R$ {p['daily_budget']/100:.2f}/dia)", quem)
    lib.print_json({"ok": True, "conta": acct, "conjunto_id": d.get("id"), "nome": p["name"], "status": "PAUSED", "avisos": avisos})


@lib.handle_fb_error
def cmd_criativo_post(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    checar_post(a.media_id)
    w = welcome_message(a)
    p = payload_criativo_post(a, w)
    if not a.confirmo:
        _saida_ensaio({"conta": acct, "criativo": p, "aviso": None if w else "sem page_welcome_message: informe --welcome-from-creative ou --welcome-json"})
    quem = _quem()
    d = _post(acct, "adcreatives", p, "criar criativo", f"{p['name']} (post {a.media_id})", quem)
    lib.print_json({"ok": True, "conta": acct, "criativo_id": d.get("id"), "nome": p["name"]})


@lib.handle_fb_error
def cmd_anuncio(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    p = payload_anuncio(a, a.conjunto, a.criativo)
    if not a.confirmo:
        _saida_ensaio({"conta": acct, "anuncio": p})
    quem = _quem()
    d = _post(acct, "ads", p, "criar anúncio", p["name"], quem)
    lib.print_json({"ok": True, "conta": acct, "anuncio_id": d.get("id"), "nome": p["name"], "status": "PAUSED",
                    "proximo_passo": f"validar: read.py ad --id {d.get('id')} e read.py preview --creative {a.criativo} --format all"})


@lib.handle_fb_error
def cmd_captacao(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    t = lib.parse_json_arg(a.targeting, "--targeting") or {}
    if a.advantage_audience is not None:
        t["targeting_automation"] = {"advantage_audience": int(a.advantage_audience)}
    t, avisos = checar_targeting(t, a.raio_maximo, acct)
    checar_post(a.media_id)
    w = welcome_message(a)
    pc = payload_campanha(a)
    a.campanha = "<id da campanha criada>"
    ps = payload_conjunto(a, t)
    pcr = payload_criativo_post(a, w)
    pa = payload_anuncio(a, "<id do conjunto criado>", "<id do criativo criado>")
    if not a.confirmo:
        _saida_ensaio({"conta": acct, "campanha": pc, "conjunto": ps, "criativo": pcr, "anuncio": pa, "avisos": avisos,
                       "aviso_welcome": None if w else "sem page_welcome_message"})
    quem = _quem()
    camp = _post(acct, "campaigns", pc, "criar campanha", pc["name"], quem)
    lib.safe_delay(1)
    ps["campaign_id"] = camp["id"]
    adset = _post(acct, "adsets", ps, "criar conjunto", f"{ps['name']} (R$ {ps['daily_budget']/100:.2f}/dia)", quem)
    lib.safe_delay(1)
    cr = _post(acct, "adcreatives", pcr, "criar criativo", f"{pcr['name']} (post {a.media_id})", quem)
    lib.safe_delay(1)
    ad = _post(acct, "ads", payload_anuncio(a, adset["id"], cr["id"]), "criar anúncio", a.nome, quem)
    lib.print_json({"ok": True, "conta": acct, "campanha_id": camp["id"], "conjunto_id": adset["id"],
                    "criativo_id": cr["id"], "anuncio_id": ad["id"], "status": "PAUSED (tudo)", "avisos": avisos,
                    "proximo_passo": f"validar: read.py ad --id {ad['id']}; read.py preview --creative {cr['id']} --format all; targeting.py auditar --adset {adset['id']}"})


def main():
    p = argparse.ArgumentParser(description="Subir campanha de captação via WhatsApp (tudo pausado)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def comum(s):
        lib.add_target_args(s)
        s.add_argument("--confirmo", action="store_true", help="enviar de verdade (só depois do OK do gestor)")

    s = sub.add_parser("campanha"); comum(s); s.add_argument("--data"); s.add_argument("--sufixo"); s.set_defaults(fn=cmd_campanha)

    def args_conjunto(s):
        s.add_argument("--nome", required=True); s.add_argument("--page-id", required=True)
        s.add_argument("--daily-budget", type=int, required=True, help="centavos (10000 = R$ 100,00)")
        s.add_argument("--targeting", required=True, help="JSON"); s.add_argument("--advantage-audience", type=int, choices=[0, 1])
        s.add_argument("--raio-maximo", type=float, default=None, help="teto em km; padrão: o maior raio que a conta já usa"); s.add_argument("--start")

    s = sub.add_parser("conjunto"); comum(s); s.add_argument("--campanha", required=True); args_conjunto(s); s.set_defaults(fn=cmd_conjunto)

    def args_criativo(s):
        s.add_argument("--media-id", required=True); s.add_argument("--instagram-user-id", required=True)
        s.add_argument("--welcome-from-creative"); s.add_argument("--welcome-json")

    s = sub.add_parser("criativo-post"); comum(s); s.add_argument("--nome", required=True); args_criativo(s); s.set_defaults(fn=cmd_criativo_post)
    s = sub.add_parser("anuncio"); comum(s); s.add_argument("--conjunto", required=True); s.add_argument("--criativo", required=True); s.add_argument("--nome", required=True); s.set_defaults(fn=cmd_anuncio)
    s = sub.add_parser("captacao"); comum(s); s.add_argument("--data"); s.add_argument("--sufixo"); args_conjunto(s); args_criativo(s); s.set_defaults(fn=cmd_captacao)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
