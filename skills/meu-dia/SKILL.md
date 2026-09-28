---
name: meu-dia
description: Mostra as tarefas do ClickUp da pessoa (atrasadas, de hoje e dos próximos dias) com o que fazer em cada uma, e detalha uma tarefa quando pedido. Use quando o gestor, o head ou o CS disser "meu dia", "minhas tarefas", "o que tenho para hoje", "o que está atrasado", "detalha a tarefa X", "como faço a tarefa X" ou "/meu-dia".
---

# /meu-dia

Lê as tarefas abertas da pessoa no ClickUp da OdontoRise com o token pessoal dela. Só leitura: nada é
fechado, comentado ou movido por esta skill.

## Onde está o script
Na skill meta-ads-odontorise, pasta `scripts/`: `tarefas.py`. Localize com
`ls ~/.claude/skills/*/meta-ads-odontorise/scripts/tarefas.py ~/.claude/skills/synced/*/meta-ads-odontorise/scripts/tarefas.py 2>/dev/null | head -1`
e chame com `python3` (Windows: `python`). Credencial: `~/OdontoRise/credentials/clickup-odontorise.env`
(passo 8 do guia). Se faltar, o script explica como criar.

## Como responder

1. Rode `tarefas.py minhas --dias 7` e leia o JSON.
2. Entregue nesta ordem, curto, com números reais:
   - 🔴 **Atrasadas**: as mais atrasadas primeiro, com nome, lista e dias de atraso. Agrupe por rotina
     quando o nome repetir (ex.: "Dashboard Mensal: 5 clientes").
   - 🟡 **Hoje**: o que vence hoje.
   - 🟢 **Próximos dias**: o que vence até 7 dias.
   - Sem data: só a contagem, a menos que a pessoa peça.
3. Feche com uma sugestão de ordem para o dia (3 itens no máximo) e pergunte por qual começar.
4. Se a pessoa pedir detalhe ("como faço a X"), rode `tarefas.py tarefa --id <id>` e resuma descrição,
   subtarefas e comentários. Se a tarefa for rotina de conta (dashboard, monitoramento, acompanhamento),
   ofereça a skill Meta correspondente: resultado da conta, saúde da conta, comparar janelas.

## Regras
- Não marcar nada como concluído nem comentar no ClickUp por esta skill.
- Tarefa de cliente que não está no cadastro local: sugerir "cadastra o cliente X" antes de operar a conta.
- Sem travessão nos textos.
