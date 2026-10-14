# Status — atualizado em 2026-10-14 (ciclo das 14:53)

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
- Ciclo de 2026-10-14 10:01 (`2026-10-14-ciclo-paragrafo-multipla-escolha.md`): crawl sem
  propostas; parágrafo por espaço na múltipla escolha; citação/item recuados, referência à
  direita, travessão, foto abaixo do título (`figure`), linha de código, URL partida, régua de
  cabeçalho; estilo em pcce-2025, pcpe-2023, pcro-2022 cargo 3, pcma-2017, pmal-2021 oficial,
  cbmro-2022 oficial e pf-2025. 27 aprovações de minos (sementes r7–r12); `pmro-2022` e
  `pmdf-2025/p2` saíram de `review`.
- Ciclo de 2026-10-14 14:53 (`2026-10-14-ciclo-texto-base-estilo-impressao-v2.md`): texto-base
  sem rótulo depois da alternativa E (emenda da 0013); linhas com rótulo, versos em estrofe,
  rótulo colado, texto branco invisível, 2ª língua estrangeira, fonte simulada do Distiller
  (emendas (8)–(13) da 0020); check 090; impressão digital v2 (decisão 0033); estilo em pmsc-2023
  soldado, pcse-2021, pmal-2021 soldado, cbmto-2022 soldado, cbmal-2017, cbmto-2021, cbmpa-2023-cfp.
  39 aprovações de minos (r13–r22); nenhuma prova real em `review`.

## Em andamento
- Estilo por prova ligado em: pcal-2022, pces-2022, pcgo-2016, pmpa-2023-cfp/cfo, pcpb-2021,
  pcrj-2021, pcro-2022, cbmto-2021, cbmto-2022, pmro-2022, pf-2018, pf-2021 delegado, pcce-2025,
  pcpe-2023, pcma-2017-apc, pcma-2017-delegado, pmal-2021, cbmro-2022 oficial, pf-2025,
  pmsc-2023-soldado, pcse-2021, cbmal-2017, cbmpa-2023-cfp.
- Impressão digital v2 (decisão 0033): 19 das 115 aprovações já estão na v2; as outras 96 (v1) não
  voltam a `review` quando só a marcação ou o parágrafo muda — por isso a reamostragem do item 3.
- Plantão: contrato v1.4; dados reais só pela API (decisão 0028).
- Deploy: passos 0–2 feitos; passo 3 parcial (tópico `emmoni-budget`; budget na fila do dono).
  Passo 8: sim do dono dado em 2026-10-13, depois do 7, só pela API (decisão 0028).

## Próximos passos
1. Hefesto: reprovação r22 de `pcpb-2021/conhecimentos-especificos-para-o-cargo-de-escrivao-de-policia`
   (q52, q50 pág. 7): "n.o" com o "o" sobrescrito vira "n.º" (e "ª"), em lote; candidatas no
   staging: `pcpb-2021` cargos 1 e 3, `pf-2025/escrivao-especificos`, `pcdf-2020` básicos,
   `cbmal-2021` oficial. Depois minos com semente nova (≠ r2–r22).
2. CBM/AL 2017 básicos cargo 1: itens 49–50 perdidos depois de "P:"/"Q:" do item 48 (gabarito com 45
   itens para 43 questões).
3. Reamostrar (minos, semente nova) as aprovações v1 mais antigas, em lotes de ~6, para passá-las à
   v2: a partir de `pmal-2017` específicos soldado, `pmma-2017` gerais/específicos cargo 5,
   `pcpe-2023` P1 cargos 1 e 3, `cbmpa-2023-cfo/p1`, `pcal-2021/escrivao`, `pmsc-2023-oficial` ...
   (lista: `grep -L fingerprint_version -r ingest/approvals`, ordenada por `approved_at`).
4. Estilo nas provas restantes sem `infer_font_styles` (lotes, hefesto → minos); `pmdf-2025` não
   precisa. Título colado na alternativa E: cbmpa-2023-cfo p1 q25, cbmto-2021 soldado q30.
5. Tirar a marca "layout" de versos já reconhecidos como estrofe (cbmal-2017 específicos cargo 2
   q114–116, "O Xote das meninas").
6. `pcma-2017-apc` gerais (cargos 1/2 q13–14, cargo 5 q16–17): teclas desenhadas sem mapeamento
   (U+FFFD, fonte `TT333o00`), revisão em `ingest/ocr/` contra a imagem; seguem em `review`.
7. Manifestos aprovados com documentos novos fora do manifesto: `pces-2022` (gabarito preliminar
   CG1_01) e `pmma-2017` (359_PMMA_001–003): incorporar ou registrar por que não entram.
8. Deploy passo 4 (caronte) depois que o budget existir.
9. Código em várias linhas como bloco (PF 2018 agente q93–96, PF 2025 bloco II g91); tabelas GFM
   (PF 2025 agente g107, q107–110); LaTeX das fórmulas (PF 2025 papiloscopista q105/q110);
   expoente perdido ("k2", "m2").
10. PF 2012 agente g12 e papiloscopista g8: poema em duas colunas e números de verso.
    cbmpa-2023-cfo/p1 1A6: estilo do crédito e subscrito de CH4/CS2.
11. Amostra de assuntos dirigida para as 6 questões do PF 2012 com assunto novo; curadoria de
    `comunicacao_e_equipes` × `cultura_organizacional`.
12. Manifestos dos demais concursos policiais do `cespe-unb`: DPF 2009, DPRF 2013, PC/DF 2013,
    DEPEN 2013.
13. Começar o crawler e o parser de outra banca.
14. `pcpe-2016` e `pcientifica-pe-2016`: calibrar o parser e ingerir (staging do pcientifica fora
    de sincronia, q29/q30).
15. Etapa `structure` e imagens para as questões em `review` por figura, fórmula e layout.
16. `pmma-2017` gerais cargo 5: `passage_key` diverge em 4 questões ao reprocessar (staging fora de
    sincronia com o HEAD).
17. PC/PB 2021 CG1A1-III: "matrícula n.º" | "1.234-56" partido e endereço juntado.

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
- Questões visíveis no esquema `api`: 5.535 (com o seed)
- Reais: 6.994 carregadas · 5.902 `published` · 1.092 `review` · 0 `draft`; provas: 115
  publicadas, 0 em `review` (mais 5 do seed)
- Registros de aprovação em `ingest/approvals/`: 115 (19 na impressão v2)
- Propostas do crawler pendentes: 0 · rejeitados: 1 · último crawl: 2026-10-14 10:25
- Taxonomia: 57 disciplinas, 917 assuntos
- Contrato do front-end: **v1.4**
