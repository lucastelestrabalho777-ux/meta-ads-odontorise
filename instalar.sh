#!/usr/bin/env bash
# Instalador do pacote de skills da OdontoRise (Mac e Linux). Rode uma vez depois de clonar o repositório:
#   bash ~/.claude/skills/meta-ads-odontorise/instalar.sh
# O que faz: cria ~/OdontoRise (CLAUDE.md, credentials/, meta-ads/), liga cada skill do pacote em
# ~/.claude/skills/ e confere Python e a biblioteca da Meta. Não mexe em credenciais nem em contas.
set -e
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SKILLS="$CFG/skills"
WS="$HOME/OdontoRise"
echo "Pacote: $AQUI"
echo "Skills do Claude Code: $SKILLS"

mkdir -p "$WS/credentials" "$WS/meta-ads" "$SKILLS"
chmod 700 "$WS/credentials"
if [ ! -f "$WS/CLAUDE.md" ]; then cp "$AQUI/workspace/CLAUDE.md" "$WS/CLAUDE.md"; echo "criado: $WS/CLAUDE.md"; else echo "mantido: $WS/CLAUDE.md"; fi

if [ "$AQUI" != "$SKILLS/meta-ads-odontorise" ]; then
  ln -sfn "$AQUI" "$SKILLS/meta-ads-odontorise"; echo "ligada: $SKILLS/meta-ads-odontorise -> $AQUI"
fi
for d in "$AQUI"/skills/*/; do
  n="$(basename "$d")"; ln -sfn "${d%/}" "$SKILLS/$n"; echo "ligada: $SKILLS/$n"
done

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then echo "AVISO: python3 não encontrado. Passo 3 do guia."; else
  if ! "$PY" -c "import facebook_business" 2>/dev/null; then
    echo "instalando a biblioteca da Meta..."
    "$PY" -m pip install --user -q -r "$AQUI/requirements.txt" 2>/dev/null || "$PY" -m pip install --user -q --break-system-packages -r "$AQUI/requirements.txt"
  fi
  "$PY" -c "import facebook_business; print('biblioteca da Meta ok', facebook_business.__version__)"
fi
echo
echo "Pronto. Próximos passos: credenciais (passo 6 e 8 do guia) e depois, no Claude: 'rode o setup da skill Meta'."
