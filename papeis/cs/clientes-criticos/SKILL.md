---
name: clientes-criticos
description: Visão geral e resumida, para a CS, dos clientes que estão na lista Clientes em Alerta do ClickUp: o problema de cada um, o que já foi feito, com quem está, há quantos dias está parado e o que falta saber, com a pergunta pronta para quem está envolvido no cliente. Só lê o ClickUp e só sugere. Use quando a CS disser "clientes críticos", "clientes em alerta", "resumo dos alertas", "como estão os alertas", "o que está parado nos alertas" ou "/clientes-criticos".
---

# /clientes-criticos (CS)

Fonte: lista Clientes em Alerta do ClickUp, só leitura. Não usa conta de anúncio.

## Como responder
1. Rode `python3 ~/.claude/skills/meta-ads-odontorise/scripts/cs.py alertas` (no Windows, `python`). Leva uns 20 segundos.
   Cada item é um alerta com o cliente, o perfil (gestor, liderança, satisfação, reunião mensal), as ações dentro do
   alerta, os dois últimos comentários, o último registro do gestor e o campo `falta_saber`.
2. Abra com uma linha: quantos clientes em alerta, quantos parados há 5 dias ou mais e quantos por motivo e por status.
3. Um bloco curto por cliente, do mais parado para o menos (status `churn` por último, só uma linha cada):
   - **Cliente (código)** · gestor · liderança · motivo · status · aberto há X dias, parado há Y
   - Problema: 1 ou 2 linhas, pelo motivo, pela descrição e pelos comentários. Só o que está escrito; não deduza causa.
   - O que já foi feito: o último comentário (quem e há quantos dias) e as ações do alerta com status.
   - Contexto: satisfação, reunião mensal, último registro do gestor, conteúdo atrasado (só se houver).
   - Falta saber: quando `falta_saber` vier preenchido, sugira com quem conversar (quem está no alerta, o gestor ou a
     liderança do cliente) e escreva a pergunta curta pronta para mandar.
4. Feche com "Sugestões para hoje", até 5 linhas: os clientes mais parados e a conversa sugerida para cada um.

## Regras
- Só leitura e só sugestão: nunca pede para preencher campo, completar ou abrir alerta, mudar status ou reorganizar o
  ClickUp.
- O resumo é interno: alerta, satisfação, descrição e comentário nunca vão para texto de cliente ou de grupo.
- Nível do alerta: mostre o número como está, sem interpretar.
- Sem travessão.
