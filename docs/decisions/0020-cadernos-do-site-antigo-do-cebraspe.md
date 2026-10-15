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

## Emenda de 2026-10-14 (10) — segunda língua estrangeira, texto invisível, crédito da figura do item; estilo no CBM/AL 2017

**Contexto.** O minos (semente r15) reprovou três provas publicadas. CBM/AL 2017 básicos cargo 2:
os itens 6–12 traziam no enunciado o bloco inteiro de LÍNGUA INGLESA da pág. 1 (texto, crédito e
itens 1–5), e faltava negrito/itálico (crédito "As veias abertas da América Latina", q14, q16, q18,
q26, o poema "Lily Braun"). CBM/AL 2017 específicos cargo 2: *Aedes aegypti* sem itálico (q110).
PC/SE 2018 conhecimentos gerais: a q1 virou "Texto *1* A existência da polícia… Em outras" sem
texto-base, e o texto-base das q12–14 começava com uma linha "Texto" que não está no caderno.

**Decisão.**

1. Itens de antes de `first_number`: a contagem dos pulados recomeça em 1 quando um "1" na margem
   vem depois de um comando ("judge", "juzgue"): é a outra língua estrangeira (espanhol e inglês,
   itens 1 a 5 cada, antes do item 6). Sem comando antes, o "1" é número de linha do texto-base e
   não recomeça nada.
2. Linha em branco (`color` 0xFFFFFF) sem figura desenhada atrás é invisível e sai do fluxo
   (`_visible`), depois de as figuras serem atribuídas às linhas: a marca de figura que ela tenha
   recebido passa à linha seguinte da mesma coluna. No PC/SE 2018, o "Texto" em 5 pt acima de
   cada texto-base. Texto branco sobre faixa desenhada (títulos) segue como antes.
3. No certo/errado, "Fonte: …" em letra miúda logo depois de um item cuja última linha recebeu a
   figura é o crédito dela e continua o item (`FIGURE_SOURCE`); antes abria um grupo novo com
   "Fonte: IBGE" de comando (CBM/AL 2017 específicos cargo 1, itens 93–96).
4. `infer_font_styles` ligado nas quatro provas do CBM/AL 2017.

**Verificação.** Varredura das 135 provas do staging, parser do HEAD × novo, com as mesmas
páginas: o item 1 muda só o CBM/AL 2017 básicos cargos 1 e 2 (itens 6–12); o item 2 muda o PC/SE
2018 gerais (q1–q7 e g8/g12 sem "Texto"; q2–q7 saem de `review`), o "-- PROVA DE REDAÇÃO --" colado
na alternativa D da q50 do CBM/TO 2021 oficial e soldado (em `review`), três textos-base `\<X>`
soltos do PM/TO 2020 QPE (g31, g36) e QPPM (g56), sem questão, e um parágrafo vazio no fim de
textos do CBM/TO 2022 oficial (1A1-I) e do PC/PB 2021 cargo 6 (6A1-II, 6A1-III) e delegado
(CG1A1-II); o item 3 só o CBM/AL 2017 específicos cargo 1 (q93–q96; q94–q96 saem de `review`,
a q93 segue pela figura). Com o estilo, o CBM/AL 2017 ganha a marcação pedida; as tabelas das
q73–q76 e q81–q83 do específicos cargo 2 mudam de corte, todas em `review`.

Fica de fora: o CBM/AL 2017 básicos cargo 1 segue fora (itens 49 e 50 perdidos depois das
proposições "P:"/"Q:" do item 48; gabarito com 45 itens para 43 questões).

## Emenda de 2026-10-14 (11) — estilo no CBM/TO 2021; título sem ponto antes; aspa no item

**Contexto.** O minos (semente r17) reprovou duas provas publicadas pela impressão da versão 1:
o CBM/TO 2021 oficial saía sem nenhum itálico nem negrito (o manifesto não tinha
`infer_font_styles`: *Crescentia cujete*, *gaapi*, *kipu-wahro* e o crédito do 1A1-I com
"**O que contam os quintais…**", "*In*", "*et al.*", "**Vozes Vegetais**"; o crédito em negrito
da q47), e o PC/PB 2021 gerais 14 a 17, q5, gravava o item III em dois parágrafos
("III “a cultura da violência que nos desumaniza a todos”" | "(décimo segundo período).").

**Decisão.**

1. `infer_font_styles` ligado no CBM/TO 2021 oficial e soldado.
2. Linha só em negrito, curta e sem pontuação final, em corpo de título (`HEADING_MIN_SIZE`)
   maior que o da alternativa, encerra a última alternativa mesmo que ela não termine em ponto
   (`_heading_after_option`): "D Facebook" | "**Normas relativas ao CBMTO**" (15 pt, no alto da
   coluna seguinte), CBM/TO 2021 soldado q40. Em corpo de texto continua valendo a exigência do
   ponto (item 4 da emenda (8)).
3. No item com recuo pendente ou no bloco recuado (`_indented_block_goes_on`), linha anterior
   terminada em aspa de fechamento continua o item quando a seguinte começa com "(" ou minúscula
   (a localização do trecho citado); com maiúscula ou aspa nova, parágrafo próprio, como antes.

