#!/usr/bin/env python3
"""
meta-ads-odontorise: clientes em alerta (head) e sinal do CS.

Subcomandos:
  listar                                   alertas abertos: cliente, motivo, nível, status, quem está com a ação, dias parado
  status-cliente --cliente X --status "Insatisfeito (Alerta)" --texto "..." --confirmo
                                           muda o Status do Projeto no perfil do cliente e registra o que foi visto (CS)
  abrir --cliente X --motivo "Cliente Ausente" --nivel 3 --texto "..." [--responsavel NOME] --confirmo
                                           cria o alerta na lista Clientes em Alerta
Sem --confirmo nada é escrito. Escritas ficam em ~/OdontoRise/meta-ads/auditoria.jsonl.
"""

import argparse
import json
import os
import sys
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import clickup, watchlist  # noqa: E402

AGORA = datetime.now().timestamp() * 1000
DIAS = lambda ms: round((AGORA - int(ms)) / 86400000, 1)


def _falha(msg, acao=None):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2)); sys.exit(1)


def _perfil_do_cliente(chave):
    dados = watchlist.carregar()
    c = watchlist.resolver(dados, chave)
    if c and c.get("clickup_task_id"):
        return c
    ok, achados = clickup.buscar(chave)
    if ok and len(achados) == 1:
        p = clickup.resumo_perfil(achados[0]); return p
    _falha(f"cliente '{chave}' não encontrado no cadastro nem no Perfil de Clientes", "cadastrar ou usar o nome exato do perfil")


def cmd_listar(a):
    ok, tasks = clickup.tarefas(clickup.LISTA_ALERTAS_ID, include_closed=False)
    if not ok:
        _falha(tasks.get("erro"))
    itens = []
    for t in tasks:
        rel = clickup.valor(t, "Alerta")
        cli = rel[0].get("name") if isinstance(rel, list) and rel and isinstance(rel[0], dict) else None
        ok2, c = clickup.get(f"task/{t['id']}/comment")
        coms = c.get("comments", []) if ok2 else []
        ultimo = max(coms, key=lambda x: int(x.get("date", 0)), default=None)
        mov = max([int(t.get("date_updated") or 0)] + [int(x.get("date", 0)) for x in coms])
        itens.append({"task": t["id"], "cliente": cli, "acao": t.get("name"), "status": t["status"]["status"],
                      "motivo": clickup.valor(t, "Motivo de Alerta"), "nivel": clickup.valor(t, "Nível de Criticidade"),
                      "com_quem": [x.get("username") for x in t.get("assignees", [])],
                      "gestor": clickup.valor(t, "Gestor"), "lideranca": clickup.valor(t, "Liderança"),
                      "aberto_ha_dias": DIAS(t["date_created"]), "parado_ha_dias": DIAS(mov),
                      "vence_em": datetime.fromtimestamp(int(t["due_date"]) / 1000).date().isoformat() if t.get("due_date") else None,
                      "ultimo_comentario": {"quem": ultimo.get("user", {}).get("username"), "ha_dias": DIAS(ultimo.get("date")), "texto": ultimo.get("comment_text", "")[:200]} if ultimo else None,
                      "url": t.get("url")})
    itens.sort(key=lambda x: -x["parado_ha_dias"])
    resumo = {"abertos": len(itens), "sem_cliente_ligado": sum(1 for i in itens if not i["cliente"]),
              "por_status": {}, "parados_5_dias_ou_mais": sum(1 for i in itens if i["parado_ha_dias"] >= 5)}
    for i in itens:
        resumo["por_status"][i["status"]] = resumo["por_status"].get(i["status"], 0) + 1
    lib.print_json({"ok": True, "resumo": resumo, "alertas": itens})


