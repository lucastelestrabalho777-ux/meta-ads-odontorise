---
name: preparar-onboarding
description: Prepara o Head da OdontoRise para a Reunião de Onboarding de um cliente novo. Lê no ClickUp o perfil, o Formulário de Pré-Onboarding, o Relatório Comercial, o andamento do onboarding e a reunião marcada, e entrega o dossiê com a leitura do cliente, o que confirmar, os temas, as perguntas por bloco e como conduzir. Use quando o head disser "tenho onboarding com X às 17h", "prepara a reunião de onboarding do X", "o que o cliente X preencheu", "dossiê do cliente novo", "me prepara para o onboarding", "briefing do onboarding", "quais onboardings tenho essa semana" ou "/preparar-onboarding".
---

# /preparar-onboarding

Pré-requisito: token do ClickUp em `~/OdontoRise/credentials/clickup-odontorise.env` (Guia de IA OdontoRise, página Onboarding, passo 8).
Fonte: `scripts/dossie.py` da skill meta-ads-odontorise, só leitura. Regras da casa: `references/regras-da-casa.md` da mesma skill.
Opcionais: conector do Google Drive no claude.ai (pasta do cliente) e conector do Google Calendar (horários para o Planejamento).
Conhecimento da reunião: `referencia/reuniao-onboarding.md` (etapas, blocos 4.1 a 4.8, postura, registro) e
`referencia/formulario-pre-onboarding.md` (como ler cada campo "PO - ..."). Ler os dois antes de montar a entrega.

## Passos

1. **Cliente.** Se o head não nomeou, rode `dossie.py proximas --dias 7` e mostre as reuniões de onboarding marcadas (hoje primeiro).
   Com o nome, #código ou id do perfil: `dossie.py cliente --cliente "<valor>"`. Ler o JSON inteiro.
   No JSON: `perfil.closer` é o campo Comercial do ClickUp; `reunioes[].link` costuma ser o evento do Calendly, que abre o Meet
   (`link_tipo` diz); `reunioes[].aviso_duracao` aparece quando o slot é menor que os 50 minutos do Playbook;
   `onboarding.proximas_depois_da_reuniao` já exclui a própria reunião que está sendo preparada.
2. **Relatório Comercial.** Costuma chegar como PDF colado num comentário do perfil ou da tarefa-mãe do onboarding
   ("Relatorio_Onboarding_<cliente>.pdf"); o JSON já traz isso em `anexos` (campo `em` diz onde). Baixar e ler:
   `dossie.py anexo --url "<url>" --pasta <scratchpad da sessão>` (PDF ganha um .txt ao lado; sem extrator, ler o PDF pela
   ferramenta de leitura de arquivos). O relatório é a fonte mais rica: o que o Closer apresentou e o que o cliente fechou
   (Start ou Select), números ditos na call, quem decide, o que ficou combinado, alertas para a equipe, tom recomendado.
   Se `faltando` acusar que não está no ClickUp e o conector do Drive estiver ligado: buscar
   `parentId = '<id da pasta em perfil.drive>'`, escolher a subpasta cujo título começa com "1. Documentos" (o nome traz o cliente
   no fim), listar por `parentId` dela; vazia, olhar também a que começa com "3. Evidências". Achou: ler e usar no item 3 da entrega
   (cruzar faturamento, meta, verba e promessas feitas com o formulário) e no 4.7 (o que foi vendido). Pasta vazia ou sem conector:
   uma linha dizendo que o Closer ainda não anexou e seguir; no 4.7, confirmar com o cliente o que foi combinado na venda.
3. **Roteiro da casa.** `onboarding.etapas[]` traz `descricao` e `checklist` da subtarefa "Reunião de onboarding" (os objetivos da
   reunião, a instrução de pontuar conflitos de informação para o cliente, coletar referências visuais e já agendar a próxima reunião,
   que o ClickUp chama de "debriefing" e o Playbook de "Reunião de Planejamento") e das próximas etapas pendentes (ex.: checklist de
   "Configuração de contas": saldo, Instagram, Página, WhatsApp). Usar no bloco 4.7 e no fechamento; não reescrever o que já está lá.
4. **Instagram.** Abrir a URL de `perfil.instagram` com busca na web. Mínimo aceitável: bio, seguidores, destaques e o que os
   thumbnails mostram. Três observações no máximo (fala com paciente final ou com dentista, aparece em câmera ou só close de dente,
   cidade na bio). Legendas e posts recentes ficam para o head olhar na hora; dizer isso se não vierem.
5. **Referências citadas.** "Referências de comunicação admiradas" são perfis que o cliente admira, não concorrentes. Entram na
   entrega como lista para o Raio-X do Planejamento, com os @ como vieram; não pesquisar agora. Concorrente citado só aparece se o
   Relatório Comercial trouxer.
6. **Planejamento.** Se o conector do Google Calendar estiver ligado, listar dois ou três horários livres do head nos 3 dias úteis
   seguintes à reunião, para ele já entrar com a proposta. Sem conector, pular.
7. **Entrega**, no formato abaixo.

## Entrega: para o head ler em dez minutos antes da chamada

Ordem fixa. Tudo com o dado real do JSON; dado ambíguo vem marcado **(confirmar)**. Números em moeda abaixo de 1000 são lidos como
milhares e marcados. O JSON inteiro não é transcrito: resume e aponta.

