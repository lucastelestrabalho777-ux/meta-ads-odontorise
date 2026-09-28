#!/usr/bin/env python3
"""
meta-ads-odontorise: conferência do ambiente.

Roda depois do passo 6 do guia e sempre que algo parar de funcionar.
Confere programas, arquivo de credencial, validade do token, conexão com a Meta
e quantas contas de anúncio a pessoa enxerga. Não altera nada.

Uso:
  python3 scripts/setup.py          saída para pessoas (no Windows: python)
  python3 scripts/setup.py --json   saída para o Claude

Códigos de saída: 0 tudo pronto · 1 há pendência · 2 erro interno
"""

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

PYTHON_MINIMO = (3, 11)   # igual ao que o passo 3 do guia pede
SDK_VERSAO = "26.0.2"

# As nove permissões que o passo 6 do guia manda marcar ao gerar o token.
PERMISSOES_ESPERADAS = [
    "ads_management", "ads_read", "business_management",
    "pages_show_list", "pages_read_engagement", "pages_manage_ads",
    "pages_read_user_content", "instagram_basic", "instagram_manage_insights",
]

GUIA = lib.ONDE_GUIA            # "Guia de IA OdontoRise, página Onboarding, passo 6"
BM_ODONTORISE = "666777657534959"
CADASTRO = os.path.expanduser("~/OdontoRise/meta-ads/contas-odontorise.json")
PY = os.path.basename(sys.executable) or "python3"
CMD_SDK = f"{PY} -m pip install --user facebook-business=={SDK_VERSAO}"


class Relatorio:
    def __init__(self, como_json):
        self.como_json = como_json
        self.itens = []
        self.pendencias = []

    def secao(self, titulo):
        if not self.como_json:
            print(f"\n{titulo}")

    def ok(self, secao, texto):
        self._add(secao, "OK", texto)

    def aviso(self, secao, texto, acao=None):
        self._add(secao, "AVISO", texto, acao)

    def falhou(self, secao, texto, acao=None):
        self._add(secao, "FALHOU", texto, acao)
        self.pendencias.append({"o_que": texto, "acao": acao})

    def pulado(self, secao, motivo):
        self._add(secao, "PULADO", motivo)

    def _add(self, secao, status, texto, acao=None, detalhe=None):
        self.itens.append({"secao": secao, "status": status, "texto": texto, "acao": acao})
        if not self.como_json:
            print(f"  [{status}] {texto}")
            if acao:
                print(f"           -> {acao}")

    @property
    def avisos(self):
        return [i for i in self.itens if i["status"] == "AVISO"]


# ---------------------------------------------------------------------------
# 1. Programas
# ---------------------------------------------------------------------------

