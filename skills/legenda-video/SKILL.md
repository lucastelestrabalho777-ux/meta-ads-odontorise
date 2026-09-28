---
name: legenda-video
description: Transcreve a fala de um vídeo (reel ou criativo) e escreve a legenda de anúncio para conversão ao WhatsApp no estilo dos anúncios que já rodam na conta do cliente. Use quando o gestor disser "legenda para esse vídeo", "transcreve o vídeo", "escreve a copy desse reel", "legenda-video" ou "/legenda-video".
---

# /legenda-video

1. **Localize o vídeo**: caminho informado ou `--downloads-latest 1` (o mais recente em Downloads).
2. **Transcreva** com `scripts/transcrever.py` da skill meta-ads-odontorise, usando o Python do ambiente
   de transcrição (Mac Apple: `~/.cache/whisper-venv/bin/python`). Se o ambiente não existir, mostre ao
   gestor os dois comandos do cabeçalho do script e pare. Nunca envie o vídeo a serviço externo.
3. **Pegue o estilo da conta**: `read.py ads-by-campaign` numa campanha ativa e `read.py creative --id`
   de dois ou três anúncios com mais mensagens (`insights.py resultado --level ad --limit 5`), e leia o texto deles.
4. **Escreva a legenda** em 3 versões curtas (gancho diferente em cada), no padrão dos anúncios ativos:
   primeira linha que prende, promessa concreta do procedimento, chamada para "chamar no WhatsApp".
   Sem promessa de resultado garantido, sem preço, sem "antes e depois" em texto quando o vídeo não mostra.
   Paciente final sempre. Sem travessão.
5. Entregue as 3 versões e pergunte qual usar. Só se o gestor pedir, siga para subir o anúncio pela
   skill Meta (create.py, tudo pausado).

## Regras
- Vídeo sem fala: não transcrever; usar a legenda de um anúncio ativo como base e avisar.
- Se o vídeo citar procedimento que não é do cliente (mentoria, curso, dentista como público): parar e avisar.
