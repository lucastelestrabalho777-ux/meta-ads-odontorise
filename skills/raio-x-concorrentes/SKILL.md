---
name: raio-x-concorrentes
description: Raio-x dos concorrentes de um cliente da OdontoRise, para o gestor (nos próprios clientes) e para o head (na carteira): quem anuncia até 5 km da clínica na Biblioteca de Anúncios do Meta, o que anunciam (temas, formatos, pegada dos vídeos), as clínicas do Google Meu Negócio no raio e o Instagram de cada uma, entregue como documento visual para o dentista ler. Funciona com ou sem Apify (sem Apify, coleta pelo navegador). Use quando o gestor ou o head disser "raio-x de concorrentes do cliente X", "quem anuncia perto do X", "mapeia os concorrentes", "o que os concorrentes estão anunciando", "pesquisa de concorrência" ou "/raio-x-concorrentes".
---

# /raio-x-concorrentes

Levantamento dos concorrentes de um cliente, entregue como documento HTML que o cliente final lê sozinho.
Quem usa: o gestor, só nos clientes do cadastro dele (`clientes.py meus`); o head, na carteira que cadastrou
(`clientes.py meus --gestor NOME`). Cliente fora do cadastro: cadastrar primeiro, nunca contornar.

`$S` = `~/.claude/skills/meta-ads-odontorise/scripts/concorrentes`. Pasta de trabalho: `~/OdontoRise/concorrentes/<cliente>/`.

## Primeira pergunta: "Você tem conta própria no Apify?"

Pergunte isso antes de qualquer coisa, uma vez por pessoa, e siga a resposta. Não há retrabalho: as duas rotas
usam os mesmos arquivos e geram o mesmo documento.

| Resposta | O que fazer |
|---|---|
| **Sim, tenho conta** | O token dela vai em `~/OdontoRise/credentials/apify-odontorise.env`, linha `APIFY_TOKEN=` (console do Apify, Settings, API & Integrations; no Mac, `chmod 600` no arquivo). Rode `python3 $S/_apify.py checar`. Com OK, motor **Apify**. |
| **Não tenho** | Motor **navegador**: `python3 $S/navegador.py checar`. Diga ao gestor que funciona do mesmo jeito, porque a Biblioteca de Anúncios do Meta é pública. O que muda está na tabela abaixo. Não sugira criar conta nem pedir token a ninguém. |
| **Token no arquivo que não é da pessoa** | `_apify.py checar` recusa e explica. O Apify do Lucas é de uso só dele: nunca peça, copie ou aponte para o token de outra pessoa. Siga pelo navegador. |

Trava em código: todo chamado ao Apify confere a conta do token contra a pessoa dona do token do ClickUp nesta
máquina. Token do Lucas em máquina que não é a dele é bloqueado antes de gastar crédito.

| Etapa | Apify | Navegador (sem Apify) |
|---|---|---|
| Descoberta de quem anuncia por termo | `coleta.py busca` | `navegador.py busca` (amostra; o id da página vem do cartão quando a Biblioteca mostra) |
| Anúncios ativos de cada página | `coleta.py paginas` | `navegador.py paginas` (mesmo formato de saída) |
| Classificação, capas, documento | `extrai.py`, `thumbs.py`, `board.py` | iguais |
| Fichas do Google Meu Negócio | `gmn.py coleta/filtra/insta` | fora do documento, ou entram se o gestor colar a lista do Google Maps (nome, nota, avaliações, distância) no `config.json`, bloco `gmn` |
| Seguidores do Instagram de cada concorrente | `gmn.py insta` | célula vazia (nunca inventar número) |

Cada robô do Apify é pago por uso. Antes de cada coleta, diga quantas buscas ou páginas vai rodar e espere o OK.
No navegador não há custo; diga quantas páginas vai abrir (cerca de 1 minuto por página com muitos anúncios).

## Antes de começar: 4 respostas

Nada roda sem as quatro. O cadastro local (`clientes.py listar`) já traz cidade, estado, especialidade e Instagram
de quem está cadastrado; o que faltar, pergunte uma coisa por vez.

1. **Nicho do cliente**: procedimento principal (Lentes, Implantes, Protocolo, Prótese, Ortodontia, HOF, Clínico geral).
   Define os termos de busca e a taxonomia de temas (`referencia/taxonomias.md`). Só entram concorrentes com o
   mesmo foco; quem faz outro procedimento fica fora da coleta (regra da casa, 06/10/2026).
2. **Instagram do cliente**: o @. Serve para achar a Página dele na Biblioteca; a conta dele entra na coleta e é a base da análise final.
3. **Região exata**: a cidade do cliente, **até 5 km** da clínica. É o padrão da casa e não se pergunta outra coisa.
   Se o gestor pedir mais que 5 km, avise antes de aceitar: raio maior aumenta o volume de páginas e anúncios a
   coletar e a ler, traz clínica que não disputa a mesma paciente e dilui o documento. Com o OK dele, registre o
   raio escolhido no rodapé do documento.
4. **Referências e concorrentes que o cliente já citou**: @s, prints, nomes de clínica. Cada um é conferido na Biblioteca;
   metade costuma não anunciar, e isso por si só é um achado para o documento.

**Exceção, "Concorrente de outros serviços":** rede fora do foco com **100 ou mais anúncios ativos** no raio pesa no
leilão e no custo por mensagem da região. Ela não entra no ranking nem nas leituras do procedimento: entra numa seção
própria no fim do documento, com os números e a galeria dela (`config.json`, bloco `outros`, com os anúncios dela
num arquivo separado). Proponha a seção no Checkpoint 1 em vez de incluir a rede na lista.

## As 6 etapas (duas param e esperam OK)

