#!/usr/bin/env python3
"""
meta-ads-odontorise: análise do onboarding (head). Só leitura.
Fonte: lista Onboarding (tarefa-mãe por cliente, subtarefas por etapa). Devolve tempo médio, os em andamento
com dias e progresso, e as etapas que mais demoram.
Uso: onboarding.py resumo
"""
import argparse, json, os, re, sys, statistics
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
    ok, ts = clickup.tarefas(clickup.LISTA_ONBOARDING_ID, include_closed=True)
    if not ok:
        print(json.dumps({"ok": False, "erro": ts.get("erro")}, ensure_ascii=False)); sys.exit(1)
    maes = {t["id"]: t for t in ts if not t.get("parent")}
    subs = {}
    for t in ts:
        if t.get("parent") in maes: subs.setdefault(t["parent"], []).append(t)
    concluidos, andamento, por_etapa = [], [], {}
    for mid, m in maes.items():
        ss = subs.get(mid, [])
        if not ss: continue
        feitas = [t for t in ss if t["status"]["type"] == "closed"]
        nome = re.sub(r"\s*\[.*$", "", m["name"])
        fins = [int(t.get("date_done") or t.get("date_closed") or 0) for t in feitas if (t.get("date_done") or t.get("date_closed"))]
        if len(feitas) == len(ss) and fins:
            concluidos.append({"cliente": nome, "dias": round(D(m["date_created"], max(fins)), 1), "etapas": len(ss)})
        else:
            pend = [t for t in ss if t["status"]["type"] != "closed"]
            andamento.append({"cliente": nome, "dias_desde_inicio": round(D(m["date_created"], AGORA), 1), "feitas": len(feitas), "total": len(ss),
                              "proximas": [{"etapa": clickup.valor(t, "Etapas do Onboarding") or t["name"], "setor": clickup.valor(t, "Setor"), "responsaveis": [x["username"] for x in t.get("assignees", [])]} for t in pend[:3]], "url": m.get("url")})
        for t in feitas:
            fim = t.get("date_done") or t.get("date_closed")
            if fim:
                e = clickup.valor(t, "Etapas do Onboarding") or re.sub(r"\s*\[.*$", "", t["name"])
                por_etapa.setdefault(e, {"dias": [], "setor": clickup.valor(t, "Setor")})["dias"].append(D(m["date_created"], fim))
    rank = sorted([{"etapa": e, "dias_medio_desde_inicio": round(statistics.mean(v["dias"]), 1), "setor": v["setor"], "n": len(v["dias"])} for e, v in por_etapa.items() if len(v["dias"]) >= 3], key=lambda x: -x["dias_medio_desde_inicio"])
    andamento.sort(key=lambda x: -x["dias_desde_inicio"])
    lib.print_json({"ok": True, "concluidos": len(concluidos), "em_andamento": len(andamento),
                    "tempo_medio_dias": round(statistics.mean([c["dias"] for c in concluidos]), 1) if concluidos else None,
                    "tempo_mediano_dias": round(statistics.median([c["dias"] for c in concluidos]), 1) if concluidos else None,
                    "mais_lentos": sorted(concluidos, key=lambda x: -x["dias"])[:3], "andamento": andamento, "etapas_que_mais_demoram": rank[:8]})

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("resumo"); s.set_defaults(fn=cmd_resumo)
    a = p.parse_args(); a.fn(a)

if __name__ == "__main__":
    main()
