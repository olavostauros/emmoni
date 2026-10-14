# 0032 — Hífen de fim de linha fica

**Data:** 2026-10-14 · **Marco:** M5

## Contexto

O parser do Cebraspe tirava o hífen de toda linha que terminava em letra minúscula + "-" seguida de
linha começando por minúscula, supondo separação silábica (`investi-` | `gação`). O minos reprovou
PC/PB 2021 cargo 12 (q66, "espécies-alvo" → "espéciesalvo") e cargo 5 (q63, "pós-morte" →
"pósmorte"), e achou o mesmo defeito em outras provas publicadas. Com maiúscula ou algarismo depois
do hífen, a junção punha um espaço ("Jaci- Paraná", "1A1- I", "1956- 1960").

Medição em 136 cadernos do staging (2012–2026, inclusive o site antigo): 70 linhas de página terminam
em letra ou algarismo + "-"; todas são hífen do original (composto, ênclise, rótulo, URL), nenhuma é
separação silábica. Das 28 junções que o `_join` fazia, as 28 estavam erradas. O Cebraspe não
hifeniza por sílaba: a linha só quebra no hífen que já existe.

## Decisão

- No parser do Cebraspe, linha que termina em hífen colado a letra ou algarismo, seguida de linha que
  começa por letra ou algarismo, emenda **sem espaço e com o hífen** ("pós-" | "morte" →
  "pós-morte", "aplica-" | "se" → "aplica-se", "Jaci-" | "Paraná" → "Jaci-Paraná").
- Traço com espaço antes ("pausa -") não é hífen de palavra e emenda com espaço, como antes.
- Separação silábica de outra banca, se aparecer, entra no parser dela, com evidência do corpus.

## Consequências

- `docs/content-format.md` e o SPECIFICATION.md §5 deixam de dizer que a hifenização de fim de linha é
  removida.
- Reprocessamento: 22 provas mudam texto em 1 a 10 questões; a impressão digital muda e elas voltam a
  `review` até nova amostra. No CBM/TO 2022 q7, o rótulo "1A1-I" reconstituído liga a questão ao
  texto-base, e ela sai de `review`.