def cmd_status_cliente(a):
    p = _perfil_do_cliente(a.cliente)
    fid, opts = clickup.campo_id(clickup.LISTA_PERFIL_ID, "Status do Projeto")
    if a.status not in opts:
        _falha(f"status '{a.status}' não existe", f"opções: {list(opts)}")
    plano = {"cliente": p.get("nome"), "perfil_task": p["clickup_task_id"], "status_de": p.get("satisfacao"), "status_para": a.status, "comentario": a.texto}
    if not a.confirmo:
        lib.print_json({"ok": False, "ensaio": True, "faria": plano, "acao": "nada foi escrito. Com OK, repetir com --confirmo"}); sys.exit(1)
    quem = clickup.quem_sou()[1]
    ok, r = clickup.definir_campo(p["clickup_task_id"], fid, opts[a.status])
    if not ok:
        _falha(f"não consegui mudar o status ({r.get('erro')})")
    ok2, r2 = clickup.comentar(p["clickup_task_id"], f"[CS] Status do Projeto: {a.status}\n{a.texto}")
    lib.auditar("status do projeto", "clickup", f"{p.get('nome')}: {a.status} · {a.texto[:100]}", ids={"task": p["clickup_task_id"]}, quem=quem)
    lib.print_json({"ok": True, "cliente": p.get("nome"), "status": a.status, "comentario": "gravado" if ok2 else f"não gravado ({r2.get('erro')})"})


def cmd_abrir(a):
    p = _perfil_do_cliente(a.cliente)
    fmot, motivos = clickup.campo_id(clickup.LISTA_ALERTAS_ID, "Motivo de Alerta")
    if a.motivo not in motivos:
        _falha(f"motivo '{a.motivo}' não existe", f"opções: {list(motivos)}")
    fniv, _ = clickup.campo_id(clickup.LISTA_ALERTAS_ID, "Nível de Criticidade")
    falerta, _ = clickup.campo_id(clickup.LISTA_ALERTAS_ID, "Alerta")
    resp_ids = []
    if a.responsavel:
        m = clickup.membros(); rid = next((v for k, v in m.items() if clickup.normalizar(a.responsavel) in k), None)
        if not rid:
            _falha(f"responsável '{a.responsavel}' não encontrado no workspace")
        resp_ids = [rid]
    nome = f"Alerta - {p.get('nome')} [#{p['clickup_task_id']}]"
    payload = {"name": nome, "description": a.texto, "status": "alerta", "assignees": resp_ids,
               "custom_fields": [{"id": fmot, "value": motivos[a.motivo]}] + ([{"id": fniv, "value": int(a.nivel)}] if a.nivel else [])
               + ([{"id": falerta, "value": {"add": [p["clickup_task_id"]]}}] if falerta else [])}
    if not a.confirmo:
        lib.print_json({"ok": False, "ensaio": True, "faria": payload, "acao": "nada foi criado. Com OK, repetir com --confirmo"}); sys.exit(1)
    quem = clickup.quem_sou()[1]
    ok, r = clickup.criar_tarefa(clickup.LISTA_ALERTAS_ID, payload)
    if not ok:
        _falha(f"o ClickUp recusou criar o alerta ({r.get('erro')})")
    lib.auditar("abrir alerta", "clickup", f"{nome}: {a.motivo} nível {a.nivel}", ids={"task": r.get("id")}, quem=quem)
    lib.print_json({"ok": True, "alerta": r.get("id"), "nome": nome, "url": r.get("url")})


def main():
    p = argparse.ArgumentParser(description="Clientes em alerta")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("listar"); s.set_defaults(fn=cmd_listar)
    s = sub.add_parser("status-cliente"); s.add_argument("--cliente", required=True); s.add_argument("--status", required=True); s.add_argument("--texto", required=True); s.add_argument("--confirmo", action="store_true"); s.set_defaults(fn=cmd_status_cliente)
    s = sub.add_parser("abrir"); s.add_argument("--cliente", required=True); s.add_argument("--motivo", required=True); s.add_argument("--nivel", type=int); s.add_argument("--texto", required=True); s.add_argument("--responsavel"); s.add_argument("--confirmo", action="store_true"); s.set_defaults(fn=cmd_abrir)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:
        _falha(f"erro interno ({type(e).__name__}): {lib.redigir(e)}")


if __name__ == "__main__":
    main()
