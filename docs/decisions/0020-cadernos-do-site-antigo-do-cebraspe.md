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

## Emenda de 2026-10-14 (2) — "*In*:" no começo da linha e crédito entre parênteses

**Contexto.** O minos reprovou, por formatação, provas em `review`: sem `infer_font_styles`,
PC/RJ 2021, PC/RO 2022 (gerais cargos 1 e 4), CBM/TO 2022 oficial e PM/RO 2022 não têm itálico nem
negrito; com ele, o "In:" do crédito do CG2A1-I do PC/RO 2022 e do CG2A1-II do PC/PB 2021 (cargos
de 4 a 13) seguia sem itálico. No PC/PB 2021 cargo 11, o crédito "(FRANÇA, … reimpr." | "Rio de
Janeiro: Guanabara Koogan, 2021, p. 474)." saía em dois parágrafos e a segunda linha colava no
comando da q66 (e no texto-base da q61).

**Decisão.**

1. A regra do "In" do crédito (adendo do PF 2018) vale também com o "In" no começo da linha ("In" |
   ": Renato S. de Lima…") e com os dois-pontos na mesma fonte ("In:" | " " | "Revista da
   EMERJ"): fonte própria, diferente das vizinhas que existem, e texto em outra fonte depois.
2. No parser do Cebraspe, o crédito em letra miúda alinhado à direita também se encerra na linha
   que termina em ")" ou ")." fechando o "(" com que começa a primeira linha do crédito (no máximo
   `CREDIT_MAX_LINES` linhas); é um parágrafo só, e o que vem depois é outro.
3. `infer_font_styles` ligado em PC/RJ 2021, PM/RO 2022, CBM/TO 2022 oficial e PC/RO 2022 (menos o
   cargo 3 específicos). O CBM/TO 2022 soldado e o PC/RO 2022 cargo 3 específicos ficam para a
   próxima reamostragem: neles o negrito tira o título de disciplina da última alternativa
   ("… militar. Matemática", "… inconsumível. CRIMINOLOGIA") e muda a pendência de questões que
   seguem em `review` por figura, além da marcação. O PM/DF 2025 tem fontes com nome (o estilo já
   chega) e não precisa da opção.

**Verificação.** Reprocessado `extract`→`classify` de todas as 135 provas do staging e comparado com
o banco: fora as provas ligadas agora, só mudam o PC/PB 2021 gerais de 4 a 13 (q5–8, "*In*") e o
cargo 11 (q61 e q66, parágrafos do crédito); o texto puro (hash) não muda em nenhuma questão
publicada. No CBM/TO 2022 oficial, q10 e q40 saem de `review` (o título "Física"/"Matemática" deixa
a alternativa E) e a q20 perde a pendência de layout. Seguem como antes as divergências conhecidas
(PM/MA 2017 gerais cargo 5; provas fora do banco).

## Emenda de 2026-10-14 (3) — estilo no PC/CE 2025, PC/PE 2023 e PC/RO 2022 cargo 3; bloco recuado na múltipla escolha

**Contexto.** O minos (semente r7) reprovou PC/RJ 2021, PC/CE 2025, PC/RO 2022 cargo 3 específicos e
PC/PE 2023 P1 cargo 2: na PC/RJ q39, cada linha da citação da Lei n.º 8.137/1990 (9 pt, recuada em
bloco) virava um parágrafo; nas outras, faltava itálico e negrito das fontes sem nome. A causa da
PC/RJ não era o espaço vertical (`_block_gap`): a citação inteira está recuada além do recuo de
parágrafo, e `_choice_paragraphs` abria parágrafo a cada linha recuada. O mesmo partia os itens
I, II… e • com recuo pendente (PC/MA 2017, PC/GO 2016, PC/PB 2021 gerais de 14 a 17).

**Decisão.**

1. Na múltipla escolha, linha recuada continua a anterior quando as duas têm o mesmo recuo de bloco
   (ou a anterior é um item I, II; a); • na margem e esta tem o recuo pendente, até `ODD_INDENT`),
   a anterior vai até a margem direita e a frase fica aberta: termina em letra, vírgula ou traço e a
   seguinte começa por letra (ou aspas, parêntese). Linha de tabela ou de equação, que termina em
   número ou ")", segue separada. O certo/errado (`_paragraphs`) não muda.
