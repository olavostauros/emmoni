# Status — atualizado em 2026-10-08 (M4 pronto; M2 reamostrado)

**Marco atual:** M5 — Mais bancas (não iniciado)
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato · M2 — Primeira ingestão · M3 — Crawling (2026-10-07) · M4 — Taxonomia e classificação (2026-10-08)

## Feito no M4 (pronto em 2026-10-08)
- Amostra de 50 classificações conferida pelo agente revisor em contexto separado: **49/50
  (98%)**; o único erro (pf-2021/agente q2) foi corrigido na origem e recarregado
  (registro `2026-10-08-m4-revisao-de-assuntos.md`).
- As 62 sem assunto confiante resolvidas: 2 faixas de disciplina corrigidas (pcpb-2021 cargo 6,
  pcgo-2016 cargo 2), 36 assuntos novos, 0 `draft` (registro `2026-10-08-sem-assunto.md`).
- Taxonomia ampliada para 863 assuntos; questão sem assunto confiante fica `draft` e volta às
  tarefas, e `review` passa a significar só defeito de extração (decisão 0010).
- Classificação das 108 provas pelo agente: 6.472 classificadas, 62 sem assunto confiante.
- Revisão humana substituída pela revisão do agente nos três pontos (decisão 0011).
- Pontas soltas do M3 (decisão 0012): crawler propõe um gabarito por bloco em caderno único
  (PCDF 2019), apaga propostas obsoletas de `_pending/`; SDS/PE 2016 entra como alias de evento
  da PC-PE → `pcpe-2016` proposto e aprovado pelo agente.

## Feito depois do M4
- Reamostragem das 18 provas do M2: 15 aprovadas de primeira; PF 2018 agente, escrivão e
  papiloscopista reprovadas, corrigidas (parser), reprocessadas e aprovadas na segunda amostra
  (decisão 0015, registro `2026-10-08-reamostragem-do-m2.md`). **108 de 108 provas aprovadas com o
  conteúdo atual do banco.**
- `emmoni ingest` segue para as provas seguintes quando uma dá `LoadError` (sai com código 1).

## Em andamento
- Nada em execução.

## Próximos passos
1. Começar o M5 (crawler e parser de outra banca).
2. `pcpe-2016` aprovado (sem ingestão): calibrar o parser nos cadernos de 2016, preencher
   `first_number` e `subjects_by_range` e ingerir.
3. Instalar o timer do systemd (`docs/operations.md`) na máquina que vai rodar o crawl diário.
4. Etapa `structure` e exportação de imagens para as questões em `review` por figura, fórmula e
   layout (1.231).
5. Negrito perdido nos enunciados do PF 2018 ("compreende", agente q19).

## Bloqueios e perguntas em aberto
- OCR (PDFs digitalizados) e itens sem gabarito legível: ver decisão 0009, adendo.
- SDS/PE Polícia Científica (2016) segue órgão candidato: não é da PC-PE (decisão 0012).
- DEPEN 2020: o gabarito de complementares (nível superior) ainda é acrescentado à mão; o nível
  do cargo não está na API.
- O registro de aprovação de provas (`data/review/<concurso>/<prova>/sample.json`) está no
  `.gitignore`: a aprovação só existe no banco de desenvolvimento. Decidir se vale versionar.
- DPF 2014 e DEPEN 2015 (API do Cebraspe dá erro 500, tentado de novo diariamente) e concursos anteriores a
  2014 (`cespe.unb.br`, fora das fontes — incluir exige decisão).
- Staging de 17 provas aprovadas diverge do parser atual: reprocessar exige reamostrar (decisão 0015).
- `emmoni coverage` previsto na especificação, ainda não implementado.
- Folga pequena em `facet_counts` sem filtros (281/300 ms), prevista na decisão 0002.

## Números
- Questões visíveis no esquema `api`: 4.994 (seed + as 108 provas aprovadas)
- Reais: 6.314 carregadas (39 concursos, 108 provas) · 5.295 `published` (todas com assunto) ·
  1.019 `review` (extração) · 0 `draft` · 282 duplicatas marcadas
- Provas: 108 aprovadas na amostragem (decisões 0014 e 0015); 5 não carregadas (DEPEN 2020, CBM/AL
  2017 básicos cargo 1, PCDF 2020 básicos, PM/TO 2020 QPE, PC/PB 2021 específicos cargo 8)
- Propostas do crawler pendentes: 0 · manifestos aprovados: 42 · rejeitados: 1
- Taxonomia: 56 disciplinas, 899 assuntos
- Contrato do front-end: **v1.1** (sem mudança)