1. **Cabeçalho.** Cliente, #código, produto, tratamento prioritário, cidade/UF. Reunião: data, hora, duração (com o aviso se for menor
   que 50 min), link. Time: Head, Gestor, CS, Closer. Onboarding: etapas feitas de total e as duas próximas depois da reunião, com o setor dono.
   Relatório Comercial: onde está ou que não está.
2. **O cliente em seis linhas.** Momento e meta · tratamento e ticket · paciente e região · histórico de marketing · comercial e
   atendimento · estrutura. É o que o cliente escreveu, citado como dele.
3. **🔴 Confirmar na reunião.** No máximo oito itens principais, cada um com a pergunta pronta usando o número dele
   ("os R$ 3 mil por mês que você colocou..."). Fonte: `alertas_automaticos`, `vazios`, `faltando` e o cruzamento com o Relatório
   Comercial. Os demais itens entram em uma linha cada, como "também vale confirmar".
4. **🎯 Leitura do Head.** Três a cinco hipóteses, marcadas como hipótese: onde está o gargalo (mídia, atendimento, oferta, capacidade),
   alavanca inicial, expectativa a ajustar, sinais da seção 7 da referência presentes neste cliente. Conta de números: pacientes novos
   por mês que a meta de faturamento exige e a meta de pacientes declarada (quando as duas bases divergem, isso é item do bloco 3),
   teto implícito por paciente fechado, conversão histórica.
5. **🗣️ Roteiro por bloco (4.1 a 4.8).** Nos blocos 4.1 a 4.6: uma linha do que o formulário já responde (não perguntar) e duas a três
   perguntas específicas deste cliente, cada uma marcada **[confirmar]** ou **[aprofundar]**, com as perguntas-modelo do Playbook
   adaptadas aos dados dele. No 4.7 (não tem campo no formulário): o que explicar do funcionamento, time e papel de cada um,
   entregas do produto contratado, comunicação, responsabilidades do cliente, cronograma, o que será pedido. No 4.8: o resumo a validar.
6. **📌 Fechar a reunião com.** Pendências a pedir (acessos à BM e conta, Página com WhatsApp Business, forma de pagamento, agenda de
   gravação, materiais com termo de consentimento) e **a Reunião de Planejamento agendada ainda na chamada**, até 3 dias, com os
   horários do passo 6 quando houver.
7. **✅ Antes de entrar.** Seis itens: câmera, luz e áudio; fundo oficial fora do escritório; Gestor alinhado sobre os pontos de
   atenção; Instagram visto; referências citadas conferidas por alto; gravação do tl;dv ligada.

Depois da reunião, oferecer em uma linha: `/resumo-reuniao` para a ata e `/raio-x-concorrentes` para o Planejamento. Só com OK.

## Regras

- Só leitura. Nada é escrito no ClickUp, no Drive, no Calendar ou na conta de anúncio.
- Dados pessoais (CPF, CNPJ, telefone, e-mail, endereço, data de nascimento) e valores de contrato não entram na entrega. O script já
  não os devolve; não buscar. CRO entra: é dado profissional público e obrigatório no anúncio.
- Dado e interpretação separados: o que o cliente escreveu é citado como dele; hipótese é marcada como hipótese.
- Recorte geográfico é decisão da reunião. Nunca propor ampliar raio nem incluir Facebook por padrão.
- Sem travessão. Números reais, nunca placeholder.
- Cliente de outro gestor: o head lê a carteira inteira. Gestor usando esta skill lê só os próprios clientes (regra 14 da casa).

## Erros comuns

| Erro | Como evitar |
|---|---|
| Perguntar na reunião o que o formulário já responde | Só o ambíguo vira [confirmar]; o claro vira ponto de partida da pergunta seguinte |
| Ler "3" como R$ 3 | `confirmar: true` nos campos de moeda: ler como milhares e confirmar na chamada |
| Concluir "lead ruim" pelo histórico de 10 leads e 1 paciente | Investigar tempo de resposta, abordagem e follow-up (bloco 4.6) antes |
| Aceitar o faturamento do formulário sem cruzar | Perfil (faixa do comercial) e "Variação 12 meses" dividida por 12 são os contrapesos; o script alerta |
| Entregar sem o bloco de fechamento | Sem Reunião de Planejamento agendada, o onboarding não conclui |
| Sugerir raio de 100 km porque os pacientes vêm de longe | Levar o recorte como pergunta por cidade; a regra é nunca ampliar raio |
| Tratar "Referências admiradas" como concorrentes | São perfis admirados; concorrente vem do Relatório Comercial ou do Raio-X |
| Dossiê sem reunião encontrada | Conferir com `dossie.py proximas`; o CS pode não ter ligado a reunião ao perfil |
| Expor telefone, e-mail, CPF ou valor do contrato na entrega | O script não devolve; se vier de PDF ou comentário, não copiar para a entrega |
| Montar o dossiê à mão com dezenas de GETs ou pelo MCP do ClickUp | O MCP devolve "Team not authorized" neste workspace; `dossie.py cliente` faz tudo em um comando |
| Ignorar o relatório porque `attachments` da tarefa veio vazio | Anexo colado em comentário só aparece em `anexos` com `em: comentário (...)`; conferir ali |
| Levar o Playbook e esquecer o roteiro da subtarefa | A subtarefa "Reunião de onboarding" tem os objetivos e o "pontuar conflitos"; os dois valem juntos |
