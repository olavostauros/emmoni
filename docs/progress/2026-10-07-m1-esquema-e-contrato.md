# 2026-10-07 — M1: esquema e contrato

**Marco:** M1 — Esquema e contrato

## O que foi feito
- Migrações (`db/migrations/20261007100000` a `…100600`): catálogo, concurso/prova/origem,
  taxonomia (com `topic_ancestor`), questões, busca textual (`ext.pt_unaccent`, vetor por trigger),
  estado do crawler (`crawl.*`) e esquema `api` (8 views, 4 funções).
- Restrições da §4.3 no banco, incluindo as diferidas (gabarito × alternativas).
- `ingest/content.py` (hash de deduplicação), `ingest/taxonomy.py` + `emmoni taxonomy load`.
- Taxonomia inicial: 9 disciplinas, 58 assuntos (`db/taxonomy/`), só o necessário para o seed.
- Seed: 65 questões fictícias, 5 concursos, 3 bancas, 5 órgãos; texto-base compartilhado (3),
  tabela, 2 imagens SVG, 1 anulada, 1 com gabarito alterado, sublinhado, múltiplos assuntos.
  Gerado por `scripts/build_seed.py`.
- 7 checks de qualidade em `db/checks/`.
- `make bench` (`scripts/bench.py`), `make seed`, `make seed-build`.
- `docs/contract.md` v1.0, `docs/content-format.md` v1.0, decisão 0002; SPECIFICATIONS.md alinhado
  (§4, §5, §6, §9).

## Verificação
- `make gates` (banco recriado do zero, ver abaixo): **passou**. 142 testes; lint, mypy e checagem
  do seed limpos; roundtrip das 8 migrações ok; 7 checks sem violação.
- `make bench`: **todas as metas atingidas** (tabela na decisão 0002). Facetas sem filtro a 281 ms
  de 300 ms.
- Caminho do front-end conferido em volume novo: `make db-reset migrate seed` e consulta como
  `emmoni_web`.
- Gabaritos do seed revisados um a um contra o texto da lei citado (CF/88, CP, CPP, Lei
  11.343/2006); continuam sendo questões fictícias.
- Não verificado: desempenho com dados reais (o bench replica as 65 questões do seed).

## Decisões
- [0002 — Contrato com o front-end: busca, paginação e facetas](../decisions/0002-contrato-busca-e-facetas.md)

## Problemas encontrados
- Faceta de assuntos lenta (390 ms) → fecho transitivo `topic_ancestor`.
- Hash só do enunciado geraria falsas duplicatas → hash inclui alternativas e texto-base.
- Concatenação de literal com `text[]` em PL/pgSQL interpretava o literal como array → `array_append`.

## Próximo passo
- M2: pipeline completo para Cebraspe + PF e PRF (manifestos, fetch, extract, segment, structure,
  answer-key, validate, load).
