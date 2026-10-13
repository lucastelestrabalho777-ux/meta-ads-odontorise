#!/usr/bin/env python3
"""
meta-ads-odontorise: visão da CS. Só ClickUp e só leitura (não usa conta de anúncio nem a biblioteca da Meta).

Uso:
  cs.py carteira [--completo]     clientes ativos classificados em saudavel / quase / cuidado / onboarding / sem_dado
                                  por satisfação, alerta aberto, reunião mensal, fase e rede; uma linha por cliente,
                                  saudáveis primeiro (base de /clientes-saudaveis da CS). --completo devolve todos os
                                  campos (saída grande, só para conferência).
  cs.py cliente --cliente X       contexto de um cliente (nome, parte do nome ou #código): perfil, alertas abertos,
                                  tarefas, conteúdos e reuniões (base de /suporte-grupo da CS)

Nunca lê nem devolve valores (contrato, ticket, faturamento, verba), CPF/CNPJ, telefone, e-mail, endereço,
nascimento, descrição ou comentário de tarefa. Resultado de anúncio não está no ClickUp: quem confirma é o gestor.
"""
import argparse
import collections
import difflib
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
SATISFACAO_BOA = ("Satisfeito", "Muito Satisfeito (Promotor)", "Embaixador da Odontorise")
SATISFACAO_RUIM = ("Neutro", "Insatisfeito (Alerta)", "Muito Insatisfeito (Crítico)")
SATISFACAO_PIOR = ("Insatisfeito (Alerta)", "Muito Insatisfeito (Crítico)")
FASES_ONBOARDING = ("ONB1", "ONB2")
REUNIAO_MENSAL_DIAS = 45  # última reunião mensal feita há mais que isso, sem outra agendada = atrasada
ORDEM = ("saudavel", "quase", "cuidado", "onboarding", "sem_dado")


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


def _status(t):
    s = t.get("status", {}).get("status")
    return "a fazer" if s == "ä fazer" else s  # nome do status com trema no ClickUp


def _primeiros(nomes):
    return [str(n).split()[0] for n in (nomes or []) if n]


def _marca(nome):
    """Marca da rede: o que vem antes do '|' no nome do perfil, sem 'implantes' (ex.: 'STAR SORRINDO')."""
    if "|" not in (nome or ""):
        return None
    m = re.sub(r"\bimplantes\b", "", clickup.normalizar(nome.split("|")[0])).strip()
    return m.upper() or None


def _perfil(t):
    r = clickup.resumo_perfil(t)
    p = {k: r.get(k) for k in ("clickup_task_id", "nome", "codigo", "gestor", "cs", "lideranca", "produto",
                               "especialidade", "cidade", "estado", "fase", "satisfacao")}
    p["status_perfil"] = r.get("status")
    entrada = clickup.valor(t, "Data de Entrada")
    dias = _ha_dias(entrada)
    p["data_entrada"] = _iso(entrada)
    p["meses_de_casa"] = round(dias / 30.4) if dias is not None and dias >= 0 else None
    p["situacao_reuniao"] = clickup.valor(t, "Situação da Reunião")
    p["_ultima_mensal"] = _dia(clickup.valor(t, "Data da Última Reunião Mensal"))
    p["_reuniao_do_mes"] = _dia(clickup.valor(t, "Reunião do mês"))
    p["rede"] = _marca(t.get("name"))
    return p


