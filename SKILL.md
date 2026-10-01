---
name: meta-ads-odontorise
description: Opera as contas Meta Ads dos clientes da OdontoRise (clínicas odontológicas) com campanhas de conversão ao WhatsApp. Lê contas, campanhas, conjuntos, anúncios e criativos. Entrega métricas de mensagem: mensagens iniciadas, custo por mensagem iniciada, valor gasto, CTR, CPM, alcance, impressões e frequência, por período e comparando janelas. Busca cidades, bairros e públicos para segmentação. Cria campanhas, conjuntos e anúncios sempre pausados, seguindo os padrões de Lentes, Implantes e Harmonização facial. Use quando o gestor falar de campanha, conjunto, anúncio, criativo, público, segmentação, raio, custo por mensagem, conversas no WhatsApp, resultado da conta, gasto, CTR, CPM, lentes, implante, harmonização, subir criativo, pausar, duplicar ou orçamento. Também dispara com /meta-ads-odontorise setup.
---

# meta-ads-odontorise

Skill dos gestores de tráfego da OdontoRise para operar as contas Meta Ads dos clientes.
Todos os scripts ficam na pasta `scripts/` ao lado deste arquivo e são chamados via Bash:

```
python3 <pasta da skill>/scripts/<script>.py <subcomando> [argumentos]
```

No Windows, `python` no lugar de `python3`. Os scripts devolvem JSON no stdout; mensagens
para pessoas vão no stderr. Erro também vem em JSON, com o campo `hint` dizendo o que fazer.

## Estado desta versão (28/09/2026)

| Pronto e testado em conta real | Observação |
|---|---|
| `setup.py` conferência do ambiente | |
| `clientes.py` cadastro a partir do ClickUp | |
| `read.py` contas, campanhas, conjuntos, anúncios, criativos, prévia, histórico | 21 subcomandos |
| `insights.py` métricas, `resultado` e `comparar-janelas` | |
| `targeting.py` cidades, bairros, públicos, `auditar` conjunto | |
| `saude.py` saldo, reprovados, gasto sem mensagem, recência | |
| `create.py` subir campanha de captação via WhatsApp; `anuncio-drive` sobe vídeo ou imagem do Google Drive num conjunto que já existe | tudo pausado, com trava; a Página do cliente precisa de WhatsApp Business |
| `drive.py` lista pasta ou arquivo do Google Drive pelo link público | só leitura, sem baixar |
| `tarefas.py` tarefas e reuniões do ClickUp | |
| `transcrever.py` transcrição local de vídeo ou áudio | precisa do ambiente de transcrição |
| `registro.py` registro de otimização e roteiro no ClickUp (cria a tarefa em Tarefas - Clientes; saldo comenta a tarefa rotineira) | escreve no ClickUp só com --confirmo |
| `alertas.py` clientes em alerta (listar), status do projeto e abrir alerta | escreve no ClickUp só com --confirmo |
| `design.py` e `onboarding.py` acompanhamento do design e do onboarding | só leitura |

Ainda não existe: editar conjunto ou anúncio, duplicar, ativar por script. Quando o gestor pedir algo
que não existe, dizer isso com clareza e oferecer o que já existe. Nunca improvisar chamadas à API por fora dos scripts.

## Skills do pacote (pasta `skills/`, uma por papel)

| Papel | Skills |
|---|---|
| Gestor | /meu-dia · /legenda-video · /custo-por-mensagem · /dias-sem-otimizacao · /recarga-saldo · /feedback-sexta · /mensagem-grupo · /sugerir-roteiros · /registrar-otimizacao · /subir-criativos-drive |
| Head | /oportunidades-carteira · /revisao-gestor · /estrategia-conta · /resolver-conflito · /clientes-criticos · /acompanhar-design · /analise-onboarding |
| CS | /agendar-reuniao · /resumo-reuniao · /suporte-grupo · /clientes-saudaveis · /monitorar-grupo |

Cada uma tem o próprio SKILL.md com os dados que usa (sempre os scripts desta skill) e o formato da entrega.
O instalador (`instalar.sh` / `instalar.ps1`) liga todas em `~/.claude/skills/`.

## Onde ficam as coisas de cada pessoa (nunca dentro da skill)

| O quê | Onde |
|---|---|
| Credencial do Meta (app próprio, token de 60 dias) | `~/OdontoRise/credentials/meta-odontorise.env` |
| Token pessoal do ClickUp | `~/OdontoRise/credentials/clickup-odontorise.env` |
| Cadastro de clientes | `~/OdontoRise/meta-ads/contas-odontorise.json` |
| Aprendizados pessoais | `~/OdontoRise/meta-ads/aprendizados-local.md` |

Como criar cada credencial: Guia de IA OdontoRise, página Onboarding, passos 6 e 8.

## Setup (primeira vez e sempre que algo parar)