2. `infer_font_styles` ligado no PC/CE 2025, nas cinco provas do PC/PE 2023 e no PC/RO 2022 cargo 3
   específicos (o negrito tira o título "CRIMINOLOGIA" da alternativa E da q95, que segue em
   `review` pela figura).

**Verificação.** Varredura das provas do staging, parser do HEAD × novo: só mudam parágrafos, em 42
questões de 11 provas de múltipla escolha. Carregadas as 18 provas afetadas; nenhuma muda de status.

## Emenda de 2026-10-14 (4) — referência alinhada à direita sem fecho, travessão no item, estilo no PC/MA 2017

**Contexto.** O minos (semente r8) reprovou três provas publicadas. No PC/RO 2022 cargo 3
específicos (q63) e no PC/PE 2023 P2 cargo 1 (texto 1A1-I), a referência em letra miúda alinhada
à direita, sem "(com adaptações)" na última linha ou com a primeira linha quase enchendo a coluna,
saía partida em parágrafos: `_credit_goes_on` só emendava até uma linha de fecho, e só linhas
recuadas além de `ODD_INDENT`. No PC/MA 2017 investigador (q26, q47), a linha do item que começa com
o travessão do aposto ("— polícias civis e militares —, ...") abria parágrafo. No PC/MA 2017 (APC),
sem `infer_font_styles`, faltava o itálico de "habeas corpus" (fontes `TT…o00` sem nome).

**Decisão.**

1. Duas linhas de letra miúda (menor que `CITATION_SIZE`) do mesmo corpo são o mesmo crédito quando
   a de baixo vem colada (espaço até 0,65 do corpo), as duas terminam no mesmo x (até 2 pt), começam
   em x diferentes, a de cima está recuada além do recuo de parágrafo, a de baixo além de
   `ODD_INDENT`, e a de cima vai até a margem. Vale para o certo/errado e para a múltipla escolha.
   As legendas de gráfico alinhadas à direita (PF 2021 g77: 6 pt de espaço em corpo 8) ficam
   separadas; linhas miúdas que começam no mesmo x seguem as regras antigas.
2. No bloco recuado da múltipla escolha (`_indented_block_goes_on`), linha que começa com travessão
   ("—", "–") continua a frase aberta, como a que começa por letra.
3. `infer_font_styles` ligado nas seis provas do PC/MA 2017 APC e no PC/MA 2017 delegado. No
   delegado, o negrito revela o título "DIREITO TRIBUTÁRIO E DIREITO" | "EMPRESARIAL" (14 pt, duas
   linhas): a segunda linha de um título de disciplina em negrito e corpo maior (a partir de
   `KNOWLEDGE_TITLE_MIN_SIZE`), logo abaixo, curta e só em negrito, também é título
   (`_heading_continuation`); sem isso "**EMPRESARIAL**" grudava na alternativa E da q15. Com o
   título em negrito saem do texto o falso texto-base g16 da q16 e o "CRIMINOLOGIA" colado na
   alternativa E da q92, e a moldura do título "DIREITO CIVIL" deixa de marcar figura na q5.

**Verificação.** Varredura das 135 provas do staging, parser do HEAD × novo: mudam só parágrafos,
em 8 questões e 3 textos-base de 9 provas (cbmro-2022 oficial q38/q40 — legenda e crédito da
figura num parágrafo só —, cbmto-2022 oficial q22, pcma-2017-apc investigador q26/q47, pcpb-2021
cargo 12 q78 e complementares 14–17 q47, pcpe-2023 P2 cargo 1 1A1-I, pcro-2022 cargo 3 q63,
pmal-2021 oficial g14, pmpa-2023-cfp básicos CB1A1-II). No PC/MA 2017 APC o estilo só muda
marcação. Carregadas as 15 provas; o delegado volta a `review` (texto de q16 e q92 mudou; as duas
passam a publicáveis, a q5 perde o motivo de figura).

