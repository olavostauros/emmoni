# Status — atualizado em 2026-10-13

**Marco atual:** M5 — Mais bancas (SPECIFICATION.md §10). M0–M4 prontos (M4 em 2026-10-08).
Ainda não há crawler nem parser de outra banca; o trabalho do M5 até aqui ampliou o Cebraspe.

## Feito neste marco
- HTTP do `www.cespe.unb.br` (decisão 0017); OCR com revisão do agente (decisão 0018); `CREDIT_END`
  e reprocessamento das 16 provas; sessões paralelas (decisão 0019).
- Site antigo do Cebraspe: `extract` com `legacy`, PF 2012 Agente publicado, disciplina `economia`
  (decisão 0020, `2026-10-08-pf-2012-site-antigo.md`).
- Provas aprovadas reprocessadas com o parser novo: 67 créditos emendados no banco, as 117 provas
  seguem publicadas sem reamostragem (`2026-10-08-reprocessamento-creditos.md`).
- API HTTP local por PostgREST (decisão 0021, contrato v1.3) e deploy no Google Cloud Run
  preparado, sem nada criado na nuvem (decisão 0022, `docs/DEPLOY.md`, agentes atlas e cerberus;
  `2026-10-08-api-http-e-deploy.md`).
- Capa do PM/AL 2021, fonte de símbolos, escape do `$` (decisão 0023, contrato v1.4) e "(ℓ.N)" em
  todos os cadernos; 13 provas reamostradas e reaprovadas (`2026-10-13-defeitos-e-cifrao.md`,
  `2026-10-13-referencia-de-linha.md`). No `main`.
- Trava do banco (decisão 0025) e ciclo autônomo (decisão 0026), ainda sem timer ligado
  (`2026-10-13-ciclo-autonomo.md`).

## Em andamento
- PF 2018 agente q51–56 e papiloscopista q48–50 em `review` por fórmula (símbolos sem mapeamento).
- Plantão: contrato v1.4 permite religar `$...$` (o `$` literal chega como `\$`).
- Deploy: passo 0 feito (2026-10-13); passos 1–7 pelo atlas, um por ciclo autônomo (decisão 0026).

## Próximos passos
0. Deploy (`docs/DEPLOY.md` §4), pelo atlas, um passo por ciclo: projeto `emmoni-prod` → contas →
   budget → corte → imagem seed → serviço privado → medição da ressalva do §2 → público com seed.
1. Crédito em três linhas ou mais: só as duas últimas são emendadas (PM/MA 2017 g39, INFOPEN do
   DEPEN). Corrigir no parser e reprocessar como em `2026-10-08-reprocessamento-creditos.md`.
2. Avaliar ligar o estilo pelas larguras (`legacy`) nos cadernos novos com fontes "TT…o00"
   (PC/PE 2023, PF 2025…): recupera itálico/negrito perdidos (inclui o negrito do PF 2018,
   "compreende", agente q19). Exige reprocessar e reamostrar.
3. Manifestos dos demais concursos policiais do `cespe-unb` (índice em
   `data/crawl/cespe-unb/concursos___antigos__default.asp`): começar por DPF 2012 (escrivão,
   delegado, perito, papiloscopista), DPF 2009, DPRF 2013, PC/DF 2013, DEPEN 2013.
4. Taxonomia: assuntos para PF 2012 q60, q62, q65 (sugestões em `topics.json`).
5. Começar o crawler e o parser de outra banca.
6. `pcpe-2016` e `pcientifica-pe-2016`: calibrar o parser, preencher `first_number` e
   `subjects_by_range` e ingerir.
7. Crawl diário: o ciclo autônomo roda `make crawl` uma vez por dia (o timer próprio de
   `docs/operations.md` fica dispensado enquanto o ciclo rodar).
8. Etapa `structure` e imagens para as questões em `review` por figura, fórmula e layout.
9. Amostra: incluir a página do comando quando ele está antes da página da questão (PCDF 2026 q96).
10. PM/MA 2017: 6 documentos fora do manifesto (decisão 0009): confirmar e silenciar no relatório.

## Bloqueios e perguntas em aberto
- Publicar as questões reais na API (imagem `all`) e no snapshot do Plantão: sim do dono.
- O `emmoni-prod` vai usar o mesmo crédito do Usher: PR #130 do Usher (automerge, 2026-10-13)
  registra no `CYBERSECURITY.md` de lá que o projeto é esperado e que o burn log lê o total da
  conta. Falta só o merge.
- CBM/AL 2017 básicos cargo 1 e PC/PB 2021 cargo 8 item 80 seguem fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (estão também no site antigo: tentar por lá).
- Sessões paralelas compartilham o Postgres, agora com trava (decisão 0025).
- Ciclo autônomo (decisão 0026): falta o dono pôr no `.claude/settings.json` as negações da
  decisão (`usher-prod`, `gcloud projects delete`, `gcloud billing accounts`, `git push --force`;
  o modo automático não deixa o agente editar as próprias permissões) e ligar `emmoni-ciclo.timer`. Esta é a fila do dono: o ciclo escreve aqui o que só ele decide.

## Números
- Questões visíveis no esquema `api`: 5.143 reais, sem duplicatas e sem o seed (`docs/coverage.md`)
- Reais: 6.634 carregadas · 5.545 `published` · 1.086 `review` · 3 `draft`; provas: 117 publicadas, 0 em `review`
- Provas: 112 aprovadas, com registro em `ingest/approvals/`; 24 de manifestos aprovados fora do
  banco, 21 delas de `pcpe-2016` e `pcientifica-pe-2016`
- Propostas do crawler pendentes: 0 · manifestos: 44 (1 do `cespe-unb`) · rejeitados: 1
- Taxonomia: 57 disciplinas, 911 assuntos
- Contrato do front-end: **v1.4**
