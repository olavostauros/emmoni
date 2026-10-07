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
- 25 órgãos estaduais, DEPEN e SEAP-MA no catálogo com apelidos de cargo; regras novas do
  crawler; `make crawl` corrigido (contato exportado; erro de configuração não grava estado).
  35 propostas pendentes (decisão 0008).

## Em andamento
- Nada em execução.

## Próximos passos
1. Ingerir os 36 manifestos aprovados em 2026-10-07 (PCDF, PC/PM/CBM estaduais, DEPEN): um por
   vez, calibrando o parser do Cebraspe em cada caderno e preenchendo `name`, `first_number` e
   `subjects_by_range` (os manifestos aprovados vieram das propostas sem ajuste).
2. M4 — crescer a taxonomia a partir de `docs/progress/2026-10-07-sugestoes-de-assuntos.md`
   (728 sugestões; 462 questões em `review` só por falta de assunto) e reclassificar. Ao reclassificar,
   as duplicatas entre cargos hoje escondidas pelo `review` passam a ser marcadas (eram 161 antes
   da classificação, hoje 105).
3. Instalar o timer do systemd (`docs/operations.md`) na máquina que vai rodar o crawl diário.
4. Etapa `structure` e exportação de imagens para as 210 questões com problema de extração.

## Bloqueios e perguntas em aberto
- Proposta pendente que deixa de ser proposta (regra mudou) não é removida de `_pending/` pelo
  crawler: `pmto-2020-qps` ficou e foi rejeitada à mão. Decidir se o crawler apaga ou marca.
- SDS/PE (2016) continua fora do catálogo: a secretaria organizou concursos de PC-PE e de
  Polícia Científica; decidir se entra como alias de `pcpe`.
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
- Provas ingeridas: 18 (18 aprovadas na amostragem)
- Propostas do crawler pendentes: 0 · manifestos aprovados: 41 (5 ingeridos) · rejeitados: 1
- Concursos vistos pelo crawler no Cebraspe: 498 (440 fora do escopo, 49 de órgãos candidatos)
- Contrato do front-end: **v1.1**