def _reuniao_mensal(p, proxima):
    """(em dia?, texto pronto). Feita = Data da Última Reunião Mensal ou Reunião do mês com situação Feita.
    Agendada = Reunião do mês futura com situação Agendada, ou próxima reunião na lista Reuniões com Clientes."""
    ultima, mes, sit = p["_ultima_mensal"], p["_reuniao_do_mes"], p.get("situacao_reuniao")
    feitas = [d for d in (ultima, mes if sit == "Feita" and mes and mes <= HOJE else None) if d]
    feita = max(feitas) if feitas else None
    futuras = [d for d in (mes if sit == "Agendada" and mes and mes >= HOJE else None,
                           date.fromisoformat(proxima["data"]) if proxima and proxima.get("data") else None) if d]
    agendada = min(futuras) if futuras else None
    dias = (HOJE - feita).days if feita else None
    em_dia = bool(agendada) or (dias is not None and dias <= REUNIAO_MENSAL_DIAS)
    if agendada:
        texto = f"agendada {agendada:%d/%m}" + (f", última feita {feita:%d/%m}" if feita else "")
    elif feita:
        texto = f"feita {feita:%d/%m}" if em_dia else f"atrasada: última feita {feita:%d/%m} ({dias} dias)"
    else:
        texto = "sem reunião mensal registrada"
    if sit == "Agendada" and mes and mes < HOJE and not (feita and feita >= mes):
        texto += f"; estava agendada para {mes:%d/%m} e não há registro de que aconteceu"
    if sit == "No show":
        texto += "; no show na reunião do mês"
    return em_dia, texto


def _alerta(t):
    motivo = clickup.valor(t, "Motivo de Alerta")
    nivel = clickup.valor(t, "Nível de Criticidade")
    return {"motivo": motivo or "não preenchido", "nivel": nivel, "status": _status(t),
            "com_quem": _primeiros(x.get("username") for x in t.get("assignees", [])),
            "aberto_ha_dias": _ha_dias(t.get("date_created")), "vence_em": _iso(t.get("due_date")),
            "incompleto": not motivo or nivel in (None, ""), "url": t.get("url")}


def _tarefa(t, campo_tipo):
    venc = _dia(t.get("due_date"))
    feita = t.get("date_done") or t.get("date_closed")
    return {"tarefa": t.get("name"), "tipo": clickup.valor(t, campo_tipo), "status": _status(t),
            "origem": clickup.valor(t, "Origem"), "criada_em": _iso(t.get("date_created")),
            "vence_em": venc.isoformat() if venc else None,
            "atraso_dias": (HOJE - venc).days if venc and venc < HOJE and not _fechada(t) else 0,
            "concluida_em": _iso(feita) if _fechada(t) else None,
            "pessoas_na_tarefa": _primeiros(x.get("username") for x in t.get("assignees", [])), "url": t.get("url")}


def _reuniao(t):
    return {"data": _iso(t.get("due_date")), "tipo": clickup.valor(t, "Tipo de Reunião"), "status": _status(t),
            "url": t.get("url")}


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


def _classificar(p, alertas, em_dia, texto_reuniao):
    """Classe e motivos. Cuidado vence tudo; onboarding e satisfação vazia não entram em lista de oferta."""
    sat = p.get("satisfacao")
    cuidado = []
    if alertas:
        cuidado.append(f"{len(alertas)} alerta(s) aberto(s): " + "; ".join(a["motivo"] for a in alertas))
    if sat in SATISFACAO_RUIM:
        cuidado.append(f"satisfação {sat}")
    if cuidado:
        return "cuidado", cuidado
    if p.get("fase") in FASES_ONBOARDING:
        return "onboarding", [f"em onboarding ({p['fase']})"]
    if not sat:
        return "sem_dado", ["Status do Projeto vazio no ClickUp"]
    falta = []
    if sat not in SATISFACAO_BOA:
        falta.append(f"satisfação '{sat}' fora da escala conhecida")
    if not p.get("fase"):
        falta.append("fase vazia no ClickUp")
    if not em_dia or p.get("situacao_reuniao") == "No show":
        falta.append(f"reunião mensal: {texto_reuniao}")
    if falta:
        return "quase", falta
    return "saudavel", [f"satisfação {sat}", "sem alerta aberto", "reunião mensal em dia"]


