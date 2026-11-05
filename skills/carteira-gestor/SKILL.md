---
name: carteira-gestor
description: Tabela da carteira de cada gestor (para o head) ou dos próprios clientes (para o gestor), cruzando a ficha do ClickUp (quando entrou, produto e ticket, satisfação) com o resultado da conta Meta em 7 dias, e marcando quem é recente (até 30 dias), bom, melhor e quem tem problema (saldo, custo acima de R$35, conta parada, reprovado). Use quando o head ou o gestor disser "carteira do Naoki", "tabela dos clientes de cada gestor", "quem são os bons clientes", "quais clientes entraram esse mês", "melhores clientes de cada um", "clientes por gestor", "como está a carteira" ou "/carteira-gestor". Só os sinais da conta, sem ficha, é /contas-criticas; candidato a depoimento é /clientes-saudaveis.
---

# /carteira-gestor

Base: `scripts/carteira.py analisar` da skill meta-ads-odontorise. Lê a lista Perfil de Clientes do ClickUp (campo
Gestor define a carteira), pega a conta Meta de cada cliente no cadastro local (`clientes.py`, o mesmo das outras
skills) e roda os cinco sinais do `saude.py` em até 4 contas ao mesmo tempo (cerca de 5 segundos por conta). Só leitura.

Escopo: `--gestor NOME` (repetir para mais de um) é do head; sem argumento, lê os clientes do dono do token do ClickUp.
`--todos` é a carteira inteira. `--so-ficha` mostra só o ClickUp, sem ler conta. `tabela` reimprime a última análise
salva em `~/OdontoRise/meta-ads/carteira/` (sem ticket; dado de contrato não fica em arquivo).

## O que entra em cada linha

| Coluna | De onde vem |
|---|---|
| # e Cliente | Código do Cliente e nome do perfil, sem "Dr/Dra" |
| Produto · ticket | Produto (Start, Select) e Valor Recorrente Mensal; "sem ticket" quando a ficha está vazia |
| Entrou | Data de Fechamento; sem ela, Data do Primeiro pagamento, Data de Entrada e por fim a criação do perfil ("Data de Entrada" quase sempre está vazia) |
| Satisfação | Status do Projeto, encurtado: Crítico, Alerta, Neutro, Satisfeito, Promotor |
| 7d: msgs · custo | mensagens iniciadas e custo por mensagem da conta inteira nos últimos 7 dias (`conta_7d` do saude.py) |
| Situação | marcador de resultado mais os sinais que dispararam, do mais urgente ao menos: saldo, anúncios, gasto, criativos, recência |

## Classificação

| Marcador | Regra |
|---|---|
| 🆕 recente | entrou há 30 dias ou menos |
| ✅ bom | teve mensagem em 7 dias a menos de R$35 cada |
| ⭐ melhor | 20 mensagens ou mais em 7 dias a menos de R$30 cada, e ficha que não é Insatisfeito nem Crítico. Ordenar por mensagens |
| 🔴 crítico | qualquer sinal crítico do saude.py: saldo zerado ou menos de 2 dias, conta UNSETTLED ou desativada, reprovado em campanha ativa, campanha de R$150+ sem mensagem, custo de R$35 ou mais, anúncio de R$100+ sem mensagem, mais de 10 dias sem alteração humana. Também 0 campanhas ativas |
| 🟡 atenção | sinal de atenção: saldo abaixo de 5 dias, custo subindo 30%+, anúncio de R$50+ sem mensagem, 7 a 10 dias sem mexer, tráfego ou outro objetivo gastando R$50+ sem mensagem |
| ⚠️ sem leitura | a credencial não enxerga a conta (#200): conta em BM do cliente sem o system user da OdontoRise, ou token sem a permissão |
| 📋 sem cadastro | o cliente está no ClickUp com esse gestor, mas não no cadastro local: a conta não é lida |

Um cliente pode carregar mais de um marcador: ⭐ com 🔴 25 dias parada é um bom resultado que ninguém está cuidando.
A ficha pesa só no ⭐ (Crítico na ficha nunca vira melhor); o resto é número da conta.

## Como responder

1. Rode `carteira.py analisar --gestor NOME` (um `--gestor` por pessoa). Mais de 15 contas leva mais de um minuto; avise.
   As tabelas saem prontas no stderr, em markdown; o JSON do stdout tem o detalhe de cada linha (`gestores[].clientes[]`).
2. Entregue uma tabela por gestor, na ordem de entrada (mais novo em cima), com a legenda em uma linha. Depois da tabela,
   quatro linhas: 🆕 recentes, ✅ bons, ⭐ melhores (com mensagens e custo), 🔴 com problema (quantos e quem).
3. Feche com os alertas de relacionamento que o script aponta (`alertas_relacionamento`): quem está Crítico na ficha com a
   conta bem (o problema não é tráfego), quem está Crítico na ficha e na conta (prioridade) e quem é Promotor com a conta
   parada (risco de perder quem indica).
4. Pendências, uma linha cada: clientes sem cadastro local (o head cadastra com `clientes.py cadastrar --nome X --carteira`
   e confirma a conta com `definir-conta`; conta nunca é assumida) e contas sem leitura (pedir ao cliente que atribua a
   conta ao system user da OdontoRise na BM dele; até lá a linha fica sem número).
5. Termine com 💰 (gasto em 7 dias sem mensagem e contas parando por saldo) e a pergunta: qual cliente aprofundar.
   Aprofundar é /contas-criticas na conta (`saude.py conta --cliente X`, `insights.py comparar-janelas`).

## Regras

- Só leitura. Nada é pausado, ativado ou editado por esta skill; cada ação depois dela exige OK explícito, item por item.
- Ticket e dado de contrato aparecem na tabela para o head e nunca vão para mensagem de grupo, nota ou memória.
- Cliente de outro gestor só entra pelo head (`--gestor`). Gestor roda sem argumento e vê só os seus.
- Cliente que mudou de gestor no ClickUp aparece na carteira nova; o cadastro local pode estar desatualizado, avisar.
- Sem travessão.
