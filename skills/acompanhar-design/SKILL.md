---
name: acompanhar-design
description: Acompanha o setor de Design para o head: demandas de vídeo e imagem atrasadas, fila esperando design, tempo médio para concluir por tipo e por pessoa. Use quando o head disser "como está o design", "demandas atrasadas do designer", "fila de criativos", "tempo médio de vídeo", "acompanhar design" ou "/acompanhar-design".
---

# /acompanhar-design

Fonte: lista Conteúdos dos Clientes do ClickUp (`scripts/design.py resumo --dias 60`, skill meta-ads-odontorise, só leitura).
Os status da lista mostram onde cada demanda está: copy pendente, aprovação copy, aguardando vídeo/foto,
aguardando design, aguardando alteração, aprovação gestor, aprovação final, aprovação cliente, concluída.

## Como responder
1. Rode `design.py resumo`. 
2. Entregue:
   - 🔴 Atrasadas: demanda · cliente · tipo (vídeo, estático, LP) · com quem · dias de atraso. As mais atrasadas primeiro.
   - Fila de design: quantas esperam design ou alteração e há quantos dias a mais antiga espera.
   - Tempo médio para concluir na janela: por tipo (vídeo, estático, LP) e por pessoa, e o tempo médio parado em
     "aguardando design".
   - Três apontamentos: gargalo (status onde as demandas mais param), pessoa sobrecarregada, cliente com mais demanda parada.
3. Pergunte se quer o texto de cobrança para o designer ou para o gestor dono da demanda.

## Regras
- Só leitura. Tempo é medido da criação à conclusão e por tempo em cada status. Sem travessão.
