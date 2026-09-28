---
name: feedback-sexta
description: Escreve o feedback semanal de cada cliente do gestor (resultado da semana em mensagens iniciadas e custo por mensagem, o que foi feito e o que vem na próxima semana), pronto para colar no grupo do cliente na sexta. Use quando o gestor disser "feedback de sexta", "feedback semanal do cliente X", "mensagem da semana para o grupo", "resumo da semana para o cliente" ou "/feedback-sexta".
---

# /feedback-sexta

Quem envia é o gestor, no grupo do cliente. A skill entrega o texto; o envio é manual.

## Dados (scripts da skill meta-ads-odontorise)
1. `insights.py resultado --cliente X --date-preset last_7d` (gasto, mensagens iniciadas, custo por mensagem, CTR, CPM, alcance).
2. `insights.py comparar-janelas --cliente X --level campaign --limit 10` para ver a tendência (7 contra 14 e 30 dias).
3. `read.py activities --cliente X --dias 7 --so-humanas --limit 20` para listar o que foi feito na conta na semana.
4. Cadastro local (`clientes.py listar`) para o nome do cliente, o procedimento e o tom.
Para "todos os meus clientes": `clientes.py meus` e repetir por cliente ativo.

## Formato do texto (por cliente, 6 a 10 linhas, sem jargão)
- Saudação pelo primeiro nome do responsável.
- Resultado da semana: mensagens iniciadas e investimento, e o custo por mensagem, comparado com a semana anterior
  (subiu, caiu, estável). Números reais, arredondados.
- O que fizemos: 2 ou 3 itens do histórico (criativo novo, ajuste de público, verba).
- Próxima semana: 1 ou 2 ações combinadas, com o motivo.
- Pedido, se houver: saldo, material, aprovação de criativo.
- Fechamento cordial e convite a responder dúvidas.

## Regras
- Sempre custo por mensagem, nunca custo por lead. Sem prometer resultado.
- Se a semana foi ruim, dizer o que mudou e o que será feito; nunca esconder número.
- Sem travessão. Não enviar nada: entregar o texto e parar.
