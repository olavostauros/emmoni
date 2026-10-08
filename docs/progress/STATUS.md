# Status — atualizado em 2026-10-08 (M4 pronto; bloqueios resolvidos)

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

## Feito depois do M4 — bloqueios (decisão 0016)
- Aprovações versionadas em `ingest/approvals/` (impressão digital do conteúdo visível); o `load`
  tira do `api` a prova cujo conteúdo visível mudou; `emmoni review restore` num banco novo.
- Polícia Científica/PE no catálogo (`policia_cientifica`, contrato v1.2); `pcientifica-pe-2016`
  aprovado, sem ingestão.
- `emmoni coverage` implementado; `facet_counts` numa passada (p95 194 ms sem filtros).
- 15 provas com staging divergente reprocessadas e reaprovadas; título de seção do CBM/TO corrigido.
- DEPEN 2020 carregada e publicada (gabarito CG2 de nível médio; cargo é de nível médio).
- Registro: `2026-10-08-bloqueios.md`.

## Em andamento
- Nada em execução.

## Próximos passos
1. Começar o M5 (crawler e parser de outra banca).
2. `pcpe-2016` e `pcientifica-pe-2016` (mesmos cadernos SDS/PE 2016): calibrar o parser, preencher
   `first_number` e `subjects_by_range` e ingerir.
3. Instalar o timer do systemd (`docs/operations.md`) na máquina que vai rodar o crawl diário.
4. Etapa `structure` e exportação de imagens para as questões em `review` por figura, fórmula e
   layout.
5. Negrito perdido nos enunciados do PF 2018 ("compreende", agente q19).
6. Amostra: incluir a página do comando quando ele está antes da página da questão (PCDF 2026 q96).
7. PM/MA 2017: o crawler acha 6 documentos fora do manifesto (provas de oficiais de saúde,
   excluídas de propósito — decisão 0009): confirmar e silenciar no relatório.

## Bloqueios e perguntas em aberto
- **`cespe.unb.br`** (concursos anteriores a 2014): o host só responde em HTTP (porta 80); o
  cliente é só HTTPS (decisão 0003). Incluir exige o dono do projeto aceitar uma exceção ao HTTPS.
- **OCR** (PCDF 2020 básicos, PM/TO 2020 QPE): falta `tesseract-data-por` e `ocrmypdf` na máquina
  (instalação do sistema, pelo dono).
- CBM/AL 2017 básicos cargo 1 (erro de numeração no gabarito oficial) e PC/PB 2021 cargo 8 item 80
  (linha do gabarito ilegível) seguem fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (tentado de novo diariamente).

## Números
- Questões visíveis no esquema `api`: 5.071 (seed + as 109 provas aprovadas); 5.006 reais sem
  duplicatas (`docs/coverage.md`)
- Reais: 6.339 carregadas (40 concursos, 109 provas) · 5.307 `published` · 1.032 `review`
- Provas: 109 aprovadas e com registro em `ingest/approvals/`; 26 de manifestos aprovados fora do
  banco (`docs/coverage.md`), 21 delas de `pcpe-2016` e `pcientifica-pe-2016`
- Propostas do crawler pendentes: 0 · manifestos aprovados: 43 · rejeitados: 1
- Taxonomia: 56 disciplinas, 899 assuntos
- Contrato do front-end: **v1.2** (novo valor de `career`, compatível)
