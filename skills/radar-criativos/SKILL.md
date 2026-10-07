---
name: radar-criativos
description: Lê os posts orgânicos do Instagram do cliente (últimos 7 dias, mais o radar de 30), diz quais falam com o paciente e valem anúncio e quais não (mentoria, pessoal, institucional, política), ranqueia por engajamento e sobe os aprovados como anúncios PAUSADOS num conjunto que já existe, mantendo curtidas e comentários do post. Use quando o gestor disser "radar de criativos", "sobe os posts da semana do cliente X", "quais posts do X valem anúncio", "transforma esse reel em anúncio", "analisa os posts do cliente", "turbinar o post", "impulsionar o post pelo gerenciador" ou "/radar-criativos".
---

# /radar-criativos

Base (skill meta-ads-odontorise): `posts.py listar --cliente X --dias 7 --radar 30` (só leitura) e
`create.py anuncio-post --cliente X --conjunto ID --media-id ID --nome "..."` (ensaio; `--confirmo` só com OK).
Só clientes do cadastro do gestor. O script lê e sobe; quem classifica é o Claude, com a legenda e a capa.
Subcomandos por id (`read.py adset --id`, `ads-by-adset --adset`, `ad --id`, `posts.py post --id`) não levam `--cliente`.

## Passos

1. Rode `posts.py listar`. Erro de Instagram não ligado ou sem permissão: mostre a `acao` e pare.
2. Classifique cada post da janela pela legenda e, quando ela não bastar, pela capa (campo `capa`) e pelo link:

   | Classe | O que é | Vira anúncio? |
   |---|---|---|
   | paciente final | caso clínico, tratamento, benefício, dúvida de paciente, convite para avaliação, depoimento | sim |
   | mentoria | fala com dentista: curso, método, vagas, "para colegas", bastidor de consultório como ensino | não |
   | pessoal | família, viagem, rotina, opinião, lazer, data comemorativa sem oferta | não |
   | institucional ou aviso | endereço novo, horário, feriado, recado, vaga de emprego | não; se for oferta com praça, avisar o gestor |
   | política ou polêmica | eleição, voto, posicionamento | não, nunca |

   Em dúvida entre paciente final e mentoria: quem compra? Paciente = sobe. Qualquer dúvida entre duas classes: marque (?)
   com as duas e deixe o gestor decidir. Tema eleitoral usado como piada (eleição, voto, candidato) continua não subindo: a
   Meta trata como anúncio político. Post datado (evento, promoção ou data que já passou) não sobe sem o gestor aceitar o texto.
   Como ver a capa: baixe a URL do campo `capa` com `curl -sL "<url>" -o <pasta temporária>/capa.jpg` e abra a imagem (a URL é
   assinada e vence em horas). Carrossel: a `capa` é o primeiro cartão; para ver todos, `posts.py post --id <id>` traz `cartoes[].capa`.
   Veja a capa sempre que a legenda deixar dúvida e em todo post que vai subir, para checar rosto de paciente.
3. Tabela da janela, um post por linha: data · formato · classe · curtidas · comentários · alcance · salvos · compartilhamentos ·
   taxa de engajamento · já é anúncio (conjunto) · link. Candidatos = paciente final que ainda não é anúncio, na ordem de
   `posicao_engajamento`. Radar (8 a 30 dias): só os paciente final sem anúncio, para o gestor recuperar se quiser. O radar vem
   só com curtidas e comentários; para ranquear o radar também, rode de novo com `--radar-insights`.
4. Destino: `read.py campaigns --cliente X` e `read.py adsets-by-campaign --campaign ID`, depois `read.py adset --id ID` do
   conjunto escolhido. Só conjunto ativo que converte em mensagem: `destination_type` WHATSAPP (ou `optimization_goal`
   CONVERSATIONS). Campanhas "Post do Instagram: ..." com LINK_CLICKS são boosts feitos pelo aplicativo e não servem de destino.
   Confira a praça no `read.py adset --id`: o DDD do número de WhatsApp (`promoted_object.whatsapp_phone_number`) e o raio ou
   as cidades do `targeting` têm que bater com o que o post fala; post de outra cidade não entra. Confirme o conjunto com o
   gestor pelo nome.
5. Nome do anúncio no padrão do anúncio mais recente do conjunto (`read.py ads-by-adset --adset ID --status ALL`; ex.:
   `AD - [Boost] Facetas naturais 05/10`). O ensaio não envia nada e roda sem OK: `create.py anuncio-post` sem `--confirmo` para
   cada candidato que o gestor quer ver. O ensaio bem-sucedido volta com `ok: false` e `ensaio: true` (é assim de propósito);
   recusa de verdade vem com `erro` e `acao`. Mostre: post (data, formato, link) · campanha · conjunto · `posicionamentos` ·
   `anuncio_modelo` · `botao` · `boas_vindas_copiadas` · `utms_copiadas` · `ja_anuncio_em_outro_conjunto` · PAUSADO.
   Avisos que o gestor precisa ouvir: UTMs não copiadas (o modelo não tinha; não bloqueia); a mensagem pré-preenchida do
   WhatsApp vem do anúncio modelo, então se o tema do post for outro (modelo fala de resina, post fala de faceta) avise que ele
   ajusta no Gerenciador antes de ativar. Se o script recusar (post já é anúncio neste conjunto, carrossel com mais de 10 cartões,
   post de outro Instagram), mostre o motivo e siga para o próximo.
6. Só com OK explícito por post, repita com `--confirmo`, um por vez. Valide cada um: `read.py ad --id <anuncio_id>` e
   `read.py preview --creative <criativo_id> --format all`. Anúncio novo aparece como PAUSED com `effective_status` IN_PROCESS
   ou PENDING_REVIEW até a Meta revisar: é normal.
7. Entregue a tabela final: post · classe · conjunto · anúncio_id · PAUSADO, mais os que não subiram com o motivo e os (?)
   para o gestor revisar. Ofereça registrar no ClickUp (/registrar-otimizacao, tarefa "Anúncio novo").

## Regras
- Tudo nasce PAUSADO. Ativar é decisão do gestor. Só conjunto que já existe: a skill não cria campanha nem conjunto.
- Regra 5 da casa: nas contas de cliente só paciente final vira anúncio. Mentoria, pessoal, institucional e política não sobem.
- Rosto de paciente só com termo assinado. Antes e depois explícito tem risco de reprovação na Meta: avisar o gestor.
- Não duplicar: post que já é anúncio no conjunto não sobe de novo (o script recusa). Em outro conjunto: avisar e seguir só com OK.
- Engajamento orgânico serve para ordenar os candidatos; o anúncio depois é julgado por mensagem iniciada.
- Toda linha de post leva o link. Sem travessão, nem o que vier em nomes da API (trocar por dois-pontos ou vírgula).
