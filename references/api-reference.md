# Referência rápida da Marketing API (o que a casa usa)

Versão fixada nos scripts: v21.0 (revisar antes de 21/01/2027).

## Objetivos e otimização
| Uso | objective | optimization_goal | destination_type |
|---|---|---|---|
| Captação via WhatsApp (padrão) | OUTCOME_SALES | CONVERSATIONS | WHATSAPP |
| Tráfego para o perfil (raro) | OUTCOME_TRAFFIC | LINK_CLICKS | (nenhum) |

Status: ACTIVE, PAUSED, ARCHIVED. `effective_status` de anúncio: ACTIVE, PAUSED, DISAPPROVED, WITH_ISSUES, PENDING_REVIEW, CAMPAIGN_PAUSED, ADSET_PAUSED.

## Orçamento
Sempre em centavos: 5000 = R$ 50,00. `daily_budget` no conjunto (ABO). Campanha ABO precisa de
`is_adset_budget_sharing_enabled: false`.

## Segmentação (targeting)
```json
{
  "geo_locations": {"cities": [{"key": "2469437", "radius": 10, "distance_unit": "kilometer"}]},
  "age_min": 25, "age_max": 60,
  "publisher_platforms": ["instagram"],
  "instagram_positions": ["stream", "story", "reels", "explore", "explore_home"],
  "targeting_automation": {"advantage_audience": 0},
  "custom_audiences": [{"id": "..."}]
}
```
Chaves de cidade e bairro: `targeting.py geolocations --q "Nome"`. Bairro sem chave: `custom_locations` com latitude, longitude e raio.
Editar targeting envia o objeto inteiro: o que não for reenviado é apagado. Ler antes, mesclar, enviar.

## Criativo
Post existente do Instagram:
```json
{"source_instagram_media_id": "<id da mídia>", "instagram_user_id": "<ig do cliente>",
 "call_to_action": {"type": "WHATSAPP_MESSAGE", "value": {"app_destination": "WHATSAPP", "link": "https://api.whatsapp.com/send"}},
 "page_welcome_message": "<JSON copiado de um anúncio ativo da conta>"}
```
Vídeo novo: `object_story_spec.video_data` com `video_id`, `message`, `image_url` (thumbnail), `call_to_action` acima, mais `instagram_user_id` e `page_welcome_message` fora do `video_data`.
Vídeo grande: upload em partes em `/act_X/advideos` (start, transfer, finish) ou por `file_url` público; esperar `status.video_status == ready`.
Aprimoramentos: `degrees_of_freedom_spec.creative_features_spec` com cada recurso em `{"enroll_status": "OPT_OUT"}`; a chave `standard_enhancements` foi descontinuada (erro 3858504 se enviada).

## Insights
Mensagens iniciadas: action_type `onsite_conversion.messaging_conversation_started_7d`.
Períodos: `date_preset` (today, yesterday, last_7d, last_14d, last_30d, maximum) ou `time_range` `{"since": "AAAA-MM-DD", "until": "AAAA-MM-DD"}`. Várias janelas de uma vez: `time_ranges`.
Níveis: account, campaign, adset, ad. Segmentações: age, gender, publisher_platform, platform_position.

## Erros que a casa já conhece
| Código | Significado | O que fazer |
|---|---|---|
| 190 | token inválido ou vencido | gerar token novo (passo 6 do guia) |
| 200 | sem permissão na conta | conta não atribuída na BM ou permissão faltando no token |
| 4, 17, 32, 613, 80004 | limite de chamadas | esperar 60 s e repetir |
| subcode 1885183 | app em modo Desenvolvimento | publicar o app |
| subcode 2875030 | reel com música protegida | pedir repost com áudio livre ou usar outro post |
| 105 (child_attachments has too many elements) | carrossel com mais de 10 cartões | escolher outro post; o script recusa antes de enviar |
| 100, subcode 2446885 | o WhatsApp da Página é conta pessoal | conectar um WhatsApp Business à Página antes de criar conjunto de conversa |
| subcode 3858749 | a Página está na BM do cliente e recusa o criativo | pedir ao admin da BM do cliente acesso para a pessoa |
| subcode 3858504 | chave standard_enhancements enviada | remover a chave |
| subcode 1870227 | advantage_audience ausente | enviar targeting_automation explícito |
| subcode 2490392 | explore_home sem explore | incluir explore nas posições |
| subcode 2654 | subtype em público de engajamento | criar o público sem subtype |
