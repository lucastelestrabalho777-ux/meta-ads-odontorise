# Workspace OdontoRise (CS)

Pasta de trabalho da CS da OdontoRise no Claude Code. Abra esta pasta no VS Code antes de pedir
qualquer coisa ao Claude: é daqui que ele lê as regras da casa e encontra a sua credencial do ClickUp.

## O que fica aqui

| Caminho | O que é |
|---|---|
| `credentials/` | só o seu token do ClickUp (`clickup-odontorise.env`). Nunca compartilhada, nunca enviada. |

As skills da CS vivem em `~/.claude/skills/` e chegam pelo repositório do GitHub da agência, instaladas com o
papel CS. Para atualizar, digite /atualizar-git-odontorise no Claude: o papel continua o mesmo.

## Skills da CS

| Skill | Para quê |
|---|---|
| /analise-onboarding | tempo médio do onboarding, clientes em andamento e há quantos dias, etapas que mais demoram |
| /clientes-criticos | clientes em alerta: o que já foi feito, com quem está a ação, há quantos dias está parado |
| /agendar-reuniao | horários livres na sua agenda, evento com o cliente convidado, textos para o grupo e para o ClickUp |
| /resumo-reuniao | ata da reunião a partir da gravação, sem enviar o arquivo a ninguém |

Os scripts de ClickUp do pacote ficam em `~/.claude/skills/meta-ads-odontorise/scripts/` e podem ser usados
(`tarefas.py`, `onboarding.py`, `alertas.py listar`). Para conferir a conexão com o ClickUp:
`python3 ~/.claude/skills/meta-ads-odontorise/scripts/tarefas.py minhas` (no Windows, `python`).

## Regras da casa

1. A CS não usa conta de anúncio. Não rodar a skill Meta Ads (meta-ads-odontorise) nem os scripts de Meta
   (`setup.py`, `saude.py`, `insights.py`, `read.py`, `create.py`, `posts.py`), mesmo que uma skill os cite.
   Resultado, saldo e criativo de conta são com o gestor do cliente.
2. ClickUp: só leitura. Comentar, mudar status e abrir alerta são ações da pessoa, feitas no ClickUp; o Claude
   entrega o texto pronto.
3. Nada é criado na agenda nem enviado ao cliente sem OK explícito, item por item.
4. Dado sensível do cliente (CPF, CNPJ, telefone, e-mail, valores de contrato, endereço) nunca vai para arquivo,
   nota ou memória: lê na hora e usa.
5. Nome de paciente citado em reunião não entra em ata: escrever "paciente".
6. Segredo (token, senha, chave) nunca entra em nota, memória, print ou chat.
7. Textos sem travessão.

## Como pedir

- "como está o onboarding" · "clientes em alerta" · "marca a reunião mensal com X" · "resumo da reunião"
- "minhas tarefas no ClickUp" · "reuniões dos próximos 7 dias"
