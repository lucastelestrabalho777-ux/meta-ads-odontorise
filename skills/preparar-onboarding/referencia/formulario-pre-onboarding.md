# Formulário de Pré-Onboarding: como ler cada campo

Lista `Pré-Onboarding | Respostas do Cliente` (`901716898751`). Uma tarefa por cliente, criada pelo ClickBot quando o cliente responde,
ligada ao perfil pelo campo "Formulário | Pré onboarding". Status `em analise - head` = caiu para o Head ler antes da reunião.
Os campos começam com "PO - ". `dossie.py cliente` já devolve tudo agrupado nos blocos abaixo (mesma ordem da reunião).

| Bloco da reunião | Campos PO | Como ler |
|---|---|---|
| 4.1/4.2 História e momento | Faturamento mensal atual · Variação de faturamento (12 meses) · Evolução nos últimos 12 meses · Meta de faturamento (6 meses) · Meta de novos pacientes por mês · Resultado esperado com a OdontoRise · Principal desafio para crescer · Existe sazonalidade · Detalhes da sazonalidade | Meta menos atual, dividido pelo ticket, dá quantos pacientes novos por mês o projeto precisa entregar. "Variação" costuma vir como texto solto ("300k"): confirmar se é faturamento anual ou oscilação. |
| 4.2 Estrutura e capacidade | Locais de atendimento · Quantidade de locais · Endereço do local principal · Dentistas no local · Cadeiras · Capacidade para novos pacientes · Dias e horários · Principal decisor · Responsável Técnico e CRO | Capacidade declarada x cadeiras x dentistas: 2 cadeiras com "bastante capacidade" pede número de pacientes por semana. Decisor diferente de quem aparece no vídeo muda quem aprova criativo. |
| 4.3 Tratamento e oferta | Tratamento prioritário · Motivo da prioridade · Ticket médio · Formas de pagamento oferecidas · Condições de pagamento mais usadas · Tempo até o fechamento · Tratamentos ou perfis a evitar | Ticket e verba definem o teto de custo por paciente. "Tratamentos a evitar" vira regra de criativo e de qualificação no WhatsApp. |
| 4.4 Paciente, região, posicionamento | Perfil do paciente desejado · Dores e desejos · Objeções mais comuns · Objeção (outro) · Regiões dos melhores pacientes · Distância de deslocamento · Diferencial percebido · Referências de comunicação admiradas | Região e distância definem o recorte geográfico: a regra da casa é nunca ampliar raio, então o recorte nasce na reunião. Referências admiradas = @ para o Raio-X e para o direcionamento criativo. |
| 4.5 Marketing e histórico | Canais de chegada dos pacientes · Já investiu em tráfego · Plataformas já anunciadas · Experiência com tráfego · Investimento anterior · Leads por mês (histórico) · Leads que viraram pacientes (histórico) · Faturamento gerado pelas campanhas · Investimento mensal em mídia neste projeto · Instagram principal · Clínica possui site · Endereço do site · Possui domínio · Domínio · Pessoa que aparece nos vídeos · Restrições para gravar · Responsável por aprovar criativos | Experiência "péssima" exige a pergunta "o que exatamente aconteceu". Histórico de leads x pacientes mostra se o problema era mídia ou atendimento. Sem site = destino WhatsApp. Restrições de gravação mudam o formato dos criativos. |
| 4.6 Comercial e jornada do lead | Responsável por atender os leads · Dedicação do responsável comercial · Canais de atendimento · Tentativas de contato antes de desistir · Rotina de follow-up · Utiliza CRM · Qual CRM · Indicadores acompanhados · Conhece a taxa de conversão · Conversão a cada 10 leads | "Minha CRM" como responsável = confusão entre ferramenta e pessoa: perguntar nome e função. CRM sem nome e sem preenchimento inviabiliza a análise do funil (Select). Follow-up "sem rotina definida" é gargalo comercial, não de mídia. |
| Outros | Informações adicionais | |

## Unidades e armadilhas

- Campos de moeda chegam como número puro. Valor abaixo de 1000 quase sempre está em milhares (3 = R$ 3.000; 5 = R$ 5.000). O script marca
  `confirmar: true` nesses casos. Confirmar na reunião sem fazer o cliente repetir tudo: "o investimento de R$ 3 mil por mês que você colocou...".
- Dropdowns como "Qual CRM utilizam" às vezes vêm com "Sim": o cliente não entendeu a pergunta.
- "Locais de atendimento: mais de um endereço" com "Quantidade: 1" é contradição: define onde anunciar.
- Campo vazio não é "não": é pergunta para a reunião, mas só se pesar na estratégia.

## O que o formulário não traz (e a reunião precisa cobrir)

Capacidade real em pacientes por semana · como o tratamento é vendido (avaliação, orçamento, parcelamento) · o que faz fechar e desistir ·
por que o paciente escolheria esta clínica · o que deu errado no tráfego anterior · tempo de resposta real ao lead · acessos e BM ·
disponibilidade de agenda para gravar · quem é a referência técnica do dia a dia na clínica.
