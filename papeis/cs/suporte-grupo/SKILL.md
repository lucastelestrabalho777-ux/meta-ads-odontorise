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
     o prazo (`vence_em`); atrasado, diga o próximo passo sem culpar ninguém. Item com `sem_vinculo: true` também é do
     cliente. Se o material que o cliente cita não aparece em produção nem entregue depois da data
     em que ele diz que mandou: nunca diga que "não está no sistema"; diga que vai confirmar o andamento e volta com o
     prazo, e pergunte ao gestor (é ele quem abre a demanda de edição).
   - **Reunião**: afirme reunião marcada só se `proxima_reuniao` vier com data. Se a `fonte` for `perfil`, a data está só
     no perfil: no bloco da CS, peça para ela conferir na agenda antes de citar; no grupo, diga que confirma a data e volta.
     Não ofereça /agendar-reuniao nesse caso. Sem `proxima_reuniao`, ofereça /agendar-reuniao.
   - **Resultado, anúncio, saldo ou criativo no ar**: a CS não tem o número e a skill não explica a causa (nada de
     "campanha nova", "fase de aprendizado", "otimização de tal dia"). Acolha, diga que o gestor traz os números e o que
     vai ajustar, e escreva a mensagem para o gestor.
   - **Reclamação**: acolha sem discutir, diga o próximo passo e quem cuida. Se houver alerta aberto, considere o
     encaminhamento dele. Reclamação séria: sugira à CS levar à liderança (campo `lideranca` do perfil), com a mensagem pronta.
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
   - **Mensagem para a liderança** (primeiro nome do campo `lideranca`), sempre que houver preço, contrato, pagamento,
     fora do escopo ou reclamação séria, no mesmo modelo:
     "Oi, <nome>! O <cliente> (<código>) mandou no grupo: "<trecho literal>". Respondi que <o que foi dito>.
     Preciso de você: 1. ... Consegue retornar ao cliente hoje?"
   - **Só para a CS** (não vai ao grupo): observações que ajudam a decidir (há alerta aberto, satisfação registrada, reunião
     só no perfil), sem pedir mudança no ClickUp.

## Nunca vai para o grupo
Alerta e nível, Status do Projeto (satisfação), status interno ou atraso de tarefa interna, nome de quem está nas tarefas
(`pessoas_na_tarefa`), a palavra ClickUp, descrição e comentário de tarefa, opinião interna sobre o cliente, nome de paciente.

## Regras
- Só leitura e só sugestão: nunca pede para preencher campo, abrir ou completar alerta, mudar status ou reorganizar o
  ClickUp. Sem travessão. Nada é enviado pela skill.
