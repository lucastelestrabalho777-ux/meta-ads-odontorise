---
name: contas-criticas
description: Ranking das contas de anúncio dos clientes do gestor (ou de toda a carteira, para o head) por sinal de problema, com o número de cada sinal e a ação por conta: saldo acabando, anúncio reprovado, campanha gastando sem mensagem, criativo que gastou sem mensagem, custo por mensagem acima de R$35 ou subindo, e dias sem otimização. Use quando o gestor ou o head disser "contas críticas", "quais contas precisam de atenção", "o que está pegando nas minhas contas", "tem conta com problema", "raio-x das minhas contas", "como estão as contas hoje" ou "/contas-criticas". Alerta aberto no ClickUp é /clientes-criticos, não esta.
---

# /contas-criticas

Base: `scripts/saude.py todas` da skill meta-ads-odontorise (cinco sinais por conta, só leitura, cerca de 5 segundos por conta).
Alcance: só os clientes do cadastro local da pessoa (`clientes.py meus`), que são os clientes que ela cuida. O head vê a carteira
que cadastrou com `clientes.py meus --gestor NOME` e `cadastrar --carteira`. Conta fora do cadastro: o script recusa e o Claude não contorna.
Para aprofundar uma conta: `saude.py conta --cliente X`; `insights.py comparar-janelas --cliente X --level adset` diz qual
conjunto puxa o custo e `--level ad` qual anúncio. Atenção: `comparar-janelas` lê só anúncios ativos, então os totais
podem ficar abaixo dos do `saude.py`, que soma a conta inteira. Total da conta é o do `saude.py`; decisão por anúncio é
com as três janelas.

## Os cinco sinais

| Sinal (chave no JSON) | 🟠 atenção | 🔴 crítico |
|---|---|---|
| Saldo e pagamento (`saldo_pagamento`) | pré-paga com menos de 5 dias de saldo | menos de 2 dias, saldo zerado, conta desativada ou cobrança pendente |
| Anúncios (`anuncios_problema`) | anúncio com problema em campanha ativa | anúncio reprovado em campanha ativa (reprovado em campanha pausada não afeta a entrega e fica ✅ com nota) |
| Gasto sem resultado (`gasto_sem_resultado`) | custo por mensagem subiu 30% ou mais contra os 7 dias anteriores; conta sem gasto | campanha ativa gastou R$150 ou mais em 7 dias sem mensagem; custo por mensagem de R$35 ou mais; custo subiu 60% ou mais |
| Criativos (`criativos_sem_resultado`) | anúncio ativo gastou R$50 ou mais em 7 dias sem mensagem | R$100 ou mais em 7 dias sem mensagem |
| Recência (`recencia`) | 7 a 10 dias sem alteração humana na conta | mais de 10 dias sem alteração humana |

## Como responder

1. Rode `saude.py todas`. Mais de 15 contas: avise que leva mais de um minuto ou rode em partes com `--limite-contas`.
2. Ranking da pior para a melhor: `resumo.status`, depois a quantidade de sinais críticos, depois a ordem de urgência dos
   sinais (saldo, anúncios, criativos, gasto, recência: conta parada ou parando por saldo vem antes de tudo). Três blocos:
   🔴 crítico, 🟠 atenção, ✅ ok (só o nome). Conta com `ok: false` vai num bloco ⚠️ no fim, com o `erro` e a `acao`.
3. Para cada conta 🔴 ou 🟠, um bloco com cliente, conta (`act_id`) e uma linha por sinal disparado, com o número real:
   - saldo: saldo restante, gasto médio por dia e dias de saldo (`dias_de_saldo` não vem quando o saldo está zerado: dizer que a conta parou);
   - anúncios: quantos reprovados em campanha ativa, em qual campanha e o motivo (`anuncios[].motivo`; quando vier vazio, dizer que a Meta não informou e que o motivo está no anúncio, no Gerenciador);
   - gasto: campanha, gasto em 7 dias e zero mensagem; ou custo por mensagem atual, o anterior, a variação e as campanhas acima de R$35 (`campanhas_acima_do_teto`);
   - criativos: nome do anúncio, conjunto, gasto em 7 dias sem mensagem e o que ele fez nos 7 dias anteriores;
   - recência: dias sem alteração, quem fez a última e o que foi.
   Sinal ✅ da conta não aparece no bloco.
4. Depois dos sinais, ações numeradas para a conta, uma por sinal 🔴 ou 🟠, começando pelo dominante. Dominante é o primeiro
   que disparou nesta ordem: saldo, anúncio reprovado em campanha ativa, criativo sem mensagem, campanha sem mensagem ou custo
   acima de R$35, custo subindo, recência.
   - saldo: valor da recarga (gasto médio por dia vezes 15, arredondado para cima em múltiplos de R$50, dizendo quantos dias cobre)
     e a mensagem para o grupo, curta: saldo atual, quando acaba, valor sugerido, como recarregar (PIX no Gerenciador de Anúncios,
     Configurações de pagamento, Adicionar fundos). É o mesmo texto de /recarga-saldo; o envio é do gestor;
   - reprovado em campanha ativa: ler o motivo e propor o ajuste ou a troca do criativo. Sem motivo: abrir o anúncio no Gerenciador;
   - campanha sem mensagem ou custo acima de R$35: dizer qual conjunto e qual anúncio puxam o custo (`comparar-janelas --level adset`
     e `--level ad`) e propor criativo novo, público, verba ou pausa. Nunca "observar";
   - criativo sem mensagem: candidato a pausa só com as três janelas (`comparar-janelas --level ad`). Anúncio com mensagem em
     30 dias a custo abaixo de R$35 não sai por 7 dias ruins. Zero mensagem em 14 e 7 dias, ou custo acima de R$35 nas três
     janelas, é candidato; a decisão é do gestor;
   - recência: dizer o que foi feito pela última vez e propor a otimização de hoje (criativo, público ou verba).
5. Head: agrupar os blocos por gestor (campo `gestor` do cadastro, uma lista de nomes, em `clientes.py listar`) e fechar com o
   pedido para cada gestor.
6. Fechar com 💰 em duas linhas: (a) soma em reais do gasto em 7 dias das campanhas e dos anúncios sem mensagem; (b) quantas contas
   param por saldo em menos de 2 dias, com o gasto médio por dia de cada uma. Perguntar por qual conta começar, sugerindo a ordem.

## Regras
- Só leitura. Nada é pausado, ativado ou editado por esta skill; cada ação só com OK explícito, item por item.
- Antes de propor pausa de anúncio, cruzar 30, 14 e 7 dias por anúncio.
- Métrica é mensagem iniciada. Campanha de tráfego, alcance ou formulário não entra em "gastou sem mensagem".
- Cliente que a pessoa cuida e não está no cadastro: sugerir "cadastra o cliente X". Cliente de outro gestor: não ler, não cadastrar.
- Sem travessão.