**Verificação.** Varredura das provas do staging, parser do HEAD × novo, com as mesmas páginas:
os itens 2 e 3 mudam só o PC/PB 2021 gerais 14 a 17 (q5) e, com o estilo ligado, o CBM/TO 2021
soldado q40 (título sai da D) e q10 e oficial q15 (o título "Matemática"/"Física" em negrito sai
da D; q10 do soldado e do oficial perdem a pendência de layout). O estilo muda, no oficial, os
textos 1A1-I e 1A3-I a 1A3-IV e as q6, q10, q13, q15, q17, q19, q22–q25, q28, q29, q31, q32,
q47 e q48 (variáveis em itálico nas fórmulas, crédito em negrito); no soldado, o texto 2A1-I e as
q6, q9, q10, q13, q15, q19, q30, q31, q34, q36–q38, q40 e q46 (termos estrangeiros em itálico,
`.pst`/`filetype:pdf` como código). Pontuação colada ao termo itálico fica dentro da marcação
quando a fonte é a mesma ("*kipu-wahro.*", "3*i,*").

## Emenda de 2026-10-14 (12) — estilo que o Distiller põe no nome da fonte

**Contexto.** O minos (semente r18) reprovou o CBM/TO 2021 soldado: q36, alternativa D,
"Gerenciador de *downloads*" saía sem itálico. A palavra está na fonte `TT14422oI00`. Quando a
TrueType não tem a face do estilo pedido, o Distiller simula o estilo (inclina a face normal) e
marca no nome: "oI00" itálico, "oB00" negrito. O padrão de fonte sem nome (`TT…o00`) não casava
com esses nomes, e as larguras, que são as da face normal, também não denunciariam o estilo.

**Decisão.**

1. Fontes `TT<hex>o00`, `TT<hex>oI00`, `TT<hex>oB00` e `TT<hex>oBI00` são todas fontes sem nome.
   O estilo do nome (`I` itálico, `B` negrito) soma-se ao que as larguras ou o desenho derem para
   a face de base, mesmo com letras de menos. A fonte simulada não serve de âncora para o desenho
   dos glifos (desenha os da face normal).
2. A letra da alternativa em fonte com estilo ("*E* intranet.", PC/PB 2021 gerais 14 a 17) sai do
   corpo como a letra em negrito já saía.

**Verificação.** O corpus inteiro (`data/raw/`) tem 11 PDFs com fontes "oI00" e nenhum com
"oB00". Com o estilo ligado (ou no site antigo), mudam só: CBM/TO 2021 soldado q36 ("*downloads*");
CBM/TO 2021 oficial q16 e q18 (variáveis das alternativas: "*h*/2.", "2*g*sen(*α*)."); CBM/AL
2017 básicos cargo 2 q48 ("Se *k* é um número primo"); PF 2012 escrivão q29 ("servidor *proxy*").
No PC/PB 2021 gerais 14 a 17, no PF 2025 papiloscopista específicos, no PC/MA 2017 cargo 5 e no
PC/PE 2023 P2 cargo 3 a fonte "oI00" só tem a letra da alternativa, pontuação ou símbolo: nada muda.

## Emenda de 2026-10-14 (13) — título de figura em negrito

**Contexto.** O minos (semente r20) reprovou o CBM/PA 2023 CFP P1 por falta de marcação (título do
poema e crédito do texto 1A1, "*debye*" na q32): o manifesto não tinha `infer_font_styles`. Ligado
o estilo, o título "**Figura 1A03**" (pág. 7, abre a coluna) passou a ser lido como título de bloco
em negrito e saiu do fluxo; as questões 36–40 perderam o texto-base. O mesmo já acontecia no PM/TO
2020 QPE (q51–57, "**Figura 1A5-I**" a "**Figura 1A5-III**", partituras), que ia para `review` por
"texto-base não encontrado".

**Decisão.**

