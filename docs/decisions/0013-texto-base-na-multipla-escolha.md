# 0013 — Texto-base na múltipla escolha só para quem o cita

**Data:** 2026-10-08 · **Marco:** M4 (publicação das provas)

## Contexto

O revisor de assuntos viu quatro questões com texto-base errado. A causa era uma regra do parser
de múltipla escolha: o texto aberto entre duas questões valia para **todas** as questões seguintes,
até a próxima abertura. Em 44 provas de múltipla escolha, 899 questões carregavam um texto que não
citavam (física em questões de medicina legal, texto de português em direito empresarial), e as
figuras desse texto mandavam questões sem figura para `review`. Além disso, PC/PE 2023 traz uma
tabela `||JUSTIFICATIVAS||` depois de cada questão, que o parser não reconhecia (plural, e a tabela
fica na margem): a justificativa da questão anterior virava o texto-base da seguinte.

## Decisões

1. Na múltipla escolha do Cebraspe, a questão que usa um texto o cita ("texto 2A1-I",
   "figura 5A2", "situação hipotética 12A3-I"). O texto-base vale para a **primeira questão depois
   dele** e para **as que citam o rótulo** (a chave ou o título da primeira linha do texto). As
   demais ficam sem texto-base.
2. Título de bloco em negrito ("**Atualidades e conhecimentos...**") entre questões não é texto-base.
3. A tabela `||JUSTIFICATIVAS||` passa pelo fluxo e a múltipla escolha pula tudo até o próximo
   título de questão; a regex aceita o plural.
4. Certo/errado não muda: o comando do grupo continua valendo para todos os itens do grupo.

## Consequências

- As 44 provas de múltipla escolha foram ressegmentadas e recarregadas; menos questões em
  `review` (as figuras do texto não se espalham mais).
- Questão que usa o texto sem citar o rótulo e não é a primeira do grupo fica sem texto-base.
  A amostragem por prova é onde isso aparece.

## Emenda de 2026-10-14 — texto sem rótulo e fim da última alternativa

O minos reprovou o `cbmro-2022/oficial` (semente r11): o texto da árvore (pág. 4, questões
23–26) e o da tabela das ligações (questões 28–30) não têm rótulo. O primeiro começa recuado no
alto da coluna seguinte à questão 22, o segundo logo abaixo da alternativa E da questão 27, e as
linhas iniciais grudavam na alternativa E (a última alternativa só terminava em linha de margem
começando com maiúscula). Mesmo separado, o texto valeria só para a primeira questão, e as
outras do grupo não podem citá-lo.

1. A última alternativa termina também na primeira linha com recuo de parágrafo (maior que o da
   continuação), longa e em maiúscula, depois de frase terminada (`_paragraph_after_option`).
2. Texto-base sem rótulo nem título, com 20 palavras ou mais, vale para a primeira questão depois
   dele e para as seguintes enquanto cada uma retomar um termo que o texto introduz (radical de
   5 letras ou sigla, fora dos termos genéricos de enunciado, que não aparece nas questões
   anteriores ao texto). A cadeia para na primeira questão que não retoma, ou que abre a sua
   própria situação: enunciado com recuo de parágrafo ou com figura (CBM/RO 2022 questão 27, o
   tanque). Texto rotulado segue a decisão 1.
3. Título de bloco em corpo de título (13,5 pt ou mais, sem pontuação final: "Normas relativas ao
   CBMTO") e título em caixa alta quebrado em duas linhas ("NOÇÕES DE DIREITO PROCESSUAL PENAL" /
   "COMUM", PM/SC 2023 soldado) não são texto-base.

Consequências: na varredura das provas de múltipla escolha mudaram `cbmro-2022/oficial`
(q22, q24–q30; as questões dos dois textos vão para `review` pela figura e pela tabela não
extraídas), `cbmto-2021` oficial (q35) e soldado (título solto), `cbmpa-2023-cfo/p1` (q17, que
cita a figura 1A3-I, ganha o texto; segue em `review`), `pmsc-2023-soldado/objetiva` (q17 perde o
título como texto-base; volta a `review` para reamostragem) e `pcientifica-pe-2016` (não
ingerida). A heurística de termos pode errar em grupos sem termo próprio; a amostra por prova é
onde isso aparece.

## Emenda de 2026-10-14 (2) — remissão com o rótulo colado

O PM/SC 2023 soldado grafa "do texto1A5-I" e "do texto1A5-II" sem espaço no próprio caderno
(q37 e q39); a remissão só era reconhecida com espaço entre a palavra do título e o rótulo, e as
duas questões ficavam sem texto-base. A palavra do título (texto, figura, tabela...) colada a um
rótulo da banca em maiúsculas ("1A5-I") conta como remissão, só na busca (`GLUED_REF`); o
enunciado guarda a grafia do caderno. Na varredura das provas do staging só essas duas questões
mudam (ganham o texto-base); nenhuma outra prova tem a grafia colada.
