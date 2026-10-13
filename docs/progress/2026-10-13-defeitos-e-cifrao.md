# 2026-10-13 — Capa do PM/AL 2021, fonte de símbolos e escape do `$`

**Marco:** M5

Checkout principal, branch `fix-defeitos-cifrao` (sobre o `main` `21bbaf3`, com o WIP `a181184`),
mudanças ainda sem commit. Carga no banco `emmoni` feita deste checkout.

## O que foi feito
- Terminado o WIP `a181184`:
  - **PROVAS OBJETIVAS** no plural abre a prova: o PM/AL 2021 oficial q1–q4 estava **publicado**
    com o lixo da capa (fonte quebrada, "����") no lugar do comando. Agora sai o comando certo;
    conferi q1–q4 contra a página 2 e o gabarito (E, C, E, E).
  - Fonte de símbolos sem mapeamento ("P(Z # !2)" = "P(Z ≤ −2)") marca a linha como fórmula.
  - Bug novo: `extract._merge` (linha juntada ao número do item) descartava o `odd_glyph`, e
    "P(X \$ 40 litros)" ("≥") passava sem flag. Corrigido.
- Escape de texto literal (decisão 0023): `$`, `*`, `_`, `` ` ``, `<` e `\` do PDF saem com `\`
  (`ingest/content.py:escape_md`). `docs/content-format.md` v1.1, contrato v1.4, SPECIFICATION §5.
  O Plantão já esperava isso (`src/lib/markdown.ts` desligou `$...$` à espera da v1.1).
- Testes: fixtures `pf-2018-papiloscopista-p4.pdf` e `pmal-2021-oficial-p1-2.pdf`; testes de
  `escape_md` e de que o hash não muda.
- Reprocessados (`extract` → `classify`) os 42 manifestos do staging, menos `pcpe-2016` e
  `pcientifica-pe-2016`. O `data/staging` deste checkout estava velho (a carga de 2026-10-08 foi do
  worktree `credit-end-reprocess`); a comparação foi feita contra o staging daquele worktree:
  - 280 questões/textos-base mudam só pelo escape;
  - PM/AL 2021 oficial q1–4 e soldado q1–6: comando corrigido;
  - PF 2018 agente q51–56 e papiloscopista q48–50 (e textos-base g51, g48): ganham `formula`.
- `load`: 6.634 questões, nenhuma nova ou removida; 10 `statement_hash` mudaram (os do PM/AL).
  Voltaram para `review` por mudança de conteúdo: **pmal-2021/oficial, pf-2018/agente,
  pf-2018/papiloscopista**.
- Reamostragem das três (revisão em subagentes, uma por prova): **nenhuma aprovada**.

## Verificação
- `make gates`: **passou** — 366 testes, `emmoni check` com 7 checks e 0 violações.
- Status e hash antes × depois comparados pelo banco (backup `pg_dump` no scratchpad da sessão).
- `docs/coverage.md` regerado: 4.858 questões publicadas (eram 5.152; −294 das três provas).

## Problemas encontrados
- **"(ℓ.N)" sai "(R.N)"**: o ℓ das referências de linha vem de uma fonte de símbolos cujo glifo
  mapeia para "R". Erro de conteúdo, **já publicado**: 188 ocorrências no staging, em 17 provas
  (PF 2018 agente/escrivão/papiloscopista, PC/GO 2016, PC/MA 2017, PM/AL 2017 e 2018, PM/MA 2017,
  CBM/AL 2017). O `_line_refs` já corrige isso, mas só no modo `legacy`.
- Itálico e negrito perdidos nas fontes "TT…o00" (próximo passo 2 do STATUS anterior): os três
  revisores acharam isso em quase todas as questões das amostras.
- Crédito em três linhas ou mais partido em parágrafos (PM/AL 2021 oficial g15, PF 2018 agente).
- A amostra é determinística e não pegou o lixo do PM/AL q1–4 na aprovação de 2026-10-08.

## Próximo passo
- Decisão do dono sobre o critério de aprovação (ver STATUS) e, depois, ligar o `_line_refs` fora
  do `legacy`, reprocessar e reamostrar.