1. Linha que é o título de um texto-base (`TITLE_LINE`: "Figura 1A03", "Tabela 2A1", "Caso
   hipotético 1A06-I") não é título de bloco, mesmo só em negrito.
2. Texto-base cujo corpo é só esse título (o conteúdo era imagem) marca a questão com `figure`:
   vai para `review` ("figura ou tabela não extraída"), nunca publicada sem a figura.

**Verificação.** No `data/staging/` inteiro, só duas provas têm título de figura/caso/proposição
em negrito que não é "Texto X" e cuja saída muda: CBM/PA 2023 CFP P1 (g36 volta, q36–40 em `review`
pela figura) e PM/TO 2020 QPE (g51, g54, g56; q51–57 continuam em `review`, agora pela figura).
PC/MA 2017 gerais 1 e 2, PC/PB 2021 cargos 5, 12 e 13, PC/PE 2023 P2 cargo 1 e PM/RO 2022: saída
idêntica.

## Emenda de 2026-10-14 (14) — indicador ordinal sobrescrito

**Contexto.** O minos (semente r22) reprovou o PC/PB 2021 escrivão específicos: q50 e q52 (pág. 7)
saíam com "Lei n.o 10.826/2003", e o original tem o ordinal sobrescrito ("n.º"). No PDF o "o" é um
span próprio da mesma fonte, em corpo 6,5 sobre 10, com a marca de sobrescrito da fonte e a linha de
base 4,6 pt acima. Outros cadernos do corpus já trazem o glifo "º" e saem certos (PC/RJ 2021, PC/RO
2022); só o grau ("800 ºC") tinha tratamento para o "o" sobrescrito.

**Decisão.** No `extract`, um span "o", "a", "os" ou "as" sobrescrito — com a marca de sobrescrito
da fonte, ou em corpo pelo menos 1,5 pt menor com a linha de base acima da do span anterior — vira
"º", "ª", "ºs", "ªs" quando o texto anterior termina em "n."/"N." ou "n"/"N" isolado, em número
com ponto ("1.", "12.") ou em "§ 1"; e quando o que vem depois não é letra colada. Fica de fora,
de propósito: número sem ponto ("30o", "α + 2o": ângulos no CBM/TO 2021 soldado), letra qualquer
("Vo", "Ka": índices, que nem sobem da linha de base) e o texto de OCR (sem corpo nem posição de
glifo; no PC/DF 2020 básicos, o "n.o" está só nas justificativas, que não são gravadas). Nenhuma
troca de "n.o" pelo texto: só o glifo sobrescrito conferido no PDF.

**Verificação.** As 135 provas do `data/staging/` reprocessadas com e sem a regra (extract,
segment, validate): só mudam "n.o" → "n.º", "n.os" → "n.ºs", "1.o"/"5.o" → "1.º"/"5.º" e "No" →
"Nº", em PC/PB 2021 escrivão (q41–52), cargo 3 (q45–51, 53, 56, 72) e cargo 1 (q52, 62); PF 2018
agente, escrivão e papiloscopista (q38–40; escrivão também o texto-base g97, "1.º/7/20x0"); PF
2025 escrivão específicos (q110); PC/MA 2017 escrivão específicos (q31, "art. 5.º"); PM/SC 2023
soldado (texto-base 1A5-III, "OFÍCIO Nº"). No PC/PE 2023 P1 cargo 2 e no CBM/AL 2021 oficial
mudam só linhas que não são gravadas (justificativa, prova discursiva). Fixture
`pcpb-2021-escrivao-p7.pdf`.

## Emenda de 2026-10-14 (15) — monoespaçada em palavra curta; "P:"/"Q:" no item

**Contexto.** O minos (semente r23) reprovou o PF 2018 papiloscopista: na pág. 5, "Bcc" (q61) e
"no" (q65, "tem o sentido da preposição no") estão em Courier e saíam sem código inline. A fonte
sem nome (`TT1A61o00`) só tem essas 4 letras no caderno, todas com 0,599 corpo, e `_mono_fonts`
pedia 8 letras distintas para afirmar que a fonte é monoespaçada. No PF 2018 agente a mesma fonte
tem letras bastantes e já saía certa. Também do STATUS (item 2): no CBM/AL 2017 básicos cargo 1, o
item 48 traz as proposições "P: ..." e "Q: ..." recuadas (36,9 pt), e o "Q:", depois de "planeta.",
era lido como o começo do texto-base seguinte; sem comando nele, os itens 49 e 50 não abriam e o
gabarito tinha 45 itens para 43 questões.

**Decisão.**

1. Fonte sem nome com menos de 8 letras distintas é monoespaçada se tem ao menos 3 letras
   distintas e todas medem a largura da Courier (0,600 corpo, ±0,005). Nenhuma letra das Times e
   Helvetica (as referências de `_font_styles`) cabe nessa margem; com 1 ou 2 letras (o "V"/"F"
   de uma tabela-verdade em Courier, PC/PB 2021 agente) a fonte continua de fora.
2. Vírgula de frase no fim de um trecho monoespaçado, com texto comum depois dela na mesma linha
   (".gif, " | "para então", PC/PB 2021 gerais 4 a 13, q12), sai do código: "`.gif`, para". No fim
   da linha (código SQL em linhas, "id_tabela INT,", PF 2025 bloco II g91), a vírgula é do código.
3. No item certo/errado, linha que começa com proposição rotulada ("P:", "Q:", "R:", "S:", com ou
   sem índice, ou "C:") continua o item quando outra linha do mesmo item, na mesma página e coluna,
   também começa com rótulo e com a mesma margem (±2 pt), mesmo recuada depois de frase fechada
   (`ITEM_PROPOSITION`, em `_continues`). Não muda o parágrafo (o `PROPOSITION` da emenda (8) segue
   sem "P:"/"Q:": o comando "...acerca da seguinte proposição:" | "P: ..." do PF 2018
   papiloscopista continua inteiro).
4. `cbmal-2017` básicos cargo 1: `raciocinio-logico` vai de 48 a 50 no `subjects_by_range`.

**Verificação.** As 135 provas do `data/staging/` reprocessadas com o código do HEAD e com o novo
(extract, segment, answer-key, validate; as 4 do `pcpe-2016` não têm staging): mudam só PF 2018
papiloscopista (q61 "`Bcc`", q65 "`no`"), PC/PB 2021 gerais 4 a 13 (q12, alternativa E: "`.gif`,"
e "`.pdf`"), PC/RO 2022 específicos cargo 1 (q36, alternativa D: "`.mil`.") e CBM/AL 2017 básicos
cargo 1 (q48 inteira com "Q: ..." e "Nesse caso, ... equivalentes."; q49 e q50 novas; 45 itens
para 45 questões). O q48 passa de "texto solto" a "figura não extraída": dois retângulos brancos
sem traço atrás da linha "Nesse caso, ..." contam como desenho (fica em `review`; filtrar desenho
branco mexe em todas as provas e fica para depois). Fixtures `pf-2018-papiloscopista-p5.pdf` e
`cbmal-2017-basicos-cargo-1-p4.pdf`.

## Emenda de 2026-10-14 (16) — fecho do crédito partido em duas linhas; figura que abre a página

**Contexto.** O minos (semente r24) reprovou o CBM/AL 2017 básicos cargo 1: o crédito do texto
CB1A1AAA (pág. 2) saía em dois parágrafos, quebrado antes de "*In*:". As três linhas do crédito
começam no mesmo x; a primeira termina em ponto ("... do desarmamento**.") e o "(com" fica no fim
da segunda, com o "adaptações)." na terceira. Nenhuma linha casava `CREDIT_END` sozinha, e o
ponto impedia `_credit_line_wraps`. Fora da amostra, no mesmo caderno, o item 40 (pé da pág. 3)
levava "Na figura precedente, o retângulo ABCD tem as seguintes", primeira linha do texto-base das
questões 41 a 44, que abre a pág. 4 logo abaixo da figura, com recuo de parágrafo (17,7 pt) igual
ao de continuação de item; o texto-base começava em "propriedades:".

**Decisão.**

1. Uma linha de crédito encerra o crédito quando casa `CREDIT_END` sozinha ou quando, junto da
   linha de crédito de cima (mesmo corpo miúdo, recuada), casa um fecho que começa na de cima
   ("(com" | "adaptações).") e a de cima não fecha nada sozinha (`_credit_closes`). Vale onde o
   fecho decide o parágrafo: `_credit_goes_on`, `_paragraphs` e `_choice_paragraphs`.
2. No item certo/errado, a primeira linha de uma coluna nova (página ou coluna diferente da última
   linha do item) logo abaixo de uma figura que abre a coluna, começando com maiúscula, não
   continua o item cuja frase já terminou (`_Entry.below_figure`, em `_continues`): é o texto-base
   do grupo seguinte, e a figura vai com ele.

**Verificação.** As provas do `data/staging/` resegmentadas (segment, answer-key, validate) com o
código do HEAD e com o novo: muda só o CBM/AL 2017 básicos cargo 1 (texto CB1A1AAA, questões 6, 8,
9, 10 e 18: crédito num parágrafo só; q40 termina em "objeto apresentado."; o texto-base g41 das
questões 41 a 44 começa em "Na figura precedente" e passa a levar a marca de figura). O básicos
cargo 2 (soldado) usa outro texto (CB2A1AAA), com o crédito já inteiro.

## Emenda de 2026-10-14 (17) — estilo no PM/MA 2017 e no CBM/PA 2023 CFO; itálico de poucas letras; item com recuo pendente no certo/errado

**Contexto.** O minos (semente r25) reprovou, por estilo perdido: PM/MA 2017 gerais cargo 5 (q40,
crédito "**Educação do campo e território**", "*campus*"; texto das q49–51, "**Formação econômica
do Maranhão**") e específicos cargo 5 (q118, "*ransomware*", "*worm*"), e CBM/PA 2023 CFO P1 (q13
e q14, "*Trypanosoma cruzi*"), provas sem `infer_font_styles`; e PC/PE 2023 P1 cargo 1 (q14,
"*blitz*"), que já tem a opção ligada. No PC/PE, "blitz" está numa fonte "TT…o00" própria de 5
letras, abaixo das 6 de `_small_font_style`, e a página não tem itálica deduzida com que casar o
desenho. No PM/MA específicos (texto das q117–120, situações I a III) e no CBM/AL 2017 básicos
cargo 1 (texto das q41–44, "• o ponto F ... entre EB e" | "EF mede 45º;"), cada linha recuada de
item com recuo pendente virava um parágrafo: a regra da múltipla escolha
(`_indented_block_goes_on`) não valia no texto-base do certo/errado.

**Decisão.**

1. `infer_font_styles: true` nas três provas do PM/MA 2017 e na P1 do CBM/PA 2023 CFO.
2. Só com `styles` (no `legacy`, os índices miúdos do PF 2012 papiloscopista, "*v*max", sairiam
   itálicos): fonte sem estilo deduzido que tem pelo menos 3 glifos de mesmo nome que uma fonte
   normal já deduzida (mesma `FontMatrix`) e desenha **todos** de outro jeito não é a face normal;
   com pelo menos 4 letras distintas, o estilo vem das larguras: a referência não normal mais
   próxima até 0,008 corpo e todas as normais pelo menos 0,006 além; das referências não normais
   dentro dessa margem da melhor, vale o estilo comum (Times itálico e negrito itálico medem igual
   "blitz": itálico). Sem estilo comum, nada.
3. No texto-base do certo/errado (`_paragraphs`, sem numeração de linhas), a linha recuada continua
   o item rotulado (I, II; a), b); •) aberto acima — na margem ou já recuado — quando fica além do
   rótulo (6 a 30 pt), no mesmo recuo da linha anterior do item, na mesma página e coluna, e a
   anterior vai até a margem direita e deixa a frase aberta (letra, vírgula ou travessão) e a
   linha começa por letra. Tabela e título recuados, sem item rotulado, seguem separados.