## Emenda de 2026-10-14 (5) — estilo no PM/AL 2021 oficial e no CBM/RO 2022 oficial; linha de código no item

**Contexto.** O minos (semente r9) reprovou duas provas publicadas sem `infer_font_styles`, com fontes
`TT…o00` sem nome: no PM/AL 2021 oficial nenhum negrito, itálico ou código chegava ao banco (crédito
do g14 e do g60, "**nem**" na q24, "**one specific special person**" e "*quilombo*" na q32,
"*rootkits*", "*emails*", "*anti-spam*" nas q48–49), e o comando `head messages.log` da q37, numa
linha à parte, colava no fim da frase; no CBM/RO 2022 oficial, "*Bolivian Syndicate*" (q40, A, C e
E) saía sem itálico.

**Decisão.**

1. `infer_font_styles` ligado no PM/AL 2021 oficial e no CBM/RO 2022 oficial. A dedução pelas
   larguras funciona nessas fontes (Type 1C com encoding próprio) sem mudar código. O PM/AL 2021
   soldado fica para a próxima reamostragem.
2. No item certo/errado, a linha que é só código (fonte monoespaçada inteira) depois de frase
   terminada é um parágrafo à parte, e a primeira linha de texto depois dela abre outro
   (`_code_line_breaks`). Código em linhas seguidas continua num bloco só, como antes (programa
   do PF 2018 agente q93–96, próximo passo à parte).

**Verificação.** Varredura das 135 provas do staging, parser do HEAD × novo: no PM/AL 2021 oficial
mudam só marcação e parágrafos (6 textos-base, 35 questões; q37–39 e q44 com o comando em parágrafo
próprio); no CBM/RO 2022 oficial, marcação em 2 textos-base e 15 questões, e o negrito tira o título
"MATEMÁTICA" da alternativa E da q15 (segue em `review` pela figura, perde a pendência de layout);
no PF 2018 agente q93–96, o código separa-se da frase em parágrafo (o texto puro não muda). Carregadas
as duas provas e o PF 2018 agente: nenhuma muda de status por isso (a impressão digital não vê
marcação nem parágrafo; reamostrar).

## Emenda de 2026-10-14 (6) — referência alinhada à direita que começa na margem

**Contexto.** O minos (semente r10) reprovou o PM/AL 2021 oficial: o crédito do texto CB1A1-I saía em
dois parágrafos ("Manoel Carlos Mendonça Filho *et al*. **Polícia, ...**. Internet:" |
"\<corteidh.or.cr> (com adaptações)."). A primeira linha enche a coluna e começa na margem (x0 igual
ao da coluna), e a regra da emenda (4) exigia recuo de parágrafo nela; o "<" não tinha papel.

**Decisão.** Em `_credit_right_aligned`, a primeira linha pode começar na margem quando a linha de
baixo encerra o crédito (`CREDIT_END`) e a linha de cima da primeira é de outro corpo (a
referência abre ali, depois do texto; texto inteiro em letra miúda seguido do crédito, como no teste
do PM/TO 2020 q23, fica separado). Sem o fecho, linha miúda na margem seguida de linha recuada
continua separada (nota de quadro, legenda). As demais condições (mesmo corpo miúdo, colada, mesmo x
final, x inicial diferente, de baixo recuada como crédito) ficam.

**Verificação.** Varredura das 135 provas, HEAD × novo: mudam só dois créditos, em parágrafo — o
CB1A1-I do PM/AL 2021 oficial e o g1 do PF 2025 básicos bloco I ("...narrativas policiais
televisivas." | "In: Vozes & Diálogo, ... (com adaptações)."; primeira linha com recuo de 14,4 pt,
abaixo do limite de 15). As duas provas carregadas seguem publicadas (a impressão digital não vê
parágrafo; reamostrar).

