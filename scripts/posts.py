#!/usr/bin/env python3
"""
meta-ads-odontorise: posts orgânicos do Instagram do cliente (só leitura).

Subcomandos:
  listar --cliente X [--dias 7] [--radar 30] [--sem-insights] [--radar-insights]
      Descobre o Instagram pela conta de anúncio, lista os posts da janela (últimos N dias) com
      legenda, formato, data, link, capa, curtidas, comentários, alcance, salvos, compartilhamentos
      e taxa de engajamento, e marca os que JÁ viraram anúncio na conta. O radar traz os posts de
      N+1 até 30 dias atrás que ainda não são anúncio, para recuperar o que ficou de fora.
  post --cliente X --id MEDIA_ID
      Um post com os mesmos campos, os cartões (se carrossel) e os anúncios já feitos dele.

Só GET. JSON no stdout. Classificar é trabalho do Claude: paciente final sobe; mentoria, conteúdo
pessoal, institucional ou política não sobe. Para subir: create.py anuncio-post.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import instagram  # noqa: E402

COMO_CLASSIFICAR = ("paciente final (caso, tratamento, benefício, dúvida de paciente, convite para avaliação, depoimento) sobe; "
                    "mentoria, conteúdo pessoal, institucional ou política não sobe. Em dúvida, abrir a capa e o link.")


def _falha(msg, extra=None):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if extra:
        out.update(extra)
    lib.print_json(out)
    sys.exit(1)


def _instagram_do_cliente(acct):
    ok, ig = instagram.descobrir(acct)
    if not ok:
        _falha(f"não achei o Instagram ligado à conta {acct} ({ig.get('erro')})", {"code": ig.get("code"), "acao": ig.get("acao")})
    return ig


def _ja_anuncios(acct):
    ok, por = instagram.anuncios_por_post(acct)
    if ok:
        return por, None
    return {}, f"não consegui listar os anúncios da conta para conferir quais posts já são anúncio ({por.get('erro')})"


@lib.handle_fb_error
def cmd_listar(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    cliente = lib.exigir_no_cadastro(acct)
    ig = _instagram_do_cliente(acct)
    radar_dias = max(a.radar, a.dias)
    ok, media = instagram.listar_posts(ig["instagram_user_id"], radar_dias)
    if not ok:
        _falha(f"não consegui ler os posts de @{ig.get('username')} ({media.get('erro')})",
               {"code": media.get("code"),
                "acao": "o token precisa de instagram_basic e instagram_manage_insights (setup.py confere) e o Instagram precisa estar ligado à Página do cliente"})
    por, aviso = _ja_anuncios(acct)
    hoje = datetime.now(timezone.utc)
    janela, radar = [], []
    for m in media:
        q = instagram._dt(m.get("timestamp"))
        dias = (hoje - q).days if q else None
        na_janela = dias is not None and dias < a.dias
        com_insights = (na_janela and not a.sem_insights) or (not na_janela and a.radar_insights)
        r = instagram.resumo_post(m, instagram.insights(m) if com_insights else None, hoje)
        r["ja_e_anuncio"] = por.get(m.get("id"), [])
        (janela if na_janela else radar).append(r)
    com_taxa = [p for p in janela if p.get("taxa_engajamento_pct") is not None]
    for i, p in enumerate(sorted(com_taxa, key=lambda p: -p["taxa_engajamento_pct"]), 1):
        p["posicao_engajamento"] = i
    radar_livres = [p for p in radar if not p["ja_e_anuncio"]]
    out = {"ok": True, "cliente": cliente.get("nome"), "conta": acct, "instagram": ig,
           "janela_dias": a.dias, "radar_dias": radar_dias,
           "resumo": {"posts_na_janela": len(janela), "ja_anuncio_na_janela": sum(1 for p in janela if p["ja_e_anuncio"]),
                      "posts_no_radar": len(radar), "radar_sem_anuncio": len(radar_livres),
                      "posts_com_anuncio_na_conta": len(por)},
           "como_classificar": COMO_CLASSIFICAR,
           "posts": janela, "radar": radar_livres,
           "proximo_passo": "create.py anuncio-post --cliente X --conjunto <id> --media-id <id> --nome \"...\" (ensaio; --confirmo só com OK do gestor)"}
    if aviso:
        out["aviso"] = aviso
    lib.print_json(out)


@lib.handle_fb_error
def cmd_post(a):
    lib.init_api(quiet=True)
    acct = lib.resolve_target(a)
    ok, m = lib.graph_get(a.id, {"fields": instagram.CAMPOS_MEDIA + ",owner"})
    if not ok:
        _falha(f"não consegui ler o post {a.id} ({m.get('erro')})", {"code": m.get("code"), "acao": "conferir o id (posts.py listar) e se o post é do Instagram do cliente"})
    r = instagram.resumo_post(m, instagram.insights(m))
    r["dono_instagram_user_id"] = (m.get("owner") or {}).get("id")
    if m.get("media_type") == "CAROUSEL_ALBUM":
        ok2, c = lib.graph_get(f"{a.id}/children", {"fields": "id,media_type,media_url,thumbnail_url", "limit": 50})
        r["cartoes"] = [{"id": x.get("id"), "tipo": x.get("media_type"), "capa": x.get("thumbnail_url") or x.get("media_url")} for x in c.get("data", [])] if ok2 else None
    por, aviso = _ja_anuncios(acct)
    r["ja_e_anuncio"] = por.get(a.id, [])
    out = {"ok": True, "conta": acct, "post": r, "como_classificar": COMO_CLASSIFICAR}
    if aviso:
        out["aviso"] = aviso
    lib.print_json(out)


def main():
    p = argparse.ArgumentParser(description="Posts orgânicos do Instagram do cliente (só leitura; só contas do seu cadastro)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("listar", help="posts da janela com métricas e marcação de quem já é anúncio")
    lib.add_target_args(s)
    s.add_argument("--dias", type=int, default=7, help="janela de candidatos (padrão 7)")
    s.add_argument("--radar", type=int, default=30, help="até quantos dias atrás olhar para o radar (padrão 30)")
    s.add_argument("--sem-insights", action="store_true", help="não buscar alcance, salvos e compartilhamentos (mais rápido)")
    s.add_argument("--radar-insights", action="store_true", help="buscar insights também dos posts do radar")
    s.set_defaults(fn=cmd_listar)
    s = sub.add_parser("post", help="um post pelo id da mídia")
    lib.add_target_args(s)
    s.add_argument("--id", required=True, help="id da mídia (campo id de posts.py listar)")
    s.set_defaults(fn=cmd_post)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
