#!/usr/bin/env python3
"""
Leitura do WhatsApp de Suporte da OdontoRise pela Uazapi. SOMENTE LEITURA.

Credencial: ~/OdontoRise/credentials/uazapi-odontorise.env com
  UAZAPI_SERVER_URL=https://...      (Server URL do painel da Uazapi)
  UAZAPI_INSTANCE_TOKEN=...          (token da instância, não o Admin Token)
(override para testes: ODR_UAZAPI_ENV apontando para outro arquivo).

O token da instância também envia mensagem. Por isso este arquivo só conhece as rotas de ROTAS_LEITURA:
qualquer outra rota é recusada aqui, antes de sair da máquina. Não acrescente rota de envio, de edição,
de grupo (criar, sair, mudar) nem de webhook.
"""

import os
import sys
import time

from . import _parse_env_file, _is_placeholder, API_TIMEOUT

UAZAPI_CRED_PATH = os.path.expanduser(
    os.environ.get("ODR_UAZAPI_ENV", "~/OdontoRise/credentials/uazapi-odontorise.env")
)

# rota -> método. Tudo que não está aqui é recusado.
ROTAS_LEITURA = {
    "/instance/status": "GET",      # a instância está conectada?
    "/group/list": "POST",          # grupos e participantes
    "/message/find": "POST",        # mensagens de um chat (a Uazapi guarda até 7 dias)
    "/message/download": "POST",    # link temporário de um áudio, para transcrever na máquina
}
PAUSA = 0.12  # segundos entre chamadas (a Uazapi aceita 10 por segundo por instância)

_cred = None
_ultima = 0.0


class ErroUazapi(Exception):
    def __init__(self, msg, acao=None):
        super().__init__(msg)
        self.acao = acao


def _credencial():
    global _cred
    if _cred:
        return _cred
    if not os.path.isfile(UAZAPI_CRED_PATH):
        raise ErroUazapi("credencial do WhatsApp de Suporte não encontrada",
                         f"criar o arquivo {UAZAPI_CRED_PATH} com UAZAPI_SERVER_URL e UAZAPI_INSTANCE_TOKEN "
                         "(passo Conectar o WhatsApp de Suporte, no guia)")
    v = _parse_env_file(UAZAPI_CRED_PATH)
    url, tok = (v.get("UAZAPI_SERVER_URL") or "").rstrip("/"), v.get("UAZAPI_INSTANCE_TOKEN") or ""
    if _is_placeholder(url) or _is_placeholder(tok) or not url.startswith("https://"):
        raise ErroUazapi("o arquivo de credencial do WhatsApp de Suporte ainda não foi preenchido",
                         f"abrir {UAZAPI_CRED_PATH} e colar a Server URL (começa com https://) e o token da instância")
    if os.name != "nt" and os.stat(UAZAPI_CRED_PATH).st_mode & 0o077:
        print(f"AVISO: outras pessoas deste computador conseguem ler a credencial. No terminal: chmod 600 {UAZAPI_CRED_PATH}",
              file=sys.stderr)
    _cred = {"url": url, "token": tok}
    return _cred


def redigir(texto):
    """Tira o token de qualquer texto antes de imprimir."""
    t = str(texto or "")
    if _cred and len(_cred["token"]) >= 8:
        t = t.replace(_cred["token"], "***")
    return t


def chamar(rota, corpo=None):
    """Chama uma rota de leitura e devolve o JSON. Recusa qualquer rota fora de ROTAS_LEITURA."""
    global _ultima
    if rota not in ROTAS_LEITURA:
        raise ErroUazapi(f"rota {rota} recusada: este pacote só lê o WhatsApp")
    import requests
    c = _credencial()
    espera = PAUSA - (time.time() - _ultima)
    if espera > 0:
        time.sleep(espera)
    cab = {"token": c["token"], "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    ultimo = None
    for tentativa in range(3):
        try:
            if ROTAS_LEITURA[rota] == "GET":
                r = requests.get(c["url"] + rota, headers=cab, timeout=API_TIMEOUT * 2)
            else:
                r = requests.post(c["url"] + rota, headers=cab, json=corpo or {}, timeout=API_TIMEOUT * 2)
        except requests.RequestException as e:
            ultimo = ErroUazapi(f"sem conexão com a Uazapi ({type(e).__name__})", "conferir a internet e a Server URL")
            time.sleep(1 + tentativa)
            continue
        finally:
            _ultima = time.time()
        if r.status_code == 401:
            raise ErroUazapi("a Uazapi recusou o token (401)", "conferir o token da instância no painel da Uazapi")
        if r.status_code == 429 or r.status_code >= 500:
            ultimo = ErroUazapi(f"a Uazapi respondeu {r.status_code}", "tentar de novo em alguns minutos")
            time.sleep(2 + 2 * tentativa)
            continue
        if r.status_code != 200:
            raise ErroUazapi(f"a Uazapi respondeu {r.status_code}: {redigir(r.text)[:200]}")
        try:
            return r.json()
        except ValueError:
            raise ErroUazapi("a Uazapi devolveu uma resposta que não é JSON")
    raise ultimo


def status():
    """Estado da instância, sem token, QR code nem código de pareamento."""
    d = chamar("/instance/status")
    i, s = d.get("instance") or {}, d.get("status") or {}
    return {"conectada": bool(s.get("connected") and s.get("loggedIn")), "perfil": i.get("profileName"),
            "numero_final": str(i.get("owner") or "")[-4:], "ultima_queda": (i.get("lastDisconnect") or "")[:10] or None}


def grupos():
    """Todos os grupos da instância, com participantes."""
    todos, off = [], 0
    while True:
        r = chamar("/group/list", {"limit": 100, "offset": off})
        todos += r.get("groups") or []
        p = r.get("pagination") or {}
        if not p.get("hasMore"):
            return todos
        off = p.get("nextOffset") or off + 100


def mensagens(chatid):
    """Mensagens que a Uazapi ainda guarda de um chat (até 7 dias), da mais antiga para a mais nova."""
    todas, off = [], 0
    while True:
        r = chamar("/message/find", {"chatid": chatid, "limit": 500, "offset": off})
        todas += r.get("messages") or []
        if not r.get("hasMore"):
            break
        off = r.get("nextOffset") or off + 500
    todas.sort(key=lambda m: m.get("messageTimestamp") or 0)
    return todas


def baixar_audio(msg_id, destino):
    """Baixa um áudio para o arquivo destino (mp3). O link da Uazapi é temporário e não é guardado."""
    import requests
    r = chamar("/message/download", {"id": msg_id, "generate_mp3": True})
    url = r.get("fileURL")
    if not url:
        raise ErroUazapi("a Uazapi não devolveu o áudio")
    b = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=API_TIMEOUT * 2)
    if b.status_code != 200:
        raise ErroUazapi(f"o áudio não baixou ({b.status_code})")
    with open(destino, "wb") as f:
        f.write(b.content)
    return destino