## Emenda de 2026-10-14 (7) — estilo no PF 2025

**Contexto.** O minos (semente r11) reprovou o PF 2025 básicos bloco I por estilo ausente: o crédito
do g1 sem negrito e itálico ("Camila Furuzawa. **Séries policiais**: ... *In*: **Vozes & Diálogo**"),
"*best-sellers*" sem itálico no g1 e na q2 e "**Manual de Redação da Presidência da República**" sem
negrito na q9. O manifesto do PF 2025 não tinha `infer_font_styles`.

**Decisão.** `infer_font_styles` ligado nas seis provas do PF 2025, sem mudar código.

**Verificação.** `extract`→`validate` com e sem estilo, prova por prova: o texto puro (sem `*`, `**`,
crases e espaços) não muda em nenhuma questão, alternativa ou texto-base. Mudam só marcação: bloco I
(g1, g54, q2, q4, q9, q10), bloco II (23 questões com itálico de estrangeirismo; g91, q91 e q92 com
código inline — o código SQL do g91 vira uma crase por linha, como já saía uma linha por parágrafo,
e o `\_` escapado vira `_` dentro da crase), agente (g107), papiloscopista (q102, q105–108, q110) e
delegado (q52, q65, q76, q97–99, q116); o escrivão não muda. Nenhum motivo de revisão muda. Carregadas
as cinco provas que mudaram: nenhuma questão nem prova muda de status (a impressão digital não vê
marcação; reamostrar).

## Emenda de 2026-10-14 (8) — estilo no PM/SC 2023, PC/SE 2021, PM/AL 2021 soldado e CBM/TO 2022 soldado; definições em linhas, títulos em negrito

**Contexto.** O minos (semente r13) reprovou o PM/SC 2023 soldado: sem `infer_font_styles` faltava o
itálico de "*post mortem*" (q29), "*chatbot*"/"*chat*" (texto 1A5-II, q38), "*Hiperlink*",
"*Cookies*", "*Plug-ins*", "*browser*" (q48) e de *x*, *c*, *l*, *w* (texto 1A7-I e q51); e as
sentenças abertas do texto 1A7-I ("c(x): …" | "l(x): …" | "w(x): …"), em linhas seguidas sem
ponto nem recuo, saíam num parágrafo só. O item 4 dos próximos passos pedia o estilo também no
PC/SE 2021, no PM/AL 2021 soldado e no CBM/TO 2022 soldado.

**Decisão.**

1. `infer_font_styles` ligado no PM/SC 2023 soldado, nas três provas do PC/SE 2021, no PM/AL 2021
   soldado e no CBM/TO 2022 soldado, sem mudar a extração.
2. Linha que começa com rótulo — proposição "P1:", conclusão "C:" ou sentença aberta/função
   "c(x):", "P(x, y):" — abre parágrafo quando a anterior fecha a frase (como já valia para "P1:")
   ou quando o parágrafo aberto também começa com rótulo (`_labeled_line_opens`, no certo/errado e
   na múltipla escolha). A continuação sem rótulo fica na definição.
