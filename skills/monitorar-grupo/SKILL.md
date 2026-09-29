---
name: monitorar-grupo
description: Registra o que o CS viu de fora do padrão no grupo de um cliente: classifica a situação, muda o Status do Projeto no perfil do cliente, grava a observação no ClickUp e, se for grave, abre o alerta na lista Clientes em Alerta para o gestor e a liderança. Use quando o CS disser "vi algo estranho no grupo do X", "cliente reclamou no grupo", "cliente sumiu", "registra o que vi no grupo", "muda o status do cliente" ou "/monitorar-grupo".
---

# /monitorar-grupo

O CS cola o que viu (mensagens ou resumo). A skill classifica e propõe o registro. Nada é escrito sem OK.

## Passos
1. Classifique: reclamação de resultado, reclamação de atendimento, cliente ausente ou silêncio, dúvida sem resposta,
   pedido de pausa ou saída, elogio. Estime a gravidade: leve (só registrar), média (registrar e avisar o gestor),
   grave (registrar e abrir alerta).
2. Proponha o Status do Projeto do cliente: Muito Insatisfeito (Crítico), Insatisfeito (Alerta), Neutro, Satisfeito,
   Muito Satisfeito (Promotor) ou Embaixador da Odontorise. Mostre o status atual (cadastro local, campo satisfacao)
   e o proposto, com o motivo em uma linha.
3. Com OK, rode `scripts/alertas.py status-cliente --cliente X --status "<status>" --texto "<o que foi visto>" --confirmo`
   (skill meta-ads-odontorise): muda o campo no perfil e grava o comentário com o que saiu do padrão.
4. Se for grave, com OK, rode `alertas.py abrir --cliente X --motivo "<motivo>" --nivel <1 a 5> --texto "<resumo>" --responsavel "<gestor>" --confirmo`.
   Motivos possíveis: Relacionamento, Resultado de Campanha, Comercial Fraco, Cliente Ausente, Desalinhamento de
   Expectativas, Falta de Feedback de agendamentos, Falta de percepção de valor, Outros.
5. Entregue ao CS a resposta sugerida para o grupo, se couber, e avise quem precisa saber (gestor, liderança).

## Regras
- Sem OK não escreve. Nome de paciente não entra no registro. Sem travessão.
- Reclamação de resultado: também oferecer a skill /resolver-conflito para o gestor.
