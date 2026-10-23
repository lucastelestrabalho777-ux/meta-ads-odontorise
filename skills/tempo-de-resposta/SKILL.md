---
name: tempo-de-resposta
description: Tempo de resposta da clínica aos leads no WhatsApp nos últimos 7 dias, separado em horário comercial, depois do horário e fim de semana, com cada lead que ficou sem resposta. Lê o Metrics. Use quando o gestor ou o head disser "tempo de resposta", "a clínica está demorando para responder", "quem ficou sem resposta", "atendimento da secretária", "SLA de atendimento" ou "/tempo-de-resposta".
---

# /tempo-de-resposta

Fonte: MCP do Metrics, só leitura (`get_attendance_report`). Se as ferramentas `mcp__metrics__*` não aparecerem, a pessoa
ainda não conectou o Metrics: mande seguir o passo "Conectar o Metrics" do guia e pare.
Alcance: só os clientes da pessoa. Liste as empresas com `list_companies` e cruze pelo nome com o cadastro local
(`scripts/clientes.py listar` da skill meta-ads-odontorise). Empresa que não bate com nenhum cliente fica de fora; nome
parecido mas não igual, pergunte. O head, quando pedir a carteira toda, vê todas.

Período: os últimos 7 dias fechados, até ontem, no horário de Brasília. Faixas pela hora em que o lead escreveu:
- Horário comercial: segunda a sexta, das 8h às 18h. Se a pessoa disser o horário da clínica, use o dela.
- Depois do horário: segunda a sexta, antes das 8h ou depois das 18h.
- Fim de semana: sábado e domingo.

## Como responder
1. Por empresa, `get_attendance_report` do período com `as_of: "fim_do_periodo"`, e de novo com `kind: "fora_sla"` e
   `kind: "sem_resposta"` (`limit: 200`) para ter `lead_falou_em` e `respondida_por_humano_em` de cada conversa.
   Os horários vêm em UTC: tire 3 horas.
2. `get_attendance_report` só do sábado e do domingo do período, para o total do fim de semana.
3. Separe as conversas das listas por faixa. As respondidas em até 15 min (`dentro_do_sla`) que não são do fim de
   semana contam como horário comercial: o Metrics não dá o horário delas.
4. Saudação automática: mediana (`tempo_mediano_resposta_min`) abaixo de 1 minuto quase sempre é a mensagem automática
   do WhatsApp Business contando como resposta da equipe. Confira: `list_chats` com `active_from` e `active_to` do
   período, abra 5 conversas iniciadas pelo lead com `get_chat_messages` no dia do primeiro contato e olhe a primeira
   mensagem da equipe. Se chega em segundos e o texto se repete entre as conversas, é automática. Meça até a primeira
   resposta que não é a automática e, no horário comercial, mostre "tempo real numa amostra de 5: X min" com
   ⚠️ saudação automática, no lugar do % em até 15 min (que fica inflado).
5. Entregue por cliente, uma linha por faixa:
   - Horário comercial: conversas, % respondidas em até 15 min e cada lead sem resposta com nome, dia e hora.
   - Depois do horário: conversas e a que horas a equipe respondeu no dia seguinte (a hora mais comum).
   - Fim de semana: conversas e quando foram respondidas: no sábado, no domingo ou só na segunda.
6. No fim: a carteira ordenada pelo % em até 15 min no horário comercial, a lista de todos os leads de horário
   comercial sem resposta (🔴, para avisar a clínica hoje) e quanto da semana chegou fora do horário.

## Regras
- Não use a média em minutos: uma conversa da noite respondida de manhã puxa tudo para cima. A mediana do Metrics
  também mistura as três faixas.
- Lead da noite respondido de manhã não é falha da secretária. Se muita coisa chega fora do horário, sugira uma
  mensagem noturna ou o agente de IA do Metrics para segurar o lead até a manhã.
- Só leitura e só sugestão: cobrar a clínica e mudar processo é decisão do gestor com o cliente. Sem travessão.
