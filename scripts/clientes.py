#!/usr/bin/env python3
"""
meta-ads-odontorise: cadastro de clientes.

Lê o Perfil de Clientes no ClickUp (token pessoal do gestor, só leitura) e mantém o
cadastro local em ~/OdontoRise/meta-ads/contas-odontorise.json com o que serve para
operar a conta. A conta de anúncio do Meta (act_) é confirmada pelo gestor.

Subcomandos:
  buscar        --nome X                     perfis do ClickUp cujo nome contém X
  meus [--gestor NOME]                       perfis em que o campo Gestor é o dono do token (ou o gestor indicado, para o head)
  cadastrar     --nome X [--task ID] [--account act_X] [--sem-conta] [--carteira]
                (--carteira: só o head, para cadastrar cliente de outro gestor)
  definir-conta --cliente X --account act_X  grava/troca a conta Meta de um cliente cadastrado
  listar                                     cadastro local
  remover       --cliente X

Saída em JSON no stdout. Nada é escrito no ClickUp.
"""

import argparse
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import clickup, watchlist  # noqa: E402

STOP = {"clinica", "odontologia", "odontologica", "instituto", "dr", "dra", "doutor", "doutora", "ca", "conta", "de", "da", "do", "e"}


def falha(msg, acao=None, code=1):
    out = {"ok": False, "erro": lib.redigir(msg)}
    if acao:
        out["acao"] = acao
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(code)


def _tokens(nome):
    return {w for w in clickup.normalizar(nome).split() if len(w) >= 4 and w not in STOP}


def contas_meta_visiveis():
    """Contas de anúncio que o token da pessoa enxerga (nome + id), sem detalhes."""
    contas, after = [], None
    while True:
        params = {"fields": "account_id,name", "limit": 200}
        if after:
            params["after"] = after
        ok, d = lib.graph_get("me/adaccounts", params=params)
        if not ok:
            return False, d
        contas.extend(d.get("data", []))
        after = d.get("paging", {}).get("cursors", {}).get("after")
        if not after or "next" not in d.get("paging", {}):
            break
    return True, contas


def candidatos_meta(perfil, contas):
    """Contas cujo nome compartilha uma palavra significativa com o nome do cliente."""
    alvo = _tokens(perfil.get("nome")) | ({perfil["instagram_user"]} if perfil.get("instagram_user") else set())
    cands = []
    for c in contas:
        toks = _tokens(c.get("name"))
        if alvo & toks:
            cands.append({"act_id": f"act_{c['account_id']}", "nome": c.get("name"), "em_comum": sorted(alvo & toks)})
    return cands


def conferir_conta(act_id):
    """Confirma que a conta existe e que a pessoa a enxerga; devolve nome e Instagram vinculado."""
    ok, d = lib.graph_get(act_id, params={"fields": "name,account_status,instagram_accounts{username}"})
    if not ok:
        return False, d
    igs = [i.get("username") for i in d.get("instagram_accounts", {}).get("data", [])]
    return True, {"act_id": act_id, "act_nome": d.get("name"), "status": d.get("account_status"), "instagrams": igs}


# ---------------------------------------------------------------------------

def cmd_buscar(a):
    ok, achados = clickup.buscar(a.nome)
    if not ok:
        falha(achados.get("erro"), "conferir a internet e o token do ClickUp (passo 8)")
    lib.print_json({"ok": True, "quantidade": len(achados), "perfis": [clickup.resumo_perfil(t) for t in achados]})


def cmd_meus(a):
    uid, nome = clickup.quem_sou()
    if not uid:
        falha("não consegui identificar o dono do token do ClickUp", "conferir o token (passo 8)")
    ok, todos = clickup.perfis()
    if not ok:
        falha(todos.get("erro"))
    if a.gestor:
        alvo = clickup.normalizar(a.gestor)
        meus = [clickup.resumo_perfil(t) for t in todos if any(alvo in clickup.normalizar(g) for g in (clickup.resumo_perfil(t).get("gestor") or []))]
        nome = f"gestor {a.gestor}"
    else:
        meus = [clickup.resumo_perfil(t) for t in todos if uid in clickup.gestor_ids(t)]
    ativos = [p for p in meus if p.get("status") == "ativo"]
    dados = watchlist.carregar()
    cadastrados = {c.get("clickup_task_id") for c in dados["clientes"]}
    for p in meus:
        p["cadastrado"] = p["clickup_task_id"] in cadastrados
    lib.print_json({"ok": True, "gestor": nome, "total": len(meus), "ativos": len(ativos),
                    "sem_cadastro_local": sum(1 for p in meus if not p["cadastrado"]), "perfis": meus})


