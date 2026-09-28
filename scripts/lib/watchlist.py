#!/usr/bin/env python3
"""
Cadastro local de clientes de cada gestor: ~/OdontoRise/meta-ads/contas-odontorise.json.
Fora da skill (a pasta da skill é sobrescrita na sincronização). Nunca entra em repositório.
"""

import json
import os
import re
import unicodedata
from datetime import date

CADASTRO_PATH = os.path.expanduser(os.environ.get("ODR_CADASTRO", "~/OdontoRise/meta-ads/contas-odontorise.json"))


def slugify(texto):
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\b(dra?|clinica|odontologia|odontologica|instituto)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def carregar():
    if not os.path.isfile(CADASTRO_PATH):
        return {"atualizado": None, "clientes": []}
    with open(CADASTRO_PATH, encoding="utf-8-sig") as f:
        dados = json.load(f)
    if not isinstance(dados, dict) or not isinstance(dados.get("clientes"), list):
        raise ValueError("cadastro em formato inesperado")
    return dados


def salvar(dados):
    os.makedirs(os.path.dirname(CADASTRO_PATH), exist_ok=True)
    dados["atualizado"] = date.today().isoformat()
    with open(CADASTRO_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CADASTRO_PATH, 0o600)
    except OSError:
        pass


def resolver(dados, chave):
    """Acha um cliente por slug, código (#408), id da task do ClickUp, act_ ou trecho do nome."""
    if not chave:
        return None
    k = str(chave).strip()
    kn = slugify(k)
    for c in dados.get("clientes", []):
        if k in (c.get("slug"), c.get("codigo"), c.get("clickup_task_id"), c.get("act_id")):
            return c
    for c in dados.get("clientes", []):
        if kn and (kn == c.get("slug") or kn in slugify(c.get("nome"))):
            return c
    return None


def upsert(dados, cliente):
    """Insere ou atualiza pelo id da task do ClickUp (ou slug)."""
    lista = dados.setdefault("clientes", [])
    for i, c in enumerate(lista):
        if c.get("clickup_task_id") == cliente.get("clickup_task_id") or c.get("slug") == cliente.get("slug"):
            mantidos = {k: c[k] for k in ("act_id", "act_nome", "page_id", "instagram_id", "observacoes") if c.get(k) and not cliente.get(k)}
            lista[i] = {**c, **cliente, **mantidos}
            return lista[i], False
    lista.append(cliente)
    return cliente, True
