# Status — atualizado em 2026-10-07

**Marco atual:** M2 — Primeira ingestão (SPECIFICATIONS.md §10) — **pronto** (18 provas aprovadas)
**Próximo marco:** M3 — Crawling
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato · M2 — Primeira ingestão (2026-10-07)

## Feito neste marco
- Fontes permitidas e cliente HTTP de cortesia; leitura do Cebraspe pela API JSON (0003, 0004).
- Pipeline completo `fetch → extract → segment → answer-key → validate → classify → load` (0005).
- Classificação por assunto feita **pelo agente**, por arquivos de tarefas/respostas (0006), sem
  Claude API. As respostas (`classify-answers.json`) são versionadas no git.
- 5 concursos, 18 provas, 1.496 questões no banco de desenvolvimento: PF 2025, PF 2021, PF 2018,
  PRF 2021, PRF 2018 (cargos policiais). `emmoni check` limpo.
- Amostras das 18 provas conferidas por humano e **aprovadas** (`emmoni review approve`) em
  2026-10-07. As questões `published` já aparecem no esquema `api`.
- `subjects_by_range` do PRF 2018 corrigido (Q103–105 → Direito Processual Penal); PF 2021 Q31–33
  já estava certo.

## Em andamento
- Nada em execução.

## Próximos passos
1. M3 — crawler do Cebraspe (o cliente HTTP e o conhecimento da API já existem). Critério: redescobrir
   PF e PRF já ingeridos e propor pelo menos um concurso policial novo.
2. M4 — crescer a taxonomia a partir de `docs/progress/2026-10-07-sugestoes-de-assuntos.md`
   (728 sugestões; 462 questões em `review` só por falta de assunto) e reclassificar. Ao reclassificar,
   as duplicatas entre cargos hoje escondidas pelo `review` passam a ser marcadas (eram 161 antes
   da classificação, hoje 105).
3. Etapa `structure` e exportação de imagens para as 210 questões com problema de extração.

## Bloqueios e perguntas em aberto
- Decidir (M4) se questão sem assunto adequado deve ser `draft` em vez de `review`: hoje ela sai
  da deduplicação junto com as de extração incompleta.
- O registro de aprovação (`data/review/<concurso>/<prova>/sample.json`, com quem e quando) está
  no `.gitignore`: a aprovação só existe no banco de desenvolvimento. Decidir se vale versionar.
- DPF 2014 (API do Cebraspe dá erro 500) e concursos anteriores a 2014 (`cespe.unb.br`, fora das
  fontes — incluir exige decisão).
- `emmoni coverage` previsto na especificação, ainda não implementado.
- Folga pequena em `facet_counts` sem filtros (281/300 ms), prevista na decisão 0002.

## Números
- Questões visíveis no esquema `api`: 784 (65 do seed + 719 reais)
- Reais: 1.496 carregadas · 824 `published` (105 delas duplicatas entre cargos do PF 2021, ocultas
  no `api`) · 672 em revisão (462 só por classificação, 210 por extração) · 0 `draft`
- Provas ingeridas: 18 (18 aprovadas)
- Propostas do crawler pendentes: 0
- Contrato do front-end: **v1.1**
