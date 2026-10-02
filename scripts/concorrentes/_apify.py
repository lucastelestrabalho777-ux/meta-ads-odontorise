#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Credencial e chamadas ao Apify para a skill /raio-x-concorrentes (pacote meta-ads-odontorise).

Token em ~/OdontoRise/credentials/apify-odontorise.env, linha APIFY_TOKEN=... (override: variável ODR_APIFY_ENV).
Nunca vai na URL: segue no cabeçalho Authorization. Mensagens de erro nunca mostram o token.

  _apify.py checar      # confere arquivo, permissão e conta (GET /v2/users/me)
"""
import json, os, stat, sys, time, urllib.request, urllib.error

ENV = os.environ.get("ODR_APIFY_ENV") or os.path.expanduser("~/OdontoRise/credentials/apify-odontorise.env")
API = "https://api.apify.com/v2"
PLACEHOLDERS = ("COLE_", "SEU_", "SUA_", "xxx", "...")


def falha(msg, acao=None):
    print(json.dumps({"ok": False, "erro": msg, "acao": acao}, ensure_ascii=False)); sys.exit(1)


def token():
    if not os.path.exists(ENV):
        falha(f"arquivo de credencial do Apify não encontrado: {ENV}",
              "crie o arquivo com a linha APIFY_TOKEN=<token do console do Apify> (página Head do guia)")
    tok = None
    for linha in open(ENV, encoding="utf-8-sig"):
        linha = linha.strip()
        if linha.startswith("APIFY_TOKEN"):
            tok = linha.split("=", 1)[1].strip().strip("\"'")
    if not tok:
        falha(f"APIFY_TOKEN vazio em {ENV}", "cole o token na linha APIFY_TOKEN=")
    if any(p in tok for p in PLACEHOLDERS) or len(tok) < 20:
        falha("APIFY_TOKEN ainda é um valor de exemplo", "troque pelo token real do console do Apify (Settings, API & Integrations)")
    return tok


def permissao_ok():
    if os.name == "nt":
        return None
    return (os.stat(ENV).st_mode & 0o077) == 0


def _req(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {token()}",
                                                          "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "ignore")[:300]
        if e.code == 401: falha("Apify recusou o token (401)", "gere um token novo no console do Apify e troque no arquivo")
        if e.code == 402: falha("Apify sem crédito ou fatura em aberto (402)", "regularize a conta em console.apify.com/billing")
        falha(f"Apify respondeu HTTP {e.code}: {corpo}")
    except urllib.error.URLError as e:
        falha(f"sem conexão com o Apify: {e.reason}")


def roda_actor(actor, entrada, espera=5):
    """Roda um actor e devolve os itens do dataset. Token só no cabeçalho."""
    run = _req(f"{API}/acts/{actor}/runs", json.dumps(entrada).encode())["data"]
    while True:
        time.sleep(espera)
        r = _req(f"{API}/actor-runs/{run['id']}")["data"]
        if r["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    if r["status"] != "SUCCEEDED":
        falha(f"actor {actor} terminou com status {r['status']}", "abra o run no console do Apify para ver o motivo")
    return _req(f"{API}/datasets/{run['defaultDatasetId']}/items?clean=true")


def checar():
    tok = token()
    perm = permissao_ok()
    me = _req(f"{API}/users/me")["data"]
    print(json.dumps({"ok": True, "arquivo": ENV, "permissao_600": perm if perm is not None else "não conferida (Windows)",
                      "usuario": me.get("username"), "plano": (me.get("plan") or {}).get("id"),
                      "token": tok[:4] + "..." + tok[-3:]}, ensure_ascii=False))
    if perm is False:
        print("AVISO: rode chmod 600 no arquivo de credencial", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "checar":
        checar()
    else:
        print(__doc__)