**Verificação.** Todas as 135 provas do `data/staging/` reprocessadas (extract → validate) com o
código do HEAD (388a4ea) e com o novo, e comparadas. Mudam: PM/MA 2017 específicos cargo 5 (q62,
q87, q88, q93, q101–112, q117–120; textos g108 e g117), gerais cargo 5 (q1, q13; g15, g39, g49) e
gerais cargo 1 (q7, q9, q57–60; CG1A1AAA, CG1A1BBB, g36, g38, g41, g49, g53), só marcação fora o
g117; CBM/PA 2023 CFO P1 (q1, q6, q10, q17–19, q22, q25, q28, q32, q35–37, q39, q40, q42–45; 1A1-I,
1A2-II, 1A6, g16, g18): marcação e, com os títulos de disciplina agora em negrito, "FÍSICA",
"QUÍMICA" e "BIOLOGIA" saem do fim de q32, q39 e q25 (cada uma perde a marca "layout"), o
"MATEMÁTICA E RACIOCÍNIO LÓGICO" sai do texto g16 (q17 acha o texto-base) e a régua do cabeçalho
"LÍNGUA INGLESA" deixa de ser figura da q10; CBM/AL 2017 básicos cargo 1 (g41); PF 2012 agente
(g76, g83; q83 e q84: o item III inteiro passa do texto-base ao começo do comando, em vez de partido
entre os dois, e as duas perdem a marca "layout"); PC/PE 2023 P1 cargo 1 (q14) e PC/MA 2017 APC
gerais cargo 5 (q16, "*mouse*").

