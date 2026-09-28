---
name: sugerir-roteiros
description: Sugere roteiros de vídeo para o cliente a partir dos anúncios que mais geram mensagens na conta dele e do playbook do procedimento (lentes, implantes, harmonização). Use quando o gestor disser "roteiros para o cliente X", "ideias de vídeo", "o que gravar para o cliente", "criativos novos para a conta" ou "/sugerir-roteiros".
---

# /sugerir-roteiros

## Dados
1. `insights.py resultado --cliente X --level ad --date-preset last_30d --limit 10`: os anúncios com mais mensagens e menor custo.
2. `read.py creative --id <criativo>` dos 3 melhores: texto, tipo (vídeo, imagem, post) e link do post.
3. Cadastro local: procedimento (especialidade) e cidade do cliente.
4. `references/padroes-campanha.md` da skill meta-ads-odontorise: ângulo, pergunta de qualificação e objeções do procedimento.

## Entrega
Cinco roteiros, cada um com: gancho (primeiros 3 segundos), estrutura em 4 blocos (problema, o que o dentista faz,
resultado esperado, chamada para o WhatsApp), duração sugerida, e "por que este": qual anúncio campeão inspirou
e qual objeção ele ataca. Um dos cinco deve ser depoimento ou caso explicado pelo dentista; nenhum pode usar
rosto de paciente sem termo assinado. Linguagem do paciente final, sem termo técnico sem explicação.

## Regras
- Só procedimentos do cliente (especialidade principal e secundária do cadastro).
- Sem promessa de resultado, sem preço no roteiro. Sem travessão.
- Se a conta não tiver 30 dias de dados, avisar e usar o playbook como base.
