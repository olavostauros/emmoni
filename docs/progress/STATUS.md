# Status — atualizado em 2026-10-13

**Marco atual:** M5 — Mais bancas (SPECIFICATION.md §10). M0–M4 prontos (M4 em 2026-10-08).
Ainda não há crawler nem parser de outra banca; o trabalho do M5 até aqui ampliou o Cebraspe.

## Feito neste marco
- HTTP do `www.cespe.unb.br` (decisão 0017); OCR com revisão do agente (decisão 0018); `CREDIT_END`
  e reprocessamento das 16 provas; sessões paralelas (decisão 0019).
- Site antigo do Cebraspe: `extract` com `legacy`, PF 2012 publicado (decisão 0020).
- API HTTP local por PostgREST (decisão 0021, contrato v1.3); deploy preparado (decisão 0022).
- Capa do PM/AL 2021, fonte de símbolos, escape do `$` (decisão 0023, contrato v1.4), "(ℓ.N)".
- Trava do banco (decisão 0025), ciclo autônomo (decisão 0026), lab `oficina` (decisão 0029).
- Ciclo das 17:44 (`2026-10-13-ciclo-pf-2012-pf-2021.md`): deploy passo 2 feito; E-009/E-010
  corrigidos no plano; PF 2012 delegado q106 e escrivão q57 publicados, parágrafo por espaço e
  código inline; `infer_font_styles` por prova (emenda da 0020); PF 2012 delegado/escrivão,
  PF 2021 delegado e PF 2018 papiloscopista reaprovados por minos.
- Ciclo das 22:40 (`2026-10-13-ciclo-pf-2018-agente-estilos.md`): PF 2018 agente publicado
  (crédito inteiro; merge do branch do crédito e o útil do `stash@{0}`); deploy passo 3 parcial
  (tópico); 6 assuntos novos (917); `infer_font_styles` lote 1 (PC/AL e PC/ES 2022) aprovado.

## Em andamento
- `infer_font_styles` em lotes: lote 1 feito (PC/AL 2022, PC/ES 2022; 47 questões). Restam 54
  provas limpas (666 questões, só marcação) e 20 provas (318 questões) em que o reprocessamento
  muda também texto ou pendências (cbmal-2017, cbmpa-2023, cbmro-2022, cbmto-2021/2022,
  depen-2020, pcma-2017-delegado, pmsc-2023, parte de pcma-2017-apc, pcpb-2021, pcpe-2023,
  pcro-2022, prf-2021): causa não investigada.
- PF 2018 agente q51–56 e papiloscopista q48–50 em `review` por fórmula.
- Plantão: contrato v1.4; dados reais só pela API (decisão 0028).
- Deploy: passos 0–2 feitos; passo 3 parcial (tópico `emmoni-budget` criado; budget na fila do
  dono). Passo 8: sim do dono dado em 2026-10-13, depois do 7, só pela API (decisão 0028).

## Próximos passos
1. `infer_font_styles` lote 2 (hefesto → minos): `pcgo-2016` (3 provas) e `pmpa-2023-cfp` (2);
   depois `pmpa-2023-cfo`, `pcse-2021`, `pcce-2025`, `pmro-2022`, `pcrj-2021`.
2. Hefesto: investigar por que 20 provas mudam texto/pendências ao reprocessar (estilo ou parser
   posterior à última carga).
3. Deploy passo 4 (caronte) depois que o budget existir.
4. PF 2012 agente g12 e papiloscopista g8: poema em duas colunas misturadas e números de verso no
   texto (q12–16 / q8–12 em `review`). cbmpa-2023-cfo/p1 1A6: estilo do crédito e subscrito de
   CH4/CS2 (q40–42 em `review`).
5. Amostra de assuntos dirigida (ou versionar `data/review/assuntos/amostra.json` antes de novo
   `review topics`) para as 6 questões do PF 2012 com assunto novo; curadoria de
   `comunicacao_e_equipes` × `cultura_organizacional`.
6. Manifestos dos demais concursos policiais do `cespe-unb`: DPF 2009, DPRF 2013, PC/DF 2013,
   DEPEN 2013.