def _montar_carteira():
    ativos = [t for t in _ler(clickup.LISTA_PERFIL_ID) if t.get("status", {}).get("status") == "ativo"]
    alertas = _por_cliente(_ler(clickup.LISTA_ALERTAS_ID), "Alerta")
    registros = _por_cliente(_ler(clickup.LISTA_TAREFAS_CLIENTES_ID, fechadas=True), "Tarefas - Clientes")
    reunioes = _por_cliente(_ler(LISTA_REUNIOES_ID), "Reunião - Clientes")
    clientes = []
    for t in ativos:
        p = _perfil(t)
        abertos = [_alerta(x) for x in alertas.get(t["id"], [])]
        p["proxima_reuniao"] = _proxima_reuniao(reunioes.get(t["id"], []))
        em_dia, p["reuniao_mensal"] = _reuniao_mensal(p, p["proxima_reuniao"])
        p["classe"], p["motivos"] = _classificar(p, abertos, em_dia, p["reuniao_mensal"])
        p["alertas_abertos"] = abertos
        p["insatisfeito_sem_alerta"] = p.get("satisfacao") in SATISFACAO_PIOR and not abertos
        p["ultimo_registro_gestor"] = _ultimo_registro(registros.get(t["id"], []))
        clientes.append(p)
    # Rede: unidades com a mesma marca contam como um cliente; unidade em cuidado segura a rede inteira.
    marcas = collections.Counter(c["rede"] for c in clientes if c["rede"])
    for c in clientes:
        if c["rede"] and marcas[c["rede"]] < 2:
            c["rede"] = None
    em_cuidado = {}
    for c in clientes:
        if c["rede"] and c["classe"] == "cuidado":
            em_cuidado.setdefault(c["rede"], []).append(f"{c['nome']} ({c['codigo']}, {c.get('satisfacao') or 'alerta'})")
    for c in clientes:
        if c["rede"] in em_cuidado and c["classe"] in ("saudavel", "quase"):
            if c["classe"] == "saudavel":
                c["classe"], c["motivos"] = "quase", []
            c["motivos"].append(f"rede {c['rede']} tem unidade em cuidado: " + ", ".join(em_cuidado[c["rede"]]))
    for c in clientes:
        c.pop("_ultima_mensal", None)
        c.pop("_reuniao_do_mes", None)
    clientes.sort(key=lambda c: (ORDEM.index(c["classe"]), c["rede"] or "", c["nome"] or ""))
    return clientes


def _linha(c):
    """Uma linha enxuta por cliente: só o que a skill usa, sem nulos nem links."""
    reg = c.get("ultimo_registro_gestor")
    if c["classe"] in ("onboarding", "sem_dado"):
        campos = {"cliente": c["nome"], "codigo": c["codigo"], "gestor": _primeiros(c["gestor"]), "fase": c["fase"],
                  "produto": "/".join(c["produto"] or []) or None}
    else:
        campos = {
            "cliente": c["nome"], "codigo": c["codigo"], "rede": c["rede"], "gestor": _primeiros(c["gestor"]),
            "lideranca": _primeiros(c["lideranca"]), "produto": "/".join(c["produto"] or []) or None,
            "satisfacao": c["satisfacao"], "meses_de_casa": c["meses_de_casa"], "reuniao_mensal": c["reuniao_mensal"],
            # alerta já vem em "alertas": nos motivos fica só o resto (satisfação, reunião, rede)
            "motivos": [m for m in c["motivos"] if not (c["alertas_abertos"] and "alerta(s) aberto(s)" in m)]
            if c["classe"] != "saudavel" else None,
            "alertas": [{k: a[k] for k in ("motivo", "nivel", "status", "com_quem", "aberto_ha_dias", "incompleto")}
                        for a in c["alertas_abertos"]] or None,
            "insatisfeito_sem_alerta": True if c["insatisfeito_sem_alerta"] else None,
            "ultimo_registro_gestor": f"{date.fromisoformat(reg['data']):%d/%m} {reg['tipo'] or reg['tarefa']}" if reg
            else "nenhum",
        }
    return {k: v for k, v in campos.items() if v not in (None, [], "")}