## Emenda de 2026-10-14 (18) — item seguinte da lista; item partido antes de número; crase no comando

**Contexto.** Reprovação do minos (semente r26) no PF 2012 agente, itens 83 e 84: o texto-base
terminava no item II, partido ("... relativos ao mês de abril de" | "2012, no valor de R\$
1.800,00;"), e os itens III e IV vinham colados ao comando "À luz do regime de caixa ..., julgue
...". Três causas: (a) a linha em recuo pendente que começa por algarismo não continuava o item
(a emenda (17) só aceitava letra ou travessão); (b) o III vai até a margem direita e termina em
";", e o IV, na mesma margem, não abria parágrafo (nem recuo, nem linha curta, nem espaço); (c) o
corte de frase de `_split_command` (`SENTENCE_END`) não conhecia o "À" maiúsculo, e a frase do
comando engolia o item IV.

**Decisão.**

1. No texto-base do certo/errado, a linha em recuo pendente que começa por algarismo continua o
   item rotulado quando a anterior termina em letra (frase aberta antes de um número).
2. Linha que começa com o rótulo seguinte da lista aberta (I → II, III → IV; a) → b)), na mesma
   margem do rótulo que abriu o parágrafo, abre parágrafo quando a anterior fecha o item (".", ":",
   ";", "?", "!"). Fora da sequência, noutra margem ou com o item aberto, nada muda.
3. `SENTENCE_END` inclui o "À" maiúsculo (a crase; o português não usa outro acento grave).

**Verificação.** As 140 provas do `data/staging/` segmentadas com o código do HEAD (824ba1a) e com
o novo, a partir do mesmo `pages.exam.json`, e comparadas. Mudam só: PF 2012 agente (g83 passa a
ter a introdução e os itens I a IV, cada um em seu parágrafo, com o II inteiro; q83 e q84 começam
no comando "À luz ...") e PM/DF 2025 P2 (g80: "b) ...;" e "c) ..." passam a parágrafos separados).

## Emenda de 2026-10-15 (19) — linha centralizada na múltipla escolha; frase inteira em negrito no item; estilo no PRF 2021

**Contexto.** Reprovação do minos (semente r30) no PM/SC 2023 oficial, questão 66: a fórmula
centralizada em linha própria ("((P ˄ S) → (Q ˅ R)) → ((~R ˅ P) → (~Q ˅ ~S)") saía no mesmo
parágrafo do comando "O número de linhas da tabela-verdade...". Ela não termina em ponto, sobra
34 pt à direita (menos que `SHORT_LINE`) e o enunciado tem linhas de menos para medir o
entrelinha: nenhuma regra de `_choice_paragraphs` abria parágrafo. A questão 67, com a citação
recuada e a última linha curta, já saía certa. Na preparação da reamostragem do PRF 2021 policial
(estilo ligado), o exemplo em negrito do item 26 ("... conforme o exemplo a seguir." |
"**Assunto: Realização de concurso público.**") encerrava o item como título de bloco e ia para o
começo do texto-base seguinte.

**Decisão.**

1. Linha **centralizada** na coluna — recuo da esquerda e sobra da direita maiores que o recuo de
   parágrafo (15 pt) e iguais até 3 pt — é um parágrafo próprio no enunciado da múltipla escolha:
   a linha seguinte, na margem e em maiúscula, abre outro. A primeira linha de parágrafo (só o
   recuo da esquerda) não é centralizada.
2. Linha só em negrito que termina em ponto não é título de bloco e não encerra o item (título de
   bloco não tem ponto final, como em `_bold_heading`). No item, a linha inteira em negrito depois
   de linha curta de frase terminada é parágrafo próprio, e a linha seguinte abre outro, como a
   linha só de código (emenda (5)).
3. `infer_font_styles: true` no PRF 2021 policial e língua inglesa. Nas outras provas do lote de
   reamostragem (PF 2021 agente, escrivão e papiloscopista; PM/TO 2020 QPPM) a opção não muda nada:
   as fontes "TT…o00" desses cadernos só aparecem na prova discursiva, e o estilo da objetiva já vem
   das fontes com nome; os manifestos ficam como estão.

**Verificação.** As 135 provas do `data/staging/` segmentadas com o código do HEAD (1684ce2) e com
o novo, a partir do mesmo `pages.exam.json`, e comparadas. A regra 1 muda só: PM/SC 2023 oficial
(q66), PC/PB 2021 específicos cargo 13 (q62, equação química centralizada antes de "Do ponto de
vista termodinâmico...") e PC/RO 2022 específicos cargos 1 e 4 (q57, a última linha da tabela
centralizada antes do comando). A regra 2 não muda nenhuma prova já com estilo. Com o estilo, o
PRF 2021 policial muda só marcação em q15, q18, q19, q22–q30, q32–q39, q64, q80, q97, q102, q120 e
nos textos 1A18-I, g27, g43 e g100, mais o parágrafo próprio do "**Assunto: ...**" no item 26; a
língua inglesa, só q7 ("**Even so**").

