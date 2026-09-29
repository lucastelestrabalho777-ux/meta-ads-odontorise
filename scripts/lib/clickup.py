#!/usr/bin/env python3
"""
Leitura do ClickUp da OdontoRise (só GET) com o token pessoal de cada gestor.

Credencial: ~/OdontoRise/credentials/clickup-odontorise.env com CLICKUP_TOKEN=...
(override para testes: ODR_CLICKUP_ENV apontando para outro arquivo).
Fonte dos clientes: lista "Perfil de Clientes" do workspace OdontoRise.
Só campos operacionais são lidos; dados pessoais e financeiros nunca saem do ClickUp.
"""

import os
import re
import sys
import unicodedata

from . import _parse_env_file, _is_placeholder, redigir, API_TIMEOUT

WORKSPACE_ID = "90171289892"
LISTA_PERFIL_ID = "901714636294"
CLICKUP_CRED_PATH = os.path.expanduser(
    os.environ.get("ODR_CLICKUP_ENV", "~/OdontoRise/credentials/clickup-odontorise.env")
)
API = "https://api.clickup.com/api/v2"

# Campo do ClickUp -> chave no cadastro local. Só o que serve para operar a conta.
CAMPOS_OPERACIONAIS = {
    "Código do Cliente": "codigo",
    "Cidade": "cidade",
    "Estado": "estado",
    "Especialidade Odontologica": "especialidade",
    "Especialidade Secundária": "especialidade_2",
    "Instagram": "instagram_url",
    "Gestor": "gestor",
    "CS": "cs",
    "Liderança": "lideranca",
    "Produto": "produto",
    "Fase Global": "fase",
    "Objetivo Principal": "objetivo",
    "Drive Geral": "drive",
    "Link do Data Studio": "data_studio",
    "Status do Projeto": "satisfacao",
    "Health Score": "health_score",
}

_token = None


def normalizar(texto):
    """minúsculas, sem acento, só letras/números/espaço"""
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", t.lower()).strip()


def token():
    global _token
    if _token:
        return _token
    if not os.path.isfile(CLICKUP_CRED_PATH):
        print("ERRO: credencial do ClickUp não encontrada.", file=sys.stderr)
        print(f"  Esperada em: {CLICKUP_CRED_PATH}", file=sys.stderr)
        print("  Conteúdo: CLICKUP_TOKEN=<seu token pessoal> (ClickUp > Configurações > Apps > Token de API).", file=sys.stderr)
        print("  Guia de IA OdontoRise, página Onboarding, passo 8.", file=sys.stderr)
        sys.exit(1)
    v = _parse_env_file(CLICKUP_CRED_PATH).get("CLICKUP_TOKEN", "")
    if _is_placeholder(v):
        print(f"ERRO: CLICKUP_TOKEN vazio ou com valor de exemplo em {CLICKUP_CRED_PATH}.", file=sys.stderr)
        sys.exit(1)
    _token = v
    return v


def get(path, **params):
    """GET no ClickUp. Devolve (ok, dado); erro vem sem segredo e sem exceção de rede."""
    import requests
    url = path if path.startswith("http") else f"{API}/{path.lstrip('/')}"
    try:
        r = requests.get(url, headers={"Authorization": token()}, params=params, timeout=API_TIMEOUT)
        body = r.json()
    except requests.RequestException as e:
        return False, {"erro": f"sem resposta do ClickUp ({type(e).__name__})", "rede": True}
    except ValueError:
        return False, {"erro": "o ClickUp respondeu algo que não é JSON", "rede": True}
    if r.status_code >= 400 or (isinstance(body, dict) and body.get("err")):
        return False, {"erro": redigir(body.get("err") if isinstance(body, dict) else r.status_code),
                       "code": body.get("ECODE") if isinstance(body, dict) else r.status_code}
    return True, body


def quem_sou():
    """Usuário dono do token: (id, nome) ou (None, None)."""
    ok, d = get("user")
    if not ok:
        return None, None
    u = d.get("user", {})
    return u.get("id"), u.get("username")


def _valor_campo(c):
    v = c.get("value")
    if v in (None, "", []):
        return None
    t = c.get("type")
    if t == "drop_down":
        opts = c.get("type_config", {}).get("options", [])
        return next((o.get("name") for o in opts if o.get("orderindex") == v or o.get("id") == v), v)
    if t == "labels":
        opts = {o["id"]: o.get("label") for o in c.get("type_config", {}).get("options", [])}
        return [opts.get(x, x) for x in v]
    if t == "users":
        return [{"id": u.get("id"), "nome": u.get("username")} for u in v]
    return v


def perfis(include_closed=True):
    """Todas as tarefas da lista Perfil de Clientes (paginado)."""
    todas, page = [], 0
    while True:
        ok, d = get(f"list/{LISTA_PERFIL_ID}/task", include_closed=str(include_closed).lower(), subtasks="true", page=page)
        if not ok:
            return False, d
        todas.extend(d.get("tasks", []))
        if d.get("last_page", True):
            break
        page += 1
    return True, todas


