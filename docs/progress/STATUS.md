# Status — atualizado em 2026-10-08

**Marco atual:** M4 — Taxonomia e classificação — falta só a conferência humana da amostra de assuntos
**Próximo marco:** M5 — Mais bancas
**Últimos marcos concluídos:** M0 — Fundação · M1 — Esquema e contrato · M2 — Primeira ingestão · M3 — Crawling (2026-10-07)

## Feito neste marco
- Taxonomia ampliada para 863 assuntos; questão sem assunto confiante fica `draft` e volta às
  tarefas, e `review` passa a significar só defeito de extração (decisão 0010).
- Classificação das 108 provas pelo agente: 6.472 classificadas, 62 sem assunto confiante.
- `emmoni review topics --n 50` / `--report`: amostra gerada em `data/review/assuntos/`, sem
  vereditos (registro de 2026-10-08).
- Revisão humana substituída pela revisão do agente nos três pontos (decisão 0011).

## Em andamento
- Nada em execução.

## Próximos passos
1. **Agente revisor** (decisão 0011): conferir `data/review/assuntos/amostra.md` em contexto
   separado do `classify` e gravar `verdict` e `reviewed_by` em `amostra.json`;
   `emmoni review topics --report`. ≥ 90% fecha o M4.
2. Amostragem por prova pelo agente (`emmoni review sample` / `approve --by <modelo>`) das 90
   provas novas para publicá-las no `api`.
3. Os 62 sem assunto: conferir se a disciplina do manifesto está certa antes de criar assunto
   novo; depois reclassificar.
4. `ingest --step load` deveria seguir para as provas seguintes quando uma falha.
5. Instalar o timer do systemd (`docs/operations.md`) na máquina que vai rodar o crawl diário.
6. Etapa `structure` e exportação de imagens para as questões em `review` por figura, fórmula e
   layout (1.231).

## Bloqueios e perguntas em aberto
- OCR (PDFs digitalizados) e itens sem gabarito legível: ver decisão 0009, adendo.
- Proposta pendente que deixa de ser proposta (regra mudou) não é removida de `_pending/` pelo
  crawler: `pmto-2020-qps` ficou e foi rejeitada à mão. Decidir se o crawler apaga ou marca.
- SDS/PE (2016) continua fora do catálogo: a secretaria organizou concursos de PC-PE e de
  Polícia Científica; decidir se entra como alias de `pcpe`.
- PCDF 2019: um caderno com dois gabaritos definitivos (básicos e específicos); o manifesto aceita
  um gabarito por prova. Mudar o modelo ou juntar os PDFs à mão na aprovação.
- O registro de aprovação de provas (`data/review/<concurso>/<prova>/sample.json`) está no
  `.gitignore`: a aprovação só existe no banco de desenvolvimento. Decidir se vale versionar.
- DPF 2014 (API do Cebraspe dá erro 500, tentado de novo diariamente) e concursos anteriores a
  2014 (`cespe.unb.br`, fora das fontes — incluir exige decisão).
- `emmoni coverage` previsto na especificação, ainda não implementado.
- Folga pequena em `facet_counts` sem filtros (281/300 ms), prevista na decisão 0002.

## Números
- Questões visíveis no esquema `api`: 1.188 (seed + as 18 provas aprovadas)
- Reais: 6.249 carregadas (39 concursos, 108 provas) · 4.978 `published` (todas com assunto) ·
  1.231 `review` (extração) · 40 `draft` · 282 duplicatas marcadas
- Provas: 18 aprovadas na amostragem; 90 sem amostragem; 5 não carregadas (DEPEN 2020, CBM/AL
  2017 básicos cargo 1, PCDF 2020 básicos, PM/TO 2020 QPE, PC/PB 2021 específicos cargo 8)
- Propostas do crawler pendentes: 0 · manifestos aprovados: 41 · rejeitados: 1
- Taxonomia: 56 disciplinas, 863 assuntos
- Contrato do front-end: **v1.1** (sem mudança)
