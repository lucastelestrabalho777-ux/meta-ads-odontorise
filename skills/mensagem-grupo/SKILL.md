---
name: mensagem-grupo
description: Escreve mensagens curtas para o gestor colar no grupo do cliente: resultado do dia ou da semana, pedido de recarga de saldo, aviso de criativo novo no ar, pedido de material, resposta a dúvida sobre resultado. Use quando o gestor disser "mensagem para o grupo", "avisa o cliente que", "texto para pedir saldo", "responde o cliente sobre o resultado" ou "/mensagem-grupo".
---

# /mensagem-grupo

Quem envia é o gestor. A skill entrega o texto pronto, no tom da casa: direto, cordial, sem jargão de tráfego,
com número real quando o assunto for resultado.

## Passos
1. Entenda o tipo de mensagem: resultado, saldo, criativo no ar, pedido de material, resposta a reclamação ou dúvida.
2. Busque o dado necessário nos scripts da skill meta-ads-odontorise:
   resultado → `insights.py resultado --cliente X` · saldo → `saude.py conta --cliente X` (sinal saldo_pagamento) ·
   criativo no ar → `read.py ads-by-campaign` e `read.py creative` · reclamação sobre resultado → `insights.py comparar-janelas`.
3. Escreva 2 versões: uma curta (3 a 4 linhas) e uma um pouco mais completa (até 8 linhas). Pergunte qual usar.

## Regras
- Métrica é mensagem iniciada e custo por mensagem. Sem promessa de resultado, sem prazo que não foi combinado.
- Pedido de saldo: valor sugerido e como recarregar (PIX no Gerenciador), sem tom de cobrança.
- Reclamação: reconhecer, mostrar o número, dizer a ação já tomada e a próxima. Nunca culpar o cliente.
- Sem travessão. Não enviar nada.
