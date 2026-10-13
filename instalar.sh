#!/usr/bin/env bash
# Instalador do pacote de skills da OdontoRise (Mac e Linux). Um comando, sem conta no GitHub:
#   curl -fsSL https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.sh | bash
# CS (Customer Success), só as skills da CS e sem Meta:
#   curl -fsSL https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.sh | bash -s cs
# Rodar de novo atualiza o pacote. O que faz: baixa (ou atualiza) o pacote em ~/.claude/skills/meta-ads-odontorise,
# cria ~/OdontoRise (CLAUDE.md, credentials/, meta-ads/), liga cada skill em ~/.claude/skills/ e confere
# Python, a biblioteca da Meta e o navegador do raio-x (Playwright + Chromium). Não mexe em credenciais nem em contas.
# Papel: sem argumento, o pacote completo (gestor e head). "cs" liga só as skills de papeis/cs.txt, usa o CLAUDE.md
# da CS e não instala a biblioteca da Meta nem o navegador. O papel fica em ~/OdontoRise/.papel e vale nas
# atualizações (/atualizar-git-odontorise roda este instalador sem argumento); "completo" volta ao pacote inteiro.
set -e
REPO_URL="https://github.com/lucastelestrabalho777-ux/meta-ads-odontorise.git"
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SKILLS="$CFG/skills"
WS="$HOME/OdontoRise"
DESTINO="$SKILLS/meta-ads-odontorise"
PAPEL="${1:-${ODR_PAPEL:-}}"
if [ -z "$PAPEL" ] && [ -f "$WS/.papel" ]; then PAPEL="$(tr -d '[:space:]' < "$WS/.papel")"; fi
case "$PAPEL" in
  ""|completo|gestor|head) PAPEL="completo" ;;
  cs) ;;
  *) echo "papel desconhecido: $PAPEL (use cs, ou nada para o pacote completo)"; exit 1 ;;
esac
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "$(dirname "${BASH_SOURCE[0]}")/SKILL.md" ]; then
  AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  AQUI="$DESTINO"
fi
mkdir -p "$SKILLS"
if [ ! -f "$AQUI/SKILL.md" ]; then
  echo "baixando o pacote em $DESTINO ..."; git clone -q "$REPO_URL" "$DESTINO"; AQUI="$DESTINO"
elif [ -d "$AQUI/.git" ]; then
  echo "atualizando o pacote ..."; git -C "$AQUI" pull -q --ff-only || echo "AVISO: não consegui atualizar (git pull); seguindo com a versão local"
fi
echo "Pacote: $AQUI"
echo "Skills do Claude Code: $SKILLS"

if [ "$PAPEL" = cs ]; then
  mkdir -p "$WS/credentials" "$SKILLS"
  echo cs > "$WS/.papel"; echo "Papel: CS (só as skills da CS, sem Meta)"
  MODELO="$AQUI/workspace/CLAUDE-cs.md"; OUTRO="$AQUI/workspace/CLAUDE.md"
else
  mkdir -p "$WS/credentials" "$WS/meta-ads" "$SKILLS"
  if [ -f "$WS/.papel" ]; then rm -f "$WS/.papel"; echo "Papel: pacote completo"; fi
  MODELO="$AQUI/workspace/CLAUDE.md"; OUTRO="$AQUI/workspace/CLAUDE-cs.md"
fi
chmod 700 "$WS/credentials"
if [ ! -f "$WS/CLAUDE.md" ]; then cp "$MODELO" "$WS/CLAUDE.md"; echo "criado: $WS/CLAUDE.md"
elif [ -f "$OUTRO" ] && cmp -s "$WS/CLAUDE.md" "$OUTRO"; then
  cp "$MODELO" "$WS/CLAUDE.md"; echo "trocado: $WS/CLAUDE.md pelo do papel atual (era o do outro papel, sem alteração)"
else
  echo "mantido: $WS/CLAUDE.md"
  if [ "$PAPEL" = cs ] && [ "$(head -n 1 "$WS/CLAUDE.md")" != "# Workspace OdontoRise (CS)" ]; then
    echo "AVISO: $WS/CLAUDE.md não é o da CS (veio de uma instalação anterior e foi editado). Para trocar: apague o arquivo e rode o instalador de novo."
  fi
