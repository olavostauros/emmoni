# 2026-10-08 — Reamostragem das 18 provas do M2

**Marco:** antes do M5

## O que foi feito
- Amostras novas das 18 provas do PF e da PRF (reprocessadas na rodada 1 depois de aprovadas).
  4 revisores em contexto separado, `ingest/prompts/review-sample@1.md`: **15 aprovadas**, 3
  reprovadas (PF 2018 agente, escrivão e papiloscopista). As 15 foram reaprovadas (`--by
  claude-opus-5-5`); as 3 voltaram para `review` (decisão 0015).
- Causas das reprovações: o staging do PF 2018 era da rodada 1. Reprocessar desde o `extract` já
  corrigiu o agente. Mais duas correções no parser:
  comando partido antes do rótulo ("...do texto" | "13A1AAA, julgue") e flag `consecutive_items`
  para itens que são períodos consecutivos de um parágrafo (PF 2018 papiloscopista, itens 6–11 →
  `review`). Testes com fixtures novas (`pf-2018-escrivao-p1-2.pdf`, `pf-2018-papiloscopista-p1.pdf`).
- Reamostragem das 3 por outro revisor: 3 de 3 aprovadas, verdicts íntegros, publicadas.
- `emmoni ingest` segue para as provas seguintes quando uma dá `LoadError` e sai com código 1,
  listando as que falharam (teste em `tests/test_ingest.py`).

## Verificação
- `make gates`: **passou** — 320 testes, lint, roundtrip, 7 checks sem violação.
- Segmentação de todas as provas com o parser antes e depois da mudança: só PF 2018 escrivão e
  papiloscopista mudam.
- Aprovação conferida por script (prova, números da amostra, todos `ok`) antes de cada `approve`.
- **Não verificado:** nenhuma conferência humana (decisão 0011). Vereditos em `data/review/` (fora
  do git).

## Decisões
- [0015](../decisions/0015-reamostragem-das-provas-do-m2.md).

## Problemas encontrados
- O staging de 17 provas aprovadas não bate com o parser atual (correções posteriores à aprovação;
  o banco tem o conteúdo aprovado). Reprocessar exige nova amostragem.
- Revisor notou: negrito no enunciado do PF 2018 se perde ("**compreende**", agente q19). Não
  reprova, mas o contrato pede a formatação relevante.
- `_I_A` / `_I_B` no PF 2025 papiloscopista q102 está assim no PDF oficial (conferido).

## Próximo passo
- M5 (crawler e parser de outra banca).
