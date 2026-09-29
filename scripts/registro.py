#!/usr/bin/env python3
"""
meta-ads-odontorise: registro de otimização no ClickUp (gestor).

Toda mexida na conta de anúncio (otimização, mudança, problema de saldo) é registrada na tarefa
rotineira do cliente na lista Ongoing: "Acompanhamento de Resultado" para otimizações e mudanças,
"Monitoramento de Saldo" para saldo. Concluir a tarefa faz a recorrência trazê-la de volta.

Subcomandos:
  preparar --cliente X [--dias 1]        junta o que foi feito na conta (ações humanas no histórico da Meta
                                         e o que a skill subiu), os números de 7 dias e as tarefas alvo; propõe o texto
  gravar   --task ID --texto "..." [--concluir] --confirmo     comenta na tarefa e, se pedido, conclui
Sem --confirmo nada é escrito. Cada escrita fica em ~/OdontoRise/meta-ads/auditoria.jsonl.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import clickup, watchlist  # noqa: E402

ROTINAS = {"otimizacao": "Acompanhamento de Resultado", "saldo": "Monitoramento de Saldo"}


def _falha(msg, acao=None):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)


def _cliente(chave):
    dados = watchlist.carregar()
    c = watchlist.resolver(dados, chave)
    if not c:
        _falha(f"cliente '{chave}' não está no cadastro local", "cadastrar com: clientes.py cadastrar --nome ...")
    return c


def acoes_humanas(act, dias):
    since = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%S")
    ok, d = lib.graph_get(f"{act}/activities", params={"fields": "event_type,event_time,actor_name,object_name,translated_event_type", "since": since, "limit": 200})
    if not ok:
        return []
    out = []
    for e in d.get("data", []):
        if "Meta" in str(e.get("actor_name") or ""):
            continue
        out.append({"quando": e.get("event_time", "")[:16].replace("T", " "), "quem": e.get("actor_name"),
                    "o_que": e.get("translated_event_type") or e.get("event_type"), "objeto": e.get("object_name")})
    return out


def acoes_da_skill(act, dias):
    p = lib.AUDITORIA_PATH
    if not os.path.isfile(p):
        return []
    limite = datetime.now() - timedelta(days=dias)
    out = []
    for l in open(p, encoding="utf-8"):
        try:
            o = json.loads(l)
        except ValueError:
            continue
        if o.get("conta") == act and datetime.fromisoformat(o["quando"]) >= limite:
            out.append({"quando": o["quando"][:16].replace("T", " "), "o_que": o["acao"], "resumo": o["resumo"]})
    return out


def numeros_7d(act):
    ok, d = lib.graph_get(f"{act}/insights", params={"fields": "spend,actions", "date_preset": "last_7d"})
    if not ok or not d.get("data"):
        return {}
    r = d["data"][0]
    gasto = float(r.get("spend") or 0)
    msgs = sum(float(a.get("value", 0)) for a in r.get("actions", []) if a.get("action_type") == "onsite_conversion.messaging_conversation_started_7d")
    return {"gasto_7d": round(gasto, 2), "mensagens_7d": int(msgs), "custo_por_mensagem": round(gasto / msgs, 2) if msgs else None}


def tarefas_alvo(nome_cliente):
    ok, todas = clickup.tarefas(clickup.LISTA_ONGOING_ID, include_closed=False)
    if not ok:
        return {}
    alvo = clickup.normalizar(nome_cliente)
    toks = [w for w in alvo.split() if len(w) >= 4 and w not in ("clinica", "odontologia", "doutor", "doutora")]
    out = {}
    for t in todas:
        n = clickup.normalizar(t.get("name"))
        if all(w in n for w in toks[:2]):
            for chave, rot in ROTINAS.items():
                if n.startswith(clickup.normalizar(rot)):
                    due = t.get("due_date")
                    out[chave] = {"task": t["id"], "nome": t["name"], "status": t["status"]["status"],
                                  "vence_em": datetime.fromtimestamp(int(due) / 1000).date().isoformat() if due else None, "url": t.get("url")}
    return out


def texto_padrao(c, humanas, skill, nums, tipo):
    hoje = datetime.now().strftime("%d/%m/%Y")
    linhas = [f"Registro de {'saldo' if tipo == 'saldo' else 'otimização'} · {hoje} · {c.get('nome')} ({c.get('act_id')})", "", "O que foi feito:"]
    itens = [f"- {a['quando']} {a['o_que']}: {a.get('objeto') or ''}".rstrip(": ") for a in humanas[:12]]
    itens += [f"- {a['quando']} {a['o_que']}: {a['resumo']}" for a in skill[:8]]
    linhas += itens or ["- (descrever a mexida)"]
    linhas += ["", "Motivo: (preencher)", "",
               f"Números dos últimos 7 dias antes da mexida: gasto R$ {nums.get('gasto_7d', 0):.2f} · {nums.get('mensagens_7d', 0)} mensagens iniciadas · custo por mensagem "
               + (f"R$ {nums['custo_por_mensagem']:.2f}" if nums.get("custo_por_mensagem") else "sem mensagem"),
               "", "Próximo checkpoint: (data) · o que olhar: custo por mensagem nas três janelas"]
    return "\n".join(linhas)


def cmd_preparar(a):
    c = _cliente(a.cliente)
    act = c.get("act_id")
    humanas = acoes_humanas(act, a.dias) if act else []
    skill = acoes_da_skill(act, a.dias) if act else []
    nums = numeros_7d(act) if act else {}
    alvos = tarefas_alvo(c.get("nome"))
    tipo = "saldo" if a.tipo == "saldo" else "otimizacao"
    lib.print_json({"ok": True, "cliente": c.get("nome"), "conta": act, "dias": a.dias,
                    "acoes_humanas_na_conta": humanas, "acoes_da_skill": skill, "numeros_7d": nums,
                    "tarefas_alvo": alvos, "tarefa_sugerida": alvos.get(tipo),
                    "texto_proposto": texto_padrao(c, humanas, skill, nums, tipo),
                    "proximo_passo": "ajustar o texto com o gestor e, com OK, gravar --task <id> --texto '...' --concluir --confirmo"})


def cmd_gravar(a):
    ok, t = clickup.get(f"task/{a.task}")
    if not ok:
        _falha(f"tarefa {a.task} não encontrada ({t.get('erro')})")
    plano = {"tarefa": t.get("name"), "status_atual": t.get("status", {}).get("status"), "comentario": a.texto, "concluir": bool(a.concluir)}
    if not a.confirmo:
        lib.print_json({"ok": False, "ensaio": True, "faria": plano, "acao": "nada foi escrito. Depois do OK do gestor, repetir com --confirmo"})
        sys.exit(1)
    quem = clickup.quem_sou()[1]
    ok, r = clickup.comentar(a.task, a.texto)
    if not ok:
        _falha(f"o ClickUp recusou o comentário ({r.get('erro')})")
    lib.auditar("comentar tarefa", "clickup", f"{t.get('name')}: {a.texto[:120]}", ids={"task": a.task, "comment": r.get("id")}, quem=quem)
    out = {"ok": True, "tarefa": t.get("name"), "comentario_id": r.get("id"), "url": t.get("url")}
    if a.concluir:
        ok, r2 = clickup.mudar_status(a.task, "complete")
        if not ok:
            out["aviso"] = f"comentário gravado, mas não consegui concluir a tarefa ({r2.get('erro')})"
        else:
            lib.auditar("concluir tarefa", "clickup", t.get("name"), ids={"task": a.task}, quem=quem)
            ok3, t2 = clickup.get(f"task/{a.task}")
            due = t2.get("due_date") if ok3 else None
            out["status"] = t2.get("status", {}).get("status") if ok3 else "complete"
            out["proximo_vencimento"] = datetime.fromtimestamp(int(due) / 1000).date().isoformat() if due else None
    lib.print_json(out)


def main():
    p = argparse.ArgumentParser(description="Registro de otimização no ClickUp")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("preparar"); s.add_argument("--cliente", required=True); s.add_argument("--dias", type=int, default=1); s.add_argument("--tipo", choices=["otimizacao", "saldo"], default="otimizacao"); s.set_defaults(fn=cmd_preparar)
    s = sub.add_parser("gravar"); s.add_argument("--task", required=True); s.add_argument("--texto", required=True); s.add_argument("--concluir", action="store_true"); s.add_argument("--confirmo", action="store_true"); s.set_defaults(fn=cmd_gravar)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:
        _falha(f"erro interno ({type(e).__name__}): {lib.redigir(e)}")


if __name__ == "__main__":
    main()
