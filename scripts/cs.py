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
  cs.py alertas                   visão resumida da lista Clientes em Alerta: cada alerta com o cliente, o perfil, as ações,
                                  os últimos comentários, o contexto e o que falta saber (base de /clientes-criticos da CS)

Nunca lê nem devolve valores (contrato, ticket, faturamento, verba), CPF/CNPJ, telefone, e-mail, endereço ou
nascimento. Comentários só dos alertas (resumo interno da CS), cortados e com e-mail, telefone, CPF, CNPJ e valores
mascarados. Resultado de anúncio não está no ClickUp: quem confirma é o gestor.
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
SATISFACAO_TOPO = ("Muito Satisfeito (Promotor)", "Embaixador da Odontorise")  # Start + topo = candidato a Select
FASES_ONBOARDING = ("ONB1", "ONB2")
REUNIAO_MENSAL_DIAS = 45  # última reunião mensal feita há mais que isso, sem outra agendada = atrasada
ORDEM = ("saudavel", "quase", "cuidado", "onboarding", "sem_dado")


_SENSIVEL = [
    (re.compile(r"https?://\S+"), "[link]"),
    (re.compile(r"\b(?:www\.)?[\w-]+(?:\.[\w-]+)*\.(?:com|br|io|app|net|org)(?:/\S*)?", re.I), "[link]"),
    (re.compile(r"\b[\w-]+\.(?:png|jpe?g|gif|webp|pdf)\b", re.I), ""),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[e-mail]"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "[CNPJ]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"), "[telefone]"),
    (re.compile(r"R\$\s?[\d.,]+"), "R$ [valor]"),
]


def _limpo(texto, n):
    """Texto numa linha, com dado sensível mascarado e cortado em n caracteres."""
    t = " ".join((texto or "").split())
    for rx, sub in _SENSIVEL:
        t = rx.sub(sub, t)
    return t[:n] + ("..." if len(t) > n else "")


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
            "fonte": "lista Reuniões com Clientes", "url": t.get("url")}


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


def _alertas_maes(tarefas):
    """Alertas (tarefas-mãe da lista) e as ações de cada um (subtarefas)."""
    ids = {t["id"] for t in tarefas}
    filhas = collections.defaultdict(list)
    for t in tarefas:
        if t.get("parent") in ids:
            filhas[t["parent"]].append(t)
    return [t for t in tarefas if t.get("parent") not in ids], filhas


