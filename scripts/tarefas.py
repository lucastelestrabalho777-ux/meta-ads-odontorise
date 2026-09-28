#!/usr/bin/env python3
"""
meta-ads-odontorise: tarefas do ClickUp (só leitura, token pessoal).

Subcomandos:
  minhas   [--dias 7]           minhas tarefas abertas: atrasadas, de hoje, próximos N dias, sem data
  tarefa   --id X               detalhe de uma tarefa com descrição e comentários
  reunioes [--dias 14]          reuniões com clientes marcadas nos próximos N dias (lista Reuniões com Clientes)

Saída em JSON no stdout e um resumo curto no stderr. Nada é escrito no ClickUp.
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import clickup  # noqa: E402

LISTA_REUNIOES_ID = "901714773363"


def _dia(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(int(ms) / 1000).date()


def _resumo_task(t):
    due = _dia(t.get("due_date"))
    return {
        "id": t.get("id"),
        "nome": t.get("name"),
        "status": t.get("status", {}).get("status"),
        "lista": t.get("list", {}).get("name"),
        "vence_em": due.isoformat() if due else None,
        "url": t.get("url"),
        "responsaveis": [a.get("username") for a in t.get("assignees", [])],
    }


def _todas_minhas(uid):
    todas, page = [], 0
    while True:
        ok, d = clickup.get(f"team/{clickup.WORKSPACE_ID}/task", **{"assignees[]": uid, "include_closed": "false",
                                                                     "subtasks": "true", "page": page})
        if not ok:
            return False, d
        todas.extend(d.get("tasks", []))
        if d.get("last_page", True):
            break
        page += 1
    return True, todas


def cmd_minhas(a):
    uid, nome = clickup.quem_sou()
    if not uid:
        _falha("não consegui identificar o dono do token do ClickUp", "conferir o token (passo 8 do guia)")
    ok, tasks = _todas_minhas(uid)
    if not ok:
        _falha(tasks.get("erro"))
    hoje = date.today()
    limite = hoje + timedelta(days=a.dias)
    grupos = {"atrasadas": [], "hoje": [], "proximas": [], "sem_data": []}
    for t in tasks:
        r = _resumo_task(t)
        d = _dia(t.get("due_date"))
        if d is None:
            grupos["sem_data"].append(r)
        elif d < hoje:
            r["dias_de_atraso"] = (hoje - d).days
            grupos["atrasadas"].append(r)
        elif d == hoje:
            grupos["hoje"].append(r)
        elif d <= limite:
            grupos["proximas"].append(r)
    grupos["atrasadas"].sort(key=lambda x: -x["dias_de_atraso"])
    grupos["proximas"].sort(key=lambda x: x["vence_em"])
    print(f"{nome}: {len(grupos['atrasadas'])} atrasada(s), {len(grupos['hoje'])} para hoje, "
          f"{len(grupos['proximas'])} nos próximos {a.dias} dias, {len(grupos['sem_data'])} sem data", file=sys.stderr)
    lib.print_json({"ok": True, "pessoa": nome, "hoje": hoje.isoformat(), "total_abertas": len(tasks), **grupos})


def cmd_tarefa(a):
    ok, t = clickup.get(f"task/{a.id}", include_subtasks="true")
    if not ok:
        _falha(t.get("erro"), "conferir o id da tarefa")
    ok, c = clickup.get(f"task/{a.id}/comment")
    comentarios = []
    if ok:
        for x in c.get("comments", []):
            comentarios.append({"quem": x.get("user", {}).get("username"), "quando": _dia(x.get("date")).isoformat() if x.get("date") else None,
                                "texto": x.get("comment_text", "")[:1000]})
    r = _resumo_task(t)
    r["descricao"] = (t.get("text_content") or t.get("description") or "")[:4000]
    r["subtarefas"] = [{"id": s.get("id"), "nome": s.get("name"), "status": s.get("status", {}).get("status")} for s in t.get("subtasks", [])]
    r["comentarios"] = comentarios
    r["campos"] = {c["name"]: clickup._valor_campo(c) for c in t.get("custom_fields", []) if clickup._valor_campo(c) is not None and c.get("type") in ("drop_down", "labels", "short_text", "date", "number", "url")}
    lib.print_json({"ok": True, "tarefa": r})


def cmd_reunioes(a):
    hoje = date.today()
    limite = hoje + timedelta(days=a.dias)
    itens, page = [], 0
    while True:
        ok, d = clickup.get(f"list/{LISTA_REUNIOES_ID}/task", include_closed="false", subtasks="true", page=page)
        if not ok:
            _falha(d.get("erro"))
        itens.extend(d.get("tasks", []))
        if d.get("last_page", True):
            break
        page += 1
    proximas = []
    for t in itens:
        dd = _dia(t.get("due_date"))
        if dd and hoje <= dd <= limite:
            proximas.append(_resumo_task(t))
    proximas.sort(key=lambda x: x["vence_em"])
    print(f"{len(proximas)} reunião(ões) nos próximos {a.dias} dias", file=sys.stderr)
    lib.print_json({"ok": True, "hoje": hoje.isoformat(), "ate": limite.isoformat(), "reunioes": proximas})


def _falha(msg, acao=None):
    import json
    out = {"ok": False, "erro": lib.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="Tarefas do ClickUp (só leitura)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("minhas"); s.add_argument("--dias", type=int, default=7); s.set_defaults(fn=cmd_minhas)
    s = sub.add_parser("tarefa"); s.add_argument("--id", required=True); s.set_defaults(fn=cmd_tarefa)
    s = sub.add_parser("reunioes"); s.add_argument("--dias", type=int, default=14); s.set_defaults(fn=cmd_reunioes)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:
        _falha(f"erro interno ({type(e).__name__}): {lib.redigir(e)}")


if __name__ == "__main__":
    main()
