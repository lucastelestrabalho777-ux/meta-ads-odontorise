# meta-ads-odontorise

Skill de Claude Code para os gestores de tráfego da OdontoRise operarem as contas Meta Ads
dos clientes (clínicas odontológicas) com campanhas de conversão ao WhatsApp.

Molde de estrutura: skill meta-ads-ratos (Ratos de IA). Conteúdo, regras e métricas próprios.

## Estado

Em construção, uma parte por vez. Prontas e testadas com dado real em 28/09/2026: biblioteca de conexão (`scripts/lib/`), conferência do ambiente (`scripts/setup.py`) e cadastro de clientes a partir do ClickUp (`scripts/clientes.py`). O que cada skill faz e como pedir está em `SKILL.md`.

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
liga as skills e instala a biblioteca da Meta. Para atualizar, rode o mesmo comando de novo.
Passo a passo com telas: Guia de IA OdontoRise, página Onboarding, passos 4 e 5.

## Regras de segredo

Token, chave secreta e senha ficam só no arquivo de credencial, com permissão 600.
Nunca em nota, memória, print, chat, WhatsApp, Drive ou neste repositório.
Os scripts mostram o token sempre mascarado.