def resumo_perfil(t):
    """Extrai só os campos operacionais de uma tarefa de perfil."""
    r = {"clickup_task_id": t.get("id"), "nome": t.get("name"), "status": t.get("status", {}).get("status")}
    for c in t.get("custom_fields", []):
        chave = CAMPOS_OPERACIONAIS.get(c.get("name"))
        if chave:
            r[chave] = _valor_campo(c)
    for k in ("gestor", "cs", "lideranca"):
        if isinstance(r.get(k), list):
            r[k] = [u["nome"] for u in r[k]]
    ig = r.get("instagram_url") or ""
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", ig)
    r["instagram_user"] = m.group(1).lower().rstrip(".") if m else None
    return r


def gestor_ids(t):
    for c in t.get("custom_fields", []):
        if c.get("name") == "Gestor" and c.get("value"):
            return [u.get("id") for u in c["value"]]
    return []


def buscar(nome):
    """Perfis cujo nome contém o texto (sem acento, sem maiúsculas)."""
    ok, todos = perfis()
    if not ok:
        return False, todos
    alvo = normalizar(nome)
    achados = [t for t in todos if alvo and alvo in normalizar(t.get("name"))]
    return True, achados


# ---------------------------------------------------------------------------
# Listas e escrita (com OK explícito e auditoria)
# ---------------------------------------------------------------------------

LISTA_ONGOING_ID = "901715565756"
LISTA_ALERTAS_ID = "901714773481"
LISTA_CONTEUDOS_ID = "901715515297"
LISTA_ONBOARDING_ID = "901714636345"
LISTA_TAREFAS_CLIENTES_ID = "901714773375"
CAMPO_STATUS_PROJETO_ID = "e3752b91-8c51-45bf-9066-5edfd91e9a2b"


def tarefas(list_id, include_closed=False):
    """Todas as tarefas de uma lista (paginado)."""
    todas, page = [], 0
    while True:
        ok, d = get(f"list/{list_id}/task", include_closed=str(include_closed).lower(), subtasks="true", page=page)
        if not ok:
            return False, d
        todas.extend(d.get("tasks", []))
        if d.get("last_page", True):
            break
        page += 1
    return True, todas


def valor(t, nome):
    for c in t.get("custom_fields", []):
        if c.get("name") == nome:
            return _valor_campo(c)
    return None


def campo_id(list_id, nome):
    """(id do campo, {nome da opção: id/orderindex}) de um campo personalizado da lista."""
    ok, d = get(f"list/{list_id}/field")
    if not ok:
        return None, {}
    for f in d.get("fields", []):
        if f.get("name") == nome:
            opts = {}
            for o in f.get("type_config", {}).get("options", []):
                opts[o.get("name") or o.get("label")] = o.get("id") if f.get("type") == "labels" else o.get("orderindex")
            return f.get("id"), opts
    return None, {}


def membros():
    """{nome normalizado: id} dos membros do workspace."""
    ok, d = get("team")
    out = {}
    if ok:
        for team in d.get("teams", []):
            if str(team.get("id")) == WORKSPACE_ID:
                for m in team.get("members", []):
                    u = m.get("user", {})
                    out[normalizar(u.get("username"))] = u.get("id")
    return out


def _escrever(metodo, path, payload):
    import requests
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(metodo, url, headers={"Authorization": token(), "Content-Type": "application/json"}, json=payload, timeout=API_TIMEOUT)
        body = r.json() if r.text else {}
    except requests.RequestException as e:
        return False, {"erro": f"sem resposta do ClickUp ({type(e).__name__})"}
    except ValueError:
        return False, {"erro": "o ClickUp respondeu algo que não é JSON"}
    if r.status_code >= 400 or (isinstance(body, dict) and body.get("err")):
        return False, {"erro": redigir(body.get("err") if isinstance(body, dict) else r.status_code), "code": r.status_code}
    return True, body


def comentar(task_id, texto):
    return _escrever("POST", f"task/{task_id}/comment", {"comment_text": texto, "notify_all": False})


def mudar_status(task_id, status):
    return _escrever("PUT", f"task/{task_id}", {"status": status})


def definir_campo(task_id, field_id, value):
    return _escrever("POST", f"task/{task_id}/field/{field_id}", {"value": value})


def criar_tarefa(list_id, payload):
    return _escrever("POST", f"list/{list_id}/task", payload)


def tempo_em_status(task_id):
    ok, d = get(f"task/{task_id}/time_in_status")
    if not ok:
        return {}
    out = {}
    for st in d.get("status_history") or []:
        out[st.get("status")] = (st.get("total_time") or {}).get("by_minute", 0) / 1440
    return out
