---
name: dias-sem-otimizacao
description: Lista os clientes do gestor por dias desde a última alteração humana na conta de anúncio (edição, criativo novo, pausa, verba), para achar conta parada. Use quando o gestor disser "quais contas estão paradas", "há quantos dias não mexo na conta X", "dias sem otimização", "contas sem mexer" ou "/dias-sem-otimizacao".
---

# /dias-sem-otimizacao

Base: `scripts/saude.py todas` da skill meta-ads-odontorise, sinal `recencia` (dias desde a última alteração
feita por uma pessoa no histórico da conta; eventos automáticos da Meta não contam).
Para uma conta: `scripts/read.py activities --cliente X --dias 45 --so-humanas --limit 10` mostra as últimas mexidas.

## Como responder
1. Rode `saude.py todas` e leia `recencia.dias_sem_alteracao` e `recencia.ultima_alteracao` de cada conta.
2. Tabela ordenada da conta mais parada para a mais recente: cliente · dias sem alteração · última ação (o que foi e quem fez).
   🔴 mais de 10 dias · 🟠 7 a 10 · ✅ menos de 7.
3. Para cada conta 🔴 ou 🟠, uma sugestão concreta do que fazer hoje, cruzando com o custo por mensagem
   (`gasto_sem_resultado`): custo subindo e conta parada é prioridade máxima. Sugerir criativo, público, verba ou pausa,
   nunca "acompanhar".
4. Perguntar por qual conta começar. Executar só com OK, item por item.

## Regras
- Alteração feita por automação ou pela Meta não conta como otimização.
- Sem travessão.
