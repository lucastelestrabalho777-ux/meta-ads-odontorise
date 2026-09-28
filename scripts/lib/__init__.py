#!/usr/bin/env python3
"""
meta-ads-odontorise: biblioteca compartilhada.

O que esta biblioteca faz:
  1. Lê a credencial da pessoa em ~/OdontoRise/credentials/meta-odontorise.env
     (só desse arquivo; variável de shell não é aceita, para nunca usar o token
     de outra conta por engano nem deixar token no histórico do terminal).
  2. Inicializa o SDK oficial da Meta com a versão da Graph API fixada.
  3. Padroniza a saída: dado em JSON no stdout, mensagens humanas no stderr,
     erro também em JSON, com dica do que fazer. Nenhuma mensagem de erro
     carrega token ou chave secreta (ver redigir()).
  4. Trata limite de chamadas (retry com espera) e delay entre escritas.
  5. Oferece os argumentos comuns de linha de comando.

Molde: skill meta-ads-ratos (Ratos de IA, abril de 2026). Adaptações: caminho
da credencial, nomes das variáveis, versão da API fixa, timeout, retry,
validação de placeholder, dicas de erro em português, fbtrace_id corrigido e
redação de segredos em toda mensagem de erro.
"""

import hashlib
import hmac
import json
import os
import re
import stat
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Versão da Graph API usada em todas as chamadas. Revisar antes de 21/01/2027,
# quando a v21.0 deixa de ser servida. Pode ser sobrescrita por ODR_GRAPH_VERSION.
GRAPH_VERSION = os.environ.get("ODR_GRAPH_VERSION", "v21.0")
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Tempo máximo de cada chamada, em segundos.
API_TIMEOUT = 30

# Onde vive a credencial de cada pessoa. Nunca dentro da skill.
# ODR_META_ENV aponta para OUTRO ARQUIVO (é o único override aceito).
CRED_PATH = os.path.expanduser(
    os.environ.get("ODR_META_ENV", "~/OdontoRise/credentials/meta-odontorise.env")
)

# Variáveis que o arquivo de credencial pode ter.
CRED_VARS = ("META_ACCESS_TOKEN", "META_APP_ID", "META_APP_SECRET", "META_BM_ID")

# Valores que indicam que a pessoa ainda não preencheu o arquivo.
_PLACEHOLDER_PREFIXES = ("COLE_", "SEU_", "SUA_", "seu-", "sua-", "XXX", "xxx", "<", "{")

# Códigos de erro da Meta que significam limite de chamadas atingido.
RATE_LIMIT_CODES = (4, 17, 32, 613, 80004)

ONDE_GUIA = "Guia de IA OdontoRise, página Onboarding, passo 6"
ONDE_GERAR_TOKEN = ONDE_GUIA + ", parte 3"

_api_initialized = False
_credentials = {}
_perm_avisada = False


# ---------------------------------------------------------------------------
# Redação de segredos
# ---------------------------------------------------------------------------

_RE_SEGREDO_URL = re.compile(r"(access_token|input_token|appsecret_proof|client_secret)=[^&\s'\"]+", re.I)
_RE_TOKEN_META = re.compile(r"\bEAA[A-Za-z0-9]{20,}")


def redigir(texto):
    """Remove token, chave secreta e afins de qualquer texto antes de imprimir."""
    if texto is None:
        return ""
    t = str(texto)
    t = _RE_SEGREDO_URL.sub(r"\1=***", t)
    t = _RE_TOKEN_META.sub("EAA***", t)
    for k in ("META_APP_SECRET", "META_ACCESS_TOKEN"):
        v = _credentials.get(k)
        if v and len(v) >= 8:
            t = t.replace(v, "***")
    return t


# ---------------------------------------------------------------------------
# Dependência
# ---------------------------------------------------------------------------

def _python_cmd():
    return os.path.basename(sys.executable) or "python3"