fi
# Regra 4 mudou em 01/10/2026: troca só a linha antiga exata; o resto do CLAUDE.md da pessoa fica como está.
REGRA4_ANTIGA="4. Nunca sugerir Facebook como posicionamento nem ampliar raio."
REGRA4_NOVA="4. Nunca ampliar raio. Posicionamento segue o que a conta já usa (Instagram, Facebook)."
if grep -qxF "$REGRA4_ANTIGA" "$WS/CLAUDE.md"; then
  awk -v a="$REGRA4_ANTIGA" -v n="$REGRA4_NOVA" '$0 == a { print n; next } { print }' "$WS/CLAUDE.md" > "$WS/CLAUDE.md.tmp" && mv "$WS/CLAUDE.md.tmp" "$WS/CLAUDE.md"
  echo "atualizado: regra 4 do $WS/CLAUDE.md (posicionamento segue o que a conta já usa)"
fi

if [ "$AQUI" != "$SKILLS/meta-ads-odontorise" ]; then
  ln -sfn "$AQUI" "$SKILLS/meta-ads-odontorise"; echo "ligada: $SKILLS/meta-ads-odontorise -> $AQUI"
fi
if [ "$PAPEL" = cs ]; then
  LISTA="$(grep -v '^#' "$AQUI/papeis/cs.txt" | tr -d '\r' | sed '/^[[:space:]]*$/d')"
  # Instalação completa anterior: desliga as skills do pacote que não são da CS (só atalhos para dentro do pacote).
  for l in "$SKILLS"/*; do
    [ -L "$l" ] || continue
    case "$(readlink "$l")" in
      "$AQUI"/skills/*|"$AQUI"/papeis/cs/*)
        n="$(basename "$l")"
        if ! printf '%s\n' "$LISTA" | grep -qxF "$n"; then rm -f "$l"; echo "desligada: $SKILLS/$n (não é da CS)"; fi ;;
    esac
  done
  for n in $LISTA; do
    # versão da CS (papeis/cs/<nome>, sem Meta) quando existe; senão a skill do pacote
    if [ -d "$AQUI/papeis/cs/$n" ]; then ORIGEM="$AQUI/papeis/cs/$n"; else ORIGEM="$AQUI/skills/$n"; fi
    if [ -d "$ORIGEM" ]; then ln -sfn "$ORIGEM" "$SKILLS/$n"; echo "ligada: $SKILLS/$n"
    else echo "AVISO: a skill $n da lista da CS não existe no pacote"; fi
  done
else
  for d in "$AQUI"/skills/*/; do
    n="$(basename "$d")"; ln -sfn "${d%/}" "$SKILLS/$n"; echo "ligada: $SKILLS/$n"
  done
fi

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then echo "AVISO: python3 não encontrado. Passo 3 do guia."
elif [ "$PAPEL" = cs ]; then
  # A CS só precisa do requests (conexão com o ClickUp); sem biblioteca da Meta e sem navegador.
  if ! "$PY" -c "import requests" 2>/dev/null; then
    echo "instalando o requests (conexão com o ClickUp)..."
    "$PY" -m pip install --user -q requests 2>/dev/null || "$PY" -m pip install --user -q --break-system-packages requests
  fi
  "$PY" -c "import requests; print('conexão com o ClickUp ok (requests ' + requests.__version__ + ')')"
  echo "A CS não usa a biblioteca da Meta nem o navegador."
else
  if ! "$PY" -c "import facebook_business, playwright" 2>/dev/null; then
    echo "instalando a biblioteca da Meta e o Playwright (navegador do raio-x de concorrentes)..."
    "$PY" -m pip install --user -q -r "$AQUI/requirements.txt" 2>/dev/null || "$PY" -m pip install --user -q --break-system-packages -r "$AQUI/requirements.txt"
  fi
  "$PY" -c "import facebook_business; print('biblioteca da Meta ok', facebook_business.__version__)"
  if "$PY" -c "import playwright" 2>/dev/null; then
    echo "conferindo o Chromium do Playwright (na primeira vez baixa uns 150 MB)..."
    "$PY" -m playwright install chromium && "$PY" -c "from importlib.metadata import version; print('navegador do raio-x ok (playwright ' + version('playwright') + ')')"
  else
    echo "AVISO: o Playwright não instalou; só o raio-x de concorrentes sem Apify precisa dele. No Claude, 'rode o setup da skill Meta' mostra o comando."
  fi
fi
echo
if [ "$PAPEL" = cs ]; then
  echo "Pronto. Próximos passos: o token do ClickUp (passo 8 do guia) e depois, no Claude: 'minhas tarefas no ClickUp'."
else
  echo "Pronto. Próximos passos: credenciais (passo 6 e 8 do guia) e depois, no Claude: 'rode o setup da skill Meta'."
fi
