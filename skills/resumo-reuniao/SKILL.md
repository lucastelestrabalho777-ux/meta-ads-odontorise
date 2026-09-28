---
name: resumo-reuniao
description: Transcreve a gravação de uma reunião com cliente (arquivo de áudio ou vídeo local) e escreve a ata com decisões, pendências e próximos passos, pronta para o ClickUp e para o grupo do cliente. Use quando o CS ou o gestor disser "resumo da reunião", "ata da reunião", "transcreve a reunião", "o que ficou decidido na call" ou "/resumo-reuniao".
---

# /resumo-reuniao

1. **Arquivo**: peça o caminho da gravação (áudio ou vídeo) ou use o mais recente em Downloads.
2. **Transcreva** com `scripts/transcrever.py` da skill meta-ads-odontorise no Python do ambiente de
   transcrição (Mac Apple: `~/.cache/whisper-venv/bin/python`). Reunião longa demora alguns minutos; avise.
   Nunca envie a gravação a serviço externo.
3. **Escreva a ata** com estes blocos, curtos e com nomes:
   - Cliente, data, quem participou.
   - Contexto em 3 linhas.
   - Decisões (o que foi combinado).
   - Pendências: o quê, quem, até quando.
   - Próxima reunião, se marcada.
   - Sinais de risco: reclamação, dúvida sobre resultado, pedido de pausa ou de saída. Se houver, destaque no topo.
4. **Duas versões**: a ata completa (para o ClickUp, na tarefa da reunião) e uma mensagem de 5 linhas
   para o grupo do cliente, no tom da casa. Sem travessão.
5. Registrar no ClickUp e enviar no grupo são ações da pessoa: entregue os textos prontos e pergunte.

## Regras
- Nome de paciente citado na reunião não entra na ata: use "paciente".
- Valores financeiros só se o cliente os tiver dito; nunca inferir.
