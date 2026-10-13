#!/usr/bin/env python3
"""
meta-ads-odontorise: visão da CS. Só ClickUp e só leitura (não usa conta de anúncio nem a biblioteca da Meta).

Uso:
  cs.py carteira                  clientes ativos com satisfação, alerta aberto, reunião mensal, fase, tempo de casa,
                                  próxima reunião e último registro do gestor, classificados em
                                  saudavel / quase / cuidado / sem_dado (base de /clientes-saudaveis da CS)
  cs.py cliente --cliente X       contexto de um cliente (nome, parte do nome ou #código): perfil, alertas abertos,
                                  tarefas, conteúdos em produção e reuniões (base de /suporte-grupo da CS)

Nunca lê nem devolve valores (contrato, ticket, faturamento, verba), CPF/CNPJ, telefone, e-mail, endereço ou
nascimento. Resultado de anúncio não está no ClickUp: quem confirma é o gestor do cliente.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import clickup  # noqa: E402

LISTA_REUNIOES_ID = "901714773363"
HOJE = date.today()
SATISFACAO_BOA = ("Satisfeito", "Muito Satisfeito (Promotor)")
SATISFACAO_RUIM = ("Neutro", "Insatisfeito (Alerta)", "Muito Insatisfeito (Crítico)")
REUNIAO_MENSAL_DIAS = 45  # última reunião mensal há mais que isso, sem outra feita ou agendada = atrasada
ORDEM = {"cuidado": 0, "saudavel": 1, "quase": 2, "sem_dado": 3}


def _falha(msg, acao=None):
    out = {"ok": False, "erro": lib.redigir(str(msg))}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)


def _dia(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000).date() if ms else None
    except (TypeError, ValueError):
        return None


def _iso(ms):
    d = _dia(ms)
    return d.isoformat() if d else None


def _ha_dias(ms):
    d = _dia(ms)
    return (HOJE - d).days if d else None


def _ler(list_id, fechadas=False):
    ok, ts = clickup.tarefas(list_id, include_closed=fechadas)
    if not ok:
        _falha(ts.get("erro"), ts.get("acao"))
    return ts


def _ligados(t, campo):
    """Ids dos perfis ligados à tarefa pelo campo de relacionamento."""
    rel = clickup.valor(t, campo)
    return [r.get("id") for r in rel if isinstance(r, dict)] if isinstance(rel, list) else []


def _fechada(t):
    return t.get("status", {}).get("type") == "closed"


def _perfil(t):
    r = clickup.resumo_perfil(t)
    p = {k: r.get(k) for k in ("clickup_task_id", "nome", "codigo", "gestor", "cs", "produto", "especialidade",
                               "cidade", "estado", "fase", "satisfacao")}
    p["status_perfil"] = r.get("status")
    entrada = clickup.valor(t, "Data de Entrada")
    p["data_entrada"] = _iso(entrada)
    dias = _ha_dias(entrada)
    p["meses_de_casa"] = round(dias / 30.4) if dias is not None and dias >= 0 else None
    mensal = clickup.valor(t, "Data da Última Reunião Mensal")
    p["ultima_reuniao_mensal"] = _iso(mensal)
    p["ultima_reuniao_mensal_ha_dias"] = _ha_dias(mensal)
    p["reuniao_do_mes"] = _iso(clickup.valor(t, "Reunião do mês"))
    p["situacao_reuniao"] = clickup.valor(t, "Situação da Reunião")
    return p


def _alerta(t):
    return {"acao": t.get("name"), "status": t["status"]["status"], "motivo": clickup.valor(t, "Motivo de Alerta"),
            "nivel": clickup.valor(t, "Nível de Criticidade"),
            "com_quem": [x.get("username") for x in t.get("assignees", [])],
            "aberto_ha_dias": _ha_dias(t.get("date_created")), "url": t.get("url")}


def _tarefa(t):
    venc = _dia(t.get("due_date"))
    feita = t.get("date_done") or t.get("date_closed")
    return {"tarefa": t.get("name"), "tipo": clickup.valor(t, "Tipo de Tarefa") or clickup.valor(t, "Tipo de Conteúdo"),
            "status": t["status"]["status"], "vence_em": venc.isoformat() if venc else None,
            "atraso_dias": (HOJE - venc).days if venc and venc < HOJE and not _fechada(t) else 0,
            "concluida_em": _iso(feita) if _fechada(t) else None,
            "responsaveis": [x.get("username") for x in t.get("assignees", [])], "url": t.get("url")}


def _reuniao(t):
    return {"data": _iso(t.get("due_date")), "tipo": clickup.valor(t, "Tipo de Reunião"),
            "status": t["status"]["status"], "url": t.get("url")}


def _por_cliente(tarefas, campo):
    por = {}
    for t in tarefas:
        for pid in _ligados(t, campo):
            por.setdefault(pid, []).append(t)
    return por


def _proxima_reuniao(reunioes):
    futuras = [t for t in reunioes if not _fechada(t) and _dia(t.get("due_date")) and _dia(t.get("due_date")) >= HOJE]
    return _reuniao(min(futuras, key=lambda t: int(t["due_date"]))) if futuras else None


def _ultimo_registro(tarefas):
    """Última tarefa CONCLUÍDA do cliente em Tarefas - Clientes (tarefa aberta é pendência, não registro)."""
    feitas = [x for x in tarefas if _fechada(x) and (x.get("date_done") or x.get("date_closed"))]
    if not feitas:
        return None
    t = max(feitas, key=lambda x: int(x.get("date_done") or x.get("date_closed")))
    quando = t.get("date_done") or t.get("date_closed")
    return {"tarefa": t.get("name"), "tipo": clickup.valor(t, "Tipo de Tarefa"), "data": _iso(quando),
            "ha_dias": _ha_dias(quando)}


def _classificar(p, alertas):
    """Classe e motivos. Cuidado vence tudo; sem satisfação preenchida não entra em lista de oferta."""
    sat = p.get("satisfacao")
    cuidado = []
    if alertas:
        cuidado.append(f"{len(alertas)} alerta(s) aberto(s): " + "; ".join(str(a["motivo"] or a["acao"]) for a in alertas))
    if sat in SATISFACAO_RUIM:
        cuidado.append(f"satisfação {sat}")
    if cuidado:
        return "cuidado", cuidado
    if not sat:
        return "sem_dado", ["Status do Projeto vazio no ClickUp"]
    falta = []
    if sat not in SATISFACAO_BOA:
        falta.append(f"satisfação '{sat}' fora da escala conhecida")
    if p.get("fase") and p["fase"] != "Ongoing":
        falta.append(f"ainda em onboarding ({p['fase']})")
    dias = p.get("ultima_reuniao_mensal_ha_dias")
    if p.get("situacao_reuniao") == "No show":
        falta.append("no show na reunião do mês")
    elif not ((dias is not None and dias <= REUNIAO_MENSAL_DIAS) or p.get("situacao_reuniao") in ("Feita", "Agendada")):
        falta.append(f"última reunião mensal há {dias} dias" if dias is not None else "sem reunião mensal registrada")
    if falta:
        return "quase", falta
    return "saudavel", [f"satisfação {sat}", "sem alerta aberto", "reunião mensal em dia"]


def cmd_carteira(a):
    ativos = [t for t in _ler(clickup.LISTA_PERFIL_ID) if t.get("status", {}).get("status") == "ativo"]
    alertas = _por_cliente(_ler(clickup.LISTA_ALERTAS_ID), "Alerta")
    registros = _por_cliente(_ler(clickup.LISTA_TAREFAS_CLIENTES_ID, fechadas=True), "Tarefas - Clientes")
    reunioes = _por_cliente(_ler(LISTA_REUNIOES_ID), "Reunião - Clientes")
    clientes = []
    for t in ativos:
        p = _perfil(t)
        abertos = [_alerta(x) for x in alertas.get(t["id"], [])]
        p["classe"], p["motivos"] = _classificar(p, abertos)
        p["alertas_abertos"] = abertos
        p["proxima_reuniao"] = _proxima_reuniao(reunioes.get(t["id"], []))
        p["ultimo_registro_gestor"] = _ultimo_registro(registros.get(t["id"], []))
        clientes.append(p)
    clientes.sort(key=lambda c: (ORDEM[c["classe"]], c["nome"] or ""))
    resumo = {"ativos": len(clientes)}
    for c in clientes:
        resumo[c["classe"]] = resumo.get(c["classe"], 0) + 1
    print(f"{len(clientes)} ativos: " + ", ".join(f"{k} {v}" for k, v in resumo.items() if k != "ativos"), file=sys.stderr)
    lib.print_json({"ok": True, "hoje": HOJE.isoformat(), "fonte": "ClickUp, só leitura", "resumo": resumo,
                    "aviso": "Resultado de anúncio não está no ClickUp: antes de qualquer oferta, confirmar com o gestor do cliente.",
                    "clientes": clientes})


def _resolver(chave, perfis):
    c = chave.strip()
    if re.fullmatch(r"#?\d+", c):
        num = c.lstrip("#")
        achados = [t for t in perfis if str(clickup.valor(t, "Código do Cliente") or "").strip().lstrip("#") == num]
    else:
        alvo = clickup.normalizar(c)
        achados = [t for t in perfis if alvo and alvo in clickup.normalizar(t.get("name"))]
        exatos = [t for t in achados if clickup.normalizar(t.get("name")) == alvo]
        achados = exatos or achados
    ativos = [t for t in achados if t.get("status", {}).get("status") == "ativo"]
    if len(achados) > 1 and ativos:
        achados = ativos
    if not achados:
        _falha(f"cliente '{chave}' não encontrado no Perfil de Clientes", "usar o nome do perfil ou o #código")
    if len(achados) > 1:
        nomes = ", ".join(f"{t.get('name')} ({clickup.valor(t, 'Código do Cliente') or 'sem código'})" for t in achados[:8])
        _falha(f"'{chave}' bate com {len(achados)} perfis: {nomes}", "repetir com o nome completo ou o #código")
    return achados[0]


def cmd_cliente(a):
    t = _resolver(a.cliente, _ler(clickup.LISTA_PERFIL_ID, fechadas=True))
    pid = t["id"]
    p = _perfil(t)
    abertos = [_alerta(x) for x in _ler(clickup.LISTA_ALERTAS_ID) if pid in _ligados(x, "Alerta")]
    tarefas = [x for x in _ler(clickup.LISTA_TAREFAS_CLIENTES_ID, fechadas=True) if pid in _ligados(x, "Tarefas - Clientes")]
    conteudos = [x for x in _ler(clickup.LISTA_CONTEUDOS_ID, fechadas=True) if pid in _ligados(x, "Conteúdo - Clientes")]
    reunioes = [x for x in _ler(LISTA_REUNIOES_ID, fechadas=True) if pid in _ligados(x, "Reunião - Clientes")]
    fim = lambda x: int(x.get("date_done") or x.get("date_closed") or 0)  # noqa: E731
    passadas = [x for x in reunioes if _dia(x.get("due_date")) and _dia(x.get("due_date")) < HOJE]
    entregues_30d = [x for x in conteudos if _fechada(x) and _ha_dias(fim(x)) is not None and _ha_dias(fim(x)) <= 30]
    saida = {
        "ok": True, "hoje": HOJE.isoformat(), "fonte": "ClickUp, só leitura", "perfil": p,
        "classe": _classificar(p, abertos)[0] if p.get("status_perfil") == "ativo" else None,
        "alertas_abertos": abertos,
        "tarefas_abertas": sorted([_tarefa(x) for x in tarefas if not _fechada(x)], key=lambda x: -x["atraso_dias"]),
        "ultimas_concluidas": [_tarefa(x) for x in sorted([x for x in tarefas if _fechada(x)], key=fim, reverse=True)[:5]],
        "conteudos_em_producao": sorted([_tarefa(x) for x in conteudos if not _fechada(x)], key=lambda x: -x["atraso_dias"]),
        "conteudos_entregues_30d": {"total": len(entregues_30d),
                                    "ultimos": [_tarefa(x) for x in sorted(entregues_30d, key=fim, reverse=True)[:3]]},
        "proxima_reuniao": _proxima_reuniao(reunioes),
        "ultima_reuniao": _reuniao(max(passadas, key=lambda x: int(x["due_date"]))) if passadas else None,
        "aviso": "Resultado, saldo e anúncio não estão no ClickUp: quem responde com número é o gestor do cliente.",
    }
    print(f"{p['nome']}: {len(abertos)} alerta(s) aberto(s), {len(saida['tarefas_abertas'])} tarefa(s) aberta(s), "
          f"{len(saida['conteudos_em_producao'])} conteúdo(s) em produção", file=sys.stderr)
    lib.print_json(saida)


def main():
    p = argparse.ArgumentParser(description="Visão da CS no ClickUp (só leitura).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("carteira"); s.set_defaults(fn=cmd_carteira)
    s = sub.add_parser("cliente"); s.add_argument("--cliente", required=True); s.set_defaults(fn=cmd_cliente)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        _falha(f"erro interno: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
