---
name: pdf-odontorise
description: Gera PDF no padrão visual da OdontoRise, em dois formatos: documento de leitura em A4 (ata, relatório, comunicado, combinado, passo a passo para o cliente) e apresentação 16:9 (treinamento, reunião, proposta). A pessoa entrega o conteúdo (texto, anotações, resultado de outra skill) e recebe o arquivo pronto na pasta OdontoRise/pdfs. Use quando a pessoa disser "faz um PDF", "PDF no padrão da OdontoRise", "transforma isso em PDF", "monta a ata em PDF", "relatório em PDF", "faz uma apresentação", "slides do treinamento", "documento para o cliente" ou "/pdf-odontorise".
---

# /pdf-odontorise

Monta o documento em cima de um modelo pronto (visual do Manual de Cultura: navy `#0f1427`, verde-água `#57d8b3`, títulos
em Arial maiúsculo, corpo em Verdana) e gera o PDF com o Chrome ou o Edge que já está no computador. Não instala nada.
O arquivo fica só no computador da pessoa: a skill não envia PDF a ninguém.

## Qual formato
- **documento** (padrão): A4 retrato, para ler. Ata de reunião, relatório, comunicado, combinado, guia para o cliente.
- **apresentacao**: slides 16:9, para apresentar. Treinamento, reunião com cliente, proposta.
Se o pedido não deixar claro, use documento e diga em uma linha que também existe a versão em slides.

## Passos
1. Antes de montar, tenha em mãos: o conteúdo, para quem é (time interno ou cliente), quem assina e a data. Se faltar
   conteúdo, peça. Nunca complete com texto ou número inventado.
2. Crie o arquivo de trabalho (no Windows, `python`):
   `python3 ~/.claude/skills/meta-ads-odontorise/scripts/pdf.py novo --tipo documento --nome "Ata reunião Dra. X novembro"`
   A saída traz o caminho do `.html` em `~/OdontoRise/pdfs/<data>-<nome>/`, já com o logo ao lado.
3. Leia esse `.html` e troque o conteúdo. O modelo traz um exemplo de cada bloco, com comentário explicando:
   - Não mexa no `<style>` nem crie classe nova. Use os blocos que existem e apague os que o conteúdo não pede.
   - Troque também o `<title>`: ele vira o nome do PDF.
   - Documento: cada `<section class="page">` é uma página e termina com `.pfoot` ("1 de 3"). A primeira abre com
     `.masthead`; as outras com `<div class="inner top">`. Blocos: `.kpis` (indicadores), `.flag` red, amber, green e
     blue (leitura), `.section` com `h2` e texto, `.goal` (caixa de destaque), `table` (com `left`, `compact`, linhas
     `total` e `hl`), `ul.pts` (lista), `.method` (como foi levantado) e `.box` (quadro de fechamento).
   - Apresentação: cada `<section class="slide">` é um slide. De 7 a 9 é o normal. Tipos: `cover`, `statement` (verde,
     uma ideia só), `rows` (linhas com rótulo), `cards` c2 a c5, `split` com `prose` e `panel`, `timeline` (t3, t4 ou 5
     passos), `quote`, `talk` (discussão) e `closing`. Rodapé com número de dois dígitos; capa e fechamento sem número.
   - Texto que veio pronto de outra pessoa não se reescreve. Se não couber, divide em mais uma página ou slide.
4. Gere: `python3 ~/.claude/skills/meta-ads-odontorise/scripts/pdf.py gerar "<caminho do .html>"`.
   A saída traz o caminho do PDF, a sobra de cada página até o rodapé e os `avisos`.
5. Se vier aviso, corrija e gere de novo, até a lista de avisos ficar vazia:
   - "conteúdo passando do rodapé": tire texto ou abra mais uma página ou slide e acerte a numeração.
   - "sobrou texto do modelo" ou "sobrou número 00": troque pelo conteúdo real ou apague o bloco.
   - "tem travessão": troque por vírgula, ponto ou dois-pontos.
6. Entregue em três linhas: o caminho do PDF, quantas páginas ou slides e o que ficou de fora ou precisou ser dividido.
   Peça para a pessoa abrir e olhar antes de enviar.

## Regras de conteúdo
- Só número real, com a fonte e o período. Sem número, o bloco de indicadores sai.
- Nome de paciente nunca aparece: escreva "paciente".
- Material para cliente ou para grupo não leva alerta, satisfação, comentário interno nem trecho de conversa de outro
  cliente. Tom "você", sem termo interno.
- Treinamento para o time não cita gestor pelo nome. Relatório de controle interno pode citar.
- Trecho de conversa de cliente lido pela /grupos-clientes não vai para PDF: resuma com as suas palavras.
- A data da capa é a do dia em que o material será usado. Assinatura: quem a pessoa disser.
- Sem travessão. Tom da agência: "a gente", frases curtas.

## Imagem e print
Coloque o arquivo na mesma pasta do `.html` e use `<img src="nome.png">`. Print com dado de paciente ou de outro cliente
não entra. PDF não toca vídeo: vídeo vira uma imagem com o link escrito.

## Erros comuns
- `não achei o Chrome nem o Edge`: instalar o Google Chrome. No Windows o Edge já vem instalado e serve.
- `o navegador demorou demais`: fechar o navegador e gerar de novo.
- `modelo não encontrado no pacote`: rodar `/atualizar-git-odontorise`.
