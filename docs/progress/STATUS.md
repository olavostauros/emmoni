# Status — atualizado em 2026-10-07

**Marco atual:** M2 — Primeira ingestão (SPECIFICATIONS.md §10) — em andamento
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato (2026-10-07)

## Feito neste marco
- Fontes permitidas (`ingest/sources.yaml`) e cliente HTTP de cortesia (decisões 0003 e 0004).
- Pipeline `fetch → extract → segment → answer-key → validate → load` com parser do Cebraspe
  (decisão 0005). `emmoni ingest <manifesto>`, `emmoni catalog load`.
- PF 2021 — Agente no banco de desenvolvimento: 120 questões (93 sem pendência, 27 em revisão).

## Em andamento
- Classificação por assunto (`classify`) — falta a chave da API.

## Próximos passos
1. `classify` com Claude API (respostas cacheadas no staging; testes com respostas gravadas).
2. `emmoni review list|show|sample|approve` e amostragem manual do PF 2021 — Agente.
3. Manifestos e ingestão das demais provas: PF 2021 (outros 3 cargos), PF 2018, DPF 2014, PF 2025,
   PRF 2018, PRF 2021. Conferir o parser em cada uma (calibrado numa prova só).
4. Etapa `structure` (LLM) e exportação de imagens para tirar questões de `review`.

## Bloqueios e perguntas em aberto
- **`ANTHROPIC_API_KEY`** no `.env` para a etapa `classify` (sem assunto nenhuma questão publica).
- Concursos anteriores a 2014 (PF 2012, PRF 2013) estão em `cespe.unb.br`, fora das fontes.
  Incluir exige decisão.
- Folga pequena em `facet_counts` sem filtros (281/300 ms a 100 mil questões), já prevista na
  decisão 0002.

## Números
- Questões publicadas: 65 (todas do seed) · reais: 0 publicadas, 27 em revisão, 93 sem assunto
- Provas ingeridas: 1 (PF 2021 — Agente, ainda não publicada)
- Propostas do crawler pendentes: 0
- Contrato do front-end: **v1.1**