Rodar `scripts/setup.py` (ou `setup.py --json` para ler o resultado). Ele confere programas,
arquivo de credencial, validade do token, as nove permissões, conexão com a Meta e quantas
contas a pessoa enxerga, e lista o que falta com a parte do guia que resolve. Não altera nada.
Se o token estiver a 10 dias ou menos do vencimento, avisar o gestor antes de qualquer outra coisa.

## Cadastro de clientes (`scripts/clientes.py`)

O cadastro nasce do ClickUp (lista Perfil de Clientes) e fica no arquivo local do gestor.
Antes de qualquer operação em conta, resolver o cliente pelo cadastro: nome, código (#408),
slug ou id da task. Se o cliente não estiver cadastrado, cadastrar primeiro.

| Subcomando | O que faz |
|---|---|
| `buscar --nome X` | perfis do ClickUp cujo nome contém X |
| `meus [--gestor NOME]` | perfis em que o campo Gestor é o dono do token (ou o gestor indicado, para o head cadastrar a carteira), com marcação de quem já está no cadastro |
| `cadastrar --nome X [--task ID] [--account act_X]` | copia os campos operacionais do perfil para o cadastro local e sugere contas Meta candidatas |
| `definir-conta --cliente X --account act_X` | confirma a conta Meta do cliente (o gestor escolhe; a skill confere se ele enxerga a conta) |
| `listar` | cadastro local, com quantos ainda estão sem conta Meta |
| `remover --cliente X` | tira do cadastro local |

Regras do cadastro:
- Só campos operacionais saem do ClickUp: código, nome, status, fase, produto, cidade, estado,
  especialidade, Instagram, gestor, CS, liderança, Drive e Data Studio. Dados pessoais,
  financeiros e de contrato ficam no ClickUp.
- A conta Meta (act_) é sempre confirmada pelo gestor. Quando `cadastrar` sugerir candidatas,
  mostrar a lista e pedir a escolha; nunca assumir.
- Particularidade de um cliente (restrição de procedimento, pedido específico) vai para a
  memória do próprio gestor, não para o cadastro.

## Leitura da conta (`scripts/read.py`)

Tudo aceita `--account act_X` ou `--cliente <nome, #código ou slug>`. Listas vêm só com ACTIVE por padrão
(`--status ALL` para tudo). Orçamentos vêm em centavos e num campo irmão `_reais`.

| Subcomando | Uso |
|---|---|
| `accounts` | contas que a pessoa enxerga |
| `account-details --cliente X` | status, moeda, saldo, gasto, teto |
| `campaigns --cliente X [--status ALL]` · `campaign --id` | campanhas |
| `adsets --cliente X` · `adsets-by-campaign --campaign ID` · `adset --id` · `adsets-by-ids --ids a,b` | conjuntos com targeting |
| `ads --cliente X` · `ads-by-campaign --campaign ID` · `ads-by-adset --adset ID` · `ad --id` | anúncios com effective_status |
| `creative --id` · `creatives-by-ad --ad ID` · `preview --creative ID --format all` | criativo e prévia |
| `images` · `videos --cliente X` | biblioteca de mídia |
| `activities --cliente X --dias 30 --so-humanas` · `activities-by-adset --adset ID` | histórico de alterações (sem eventos automáticos da Meta) |
| `custom-audiences` · `lookalike-audiences --cliente X` | públicos |

## Resultados (`scripts/insights.py`)

| Subcomando | Uso |
|---|---|
| `resultado --cliente X [--level campaign\|adset\|ad] [--date-preset last_7d] [--limit 50]` | gasto, mensagens iniciadas, custo por mensagem, CTR, CPM, alcance, impressões, frequência, ordenado por gasto, com totais |
| `comparar-janelas --cliente X [--level ad] [--limit 50]` | 30, 14 e 7 dias lado a lado por objeto: obrigatório antes de propor qualquer pausa |
| `account --cliente X` · `campaign --id` · `adset --id` · `ad --id` | insights genéricos, padrão last_7d, `--raw` para a resposta crua |

Ao apresentar resultado, sempre dizer o período. Ao propor pausa, mostrar as três janelas do anúncio.

## Segmentação (`scripts/targeting.py`)

`geolocations --q "Cidade"` (chaves de cidade, bairro e região no Brasil), `interests --q`, `interest-suggestions --nomes`,
`behaviors`, `demographics`, `validate`, `reach`, `delivery` e `describe` (com `--spec`, `--spec-file` ou `--adset`),
e `auditar --adset ID`, que devolve os alertas da casa: raio acima do
máximo, público sem advantage_audience explícito. A Meta não devolve interesses para termos odontológicos:
segmentar por localização e público, não por interesse.

## Saúde da conta (`scripts/saude.py`)

`conta --cliente X` ou `todas` (todos os clientes do cadastro com conta). Quatro sinais com ok, atenção ou crítico:
saldo e pagamento (dias de saldo em conta pré-paga), anúncios reprovados ou com problema, gasto sem mensagem em
campanhas de mensagem nos últimos 7 dias (e custo por mensagem contra os 7 dias anteriores), e dias desde a última
alteração humana. É a base de "contas críticas", "dias sem otimização" e "recarga de saldo".

## Subir campanha (`scripts/create.py`)

Cria campanha, conjunto, criativo a partir de um post do Instagram e anúncio no padrão da casa
(`references/padroes-campanha.md`), tudo PAUSED. Sem `--confirmo` o script só mostra o que enviaria
(ensaio). O Claude:
1. Faz o diagnóstico do padrão (campanhas ativas, página, Instagram, mensagem de boas-vindas de um anúncio ativo).
2. Roda o ensaio e mostra ao gestor o que será criado, com o valor em reais.
3. Só depois do OK explícito repete com `--confirmo`.
4. Valida com `read.py ad`, `read.py preview --format all` e `targeting.py auditar`.
5. Nunca ativa. Ativar é o gestor, no Gerenciador ou por pedido explícito depois.
Guardas no código: conjunto novo sem posicionamento segue o que os conjuntos ativos da conta usam; recusa raio acima do maior raio que a conta já usa
(ou 10 km se a conta não usa raio); exige público explícito (advantage_audience 0 ou 1); recusa carrossel com mais de 10 cartões. Toda escrita fica em `~/OdontoRise/meta-ads/auditoria.jsonl`.
Subcomandos: `campanha`, `conjunto`, `criativo-post`, `anuncio`, `captacao` (fluxo completo) e `anuncio-drive`.
`anuncio-drive`: vídeo ou imagem do Google Drive vira anúncio PAUSED num conjunto que já existe (skill /subir-criativos-drive).
A Meta busca o vídeo direto no Drive pelo link, nada é baixado no computador; o link precisa estar como "Qualquer pessoa
com o link". Página, Instagram, botão, título, boas-vindas e UTMs vêm do anúncio ativo mais recente do conjunto.
Pré-requisito da conta do cliente: a Página precisa ter um WhatsApp Business conectado; com número pessoal a Meta recusa o conjunto.

## Tarefas do ClickUp (`scripts/tarefas.py`)

`minhas --dias 7` (atrasadas, hoje, próximas, sem data), `tarefa --id X` (descrição, subtarefas, comentários),
`reunioes --dias 14` (reuniões com clientes marcadas). Só leitura. É a base da skill /meu-dia.

## Registro no ClickUp (`scripts/registro.py`)

Otimização, anúncio novo e roteiro feitos para um cliente viram uma tarefa concluída em Tarefas - Clientes, ligada ao
cliente (skill /registrar-otimizacao). Sempre que o Claude escrever roteiro para um cliente, em qualquer conversa,
oferecer no fim: "Quer que eu registre no ClickUp que o roteiro foi feito?". Registrar só com OK.

## Regras da casa (valem em toda operação)

1. Nada é executado sem OK explícito do gestor, item por item. Apresentar sugestões numeradas.
2. Toda campanha, conjunto e anúncio nasce pausado. Ativar é decisão do gestor, depois de conferir.
3. Antes de pausar um anúncio, cruzar 30, 14 e 7 dias por anúncio. Nunca decidir por uma janela só.
4. Nunca ampliar raio de localização. Posicionamento segue o que a conta já usa: não incluir nem tirar Facebook sem entender o que está rodando.
5. Post do Instagram do cliente passa por análise antes de virar anúncio: paciente final sobe; mentoria, conteúdo pessoal ou sem sentido para captação não sobe, e o gestor é avisado.
6. Rosto de paciente em anúncio só com termo assinado pelo paciente.
7. Orçamento em centavos na API (5000 = R$ 50,00). Confirmar o valor com o gestor antes de enviar.
8. Ao mostrar resultado de conta, quebrar por campanha antes de atribuir gasto ou resultado a uma campanha.
9. Token, chave secreta e senha nunca aparecem em resposta, nota, memória ou print.
10. Textos sem travessão.

## Métricas que importam

Campanhas de conversão ao WhatsApp. As métricas são: mensagens iniciadas, custo por mensagem
iniciada, valor gasto, CTR, CPM, alcance, impressões e frequência. Sempre com o período
explícito (7, 14 ou 30 dias) e, quando o pedido for decidir algo, com as três janelas lado a lado.

## Aprendizados

Quando o gestor corrigir algo ("faltou o botão", "era outro público"), perguntar:
"Quer que eu registre isso nos aprendizados para não esquecer nas próximas vezes?"
Se sim, acrescentar em `~/OdontoRise/meta-ads/aprendizados-local.md` no formato:

```
### AAAA-MM-DD: título curto
Regra: o que fazer sempre ou nunca.
Contexto: o que aconteceu.
```

Ler esse arquivo antes de criar qualquer coisa. Não duplicar regra que já existe.

## Segurança

- Os scripts mascaram o token e limpam qualquer segredo das mensagens de erro.
- O arquivo de credencial precisa de permissão 600; o setup reprova se estiver aberto.
- Nenhum script escreve no ClickUp. A escrita no Meta ainda não existe nesta versão.
