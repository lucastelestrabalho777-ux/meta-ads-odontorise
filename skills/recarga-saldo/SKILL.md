---
name: recarga-saldo
description: Quais contas pré-pagas dos clientes do gestor estão com saldo acabando, quantos dias restam e quanto pedir de recarga ao cliente, com a mensagem pronta para o grupo. Use quando o gestor disser "quem está sem saldo", "saldo acabando", "quanto pedir de recarga", "conta vai parar por saldo" ou "/recarga-saldo".
---

# /recarga-saldo

Base: `scripts/saude.py todas` da skill meta-ads-odontorise, sinal `saldo_pagamento`: tipo da conta (pré-paga ou
pós-paga), saldo restante, gasto médio diário e dias de saldo. Para uma conta: `saude.py conta --cliente X`.

## Como responder
1. Rode `saude.py todas` e separe as contas pré-pagas.
2. Tabela ordenada por dias de saldo: cliente · saldo restante · gasto médio por dia · dias de saldo · status.
   🔴 menos de 2 dias ou conta desativada por pagamento · 🟠 menos de 5 dias · ✅ acima disso.
   Conta pós-paga: listar à parte só se houver problema de pagamento (cobrança pendente, cartão recusado).
3. Para cada 🔴 e 🟠, sugerir o valor da recarga: gasto médio diário multiplicado por 15 dias, arredondado para cima
   em múltiplos de R$ 50, e dizer quantos dias esse valor cobre.
4. Entregar a mensagem para o grupo do cliente, curta e no tom da casa: saldo atual, quando acaba, valor sugerido,
   como recarregar (PIX no Gerenciador de Anúncios). O envio é do gestor.

## Regras
- Recarga é feita pelo cliente; a skill nunca mexe em pagamento.
- Conta que não é pré-paga não recebe pedido de recarga. Sem travessão.
