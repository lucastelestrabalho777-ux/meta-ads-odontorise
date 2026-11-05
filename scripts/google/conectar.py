#!/usr/bin/env python3
"""
meta-ads-odontorise: conectar o Google Ads (passo 7 do guia).

Autoriza a SUA conta Google no aplicativo da OdontoRise e guarda a credencial em
~/OdontoRise/credentials/google-ads-odontorise.yaml (só o seu usuário lê).
Depois testa: mostra o MCC Odontorise e as contas de cliente que você enxerga.

Uso:
  python3 scripts/google/conectar.py            autoriza (abre o navegador) e testa
  python3 scripts/google/conectar.py --testar   só testa a credencial que já existe
  python3 scripts/google/conectar.py --testar --json   saída para o Claude e para o setup

Não altera nada em conta de anúncio. Nunca mostra token, chave ou segredo.
Códigos de saída: 0 ok · 1 pendência · 2 erro interno
"""

import json
import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = Path(os.environ.get("ODONTORISE_HOME") or (Path.home() / "OdontoRise"))
CRED = HOME / "credentials"
CLIENT_JSON = CRED / "client_secret_odontorise.json"
YAML = CRED / "google-ads-odontorise.yaml"
MCC = "4820610378"                      # conta gerenciadora (MCC) Odontorise
SCOPES = ["https://www.googleapis.com/auth/adwords"]
GUIA = "Guia de IA OdontoRise, página Onboarding, passo 7"
PY = os.path.basename(sys.executable) or "python3"
# Desde 09/09/2026 o Google ignora o developer token: o nível de acesso é do projeto Cloud
# do aplicativo. A biblioteca ainda exige a chave no arquivo, por isso o valor fixo abaixo.
DEV_TOKEN = "ignorado-pelo-google-desde-2026-09-09"


def ler_yaml(path):
    cfg = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, _, v = line.partition(":")
            cfg[k.strip()] = v.split("#")[0].strip().strip('"')
    return cfg


def escrever_yaml(cfg):
    CRED.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CRED, 0o700)
    except OSError:
        pass
    linhas = [
        "# Google Ads API - credencial da OdontoRise (gerada por scripts/google/conectar.py)",
        "# NUNCA compartilhe este arquivo. Para refazer: rode o conectar.py de novo.",
        "",
        f'developer_token: "{cfg["developer_token"]}"',
        f'client_id: "{cfg["client_id"]}"',
        f'client_secret: "{cfg["client_secret"]}"',
        f'refresh_token: "{cfg["refresh_token"]}"',
        f'login_customer_id: "{MCC}"',
        "use_proto_plus: True",
        "",
    ]
    YAML.write_text("\n".join(linhas), encoding="utf-8")
    try:
        os.chmod(YAML, 0o600)
    except OSError:
        pass


def falha(erro, acao):
    return {"ok": False, "erro": erro, "acao": acao}


def _codigo(err):
    # "authorization_error: USER_PERMISSION_DENIED" -> texto seguro, sem token
    try:
        return str(err.error_code).strip().replace("\n", " ")
    except Exception:
        return "erro desconhecido"


def testar():
    """Lê a credencial, confere o acesso ao MCC e lista as contas. Só leitura."""
    try:
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.errors import GoogleAdsException
    except ImportError:
        return falha("biblioteca do Google Ads não instalada",
                     f"no Claude, /atualizar-git-odontorise; ou no terminal: {PY} -m pip install --user google-ads")
    if not YAML.is_file():
        return falha(f"credencial não encontrada: {YAML}",
                     f"rodar este comando sem --testar para autorizar ({GUIA}, parte B)")
    cfg = ler_yaml(YAML)
    faltando = [k for k in ("client_id", "client_secret", "refresh_token") if not cfg.get(k)]
    if faltando:
        return falha(f"credencial incompleta (falta {', '.join(faltando)})",
                     "rodar este comando sem --testar para gerar o arquivo de novo")
    cfg["developer_token"] = cfg.get("developer_token") or DEV_TOKEN
    cfg["login_customer_id"] = MCC
    cfg["use_proto_plus"] = True
    try:
        client = GoogleAdsClient.load_from_dict(cfg)
        acessiveis = [r.split("/")[-1] for r in client.get_service("CustomerService").list_accessible_customers().resource_names]
    except GoogleAdsException as e:
        return _mapear(_codigo(e.failure.errors[0]) if e.failure.errors else "erro desconhecido")
    except Exception as e:  # RefreshError e afins: nunca imprimir a mensagem inteira
        nome = type(e).__name__
        texto = str(e)[:200]
        if "invalid_grant" in texto or "Refresh" in nome:
            return falha("a autorização do Google foi revogada ou expirou (invalid_grant)",
                         "rodar este comando sem --testar para autorizar de novo")
        return falha(f"não consegui falar com o Google ({nome})",
                     "conferir a internet e rodar de novo; se repetir, avisar quem mantém a skill")
    if MCC not in acessiveis:
        return falha(f"sua conta Google enxerga {len(acessiveis)} conta(s), mas não o MCC Odontorise {MCC}",
                     f"pedir ao administrador para colocar o seu e-mail no MCC e aceitar o convite ({GUIA}, parte A e parte B.1)")
    try:
        ga = client.get_service("GoogleAdsService")
        nome_mcc = ""
        for r in ga.search(customer_id=MCC, query="SELECT customer.descriptive_name FROM customer LIMIT 1"):
            nome_mcc = r.customer.descriptive_name
        contas = []
        q = ("SELECT customer_client.id, customer_client.descriptive_name FROM customer_client "
             "WHERE customer_client.level = 1 AND customer_client.status = 'ENABLED' "
             "ORDER BY customer_client.descriptive_name")
        for r in ga.search(customer_id=MCC, query=q):
            contas.append({"id": str(r.customer_client.id), "nome": r.customer_client.descriptive_name})
    except GoogleAdsException as e:
        return _mapear(_codigo(e.failure.errors[0]) if e.failure.errors else "erro desconhecido")
    return {"ok": True, "mcc": MCC, "mcc_nome": nome_mcc, "contas": contas, "credencial": str(YAML)}


