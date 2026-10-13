# Workspace OdontoRise (CS)

Pasta de trabalho da CS da OdontoRise no Claude Code (`~/OdontoRise`). Abra esta pasta no VS Code antes de pedir
qualquer coisa ao Claude: é daqui que ele lê as regras da casa.

## O que fica aqui

| Caminho | O que é |
|---|---|
| `~/OdontoRise/credentials/clickup-odontorise.env` | só o seu token do ClickUp. Nunca compartilhado, nunca enviado. |

As skills da CS vivem em `~/.claude/skills/` e chegam pelo repositório do GitHub da agência, instaladas com o
papel CS. Para atualizar, digite /atualizar-git-odontorise no Claude: o papel continua o mesmo.

## Skills da CS

| Skill | Para quê |
|---|---|
| /analise-onboarding | tempo médio do onboarding, clientes em andamento e há quantos dias, etapas que mais demoram |
| /clientes-criticos | clientes em alerta: o que já foi feito, com quem está a ação, há quantos dias está parado |
| /agendar-reuniao | horários livres na sua agenda, evento com o cliente convidado, textos para o grupo e para o ClickUp |
| /resumo-reuniao | ata da reunião a partir da gravação, sem enviar o arquivo a ninguém |
| /clientes-saudaveis | quem está bem no relacionamento (candidatos a depoimento ou indicação) e quem precisa de cuidado |
| /suporte-grupo | resposta para dúvida ou reclamação no grupo, com o que o ClickUp mostra do cliente |

Os scripts de ClickUp ficam em `~/.claude/skills/meta-ads-odontorise/scripts/` e são permitidos: `cs.py`, `tarefas.py`,
`onboarding.py` e `alertas.py listar`. Para conferir a conexão com o ClickUp:
`python3 ~/.claude/skills/meta-ads-odontorise/scripts/tarefas.py minhas` (no Windows, `python`).

## Quem é quem no cliente

O perfil do cliente no ClickUp traz o gestor, a CS e a liderança (campos Gestor, CS e Liderança). Conteúdo (vídeo, arte,
LP, roteiro) é demanda na lista Conteúdos dos Clientes, aberta pelo gestor. Resultado, saldo e anúncio são com o gestor.

## Regras da casa

1. A CS não usa conta de anúncio. A skill Meta Ads (meta-ads-odontorise) aparece instalada porque os scripts de ClickUp
   moram na pasta dela, mas ela não é da CS: não seguir as instruções dela nem rodar os scripts de Meta (`setup.py`,
   `saude.py`, `insights.py`, `read.py`, `create.py`, `posts.py`), mesmo que alguma skill os cite.
2. ClickUp: só leitura. Comentar, mudar status, preencher campo e abrir alerta são ações da pessoa, feitas no ClickUp;
   o Claude entrega o texto pronto.
3. Nada é criado na agenda nem enviado ao cliente sem OK explícito, item por item.
4. Dado sensível do cliente (CPF, CNPJ, telefone, e-mail, valores de contrato, endereço) nunca vai para arquivo,
   nota ou memória: lê na hora e usa.
5. Nome de paciente citado em reunião não entra em ata: escrever "paciente".
6. Segredo (token, senha, chave) nunca entra em nota, memória, print ou chat.
7. Textos sem travessão.
8. Descrição e comentário de tarefa, alerta, satisfação e opinião interna sobre o cliente são internos: nunca vão para
   texto de cliente ou de grupo.

## Como pedir

- "como está o onboarding" · "clientes em alerta" · "marca a reunião mensal com X" · "resumo da reunião"
- "quem está bem para depoimento" · "o cliente X perguntou isso no grupo, como respondo?"
- "minhas tarefas no ClickUp" · "reuniões dos próximos 7 dias"
