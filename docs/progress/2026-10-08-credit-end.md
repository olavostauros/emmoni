# 2026-10-08 — Staging das provas que mudam com `CREDIT_END`

**Marco:** antes do M5

## O que foi feito
- O trabalho da sessão anterior (decisões 0017 e 0018), que estava sem commit no `main`, entrou num
  commit próprio no ramo `worktree-credit-end-reprocess`.
- Os manifestos afetados (cbmpa-2023-cfo, cbmpa-2023-cfp, cbmro-2022, cbmto-2021, cbmto-2022,
  pcce-2025, pcpb-2021, pcro-2022, pmto-2020-qppm) reprocessados de `extract` a `load`. Comparação
  do staging anterior com o novo: exatamente as 16 provas previstas mudam, em 51 questões (o STATUS
  dizia 47). Todo o texto muda só em espaço: o crédito da fonte vira parágrafo próprio, separado do
  comando. Conferidos os 51 trechos.
- A impressão digital da aprovação usa o `statement_hash` normalizado, então 15 provas seguiram
  publicadas sem reamostragem (o STATUS previa que todas sairiam do `api`; não saem).
- CBM/RO 2022 oficial: q21 passou a ter a marca `formula` (`odd_glyph` nas opções "**A** 5*x* +
  3y": dígito em fonte própria entre a letra da opção, em negrito, e a variável, em itálico). O
  staging anterior era de antes da regra. A questão foi para `review` e a prova saiu do `api`.
  Reamostrada (10 sorteadas + 33, 34, 35, 36, 37 e 39, com crédito mudado) por um revisor em
  contexto separado: 16/16 ok; aprovada por claude-opus-5-5.
- Testada a regra "letras dos dois lados na mesma fonte" para o `odd_glyph` em todos os PDFs de
  `data/raw`: tiraria a marca de 49 linhas com índices reais (R4, sp2, W1, P2). Regra mantida; a
  q21 fica em `review` (falso positivo, erra para o lado seguro).
- `docs/coverage.md` regerado: 5.062 questões publicadas (−1, a q21).

## Verificação
- `make gates`: **passou** — 341 testes, `emmoni check` sem violações.
- Verdicts conferidos por script antes do `approve` (prova, números da amostra, todos `ok`).
- **Não verificado:** nenhuma conferência humana (decisão 0011). Os 45 créditos das 15 provas que
  não foram reamostradas foram conferidos só no texto (diff), não contra a página do PDF.

## Problemas encontrados
- PC/PB 2021 cargo 8 segue fora (gabarito com 29 itens para 30 questões; bloqueio conhecido).

## Próximo passo
- Manifestos dos concursos policiais antigos do `cespe-unb`.
