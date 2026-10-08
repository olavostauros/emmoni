# Status — atualizado em 2026-10-08

**Marco atual:** M5 — Mais bancas (SPECIFICATION.md §10). M0–M4 prontos (M4 em 2026-10-08).
Ainda não há crawler nem parser de outra banca; o trabalho do M5 até aqui ampliou o Cebraspe.

## Feito neste marco
- HTTP do `www.cespe.unb.br` (decisão 0017); OCR com revisão do agente (decisão 0018); `CREDIT_END`
  e reprocessamento das 16 provas; sessões paralelas (decisão 0019).
- Site antigo do Cebraspe: `extract` com `legacy`, PF 2012 Agente publicado, disciplina `economia`
  (decisão 0020, `2026-10-08-pf-2012-site-antigo.md`).
- Provas aprovadas reprocessadas com o parser novo: 67 créditos emendados no banco, as 117 provas
  seguem publicadas sem reamostragem (`2026-10-08-reprocessamento-creditos.md`).

## Em andamento
- Nada em execução. Branch `worktree-credit-end-reprocess` ainda não integrado ao `main` (PR aberto).

## Próximos passos
1. Crédito em três linhas ou mais: só as duas últimas são emendadas (PM/MA 2017 g39, INFOPEN do
   DEPEN). Corrigir no parser e reprocessar como em `2026-10-08-reprocessamento-creditos.md`.
2. Avaliar ligar o estilo pelas larguras (`legacy`) nos cadernos novos com fontes "TT…o00"
   (PC/PE 2023, PF 2025…): recupera itálico/negrito perdidos (inclui o negrito do PF 2018,
   "compreende", agente q19). Exige reprocessar e reamostrar.
3. Manifestos dos demais concursos policiais do `cespe-unb` (índice em
   `data/crawl/cespe-unb/concursos___antigos__default.asp`): começar por DPF 2012 (escrivão,
   delegado, perito, papiloscopista), DPF 2009, DPRF 2013, PC/DF 2013, DEPEN 2013.
4. Taxonomia: assuntos para PF 2012 q60, q62, q65 (sugestões em `topics.json`).
5. Começar o crawler e o parser de outra banca.
6. `pcpe-2016` e `pcientifica-pe-2016`: calibrar o parser, preencher `first_number` e
   `subjects_by_range` e ingerir.
7. Instalar o timer do systemd (`docs/operations.md`).
8. Etapa `structure` e imagens para as questões em `review` por figura, fórmula e layout.
9. Amostra: incluir a página do comando quando ele está antes da página da questão (PCDF 2026 q96).
10. PM/MA 2017: 6 documentos fora do manifesto (decisão 0009): confirmar e silenciar no relatório.

## Bloqueios e perguntas em aberto
- CBM/AL 2017 básicos cargo 1 e PC/PB 2021 cargo 8 item 80 seguem fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (estão também no site antigo: tentar por lá).
- Sessões paralelas compartilham o Postgres; a regra é de processo, sem trava (decisão 0019).

## Números
- Questões visíveis no esquema `api`: 5.152 reais, sem duplicatas e sem o seed (`docs/coverage.md`)
- Reais: 6.634 carregadas · 5.554 `published` · 1.077 `review` · 3 `draft`
- Provas: 112 aprovadas, com registro em `ingest/approvals/`; 24 de manifestos aprovados fora do
  banco, 21 delas de `pcpe-2016` e `pcientifica-pe-2016`
- Propostas do crawler pendentes: 0 · manifestos: 44 (1 do `cespe-unb`) · rejeitados: 1
- Taxonomia: 57 disciplinas, 911 assuntos
- Contrato do front-end: **v1.2**
