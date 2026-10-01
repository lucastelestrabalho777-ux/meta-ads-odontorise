---
name: registrar-otimizacao
description: Registra no ClickUp o que foi feito para um cliente (otimização, mudança, anúncio novo, roteiro, campanha nova, problema de saldo): junta as ações do dia, escreve o registro no padrão da casa e cria a tarefa em Tarefas - Clientes ligada ao cliente, já concluída; saldo vai na tarefa rotineira de saldo da lista Ongoing. Use quando o gestor disser "registra a otimização", "registra o que fiz na conta X", "anota no ClickUp", "sobe essa demanda no ClickUp", "registra o roteiro", "registra o problema de saldo" ou "/registrar-otimizacao".
---

# /registrar-otimizacao

Toda mexida em conta de anúncio e todo roteiro feito para o cliente precisam ficar registrados no ClickUp. Cada registro
vira uma tarefa nova na lista **Tarefas - Clientes**, no padrão do time:

- Nome: tarefa, data e cliente com o código. Ex.: `Otimização 01/10/26 - DRA DANIELLE MOREIRA [#419]`.
  O nome do gestor não entra: ele já é o responsável e o cliente já fica relacionado.
- Tipo de Tarefa: otimização, anúncio novo e roteiro → **Otimização de Clientes**; campanha nova → **Subir Campanha**;
  problema na conta → **Resolução de Problemas**; mudança de estratégia → **Mudar Estratégia**; mudança de funil → **Mudar o Funil**.
- Origem "Gerada Manualmente", cliente relacionado, vencimento no dia, **só o gestor** como responsável.
- O registro vai em comentário e a tarefa fica concluída.

Saldo é diferente: a tarefa **Monitoramento de Saldo** da lista Ongoing é um lembrete recorrente para nenhuma campanha
sair do ar por falta de saldo. Problema de saldo é comentado nela e ela é concluída; a recorrência traz de volta.

## Passos
1. Rode `scripts/registro.py preparar --cliente X --dias 1 --tarefa "Otimização"` (skill meta-ads-odontorise). Ele devolve
   as ações humanas do histórico da conta no período, o que a skill Meta subiu, os números de 7 dias (gasto, mensagens
   iniciadas, custo por mensagem), a tarefa proposta e o texto proposto. Para saldo, use `--tipo saldo`: ele devolve a
   tarefa Monitoramento de Saldo do cliente. Para roteiro, pule este passo: o texto sai dos roteiros entregues.
2. Monte o texto do registro a partir de `texto_proposto`, completando com o gestor o que a API não sabe: o motivo da
   mexida e o próximo checkpoint. Padrão fixo: data · o que foi feito (itens) · motivo · números de 7 dias antes ·
   próximo checkpoint. Roteiro: quantos roteiros foram feitos e o tema e o gancho de cada um. Curto, sem jargão, sem travessão.
3. Mostre ao gestor o nome da tarefa, o tipo, o cliente e o texto. Só com OK explícito rode
   `scripts/registro.py registrar --cliente X --tarefa "Otimização" --tipo-tarefa "Otimização de Clientes" --texto "<texto>" --confirmo`.
   Saldo: `scripts/registro.py gravar --task <id> --texto "<texto>" --concluir --confirmo`.
4. Confirme o resultado com o link da tarefa criada. No saldo, confirme o comentário gravado e o próximo vencimento da tarefa.

## Regras
- Nunca gravar sem OK. Um registro, uma tarefa nova em Tarefas - Clientes; saldo só na tarefa de saldo.
- A tarefa "Acompanhamento de Resultado" da Ongoing saiu do processo: não comentar nem concluir nela.
- Não inventar ação: o registro traz só o que está no histórico da conta ou o que o gestor disse.
- Números sempre do período anterior à mexida, para o próximo checkpoint ter base de comparação.
