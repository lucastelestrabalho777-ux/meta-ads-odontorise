---
name: atualizar-git-odontorise
description: Atualiza o pacote de skills da OdontoRise pelo GitHub sem sair do Claude: baixa a versão nova, liga as skills novas, ajusta o CLAUDE.md da pasta OdontoRise quando a regra mudou e mostra o que chegou. Use quando a pessoa disser "atualizar git odontorise", "atualiza o pacote", "atualiza as skills", "puxa a versão nova", "chegou atualização" ou "/atualizar-git-odontorise".
---

# /atualizar-git-odontorise

Faz o mesmo que o comando de instalação do guia, sem abrir o Terminal. Não mexe em credenciais, cadastro nem contas.
O Claude vai pedir permissão para rodar os comandos: a pessoa aprova.

## Passos
1. Guarde a versão atual:
   `git -C "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/meta-ads-odontorise" log -1 --format=%h`
2. Baixe a versão nova e rode o instalador já atualizado (nesta ordem: o instalador velho não conhece as mudanças novas).
   - Mac (e Windows quando o terminal do Claude for Git Bash):
     ```
     PKG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/meta-ads-odontorise"
     git -C "$PKG" pull --ff-only && bash "$PKG/instalar.sh"
     ```
     No Windows com Git Bash, a segunda parte é
     `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PKG/instalar.ps1")"`.
   - Windows com PowerShell:
     ```
     $Pkg = "$HOME\.claude\skills\meta-ads-odontorise"
     git -C $Pkg pull --ff-only; if ($LASTEXITCODE -eq 0) { powershell -NoProfile -ExecutionPolicy Bypass -File "$Pkg\instalar.ps1" }
     ```
3. Mostre o que chegou: `git -C "<pacote>" log --format="%h %s" <versão do passo 1>..HEAD`. Traduza cada título em uma
   linha simples para a pessoa. Se não vier nada, diga que já estava na versão mais nova.
4. Confira: as skills novas aparecem na lista (`ls` da pasta de skills). Elas já valem nesta conversa; se alguma não
   aparecer, digite `/reload-skills` ou abra uma conversa nova.

## Se der erro
- "not possible to fast-forward" ou arquivo alterado: alguém mexeu em arquivo dentro da pasta do pacote. Mostre
  `git -C "<pacote>" status --short` e peça para chamar o Lucas. Nunca apagar nem descartar alteração por conta própria.
- `git` não encontrado: peça para chamar o Lucas.
- Sem internet ou GitHub fora do ar: tentar de novo mais tarde.

## Regras
- Só atualiza o pacote. Credenciais, cadastro de clientes, aprendizados e auditoria ficam como estão.
- Sem travessão.
