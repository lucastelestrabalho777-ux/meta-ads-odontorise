# Workspace OdontoRise

Pasta de trabalho do time da OdontoRise no Claude Code. Abra esta pasta no VS Code antes de pedir
qualquer coisa ao Claude: é daqui que ele lê as regras da casa e encontra as suas credenciais.

## O que fica aqui

| Caminho | O que é |
|---|---|
| `credentials/` | só os seus arquivos de credencial (Meta, ClickUp). Nunca compartilhada, nunca enviada. |
| `meta-ads/` | seu cadastro de clientes, seus aprendizados e o log de auditoria; a skill cria e mantém |

As skills (Meta Ads, cadastro, tarefas, legenda, reunião) vivem em `~/.claude/skills/` e chegam pelo
repositório do GitHub da agência. Para atualizar, digite /atualizar-git-odontorise no Claude.

## Regras da casa (resumo; a lista completa está na skill, em references/regras-da-casa.md)

1. Nada é executado em conta de anúncio, ClickUp ou grupo de cliente sem OK explícito, item por item.
2. Campanha, conjunto e anúncio nascem pausados. Ativar é decisão do gestor.
3. Antes de pausar um anúncio, cruzar 30, 14 e 7 dias.
4. Nunca ampliar raio. Posicionamento segue o que a conta já usa (Instagram, Facebook).
5. Post do cliente só vira anúncio depois de analisado: paciente final sobe; mentoria, conteúdo pessoal ou sem sentido não sobe.
6. Métricas: mensagens iniciadas, custo por mensagem iniciada, gasto, CTR, CPM, alcance, impressões, frequência.
7. Segredo (token, senha, chave) nunca entra em nota, memória, print ou chat.
8. Textos sem travessão.
9. Roteiro escrito para cliente: no fim, oferecer registrar no ClickUp (/registrar-otimizacao, tarefa "Roteiro").
10. Cada pessoa só lê e opera as contas dos clientes que cuida (o cadastro local, vindo do ClickUp). Conta de outro gestor: nem ler, nem cadastrar. O head cadastra a carteira inteira.

## Como pedir

- "rode o setup da skill Meta" · "cadastra o cliente X" · "resultado da conta X nos últimos 7 dias"
- "compara as janelas dos anúncios da X" · "saúde da conta X" · "contas críticas" · "meu dia" · "legenda para esse vídeo"