3. Título de disciplina em negrito, caixa alta e corpo do texto quebrado em duas linhas ("NOÇÕES
   DE DIREITO PROCESSUAL PENAL" | "COMUM", PM/SC 2023 antes da q17): a segunda linha, também
   caixa alta e só negrito, sem número e com até 3 palavras, é título (`_heading_continuation`).
   Com o estilo, a primeira linha já saía como título e "**COMUM**" grudava na alternativa E da q16.
4. Na múltipla escolha, linha só em negrito, curta (até 8 palavras), sem pontuação final, depois de
   alternativa terminada em ponto encerra a última alternativa (`_heading_after_option`); o título
   vai para a abertura seguinte, onde `_bold_heading` o descarta ("**Normas relativas ao CBMTO**",
   "**Noções de Informática**" no CBM/TO 2022 soldado q10 e q30).

**Verificação.** Varredura das provas do staging, parser do HEAD × novo, com as mesmas páginas: os
itens 2–4 mudam só PM/SC 2023 (1A7-I; q16), PC/PE 2023 P2 cargo 1 (situação 1A3-II: P1, P2 e "C:"
em parágrafos próprios), CBM/TO 2022 oficial (q30 perde "Normas relativas ao CBMTO" da alternativa
D) e soldado (q10, q30), CBM/RO 2022 oficial (q75 perde "INSTRUÇÕES TÉCNICAS DO CBM/RO" da E) e PM/TO
2020 QPE q40 e QPPM q30 e q45 (título colado na E). Com o estilo, o texto puro não muda em nenhuma
questão das provas ligadas, fora os títulos que saem das alternativas; o "s*pear phishing*" do PC/SE
2021 é do original (o "s" vem em redondo). PM/AL 2021 soldado q42, q45 e q50 ganham itálico picado
nas fórmulas, mas seguem em `review` pela fórmula. Questões que passam a publicáveis: PM/SC 2023 q8 e
q42, CBM/TO 2022 soldado q20, CBM/RO 2022 oficial q75, PM/TO 2020 QPE q40.

## Emenda de 2026-10-14 (9) — verso em quebra de linha, estrofe em parágrafo

**Contexto.** O minos (semente r14) reprovou o PM/AL 2021 soldado: o poema "À procura da
infância" (g20, pág. 3, itens 20–24) é uma estrofe só no caderno, mas cada linha curta abria
parágrafo e o poema saía em 21 "estrofes" de uma linha. O `docs/content-format.md` já manda grafar
a quebra de verso com `\` no fim da linha.

**Decisão.** No texto-base e no enunciado (certo/errado e múltipla escolha), um bloco de linhas
seguidas na mesma página e coluna, no mesmo corpo, alinhadas na margem sem recuo (ou com o mesmo
meio, recuadas: versos centralizados), sem espaço vertical maior que o entrelinha, é estrofe quando
tem 4 linhas ou mais, 3 linhas curtas no meio e, entre as curtas, pelo menos 2 que terminam em
palavra (2 letras ou mais) ou vírgula e não menos que as que fecham a frase (`_verse_breaks`). Na
estrofe, a linha curta termina em quebra de linha (`\`); a linha que vai até a margem é verso longo
e continua na seguinte com espaço; estrofe nova só com o espaço vertical. Não entram no bloco
título em negrito, item de lista (I, II; a); •; travessão; número; parêntese), linha com rótulo
("P1:", "c(x):"), linha de código nem o crédito; linha que termina em número (tabela) ou em letra
solta (tabela-verdade) não conta como verso aberto; correspondência oficial (vocativo ou fecho,
`LETTER_LINE`) fica de fora inteira — cabeçalho e endereçamento seguem como antes.

**Verificação.** Varredura das provas do staging, parser do HEAD × novo, com as mesmas páginas:
mudam só quatro poemas, todos em provas publicadas — PM/AL 2021 soldado (g20), CBM/AL 2017
básicos cargo 2 (g33, "A história de Lily Braun", duas estrofes), CBM/AL 2017 específicos cargo 2
(g114, "O Xote das meninas", centralizado) e PC/SE 2018 conhecimentos gerais (g12, "Minha Alma").
Nenhum enunciado, alternativa ou motivo de revisão muda. As tentativas intermediárias pegavam a
lista de contas do PF 2018 agente (g100), os campos do PF 2018 escrivão (g93), o SQL do PF 2025
bloco II (g91), a tabela-verdade do PF 2025 bloco I (g54) e do CBM/PA 2023 (q23/q44) e o cabeçalho
do ofício do PC/PB 2021 (CG1A1-III): as exclusões acima existem por eles. A impressão digital da
aprovação não vê parágrafo; as quatro provas seguem publicadas e precisam de amostra nova.
Ficam como estão: o poema em duas colunas com números de verso do PF 2012 (agente g12,
papiloscopista g8; próximos passos) e os endereços de correspondência.
