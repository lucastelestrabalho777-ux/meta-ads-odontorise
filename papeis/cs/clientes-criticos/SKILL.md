---
name: clientes-criticos
description: Visão geral e resumida, para a CS, dos clientes que estão na lista Clientes em Alerta do ClickUp: o problema de cada um, o que já foi feito, há quantos dias está parado e o que falta saber, com a pergunta pronta para quem está envolvido no cliente. Só lê o ClickUp e só sugere. Use quando a CS disser "clientes críticos", "clientes em alerta", "resumo dos alertas", "como estão os alertas", "o que está parado nos alertas" ou "/clientes-criticos".
---

# /clientes-criticos (CS)

Fonte: lista Clientes em Alerta do ClickUp, só leitura. Não usa conta de anúncio.

## Como responder
1. Rode `python3 ~/.claude/skills/meta-ads-odontorise/scripts/cs.py alertas` (no Windows, `python`). Leva uns 30 segundos.
   Cada item é um alerta com o cliente, o perfil (gestor, liderança, satisfação, reunião mensal), as ações dentro do
   alerta, os dois últimos comentários, o último registro do gestor e o campo `falta_saber`. O campo `voce` é quem está
   rodando a skill.
2. Resposta curta por padrão (cabe numa tela):
   - Uma linha de abertura: quantos clientes em alerta, quantos em churn, quantos parados há 5 dias ou mais fora do
     churn, e a contagem por motivo.
   - Uma linha por cliente fora do churn, do mais parado para o menos:
     **Cliente (código)** · motivo · parado há Y dias · a última coisa feita (quem, há quantos dias, em poucas palavras).
   - Churn: uma linha só com os nomes.
   - **Sugestões para hoje**, até 5 linhas, só com clientes fora do churn: os mais parados e os que têm `falta_saber`,
     cada um com a conversa sugerida e a pergunta curta pronta.
3. Detalhe de um cliente (problema, comentários, ações, contexto) só quando a CS pedir ("detalha o X").

## Com quem conversar
Na ordem: quem escreveu o último comentário, quem está com a ação dentro do alerta, o gestor do cliente, a liderança do
cliente. Nunca a própria pessoa que está usando a skill (campo `voce`). Se o comentário já explica o problema ou o
próximo passo, use o que está escrito e não pergunte de novo.

## Regras
- Só leitura e só sugestão: nunca pede para preencher campo, completar ou abrir alerta, mudar status ou reorganizar o
  ClickUp.
- Problema e causa só como estão escritos no motivo, na descrição ou nos comentários; não deduza.
- Cliente em churn não recebe pergunta nem sugestão.
- O resumo é interno: alerta, satisfação, descrição e comentário nunca vão para texto de cliente ou de grupo.
- Nível do alerta: mostre o número como está, sem interpretar.
- Sem travessão.
