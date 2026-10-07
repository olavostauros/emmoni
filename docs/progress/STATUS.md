# Status — atualizado em 2026-10-07

**Marco atual:** M2 — Primeira ingestão (SPECIFICATIONS.md §10) — falta só a aprovação humana das amostras
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato (2026-10-07)

## Feito neste marco
- Fontes permitidas e cliente HTTP de cortesia; leitura do Cebraspe pela API JSON (0003, 0004).
- Pipeline completo `fetch → extract → segment → answer-key → validate → classify → load` (0005).
- Classificação por assunto feita **pelo agente**, por arquivos de tarefas/respostas (0006), sem
  Claude API. As respostas (`classify-answers.json`) são versionadas no git.
- 5 concursos, 18 provas, 1.496 questões no banco de desenvolvimento: PF 2025, PF 2021, PF 2018,
  PRF 2021, PRF 2018 (cargos policiais). Todas classificadas e carregadas; `emmoni check` limpo.
- Amostras das 18 provas geradas em `data/review/<concurso>/<prova>/amostra.html`.

## Em andamento
- Nada em execução. Tudo depende da aprovação humana (abaixo).

## Próximos passos
1. **Humano:** conferir as amostras e rodar `emmoni review approve <concurso>/<prova>` para as 18
   provas → as 822 questões `published` passam a aparecer no esquema `api` → M2 pronto.
2. Corrigir `subjects_by_range` dos manifestos com blocos mistos de Direito Penal/Processual Penal
   (PRF 2018 Q103–105, PF 2021 Q31–33) e rerodar `validate → classify → load` dessas provas.
3. M3 — crawler do Cebraspe (o cliente HTTP e o conhecimento da API já existem).
4. M4 — crescer a taxonomia a partir de `docs/progress/2026-10-07-sugestoes-de-assuntos.md`
   (728 sugestões; 464 questões em `review` só por falta de assunto) e reclassificar.
5. Etapa `structure` e exportação de imagens para as 210 questões com problema de extração.

## Bloqueios e perguntas em aberto
- **Amostragem humana** das 18 provas: só uma pessoa pode aprovar.
- Decidir (M4) se questão sem assunto adequado deve ser `draft` em vez de `review`: hoje ela sai
  da deduplicação junto com as de extração incompleta.
- DPF 2014 (API do Cebraspe dá erro 500) e concursos anteriores a 2014 (`cespe.unb.br`, fora das
  fontes — incluir exige decisão).
- `emmoni coverage` previsto na especificação, ainda não implementado.
- Folga pequena em `facet_counts` sem filtros (281/300 ms), prevista na decisão 0002.

## Números
- Questões publicadas no contrato: 65 (todas do seed) · reais: 1.496 carregadas, 822 `published`
  (aguardando aprovação da prova), 674 em revisão (464 só por classificação, 210 por extração),
  105 duplicatas, 0 `draft`
- Provas ingeridas: 18 (nenhuma aprovada)
- Propostas do crawler pendentes: 0
- Contrato do front-end: **v1.1**
