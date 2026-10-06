---
name: oportunidades-carteira
description: Varre todas as contas do cadastro e aponta onde o head deve agir: custo por mensagem fora da curva, gasto sem mensagem, saldo acabando, anúncios reprovados, conta parada sem otimização. Use quando o head disser "oportunidades na carteira", "onde estamos perdendo", "raio-x da carteira", "quais contas precisam de atenção" ou "/oportunidades-carteira".
---

# /oportunidades-carteira

Base: `scripts/saude.py todas` da skill meta-ads-odontorise (5 sinais por conta) e, para aprofundar uma conta,
`insights.py comparar-janelas --cliente X --level campaign`.
O cadastro local do head precisa ter as contas da carteira (`clientes.py cadastrar` para cada cliente, com a conta Meta).

## Como responder
1. Rode `saude.py todas` e monte um ranking da pior conta para a melhor, usando o pior sinal de cada uma.
2. Entregue em quatro blocos, com números reais e no máximo 5 contas por bloco:
   - 🔴 Crítico: gasto sem mensagem (campanha ou criativo), custo por mensagem de R$35 ou mais, saldo para menos de 2 dias, anúncio reprovado, conta desativada, conta parada há mais de 10 dias.
   - 🟡 Esta semana: custo por mensagem subiu mais de 30%, conta parada há 7 dias ou mais, criativo com R$50 sem mensagem, saldo para menos de 5 dias.
   - 🟢 Oportunidades: custo por mensagem caindo com verba baixa (candidata a escalar), conta com criativo campeão antigo.
   - ✅ Funcionando: contas estáveis, só para registro.
3. Para cada conta 🔴 ou 🟡: gestor responsável (do cadastro), o dado que justifica e uma ação concreta a pedir ao gestor.
4. Fechar com 💰 estimativa: quanto está sendo gasto por semana nas contas sem mensagem e quanto a carteira gasta no total.

## Regras
- O head não opera a conta: a saída é a lista de pedidos para cada gestor. Nada é executado.
- Sem travessão. Métrica é mensagem iniciada.