## Emenda de 2026-10-15 (20) — faixa atrás do título de bloco; negrito pela tinta; estilo no DEPEN 2020

**Contexto.** Itens do STATUS: no CBM/TO 2021 soldado, a questão 30 (pág. 6) ficava em `review`
com "figura não extraída": o título "Noções de Informática" (corpo 15) vem numa faixa cinza
desenhada logo depois da alternativa D, e a faixa contava como figura da questão de cima (o texto
do título já não ia para a alternativa desde a emenda de 2026-10-14). No PM/SC 2023 soldado,
texto 1A5-III (pág. 7), o ofício vem num Calibri convertido pelo Distiller ("TT…o00"): as
larguras não são as do Times nem as da Helvetica, nenhuma face é deduzida, e "Assunto" e
"Solicitação de senha.", em negrito no PDF, saíam sem negrito (a emenda (19) não tratava disso).
Na preparação do lote 2 da reamostragem v1 → v2 (CBM/AL 2021 oficial, PC/AL 2021 agente, DEPEN
2020 agente, PC/SE 2018 específicos, PC/DF 2026 P1, PC/DF 2020 básicos), o estilo ligado só muda
o DEPEN 2020.

**Decisão.**

1. Desenho que contém inteira uma linha em corpo de título (`HEADING_MIN_SIZE`) sem pontuação
   final e não passa dela mais que 4 pt em cima e embaixo é a faixa de fundo do título: não é
   figura (`_title_band`, em `_with_figures`). Desenho mais alto, ou atrás de linha em corpo de
   texto, segue marcando.
2. Só com `styles`: fonte sem nome ainda sem estilo depois das regras anteriores é negrito quando,
   contra uma face de texto (fonte sem nome com pelo menos 20 letras, normal ou sem estilo
   deduzido), em pelo menos 4 letras em comum, desenha bem mais tinta — área do contorno do glifo
   por corpo², mediana da razão ≥ 1,3 e cada letra ≥ 1,15 — e as larguras de cada letra ficam
   entre 0,97 e 1,15 das da face de texto (mesma família; outra família sai da faixa). O itálico
   desenha a mesma tinta e não casa; nada além do negrito se deduz assim (`_bold_by_ink`).
3. `infer_font_styles: true` no DEPEN 2020 agente. Nas outras cinco provas do lote a opção não muda
   nada (no PC/AL 2021 agente as fontes "TT…o00" só aparecem na prova discursiva, págs. 8 e 9;
   CBM/AL 2021, PC/SE 2018 e PC/DF 2026 não têm fonte sem nome; o PC/DF 2020 básicos é OCR); os
   manifestos ficam como estão.

**Verificação.** As 135 provas do `data/staging/` reprocessadas (extract → validate) com o código
do HEAD (317bf8f) e com o novo, e comparadas. A regra 1 muda: CBM/TO 2021 soldado (q30 sai de
`review`), CBM/AL 2021 oficial (faixas de "Língua Estrangeira (Inglês)", "Noções de Informática",
"Ética, Cidadania e Direitos Humanos" e "Legislação pertinente ao CBMAL": g16, q16–q21 e q56–q65
perdem a marca de figura; q56–q65 saem de `review`) e soldado (g31, q31–q44, q100 e q110 perdem a
marca; q110 sai de `review`); o resto das marcas dessas provas (fórmula, layout) fica. A regra 2
muda só o PM/SC 2023 soldado (texto 1A5-III, "**Assunto**: **Solicitação de senha.**"), e com o
estilo ligado em todas as 135 provas também só ela. Com a regra 3, o DEPEN 2020 agente muda
marcação em q51 (*shopping*), q55 (*habeas corpus*), q89 (**Situação hipotética**), q117
(*parquet*), q119–q120 (**Manual de Assistências do Sistema Penitenciário Federal**), e a faixa
"-- CONHECIMENTOS COMPLEMENTARES --" deixa de ser o texto-base g81 das q81–q82. Páginas conferidas
renderizadas: DEPEN 2020 págs. 5, 7 e 8; CBM/TO 2021 soldado pág. 6; CBM/AL 2021 oficial págs. 3
e 6 e soldado págs. 4 e 8; PM/SC 2023 soldado pág. 7. Fixture `pmsc-2023-soldado-p7.pdf`.

## Emenda de 2026-10-15 (21) — proposições rotuladas no item; corpo do crédito no OCR

