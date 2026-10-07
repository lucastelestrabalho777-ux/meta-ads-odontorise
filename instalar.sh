#!/usr/bin/env bash
# Instalador do pacote de skills da OdontoRise (Mac e Linux). Um comando, sem conta no GitHub:
#   curl -fsSL https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.sh | bash
# Rodar de novo atualiza o pacote. O que faz: baixa (ou atualiza) o pacote em ~/.claude/skills/meta-ads-odontorise,
# cria ~/OdontoRise (CLAUDE.md, credentials/, meta-ads/), liga cada skill em ~/.claude/skills/ e confere
# Python, a biblioteca da Meta e o navegador do raio-x (Playwright + Chromium). Não mexe em credenciais nem em contas.
set -e
REPO_URL="https://github.com/lucastelestrabalho777-ux/meta-ads-odontorise.git"
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SKILLS="$CFG/skills"
WS="$HOME/OdontoRise"
DESTINO="$SKILLS/meta-ads-odontorise"
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

mkdir -p "$WS/credentials" "$WS/meta-ads" "$SKILLS"
chmod 700 "$WS/credentials"
if [ ! -f "$WS/CLAUDE.md" ]; then cp "$AQUI/workspace/CLAUDE.md" "$WS/CLAUDE.md"; echo "criado: $WS/CLAUDE.md"; else echo "mantido: $WS/CLAUDE.md"; fi
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
for d in "$AQUI"/skills/*/; do
  n="$(basename "$d")"; ln -sfn "${d%/}" "$SKILLS/$n"; echo "ligada: $SKILLS/$n"
done

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then echo "AVISO: python3 não encontrado. Passo 3 do guia."; else
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
echo "Pronto. Próximos passos: credenciais (passo 6 e 8 do guia) e depois, no Claude: 'rode o setup da skill Meta'."
