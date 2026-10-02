#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baixa as capas dos anuncios. RODAR NA MESMA SESSAO DA COLETA: as URLs do fbcdn expiram.

  thumbs.py anuncios.json thumbs/     # baixa originais e gera thumbs/mini/ (300px, p/ o documento)
"""
import concurrent.futures, json, os, subprocess, sys, urllib.request

anuncios, dest = sys.argv[1], sys.argv[2].rstrip("/")
mini = f"{dest}/mini"
os.makedirs(mini, exist_ok=True)
d = json.load(open(anuncios))


def baixa(a):
    u = a.get("thumb")
    if not u: return None
    p = f"{dest}/{a['ad_id']}.jpg"
    if os.path.exists(p): return p
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        open(p, "wb").write(urllib.request.urlopen(req, timeout=25).read())
        return p
    except Exception:
        return None


with concurrent.futures.ThreadPoolExecutor(12) as ex:
    res = list(ex.map(baixa, d))
ok = [r for r in res if r]
print(f"baixadas: {len(ok)} de {len(d)}")

for p in ok:
    alvo = f"{mini}/{os.path.basename(p)}"
    if not os.path.exists(alvo):
        subprocess.run(["cp", p, alvo], check=True)
import shutil
if shutil.which("sips"):
    subprocess.run(f"sips -Z 300 -s format jpeg -s formatOptions 50 {mini}/*.jpg", shell=True, capture_output=True)
    print("mini prontas em", mini)
else:
    print("mini copiadas sem redimensionar (sips só existe no Mac); o documento usa as originais em", mini)