**1. Recorte.** Fechar com quem pediu: raio (5 km), perfil do concorrente (só dentistas do mesmo procedimento? inclui
clínica de estética e HOF quando o foco é HOF) e a lista de indicados. Cruzar os candidatos com a carteira da OdontoRise
(`clientes.py buscar --nome`): cliente da casa nunca entra no relatório; retire em silêncio e avise no chat.

**2. Descoberta.** Termos do nicho + bairro ou cidade ("lentes de contato dental guarulhos", "facetas guarulhos") em `termos.json`.
Apify: `python3 $S/coleta.py busca termos.json 30 descoberta.json`. Navegador: `python3 $S/navegador.py busca termos.json 30 descoberta.json`.
Confirmar cada candidato: é dentista, tem o mesmo foco, atende até 5 km (site, Google, Doutoralia). Buscar também cada @
indicado pelo cliente e dizer quem anuncia e quem não.

🛑 **CHECKPOINT 1**: apresentar a lista de concorrentes (e a eventual seção de outros serviços) e esperar OK antes de coletar.

**3. Coleta.** `paginas.json` com todas as páginas aprovadas **e a do próprio cliente**.
Apify: `python3 $S/coleta.py paginas paginas.json 150 coleta.json`; página vazia (`Empty or private data`): repetir com o id numérico.
Navegador: `python3 $S/navegador.py paginas paginas.json 150 coleta.json`; aceita id numérico, link ou nome; quando não
resolve o id, o resultado traz `sem_id` e o gestor copia o `view_all_page_id` da URL ao abrir a página na Biblioteca.
Em qualquer rota, compare `declarado` com `coletados`: diferença grande pede uma segunda passada só naquela página.

**4. Classificação.** `python3 $S/extrai.py coleta.json anuncios.json --nicho odonto`, depois
`python3 $S/thumbs.py anuncios.json thumbs/` **na mesma sessão** (as capas expiram) e
`python3 $S/board.py config.json anuncios.json --folha` para olhar as capas antes de fechar a leitura dos vídeos.
Rede de outros serviços: `extrai.py` separado para `anuncios_outros.json`.

**5. Google Meu Negócio.** Apify: `python3 $S/gmn.py coleta LAT LNG 5 "dentista" "clínica odontológica"`,
`python3 $S/gmn.py filtra gmn.json --categoria Dentist --lat LAT --lng LNG` e `python3 $S/gmn.py insta gmn_sel.json`.
Seleção: fichas até 2 km, as de maior reputação do raio e todas as que também anunciam.
Sem Apify: pule, ou peça ao gestor a lista do Google Maps (nome, nota, avaliações, distância) e preencha `gmn.linhas`
no `config.json`; seguidores ficam vazios.

**6. Documento.** Preencher `config.json` a partir de `referencia/config-modelo.json` (todo texto segue `referencia/tom-cliente.md`)
e rodar `python3 $S/board.py config.json anuncios.json`. Abrir o HTML no navegador. Estrutura fixa: capa com números,
ranking de anunciantes, temas e pegada dos vídeos, cinco leituras, os perfis que o cliente indicou, galeria de criativos
com link para a Biblioteca, seção de outros serviços (quando houver), concorrentes do Google Meu Negócio (quando houver)
e a análise final.

🛑 **CHECKPOINT 2**: mostrar o documento antes de dar como entregue. Depois, oferecer o registro no ClickUp pelo
`/registrar-otimizacao` (tipo Otimização de Clientes, "Raio-x de concorrentes entregue").

Arquivos da pasta de trabalho: termos.json, descoberta.json, paginas.json, coleta.json, anuncios.json, anuncios_outros.json, thumbs/, config.json, HTML.

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
- Observação interna (cliente da casa, quem saiu do recorte, falha de coleta, rota usada) vai no chat, nunca no arquivo.
- Não publicar seguidores de um @ não confirmado; célula vazia é melhor que dado errado.
- Só clientes do cadastro da pessoa. Só 5 km, salvo OK explícito depois do aviso de volume.
- Token do Apify é pessoal: nunca pedir, copiar ou usar o de outra pessoa. Sem conta, navegador.
- Ao adaptar ideia que mostra paciente, lembrar: dentista pode usar rosto de paciente com termo assinado (CFO).
- Sem travessão em nenhum texto.

## Erros comuns
| Erro | Como evitar |
|---|---|
| Coletar por `facebook.com/<handle>` e voltar vazio (Apify) | Repetir com o id numérico da Página |
| Nome com várias páginas iguais (navegador) | O resultado lista os candidatos em `sem_id`; escolher o id e repetir |
| Baixar as capas depois | As URLs expiram: `thumbs.py` na mesma sessão da coleta |
| Confiar no volume da descoberta | O limite corta; volume real só na coleta por página |
| `declarado` muito maior que `coletados` (navegador) | A Biblioteca parou de carregar; repetir só aquela página com `--rolagens 120` |
| Assumir que indicado anuncia | Checar página por página |
| Incluir clínica de outra região, de outro procedimento ou além de 5 km | Confirmar endereço, especialidade e distância antes do Checkpoint 1 |
| Incluir cliente da OdontoRise | Cruzar com `clientes.py buscar` antes do Checkpoint 1 |
| Token do Apify recusado (401), sem crédito (402) ou de outra pessoa | `_apify.py checar` diz o que fazer; sem conta própria, navegador |
| Chromium ausente | `navegador.py checar` devolve o comando de instalação (`python3 -m playwright install chromium`) |

## Atualizações
- 07/10/2026: aberta aos gestores (só nos próprios clientes); rota sem Apify pelo navegador (`navegador.py`); trava do token do Apify por pessoa; regra de 5 km com aviso de volume; seção "Concorrente de outros serviços" no documento.
- 02/10/2026: primeira versão, só head, só Apify.