def ensure_sdk():
    """Confere se a biblioteca da Meta (facebook-business) está instalada."""
    try:
        import facebook_business  # noqa: F401
        return True
    except ImportError:
        print("ERRO: a biblioteca da Meta (facebook-business) não está instalada.", file=sys.stderr)
        print(f"  No terminal, rode: {_python_cmd()} -m pip install --user facebook-business==26.0.2", file=sys.stderr)
        print("  (se aparecer externally-managed-environment, repita acrescentando --break-system-packages no final)", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Credencial
# ---------------------------------------------------------------------------

def _parse_env_file(path):
    """Lê um arquivo .env simples (CHAVE=valor). Aceita BOM e não quebra com acento."""
    values = {}
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
    return values


def _is_placeholder(value):
    if not value:
        return True
    return any(value.startswith(p) for p in _PLACEHOLDER_PREFIXES)


def checar_permissao(path):
    """
    Devolve (status, texto): 'ok', 'aberto' (outros usuários leem), 'dono' (outro dono)
    ou 'nao_verificado' (Windows, permissão é por ACL e não é conferida aqui).
    """
    if os.name == "nt":
        return "nao_verificado", "permissão não conferida no Windows"
    st = os.stat(path)
    modo = stat.S_IMODE(st.st_mode)
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        return "dono", "o arquivo pertence a outro usuário"
    if modo & 0o077:
        return "aberto", f"permissão do arquivo é {oct(modo)[2:]}; deveria ser 600"
    return "ok", "só o seu usuário lê o arquivo"


def load_credentials():
    """
    Carrega a credencial do arquivo em CRED_PATH. Não existe fallback para o shell.
    Retorna dict com as variáveis conhecidas mais '_source' (caminho ou None).
    Avisa uma vez no stderr se o arquivo estiver legível por outros usuários.
    """
    global _credentials, _perm_avisada
    if _credentials:
        return _credentials

    creds = {k: "" for k in CRED_VARS}
    creds["_source"] = None
    if os.path.isfile(CRED_PATH):
        file_values = _parse_env_file(CRED_PATH)
        for k in CRED_VARS:
            creds[k] = file_values.get(k, "")
        creds["_source"] = CRED_PATH
        status, texto = checar_permissao(CRED_PATH)
        if status in ("aberto", "dono") and not _perm_avisada:
            print(f"AVISO: {texto}. No terminal, rode: chmod 600 {CRED_PATH}", file=sys.stderr)
            _perm_avisada = True
    _credentials = creds
    return creds


def mask_token(token):
    """Mascara o token para nunca aparecer inteiro em tela."""
    if not token or len(token) < 12:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def _exit_missing_token(creds):
    if not creds.get("_source"):
        print("ERRO: arquivo de credencial não encontrado.", file=sys.stderr)
        print(f"  Esperado em: {CRED_PATH}", file=sys.stderr)
        print(f"  Crie o arquivo seguindo o {ONDE_GUIA}, parte 4.", file=sys.stderr)
    else:
        print("ERRO: o arquivo de credencial ainda tem linha vazia ou com valor de exemplo.", file=sys.stderr)
        print(f"  Arquivo: {CRED_PATH}", file=sys.stderr)
        print("  O arquivo precisa destas linhas, com os seus valores:", file=sys.stderr)
        print("    META_ACCESS_TOKEN=COLE_AQUI_O_SEU_TOKEN_DE_60_DIAS      (parte 3)", file=sys.stderr)
        print("    META_APP_ID=COLE_AQUI_O_ID_DO_SEU_APP                  (parte 2)", file=sys.stderr)
        print("    META_APP_SECRET=COLE_AQUI_A_CHAVE_SECRETA_DO_SEU_APP   (parte 2)", file=sys.stderr)
        print("    META_BM_ID=666777657534959", file=sys.stderr)
        print(f"  Onde pegar cada valor: {ONDE_GUIA}.", file=sys.stderr)
    sys.exit(1)


def init_api(quiet=False):
    """Inicializa o SDK uma vez por processo, com a credencial da pessoa e a versão fixa da API."""
    global _api_initialized
    if _api_initialized:
        return

    ensure_sdk()
    from facebook_business.api import FacebookAdsApi

    creds = load_credentials()
    token = creds.get("META_ACCESS_TOKEN", "")
    if _is_placeholder(token):
        _exit_missing_token(creds)

    app_id = creds.get("META_APP_ID") or None
    app_secret = creds.get("META_APP_SECRET") or None
    if _is_placeholder(app_id):
        app_id = None
    if _is_placeholder(app_secret):
        app_secret = None

    FacebookAdsApi.init(
        app_id=app_id,
        app_secret=app_secret,
        access_token=token,
        api_version=GRAPH_VERSION,
        timeout=API_TIMEOUT,
    )
    _api_initialized = True

    if not quiet:
        print(f"Credencial: {creds['_source']} (token {mask_token(token)}) · Graph API {GRAPH_VERSION}", file=sys.stderr)


def resolve_account(args_account=None):
    """
    Resolve a conta de anúncio a partir do argumento --account.
    Não existe conta padrão: com dezenas de contas de clientes, toda operação
    precisa dizer em qual conta roda. O cadastro de clientes (nome para act_)
    entra em uma parte seguinte e usará esta mesma função.
    """
    if not args_account:
        print("ERRO: nenhuma conta informada.", file=sys.stderr)
        print("  Use --account act_XXXXXXXXX (o id da conta do cliente).", file=sys.stderr)
        sys.exit(1)
    acct = str(args_account).strip()
    if not acct.startswith("act_"):
        acct = f"act_{acct}"
    return acct


def add_target_args(parser):
    """--account act_X ou --cliente <nome, código ou slug do cadastro>."""
    parser.add_argument("--account", help="Conta de anúncio (act_123)")
    parser.add_argument("--cliente", help="Cliente do cadastro local (nome, #código ou slug); resolve a conta Meta dele")


def resolve_target(args):
    """
    Conta de anúncio a partir de --account ou --cliente. Com --cliente, procura no
    cadastro local; se o cliente não tiver conta Meta definida, orienta a definir.
    """
    acct = getattr(args, "account", None)
    cli = getattr(args, "cliente", None)
    if acct:
        return resolve_account(acct)
    if cli:
        from . import watchlist
        dados = watchlist.carregar()
        c = watchlist.resolver(dados, cli)
        if not c:
            print(f"ERRO: cliente '{cli}' não está no cadastro local.", file=sys.stderr)
            print("  Cadastre com: clientes.py cadastrar --nome <nome>", file=sys.stderr)
            sys.exit(1)
        if not c.get("act_id"):
            print(f"ERRO: o cliente '{c.get('nome')}' está cadastrado sem conta Meta.", file=sys.stderr)
            print(f"  Defina com: clientes.py definir-conta --cliente {c.get('slug')} --account act_XXX", file=sys.stderr)
            sys.exit(1)
        return c["act_id"]
    return resolve_account(None)


# ---------------------------------------------------------------------------
# Chamadas diretas (sem SDK), com o token no cabeçalho, nunca na URL
# ---------------------------------------------------------------------------

def appsecret_proof(token, app_secret):
    """Prova do app secret exigida quando o app tem 'Exigir chave secreta' ligado."""
    if not app_secret or _is_placeholder(app_secret):
        return None
    return hmac.new(app_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def graph_get(path, params=None, token=None):
    """
    GET na Graph API com o token no cabeçalho Authorization.
    Devolve (ok, dado): ok=False traz {'erro': texto sem segredo, 'code': ...}.
    Nunca levanta exceção de rede para quem chama.
    """
    import requests
    creds = load_credentials()
    token = token or creds.get("META_ACCESS_TOKEN", "")
    params = dict(params or {})
    proof = appsecret_proof(token, creds.get("META_APP_SECRET", ""))
    if proof:
        params["appsecret_proof"] = proof
    url = path if path.startswith("http") else f"{GRAPH_URL}/{path.lstrip('/')}"
    try:
        r = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=API_TIMEOUT)
        body = r.json()
    except requests.RequestException as e:
        return False, {"erro": f"sem resposta da Meta ({type(e).__name__})", "code": None, "rede": True}
    except ValueError:
        return False, {"erro": "a Meta respondeu algo que não é JSON", "code": None, "rede": True}
    if isinstance(body, dict) and "error" in body:
        err = body["error"]
        return False, {"erro": redigir(err.get("message")), "code": err.get("code"),
                       "subcode": err.get("error_subcode"), "fbtrace_id": err.get("fbtrace_id")}
    return True, body


def graph_post(path, data=None, token=None):
    """
    POST na Graph API (escrita). Token no cabeçalho, appsecret_proof quando houver chave.
    Devolve (ok, dado) sem levantar exceção de rede e sem segredo na mensagem.
    Quem chama é responsável por ter o OK do gestor e por registrar auditoria.
    """
    import requests
    creds = load_credentials()
    token = token or creds.get("META_ACCESS_TOKEN", "")
    data = dict(data or {})
    proof = appsecret_proof(token, creds.get("META_APP_SECRET", ""))
    if proof:
        data["appsecret_proof"] = proof
    for k, v in list(data.items()):
        if isinstance(v, (dict, list)):
            data[k] = json.dumps(v, ensure_ascii=False)
    url = path if path.startswith("http") else f"{GRAPH_URL}/{path.lstrip('/')}"
    try:
        r = requests.post(url, data=data, headers={"Authorization": f"Bearer {token}"}, timeout=API_TIMEOUT)
        body = r.json()
    except requests.RequestException as e:
        return False, {"erro": f"sem resposta da Meta ({type(e).__name__})", "code": None, "rede": True}
    except ValueError:
        return False, {"erro": "a Meta respondeu algo que não é JSON", "code": None, "rede": True}
    if isinstance(body, dict) and "error" in body:
        err = body["error"]
        out = {"erro": redigir(err.get("message")), "code": err.get("code"), "subcode": err.get("error_subcode"),
               "fbtrace_id": err.get("fbtrace_id"), "titulo": err.get("error_user_title"), "detalhe": redigir(err.get("error_user_msg"))}
        if out["subcode"] in _SUBCODE_HINTS:
            out["hint"] = _SUBCODE_HINTS[out["subcode"]]
        elif out["code"] in _HINTS:
            out["hint"] = _HINTS[out["code"]]
        return False, out
    return True, body


AUDITORIA_PATH = os.path.expanduser(os.environ.get("ODR_AUDITORIA", "~/OdontoRise/meta-ads/auditoria.jsonl"))


def auditar(acao, conta, resumo, ids=None, quem=None):
    """Registra uma escrita no log local da pessoa (uma linha JSON por ação). Nunca inclui token."""
    os.makedirs(os.path.dirname(AUDITORIA_PATH), exist_ok=True)
    linha = {"quando": datetime.now().isoformat(timespec="seconds"), "quem": quem, "acao": acao,
             "conta": conta, "resumo": redigir(resumo), "ids": ids or {}}
    with open(AUDITORIA_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    try:
        os.chmod(AUDITORIA_PATH, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Validade do token
# ---------------------------------------------------------------------------

_TIPOS_TOKEN = {"USER": "token de usuário", "SYSTEM_USER": "token de usuário do sistema", "PAGE": "token de página"}


def _fmt_ts(ts):
    if not ts:
        return "nunca"
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone().strftime("%d/%m/%Y")


def _days_left(ts):
    """Dias até o instante ts (negativo se já passou); None se ts vazio (não expira)."""
    if not ts:
        return None
    delta = datetime.fromtimestamp(int(ts), tz=timezone.utc) - datetime.now(timezone.utc)
    return int(delta.total_seconds() // 86400)


def token_info():
    """
    Consulta /debug_token e devolve validade e permissões do token da pessoa.
    Precisa de META_APP_ID e META_APP_SECRET do aplicativo que gerou o token.
    Nunca imprime nem devolve o token; nunca levanta exceção de rede.
    """
    creds = load_credentials()
    token = creds.get("META_ACCESS_TOKEN", "")
    app_id = creds.get("META_APP_ID", "")
    app_secret = creds.get("META_APP_SECRET", "")
    if _is_placeholder(token):
        return {"ok": False, "erro": "token ausente ou com valor de exemplo", "code": None}
    if _is_placeholder(app_id) or _is_placeholder(app_secret):
        return {"ok": False, "erro": "META_APP_ID ou META_APP_SECRET ausentes: validade não conferida", "code": None}

    ok, body = graph_get("debug_token", params={"input_token": token}, token=f"{app_id}|{app_secret}")
    if not ok:
        return {"ok": False, "erro": body.get("erro"), "code": body.get("code"), "rede": body.get("rede", False)}

    d = body.get("data", {})
    if not d.get("is_valid"):
        err = d.get("error") or {}
        return {"ok": False, "erro": redigir(err.get("message")) or "a Meta marcou o token como inválido",
                "code": err.get("code"), "tipo": d.get("type")}

    expires = d.get("expires_at", 0)
    data_access = d.get("data_access_expires_at", 0)
    info = {
        "ok": True,
        "tipo": d.get("type"),
        "tipo_texto": _TIPOS_TOKEN.get(d.get("type"), str(d.get("type"))),
        "app_id": str(d.get("app_id", "")),
        "app_confere": str(d.get("app_id", "")) == str(app_id),
        "expira_em": _fmt_ts(expires),
        "dias_restantes": _days_left(expires),
        "acesso_a_dados_ate": _fmt_ts(data_access),
        "dias_acesso_a_dados": _days_left(data_access),
        "permissoes": sorted(d.get("scopes", [])),
    }
    dias = info["dias_restantes"]
    if dias is not None and dias <= 10:
        info["alerta"] = f"Token vence em {dias} dia(s). Gerar um novo: {ONDE_GERAR_TOKEN}."
    return info


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------

def print_json(obj):
    """Imprime qualquer objeto do SDK ou dict como JSON no stdout."""
    print(json.dumps(_serialize(obj), indent=2, ensure_ascii=False, default=str))


def _serialize(obj):
    """Converte objetos do SDK em estruturas serializáveis."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if hasattr(obj, "export_all_data"):
        return _serialize(obj.export_all_data())
    if hasattr(obj, "__iter__") and hasattr(obj, "params"):
        return [_serialize(item) for item in obj]
    try:
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError):
        return str(obj)


def print_error(msg):
    """Mensagem de erro no stderr, sempre sem segredo."""
    print(f"ERRO: {redigir(msg)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Erros da Meta
# ---------------------------------------------------------------------------

_HINTS = {
    190: f"Token inválido ou vencido (ou a senha do Facebook foi trocada). Gerar um novo: {ONDE_GERAR_TOKEN}.",
    200: "Sem permissão nesta conta. Conferir se a conta foi atribuída a você na BM e se as nove permissões estão no token.",
    10: "Permissão negada pelo aplicativo. Conferir as permissões marcadas ao gerar o token.",
    100: "Parâmetro inválido. Conferir id, campos e formato do JSON enviado.",
}
_SUBCODE_HINTS = {
    1885183: "O aplicativo está em modo Desenvolvimento. Para subir criativos ele precisa estar publicado (modo Ativo).",
    463: f"Token expirado. Gerar um novo: {ONDE_GERAR_TOKEN}.",
    460: f"A senha do Facebook foi trocada e o token caiu. Gerar um novo: {ONDE_GERAR_TOKEN}.",
}


def _fbtrace(e):
    """Extrai o fbtrace_id do corpo do erro, se existir."""
    try:
        body = e.body()
        if isinstance(body, dict):
            return body.get("error", {}).get("fbtrace_id")
    except Exception:
        pass
    return None


def is_rate_limit(e):
    try:
        return e.api_error_code() in RATE_LIMIT_CODES
    except Exception:
        return False


def handle_fb_error(func):
    """Decorator: transforma erro da Meta em JSON com dica, sem segredo, e sai com código 1."""
    def wrapper(*args, **kwargs):
        ensure_sdk()
        import requests
        from facebook_business.exceptions import FacebookRequestError
        try:
            return func(*args, **kwargs)
        except FacebookRequestError as e:
            code = e.api_error_code()
            subcode = e.api_error_subcode()
            error_data = {
                "error": True,
                "message": redigir(e.api_error_message()),
                "code": code,
                "subcode": subcode,
                "type": e.api_error_type(),
                "fbtrace_id": _fbtrace(e),
            }
            if code in RATE_LIMIT_CODES:
                error_data["hint"] = "Limite de chamadas atingido nesta conta. Aguardar 60 segundos e tentar de novo."
            elif subcode in _SUBCODE_HINTS:
                error_data["hint"] = _SUBCODE_HINTS[subcode]
            elif code in _HINTS:
                error_data["hint"] = _HINTS[code]
            print(json.dumps(error_data, indent=2, ensure_ascii=False, default=str))
            sys.exit(1)
        except requests.RequestException as e:
            print_error(f"sem resposta da Meta ({type(e).__name__}). Conferir a internet e tentar de novo.")
            sys.exit(1)
        except SystemExit:
            raise
        except Exception as e:
            print_error(f"{type(e).__name__}: {redigir(e)}")
            sys.exit(1)
    return wrapper


def retry_call(fn, tries=3, wait=60):
    """
    Executa fn(); se a Meta responder limite de chamadas, espera e tenta de novo.
    Outros erros sobem na hora. Uso: retry_call(lambda: conta.get_campaigns(...)).
    """
    ensure_sdk()
    from facebook_business.exceptions import FacebookRequestError
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except FacebookRequestError as e:
            if is_rate_limit(e) and attempt < tries:
                print(f"Limite de chamadas: aguardando {wait}s (tentativa {attempt} de {tries})", file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def safe_delay(seconds=1):
    """Pausa entre operações de escrita."""
    time.sleep(seconds)


# ---------------------------------------------------------------------------
# Argumentos comuns
# ---------------------------------------------------------------------------

def add_account_arg(parser):
    parser.add_argument("--account", required=False, help="Conta de anúncio do cliente (ex: act_123). Obrigatória.")


def add_fields_arg(parser):
    parser.add_argument("--fields", help="Campos separados por vírgula (ex: name,status,id)")


def add_pagination_args(parser):
    parser.add_argument("--limit", type=int, default=None, help="Máximo de resultados (padrão: todos)")
    parser.add_argument("--after", help="Cursor de paginação (próxima página)")
    parser.add_argument("--before", help="Cursor de paginação (página anterior)")


def add_status_filter_arg(parser, default=None):
    parser.add_argument("--status", default=default, help="Filtrar por status: ACTIVE,PAUSED,ARCHIVED (separados por vírgula)")


def parse_fields(fields_str):
    if not fields_str:
        return None
    return [f.strip() for f in fields_str.split(",") if f.strip()]


def parse_json_arg(json_str, arg_name="argumento"):
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print_error(f"JSON inválido no argumento {arg_name}: {e}")
        sys.exit(1)


def parse_status_filter(status_str):
    if not status_str:
        return None
    return [s.strip().upper() for s in status_str.split(",") if s.strip()]
