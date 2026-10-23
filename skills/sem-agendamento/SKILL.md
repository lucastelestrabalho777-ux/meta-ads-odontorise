---
name: sem-agendamento
description: Clientes do gestor sem agendamento registrado no Metrics há mais de 15 dias, com a data do último agendamento e quantos leads entraram no mesmo período, para separar problema de comercial da clínica de problema de volume. Use quando o gestor ou o head disser "sem agendamento", "cliente que não agenda", "agenda parada", "quem não agendou nos últimos 15 dias" ou "/sem-agendamento".
---

# /sem-agendamento

Fonte: MCP do Metrics, só leitura (`search_leads`). Se as ferramentas `mcp__metrics__*` não aparecerem, a pessoa
ainda não conectou o Metrics: mande seguir o passo "Conectar o Metrics" do guia e pare.
Alcance: só os clientes da pessoa (`list_companies` cruzado pelo nome com `scripts/clientes.py listar` da skill
meta-ads-odontorise). O head, quando pedir a carteira toda, vê todas.

## Como responder
1. Data de início do Metrics de cada empresa: `search_leads` com `sort: "data_criacao"`, `order: "asc"`, `limit: 1`,
   `output: "summary"`. Com menos de 30 dias, a empresa vai para a lista "Metrics novo desde DD/MM" e não entra no ranking.
2. Último agendamento: `search_leads` com `date_field: "stage_date_agendado"`, `sort: "stage_date_agendado"`,
   `order: "desc"`, `limit: 1`, `output: "full"` e os últimos 180 dias. A data está em `datas_acao.stage_date_agendado`.
   Se a etapa não existir, rode `list_pipelines_and_config` e use o slug da etapa de categoria `scheduling`.
3. Leads que entraram nos últimos 15 dias: `search_leads` com `output: "count"` e o período.
4. Entregue:
   - 🔴 Sem agendamento há mais de 15 dias, do mais parado para o menos: data do último agendamento, dias sem agendar
     e leads que entraram nos 15 dias.
   - 🟡 Entre 8 e 15 dias.
   - ✅ Agendou nos últimos 7 dias: só a contagem.
   - Metrics novo: à parte, com a data de início.
5. Leitura de cada 🔴: leads entrando e agenda parada é gargalo no comercial da clínica; poucos leads é volume, e aí
   vale olhar a conta (/contas-criticas).

## Regras
- Antes de cobrar, confirme se a clínica registra o agendamento no Metrics. Se o último agendamento tem a mesma data de
  compareceu e comprou, a equipe só marca quem fecha: "sem agendamento" vira "sem venda registrada".
- Só leitura e só sugestão. Sem travessão.
