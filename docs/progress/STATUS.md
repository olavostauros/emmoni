# Status — atualizado em 2026-10-08

**Marco atual:** M5 — Mais bancas (SPECIFICATIONS.md §10). M0–M4 prontos (M4 em 2026-10-08).
Ainda não há crawler nem parser de outra banca; o trabalho do M5 até aqui ampliou o Cebraspe.

## Feito neste marco
- HTTP do `www.cespe.unb.br` autorizado pelo dono; fonte `cespe-unb` só com `fetch`
  (decisão 0017, `2026-10-08-cespe-unb-http.md`).
- OCR na etapa `extract` com revisão linha a linha pelo agente; PCDF 2020 básicos e PM/TO 2020 QPE
  publicados (decisão 0018).
- Parser do Cebraspe: `CREDIT_END`; as 16 provas afetadas reprocessadas, CBM/RO 2022 oficial
  reaprovada (`2026-10-08-credit-end.md`).
- Contexto do agente auditado: `AGENTS.md` alinhado ao SPECIFICATIONS.md, regra de sessões
  paralelas, este arquivo de volta ao formato do README (decisão 0019,
  `2026-10-08-contexto-do-agente.md`).

## Em andamento
- Nada em execução.

## Próximos passos
0. Manifestos dos concursos policiais antigos do `cespe-unb` (DPF 2004–2013, PRF 2013, PCs e PMs).
1. Começar o crawler e o parser de outra banca.
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
- CBM/AL 2017 básicos cargo 1 (erro de numeração no gabarito oficial) e PC/PB 2021 cargo 8 item 80
  (linha do gabarito ilegível) seguem fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (tentado de novo diariamente).
- Sessões paralelas compartilham o Postgres; a regra é de processo, sem trava (decisão 0019).

## Números
- Questões visíveis no esquema `api`: 5.062 reais, sem duplicatas e sem o seed (`docs/coverage.md`)
- Reais: 6.514 carregadas · 5.464 `published` · 1.050 `review`
- Provas: 111 aprovadas, com registro em `ingest/approvals/`; 24 de manifestos aprovados fora do
  banco, 21 delas de `pcpe-2016` e `pcientifica-pe-2016`
- Propostas do crawler pendentes: 0 · manifestos aprovados: 43 · rejeitados: 1
- Taxonomia: 56 disciplinas, 899 assuntos
- Contrato do front-end: **v1.2**
