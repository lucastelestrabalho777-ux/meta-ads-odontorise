---
name: suporte-grupo
description: Escreve para a CS a resposta a uma dúvida ou reclamação de cliente no grupo, no tom da casa, com o que o ClickUp mostra do cliente (conteúdos em produção, tarefas, reuniões, alertas); assunto de resultado, saldo ou anúncio vai para o gestor. Só lê o ClickUp, sem conta de anúncio. Use quando a CS disser "responde o cliente", "o cliente perguntou X no grupo", "como respondo essa reclamação", "suporte no grupo" ou "/suporte-grupo".
---

# /suporte-grupo (CS)

Quem envia é a CS. A skill entrega o texto. Fonte: só o ClickUp, só leitura; não usa conta de anúncio.

## Passos
1. Leia a mensagem que a CS colar e classifique: conteúdo (vídeo, arte, roteiro), agenda e reunião, resultado ou
   anúncio, saldo ou pagamento, reclamação, elogio, fora do escopo.
2. Rode `python3 ~/.claude/skills/meta-ads-odontorise/scripts/cs.py cliente --cliente "<nome ou #código>"`
   (no Windows, `python`). Ele traz o perfil (gestor, produto, fase, satisfação), alertas abertos, tarefas abertas e as
   últimas concluídas, conteúdos em produção com status e prazo, conteúdos entregues em 30 dias e a próxima e a
   última reunião. Se o nome bater com mais de um perfil, pergunte qual é.
3. Responda conforme o assunto:
   - Conteúdo: diga o status e o prazo que estão no ClickUp. Atrasado: diga o próximo passo e quem cuida, sem culpar setor.
   - Reunião: confirme a data da próxima. Se não houver, ofereça /agendar-reuniao.
   - Resultado, anúncio, saldo ou criativo no ar: a CS não tem esse número. Acolha, diga que o gestor do cliente
     (nome do perfil) responde com os números, e entregue também a mensagem para a CS mandar ao gestor.
   - Reclamação: acolha sem discutir, diga o próximo passo e quem cuida. Se já houver alerta aberto, considere o
     encaminhamento dele. Reclamação séria sem alerta: oriente a CS a abrir o alerta no ClickUp (ação dela) e avisar a liderança.
   - Preço, contrato ou pagamento: encaminhar para a liderança, nunca discutir no grupo.
4. Resposta em até 6 linhas: acolhe, responde com o fato, diz o próximo passo e quem cuida.

## Regras
- Só leitura no ClickUp. Sem promessa de resultado. Sem travessão. Nada é enviado pela skill.
- Nome de paciente não aparece na resposta.