def cmd_carteira(a):
    clientes = _montar_carteira()
    resumo = {"ativos": len(clientes)}
    for g in ORDEM:
        resumo[g] = sum(1 for c in clientes if c["classe"] == g)
    resumo["redes"] = sorted({c["rede"] for c in clientes if c["rede"]})
    print(f"{len(clientes)} ativos: " + ", ".join(f"{g} {resumo[g]}" for g in ORDEM), file=sys.stderr)
    cab = {"ok": True, "hoje": HOJE.isoformat(), "fonte": "ClickUp, só leitura", "resumo": resumo,
           "aviso": "Resultado de anúncio não está no ClickUp: antes de qualquer oferta, confirmar com o gestor do cliente."}
    if a.completo:
        lib.print_json({**cab, "clientes": clientes})
        return
    # JSON válido com um cliente por linha, saudáveis primeiro (saída curta o bastante para o Claude ler inteira).
    saida = [json.dumps(cab, ensure_ascii=False)[:-1] + ","]
    for i, g in enumerate(ORDEM):
        itens = [_linha(c) for c in clientes if c["classe"] == g]
        saida.append(f'"{g}": [')
        saida += ["  " + json.dumps(x, ensure_ascii=False) + ("," if k < len(itens) - 1 else "") for k, x in enumerate(itens)]
        saida.append("]" + ("," if i < len(ORDEM) - 1 else ""))
    saida.append("}")
    print("\n".join(saida))


def _palavras(texto):
    """Palavras do nome sem acento, maiúscula nem pontuação ('VIVER SORRINDO | ITAPIRA' -> viver, sorrindo, itapira)."""
    return re.sub(r"[^a-z0-9 ]", " ", clickup.normalizar(texto or "")).split()


def _resolver(chave, perfis):
    c = chave.strip()
    if re.fullmatch(r"#?\d+(\.\d+)?", c):
        num = c.lstrip("#")
        achados = [t for t in perfis if str(clickup.valor(t, "Código do Cliente") or "").strip().lstrip("#") == num]
    else:
        alvo = _palavras(c)
        achados = [t for t in perfis if alvo and set(alvo) <= set(_palavras(t.get("name")))]
        exatos = [t for t in achados if _palavras(t.get("name")) == alvo]
        achados = exatos or achados
    ativos = [t for t in achados if t.get("status", {}).get("status") == "ativo"]
    if len(achados) > 1 and ativos:
        achados = ativos
    if not achados:
        nomes = {clickup.normalizar(t.get("name")): t.get("name") for t in perfis if t.get("status", {}).get("status") == "ativo"}
        perto = difflib.get_close_matches(clickup.normalizar(c), list(nomes), n=3, cutoff=0.6)
        perto += [nomes[n] for n in nomes if any(difflib.SequenceMatcher(None, clickup.normalizar(c), p).ratio() > 0.8
                                                  for p in n.split())][:3]
        sugestao = sorted({nomes.get(p, p) for p in perto})
        _falha(f"cliente '{chave}' não encontrado no Perfil de Clientes"
               + (f"; parecidos: {', '.join(sugestao)}" if sugestao else ""), "usar o nome do perfil ou o #código")
    if len(achados) > 1:
        nomes = ", ".join(f"{t.get('name')} ({clickup.valor(t, 'Código do Cliente') or 'sem código'})" for t in achados[:8])
        _falha(f"'{chave}' bate com {len(achados)} perfis: {nomes}", "repetir com o nome completo ou o #código")
    return achados[0]


