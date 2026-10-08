# 2026-10-08 — Bloqueios e perguntas em aberto

**Marco:** antes do M5

## O que foi feito
- Decisões do dono do projeto: versionar aprovações, Polícia Científica/PE no catálogo, incluir
  `cespe.unb.br` (esta última esbarrou no HTTP — ver bloqueios). Registradas na decisão 0016.
- Aprovação versionada em `ingest/approvals/` com impressão digital do conteúdo visível; `load`
  reconcilia o status da prova; `emmoni review restore`; `emmoni review sample --also`.
- `pcientifica-pe` no catálogo (carreira `policia_cientifica`, contrato v1.2); crawler atribui a
  prova comum por série de cadernos; manifesto `pcientifica-pe-2016` aprovado e ajustado (sem
  ingestão).
- `emmoni coverage` → `docs/coverage.md`.
- `facet_counts` numa passada (migração `20261008000100`).
- 15 provas aprovadas cujo staging divergia do parser: reprocessadas e reamostradas (4 revisores
  em contexto separado, amostra + questões que mudaram). 14 aprovadas; CBM/TO 2022 soldado
  reprovada (título de seção grudado na alternativa D da q40) → correção no parser → CBM/TO 2021
  oficial e soldado e 2022 soldado reamostradas e aprovadas.
- DEPEN 2020: gabarito de complementares errado (CG1, nível superior) → CG2 (nível médio, 81–120);
  cargo agente é de nível médio. Carregada, amostrada (10/10) e publicada: 90 questões.
- PCDF 2026 q96: o comando da questão está na página 11, fora das imagens da amostra; o revisor
  não viu e marcou `ok`. O agente coordenador conferiu a página 11 (texto idêntico) e registrou
  no verdicts antes de aprovar.

## Verificação
- `make gates`: **passou** — 329 testes, lint, roundtrip das migrações, 7 checks sem violação.
- `make bench`: todas as metas; `facet_counts` sem filtros p95 194 ms (era 2.185 ms).
- `facet_counts` nova = antiga em 30 combinações de filtros/texto (banco de desenvolvimento).
- Segmentação de todas as provas com o parser antes e depois da correção dos títulos: só as 4
  questões visadas mudam.
- `emmoni review restore`: 109 de 109 provas conferem com a aprovação registrada.
- **Não verificado:** nenhuma conferência humana (decisão 0011). As páginas da amostra não incluem
  a página do comando quando ele está numa página anterior à da questão (caso PCDF 2026 q96).

## Decisões
- [0016](../decisions/0016-bloqueios-aprovacoes-policia-cientifica-facetas.md) (com adendo).

## Próximo passo
- M5, `pcpe-2016` + `pcientifica-pe-2016` (mesmos cadernos SDS/PE 2016).
