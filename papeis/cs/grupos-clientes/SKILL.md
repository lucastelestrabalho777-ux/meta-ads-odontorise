---
name: grupos-clientes
description: Leitura, para a CS, dos grupos de WhatsApp dos clientes ativos em um comando só: quem está esperando resposta há mais de 40 minutos úteis, o que o grupo mostra dos clientes em alerta, clientes com atrito ou reclamação e clientes sem engajamento, cada um com a ação sugerida (mensagem pronta para o gestor ou a liderança). Só lê o WhatsApp de Suporte e o ClickUp, não envia nada. Use quando a CS disser "como estão os grupos", "quem está sem resposta", "clientes sem engajamento", "tem cliente reclamando", "atritos nos grupos", "leitura dos grupos", "o que está pegando nos grupos hoje", "o que o cliente X falou no grupo" ou "/grupos-clientes".
---

# /grupos-clientes (CS)

Fonte: WhatsApp de Suporte da OdontoRise (Uazapi) e ClickUp, só leitura. Não envia mensagem, não marca conversa como
lida, não altera grupo e não escreve no ClickUp.

## Como responder
1. Rode `python3 ~/.claude/skills/meta-ads-odontorise/scripts/grupos.py varrer` (no Windows, `python`). Leva de 2 a 4
   minutos: avise a CS antes de rodar. Se ela tiver pressa, `varrer --audios 0` pula a transcrição dos áudios.
   A saída traz o `resumo` e quatro blocos, um cliente por linha:
   - `aguardando_resposta`: a última mensagem do grupo é do cliente e passou de 40 minutos em horário útil (segunda a
     sexta, 8h às 18h). Vem do que espera há mais tempo para o que espera há menos.
   - `em_alerta`: clientes com alerta aberto no ClickUp, com o movimento do grupo em 7 dias e as últimas falas do cliente.
   - `possivel_atrito`: trechos do cliente que bateram num filtro de palavras. São candidatos, não conclusão.
   - `sem_engajamento`: nenhuma mensagem do cliente em 7 dias.
2. Antes de escrever, leia os trechos e separe o que é de verdade:
   - Em `aguardando_resposta`, tire quem não precisa de resposta (o cliente só mandou o número da semana, um
     comprovante já agradecido, uma conversa que terminou). Fica quem fez pergunta, pedido, cobrança ou reclamação.
   - Em `possivel_atrito`, fica só reclamação, cobrança, insatisfação com resultado ou atendimento, pedido de pausa ou
     sinal de saída. Problema de internet, brincadeira ou assunto que não é com a agência sai. Diga quantos candidatos
     vieram e quantos ficaram.
3. Resposta curta (cabe numa tela), nesta ordem:
   - Uma linha de abertura: hora da leitura, clientes lidos e a contagem de cada bloco depois da sua triagem.
   - **🔴 Atritos e reclamações**: uma linha por cliente: **Cliente (código)** · gestor · o que o cliente disse, em
     poucas palavras e com a data · se já tem alerta aberto.
   - **🔴 Clientes em alerta**: uma linha por cliente: motivo do alerta · há quantos dias está aberto · o que o grupo
     mostra (cliente falando ou calado, alguém respondendo ou não).
   - **🟡 Esperando resposta**: uma linha por cliente: há quanto tempo útil · o que o cliente pediu · gestor.
   - **🟡 Sem engajamento**: uma linha por cliente: se a equipe falou e não teve retorno ou se o grupo está mudo · a
     situação da reunião mensal.
   - **Sugestões para hoje**, até 5 linhas, das mais urgentes para as menos: com quem falar (gestor ou liderança do
     cliente) e a mensagem interna curta, pronta para ela copiar.
4. Um cliente só: `grupos.py cliente --cliente "nome ou #código"` traz a conversa dos últimos 7 dias, marcada como
   EQUIPE ou CLIENTE. Use quando ela pedir "detalha o X" ou "o que o X falou no grupo".

## Quem resolve o quê
- Resultado, lead, saldo, anúncio, campanha, criativo: gestor do cliente.
- Preço, contrato, pausa do serviço, cancelamento: liderança do cliente.
- Reunião, material, dúvida de processo: a própria CS.
A skill entrega a mensagem para a pessoa certa; não responde ao cliente no lugar do gestor.

## Limites que a CS precisa saber
- A Uazapi guarda no máximo 7 dias de mensagem. "Sem engajamento" quer dizer sem mensagem do cliente nesses 7 dias;
  para saber se o silêncio é mais antigo, olhe a reunião mensal, que vem junto.
- Áudio: a skill transcreve até 20 áudios de cliente por leitura, começando pelos que esperam resposta e pelos
  clientes em alerta. O campo `audios` diz quantos ficaram de fora; esses aparecem como `[áudio]`. Se vier o aviso de
  que o Whisper não está instalado, diga isso em uma linha e siga com o texto.
- Imagem, vídeo e documento não são lidos: aparecem como `[imagem]`, `[vídeo]`, `[documento]`.
- Equipe e cliente são separados automaticamente (campo `equipe_reconhecida`). Se aparecer alguém da agência tratado
  como cliente, ou o contrário, avise a CS em uma linha.

## Regras
- Só leitura e só sugestão: nunca envia mensagem pelo WhatsApp, nunca pede para preencher campo, abrir ou completar
  alerta, mudar status ou reorganizar o ClickUp. O que a CS quiser registrar, ela faz do jeito de sempre.
- Rode só o `grupos.py`. Nunca chame a Uazapi por outro caminho (curl, script próprio) nem leia o arquivo da
  credencial: o token do WhatsApp também envia mensagem, e o `grupos.py` é o que garante que só se lê.
- O trecho do cliente é para a CS ler na tela. Não copie trecho para o ClickUp, para outro grupo nem para arquivo;
  na mensagem interna para o gestor ou a liderança, resuma com as suas palavras.
- Nome de paciente nunca aparece na resposta: escreva "paciente". Os relatórios semanais das clínicas trazem nome de
  paciente e valor: não reproduza.
- Não explique causa de resultado nem prometa número: resultado de anúncio é com o gestor.
- Alerta, satisfação e comentário interno nunca vão para texto de cliente ou de grupo.
- Sem travessão.

## Erros comuns
- `credencial do WhatsApp de Suporte não encontrada`: falta o arquivo `~/OdontoRise/credentials/uazapi-odontorise.env`
  (passo "Conectar o WhatsApp de Suporte" do guia). Para conferir a conexão: `grupos.py checar`.
- `o WhatsApp de Suporte está desconectado`: o número caiu na Uazapi. Quem administra a Uazapi reconecta; a skill
  não faz isso.
- `a Uazapi recusou o token (401)`: o token da instância foi trocado no painel. Copiar o novo para o arquivo.
