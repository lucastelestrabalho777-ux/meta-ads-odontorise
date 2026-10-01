#!/usr/bin/env python3
"""
Criativos no Google Drive pelo link público: sem login e sem baixar o vídeo.

Funciona com pasta ou arquivo compartilhado como "Qualquer pessoa com o link" (Leitor).
A lista da pasta vem da página pública embeddedfolderview. O arquivo é conferido pelos cabeçalhos
do link direto pedindo só 1 byte. A Meta busca o vídeo sozinha pelo link direto (file_url);
imagem passa só pela memória (a Meta não aceita link de imagem), nunca vira arquivo no computador.
"""

import html
import re
from urllib.parse import unquote

from . import API_TIMEOUT

COMO_LIBERAR = ("No Drive: botão Compartilhar > Acesso geral > Qualquer pessoa com o link (Leitor), "
                "na pasta e nos arquivos. Depois mandar o link de novo.")
EXT_VIDEO = {"mp4", "mov", "m4v", "webm", "avi", "mkv"}
EXT_IMAGEM = {"jpg", "jpeg", "png"}
LIMITE_IMAGEM_MB = 30
_RE_ID = r"([A-Za-z0-9_-]{20,})"


def link_direto(file_id):
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"


def extrair_id(link):
    """('pasta' | 'arquivo' | None, id) a partir de um link do Drive ou de um id solto."""
    t = str(link or "").strip()
    m = re.search(r"/folders/" + _RE_ID, t)
    if m:
        return "pasta", m.group(1)
    m = re.search(r"/(?:file/)?d/" + _RE_ID, t) or re.search(r"[?&]id=" + _RE_ID, t)
    if m:
        return "arquivo", m.group(1)
    if re.fullmatch(_RE_ID, t):
        return None, t
    return None, None


def tipo_por_nome(nome, mime=""):
    ext = str(nome or "").rsplit(".", 1)[-1].lower() if "." in str(nome or "") else ""
    if ext in EXT_VIDEO or mime.startswith("video/"):
        return "video"
    if ext in EXT_IMAGEM or mime in ("image/jpeg", "image/png"):
        return "imagem"
    if "folder" in mime:
        return "pasta"
    return "outro"


def _get(url, **kw):
    import requests
    try:
        return True, requests.get(url, timeout=kw.pop("timeout", API_TIMEOUT), **kw)
    except requests.RequestException as e:
        return False, {"erro": f"sem resposta do Google Drive ({type(e).__name__})", "rede": True}


def listar_pasta(folder_id):
    """(ok, [{id, nome, tipo, link}]) dos itens de uma pasta pública. Subpasta vem com tipo 'pasta'."""
    ok, r = _get(f"https://drive.google.com/embeddedfolderview?id={folder_id}")
    if not ok:
        return False, r
    if r.status_code != 200 or "accounts.google.com" in r.url:
        return False, {"erro": "a pasta não abre sem login (restrita) ou o link está errado", "restrito": True, "acao": COMO_LIBERAR}
    itens = []
    for bloco in r.text.split('class="flip-entry" id="entry-')[1:]:
        fid = bloco.split('"', 1)[0]
        nome = re.search(r'class="flip-entry-title">([^<]*)<', bloco)
        mime = re.search(r'/16/type/([^"]+)"', bloco)
        href = re.search(r'<a href="([^"]+)"', bloco)
        nome = html.unescape(nome.group(1)) if nome else fid
        mime = html.unescape(mime.group(1)) if mime else ""
        tipo = "pasta" if href and "/folders/" in href.group(1) else tipo_por_nome(nome, mime)
        itens.append({"id": fid, "nome": nome, "tipo": tipo,
                      "link": f"https://drive.google.com/drive/folders/{fid}" if tipo == "pasta" else f"https://drive.google.com/file/d/{fid}/view"})
    return True, itens


def conferir_arquivo(file_id):
    """(ok, {id, nome, tipo, tamanho_mb, link_direto}) lendo só 1 byte. ok=False se a Meta não vai conseguir buscar."""
    ok, r = _get(link_direto(file_id), headers={"Range": "bytes=0-0"}, stream=True)
    if not ok:
        return False, r
    r.close()
    ctype = r.headers.get("content-type", "")
    if r.status_code not in (200, 206) or "text/html" in ctype:
        return False, {"erro": "o arquivo não abre sem login (restrito) ou o link está errado", "restrito": True, "acao": COMO_LIBERAR}
    disp = r.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;]+)", disp) or re.search(r'filename="([^"]+)"', disp)
    nome = unquote(m.group(1)) if m else file_id
    try:
        nome = nome.encode("latin-1").decode("utf-8")  # cabeçalho vem em UTF-8 lido como latin-1
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    total = re.search(r"/(\d+)$", r.headers.get("content-range", ""))
    tamanho = int(total.group(1)) if total else int(r.headers.get("content-length") or 0)
    return True, {"id": file_id, "nome": nome, "tipo": tipo_por_nome(nome, ctype),
                  "tamanho_mb": round(tamanho / 1048576, 1), "link_direto": link_direto(file_id)}


def imagem_em_memoria(file_id):
    """(ok, bytes) de uma imagem pública, só na memória. Recusa acima de 30 MB (limite da Meta)."""
    ok, r = _get(link_direto(file_id), timeout=120)
    if not ok:
        return False, r
    if r.status_code != 200 or "text/html" in r.headers.get("content-type", ""):
        return False, {"erro": "a imagem não abre sem login (restrita)", "restrito": True, "acao": COMO_LIBERAR}
    if len(r.content) > LIMITE_IMAGEM_MB * 1048576:
        return False, {"erro": f"imagem acima de {LIMITE_IMAGEM_MB} MB, a Meta não aceita"}
    return True, r.content
