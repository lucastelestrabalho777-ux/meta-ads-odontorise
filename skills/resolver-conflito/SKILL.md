---
name: resolver-conflito
description: Prepara a resposta a um cliente insatisfeito com números na mão: o que aconteceu na conta, o resultado nas três janelas, o que já foi feito, o que será feito e o texto para a conversa. Use quando o head ou o gestor disser "cliente reclamando", "cliente quer sair", "cliente diz que não tem resultado", "como responder o cliente X" ou "/resolver-conflito".
---

# /resolver-conflito

## Dados
1. `insights.py comparar-janelas --cliente X --level campaign` e `--level ad --limit 15`: o resultado em 30, 14 e 7 dias.
2. `insights.py resultado --cliente X --date-preset last_30d`: mensagens, custo por mensagem, gasto do mês.
3. `read.py activities --cliente X --dias 30 --so-humanas --limit 50`: o que foi feito e quando, por quem.
4. `saude.py conta --cliente X`: saldo, reprovados, conta parada.
5. Cadastro: satisfação registrada no ClickUp, procedimento, produto contratado.

## Entrega
- Leitura honesta em 5 linhas: o resultado caiu, subiu ou está estável, desde quando, e a causa mais provável
  (criativo cansado, saldo, verba cortada, conta parada, sazonalidade). Se a causa é nossa, dizer.
- O que já foi feito (com datas) e o que será feito nos próximos 7 dias, com o critério de sucesso.
- Texto para a conversa com o cliente: reconhece a insatisfação, mostra 2 ou 3 números, apresenta o plano e pede um prazo
  combinado para reavaliar. Tom calmo, sem defensiva, sem promessa de resultado.
- Se o problema estiver fora do tráfego (atendimento no WhatsApp, agenda, preço), dizer com o dado que mostra isso
  (mensagens iniciadas altas e reclamação de "não vende" apontam para a conversão na clínica).

## Regras
- Número real sempre; nunca esconder queda. Sem travessão. A skill não envia nada nem mexe na conta.