def cmd_cadastrar(a):
    ok, achados = clickup.buscar(a.nome)
    if not ok:
        falha(achados.get("erro"), "conferir a internet e o token do ClickUp (passo 8)")
    if a.task:
        achados = [t for t in achados if t.get("id") == a.task]
    if not achados:
        falha(f"nenhum perfil no ClickUp com '{a.nome}'", "conferir o nome em Perfil de Clientes ou usar 'buscar --nome' com um trecho")
    if len(achados) > 1:
        print(json.dumps({"ok": False, "erro": "mais de um perfil encontrado; repita com --task <id>",
                          "perfis": [{"task": t["id"], "nome": t["name"], "status": t["status"]["status"]} for t in achados]},
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    perfil = clickup.resumo_perfil(achados[0])
    perfil["slug"] = watchlist.slugify(perfil["nome"])
    resultado = {"ok": True, "cliente": perfil}

    # Regra da casa: cada pessoa só cadastra (e depois opera) os clientes que cuida.
    # O head cadastra a carteira dos gestores com --carteira.
    uid, _eu = clickup.quem_sou()
    donos = clickup.gestor_ids(achados[0])
    gestores = ", ".join(perfil.get("gestor") or []) or "ninguém"
    if uid and donos and uid not in donos:
        if not a.carteira:
            falha(f"no ClickUp o gestor de '{perfil['nome']}' é {gestores}, não você",
                  "cada pessoa só opera os clientes que cuida; se você é o head cadastrando a carteira, repita com --carteira")
        resultado["aviso_escopo"] = f"cadastrado como carteira do head: o gestor deste cliente no ClickUp é {gestores}"
    elif not donos:
        resultado["aviso_escopo"] = "o perfil não tem Gestor definido no ClickUp; confira com o head antes de operar"

    if a.account:
        act = a.account if a.account.startswith("act_") else f"act_{a.account}"
        ok, info = conferir_conta(act)
        if not ok:
            falha(f"a conta {act} não está acessível para você ({info.get('erro')})",
                  "conferir o id e se a conta aparece para você na Business Manager (passo 6, parte 1)")
        perfil["act_id"], perfil["act_nome"] = info["act_id"], info["act_nome"]
        if perfil.get("instagram_user") and info["instagrams"] and perfil["instagram_user"] not in [i.lower() for i in info["instagrams"]]:
            resultado["aviso"] = f"o Instagram do perfil ({perfil['instagram_user']}) não é o vinculado à conta ({', '.join(info['instagrams'])}); confira"
    else:
        ok, contas = contas_meta_visiveis()
        if not ok:
            falha(contas.get("erro"), "conferir a credencial do Meta (setup)")
        cands = candidatos_meta(perfil, contas)
        perfil["act_id"] = None
        resultado["contas_candidatas"] = cands
        resultado["acao"] = ("confirme a conta com: clientes.py definir-conta --cliente "
                             f"{perfil['slug']} --account act_XXX" + (" (candidatas acima)" if cands else " (nenhuma candidata pelo nome; escolha na lista do setup)"))
        if not a.sem_conta and not cands:
            resultado["aviso"] = "cadastrado sem conta Meta; defina a conta antes de operar"

    dados = watchlist.carregar()
    salvo, novo = watchlist.upsert(dados, perfil)
    watchlist.salvar(dados)
    resultado["novo"] = novo
    resultado["arquivo"] = watchlist.CADASTRO_PATH
    lib.print_json(resultado)


def cmd_definir_conta(a):
    dados = watchlist.carregar()
    c = watchlist.resolver(dados, a.cliente)
    if not c:
        falha(f"cliente '{a.cliente}' não está no cadastro local", "cadastrar primeiro com: clientes.py cadastrar --nome ...")
    act = a.account if a.account.startswith("act_") else f"act_{a.account}"
    ok, info = conferir_conta(act)
    if not ok:
        falha(f"a conta {act} não está acessível para você ({info.get('erro')})",
              "conferir o id e se a conta aparece para você na Business Manager (passo 6, parte 1)")
    c["act_id"], c["act_nome"] = info["act_id"], info["act_nome"]
    if info["instagrams"]:
        c["instagram_vinculado"] = info["instagrams"]
    watchlist.salvar(dados)
    lib.print_json({"ok": True, "cliente": c})


def cmd_listar(a):
    dados = watchlist.carregar()
    lib.print_json({"ok": True, "atualizado": dados.get("atualizado"), "quantidade": len(dados["clientes"]),
                    "sem_conta_meta": sum(1 for c in dados["clientes"] if not c.get("act_id")), "clientes": dados["clientes"]})


def cmd_remover(a):
    dados = watchlist.carregar()
    c = watchlist.resolver(dados, a.cliente)
    if not c:
        falha(f"cliente '{a.cliente}' não está no cadastro local")
    dados["clientes"] = [x for x in dados["clientes"] if x is not c]
    watchlist.salvar(dados)
    lib.print_json({"ok": True, "removido": c.get("nome"), "restam": len(dados["clientes"])})


def main():
    p = argparse.ArgumentParser(description="Cadastro de clientes (ClickUp -> arquivo local)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("buscar"); s.add_argument("--nome", required=True); s.set_defaults(fn=cmd_buscar)
    s = sub.add_parser("meus"); s.add_argument("--gestor", help="perfis de outro gestor, pelo nome (para o head)"); s.set_defaults(fn=cmd_meus)
    s = sub.add_parser("cadastrar"); s.add_argument("--nome", required=True); s.add_argument("--task"); s.add_argument("--account"); s.add_argument("--sem-conta", action="store_true"); s.add_argument("--carteira", action="store_true", help="head: cadastrar cliente de outro gestor"); s.set_defaults(fn=cmd_cadastrar)
    s = sub.add_parser("definir-conta"); s.add_argument("--cliente", required=True); s.add_argument("--account", required=True); s.set_defaults(fn=cmd_definir_conta)
    s = sub.add_parser("listar"); s.set_defaults(fn=cmd_listar)
    s = sub.add_parser("remover"); s.add_argument("--cliente", required=True); s.set_defaults(fn=cmd_remover)
    a = p.parse_args()
    try:
        a.fn(a)
    except SystemExit:
        raise
    except Exception as e:  # nunca imprimir str(e) cru
        falha(f"erro interno ({type(e).__name__}): {lib.redigir(e)}", code=2)


if __name__ == "__main__":
    main()
