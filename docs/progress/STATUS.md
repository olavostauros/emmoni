# Status — atualizado em 2026-10-07

**Marco atual:** M2 — Primeira ingestão (SPECIFICATIONS.md §10) — não iniciado
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato (2026-10-07)

## Feito
- M0: ambiente, papéis, `make gates`.
- M1: esquema completo, esquema `api`, `docs/contract.md` v1.0, seed com 65 questões, `make bench`
  dentro das metas. **O agente de front-end já pode começar** com `make db-up migrate seed`.

## Em andamento
- —

## Próximos passos
1. Manifestos dos últimos 5 concursos de PF e PRF (Cebraspe) em `ingest/manifests/`.
2. Etapas `fetch` e `extract` (PyMuPDF, OCR de fallback), com PDFs pequenos em `fixtures/`.
3. Parser do Cebraspe (`segment`), gabaritos (`answer-key`), `validate`, `load`.
4. Amostragem manual e publicação da primeira prova real.

## Bloqueios e perguntas em aberto
- Folga pequena em `facet_counts` sem filtros (281/300 ms a 100 mil questões). Otimização prevista
  na decisão 0002, a fazer antes do M6.

## Números
- Questões publicadas: 65 (todas do seed) · reais: 0 · provas ingeridas: 0
- Propostas do crawler pendentes: 0
- Contrato do front-end: **v1.0**
