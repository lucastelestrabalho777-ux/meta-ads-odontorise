# Padrões de campanha (OdontoRise)

O Claude DEVE ler este arquivo antes de criar ou avaliar qualquer campanha. O padrão da casa é um só,
captação via WhatsApp, com três variações por procedimento. Tudo nasce pausado e só ativa com OK do gestor.

## Fluxo obrigatório

### Antes de criar: diagnóstico
1. Resolver o cliente pelo cadastro (`clientes.py`) e confirmar a conta Meta.
2. Ler as campanhas ativas da conta (`read.py campaigns --cliente X`) e um conjunto e um anúncio
   que estejam entregando (`read.py adsets-by-campaign`, `read.py ads-by-campaign`, `read.py creative`).
3. Extrair o que já funciona na conta: página, conta do Instagram, mensagem de boas-vindas do WhatsApp,
   públicos, cidade ou bairros, posicionamentos, desligamento dos aprimoramentos.
4. Usar isso como base. Só muda o que o gestor pediu (criativo, verba, público, nome).
5. Ler a legenda e o conteúdo do post escolhido e classificar: fala com o paciente final (sobe) ou é mentoria,
   conteúdo pessoal ou sem sentido para captação (não sobe; avisar o gestor e sugerir outro post).

### Depois de criar: validação
1. Ler o anúncio criado (`read.py ad --id`) e conferir `effective_status` (não pode ser DISAPPROVED).
2. Conferir o preview (`read.py preview --creative <id> --format all`).
3. Auditar o conjunto (`targeting.py auditar --adset <id>`): só Instagram, raio dentro do limite, público explícito.
4. Só então dizer ao gestor que está pronto para ativar. Ativar é decisão dele.

## Padrão base: Captação via WhatsApp

| Nível | Campo | Valor |
|---|---|---|
| Campanha | objective | `OUTCOME_SALES` |
| Campanha | orçamento | no conjunto (ABO); `is_adset_budget_sharing_enabled: false` |
| Campanha | nome | `[Odontorise] [Vendas] Captação de Leads - DD/MM` (sufixo livre) |
| Campanha | special_ad_categories | `[]` |
| Conjunto | optimization_goal | `CONVERSATIONS` |
| Conjunto | destination_type | `WHATSAPP` |
| Conjunto | promoted_object | `{"page_id": "<página do cliente>"}` |
| Conjunto | billing_event | `IMPRESSIONS` |
| Conjunto | bid_strategy | `LOWEST_COST_WITHOUT_CAP` |
| Conjunto | attribution_spec | `[{"event_type": "CLICK_THROUGH", "window_days": 1}]` |
| Conjunto | publisher_platforms | `["instagram"]` (nunca facebook, audience_network ou messenger) |
| Conjunto | instagram_positions | `["stream", "story", "reels", "explore", "explore_home"]` (explore_home exige explore) |
| Conjunto | geo | cidade do cliente ou bairros; raio só se já existir na conta e nunca ampliado |
| Conjunto | targeting_automation | `{"advantage_audience": 0}` ou `1`, sempre explícito |
| Conjunto | daily_budget | em centavos (10000 = R$ 100,00), confirmado com o gestor |
| Criativo | instagram_user_id | conta do Instagram do cliente (obrigatório) |
| Criativo | botão | `WHATSAPP_MESSAGE` com `{"app_destination": "WHATSAPP", "link": "https://api.whatsapp.com/send"}` |
| Criativo | page_welcome_message | copiada de um anúncio ativo da conta (mensagem de boas-vindas com pergunta que qualifica) |
| Criativo | degrees_of_freedom_spec | `advantage_plus_creative: OPT_OUT` e demais recursos OPT_OUT; NUNCA incluir a chave `standard_enhancements` |
| Anúncio | status | `PAUSED` ao nascer, sem exceção |

Criativo a partir de post do Instagram: `source_instagram_media_id` + `instagram_user_id` + botão WhatsApp
+ `page_welcome_message`. Sem `object_story_spec`. Reels com música protegida não podem virar anúncio (erro 2875030).

Estrutura de teste de criativos: 1 conjunto = 1 criativo x 1 público. N criativos e 2 públicos = 2N conjuntos,
1 anúncio em cada. Não agrupar criativos num conjunto só.

## Variações por procedimento

### Lentes (lentes de contato dental e facetas)
- Ângulo do criativo: transformação natural do sorriso, antes e depois em vídeo com o dentista explicando,
  "ninguém percebe que você fez".
- Pergunta que qualifica na mensagem de boas-vindas: o que a pessoa quer mudar no sorriso e se já fez avaliação.
- Objeções típicas: preço, medo de ficar artificial, desgaste do dente, durabilidade.
- Métrica: custo por mensagem iniciada; volume alto é esperado, a qualificação vem da conversa.

### Implantes
- Ângulo do criativo: voltar a mastigar e sorrir, prótese fixa, resolução em uma etapa, segurança do procedimento.
- Pergunta que qualifica: quantos dentes faltam ou se usa prótese removível hoje.
- Objeções típicas: dor, tempo de tratamento, preço parcelado, medo de cirurgia.
- Métrica: custo por mensagem iniciada; lead costuma ser mais velho, público 35 ou mais quando a conta já valida isso.

### Harmonização facial
- Usada como última via: só quando o cliente pede ou quando não há procedimento de maior ticket para anunciar.
- Ângulo do criativo: naturalidade, profissional habilitado, segurança e resultado sutil.
- Pergunta que qualifica: qual região quer tratar e se já fez algum procedimento.
- Objeções típicas: medo de exagero, preço, dor.
- Métrica: custo por mensagem iniciada; concorrência maior, comparar sempre as três janelas antes de mexer.

## Como adicionar um padrão novo
Só depois de rodar de verdade: preview sem erro, entregando por pelo menos 7 dias, custo por mensagem
dentro do esperado. Formato: nome, tabela por nível, regras críticas (o que quebra se não fizer), exemplo completo.
