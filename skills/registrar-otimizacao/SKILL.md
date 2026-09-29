---
name: registrar-otimizacao
description: Registra no ClickUp tudo o que foi feito na conta de anúncio de um cliente (otimização, mudança, problema de saldo): junta as ações do dia, escreve o registro no padrão da casa, comenta na tarefa rotineira certa da lista Ongoing, conclui a tarefa e segue a rotina. Use quando o gestor disser "registra a otimização", "registra o que fiz na conta X", "anota no ClickUp", "fechar a rotina do cliente X", "registra o problema de saldo" ou "/registrar-otimizacao".
---

# /registrar-otimizacao

Toda mexida em conta de anúncio precisa ficar registrada no ClickUp. A tarefa certa já existe na lista Ongoing,
uma por cliente e por rotina: **Acompanhamento de Resultado** (otimizações e mudanças) e **Monitoramento de Saldo**
(saldo e pagamento). Concluir a tarefa faz a recorrência trazê-la de volta com o próximo vencimento.

## Passos
1. Rode `scripts/registro.py preparar --cliente X --dias 1` (skill meta-ads-odontorise). Ele devolve as ações humanas
   do histórico da conta no período, o que a skill Meta subiu, os números de 7 dias (gasto, mensagens iniciadas, custo por
   mensagem) e as tarefas alvo com status e vencimento. Para saldo, use `--tipo saldo`.
2. Monte o texto do registro a partir de `texto_proposto`, completando com o gestor o que a API não sabe: o motivo da
   mexida e o próximo checkpoint. Padrão fixo: data · o que foi feito (itens) · motivo · números de 7 dias antes ·
   próximo checkpoint. Curto, sem jargão, sem travessão.
3. Mostre ao gestor o texto e a tarefa alvo (nome, status, vencimento). Só com OK explícito rode
   `scripts/registro.py gravar --task <id> --texto "<texto>" --concluir --confirmo`.
4. Confirme o resultado: comentário gravado e o próximo vencimento da tarefa. Se o gestor fez algo que não cabe na
   rotina (campanha nova, mudança de estratégia), ofereça criar a tarefa avulsa em Tarefas - Clientes com o tipo certo.

## Regras
- Nunca gravar sem OK. Uma tarefa por registro; saldo vai na tarefa de saldo, o resto na de acompanhamento.
- Não inventar ação: o registro traz só o que está no histórico da conta ou o que o gestor disse.
- Números sempre do período anterior à mexida, para o próximo checkpoint ter base de comparação.
