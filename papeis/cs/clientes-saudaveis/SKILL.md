---
name: clientes-saudaveis
description: Lista para a CS os clientes que estão bem no relacionamento (satisfação boa no ClickUp, sem alerta aberto, reunião mensal em dia) como candidatos a depoimento ou indicação, e os que precisam de cuidado antes de qualquer pedido. Só lê o ClickUp, sem conta de anúncio. Use quando a CS disser "quem está bem", "clientes para depoimento", "quem pode indicar", "clientes saudáveis", "quem está satisfeito", "candidatos a upsell" ou "/clientes-saudaveis".
---

# /clientes-saudaveis (CS)

Fonte: só o ClickUp, só leitura. Não usa conta de anúncio nem a skill Meta Ads.

## Como responder
1. Rode `python3 ~/.claude/skills/meta-ads-odontorise/scripts/cs.py carteira` (no Windows, `python`). Leva uns 15 segundos.
   A saída é JSON com um cliente por linha, separado por classe: `saudavel`, `quase`, `cuidado`, `sem_dado`
   (onboarding vem só como contagem no `resumo`).
   A classe vem pronta: você pode acrescentar observações, sem mudar a classe.
2. Pergunte à CS, em uma linha, se ela já pediu depoimento ou indicação a algum cliente nos últimos meses (o ClickUp não
   guarda isso) e tire esses da sugestão.
3. Entregue, com os dados da saída, nesta ordem e sem alongar:
   - ✅ Saudáveis, agrupados por gestor: cliente · código · produto · satisfação · reunião mensal (campo `reuniao_mensal`,
     como veio) · sugestão. **Um pedido por cliente no mês:**
     - Muito Satisfeito (Promotor) ou Embaixador da Odontorise: depoimento em vídeo do dentista.
     - Satisfeito: indicação.
     - `candidato_select: true` (Start com Promotor ou Embaixador): só uma linha de observação "candidatos a Select",
       nunca pedido da CS, e só depois de o gestor confirmar o resultado.
     - Rede (campo `rede`): todas as unidades contam como um cliente só, com um pedido só, feito ao dono da rede.
   - 🟡 Quase: o que falta, pelo campo `motivos` (reunião atrasada, no show, rede com unidade em cuidado).
   - 🔴 Cuidado: nunca oferecer nada a quem está aqui. Destaque só, como observação:
     - Insatisfeito ou Crítico sem alerta aberto (`insatisfeito_sem_alerta`): cliente, gestor, liderança. Sugestão: vale
       conversar com o gestor ou a liderança sobre esse cliente.
     - O resto em uma linha cada: "N com alerta aberto" e "N neutros sem alerta (com o gestor)". Liste os nomes só se a CS pedir.
   - Onboarding e sem dado: uma linha com a contagem (sem satisfação registrada, o cliente não entra em sugestão de pedido).
4. Resultado de anúncio não está no ClickUp. Antes de qualquer pedido, a CS confirma com o gestor: uma mensagem por gestor
   (primeiro nome), com os clientes dele e a pergunta "o resultado está estável ou melhorando? posso pedir
   depoimento/indicação?". Se o `ultimo_registro_gestor` do cliente for "nenhum" ou tiver mais de 20 dias, pergunte também
   como está a conta.
5. Termine perguntando se ela quer os textos-modelo de depoimento e indicação para o cliente (para usar só depois do OK
   do gestor). Não escreva os textos antes de ela pedir.

## Regras
- Só leitura e só sugestão: a skill nunca pede para preencher campo, abrir ou completar alerta, mudar status ou
  reorganizar o ClickUp. Dado que falta no ClickUp é contornado (pergunta à CS), não vira tarefa.
- Depoimento de paciente exige termo assinado; depoimento do dentista não.
- Resposta enxuta: uma tabela curta por bloco, sem repetir campo vazio. Sem travessão. Nada é enviado pela skill.
