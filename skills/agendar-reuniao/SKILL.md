---
name: agendar-reuniao
description: Marca a reunião mensal ou de onboarding com um cliente da OdontoRise: propõe horários pelo Google Calendar da pessoa, cria o evento com o cliente convidado e deixa pronta a atualização da tarefa no ClickUp e a mensagem para o grupo. Use quando o CS ou o gestor disser "marca reunião com X", "agenda a mensal do cliente X", "horários para a reunião", "agendar-reuniao" ou "/agendar-reuniao".
---

# /agendar-reuniao

Pré-requisitos: conector Google Calendar conectado no claude.ai com a conta @odontorise.com (passo 8 do guia)
e token do ClickUp (passo 8). O e-mail do cliente vem do ClickUp (Perfil de Clientes) e não é gravado em lugar nenhum.

## Passos
1. **Identifique o cliente e a tarefa**: `tarefas.py reunioes --dias 30` lista as reuniões já criadas na
   lista Reuniões com Clientes; se a reunião do cliente estiver lá, use a data prevista e o id da tarefa.
2. **Proponha horários**: pelo conector do Calendar, encontre 3 horários livres na agenda da pessoa nos
   próximos 5 dias úteis, em horário comercial, com 45 minutos. Mostre as 3 opções e pergunte qual enviar ao cliente.
3. **Crie o evento** só depois do OK: título "Reunião mensal de performance: <cliente>", 45 minutos,
   convidado o e-mail do cliente (do Perfil de Clientes, campo Email; leia pelo ClickUp na hora, não copie para arquivo),
   descrição com 3 linhas do que será visto (resultado do mês, próximos passos, pendências), link de vídeo do Calendar.
4. **Entregue os textos**: a mensagem para o grupo do cliente confirmando dia e hora, e o comentário para a
   tarefa do ClickUp ("Reunião marcada para DD/MM às HH:MM, evento criado"). Registrar no ClickUp e enviar no grupo
   são ações da pessoa; ofereça e pare.

## Regras
- Nunca criar evento sem o OK explícito no horário escolhido.
- Não mover nem cancelar reunião existente por esta skill.
- Sem travessão nos textos.
