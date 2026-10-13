# 2026-10-13 — "(ℓ.N)" que saía "(R.N)"

**Marco:** M5

Checkout principal, branch `fix-defeitos-cifrao`, depois do commit `5c85ba6`. Carga no banco
`emmoni` feita deste checkout.

## O que foi feito
- `extract._line_refs`: a troca do "R" (glifo do ℓ numa fonte de símbolos) por "ℓ" vale para todo
  caderno, não só no `legacy`. O "*In*" do crédito segue só no `legacy`. Teste novo com
  `pf-2018-agente-p1.pdf`; `test_extract_legacy` atualizado (o ℓ agora sai também sem `legacy`).
- Varredura dos PDFs crus: 289 "R" casam com a regra; os 75 que sobram são "R" de verdade
  (resistência, variáveis) ou o "NaCℓ" da Polícia Científica/PE 2016, fora do banco.
- Reprocessados os 42 manifestos e comparados com o staging do commit `5c85ba6`: 128 questões e
  textos-base mudam, todos só por "(R" → "(ℓ"; nenhum motivo de revisão muda.
- `load`: voltaram para `review` mais 10 provas: cbmal-2017 cargo 2, pcgo-2016 cargos 1 e 2,
  pf-2018/escrivao, pcma-2017-apc cargos 1, 2 e 5, pmal-2017, pmal-2018,
  pmma-2017 cargo 1. Com as 3 da sessão anterior, 13 provas em `review`.
- Reamostragem das 10, em subagentes de contexto separado (duas provas cada): **nenhum defeito de
  conteúdo**, ℓ e gabaritos conferem em todas; todas com defeitos de formatação (itálico e negrito
  perdidos, créditos e itens partidos em parágrafos, "Assinale a opção correta." grudado ao item
  IV no PC/MA). Pelo critério estrito, **nenhuma aprovada**.

## Verificação
- `make gates`: **passou** — 367 testes, `emmoni check` com 7 checks e 0 violações.
- `docs/coverage.md` regerado antes da aprovação: 4.487 questões publicadas (as 13 provas fora).

## Aprovação
- Os revisores foram mais estritos que `ingest/prompts/review-sample@1.md`, que já manda ignorar
  marcação de itálico/negrito e quebras de linha. Com o sim do dono, as 13 provas foram aprovadas
  por essa regra (`verdicts.json` com `approve`, `--by claude-opus-5-5`; o dono rodou o
  `emmoni review approve`, que o modo automático bloqueou). Sem decisão nova.
- Na pmal-2021/oficial e no PF 2018 agente e papiloscopista, o único defeito de conteúdo (ℓ) foi
  conferido na amostra regenerada: nenhum "(R." restante.
- `make gates`: **passou** de novo (367 testes, 0 violações). `docs/coverage.md`: 5.143 questões
  publicadas, 117 provas publicadas, 0 em `review`.

## Próximo passo
- Recuperar itálico e negrito nas fontes "TT…o00" (STATUS, próximo passo 2).
