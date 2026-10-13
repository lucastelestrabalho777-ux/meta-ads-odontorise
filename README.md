# meta-ads-odontorise

Skill de Claude Code para os gestores de tráfego da OdontoRise operarem as contas Meta Ads
dos clientes (clínicas odontológicas) com campanhas de conversão ao WhatsApp.

Molde de estrutura: skill meta-ads-ratos (Ratos de IA). Conteúdo, regras e métricas próprios.

## Estado

Em construção, uma parte por vez. Prontas e testadas com dado real em 28/09/2026: biblioteca de conexão (`scripts/lib/`), conferência do ambiente (`scripts/setup.py`) e cadastro de clientes a partir do ClickUp (`scripts/clientes.py`). O que cada skill faz e como pedir está em `SKILL.md`.

07/10/2026: `/raio-x-concorrentes` aberto aos gestores (só nos próprios clientes), com rota sem Apify pelo navegador (`scripts/concorrentes/navegador.py`, Playwright + Chromium instalados pelo instalador), trava de token pessoal do Apify, regra de 5 km e seção "Concorrente de outros serviços" no documento.

## Onde ficam as coisas

| O quê | Onde | Entra no repositório? |
|---|---|---|
| Skill (regras, scripts, referências) | esta pasta | sim |
| Credencial do Meta de cada pessoa | `~/OdontoRise/credentials/meta-odontorise.env` | nunca |
| Token pessoal do ClickUp | `~/OdontoRise/credentials/clickup-odontorise.env` | nunca |
| Cadastro de clientes, aprendizados locais, auditoria | `~/OdontoRise/meta-ads/` | nunca |

## Instalar (gestor): um comando, sem conta no GitHub

Mac (Terminal):
```bash
curl -fsSL https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.sh | bash
```
Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.ps1 | iex
```
O instalador baixa o pacote em `~/.claude/skills/meta-ads-odontorise`, cria `~/OdontoRise` (CLAUDE.md, credentials, meta-ads),
liga as skills e instala a biblioteca da Meta. Para atualizar, digite `/atualizar-git-odontorise` no Claude
(ou rode o mesmo comando de novo).
Passo a passo com telas: Guia de IA OdontoRise, página Onboarding, passos 4 e 5.

O head usa esta mesma instalação: as skills de carteira leem as contas de anúncio.

## Instalar (CS): só as skills da CS, sem Meta

Mac (Terminal):
```bash
curl -fsSL https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.sh | bash -s cs
```
Windows (PowerShell):
```powershell
$env:ODR_PAPEL="cs"; irm https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.ps1 | iex
```
Liga só as skills de `papeis/cs.txt`, cria `~/OdontoRise` com o CLAUDE.md da CS (`workspace/CLAUDE-cs.md`) e não instala
a biblioteca da Meta nem o navegador. A CS precisa só do token do ClickUp (e do Google Calendar no claude.ai).
O papel fica gravado em `~/OdontoRise/.papel`, então `/atualizar-git-odontorise` mantém a CS. Quem já tinha o pacote
completo e roda com `cs` tem as outras skills desligadas (o pacote não é apagado). Para voltar: `bash -s completo`
(Windows: `$env:ODR_PAPEL="completo"`).

## Regras de segredo

Token, chave secreta e senha ficam só no arquivo de credencial, com permissão 600.
Nunca em nota, memória, print, chat, WhatsApp, Drive ou neste repositório.
Os scripts mostram o token sempre mascarado.