**Contexto.** Reprovações do minos (semente r32). No CBM/AL 2021 soldado, item 86 (pág. 7), o
item traz "Considere as seguintes sentenças." | "S1: ..." | "S2: ..." (partida em duas linhas) |
"Sendo as sentenças S1 e S2 verdadeiras, ..." e saía num parágrafo só: o enunciado do item
certo/errado só abria parágrafo por linha de código, linha em negrito e correspondência; a regra
de linhas com rótulo da emenda (8) (`_labeled_line_opens`) vale no texto-base e na múltipla
escolha, não no item, e o `PROPOSITION` dela nem tinha "S1:". No PC/DF 2020 básicos (prova OCR),
o crédito do texto da pág. 2 ("Raduan Nassar. **Aí pelas três da tarde**. *In*: ... **Os cem
melhores**" | "**contos brasileiros do século**. ... (com adaptações).") saía em dois parágrafos:
o corpo das duas linhas vem da altura da caixa do OCR (5,2 e 4,7; a de cima tem "Í" e negrito), e
as regras de crédito pedem o mesmo corpo. O crédito do Harari, na mesma prova, tem 4,7 nas duas.

**Decisão.**

1. No item certo/errado, com duas ou mais linhas começando com proposição rotulada
   (`ITEM_PROPOSITION`: "P:", "Q:", "S1:", "C:"...) na mesma margem (±2 pt), página e coluna,
   a linha rotulada abre parágrafo depois de frase fechada ou de outra proposição, e a primeira
   linha sem rótulo, em maiúscula, depois de proposição terminada em ".", "?" ou "!", também
   abre — quando a anterior é curta, o corpo muda ou há espaço de bloco (`_proposition_breaks`).
   Proposição solta ("... a seguinte proposição:" | "P: ...", PF 2018 papiloscopista) segue no
   parágrafo.
2. `PROPOSITION` (texto-base e múltipla escolha) aceita "Q1:", "R1:", "S1:" além de "P1:"; sem
   índice continua de fora.
3. Na página de OCR (`_Entry.ocr`), duas linhas miúdas são do mesmo corpo de crédito com até 20%
   de diferença do corpo menor (`_same_credit_size`, em `_credit_line` e
   `_credit_right_aligned`). No PDF com texto o corpo continua exato.

**Verificação.** As 140 provas do `data/staging/` segmentadas com o código do HEAD (360d254) e com
o novo, a partir do mesmo `pages.exam.json`, e comparadas. A regra 3 muda só o PC/DF 2020 básicos
(texto g1: o crédito num parágrafo só, "**Os cem melhores contos brasileiros do século**"). A regra
1 muda só: CBM/AL 2021 soldado (q86), CBM/AL 2017 básicos cargo 1 (q48: "P: ...", "Q: ..." e
"Nesse caso, ..." em parágrafos próprios) e PF 2025 bloco I (q55: "P: “...”", "Q: “...”" e "Com
base nessas proposições, ..."). A regra 2 não muda nenhuma prova.

## Emenda de 2026-10-15 (22) — recuo na linha numerada; margem do texto numerado por coluna

**Contexto.** Reprovação do minos (semente r34) no PM/AL 2018, texto 1A1-I ("Dói. Dói muito…",
pág. 1): o texto tem 4 parágrafos, e o 2.º e o 3.º saíam juntos. A linha 13 ("Há que experimentar
o prazer…") abre parágrafo com recuo de primeira linha (x≈81 contra 46), depois de uma linha que
vai até a margem direita; o item 2 cita o "terceiro parágrafo". O número de linha da margem vem
numa linha própria do PDF e `_merge` o une ao texto: a linha unida começa no x do número, e
`_strip_line_numbers` a punha na margem do corpo, perdendo o recuo. A regra do recuo já existia
(`indented` em `_paragraphs`); faltava a posição. Na mesma varredura, duas falhas vizinhas da
margem do texto numerado, que era uma só para o texto inteiro: (a) no PM/AL 2017 básicos, o
comando "Com relação às ideias do texto CB1A1AAA, julgue os itens que se" | "seguem." abre a coluna
da direita; contra a margem do texto da coluna da esquerda as duas linhas pareciam recuadas,
viravam dois parágrafos, e `_split_command` só via o "seguem.": o comando ficava no texto-base,
marcado `no_command`, os itens 1 a 6 ficavam sem ele no enunciado e os 14 itens do texto iam para
`review` ("grupo de itens sem comando reconhecido"); (b) no PC/MA 2017 delegado,
texto CG1A1AAA, o texto numerado continua no alto da coluna da direita, com margem própria
(x≈322): os números 46, 49 e 52 não eram tirados e cada linha virava um parágrafo.

**Decisão.**

1. `Line.body_x0` (extração): quando `_merge` une à linha um número sozinho na frente (número de
   linha ou de item), guarda o x0 do texto depois dele. `_strip_line_numbers` põe a linha no
   `body_x0` em vez da margem (se ele não fica à esquerda da margem), e o recuo de primeira linha
   abre parágrafo como nas linhas sem número, mesmo depois de linha cheia. Sem `body_x0` (OCR,
   `pages.json` antigo), a margem, como antes.
2. A margem do corpo do texto numerado vale por página e coluna (`_column_bases`: o x0 mais comum
   ali, no empate o menor). A coluna sem linha numerada usa a própria margem, como texto sem
   numeração.
3. Texto já numerado que continua noutra coluna ou página com margem própria: o número na frente
   da linha sai contra a margem dali (linhas sem número), se seguir a numeração já tirada (maior
   que o último, até 10 adiante). Fora da sequência ("2020 foi…") fica no texto.

**Verificação.** As 135 provas do `data/staging/` reprocessadas (extract → segment) com o código do
HEAD (92a1330) e com o novo, e comparadas. Mudam só: PM/AL 2018 (texto 1A1-I: 4 parágrafos e o
crédito, o 3.º começando em "Há que experimentar"), PM/AL 2017 básicos (texto CB1A1AAA: "Lançadas
com o intuito…" (linha 13) e "O mito da criminalidade…" (linha 22) em parágrafos próprios; o
comando sai do texto e abre o enunciado dos itens 1 a 6; os itens 1 a 14 saem de `review`), PC/MA 2017
delegado (texto CG1A1AAA: os números 46, 49 e 52 saem e as oito linhas da coluna da direita viram
dois parágrafos, "Outro passo…" e "É, então…") e PC Científica/PE 2016 gerais (texto CG1A1AAA: "O
mundo não renunciou à guerra." (linha 10) em parágrafo próprio; prova não ingerida). Páginas
conferidas renderizadas: PM/AL 2018, PM/AL 2017 básicos, PC/MA 2017 delegado e PC Científica/PE
2016 gerais, pág. 1. Fixtures `pmal-2018-p1.pdf`, `pmal-2017-basicos-soldado-p1.pdf` e
`pcma-2017-delegado-p1.pdf`.

## Emenda de 2026-10-15 (23) — alternativa de linhas soltas; itálico pela inclinação do desenho

**Contexto.** Reprovações do minos (semente r39). No PC/PE 2023 P2 cargo 1, questão 50 (pág. 13,
coluna direita), cada alternativa traz quatro lançamentos, um por linha ("débito – despesas
bancárias" | "débito – despesa de juros" | "débito – conta-corrente bancária" | "crédito – títulos
a receber"), e as linhas saíam coladas com espaço: `_join` junta as linhas da alternativa como
texto corrido. No PC/PB 2021 específicos cargo 4, questão 70, alternativa E (pág. 4, coluna
esquerda), " code" de "QR *code*" vem numa fonte "TT…o00" própria (`TT37B42o00`, sem estilo no
nome nem `ItalicAngle`), com o estilo ligado: a regra da emenda (17) já via que a fonte desenha
"c", "o", "d", "e" de outro jeito que a face normal (`_not_upright`), mas as larguras dessas
letras são as mesmas no Times normal, itálico e negrito itálico, e `_few_letters_style` não
decidia (falta a margem para a face normal).

**Decisão.**

1. Alternativa da múltipla escolha com três ou mais linhas, na mesma página e coluna, sem marca
   (figura, fórmula, layout) nem texto invisível, em que cada linha menos a última termina antes
   de `SHORT_LINE` da margem direita da coluna, sem ".", "?", "!", ",", ";" ou ":" no fim, e a
   primeira palavra da linha seguinte, mais um espaço, caberia na sobra (largura estimada pela
   média por caractere da linha seguinte): as linhas são de propósito e saem com quebra de linha
   dura (`\` no fim, docs/content-format.md), como os versos (`_option_line_list`). Texto corrido
   (linha de cima até a margem), alternativa de duas linhas e linha que fecha frase não mudam.
2. Só com `styles`: fonte que não é a normal (`_not_upright`) e que as larguras não resolvem é
   itálica quando, contra cada face normal já deduzida com a mesma `FontMatrix` (sem inclinação na
   matriz) e pelo menos 3 letras desenhadas em comum (mesmo glifo, mesma letra pelo traço do
   texto), toda letra em comum inclina pelo menos 0,12 a mais (`StatisticsPen.slant` do contorno;
   no PC/PB o itálico do Times fica 0,2 a 0,3 acima da normal), e as larguras ficam até
   `SMALL_MAX_STYLE_DISTANCE` de uma referência itálica do Times ou da Helvetica
   (`_italic_by_slant`). Só o itálico se deduz assim: o negrito itálico sai itálico.

**Verificação.** As 135 provas do `data/staging/` reprocessadas (extract → segment → answer-key →
validate) com o código do HEAD (f1008a3) e com o novo, e comparadas. A regra 1 muda só: PC/PE 2023
P2 cargo 1 (q50, as cinco alternativas) e PC/PB 2021 específicos cargo 3 (q73, os lançamentos
"D – Fornecedores" | "C – Bancos conta movimento" | ... das cinco alternativas). A regra 2 muda só:
PC/PB 2021 específicos cargo 4 (q70 E, "QR *code*"), PC/PB 2021 específicos cargo 12 (q80,
"**Amostras** *loci*", negrito itálico no PDF), CBM/PA 2023 CFO P1 (q44, cabeçalho da tabela
"*n l m*l *m*s", negrito itálico no PDF) e PF 2018 escrivão (texto g41 e q43, "*N*", "*n*", "*P*",
"*P*pop", negrito itálico no PDF). Com o estilo ligado em todas as 132 provas fora do site antigo,
a regra 2 dá itálico também a fontes de variáveis e estados físicos no PF 2018 papiloscopista
("Ba(*s*)", "O2(*g*)", "Δ*H*") e na PC Científica/PE 2016 cargos 7, 8, 13 e 14 ("λMAX", "*i*",
"*j*", "*x*", "(*aq*)"), todas itálicas no PDF (os vetores "*i*", "*j*", "d*a*", em negrito
itálico); nenhuma dessas provas tem o estilo ligado. Páginas
conferidas renderizadas: PC/PE 2023 P2 cargo 1 pág. 13; PC/PB 2021 específicos cargo 4 pág. 4,
cargo 3 pág. 7 e cargo 12 pág. 8; CBM/PA 2023 CFO P1 pág. 9; PF 2018 escrivão pág. 4 e
papiloscopista pág. 9; PC Científica/PE 2016 cargos 7 (pág. 13), 8 (pág. 3), 13 (pág. 2) e 14 (pág. 6). Fixture `pcpb-2021-especificos-cargo-4-p4.pdf`.
