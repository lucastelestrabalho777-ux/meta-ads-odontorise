---
name: suporte-grupo
description: Escreve a resposta para uma dúvida ou reclamação de cliente no grupo, no tom da casa, com o dado certo quando o assunto for resultado, saldo ou criativo. Use quando o CS disser "responde o cliente", "o cliente perguntou X no grupo", "como respondo essa reclamação", "suporte no grupo" ou "/suporte-grupo".
---

# /suporte-grupo

Quem envia é o CS (ou o gestor). A skill entrega o texto.

## Passos
1. Leia a mensagem do cliente que o CS colar e classifique: dúvida de resultado, saldo ou pagamento, criativo ou aprovação,
   agenda e reunião, reclamação, elogio, pedido fora do escopo.
2. Busque o dado se precisar (scripts da skill meta-ads-odontorise): resultado → `insights.py resultado --cliente X`;
   saldo → `saude.py conta --cliente X`; criativo → `read.py ads-by-campaign` e `read.py creative`; reunião → `tarefas.py reunioes`.
3. Escreva a resposta em até 6 linhas: acolhe, responde com o fato, diz o próximo passo e quem cuida (gestor ou CS).
   Se a resposta depende do gestor, dizer que ele responde até tal hora e avisar o gestor.
4. Reclamação de resultado: não responder só com texto; oferecer a skill /resolver-conflito para preparar a conversa.

## Regras
- Métrica é mensagem iniciada. Sem promessa. Sem travessão. Nada é enviado pela skill.
- Nunca discutir preço ou contrato no grupo: encaminhar para a liderança.
