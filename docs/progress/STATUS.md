# Status — atualizado em 2026-10-15 (ciclo das 13:41)

**Marco atual:** M5 — Mais bancas (SPECIFICATION.md §10). M0–M4 prontos (M4 em 2026-10-08).
Ainda não há crawler nem parser de outra banca; o trabalho do M5 até aqui ampliou o Cebraspe.

## Feito neste marco
- HTTP do `www.cespe.unb.br` (0017); OCR com revisão do agente (0018); sessões paralelas (0019);
  site antigo do Cebraspe com `legacy` (0020, emendas até a (33)); API local por PostgREST
  (0021, contrato v1.4); deploy preparado (0022); trava do banco (0025); ciclo autônomo (0026);
  lab `oficina` (0029); figura citada sem imagem vai para `review` (0030); `review sample --seed`
  (0031); hífen de fim de linha (0032); impressão digital v2 (0033).
- Ciclos de 2026-10-13 e 2026-10-14: ver os registros `2026-10-13-*` e `2026-10-14-*`.
- Ciclos de 2026-10-15 00:16 e 08:41 (pararam no limite de sessão, sem registro próprio):
  emendas (19)–(28) da 0020, reaprovações r31–r48; todas as aprovações estão na impressão v2.
- Ciclo de 2026-10-15 13:41 (`2026-10-15-ciclo-site-antigo-2009-2013.md`): reamostragem r49 de
  8 provas; estilo conferido nas 12 provas sem `infer_font_styles` (fica desligado); 7 provas novas
  do site antigo publicadas — PRF 2013, PF 2009 agente e escrivão, PC/DF 2013 agente e escrivão,
  DEPEN 2013 básicos e específicos (emendas (29)–(33): nota de seção, fração empilhada, linha
  partida por ícone, glifos pelo desenho, lista ▸, faixa "Texto para os itens de X a Y").

## Em andamento
- Plantão: contrato v1.4; dados reais só pela API (decisão 0028).
- Deploy: passos 0–2 feitos; passo 3 parcial (tópico `emmoni-budget`; budget na fila do dono).
  Passo 8: sim do dono dado em 2026-10-13, depois do 7, só pela API (decisão 0028).
- PDFs do site antigo copiados de `data/crawl/cespe-unb/` para `data/raw/` só no checkout
  principal (sha256 conferido); outro checkout repete a cópia ou o `fetch` vai à rede.

## Próximos passos
1. Textos em `review` das provas novas: PC/DF 2013 agente g1 (poema "Pavio do destino", Q1–10,
   marca `layout`) e PF 2009 escrivão g74 (Q74–81, marca `formula`): tirar a marca se o texto
   estiver certo (hefesto) e o minos conferir. PC/DF 2013 agente Q21: cabeçalho de memorando de
   6 linhas centralizadas sai num parágrafo só (em `review`).
2. Amostra de assuntos dirigida às provas novas (itens de baixa confiança: PRF 2013 q63, q99–100;
   PF 2009 AFO; PC/DF 2013 informática forense) e às 6 do PF 2012 com assunto novo; curadoria
   `comunicacao_e_equipes` × `cultura_organizacional`.
3. Outros concursos do índice antigo do `cespe-unb` (só policiais): conferir DPRF 2008 e o que mais
   houver de cargo policial; DPF 2013/DPRF 2012 administrativos ficam fora (decisão 0009).
4. `pf-2012/agente` q84: tabela das q85–86 colada no enunciado; regra estreita sem quebrar os
   rótulos do circuito do PF 2012 papiloscopista q104–106.
5. `pcma-2017-apc` gerais (cargos 1/2 q13–14, cargo 5 q16–17) e `pcpb-2021` gerais 4 a 13 q12:
   teclas desenhadas sem mapeamento (U+FFFD); talvez a tabela de glifos da emenda (32) sirva.
6. Deploy passo 4 (caronte) depois que o budget existir.
7. Código em várias linhas como bloco; tabelas GFM (PF 2025 agente q107–110); LaTeX das fórmulas;
   expoente perdido ("k2", "m2", "105 Pa"); colchetes de fórmula do PRF 2013 p. 10.
8. PF 2012 agente g12 e papiloscopista g8: poema em duas colunas. cbmpa-2023-cfo/p1 1A6: subscrito
   de CH4/CS2. PF 2018 escrivão g97: "•" lido como "C". Ângulos "30o" (CBM/TO 2021 soldado) pedem
   decisão "°" × "º".
9. Começar o crawler e o parser de outra banca.
10. `pcpe-2016` e `pcientifica-pe-2016`: calibrar o parser e ingerir.
11. Etapa `structure` e imagens para as questões em `review` por figura, fórmula e layout.

## Bloqueios e perguntas em aberto
- **Ciclos parando no limite de sessão (dono)**: em 2026-10-15 os ciclos das 00:16, 05:40 e 08:41
  bateram no limite do plano ("You've hit your session limit"); o das 05:40 nem começou. As sobras
  foram para stash e este ciclo as recuperou. Espaçar o `emmoni-ciclo.timer` ou aceitar a perda.
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
  - `stash@{0}` ("ciclo 2026-10-15-1040: sobra"): as nove aprovações r48, commitadas em `9f645dd`;
  - `stash@{1}` ("ciclo 2026-10-15-0240: sobra"): aprovações já no `main` pelo r38 (`c7474e4`);
  - `stash@{2}` ("ciclo 2026-10-14-0227: sobra"): já em `9c5715b`;
  - `stash@{3}` ("ciclo 2026-10-13-2304: sobra"): o lote 1 do estilo, já em `976607e`;
  - `stash@{4}` ("ciclo 2026-10-13-1443: sobra"): o que o PF 2018 precisava já está em `2d970a3`.
- Plantão lendo a API em vez do snapshot real (decisão 0028): pedido enviado à sessão do Plantão
  em 2026-10-13; a escolha é de lá.
- DPF 2012 perito: o cargo não está em `db/catalog.yaml`.
- PC/PB 2021 cargo 8 item 80 segue fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (tentar pelo site antigo).

## Números
- Questões visíveis no esquema `api`: 6.259 (com o seed)
- Reais: 7.694 carregadas · 6.616 `published` · 1.078 `review` · 0 `draft`; provas: 123
  publicadas, nenhuma em `review`, mais 5 do seed
- Registros de aprovação em `ingest/approvals/`: 123 (todos na impressão v2)
- Propostas do crawler pendentes: 0 · rejeitados: 1 · último crawl: 2026-10-15 08:43
- Taxonomia: 57 disciplinas, 917 assuntos
- Contrato do front-end: **v1.4**