def _mapear(codigo):
    if any(k in codigo for k in ("USER_PERMISSION_DENIED", "CUSTOMER_NOT_FOUND", "NOT_ADS_USER")):
        return falha(f"o Google negou o acesso ao MCC ({codigo})",
                     f"seu e-mail ainda não é usuário do MCC Odontorise, ou o convite não foi aceito ({GUIA}, parte A e parte B.1)")
    if "RESOURCE_EXHAUSTED" in codigo:
        return falha("a cota do dia acabou (2.880 operações, somadas entre todas as pessoas)",
                     "esperar; a janela é de 24 horas")
    if "OAUTH_TOKEN" in codigo:
        return falha(f"a autorização não vale mais ({codigo})",
                     "rodar este comando sem --testar para autorizar de novo")
    if "CLOUD_PROJECT_NOT_APPROVED" in codigo or "DEVELOPER_TOKEN" in codigo:
        return falha(f"o aplicativo da OdontoRise perdeu o nível de acesso no Google ({codigo})",
                     "avisar o administrador: o nível do projeto no Google Cloud precisa ser Explorer ou acima")
    return falha(f"o Google respondeu com erro ({codigo})",
                 "rodar de novo; se repetir, avisar quem mantém a skill")


def autorizar():
    """Abre o navegador para a pessoa autorizar com a conta dela e grava o yaml."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return falha("biblioteca do Google Ads não instalada",
                     f"no Claude, /atualizar-git-odontorise; ou no terminal: {PY} -m pip install --user google-ads")
    if not CLIENT_JSON.is_file():
        return falha(f"arquivo do aplicativo não encontrado: {CLIENT_JSON}",
                     f"salvar o client_secret_odontorise.json que o administrador enviou nessa pasta ({GUIA}, parte B.2)")
    try:
        dados = json.loads(CLIENT_JSON.read_text(encoding="utf-8"))
        app = dados.get("installed") or dados.get("web") or {}
        client_id, client_secret = app["client_id"], app["client_secret"]
    except (ValueError, KeyError, OSError):
        return falha("o client_secret_odontorise.json não abre ou está incompleto",
                     "pedir o arquivo de novo ao administrador e salvar sem editar")

    print()
    print("  Google Ads OdontoRise: conectar (passo 7 do guia)")
    print("  " + "=" * 56)
    print("  Vai abrir uma aba do navegador. Nela:")
    print("   1. escolha a conta Google que o administrador colocou no MCC (normalmente a @odontorise.com);")
    print("   2. em 'O Google não verificou este app', clique em Avançado e em Acessar Gads - Odontorise;")
    print("   3. clique em Permitir.")
    print()
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_JSON), SCOPES)
    kwargs = dict(
        prompt="consent", open_browser=True,
        authorization_prompt_message="  Se a aba não abrir sozinha, cole este link no navegador:\n\n  {url}\n",
        success_message="Autorização concluída. Pode fechar esta aba e voltar ao terminal.",
    )
    try:
        try:
            creds = flow.run_local_server(port=8080, **kwargs)
        except OSError:
            creds = flow.run_local_server(port=0, **kwargs)
    except Exception as e:
        return falha(f"a autorização não terminou ({type(e).__name__})",
                     "rodar de novo e concluir a tela do Google até 'Permitir'")
    if not creds.refresh_token:
        return falha("o Google não devolveu a autorização", "rodar de novo (a tela de consentimento precisa aparecer e ser aceita)")
    escrever_yaml({"developer_token": DEV_TOKEN, "client_id": client_id,
                   "client_secret": client_secret, "refresh_token": creds.refresh_token})
    print(f"  [OK] credencial gravada em {YAML} (só o seu usuário lê)")
    print("  Testando o acesso...")
    return {"ok": True}


def main():
    como_json = "--json" in sys.argv
    so_testar = "--testar" in sys.argv
    if not so_testar:
        r = autorizar()
        if not r["ok"]:
            _sair(r, como_json)
    r = testar()
    _sair(r, como_json)


def _sair(r, como_json):
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif r["ok"]:
        print()
        print("  Google Ads conectado.")
        print(f"  MCC    : {r['mcc_nome']} ({r['mcc']})")
        print(f"  Contas : {len(r['contas'])} de cliente ativas")
        for c in r["contas"]:
            print(f"    - {c['id']}  {c['nome']}")
        print(f"  Arquivo: {r['credencial']}")
        print("  Pronto. No chat do Claude, peça: 'rode o setup da skill Meta' para a conferência completa.")
        print()
    else:
        print()
        print(f"  [FALHOU] {r['erro']}")
        print(f"           -> {r['acao']}")
        print()
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # nunca imprimir str(e): pode carregar URL com token
        print(f"\nERRO INTERNO ({type(e).__name__}). Rode de novo; se repetir, avise quem mantém a skill.")
        sys.exit(2)
