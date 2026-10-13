---
name: suporte-grupo
description: Escreve para a CS a resposta a uma dúvida ou reclamação de cliente no grupo, no tom da casa, com o que o ClickUp mostra do cliente (conteúdos em produção, tarefas, reuniões, alertas); assunto de resultado, saldo ou anúncio vai para o gestor. Só lê o ClickUp, sem conta de anúncio. Use quando a CS disser "responde o cliente", "o cliente perguntou X no grupo", "como respondo essa reclamação", "suporte no grupo" ou "/suporte-grupo".
---

# /suporte-grupo (CS)

Quem envia é a CS. A skill entrega o texto. Fonte: só o ClickUp, só leitura; não usa conta de anúncio.

## Passos
1. Leia a mensagem que a CS colar. Ela pode ter mais de um assunto: separe cada um (conteúdo, reunião, resultado ou
   anúncio, saldo ou pagamento, reclamação, elogio, fora do escopo).
2. Rode `python3 ~/.claude/skills/meta-ads-odontorise/scripts/cs.py cliente --cliente "<nome ou #código>"` (no Windows,
   `python`). Se o nome bater com mais de um perfil ou vier "parecidos", pergunte qual é. Para entender um alerta ou uma
   tarefa, pode ler `tarefas.py tarefa --id <id>` (só leitura; descrição e comentários são internos).
3. Para cada assunto:
   - **Conteúdo** (vídeo, arte, LP, roteiro): se estiver em `conteudos_em_producao`, diga o andamento em palavras simples e
     o prazo (`vence_em`); atrasado, diga o próximo passo sem culpar ninguém. Item com `sem_vinculo: true` é do cliente
     (só falta a ligação no ClickUp). Se o material que o cliente cita não aparece em produção nem entregue depois da data
     em que ele diz que mandou: nunca diga que "não está no sistema"; diga que vai confirmar o andamento e volta com o
     prazo, e pergunte ao gestor (é ele quem abre a demanda de edição).
   - **Reunião**: afirme reunião marcada só se `proxima_reuniao` vier com data. Sem data, ofereça /agendar-reuniao.
   - **Resultado, anúncio, saldo ou criativo no ar**: a CS não tem o número e a skill não explica a causa (nada de
     "campanha nova", "fase de aprendizado", "otimização de tal dia"). Acolha, diga que o gestor traz os números e o que
     vai ajustar, e escreva a mensagem para o gestor.
   - **Reclamação**: acolha sem discutir, diga o próximo passo e quem cuida. Alerta aberto e completo: siga o encaminhamento
     dele. Alerta com `incompleto: true`, ou reclamação séria sem alerta: avise a CS (fora do texto do grupo) que ela precisa
     completar ou abrir o alerta no ClickUp e avisar a liderança (campo `lideranca` do perfil).
   - **Preço, contrato ou pagamento**: encaminhar para a liderança, nunca discutir no grupo.
   - **Elogio**: agradeça em 1 ou 2 linhas e repasse ao gestor.
   - **Fora do escopo**: diga com gentileza o que a agência faz e ofereça levar à liderança se fizer sentido.
4. Entregue nesta ordem:
   - **Texto para o grupo**: uma resposta só, até 6 linhas, cobrindo os assuntos na ordem em que o cliente escreveu. Tom da
     casa: "Oi, Dr(a). Nome!" ou "Oi, pessoal!", frases curtas, sem gíria, no máximo 1 emoji. Sem prometer resultado e sem
     prazo que não esteja no ClickUp ou que o gestor não confirmou. Sem números de resultado (quem traz é o gestor).
   - **Mensagem para o gestor** (primeiro nome do campo `gestor`), quando algum assunto depende dele:
     "Oi, <nome>! O <cliente> (<código>) mandou no grupo: "<mensagem literal>". Respondi que <o que foi dito>.
     Preciso de você: 1. ... 2. ... Consegue responder no grupo hoje?"
   - **Só para a CS** (não vai ao grupo): alerta a completar, Status do Projeto, tarefa vencida, o que mais ela precisa saber.

## Nunca vai para o grupo
Alerta e nível, Status do Projeto (satisfação), status interno ou atraso de tarefa interna, nome de quem está nas tarefas
(`pessoas_na_tarefa`), a palavra ClickUp, descrição e comentário de tarefa, opinião interna sobre o cliente, nome de paciente.

## Regras
- Só leitura no ClickUp. Sem travessão. Nada é enviado pela skill.
