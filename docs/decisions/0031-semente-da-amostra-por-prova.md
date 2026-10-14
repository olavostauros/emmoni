# 0031 — Semente da amostra por prova

**Data:** 2026-10-14 · **Marco:** M5

## Contexto

`emmoni review sample` sorteava com a semente fixa `<concurso>/<prova>`: depois de uma correção, a
amostra nova trazia as mesmas questões (menos as que foram para `review`). O processo pede que, depois
de uma reprovação corrigida, o revisor amostre de novo com outra semente.

## Decisão

- `emmoni review sample <concurso>/<prova> [--seed <texto>]`. Sem `--seed`, a semente é
  `<concurso>/<prova>` e o sorteio é o mesmo de antes.
- A semente usada fica gravada em `data/review/<concurso>/<prova>/sample.json` (`seed`), no
  cabeçalho do `amostra.md` e, na aprovação, em `ingest/approvals/<concurso>/<prova>.json`
  (`seed`; ausente nas aprovações anteriores a esta decisão).
- A semente não entra na impressão digital: ela diz o que foi conferido, não o conteúdo.

## Consequências

- Reamostrar com outra semente é reprodutível: a mesma semente sorteia as mesmas questões.
- Aprovações novas ganham o campo `seed`; as antigas ficam como estão.
