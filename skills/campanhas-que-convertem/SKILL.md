---
name: campanhas-que-convertem
description: Quais campanhas e criativos trouxeram leads qualificados na semana (qualificado, agendou, compareceu, fechou) em cada cliente do gestor, com investimento, custo por lead, status da campanha, de onde vieram os últimos 10 agendamentos e o que manter, revisar e pedir de conteúdo à doutora. Lê o Metrics e a conta Meta. Use quando o gestor ou o head disser "quais campanhas geraram agendamento", "de onde vêm os agendamentos", "criativo campeão", "campanha que mais vende", "campanhas que convertem" ou "/campanhas-que-convertem".
---

# /campanhas-que-convertem

Fonte: MCP do Metrics, só leitura (`get_ads_performance`, `search_leads`), e o status das campanhas pela skill
meta-ads-odontorise (`scripts/read.py campaigns --cliente X --status ALL`). Se as ferramentas `mcp__metrics__*` não
aparecerem, a pessoa ainda não conectou o Metrics: mande seguir o passo "Conectar o Metrics" do guia e pare.
Alcance: só os clientes da pessoa (`list_companies` cruzado pelo nome com `scripts/clientes.py listar`). O head, quando
pedir a carteira toda, vê todas.

Período: os últimos 7 dias fechados, até ontem. A pessoa pode pedir outro período ou um cliente só.

## Como responder (por cliente)
1. `get_ads_performance` com `level: "campanha"` e depois `level: "anuncio"`. Leads são as conversas que entraram no
   período; as etapas (qualificado, agendado, compareceu, comprou) contam quem avançou no período, atribuído à campanha
   que trouxe o lead, mesmo que o lead seja de antes.
2. Junte as linhas do mesmo anúncio: quando o nome se repete em mais de uma campanha, o Metrics põe o gasto em linhas
   "nome (id:...)" com 0 lead. Some esse investimento ao anúncio de mesmo nome antes de calcular custo por lead.
3. "Click to Chat", "Campanha não rastreada", "Ad não rastreado" e "Não informado" são leads sem anúncio identificado
   (link da bio, indicação ou anúncio sem rastreio). Mostre juntos, numa linha só.
4. Últimos 10 agendamentos: `search_leads` com `date_field: "stage_date_agendado"` nos últimos 60 dias,
   `sort: "stage_date_agendado"`, `order: "desc"`, `limit: 10`, `output: "summary"`. Conte por campanha e anúncio.
5. Status de cada campanha que gastou: `read.py campaigns --cliente X --status ALL` (ativa ou pausada, orçamento por dia).
6. Link do criativo campeão: ache o id do anúncio pelo nome em `read.py ads --cliente X --status ALL` (ou no
   `rastreamento.meta.source_id` dos leads do Metrics). Link do Instagram: `read.py creatives-by-ad --ad <id>`, campo
   `instagram_permalink_url`. Prévia que abre sem login: `read.py ad --id <id> --fields preview_shareable_link`.
   Se o mesmo criativo roda em outras versões (Feed, Stories, outro público), liste cada uma com status e link.
7. Entregue:
   - Tabela por campanha: status e orçamento · investimento · leads · custo por lead · qualificado · agendou ·
     compareceu · fechou · faturamento.
   - Criativo campeão: o anúncio com mais agendamento e venda por real investido, com os números, o link do
     Instagram e a prévia.
   - De onde vieram os últimos 10 agendamentos, em contagem: "6 de 10 sem anúncio identificado, 3 de 10 do anúncio X
     da campanha Y".
   - 🔴 Campanha ativa que gastou na semana sem nenhum lead ou sem nenhum avanço de etapa.
8. Feche com no máximo 3 sugestões concretas: manter ou escalar a campanha que agenda, pedir à doutora mais conteúdo no
   formato do criativo campeão (dizer qual e por quê), revisar a campanha que gasta sem agendar.

## Regras
- Só sugere, nada é alterado. Antes de sugerir pausa ou corte de verba, rode
  `scripts/insights.py comparar-janelas --cliente X --level ad` (30, 14 e 7 dias): nunca decidir por uma janela só.
- Semana com menos de 5 agendamentos é leitura fraca: diga isso e apoie a conclusão nos últimos 10 agendamentos.
- Cliente com Metrics há menos de 30 dias (lead mais antigo em `search_leads`, `sort: "data_criacao"`, `order: "asc"`):
  avise que o histórico é curto.
- Sem travessão.
