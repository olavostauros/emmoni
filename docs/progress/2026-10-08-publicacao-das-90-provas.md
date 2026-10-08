# 2026-10-08 — Publicação das 90 provas pela amostragem do agente

**Marco:** M4 → publicação (antes do M5)

## O que foi feito
- Rodadas 2 a 5 da amostragem (a rodada 1 foi anulada; ver `2026-10-08-amostragem-rodada-1.md`):
  revisores em paralelo, até 5 provas cada, instruções em `ingest/prompts/review-sample@1.md`.
  Rodada 2: 69 de 90 aprovadas; rodada 3: +10; rodada 4: +8; rodada 5: +3. **90 de 90.**
- Entre as rodadas, correções no parser e no extract (decisão 0014) e reprocessamento só das
  provas ainda não aprovadas. Commits d481872, 55d9cac, bd95bc4.
- `emmoni review sample` inclui as páginas do texto-base e a página seguinte à questão.

## Verificação
- `make gates`: **passou** — 317 testes, lint, roundtrip, 7 checks sem violação.
- Provas carregadas: 108, todas `published`. `api.question`: 5.000 questões (antes 1.188).
- Questões reais: 5.301 `published`, 1.013 `review` (figura, fórmula, layout, texto-base não
  encontrado) — ficam fora do `api`.
- Aprovação conferida por script: `verdicts.json` com o nome da prova, os mesmos 10 números de
  `sample.json` e todos `ok`.
- **Não verificado:** as 18 provas do M2 foram reprocessadas depois de aprovadas (rodada 1) e não
  foram reamostradas. Nenhuma conferência humana (decisão 0011). Vereditos e amostras ficam em
  `data/review/` (fora do git).

## Decisões
- [0014](../decisions/0014-amostragem-das-90-provas.md).

## Problemas encontrados
- Limite de imagens do revisor: na rodada 1 um revisor aprovou sem ver as páginas → regra de
  `unverified`/`incomplete`.
- Revisores em paralelo sobrescreveram um script auxiliar comum → nomes próprios por lote e
  conferência do nome da prova no veredito.
- Ainda sem solução: números de linha dos textos-base ("ℓ" → "R"), hífen real perdido em quebra
  de linha, figuras não exportadas, tirinhas só como imagem.

## Próximo passo
- Reamostrar as 18 provas do M2 (pf/prf) com o parser atual.
- Depois, M5.
