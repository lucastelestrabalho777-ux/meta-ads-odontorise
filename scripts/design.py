#!/usr/bin/env python3
"""
meta-ads-odontorise: acompanhamento do Designer (head). Só leitura.
Fonte: lista Conteúdos dos Clientes. Devolve atrasadas, fila de design, tempo médio por tipo e por pessoa.
Uso: design.py resumo [--dias 60]
"""
import argparse, json, os, sys, statistics
from datetime import datetime
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import clickup  # noqa: E402
AGORA = datetime.now().timestamp() * 1000
D = lambda a, b: (int(b) - int(a)) / 86400000

def cmd_resumo(a):
    ok, ts = clickup.tarefas(clickup.LISTA_CONTEUDOS_ID, include_closed=True)
    if not ok:
        print(json.dumps({"ok": False, "erro": ts.get("erro")}, ensure_ascii=False)); sys.exit(1)
    abertas = [t for t in ts if t["status"]["type"] != "closed"]
    fechadas = [t for t in ts if t["status"]["type"] == "closed" and (t.get("date_done") or t.get("date_closed"))]
    recentes = [t for t in fechadas if D(t.get("date_done") or t.get("date_closed"), AGORA) <= a.dias]
    def linha(t):
        rel = clickup.valor(t, "Conteúdo - Clientes"); cli = rel[0].get("name") if isinstance(rel, list) and rel and isinstance(rel[0], dict) else None
        return {"task": t["id"], "demanda": t["name"], "cliente": cli, "tipo": clickup.valor(t, "Tipo de Conteúdo"), "status": t["status"]["status"],
                "responsaveis": [x["username"] for x in t.get("assignees", [])], "criada_ha_dias": round(D(t["date_created"], AGORA), 1),
                "vence_em": datetime.fromtimestamp(int(t["due_date"]) / 1000).date().isoformat() if t.get("due_date") else None,
                "atraso_dias": round(D(t["due_date"], AGORA), 1) if t.get("due_date") and int(t["due_date"]) < AGORA else 0, "url": t.get("url")}
    atrasadas = sorted([linha(t) for t in abertas if t.get("due_date") and int(t["due_date"]) < AGORA], key=lambda x: -x["atraso_dias"])
    fila = sorted([linha(t) for t in abertas if t["status"]["status"] in ("aguardando design", "aguardando alteração")], key=lambda x: -x["criada_ha_dias"])
    por_tipo, por_pessoa = {}, {}
    for t in recentes:
        d = D(t["date_created"], t.get("date_done") or t.get("date_closed")); tp = str(clickup.valor(t, "Tipo de Conteúdo"))
        por_tipo.setdefault(tp, []).append(d)
        for x in t.get("assignees", []): por_pessoa.setdefault(x["username"], []).append(d)
    tempo_design = []
    for t in recentes[:a.amostra]:
        tis = clickup.tempo_em_status(t["id"]); v = tis.get("aguardando design")
        if v: tempo_design.append(v)
    por_status = {}
    for t in abertas: por_status[t["status"]["status"]] = por_status.get(t["status"]["status"], 0) + 1
    lib.print_json({"ok": True, "janela_dias": a.dias, "abertas": len(abertas), "por_status": por_status, "atrasadas": len(atrasadas),
                    "concluidas_na_janela": len(recentes),
                    "tempo_medio_criacao_a_conclusao_dias": {k: round(statistics.mean(v), 1) for k, v in por_tipo.items()},
                    "tempo_medio_por_pessoa_dias": {k: round(statistics.mean(v), 1) for k, v in por_pessoa.items()},
                    "tempo_medio_parado_em_aguardando_design_dias": round(statistics.mean(tempo_design), 1) if tempo_design else None,
                    "fila_design": fila, "lista_atrasadas": atrasadas})

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("resumo"); s.add_argument("--dias", type=int, default=60); s.add_argument("--amostra", type=int, default=25); s.set_defaults(fn=cmd_resumo)
    a = p.parse_args(); a.fn(a)

if __name__ == "__main__":
    main()