def _cliente_do_alerta(t, perfis, ativos):
    """(id do perfil, como achou): campo Alerta; senão o id no título ("Alerta - Nome [#id]"); senão o nome do título."""
    pid = (_ligados(t, "Alerta") or [None])[0]
    if pid:
        return pid, "campo Alerta"
    m = re.search(r"\[#(\w+)\]", t.get("name") or "")
    if m and m.group(1) in perfis:
        return m.group(1), "id no título"
    nome = re.sub(r"^\s*alerta\s*-\s*|\[#\w+\]", "", t.get("name") or "", flags=re.I)
    achados = [x for x in ativos if _palavras(nome) and set(_palavras(nome)) <= set(_palavras(x.get("name")))]
    return (achados[0]["id"], "nome no título") if len(achados) == 1 else (None, None)


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
    perfis = {t["id"]: t for t in _ler(clickup.LISTA_PERFIL_ID)}
    ativos = [t for t in perfis.values() if t.get("status", {}).get("status") == "ativo"]
    alertas = collections.defaultdict(list)
    for t in _alertas_maes(_ler(clickup.LISTA_ALERTAS_ID))[0]:
        pid = _cliente_do_alerta(t, perfis, ativos)[0]
        if pid:
            alertas[pid].append(t)
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
    # Marcas diferentes com o mesmo gestor, a mesma especialidade e a mesma reunião do mês em todas as unidades
    # (reunião conjunta) contam como um grupo só. É conservador: a unidade em cuidado segura o grupo inteiro,
    # e a skill pede para confirmar com o gestor se é o mesmo dono.
    assinaturas = {}
    for marca in sorted({c["rede"] for c in clientes if c["rede"]}):
        chaves = {(tuple(c["gestor"] or []), c["_reuniao_do_mes"], c.get("especialidade")) for c in clientes if c["rede"] == marca}
        if len(chaves) == 1 and next(iter(chaves))[1]:
            assinaturas.setdefault(next(iter(chaves)), []).append(marca)
    juntas = {m: " + ".join(ms) for ms in assinaturas.values() if len(ms) > 1 for m in ms}
    for c in clientes:
        if c["rede"] in juntas:
            c["rede"] = juntas[c["rede"]]
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
    neutro_sem_alerta = c["classe"] == "cuidado" and not c["alertas_abertos"] and not c["insatisfeito_sem_alerta"]
    if c["classe"] == "sem_dado" or neutro_sem_alerta:
        campos = {"cliente": c["nome"], "codigo": c["codigo"], "gestor": _primeiros(c["gestor"]),
                  "neutro_sem_alerta": True if neutro_sem_alerta else None}
    else:
        produto = "/".join(c["produto"] or []) or None
        campos = {
            "cliente": c["nome"], "codigo": c["codigo"], "rede": c["rede"], "gestor": _primeiros(c["gestor"]),
            "lideranca": _primeiros(c["lideranca"]) if c["classe"] == "cuidado" else None,
            "produto": produto, "satisfacao": c["satisfacao"], "reuniao_mensal": c["reuniao_mensal"],
            "candidato_select": True if c["classe"] == "saudavel" and produto == "Start"
            and c["satisfacao"] in SATISFACAO_TOPO else None,
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
    if any(" + " in r for r in resumo["redes"]):
        resumo["aviso_redes"] = ("rede com '+' junta marcas com o mesmo gestor e a mesma reunião mensal: "
                                 "confirmar com o gestor se é o mesmo dono")
    resumo["onboarding_por_gestor"] = dict(collections.Counter(
        ", ".join(_primeiros(c["gestor"])) or "sem gestor" for c in clientes if c["classe"] == "onboarding"))
    print(f"{len(clientes)} ativos: " + ", ".join(f"{g} {resumo[g]}" for g in ORDEM), file=sys.stderr)
    cab = {"ok": True, "hoje": HOJE.isoformat(), "fonte": "ClickUp, só leitura", "resumo": resumo,
           "aviso": "Resultado de anúncio não está no ClickUp: antes de qualquer oferta, confirmar com o gestor do cliente."}
    if a.completo:
        lib.print_json({**cab, "clientes": clientes})
        return
    # JSON válido com um cliente por linha, saudáveis primeiro (saída curta o bastante para o Claude ler inteira).
    saida = [json.dumps(cab, ensure_ascii=False)[:-1] + ","]
    grupos = [g for g in ORDEM if g != "onboarding"]  # onboarding vai só como contagem no resumo
    for i, g in enumerate(grupos):
        itens = [_linha(c) for c in clientes if c["classe"] == g]
        saida.append(f'"{g}": [')
        saida += ["  " + json.dumps(x, ensure_ascii=False) + ("," if k < len(itens) - 1 else "") for k, x in enumerate(itens)]
        saida.append("]" + ("," if i < len(grupos) - 1 else ""))
    saida.append("}")
    texto = "\n".join(saida)
    if len(texto) > 28000:
        print(f"AVISO: saída com {len(texto)} caracteres, perto do limite de leitura do Claude; enxugar _linha.", file=sys.stderr)
    print(texto)


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
    todos = _ler(clickup.LISTA_PERFIL_ID, fechadas=True)
    t = _resolver(a.cliente, todos)
    pid = t["id"]
    perfis = {x["id"]: x for x in todos}
    ativos = [x for x in todos if x.get("status", {}).get("status") == "ativo"]
    p = _perfil(t)
    codigo = str(p.get("codigo") or "").strip()
    no_titulo = re.compile(re.escape(codigo) + r"(?![\d.])") if codigo.startswith("#") else None
    abertos = [_alerta(x) for x in _alertas_maes(_ler(clickup.LISTA_ALERTAS_ID))[0]
               if _cliente_do_alerta(x, perfis, ativos)[0] == pid]
    tarefas = [x for x in _ler(clickup.LISTA_TAREFAS_CLIENTES_ID, fechadas=True) if pid in _ligados(x, "Tarefas - Clientes")]
    conteudos, sem_vinculo = [], []
    for x in _ler(clickup.LISTA_CONTEUDOS_ID, fechadas=True):
        if pid in _ligados(x, "Conteúdo - Clientes"):
            conteudos.append(x)
        elif no_titulo and no_titulo.search(x.get("name") or "") and not _ligados(x, "Conteúdo - Clientes"):
            sem_vinculo.append(x)  # demanda com o #código no título mas sem o cliente ligado no campo
    reunioes = [x for x in _ler(LISTA_REUNIOES_ID, fechadas=True) if pid in _ligados(x, "Reunião - Clientes")]
    proxima = _proxima_reuniao(reunioes)
    mes = p["_reuniao_do_mes"]
    if not proxima and p.get("situacao_reuniao") == "Agendada" and mes and mes >= HOJE:
        # sem evento na lista Reuniões com Clientes: a data vem só do perfil e precisa ser conferida na agenda
        proxima = {"data": mes.isoformat(), "tipo": "Reunião mensal", "status": "agendada no perfil", "fonte": "perfil"}
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


def cmd_alertas(a):
    _, voce = clickup.quem_sou()  # quem roda a skill: nunca vira sugestão de "com quem conversar"
    voce = (voce or "").split()[0] if voce else None
    tarefas = _ler(clickup.LISTA_ALERTAS_ID)
    perfis = {t["id"]: t for t in _ler(clickup.LISTA_PERFIL_ID, fechadas=True)}
    ativos = [t for t in perfis.values() if t.get("status", {}).get("status") == "ativo"]
    registros = _por_cliente(_ler(clickup.LISTA_TAREFAS_CLIENTES_ID, fechadas=True), "Tarefas - Clientes")
    conteudos = _por_cliente(_ler(clickup.LISTA_CONTEUDOS_ID), "Conteúdo - Clientes")
    reunioes = _por_cliente(_ler(LISTA_REUNIOES_ID), "Reunião - Clientes")
    maes, filhas = _alertas_maes(tarefas)
    itens = []
    for t in maes:
        pid, origem = _cliente_do_alerta(t, perfis, ativos)
        ok, c = clickup.get(f"task/{t['id']}/comment")
        coms = sorted(c.get("comments", []) if ok else [], key=lambda x: int(x.get("date", 0)), reverse=True)
        mov = max([int(x.get("date_updated") or 0) for x in [t] + filhas[t["id"]]] + [int(x.get("date", 0)) for x in coms])
        alerta = _alerta(t)
        churn = alerta["status"] == "churn"
        motivo = alerta["motivo"] if alerta["motivo"] != "não preenchido" else "sem motivo marcado"
        item = {"alerta": t.get("name"), "url": t.get("url"), "churn": True if churn else None,
                "motivo": motivo, "nivel": alerta["nivel"], "status": alerta["status"],
                "com_quem": [n for n in alerta["com_quem"] if n != voce] or None,
                "aberto_ha_dias": alerta["aberto_ha_dias"], "parado_ha_dias": _ha_dias(mov), "vence_em": alerta["vence_em"],
                "descricao": _limpo(t.get("text_content") or t.get("description"), 300) or None,
                # o comentário mais recente vai quase inteiro (traz contexto e próximos passos); o anterior, curto
                "ultimos_comentarios": [{"quem": _primeiros([x.get("user", {}).get("username")]), "ha_dias": _ha_dias(x.get("date")),
                                         "texto": _limpo(x.get("comment_text"), 600 if k == 0 else 250)} for k, x in enumerate(coms[:2])],
                "acoes": [{"acao": f.get("name"), "status": _status(f),
                           "com_quem": _primeiros(y.get("username") for y in f.get("assignees", [])),
                           "vence_em": _iso(f.get("due_date")),
                           "atraso_dias": (HOJE - _dia(f["due_date"])).days if f.get("due_date") and _dia(f["due_date"]) < HOJE and not _fechada(f) else 0}
                          for f in filhas[t["id"]]]}
        falta = []
        if pid in perfis:
            p = _perfil(perfis[pid])
            prox = _proxima_reuniao(reunioes.get(pid, []))
            _, reuniao = _reuniao_mensal(p, prox)
            reg = _ultimo_registro(registros.get(pid, []))
            atrasados = [x for x in conteudos.get(pid, []) if _dia(x.get("due_date")) and _dia(x.get("due_date")) < HOJE]
            item.update({"cliente": p["nome"], "codigo": p["codigo"], "cliente_achado_por": origem,
                         "status_perfil": p["status_perfil"], "gestor": _primeiros(p["gestor"]),
                         "lideranca": _primeiros(p["lideranca"]), "cs": _primeiros(p["cs"]),
                         "produto": "/".join(p["produto"] or []) or None, "fase": p["fase"], "satisfacao": p["satisfacao"],
                         "reuniao_mensal": reuniao,
                         "ultimo_registro_gestor": f"{date.fromisoformat(reg['data']):%d/%m} {reg['tipo'] or reg['tarefa']}" if reg else "nenhum",
                         "conteudos_atrasados": len(atrasados)})
        else:
            falta.append("qual é o cliente (o alerta não está ligado a um perfil)")
        escrito = bool(coms or item["descricao"])
        if not churn:  # cliente em churn já saiu: nada a perguntar
            if not escrito:
                falta.append("o que aconteceu e o que já foi feito (nada escrito no alerta)")
            if not item["acoes"] and not escrito and alerta["status"] in ("em cadastro", "delegado", "em execução"):
                falta.append("o próximo passo combinado")
        item["falta_saber"] = falta
        itens.append({k: v for k, v in item.items() if v not in (None, [], "")})
    itens.sort(key=lambda x: (bool(x.get("churn")), -(x.get("parado_ha_dias") or 0)))
    ativos_alerta = [i for i in itens if not i.get("churn")]
    resumo = {"alertas": len(itens), "em_churn": len(itens) - len(ativos_alerta),
              "parados_5_dias_ou_mais_fora_do_churn": sum(1 for i in ativos_alerta if (i.get("parado_ha_dias") or 0) >= 5),
              "por_motivo": dict(collections.Counter(i["motivo"] for i in itens)),
              "por_status": dict(collections.Counter(i["status"] for i in itens)),
              "com_informacao_faltando": sum(1 for i in itens if i.get("falta_saber"))}
    print(f"{len(itens)} alerta(s), {resumo['em_churn']} em churn, {resumo['parados_5_dias_ou_mais_fora_do_churn']} "
          "parado(s) há 5 dias ou mais fora do churn", file=sys.stderr)
    cab = {"ok": True, "hoje": HOJE.isoformat(), "voce": voce, "fonte": "ClickUp, lista Clientes em Alerta, só leitura", "resumo": resumo,
           "aviso": "Resumo interno da CS: alerta, satisfação e comentários nunca vão para grupo ou cliente."}
    linhas = [json.dumps(cab, ensure_ascii=False)[:-1] + ',', '"itens": [']
    linhas += ["  " + json.dumps(i, ensure_ascii=False) + ("," if k < len(itens) - 1 else "") for k, i in enumerate(itens)]
    print("\n".join(linhas + ["]}"]))


def main():
    p = argparse.ArgumentParser(description="Visão da CS no ClickUp (só leitura).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("carteira"); s.add_argument("--completo", action="store_true"); s.set_defaults(fn=cmd_carteira)
    s = sub.add_parser("cliente"); s.add_argument("--cliente", required=True); s.set_defaults(fn=cmd_cliente)
    s = sub.add_parser("alertas"); s.set_defaults(fn=cmd_alertas)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        _falha(f"erro interno: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
