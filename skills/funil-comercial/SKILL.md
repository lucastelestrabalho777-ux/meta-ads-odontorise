---
name: funil-comercial
description: Taxa de conversão de cada etapa do funil comercial dos clientes do gestor nos últimos 30 dias (agendamento, comparecimento e venda), a etapa que mais trava em cada cliente e na carteira toda. Lê o Metrics. Use quando o gestor ou o head disser "funil comercial", "taxa de conversão dos clientes", "qual etapa preciso melhorar", "quantos agendam, comparecem e fecham" ou "/funil-comercial".
---

# /funil-comercial

Fonte: MCP do Metrics, só leitura (`get_overview_metrics`). Se as ferramentas `mcp__metrics__*` não aparecerem, a
pessoa ainda não conectou o Metrics: mande seguir o passo "Conectar o Metrics" do guia e pare.
Alcance: só os clientes da pessoa (`list_companies` cruzado pelo nome com `scripts/clientes.py listar` da skill
meta-ads-odontorise). O head, quando pedir a carteira toda, vê todas.

## Como responder
1. Data de início do Metrics de cada empresa: `search_leads` com `sort: "data_criacao"`, `order: "asc"`, `limit: 1`,
   `output: "summary"`. Com menos de 30 dias, a empresa vai para a lista "Metrics novo desde DD/MM" e fica fora das médias.
2. Por empresa, `get_overview_metrics` dos últimos 30 dias fechados, até ontem. Use `funil.taxas`: agendamento
   (agendou sobre leads válidos), comparecimento (compareceu sobre agendou) e venda (fechou sobre compareceu), com os
   números de cada etapa, mais `financeiro.faturamento_total` e `financeiro.investimento_total`.
3. Mês anterior: só para empresa com Metrics há mais de 60 dias, rode `get_overview_metrics` de novo com as datas dos
   30 dias anteriores. Não use `compare: true`: o período anterior vem com datas erradas e tudo zerado.
4. Registro incompleto: taxa acima de 100%, ou agendou, compareceu e fechou com o mesmo número, quer dizer que a clínica
   pula etapa e marca só quem fecha. Mostre o cliente com ⚠️ registro incompleto e deixe fora da média da carteira.
5. Entregue uma tabela por cliente: leads · agendou (% e número) · compareceu · fechou · faturamento · variação de cada
   taxa contra os 30 dias anteriores.
6. Média da carteira somando os números dos clientes (não a média das porcentagens), sem Metrics novo e sem registro
   incompleto. Em cada cliente, aponte a etapa mais abaixo da média da carteira.
7. Feche com a etapa que mais trava na carteira toda e uma sugestão concreta para ela (atendimento, confirmação de
   consulta, follow-up de orçamento), dizendo em quais clientes começar.

## Regras
- Investimento zerado com leads de anúncio: a empresa pode estar ligada a uma conta de anúncio antiga no Metrics.
  Avise, não calcule retorno.
- Só leitura e só sugestão. Sem travessão.
