"""
Instagram do cliente, só leitura: conta ligada à conta de anúncio, posts com métricas e quais
posts já viraram anúncio. Usado por posts.py (listar, post) e create.py (anuncio-post).
"""
from datetime import datetime, timezone, timedelta

from . import graph_get

CAMPOS_MEDIA = ("id,caption,timestamp,permalink,media_type,media_product_type,thumbnail_url,media_url,"
                "like_count,comments_count")
METRICAS_BASE = "reach,saved,shares,total_interactions"
METRICAS_REELS = METRICAS_BASE + ",ig_reels_avg_watch_time"
PAGINA_MEDIA = 50
MAX_PAGINAS_MEDIA = 6            # até 300 posts
PAGINA_ADS = 200
MAX_PAGINAS_ADS = 10             # até 2000 anúncios na conferência de "já é anúncio"


def descobrir(acct):
    """
    Instagram ligado à conta de anúncio. Primeiro pela Página promovida (traz page_id),
    depois pela lista de contas do Instagram da conta. Devolve (ok, dado).
    """
    ok, d = graph_get(f"{acct}/promote_pages", {
        "fields": "id,name,instagram_business_account{id,username},connected_instagram_account{id,username}", "limit": 25})
    if ok:
        for p in d.get("data", []):
            ig = p.get("instagram_business_account") or p.get("connected_instagram_account")
            if ig and ig.get("id"):
                return True, {"instagram_user_id": ig["id"], "username": ig.get("username"),
                              "page_id": p.get("id"), "page_nome": p.get("name"), "origem": "página promovida"}
    ok2, d2 = graph_get(f"{acct}/instagram_accounts", {"fields": "id,username", "limit": 25})
    if ok2 and d2.get("data"):
        ig = d2["data"][0]
        return True, {"instagram_user_id": ig["id"], "username": ig.get("username"),
                      "page_id": None, "page_nome": None, "origem": "instagram_accounts"}
    if not ok and not ok2:
        erro = d2.get("erro") or d.get("erro")
    else:
        erro = "nenhum Instagram ligado à conta de anúncio"
    return False, {"erro": erro, "code": (d2 if not ok2 else d).get("code"),
                   "acao": "ligar o Instagram do cliente à Página na Business Manager, ou conferir se a conta está atribuída a você"}


def _dt(ts):
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
    except (TypeError, ValueError):
        return None


def listar_posts(ig_id, dias):
    """Posts dos últimos `dias` dias (UTC), do mais novo ao mais antigo. Para de paginar ao passar da janela."""
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    posts, after, paginas = [], None, 0
    while True:
        params = {"fields": CAMPOS_MEDIA, "limit": PAGINA_MEDIA}
        if after:
            params["after"] = after
        ok, d = graph_get(f"{ig_id}/media", params)
        if not ok:
            return False, d
        paginas += 1
        passou = False
        for m in d.get("data", []):
            q = _dt(m.get("timestamp"))
            if q and q < corte:
                passou = True
                break
            posts.append(m)
        paging = d.get("paging", {})
        after = paging.get("cursors", {}).get("after")
        if passou or not after or "next" not in paging or paginas >= MAX_PAGINAS_MEDIA:
            return True, posts


def formato(m):
    if m.get("media_product_type") == "REELS":
        return "reel"
    if m.get("media_type") == "CAROUSEL_ALBUM":
        return "carrossel"
    if m.get("media_type") == "VIDEO":
        return "video"
    return "imagem"


def insights(m):
    """Alcance, salvos, compartilhamentos, interações (e tempo médio assistido no reel). {'erro': ...} quando a Meta não dá."""
    metricas = METRICAS_REELS if formato(m) == "reel" else METRICAS_BASE
    ok, d = graph_get(f"{m['id']}/insights", {"metric": metricas})
    if not ok and metricas != METRICAS_BASE:
        ok, d = graph_get(f"{m['id']}/insights", {"metric": METRICAS_BASE})
    if not ok:
        return {"erro": d.get("erro")}
    out = {}
    for item in d.get("data", []):
        vals = item.get("values") or []
        out[item.get("name")] = vals[0].get("value") if vals else None
    return out


def resumo_post(m, ins=None, hoje=None):
    """Campos que o Claude usa para classificar (legenda, capa, link) e ranquear (engajamento)."""
    hoje = hoje or datetime.now(timezone.utc)
    q = _dt(m.get("timestamp"))
    curtidas = m.get("like_count") or 0
    comentarios = m.get("comments_count") or 0
    r = {"id": m.get("id"), "data": q.strftime("%d/%m/%Y") if q else None, "dias_atras": (hoje - q).days if q else None,
         "formato": formato(m), "legenda": m.get("caption") or "", "link": m.get("permalink"),
         "capa": m.get("thumbnail_url") or (m.get("media_url") if m.get("media_type") in ("IMAGE", "CAROUSEL_ALBUM") else None),
         "curtidas": curtidas, "comentarios": comentarios}
    if ins is not None:
        if ins.get("erro"):
            r["insights_erro"] = ins["erro"]
        alcance = ins.get("reach")
        salvos = ins.get("saved") or 0
        comp = ins.get("shares") or 0
        r.update({"alcance": alcance, "salvos": salvos, "compartilhamentos": comp, "interacoes": ins.get("total_interactions"),
                  "taxa_engajamento_pct": round((curtidas + comentarios + salvos + comp) / alcance * 100, 2) if alcance else None})
        if ins.get("ig_reels_avg_watch_time") is not None:
            r["tempo_medio_assistido_s"] = round(ins["ig_reels_avg_watch_time"] / 1000, 1)
    return r


def anuncios_por_post(acct):
    """Dicionário media_id -> anúncios da conta feitos a partir desse post (qualquer status). Devolve (ok, dado)."""
    por, after, paginas = {}, None, 0
    while True:
        params = {"fields": "id,name,effective_status,created_time,adset_id,adset{name},"
                            "creative{id,effective_instagram_media_id,source_instagram_media_id}",
                  "limit": PAGINA_ADS}
        if after:
            params["after"] = after
        ok, d = graph_get(f"{acct}/ads", params)
        if not ok:
            return False, d
        paginas += 1
        for ad in d.get("data", []):
            cr = ad.get("creative") or {}
            for mid in {cr.get("effective_instagram_media_id"), cr.get("source_instagram_media_id")}:
                if mid:
                    por.setdefault(mid, []).append({
                        "anuncio_id": ad.get("id"), "nome": ad.get("name"), "status": ad.get("effective_status"),
                        "conjunto_id": ad.get("adset_id"), "conjunto": (ad.get("adset") or {}).get("name"),
                        "criado": (ad.get("created_time") or "")[:10]})
        paging = d.get("paging", {})
        after = paging.get("cursors", {}).get("after")
        if not after or "next" not in paging or paginas >= MAX_PAGINAS_ADS:
            return True, por
