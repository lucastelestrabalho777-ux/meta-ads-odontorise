---
name: subir-criativos-drive
description: Sobe vídeos e imagens de um link do Google Drive (pasta ou arquivo) como anúncios PAUSADOS num conjunto que já existe na conta do cliente, direto do Drive para o Gerenciador, sem baixar nada no computador. Use quando o gestor mandar um link drive.google.com pedindo para subir anúncio, ou disser "sobe os criativos desse drive", "sobe esse vídeo do drive no conjunto X", "pega os vídeos da pasta e sobe na campanha", "subir criativo do drive" ou "/subir-criativos-drive".
---

# /subir-criativos-drive

O gestor manda o link do Drive e diz o cliente e o conjunto. A Meta busca cada vídeo direto no Drive pelo link:
nada é baixado no computador (imagem passa só pela memória). Cada arquivo vira um anúncio PAUSADO no conjunto, com
Página, Instagram, botão de WhatsApp, título, boas-vindas e UTMs copiados do anúncio que já roda nesse conjunto.

## Passos
1. Leia o Drive: `scripts/drive.py listar --link "<link>"` (skill meta-ads-odontorise). Se vier erro de link restrito,
   mostre ao gestor o campo `acao` (como liberar o link) e pare. Subpasta aparece com o próprio link: liste se o gestor quiser.
2. Ache o destino: `read.py campaigns --cliente X` e `read.py adsets-by-campaign --campaign ID`. Confirme o conjunto
   com o gestor pelo nome.
3. Para cada arquivo, combine com o gestor o nome do anúncio (seguir o padrão dos anúncios do conjunto, ex.: `AD-VD Caso JP`)
   e a legenda. Legenda: a que o gestor mandar. Sem legenda, pergunte; se ele quiser que a IA escreva, siga o estilo das
   legendas dos anúncios ativos da conta (`read.py creative --id`).
4. Rode o ensaio de cada arquivo:
   `scripts/create.py anuncio-drive --cliente X --conjunto ID --arquivo "<link ou id>" --nome "..." --legenda "..."`.
   Mostre uma tabela: arquivo · tipo · tamanho · campanha · conjunto · onde entrega · anúncio modelo · nome · começo da legenda ·
   boas-vindas copiadas · PAUSADO. Se vier `aviso`, mostre.
5. Só com OK explícito, repita cada um com `--confirmo`, um arquivo por vez. Vídeo leva de 1 a 5 minutos (a Meta busca no
   Drive e processa).
6. Valide cada anúncio: `read.py ad --id <anuncio_id>` e `read.py preview --creative <criativo_id> --format all`.
   Entregue a lista com os links da prévia.
7. Ofereça registrar no ClickUp (/registrar-otimizacao, tarefa "Anúncio novo").

## Regras
- Tudo nasce PAUSADO. Ativar é decisão do gestor.
- Só conjunto que já existe. O posicionamento é o do conjunto (o ensaio mostra onde ele entrega); a skill não muda.
- Nunca baixar o vídeo no computador para subir. Drive restrito: pedir para liberar o link.
- Rosto de paciente só com termo assinado. Antes e depois explícito tem risco de reprovação na Meta: avisar o gestor.
- Sem travessão.
