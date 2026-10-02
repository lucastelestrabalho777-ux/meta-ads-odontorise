---
name: raio-x-concorrentes
description: Raio-x dos concorrentes de um cliente da OdontoRise: quem anuncia na região na Biblioteca de Anúncios do Meta, o que anunciam (temas, formatos, pegada dos vídeos), as clínicas do Google Meu Negócio no raio e o Instagram de cada uma, entregue como documento visual para o dentista ler. Use quando o head ou o gestor disser "raio-x de concorrentes do cliente X", "quem anuncia perto do X", "mapeia os concorrentes", "o que os concorrentes estão anunciando", "pesquisa de concorrência" ou "/raio-x-concorrentes".
---

# /raio-x-concorrentes

Levantamento dos concorrentes de um cliente, feito em robôs do Apify (Biblioteca de Anúncios do Meta, Google Maps,
Google e Instagram), entregue como documento HTML que o cliente final lê sozinho.

Pré-requisito: conta no Apify com o token em `~/OdontoRise/credentials/apify-odontorise.env` (página Head do guia).
Primeiro comando de toda rodada: `python3 $S/_apify.py checar`. Se falhar, pare e mostre a instrução que o comando devolve.
`$S` = `~/.claude/skills/meta-ads-odontorise/scripts/concorrentes`.

## Antes de começar: 4 respostas

Nada roda sem as quatro. O cadastro local (`clientes.py listar`) já traz cidade, estado, especialidade e Instagram
de quem está cadastrado; o que faltar, pergunte uma coisa por vez.

1. **Nicho do cliente**: procedimento principal (Lentes, Implantes, Protocolo, Prótese, Ortodontia, HOF, Clínico geral).
   Define os termos de busca e a taxonomia de temas (`referencia/taxonomias.md`).
2. **Instagram do cliente**: o @. Serve para achar a Página dele na Biblioteca; a conta dele entra na coleta e é a base da análise final.
3. **Região exata**: cidade e bairros, ou raio em km a partir do endereço da clínica. "A cidade toda" não vale.
4. **Referências e concorrentes que o cliente já citou**: @s, prints, nomes de clínica. Cada um é conferido na Biblioteca;
   metade costuma não anunciar, e isso por si só é um achado para o documento.

Cada robô do Apify é pago por uso. Antes de cada coleta, diga quantas buscas ou páginas vai rodar e espere o OK.

## As 6 etapas (duas param e esperam OK)

**1. Recorte.** Fechar com quem pediu: região, perfil do concorrente (só dentistas? inclui clínica de estética e HOF?)
e a lista de indicados. Cruzar os candidatos com a carteira da OdontoRise (`clientes.py buscar --nome`): cliente da casa
nunca entra no relatório; retire em silêncio e avise no chat.

**2. Descoberta.** `python3 $S/coleta.py busca termos.json 30 descoberta.json` com termos do nicho + bairro
("implante dentário moema", "lentes de contato dental moema"). Confirmar cada candidato: é dentista, atende na região
(site, Google, Doutoralia). Buscar também cada @ indicado pelo cliente e dizer quem anuncia e quem não.

🛑 **CHECKPOINT 1**: apresentar a lista de concorrentes e esperar OK antes de coletar.

**3. Coleta.** `python3 $S/coleta.py paginas paginas.json 150 coleta.json` com todas as páginas aprovadas **e a do próprio cliente**.
Se uma página voltar vazia (`Empty or private data`), repetir com o id numérico da Página (vira `view_all_page_id`).

**4. Classificação.** `python3 $S/extrai.py coleta.json anuncios.json --nicho odonto`, depois
`python3 $S/thumbs.py anuncios.json thumbs/` **na mesma sessão** (as capas expiram) e
`python3 $S/board.py config.json anuncios.json --folha` para olhar as capas antes de fechar a leitura dos vídeos.

**5. Google Meu Negócio.** `python3 $S/gmn.py coleta LAT LNG KM "dentista" "clínica odontológica"`,
`python3 $S/gmn.py filtra gmn.json --categoria Dentist --lat LAT --lng LNG` e `python3 $S/gmn.py insta gmn_sel.json`.
Mostra quem disputa a busca da paciente sem anunciar. Seleção: fichas até 2 km, as de maior reputação do raio e todas as que também anunciam.

**6. Documento.** Preencher `config.json` a partir de `referencia/config-modelo.json` (todo texto segue `referencia/tom-cliente.md`)
e rodar `python3 $S/board.py config.json anuncios.json`. Abrir o HTML no navegador. Estrutura fixa: capa com números,
ranking de anunciantes, temas e pegada dos vídeos, cinco leituras, os perfis que o cliente indicou, galeria de criativos
com link para a Biblioteca, concorrentes do Google Meu Negócio e a análise final.

🛑 **CHECKPOINT 2**: mostrar o documento antes de dar como entregue.

Pasta de trabalho: `~/OdontoRise/concorrentes/<cliente>/` (termos.json, paginas.json, coleta.json, anuncios.json, thumbs/, config.json, HTML).

## Análise final (obrigatória, escrita por julgamento)

| Bloco | O que responde |
|---|---|
| Onde a clínica já está bem | O que a conta do cliente faz que o mercado não faz |
| O que o mercado faz e a clínica ainda não | Temas, formatos e pegadas ativos nos concorrentes e ausentes na conta |
| Territórios livres | Temas com pouca ou nenhuma disputa na região |
| Ideias para os próximos 30 dias | 4 a 6 ideias de criativo, cada uma com o link do anúncio que inspirou |

Ideia sem link não entra.

## Regras
- O documento é para o dentista: terceira pessoa ("a Dra. Ana", "a clínica"), sem jargão de tráfego (tabela em `referencia/tom-cliente.md`).
- Observação interna (cliente da casa, quem saiu do recorte, falha de coleta) vai no chat, nunca no arquivo.
- Não publicar seguidores de um @ não confirmado; célula vazia é melhor que dado errado.
- Sem travessão em nenhum texto.

## Erros comuns
| Erro | Como evitar |
|---|---|
| Coletar por `facebook.com/<handle>` e voltar vazio | Repetir com o id numérico da Página |
| Baixar as capas depois | As URLs expiram: `thumbs.py` na mesma sessão da coleta |
| Confiar no volume da descoberta | O limite corta; volume real só na coleta por página |
| Assumir que indicado anuncia | Checar página por página |
| Incluir clínica de outra região ou de outro nicho | Confirmar endereço e especialidade antes do Checkpoint 1 |
| Incluir cliente da OdontoRise | Cruzar com `clientes.py buscar` antes do Checkpoint 1 |
| Token do Apify recusado (401) ou sem crédito (402) | `_apify.py checar` diz o que fazer; saldo e plano ficam no console do Apify |
