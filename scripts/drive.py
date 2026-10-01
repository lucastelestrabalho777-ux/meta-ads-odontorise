#!/usr/bin/env python3
"""
meta-ads-odontorise: criativos no Google Drive pelo link (só leitura, sem login, sem baixar).

Subcomandos:
  listar --link URL     pasta ou arquivo: nome, tipo (video, imagem, pasta, outro), tamanho e se a Meta
                        consegue buscar o arquivo pelo link. Subpasta aparece com o próprio link para listar.

O link precisa estar como "Qualquer pessoa com o link" (Leitor). Para subir: create.py anuncio-drive.
"""

import argparse
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import drive  # noqa: E402


def _falha(msg, acao=None):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)


def cmd_listar(a):
    tipo, fid = drive.extrair_id(a.link)
    if not fid:
        _falha("não reconheci o link do Drive", "mandar o link da pasta (drive.google.com/drive/folders/...) ou do arquivo (drive.google.com/file/d/...)")
    if tipo != "pasta":
        ok, arq = drive.conferir_arquivo(fid)
        if ok or tipo == "arquivo":
            if not ok:
                _falha(arq.get("erro"), arq.get("acao"))
            lib.print_json({"ok": True, "tipo_link": "arquivo", "arquivos": [arq], "subpastas": [], "ignorados": []})
            return
    ok, itens = drive.listar_pasta(fid)
    if not ok:
        _falha(itens.get("erro"), itens.get("acao"))
    arquivos, subpastas, ignorados = [], [], []
    for it in itens:
        if it["tipo"] == "pasta":
            subpastas.append({"nome": it["nome"], "link": it["link"]})
        elif it["tipo"] in ("video", "imagem"):
            ok, arq = drive.conferir_arquivo(it["id"])
            arquivos.append(arq if ok else {**it, "erro": arq.get("erro"), "acao": arq.get("acao")})
        else:
            ignorados.append(it["nome"])
    bloqueados = [x["nome"] for x in arquivos if x.get("erro")]
    print(f"{len(arquivos)} criativo(s), {len(subpastas)} subpasta(s), {len(ignorados)} ignorado(s)"
          + (f", {len(bloqueados)} restrito(s)" if bloqueados else ""), file=sys.stderr)
    lib.print_json({"ok": True, "tipo_link": "pasta", "arquivos": arquivos, "subpastas": subpastas, "ignorados": ignorados,
                    "acao": drive.COMO_LIBERAR if bloqueados else None})


def main():
    p = argparse.ArgumentParser(description="Criativos no Google Drive (só leitura)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("listar"); s.add_argument("--link", required=True); s.set_defaults(fn=cmd_listar)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:
        _falha(f"erro interno ({type(e).__name__}): {lib.redigir(e)}")


if __name__ == "__main__":
    main()
