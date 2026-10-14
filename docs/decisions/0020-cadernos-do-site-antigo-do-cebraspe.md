# 0020 — Cadernos do site antigo do Cebraspe: fontes sem nome e sem mapeamento

**Data:** 2026-10-08 · **Marco:** M5

## Contexto

O primeiro caderno do `www.cespe.unb.br` (PF 2012, Agente) tem texto, mas o Distiller converteu as
fontes TrueType em Type 1 sem nome ("TTD0ABo00") e sem peso nem ângulo no descritor:

- os números de item estão numa fonte subconjunto sem ToUnicode e com glifos "g18".."g27": saem
  como códigos de controle (`\x02\x0b` = 10), e o parser achava 1 questão em 120;
- negrito e itálico somem (todas as fontes vêm com o mesmo `flags`);
- o "ℓ" de "(ℓ.12)" vem numa fonte de símbolos cujo glifo se chama "R";
- a faixa "PROVA OBJETIVA" e os quadros "RASCUNHO" estão em outra fonte sem mapeamento;
- a coluna da esquerda vai de 28 a 312 pt numa página de 595: passa do meio da página, e as linhas
  dela viravam "largura total".

O OCR dos números na margem (Tesseract só com dígitos) foi tentado e descartado: lê "11" como "1",
"9 O" como "90" e quase nada na coluna da direita.

## Decisões

1. **`extract(..., legacy=True)` só para a fonte `cespe-unb`** (`LEGACY_SOURCES` no pipeline).
   Nenhum PDF já aprovado muda: os 270 PDFs do staging foram extraídos com o código antigo e o novo e
   comparados, sem diferença.
2. **Vão entre as colunas** deduzido da página: se alguma linha cruza a metade da largura e outra
   posição entre 35% e 65% é cruzada por menos linhas, o vão é a faixa menos cruzada mais perto do
   meio.
3. **Números de item decodificados, não lidos por OCR**: numa fonte só com códigos de controle, os
   nove primeiros números de um glifo, na ordem de leitura, são 1 a 9 e o código que sobra é 0. A
   tabela só vale se todos os números da fonte formarem uma sequência de um em um.
4. **Negrito e itálico pelas larguras**: a largura média das letras de cada fonte sem nome é
   comparada com a das fontes-padrão do PDF (Times e Helvetica, quatro estilos); a mais próxima dá o
   estilo, com no mínimo 20 letras e distância média até 0,02 corpo. Helvetica normal e oblíqua têm
   as mesmas larguras: no empate fica a normal. Pontuação sozinha não recebe estilo.
5. **"(R.12)" → "(ℓ.12)"** quando o "R" está sozinho, em fonte diferente das vizinhas, entre "(" e
   ".<dígito>".
6. **Correções revisadas valem também em página com texto**: `ingest/ocr/<sha256>.yaml` (decisão
   0018) passa a corrigir linhas em fonte sem mapeamento, conferidas contra a imagem da página
   ("PROVA OBJETIVA", "RASCUNHO", a tecla Enter desenhada). A página corrigida ganha
   `revisado:<modelo>` no `extracted_by`.
7. **Parser**: "RASCUNHO" é ignorado como "Espaço livre"; comando que começa com minúscula marca a
   questão com `layout` (o corte entre texto-base e comando errou — lista I–IV com recuo deslocado).
8. **Crédito do texto em duas linhas** (letra miúda, alinhado à direita, termina em "(com
   adaptações)") é um parágrafo só, com o negrito do título emendado; e "In" numa fonte própria
   seguido de ":" é itálico (*In*:), já que duas letras não bastam para deduzir o estilo. A primeira
   amostra do PF 2012 foi recusada por esses dois defeitos; a segunda passou 10/10.
9. **Disciplina nova `economia`** (micro, macro, setor público, economia brasileira): o PF 2012 tem
   8 itens de economia e não havia onde pô-los.

## Consequências

- PF 2012 Agente: 120 itens, 13 textos-base, gabarito com 8 anulados; 27 itens em `review` (poema
  em duas colunas, ofícios, figuras, a lista I–IV dos itens 83–84).
- As fontes "TT...o00" sem estilo também aparecem em cadernos novos já aprovados (PC/PE 2023, PF
  2025...): com o item 4 eles ganhariam itálico e negrito que hoje faltam ("*videogame*",
  "**Ciência Hoje**"). Ligar `legacy` para eles exige reprocessar e reamostrar; fica como próximo
  passo.
- O item 8 vale para todos os cadernos: 82 textos-base de provas aprovadas (PF 2021, CBM/AL 2017
  e outras) hoje publicam o crédito partido ao meio ("... geopolítica" | "global. Campinas...").
  Corrige-se ao reprocessar e reamostrar essas provas.
- As mudanças do item 7 alteram, no próximo reprocessamento, flags de provas aprovadas: CBM/AL 2021
  soldado e oficial (itens perdem `figure`/`layout` falsos vindos do "RASCUNHO"), PM/TO 2020 QPE q50 e QPPM
  q35 (idem) e PF 2021 agente q97–101 (ganham `layout`: o comando começa no meio da tabela). Nada
  muda no banco até essas provas serem reprocessadas.

## Emenda de 2026-10-13 — estilo pelas larguras por prova (`infer_font_styles`)