def cmd_cliente(a):
    t = _resolver(a.cliente, _ler(clickup.LISTA_PERFIL_ID, fechadas=True))
    pid = t["id"]
    p = _perfil(t)
    codigo = str(p.get("codigo") or "").strip()
    no_titulo = re.compile(re.escape(codigo) + r"(?![\d.])") if codigo.startswith("#") else None
    abertos = [_alerta(x) for x in _ler(clickup.LISTA_ALERTAS_ID) if pid in _ligados(x, "Alerta")]
    tarefas = [x for x in _ler(clickup.LISTA_TAREFAS_CLIENTES_ID, fechadas=True) if pid in _ligados(x, "Tarefas - Clientes")]
    conteudos, sem_vinculo = [], []
    for x in _ler(clickup.LISTA_CONTEUDOS_ID, fechadas=True):
        if pid in _ligados(x, "Conteúdo - Clientes"):
            conteudos.append(x)
        elif no_titulo and no_titulo.search(x.get("name") or "") and not _ligados(x, "Conteúdo - Clientes"):
            sem_vinculo.append(x)  # demanda com o #código no título mas sem o cliente ligado no campo
    reunioes = [x for x in _ler(LISTA_REUNIOES_ID, fechadas=True) if pid in _ligados(x, "Reunião - Clientes")]
    proxima = _proxima_reuniao(reunioes)
    em_dia, p["reuniao_mensal"] = _reuniao_mensal(p, proxima)
    classe = _classificar(p, abertos, em_dia, p["reuniao_mensal"])[0] if p.get("status_perfil") == "ativo" else None
    p.pop("_ultima_mensal", None)
    p.pop("_reuniao_do_mes", None)
    fim = lambda x: int(x.get("date_done") or x.get("date_closed") or 0)  # noqa: E731
    passadas = [x for x in reunioes if _dia(x.get("due_date")) and _dia(x.get("due_date")) < HOJE]
    entregues_30d = [x for x in conteudos + sem_vinculo if _fechada(x) and _ha_dias(fim(x)) is not None and _ha_dias(fim(x)) <= 30]
    em_producao = [dict(_tarefa(x, "Tipo de Conteúdo"), sem_vinculo=True) if x in sem_vinculo else _tarefa(x, "Tipo de Conteúdo")
                   for x in conteudos + sem_vinculo if not _fechada(x)]
    saida = {
        "ok": True, "hoje": HOJE.isoformat(), "fonte": "ClickUp, só leitura", "perfil": p, "classe": classe,
        "alertas_abertos": abertos,
        "tarefas_abertas": sorted([_tarefa(x, "Tipo de Tarefa") for x in tarefas if not _fechada(x)], key=lambda x: -x["atraso_dias"]),
        "ultimas_concluidas": [_tarefa(x, "Tipo de Tarefa") for x in sorted([x for x in tarefas if _fechada(x)], key=fim, reverse=True)[:5]],
        "conteudos_em_producao": sorted(em_producao, key=lambda x: -x["atraso_dias"]),
        "conteudos_entregues_30d": {"total": len(entregues_30d),
                                    "ultimos": [_tarefa(x, "Tipo de Conteúdo") for x in sorted(entregues_30d, key=fim, reverse=True)[:3]]},
        "proxima_reuniao": proxima,
        "ultima_reuniao": _reuniao(max(passadas, key=lambda x: int(x["due_date"]))) if passadas else None,
        "aviso": "Resultado, saldo e anúncio não estão no ClickUp: quem responde com número é o gestor do cliente. "
                 "Alerta, satisfação, status interno e nomes de quem está nas tarefas não vão para o grupo.",
    }
    print(f"{p['nome']}: {len(abertos)} alerta(s) aberto(s), {len(saida['tarefas_abertas'])} tarefa(s) aberta(s), "
          f"{len(em_producao)} conteúdo(s) em produção", file=sys.stderr)
    lib.print_json(saida)


def main():
    p = argparse.ArgumentParser(description="Visão da CS no ClickUp (só leitura).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("carteira"); s.add_argument("--completo", action="store_true"); s.set_defaults(fn=cmd_carteira)
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
