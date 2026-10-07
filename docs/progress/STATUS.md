# Status — atualizado em 2026-10-07

**Marco atual:** M3 — Crawling (SPECIFICATIONS.md §10) — **pronto**
**Próximo marco:** M4 — Taxonomia e classificação
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato · M2 — Primeira ingestão · M3 — Crawling (2026-10-07)

## Feito neste marco
- Crawler do Cebraspe pela API JSON (`ingest/crawlers/cebraspe.py`), orquestração com estado em
  `crawl.page` e cache em `data/crawl/` (`ingest/crawl.py`), propostas e aprovação
  (`ingest/proposals.py`, `emmoni manifests`), `emmoni crawl` / `make crawl` (decisão 0007).
- Execução real: os 5 concursos de PF e PRF do M2 foram redescobertos com 36/36 documentos dos
  manifestos manuais; 3 concursos novos propostos (PCDF 2019, 2020 e 2026). PCDF entrou no
  catálogo.
- 51 testes novos com fixtures JSON em `fixtures/crawl/cebraspe/`; `docs/operations.md` com o
  agendamento diário.

## Em andamento
- Nada em execução.

## Próximos passos
1. Humano decide sobre as 3 propostas pendentes de PCDF (`emmoni manifests pending|approve|reject`).
   Ingerir exige calibrar o parser do Cebraspe nos cadernos da PCDF e preencher `subjects_by_range`.
2. M4 — crescer a taxonomia a partir de `docs/progress/2026-10-07-sugestoes-de-assuntos.md`
   (728 sugestões; 462 questões em `review` só por falta de assunto) e reclassificar. Ao reclassificar,
   as duplicatas entre cargos hoje escondidas pelo `review` passam a ser marcadas (eram 161 antes
   da classificação, hoje 105).
3. Instalar o timer do systemd (`docs/operations.md`) na máquina que vai rodar o crawl diário.
4. Etapa `structure` e exportação de imagens para as 210 questões com problema de extração.

## Bloqueios e perguntas em aberto
- Órgãos policiais que o Cebraspe lista e não estão no catálogo (PC de 10 estados, PM de 8, CBM,
  DEPEN, SEAP, SDS/PE): cada um entra por commit em `db/catalog.yaml` com `aliases`; o crawler
  então busca o detalhe e propõe. Decidir a ordem (M5 prevê outras bancas; os órgãos podem vir antes).
- PCDF 2019: um caderno com dois gabaritos definitivos (básicos e específicos); o manifesto aceita
  um gabarito por prova. Mudar o modelo ou juntar os PDFs à mão na aprovação.
- Decidir (M4) se questão sem assunto adequado deve ser `draft` em vez de `review`: hoje ela sai
  da deduplicação junto com as de extração incompleta.
- O registro de aprovação de provas (`data/review/<concurso>/<prova>/sample.json`) está no
  `.gitignore`: a aprovação só existe no banco de desenvolvimento. Decidir se vale versionar.
- DPF 2014 (API do Cebraspe dá erro 500, tentado de novo diariamente) e concursos anteriores a
  2014 (`cespe.unb.br`, fora das fontes — incluir exige decisão).
- `emmoni coverage` previsto na especificação, ainda não implementado.
- Folga pequena em `facet_counts` sem filtros (281/300 ms), prevista na decisão 0002.

## Números
- Questões visíveis no esquema `api`: 784 (65 do seed + 719 reais)
- Reais: 1.496 carregadas · 824 `published` (105 delas duplicatas entre cargos do PF 2021, ocultas
  no `api`) · 672 em revisão (462 só por classificação, 210 por extração) · 0 `draft`
- Provas ingeridas: 18 (18 aprovadas)
- Propostas do crawler pendentes: 3 (pcdf-2019, pcdf-2020, pcdf-2026)
- Concursos vistos pelo crawler no Cebraspe: 498 (440 fora do escopo, 49 de órgãos candidatos)
- Contrato do front-end: **v1.1**