**Contexto.** O minos reprovou a amostra do PF 2021 delegado: o itálico de "*habeas corpus*" (q26)
e "*habeas data*" (q25) não chega ao banco. O caderno usa fontes "TT…o00" sem nome de estilo, e o
item 4 só vale com `legacy`, que é só da fonte `cespe-unb`.

**Decisão.** `extract(..., styles=True)` liga só o item 4 (negrito/itálico pelas larguras das fontes
sem nome); vão entre colunas, números de item, "ℓ" de fonte própria, "*In*:" e fonte monoespaçada
seguem como sem `legacy`. Documento sem fonte sem nome não muda. No manifesto, a prova liga com
`infer_font_styles: true`, e vale só para o caderno (o gabarito não tem marcação). Ligado por
enquanto só no PF 2021 delegado.

**Por que por prova.** Comparado `extract`+`segment` com e sem `styles` em todos os PDFs do staging
fora do `cespe-unb`: o texto muda em quase todas as provas já publicadas (só a marcação; o texto puro
não muda), e em algumas mudam também as pendências (`flags`) de itens. Ligar para todas deixaria o
banco diferente do `main` até reprocessar e reamostrar tudo. Cada prova liga a opção quando for
reprocessada e reamostrada; quando todas tiverem passado, a opção pode virar o padrão.

**Adendo (2026-10-13, PF 2018).** O PF 2018 inteiro (agente, escrivão, papiloscopista, delegado) liga
`infer_font_styles`: o banco dessas provas já tinha sido carregado com o estilo pelas larguras (código
de um ciclo anterior que não chegou ao `main`), e o papiloscopista foi aprovado assim. Com ele vem
uma regra do item 4 que também vale com `styles`: a fonte sem nome que escreve o "In" de "*In*:" no
crédito e tem letras de menos para as larguras é a itálica miúda do crédito, e todo o texto nela
fica itálico ("Z. Nateghian *et al*.", "K*ps*"). Nos cadernos do `cespe-unb` e no PF 2021 delegado
o resultado não muda (comparado `extract`+`segment` antes e depois).

## Emenda de 2026-10-14 — fontes com letras de menos e fonte monoespaçada com `infer_font_styles`

**Contexto.** O minos reprovou 4 provas do lote 2 do `infer_font_styles`: no PM/PA 2023 CFP
(específicos), "*chip*" (q37) e "*habeas corpus*" (q58) sem itálico, cada um numa fonte "TT…o00"
própria com 4 e 13 letras; no PM/PA 2023 CFO (básicos p1), o título do crédito "**Comunicação não
violenta**" sem negrito (fonte de 6 pt com 19 letras ASCII); no PC/GO 2016 básicos (agente e
escrivão, mesmo caderno), q15 com comandos e caminhos em fonte monoespaçada sem código inline. As
duas primeiras ficam abaixo das 20 letras do item 4; a terceira é o `mono` do `legacy`, que a
emenda de 2026-10-13 deixou de fora do `styles`.

**Decisão.** Valem com `legacy` e com `styles`, só para fontes sem nome sem estilo deduzido pelo
item 4:

1. **Mesmo desenho, mesmo estilo.** O Distiller dá a cada página um subconjunto próprio da fonte,
   com os glifos de mesmo nome e mesmo desenho; normal, negrito e itálico têm desenhos diferentes.
   A fonte sem estilo que desenha (CFF embutida, mesma `FontMatrix`) pelo menos 3 glifos em comum
   exatamente como uma fonte já deduzida pelas larguras herda o estilo dela. Fontes de estilos
   diferentes casando ao mesmo tempo: nada. A fonte do "*In*:" (adendo do PF 2018) não serve de
   referência.
2. **Larguras com margem.** Sem desenho que case, a fonte com pelo menos 6 letras ASCII, 4 delas
   distintas, recebe o estilo da referência mais próxima (Times/Helvetica, quatro estilos) se a
   distância média for até 0,008 corpo e a referência de outro estilo mais próxima ficar pelo
   menos 0,006 corpo além. Letras que medem o mesmo em dois estilos ("chip" no Times normal e
   itálico) zeram a margem e nada se deduz; a Helvetica oblíqua não conta como rival da normal.
3. **Fonte monoespaçada vira código inline também com `styles`**: a mesma regra do `legacy` (fonte
   sem nome com pelo menos 8 letras distintas, todas da mesma largura, a 0,01 corpo), e o trecho
   nela vai entre crases (docs/content-format.md).

`fonttools` (já instalado como dependência do `ocrmypdf`) passa a ser dependência direta, para ler
o desenho dos glifos.

**Verificação.** Reprocessado `extract`→`validate` de todas as provas com `infer_font_styles` e
das quatro do `cespe-unb` e comparado com o banco: nenhum texto puro (hash do enunciado) nem
pendência muda; com o código anterior o reprocessamento é idêntico ao banco. Mudam só marcações:
os três itálicos/negritos acima e código inline em PC/GO 2016 básicos q15 (agente e escrivão),
PC/AL 2022 gerais q25, PC/ES 2022 gerais q10, q11, q13 e q14, PF 2018 agente q77, q81, q83 e
q93–96 e PF 2018 escrivão q93–96 (texto-base). Nenhuma mudança nos cadernos do `cespe-unb` nem no
PF 2021 delegado.
