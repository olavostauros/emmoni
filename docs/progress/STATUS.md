# Status — atualizado em 2026-10-14

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
- Ciclos de 2026-10-14 02:05 e 05:28 (`2026-10-14-ciclo-estilo-hifen-normalizacao.md`): auditoria
  E-011; estilo de fonte pequena e código inline (emendas da 0020); figura citada sem imagem vai
  para `review` (0030); `review sample --seed` (0031); justificativa pela cor (emenda da 0009);
  hífen de fim de linha é do original (0032); NFC e strip na gravação (check 080); estilo ligado em
  pcgo-2016, pmpa-2023, pcpb-2021, pcrj-2021, pcro-2022, cbmto-2022 oficial e pmro-2022. Cerca de
  30 provas reaprovadas por minos (sementes r2–r6).

## Em andamento
- Estilo por prova: ligado em pcal-2022, pces-2022, pcgo-2016, pmpa-2023-cfp/cfo, pcpb-2021,
  pcrj-2021, pcro-2022 (menos cargo 3 específicos), cbmto-2022 oficial, pmro-2022, pf-2018,
  pf-2021 delegado. As "20 provas que mudam texto ao reprocessar" eram o hífen (0032), já resolvido.
- Em `review`: `pmro-2022/objetiva` e `pmdf-2025/p2` (comando colado no parágrafo anterior).
- Plantão: contrato v1.4; dados reais só pela API (decisão 0028).
- Deploy: passos 0–2 feitos; passo 3 parcial (tópico `emmoni-budget` criado; budget na fila do
  dono). Passo 8: sim do dono dado em 2026-10-13, depois do 7, só pela API (decisão 0028).

## Próximos passos
1. `make crawl` (o último foi em 2026-10-13 10:24) e as propostas novas ao minos.
2. Hefesto: `_choice_paragraphs` com `_block_gap` (parágrafo por espaço vertical na múltipla
   escolha), com varredura em lote; depois minos em `pmro-2022/objetiva` (q41, q100) e
   `pmdf-2025/p2` (q76).
3. `review sample` com impressão digital que veja formatação e parágrafo (hoje mudança só de
   marcação, espaço ou parágrafo não devolve a prova a `review`). Até lá, minos amostrar as
   publicadas que mudaram sem amostra nova: 15 provas do `pcpb-2021` (só marcação), `pcro-2022`
   específicos cargos 1 e 4 e gerais cargo 3, `cbmro-2022` oficial q36/q38, `cbmto-2021` oficial
   q47, `pcce-2025` q64, `pcpb-2021` cargos 4 (q60) e 13 (q65).
4. Estilo nas provas restantes (lotes, hefesto → minos): `pcse-2021`, `pcce-2025` e os demais
   manifestos sem `infer_font_styles` (`pmdf-2025` não precisa: fontes com nome). `cbmto-2022/soldado` e `pcro-2022` cargo 3
   específicos: o estilo tira o título de disciplina colado na alternativa E e muda pendências
   (carregar e reamostrar).
5. Deploy passo 4 (caronte) depois que o budget existir.
6. PF 2012 agente g12 e papiloscopista g8: poema em duas colunas e números de verso (q12–16 /
   q8–12 em `review`). cbmpa-2023-cfo/p1 1A6: estilo do crédito e subscrito de CH4/CS2.
7. PF 2018 agente q93–96: preservar as linhas do programa (hoje spans de código soltos).
8. Amostra de assuntos dirigida para as 6 questões do PF 2012 com assunto novo; curadoria de
   `comunicacao_e_equipes` × `cultura_organizacional`.
9. Manifestos dos demais concursos policiais do `cespe-unb`: DPF 2009, DPRF 2013, PC/DF 2013,
   DEPEN 2013.
10. Começar o crawler e o parser de outra banca.
11. `pcpe-2016` e `pcientifica-pe-2016`: calibrar o parser e ingerir.
12. Etapa `structure` e imagens para as questões em `review` por figura, fórmula e layout
    (inclui as de figura citada da decisão 0030).
13. `pmma-2017` gerais cargo 5: `passage_key` diverge em 4 questões ao reprocessar.
14. PC/PB 2021 CG1A1-III: "matrícula n.º" | "1.234-56" partido e endereço juntado.
15. PM/MA 2017: 6 documentos fora do manifesto (decisão 0009): confirmar e silenciar.

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
- Stashes (descartar é do dono; nada deles falta no `main`):
  - `stash@{0}` ("ciclo 2026-10-14-0227: sobra"): o trabalho do hefesto interrompido, já
    aplicado e commitado em `9c5715b`;
  - `stash@{1}` ("ciclo 2026-10-13-2304: sobra"): o lote 1 do estilo, já em `976607e`;
  - `stash@{2}` ("ciclo 2026-10-13-1443: sobra"): o que o PF 2018 precisava já está em `2d970a3`.
- Plantão lendo a API em vez do snapshot real (decisão 0028): pedido enviado à sessão do Plantão
  em 2026-10-13; a escolha é de lá.
- DPF 2012 perito: o cargo não está em `db/catalog.yaml`.
- CBM/AL 2017 básicos cargo 1 e PC/PB 2021 cargo 8 item 80 seguem fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (tentar pelo site antigo).

## Números
- Questões visíveis no esquema `api`: 5.310 reais, sem duplicatas e sem o seed (`docs/coverage.md`)
- Reais: 6.929 carregadas · 5.806 `published` · 1.123 `review` · 0 `draft`; provas: 113
  publicadas, 2 em `review`
- Registros de aprovação em `ingest/approvals/`: 115
- Propostas do crawler pendentes: 0 · rejeitados: 1
- Taxonomia: 57 disciplinas, 917 assuntos
- Contrato do front-end: **v1.4**