7. `review sample` com semente e impressão digital que veja formatação (hoje mudança só de
   formatação não devolve a prova a `review`).
8. Começar o crawler e o parser de outra banca.
9. `pcpe-2016` e `pcientifica-pe-2016`: calibrar o parser e ingerir.
10. Crawl diário pelo ciclo autônomo (`make crawl` uma vez por dia; último em 2026-10-13 10:24).
11. Etapa `structure` e imagens para as questões em `review` por figura, fórmula e layout
    (inclui "PvQ" do PF 2012 q40 e agente q53).
12. PC/PB 2021 CG1A1-III: "matrícula n.º" | "1.234-56" partido e endereço juntado.
13. PM/MA 2017: 6 documentos fora do manifesto (decisão 0009): confirmar e silenciar.
14. Código inline para trechos monoespaçados (PC/AL 2022 gerais q25, PC/ES 2022 gerais q14).

## Bloqueios e perguntas em aberto
- **Budget do passo 3 do deploy (dono, R$ 0)**: o tópico `emmoni-budget` já existe; o
  `gcloud billing budgets create` (e o `list`) foi negado pela permissão da sessão em 2026-10-13.
  O deploy para aqui (o corte do passo 4 depende do budget). Rodar à mão, ou liberar o comando:
  `gcloud billing budgets create --billing-account=01F985-1C44C6-40CDE9 --display-name=emmoni-monthly --budget-amount=40BRL --filter-projects=projects/emmoni-prod --credit-types-treatment=exclude-all-credits --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 --threshold-rule=percent=1.0,basis=forecasted-spend --notifications-rule-pubsub-topic=projects/emmoni-prod/topics/emmoni-budget`
- **Remoções na nuvem (dono, R$ 0)**, `emmoni-prod`:
  - E-003: `gcloud projects remove-iam-policy-binding emmoni-prod --role=roles/cloudbuild.builds.builder --member=serviceAccount:27333211980@cloudbuild.gserviceaccount.com`
  - E-002: `gcloud services disable source.googleapis.com --project=emmoni-prod`
  - E-010 (depois do passo 4): tirar `roles/artifactregistry.writer` da `emmoni-build` no projeto.
  - E-009 (depois do passo 6): tirar `emmoniIngressCap` da `emmoni-budget-cap` no projeto.
  Os comandos completos estão no `DEPLOY.md`, passo 2. E-009 e E-010 são pré-condição do passo 7.
- **Commit do lote 1 do estilo negado** pelo classificador de permissões da sessão (Modify Shared
  Resources) em 2026-10-13 23:03. Ficaram no working tree, sem commit, aprovados por minos e já no
  banco: `ingest/manifests/pcal-2022.yaml`, `ingest/manifests/pces-2022.yaml` e os 4 arquivos em
  `ingest/approvals/pcal-2022/` e `ingest/approvals/pces-2022/`. O dono commita ou libera.
- `stash@{0}` ("ciclo 2026-10-13-1443: sobra"): tudo o que o PF 2018 precisava já está no `main`
  (`2d970a3`); descartar o stash é do dono.
- Plantão lendo a API em vez do snapshot real (decisão 0028): pedido enviado à sessão do Plantão
  em 2026-10-13; a escolha é de lá.
- DPF 2012 perito: o cargo não está em `db/catalog.yaml`.
- CBM/AL 2017 básicos cargo 1 e PC/PB 2021 cargo 8 item 80 seguem fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (tentar pelo site antigo).

## Números
- Questões visíveis no esquema `api`: 5.443 reais, sem duplicatas e sem o seed (`docs/coverage.md`)
- Reais: 6.994 carregadas · 5.875 `published` · 1.119 `review` · 0 `draft`; provas: 120
  publicadas, 0 em `review`
- Registros de aprovação em `ingest/approvals/`: 115
- Propostas do crawler pendentes: 0 · rejeitados: 1
- Taxonomia: 57 disciplinas, 917 assuntos
- Contrato do front-end: **v1.4**
