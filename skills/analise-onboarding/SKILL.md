---
name: analise-onboarding
description: Analisa o onboarding dos clientes para o head: tempo médio para concluir, quais estão em andamento e há quantos dias, quais etapas mais demoram e de qual setor. Use quando o head disser "como está o onboarding", "tempo médio de onboarding", "onboarding travado", "qual etapa demora mais", "análise de onboarding" ou "/analise-onboarding".
---

# /analise-onboarding

Fonte: lista Onboarding do ClickUp, uma tarefa-mãe por cliente com uma subtarefa por etapa
(`scripts/onboarding.py resumo`, skill meta-ads-odontorise, só leitura).

## Como responder
1. Rode `onboarding.py resumo`.
2. Entregue:
   - Tempo médio e mediano para concluir, com os três mais lentos.
   - Em andamento: cliente · dias desde o início · etapas feitas de total · próximas etapas com setor e responsável.
     🔴 os que passaram do dobro do tempo médio.
   - Etapas que mais demoram (dias desde o início do onboarding até a conclusão), com o setor dono de cada uma.
   - Três apontamentos: etapa gargalo, setor gargalo, cliente a destravar hoje.
3. Ofereça o texto para cobrar o responsável da próxima etapa do cliente mais travado.

## Regras
- Só leitura. Sem travessão. Números reais, período explícito.
