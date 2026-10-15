# 2026-10-14 — Ciclo autônomo das 19:32: ordinal sobrescrito, estilo em lote e reamostragem v1 → v2

**Marco:** M5

Ciclo autônomo (decisão 0026), sem o dono. Coordenadora → hefesto/minos em turnos, nunca os
dois ao mesmo tempo no banco. Tudo carregado a partir do checkout principal (`main`), sem
worktree; cada carga foi feita sobre o HEAD anterior mais as mudanças que viraram o commit seguinte.
Crawl não rodou: o último foi 2026-10-14 10:25 (menos de 24 h). Deploy parado no budget (fila do
dono); `deploy/` e nuvem sem mudança, sem auditoria nova.

## O que foi feito
- **Correções do hefesto** (cada uma com testes e comparação do staging antes/depois em todas as
  provas):
  - `7c00e5d`: ordinal sobrescrito vira "º"/"ª" ("n.º", "n.ºs", "1.º", "Nº"), só pelo glifo no PDF
    (flag de sobrescrito ou corpo menor com base acima); ângulos ("30o") e OCR ficam como estão
    (emenda (14) da 0020). Fecha a reprovação r22. 9 provas recarregadas.
  - `d197fb2`: fonte monoespaçada com poucas letras (≥3, todas na largura da Courier) vira código
    inline; vírgula de frase sai do código; proposições "P:"/"Q:" com a mesma margem continuam o
    item (emenda (15)). Fecha a r23 (PF 2018 papiloscopista q61/q65) e recupera os itens 49–50 do
    CBM/AL 2017 básicos cargo 1 (45 itens = 45 do gabarito).
  - `f42931b`: fecho do crédito partido em duas linhas; figura que abre a coluna inicia o
    texto-base seguinte (emenda (16)). Fecha a r24 (CBM/AL 2017 CB1A1AAA, q40/g41).
  - `f575fc1`: `infer_font_styles` em `pmma-2017` (3 provas) e `cbmpa-2023-cfo/p1`; estilo de
    fonte com poucas letras pela largura (só fora do `legacy`; empate itálico × negrito itálico dá
    itálico); item rotulado com recuo pendente no certo/errado (emenda (17)). Fecha a r25. De
    quebra, títulos de disciplina do CBM/PA CFO saem das alternativas (q25, q32, q39).
  - `16db2cc`: o próximo rótulo da lista (I→II, a)→b)) abre parágrafo; "À" abre frase no corte do
    comando (emenda (18)). Fecha a r26 (PF 2012 agente q83/q84).
  - `29cedbf`: justificativa de alternativa ("||A|| - Incorreta…") na cor das justificativas, sem
    cabeçalho, não vira texto-base (emenda (2) da 0009). O `pmdf-2025/p2` q80 apontava para a
    justificativa da q79 como texto-base, numa prova publicada.
  - `b9c9f31`: `infer_font_styles` em `pmsc-2023-oficial`, `pcdf-2019` e `prf-2021` espanhol
    (só nessa prova do PRF). Fecha a r29 de pcdf e prf.
- **Aprovações do minos** (claude-opus-5-5), 27 registros:
  - r23 (`980d47f`): `pcpb-2021` escrivão e cargos 1 e 3, `pf-2018` agente e escrivão,
    `pf-2025/escrivao-especificos`, `pcma-2017-apc` escrivão, `pmsc-2023-soldado/objetiva`.
  - r24 (`1193cf5`): `pf-2018/papiloscopista`, `pcpb-2021` gerais 4 a 13, `pcro-2022` específicos
    cargo 1.
  - r25 (`388a4ea`): `cbmal-2017` básicos cargo 1 (primeira aprovação), `pmal-2017` específicos
    soldado, `pcpe-2023/p1-cargo-3`.
  - r26 (`824ba1a`): `pmma-2017` gerais cargos 1 e 5 e específicos cargo 5, `pcpe-2023/p1-cargo-1`,
    `cbmpa-2023-cfo/p1`.
  - r27 (`3475a3d`): `pf-2012/agente`.
  - r28 (`804fd67`): `pmdf-2025/p2`.
  - r29 (`c1d4563`): `pcal-2021/escrivao`, `cbmal-2021/soldado`, `pf-2018/delegado`.
  - r30 (`cc71a88`): `pcdf-2019/objetiva`, `prf-2021/lingua-espanhola`.
  - Reprovações fechadas no ciclo: r22, r23, r24, r25 ×4, r26, r29 ×2. Fica aberta a r30.

## Verificação
- `make gates` final (HEAD `cc71a88`): ok — lint, roundtrip das migrações, 624 testes, `emmoni
  check` 9 checagens com 0 violações.
- Não verificado: marcação nova fora das amostras (PM/MA 2017 gerais cargo 1, PC/DF 2019 páginas
  além das amostradas, CBM/PA "*Z*O", "*mv*2") não foi conferida página a página; a regra
  `below_figure` (emenda (16)) e a de ordinal só foram testadas contra os PDFs em `data/raw`.

## Decisões
- Emendas (14)–(18) da 0020 e (2) da 0009; SPECIFICATION.md §7.
- Conservador: ordinal só pelo glifo, nunca por regex no texto; plural "n.ºs" com "s" comum;
  ângulos "30o" ficam (pede decisão própria: "°" ou "º"); estilo de poucas letras fora do
  `legacy`; recuo pendente só em item rotulado; estilo ligado só na prova de espanhol do PRF 2021.
- Tentativa de separar a tabela da q84 do PF 2012 agente revertida: quebrava o PF 2012
  papiloscopista q104–106 e perdia linhas da tabela.

## Problemas encontrados
- `pmsc-2023-oficial/objetiva` reprovada (r30), em `review` (fora da API): q66 (pág. 10), fórmula
  centralizada em linha própria colada ao comando seguinte no mesmo parágrafo. O resto confere.
- `pf-2012/agente` q84: a tabela das q85–86 sai colada no fim do enunciado (recuo > `HANGING_MAX`
  com minúscula não fecha o item); q85–86 sem texto-base. As três seguem em `review`.
- `cbmal-2017` básicos cargo 1: q48 em `review` por dois retângulos brancos sem traço contados como
  desenho; q50 por glifos sem mapeamento; marcadores do g41 são "•" literal.
- `pf-2018/escrivao` g97: marcador "•" lido como "C" e parágrafo partido (questões em `review`).
- `pmsc-2023-soldado` 1A5-III: "Assunto: Solicitação de senha." em negrito no PDF, sem negrito no
  banco (questões em `review`).
- Disciplina "Legislação Penal Militar" no `pmsc-2023-oficial` para seções "Direito Penal Militar"
  / "Direito Processual Penal Militar" do PDF (nome do catálogo; minos não reprovou).

## Próximo
- Hefesto: fórmula centralizada isolada como parágrafo (PM/SC 2023 oficial q66); minos com semente
  nova (≠ r2–r30).
