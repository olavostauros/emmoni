# Status — atualizado em 2026-10-07

**Marco atual:** M2 — Primeira ingestão (SPECIFICATIONS.md §10) — falta classificar e aprovar
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato (2026-10-07)

## Feito neste marco
- Fontes permitidas e cliente HTTP de cortesia; leitura do Cebraspe pela API JSON (0003, 0004).
- Pipeline completo `fetch → extract → segment → answer-key → validate → classify → load` (0005).
- 5 concursos, 18 provas no banco de desenvolvimento: PF 2025, PF 2021, PF 2018, PRF 2021,
  PRF 2018 (cargos policiais).
- Fila de revisão e amostragem: amostras geradas em `data/review/` para as 18 provas.

## Em andamento
- Classificação por assunto: etapa pronta e testada, falta credencial da API.

## Próximos passos
1. Com credencial: `emmoni ingest <concurso> --step classify` e `--step load` para cada concurso.
2. Aprovação humana das amostras (`emmoni review approve <concurso>/<prova>`) → M2 pronto.
3. Etapa `structure` (LLM) e exportação de imagens para as 210 questões em revisão.
4. M3 — crawler do Cebraspe (o cliente HTTP e o conhecimento da API já existem).

## Bloqueios e perguntas em aberto
- **Credencial da Claude API** (`ANTHROPIC_API_KEY` no `.env` ou `ant auth login`).
- **Amostragem humana** das provas: só uma pessoa pode aprovar.
- DPF 2014 (API do Cebraspe dá erro 500) e concursos anteriores a 2014 (`cespe.unb.br`, fora das
  fontes — incluir exige decisão).
- Folga pequena em `facet_counts` sem filtros (281/300 ms), prevista na decisão 0002.

## Números
- Questões publicadas: 65 (todas do seed) · reais: 1.496 carregadas, 210 em revisão,
  161 duplicatas, 0 publicadas
- Provas ingeridas: 18 (nenhuma publicada)
- Propostas do crawler pendentes: 0
- Contrato do front-end: **v1.1**
