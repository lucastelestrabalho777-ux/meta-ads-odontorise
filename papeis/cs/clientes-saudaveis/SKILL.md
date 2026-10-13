---
name: clientes-saudaveis
description: Lista para a CS os clientes que estão bem no relacionamento (satisfação boa no ClickUp, sem alerta aberto, reunião mensal em dia) como candidatos a depoimento, indicação ou novo serviço, e os que precisam de cuidado antes de qualquer oferta. Só lê o ClickUp, sem conta de anúncio. Use quando a CS disser "quem está bem", "clientes para depoimento", "quem pode indicar", "clientes saudáveis", "quem está satisfeito", "candidatos a upsell" ou "/clientes-saudaveis".
---

# /clientes-saudaveis (CS)

Fonte: só o ClickUp, só leitura. Não usa conta de anúncio nem a skill Meta Ads.

## Como responder
1. Rode `python3 ~/.claude/skills/meta-ads-odontorise/scripts/cs.py carteira` (no Windows, `python`).
   Demora uns 15 segundos. O script já classifica cada cliente ativo em `saudavel`, `quase`, `cuidado` ou `sem_dado`,
   com os motivos: não reclassifique por conta própria.
2. Entregue, com números reais:
   - ✅ Saudáveis: cliente · código · gestor · produto · satisfação · meses de casa (se houver) · reunião mensal ·
     sugestão e o gancho. Muito Satisfeito (Promotor): depoimento em vídeo do dentista ou indicação. Satisfeito:
     indicação. Produto Start com Promotor ou Satisfeito: conversa sobre o Select.
   - 🟡 Quase: o que falta, como o script diz (reunião mensal atrasada, ainda em onboarding, no show).
   - 🔴 Cuidado: o motivo (alerta aberto, Neutro ou pior) e quem age (gestor do cliente ou liderança).
     Nunca oferecer nada a quem está em cuidado.
   - Sem dado: quantos e quais estão com o Status do Projeto vazio no ClickUp (preencher é ação da CS no ClickUp).
3. Resultado de anúncio não está no ClickUp. Antes de qualquer oferta a um saudável, a CS confirma com o gestor do
   cliente: entregue a mensagem curta para o gestor ("o resultado do cliente X está estável ou melhorando? vou propor
   depoimento/indicação/Select").
4. Por último, o texto curto para a CS abrir a conversa de depoimento ou indicação com um cliente saudável, para usar
   só depois do OK do gestor.

## Regras
- Só leitura. Mudar o Status do Projeto, comentar ou abrir alerta são ações da pessoa, no ClickUp.
- Depoimento de paciente exige termo assinado; depoimento do dentista não.
- Sem travessão. Nada é enviado pela skill.
