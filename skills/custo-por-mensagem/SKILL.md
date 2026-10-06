---
name: custo-por-mensagem
description: Custo por mensagem iniciada dos clientes do gestor nos últimos 7 dias, comparado com os 7 dias anteriores, pronto para colar na planilha de acompanhamento. Use quando o gestor disser "custo por mensagem da semana", "quanto está custando a mensagem", "números para a planilha", "custo por conversa dos meus clientes" ou "/custo-por-mensagem".
---

# /custo-por-mensagem

Base: `scripts/saude.py todas` da skill meta-ads-odontorise (usa o cadastro local; só clientes com conta Meta).
Para um cliente só: `scripts/insights.py resultado --cliente X` (padrão últimos 7 dias).

## Como responder
1. Rode `saude.py todas` e leia, por conta, `gasto_sem_resultado.conta_7d` (gasto, mensagens, custo_por_mensagem)
   e `conta_7d_anteriores`, mais `variacao_custo_mensagem_pct`.
2. Entregue uma tabela por cliente, ordenada do pior custo por mensagem para o melhor:
   cliente · gasto 7d · mensagens iniciadas · custo por mensagem · variação contra os 7 dias anteriores.
   Cliente sem gasto: mostrar "sem gasto" e perguntar se é intencional. Cliente com gasto e zero mensagem: 🔴 no topo.
3. Abaixo da tabela, um bloco "para colar na planilha": só os valores de custo por mensagem, um por linha,
   vírgula decimal, sem "R$", na mesma ordem em que o gestor pediu (se ele mandar a ordem, seguir a dele).
4. Feche com 3 apontamentos no máximo: onde o custo está em R$35 ou mais (`custo_acima_do_teto`), onde subiu mais de 30%, onde caiu, onde não há mensagem.
   Cada apontamento sugere uma ação concreta (criativo, público, verba, pausa), nunca "observar".

## Regras
- Métrica é mensagem iniciada, nunca lead de formulário. Período sempre explícito.
- Nada é executado: a skill só lê e sugere. Sem travessão.
