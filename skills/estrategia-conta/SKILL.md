---
name: estrategia-conta
description: Monta a proposta de estratégia para a conta de um cliente a partir do procedimento, da cidade, da verba e do resultado atual: estrutura de campanhas, públicos, criativos, verba por conjunto e metas de custo por mensagem. Use quando o head ou o gestor disser "estratégia para a conta X", "como estruturar a conta do cliente", "plano para o cliente novo", "reestruturar a conta" ou "/estrategia-conta".
---

# /estrategia-conta

## Dados
1. Cadastro local: procedimento (especialidade principal e secundária), cidade, estado, produto, satisfação.
2. Conta atual: `read.py campaigns --cliente X --status ALL`, `read.py adsets-by-campaign`, `insights.py resultado --cliente X --date-preset last_30d --level campaign`
   e `insights.py comparar-janelas`. Conta nova sem histórico: dizer isso e partir do playbook.
3. `references/padroes-campanha.md` (padrão Captação via WhatsApp e a variação do procedimento) e `references/regras-da-casa.md`.
4. Segmentação: `targeting.py geolocations --q "<cidade>"` para as chaves de cidade e bairros; `targeting.py auditar --adset` nos conjuntos atuais.

## Entrega (uma página, para o gestor executar)
- Diagnóstico em 5 linhas: o que a conta tem hoje, custo por mensagem atual e tendência.
- Estrutura proposta: campanhas e conjuntos (1 conjunto = 1 criativo x 1 público), verba diária por conjunto e total,
  públicos (localização, público quente, semelhante quando houver base), só Instagram.
- Criativos: quantos e quais ângulos, a partir da variação do procedimento; o que pedir ao cliente gravar.
- Mensagem de boas-vindas do WhatsApp com a pergunta de qualificação do procedimento.
- Metas: custo por mensagem alvo para 30 dias, com base no histórico da conta (ou do playbook se não houver).
- Checkpoints: o que olhar em 7 e em 14 dias, e o critério para pausar (três janelas).

## Regras
- Nunca ampliar raio nem incluir Facebook. Tudo nasce pausado. Verba é a combinada com o cliente, não uma sugestão de aumento sem OK.
- Sem travessão. A skill propõe; quem executa é o gestor, item por item.
