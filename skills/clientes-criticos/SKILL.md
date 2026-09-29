---
name: clientes-criticos
description: Analisa os clientes em alerta no ClickUp para o head: o que já foi feito em cada alerta, quem está com a ação pendente, há quantos dias está parado e o texto para cobrar a pessoa certa. Use quando o head disser "clientes críticos", "clientes em alerta", "o que está parado nos alertas", "quem está devendo ação", "status dos alertas" ou "/clientes-criticos".
---

# /clientes-criticos

Fonte: lista Clientes em Alerta do ClickUp (`scripts/alertas.py listar`, skill meta-ads-odontorise, só leitura).
Cada alerta traz cliente, motivo, nível de criticidade, status (em cadastro, alerta, delegado, em execução,
definir novo plano, acompanhamento, churn), quem está com a ação, dias aberto, dias parado e o último comentário.

## Como responder
1. Rode `alertas.py listar`. Ordene pelo tempo parado.
2. Entregue em três blocos, com números reais:
   - 🔴 Parados há 5 dias ou mais, ou sem responsável: cliente · motivo · status · com quem está · dias parado · o que
     foi a última movimentação. Para cada um, o texto de cobrança para a pessoa (curto, direto, com o pedido e o prazo).
   - 🟡 Em andamento: o que já foi feito (último comentário) e o próximo passo esperado.
   - ✅ Em acompanhamento ou resolvidos na semana: só a contagem.
3. Aponte alertas sem cliente ligado ou sem motivo preenchido: são cadastros incompletos.
4. Feche com a lista de pessoas a consultar hoje, uma linha por pessoa, com os alertas dela.

## Regras
- Só leitura: cobrar, mover status e comentar são ações do head. Sem travessão.
- Quando o head pedir o contexto de tráfego de um cliente em alerta, use `saude.py conta --cliente X` e `insights.py comparar-janelas`.