def check_programas(rel):
    rel.secao("1. Programas")
    v = sys.version_info
    if (v.major, v.minor) >= PYTHON_MINIMO:
        rel.ok("programas", f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        rel.falhou("programas", f"Python {v.major}.{v.minor} é antigo (o guia pede {PYTHON_MINIMO[0]}.{PYTHON_MINIMO[1]} ou mais novo)",
                   "instalar pelo passo 3 do guia (Mac: brew install python; Windows: winget install Python.Python.3.12) e abrir um terminal novo")
    try:
        import facebook_business
        rel.ok("programas", f"biblioteca da Meta (facebook-business {getattr(facebook_business, '__version__', '?')})")
    except ImportError:
        rel.falhou("programas", "biblioteca da Meta (facebook-business) não instalada",
                   f"no terminal, rodar: {CMD_SDK} (se aparecer externally-managed-environment, repita acrescentando --break-system-packages no final). Esse programa não está no passo 3 do guia, é instalado só aqui.")
    try:
        import requests
        rel.ok("programas", f"requests {requests.__version__}")
        return True
    except ImportError:
        rel.falhou("programas", "biblioteca requests não instalada", f"no terminal, rodar: {PY} -m pip install --user requests")
        return False


# ---------------------------------------------------------------------------
# 2. Credencial
# ---------------------------------------------------------------------------

def check_credencial(rel):
    rel.secao("2. Credencial")
    path = lib.CRED_PATH
    if not os.path.isfile(path):
        rel.falhou("credencial", f"arquivo não encontrado: {path}",
                   f"criar o arquivo seguindo o {GUIA}, parte 4")
        return None
    rel.ok("credencial", f"arquivo encontrado: {path}")

    status, texto = lib.checar_permissao(path)
    if status == "ok":
        rel.ok("credencial", texto)
    elif status == "nao_verificado":
        rel.aviso("credencial", texto, "manter o arquivo dentro da sua pasta de usuário, fora de pastas compartilhadas ou sincronizadas")
    elif status == "dono":
        rel.falhou("credencial", texto, f"no terminal, rodar: chown $(whoami) {path} && chmod 600 {path}")
    else:
        rel.falhou("credencial", texto, f"no terminal, rodar: chmod 600 {path}")

    try:
        c = lib.load_credentials()
    except (OSError, UnicodeDecodeError) as e:
        rel.falhou("credencial", f"não consegui ler o arquivo ({type(e).__name__})",
                   "salvar o arquivo como UTF-8 e conferir a permissão")
        return None

    faltando = [k for k in ("META_ACCESS_TOKEN", "META_APP_ID", "META_APP_SECRET", "META_BM_ID") if lib._is_placeholder(c.get(k, ""))]
    if faltando:
        rel.falhou("credencial", "linhas vazias ou com valor de exemplo: " + ", ".join(faltando),
                   f"abrir o arquivo ({GUIA}, parte 4) e trocar essas linhas pelos seus valores: ID e chave secreta do app vêm da parte 2, o token de 60 dias vem da parte 3")
        return None
    mask = "" if rel.como_json else f" ({lib.mask_token(c['META_ACCESS_TOKEN'])})"
    rel.ok("credencial", f"META_ACCESS_TOKEN preenchido{mask}")
    rel.ok("credencial", f"META_APP_ID e META_APP_SECRET preenchidos (app {c['META_APP_ID']})")
    if c["META_BM_ID"] == BM_ODONTORISE:
        rel.ok("credencial", f"META_BM_ID = {c['META_BM_ID']} (BM OdontoRise)")
    else:
        rel.aviso("credencial", f"META_BM_ID = {c['META_BM_ID']} não é a BM da OdontoRise ({BM_ODONTORISE})",
                  "conferir a linha META_BM_ID no arquivo")
    return c


# ---------------------------------------------------------------------------
# 3. Token
# ---------------------------------------------------------------------------

def _motivo_token(info):
    code = info.get("code")
    msg = (info.get("erro") or "").lower()
    if info.get("rede"):
        return "não consegui falar com a Meta para conferir o token (sem internet ou rede bloqueada)", "conferir a conexão e rodar de novo"
    if code == 100 or "owner or developer of the app" in msg:
        return ("este token não foi gerado pelo seu aplicativo (META_APP_ID no arquivo)",
                f"no Explorador da Graph API, escolha o SEU app no menu App da Meta antes de gerar o token ({GUIA}, parte 3, item 2); se o app estiver certo, confira se META_APP_ID e META_APP_SECRET são do mesmo aplicativo (parte 2)")
    if "signature" in msg:
        return ("a chave secreta do app (META_APP_SECRET) não confere com o aplicativo",
                f"copiar de novo a chave secreta em Configurações do app, Básico, Mostrar ({GUIA}, parte 2, item 5) e colar no arquivo (parte 4)")
    if "validating application" in msg or "application info" in msg:
        return ("o ID do app (META_APP_ID) não existe ou não é o seu",
                f"copiar de novo o ID do app em Configurações do app, Básico ({GUIA}, parte 2, item 5) e colar no arquivo (parte 4)")
    if "malformed" in msg or "cannot parse" in msg:
        return ("o token está incompleto ou foi colado errado",
                f"copiar o token de novo, inteiro e sem espaços, e colar na primeira linha do arquivo ({GUIA}, partes 3 e 4)")
    if code in (190, 463) or "expired" in msg:
        return "o token venceu", f"gerar um token novo pelo {GUIA}, parte 3, e trocar a primeira linha do arquivo (parte 4)"
    if code == 460 or "password" in msg:
        return "a senha do Facebook foi trocada e o token caiu", f"gerar um token novo pelo {GUIA}, parte 3, e trocar a primeira linha do arquivo (parte 4)"
    if "valor de exemplo" in msg or "ausentes" in msg:
        return info.get("erro"), f"preencher o arquivo ({GUIA}, parte 4)"
    return "a Meta marcou o token como inválido", f"gerar um token novo pelo {GUIA}, parte 3, e trocar a primeira linha do arquivo (parte 4)"


def check_token(rel):
    rel.secao("3. Token")
    info = lib.token_info()
    if not info.get("ok"):
        texto, acao = _motivo_token(info)
        rel.falhou("token", f"token vencido ou inválido: {texto}", acao)
        return info

    dias = info.get("dias_restantes")
    tipo = info.get("tipo_texto", "token")
    renovar = f"gerar um token novo pelo {GUIA}, parte 3, e trocar a primeira linha do arquivo (parte 4)"
    if dias is None:
        rel.ok("token", f"{tipo} válido, não vence")
    elif dias < 0:
        rel.falhou("token", f"{tipo} venceu em {info['expira_em']}", renovar)
    elif dias <= 10:
        rel.falhou("token", f"{tipo} vence em {info['expira_em']} (faltam {dias} dias)", "gerar um token novo agora: " + renovar)
    elif dias <= 20:
        rel.aviso("token", f"{tipo} válido, vence em {info['expira_em']} (faltam {dias} dias)", f"renovar nesta semana: {GUIA}, parte 3")
    else:
        rel.ok("token", f"{tipo} válido, vence em {info['expira_em']} ({dias} dias)")

    if not info.get("app_confere"):
        rel.aviso("token", f"o token foi gerado por outro aplicativo ({info.get('app_id')}), não pelo META_APP_ID do arquivo",
                  f"gerar o token no Explorador com o SEU aplicativo selecionado ({GUIA}, parte 3, item 2)")
    dad = info.get("dias_acesso_a_dados")
    if dad is not None and dad < 0:
        rel.falhou("token", f"a Meta cortou o acesso aos dados deste token em {info['acesso_a_dados_ate']}", renovar)
    elif dad is not None and dad <= 10:
        rel.aviso("token", f"a Meta vai cortar o acesso aos dados deste token em {info['acesso_a_dados_ate']}", f"gerar um token novo antes disso ({GUIA}, parte 3)")

    faltam = [p for p in PERMISSOES_ESPERADAS if p not in info.get("permissoes", [])]
    if faltam:
        rel.aviso("token", "permissões que faltam no token: " + ", ".join(faltam),
                  "ao gerar o próximo token, marcar as nove permissões da tabela do passo 6")
    else:
        rel.ok("token", "as nove permissões do guia estão no token")
    return info


# ---------------------------------------------------------------------------
# 4. Conexão
# ---------------------------------------------------------------------------

def check_conexao(rel):
    rel.secao("4. Conexão com a Meta")
    resultado = {"nome": None, "contas": 0, "amostra": []}

    ok, d = lib.graph_get("me", params={"fields": "id,name"})
    if not ok:
        if d.get("rede"):
            rel.falhou("conexao", "não consegui falar com a Meta (sem internet, rede bloqueada ou a Meta fora do ar)", "conferir a conexão e rodar de novo")
        elif d.get("code") in lib.RATE_LIMIT_CODES:
            rel.aviso("conexao", "limite de chamadas da Meta atingido", "aguardar 60 segundos e rodar de novo")
        else:
            rel.falhou("conexao", f"a Meta recusou o token ({d.get('erro')})", f"gerar um token novo ({GUIA}, parte 3)")
        return resultado
    resultado["nome"] = d.get("name")
    rel.ok("conexao", f"conectado como: {d.get('name')}")

    contas, after = [], None
    while True:
        params = {"fields": "account_id,name", "limit": 200}
        if after:
            params["after"] = after
        ok, d = lib.graph_get("me/adaccounts", params=params)
        if not ok:
            if d.get("code") in lib.RATE_LIMIT_CODES:
                rel.aviso("conexao", "limite de chamadas da Meta atingido ao listar as contas", "aguardar 60 segundos e rodar de novo")
            else:
                rel.falhou("conexao", f"erro ao listar as contas ({d.get('erro')})", f"tentar de novo em 1 minuto; se repetir, gerar um token novo ({GUIA}, parte 3)")
            return resultado
        contas.extend(d.get("data", []))
        after = d.get("paging", {}).get("cursors", {}).get("after")
        if not after or "next" not in d.get("paging", {}):
            break

    resultado["contas"] = len(contas)
    resultado["amostra"] = [f"{c.get('name')} (act_{c.get('account_id')})" for c in contas[:5]]
    if contas:
        rel.ok("conexao", f"{len(contas)} conta(s) de anúncio visíveis")
        if not rel.como_json:
            for linha in resultado["amostra"]:
                print(f"           · {linha}")
            if len(contas) > 5:
                print(f"           · ... e mais {len(contas) - 5}")
    else:
        rel.falhou("conexao", "nenhuma conta de anúncio visível",
                   f"pedir ao administrador da BM para atribuir a você as contas dos seus clientes ({GUIA}, parte 1) e rodar o setup de novo quando ele confirmar")
    return resultado


# ---------------------------------------------------------------------------
# 5. Cadastro de clientes
# ---------------------------------------------------------------------------

def check_cadastro(rel):
    rel.secao("5. Cadastro de clientes")
    if not os.path.isfile(CADASTRO):
        rel.aviso("cadastro", "ainda sem cadastro de clientes (normal na primeira vez)",
                  "a skill pergunta o cliente e monta o cadastro a partir do ClickUp")
        return
    try:
        with open(CADASTRO, encoding="utf-8-sig") as f:
            dados = json.load(f)
        clientes = dados.get("clientes", []) if isinstance(dados, dict) else None
        if clientes is None:
            raise ValueError("formato inesperado")
        rel.ok("cadastro", f"{len(clientes)} cliente(s) cadastrados em {CADASTRO}")
    except (ValueError, OSError, AttributeError, TypeError):
        rel.aviso("cadastro", "o arquivo de cadastro existe mas não abre",
                  f"apagar o arquivo {CADASTRO} e pedir ao Claude: monte o cadastro de clientes de novo a partir do ClickUp")


# ---------------------------------------------------------------------------

def main():
    como_json = "--json" in sys.argv
    rel = Relatorio(como_json)
    if not como_json:
        print("=" * 56)
        print("Conferência do ambiente Meta Ads (OdontoRise)")
        print("Confere programas, credencial, token, conexão e cadastro. Não altera nada.")
        print("=" * 56)

    token = None
    conexao = None
    try:
        tem_requests = check_programas(rel)
        creds = check_credencial(rel)
        if creds and tem_requests:
            token = check_token(rel)
            if token.get("ok"):
                conexao = check_conexao(rel)
            else:
                rel.secao("4. Conexão com a Meta")
                rel.pulado("conexao", "não conferido: depende de um token válido (seção 3)")
        else:
            rel.secao("3. Token")
            rel.pulado("token", "não conferido: resolva a seção 2 (credencial) e rode o setup de novo")
            rel.secao("4. Conexão com a Meta")
            rel.pulado("conexao", "não conferido: depende do token")
        check_cadastro(rel)
    except Exception as e:  # nunca imprimir str(e): pode carregar URL com token
        nome = type(e).__name__
        if como_json:
            print(json.dumps({"pronto": False, "erro_interno": nome, "pendencias": rel.pendencias, "itens": rel.itens}, ensure_ascii=False, indent=2))
        else:
            print(f"\nERRO INTERNO ({nome}). Rode de novo; se repetir, avise quem mantém a skill.")
        sys.exit(2)

    pronto = not rel.pendencias
    if como_json:
        print(json.dumps({
            "pronto": pronto,
            "pendencias": rel.pendencias,
            "avisos": len(rel.avisos),
            "itens": rel.itens,
            "token": {k: v for k, v in (token or {}).items() if k != "permissoes"},
            "conexao": conexao,
            "graph_version": lib.GRAPH_VERSION,
        }, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 56)
        if pronto:
            print("TUDO PRONTO. A skill pode ser usada.")
            if rel.avisos:
                print(f"Há {len(rel.avisos)} aviso(s) acima: não impedem de começar, mas resolva quando puder.")
        else:
            print(f"AINDA NÃO. O que falta ({len(rel.pendencias)}):")
            for i, p in enumerate(rel.pendencias, 1):
                print(f"  {i}. {p['o_que']}")
                if p["acao"]:
                    print(f"     -> {p['acao']}")
            print(f"Depois de corrigir, rode de novo: {PY} scripts/setup.py")
        print("=" * 56)
    sys.exit(0 if pronto else 1)


if __name__ == "__main__":
    main()
