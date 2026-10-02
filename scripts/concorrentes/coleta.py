#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coleta na Biblioteca de Anuncios do Meta via Apify.

  coleta.py busca   termos.json   30  descoberta.json   # descoberta por palavra-chave
  coleta.py paginas paginas.json  150 coleta.json       # todos os ads ativos de cada pagina

termos.json  = ["botox brasilia", "dermatologista lago sul", ...]
paginas.json = ["https://www.facebook.com/handle/", "12345678901234", ...]
               id numerico vira view_all_page_id (use quando a URL de handle voltar vazia)
"""
import json, os, sys, time, urllib.parse, urllib.request

ACTOR = "apify~facebook-ads-scraper"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _apify


def token():
    return _apify.token()


def url_busca(termo, pais="BR"):
    return ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
            f"&country={pais}&q={urllib.parse.quote(termo)}"
            "&search_type=keyword_unordered&media_type=all")


def url_pagina(alvo, pais="BR"):
    alvo = str(alvo).strip()
    if alvo.startswith("http"):
        return alvo
    # id numerico -> URL de pagina da Biblioteca (mais confiavel que o handle)
    return ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
            f"&country={pais}&view_all_page_id={alvo}")


def roda(urls, limite, saida, tok):
    entrada = {"startUrls": [{"url": u} for u in urls],
               "resultsLimit": limite,
               "activeStatus": "active",
               "sorting": ""}          # so aceita "", total_impressions, relevancy_monthly_grouped
    run = _apify._req(f"{_apify.API}/acts/{ACTOR}/runs", json.dumps(entrada).encode())["data"]
    print("runId:", run["id"], flush=True)
    while True:
        time.sleep(15)
        st = _apify._req(f"{_apify.API}/actor-runs/{run['id']}")["data"]
        print(st["status"], st.get("stats", {}).get("runTimeSecs"), flush=True)
        if st["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    itens = _apify._req(f"{_apify.API}/datasets/{run['defaultDatasetId']}/items?clean=true")
    json.dump(itens, open(saida, "w"), ensure_ascii=False)
    print("itens:", len(itens))

    vazias = [i for i in itens if i.get("errorDescription") or i.get("totalCount") == 0]
    for v in vazias:
        print("  SEM ANUNCIO:", v.get("inputUrl") or v.get("url"), "|", v.get("errorDescription") or "totalCount=0")
    if vazias:
        print("  -> se a pagina anuncia mesmo, refaca com o page_id numerico (view_all_page_id)")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    modo, entrada, limite, saida = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    alvos = json.load(open(entrada))
    urls = [url_busca(a) for a in alvos] if modo == "busca" else [url_pagina(a) for a in alvos]
    roda(urls, limite, saida, token())
