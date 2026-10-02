#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mapeia as fichas do Google Meu Negocio na regiao e cruza com Instagram.

  gmn.py coleta  -15.7955 -47.9265 12 "dentista" "clínica odontológica"   > roda o scraper
  gmn.py filtra  gmn.json --categoria Dentist --lat -15.7955 --lng -47.9265     > filtra + distancia
  gmn.py insta   gmn_sel.json                                                      > acha @ e seguidores

Fluxo: coleta -> filtra -> escolher a selecao (perto + reputacao + quem anuncia) -> insta.
O casamento com quem anuncia e manual: editar RADAR no proprio json de selecao.
"""
import concurrent.futures, json, math, os, re, ssl, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _apify
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
RX_IG = re.compile(r"instagram\.com(?:%2F|\\?/)+([A-Za-z0-9_.]{2,40})")
BAD = {"p", "reel", "reels", "explore", "accounts", "stories", "instagram", "tv"}


def roda_actor(actor, entrada, saida):
    """Roda o actor pelo helper (token só no cabeçalho) e grava o dataset em `saida`, se houver."""
    itens = _apify.roda_actor(actor, entrada, espera=10)
    if saida:
        json.dump(itens, open(saida, "w"), ensure_ascii=False)
    print(f"{actor}: {len(itens)} itens", file=sys.stderr)
    return itens


def km(a, b):
    R, p = 6371, math.pi / 180
    dlat, dlon = (b[0] - a[0]) * p, (b[1] - a[1]) * p
    h = math.sin(dlat / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def coleta(lat, lng, raio, termos):
    return roda_actor("compass~crawler-google-places", {
        "searchStringsArray": termos,
        "customGeolocation": {"type": "Point", "coordinates": [lng, lat], "radiusKm": raio},
        "maxCrawledPlacesPerSearch": 140, "language": "pt-BR", "countryCode": "br",
        "skipClosedPlaces": True, "scrapePlaceDetailPage": False, "maxImages": 0, "maxReviews": 0,
    }, "gmn.json")


def filtra(arquivo, categoria, lat, lng, bairros=None):
    d = json.load(open(arquivo))
    sel, vistos = [], set()
    for x in d:
        cats = " ".join(x.get("categories") or []) + " " + (x.get("categoryName") or "")
        if categoria.lower() not in cats.lower(): continue
        if "veterin" in cats.lower(): continue          # dermatologia veterinaria polui a busca
        if bairros and (x.get("neighborhood") or "") not in bairros: continue
        chave = (x.get("title"), x.get("address"))
        if chave in vistos: continue
        vistos.add(chave)
        loc = x.get("location") or {}
        x["km"] = round(km((lat, lng), (loc.get("lat", 0), loc.get("lng", 0))), 1)
        sel.append(x)
    sel.sort(key=lambda x: x["km"])
    json.dump(sel, open("gmn_derm.json", "w"), ensure_ascii=False)
    print("fichas:", len(sel), "| ate 2km:", sum(1 for r in sel if r["km"] <= 2))
    return sel


def _busca_site(r):
    w = (r.get("website") or "").rstrip("/")
    if "instagram.com" in w.lower():
        m = RX_IG.search(w)
        if m and m.group(1).lower() not in BAD: return m.group(1)
    if not w.startswith("http"): return None
    for suf in ("", "/contato", "/contato/", "/sobre"):
        try:
            req = urllib.request.Request(w + suf, headers={"User-Agent": "Mozilla/5.0"})
            h = urllib.request.urlopen(req, timeout=18, context=CTX).read().decode("utf-8", "ignore")
        except Exception:
            continue
        for m in RX_IG.finditer(h):
            if m.group(1).lower() not in BAD: return m.group(1)
    return None


def insta(arquivo):
    sel = json.load(open(arquivo))
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for r, ig in zip(sel, ex.map(_busca_site, sel)):
            r["ig"] = r.get("ig") or ig
    falta = [r for r in sel if not r.get("ig")]
    if falta:  # 2a tentativa: busca no Google
        qs = [f'{r["title"].split("|")[0].strip()} instagram' for r in falta]
        itens = roda_actor("apify~google-search-scraper", {
            "queries": "\n".join(qs), "resultsPerPage": 10, "maxPagesPerQuery": 1,
            "countryCode": "br", "languageCode": "pt-BR"}, None)
        mapa = {}
        for it in itens:
            q = it.get("searchQuery", {}).get("term", "")
            for res in (it.get("organicResults") or []):
                m = RX_IG.search(res.get("url") or "")
                if m and m.group(1).lower() not in BAD:
                    mapa.setdefault(q, m.group(1)); break
        for r, q in zip(falta, qs):
            r["ig"] = mapa.get(q)
    users = sorted({r["ig"] for r in sel if r.get("ig")})
    perfis = roda_actor("apify~instagram-profile-scraper", {"usernames": users}, None) if users else []
    idx = {p["username"].lower(): p for p in perfis}
    for r in sel:
        p = idx.get((r.get("ig") or "").lower())
        seg = int(p.get("followersCount") or 0) if p else 0
        # perfil com quase nenhum seguidor = handle provavelmente errado, nao publicar numero incerto
        r["seg"] = seg if seg >= 100 else None
        r["bio"] = (p.get("biography") or "")[:140] if p else ""
    json.dump(sel, open(arquivo, "w"), ensure_ascii=False)
    print("com Instagram confirmado:", sum(1 for r in sel if r.get("seg")), "de", len(sel))
    for r in sorted(sel, key=lambda x: -(x["seg"] or 0)):
        print(f"  {r['km']:>5}km {str(r.get('totalScore') or '-'):>4} ({r.get('reviewsCount') or 0:>4}) "
              f"{str(r['seg'] or '-'):>9}  @{r.get('ig') or '-'} | {r['title'][:42]}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "coleta":
        coleta(float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5:])
    elif cmd == "filtra":
        a = sys.argv
        filtra(a[2], a[a.index("--categoria") + 1], float(a[a.index("--lat") + 1]), float(a[a.index("--lng") + 1]))
    elif cmd == "insta":
        insta(sys.argv[2])
    else:
        raise SystemExit(__doc__)
