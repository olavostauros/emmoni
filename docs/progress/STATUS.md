# Status — atualizado em 2026-10-08 (M4 pronto)

**Marco atual:** M5 — Mais bancas (não iniciado)
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato · M2 — Primeira ingestão · M3 — Crawling (2026-10-07) · M4 — Taxonomia e classificação (2026-10-08)

## Feito no M4 (pronto em 2026-10-08)
- Amostra de 50 classificações conferida pelo agente revisor em contexto separado: **49/50
  (98%)**; o único erro (pf-2021/agente q2) foi corrigido na origem e recarregado
  (registro `2026-10-08-m4-revisao-de-assuntos.md`).
- Taxonomia ampliada para 863 assuntos; questão sem assunto confiante fica `draft` e volta às
  tarefas, e `review` passa a significar só defeito de extração (decisão 0010).
- Classificação das 108 provas pelo agente: 6.472 classificadas, 62 sem assunto confiante.
- Revisão humana substituída pela revisão do agente nos três pontos (decisão 0011).
- Pontas soltas do M3 (decisão 0012): crawler propõe um gabarito por bloco em caderno único
  (PCDF 2019), apaga propostas obsoletas de `_pending/`; SDS/PE 2016 entra como alias de evento
  da PC-PE → `pcpe-2016` proposto e aprovado pelo agente.

## Em andamento
- Nada em execução.

## Próximos passos
1. Amostragem por prova pelo agente (`emmoni review sample` / `approve --by <modelo>`) das 90
   provas novas para publicá-las no `api`. O revisor de assuntos já viu texto-base errado em
   pcgo-2016 (escrivão básicos) q14, pcpe-2023/p1-cargo-1 q6, cbmro-2022/oficial q84 e
   pcma-2017-delegado q99: corrigir a segmentação antes de amostrar essas provas.
2. Começar o M5 (crawler e parser de outra banca).
3. Os 62 sem assunto: conferir se a disciplina do manifesto está certa antes de criar assunto
   novo; depois reclassificar.
4. `ingest --step load` deveria seguir para as provas seguintes quando uma falha.
5. `pcpe-2016` aprovado (sem ingestão): calibrar o parser nos cadernos de 2016, preencher
   `first_number` e `subjects_by_range` e ingerir.
6. Instalar o timer do systemd (`docs/operations.md`) na máquina que vai rodar o crawl diário.
7. Etapa `structure` e exportação de imagens para as questões em `review` por figura, fórmula e
   layout (1.231).

## Bloqueios e perguntas em aberto
- OCR (PDFs digitalizados) e itens sem gabarito legível: ver decisão 0009, adendo.
- SDS/PE Polícia Científica (2016) segue órgão candidato: não é da PC-PE (decisão 0012).
- DEPEN 2020: o gabarito de complementares (nível superior) ainda é acrescentado à mão; o nível
  do cargo não está na API.
- O registro de aprovação de provas (`data/review/<concurso>/<prova>/sample.json`) está no
  `.gitignore`: a aprovação só existe no banco de desenvolvimento. Decidir se vale versionar.
- DPF 2014 e DEPEN 2015 (API do Cebraspe dá erro 500, tentado de novo diariamente) e concursos anteriores a
  2014 (`cespe.unb.br`, fora das fontes — incluir exige decisão).
- `emmoni coverage` previsto na especificação, ainda não implementado.
- Folga pequena em `facet_counts` sem filtros (281/300 ms), prevista na decisão 0002.

## Números
- Questões visíveis no esquema `api`: 1.188 (seed + as 18 provas aprovadas)
- Reais: 6.249 carregadas (39 concursos, 108 provas) · 5.043 `published` (todas com assunto) ·
  1.231 `review` (extração) · 40 `draft` · 282 duplicatas marcadas
- Provas: 18 aprovadas na amostragem; 90 sem amostragem; 5 não carregadas (DEPEN 2020, CBM/AL
  2017 básicos cargo 1, PCDF 2020 básicos, PM/TO 2020 QPE, PC/PB 2021 específicos cargo 8)
- Propostas do crawler pendentes: 0 · manifestos aprovados: 42 · rejeitados: 1
- Taxonomia: 56 disciplinas, 863 assuntos
- Contrato do front-end: **v1.1** (sem mudança)
