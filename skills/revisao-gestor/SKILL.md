---
name: revisao-gestor
description: Prepara a revisão semanal de um gestor para o head: o que ele mexeu em cada conta na semana, cruzado com o resultado (mensagens e custo por mensagem) e com as contas que ficaram sem otimização. Use quando o head disser "revisão do gestor X", "o que o X fez essa semana", "revisar as contas do X", "1:1 com o gestor" ou "/revisao-gestor".
---

# /revisao-gestor

## Dados (scripts da skill meta-ads-odontorise)
1. Contas do gestor: no cadastro local, clientes cujo campo `gestor` é a pessoa (`clientes.py listar`), ou `clientes.py meus` se o próprio gestor estiver rodando.
2. Por conta: `read.py activities --cliente X --dias 7 --so-humanas --limit 50` (o que foi feito e quando) e
   `insights.py resultado --cliente X` (últimos 7 dias) mais `saude.py conta --cliente X` (sinais).
3. Se o histórico mostrar autor diferente do gestor, registrar quem mexeu.

## Entrega
- Tabela por conta: mexidas na semana (quantas e quais tipos: criativo, público, verba, pausa) · mensagens iniciadas ·
  custo por mensagem e variação · sinal de saúde.
- Três pontos fortes da semana (com número) e três pontos de atenção (conta parada, custo subindo sem ação, gasto sem mensagem).
- Perguntas para o 1:1 (no máximo 5), cada uma ligada a um dado da tabela.
- Combinados sugeridos para a próxima semana, por conta.

## Regras
- Tom de revisão, não de auditoria: fato e número, sem julgamento de pessoa. Sem travessão.
- Nada é executado; a skill só lê.
