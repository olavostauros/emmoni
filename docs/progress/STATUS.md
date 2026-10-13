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

## Em andamento
- **`pf-2018/agente` em `review`** (fora da API): minos reprovou (crédito do Poe partido, q15, 19,
  20, 22). Correção no branch `ciclo/2026-10-13-credito-justificado`, não aplicada: o banco do
  PF 2018 foi extraído com código do `stash@{0}` ("ciclo 2026-10-13-1443: sobra"), que não está
  no `main`.
- PF 2018 agente q51–56 e papiloscopista q48–50 em `review` por fórmula.
- Plantão: contrato v1.4; dados reais só pela API (decisão 0028).
- Deploy: passos 0–2 feitos; passo 3 (tópico e budget) é o próximo, pelo caronte, um por ciclo.
  Passo 8: sim do dono dado em 2026-10-13, depois do 7, só pela API (decisão 0028).

## Próximos passos
1. Hefesto: aplicar do `stash@{0}` o que o PF 2018 precisa (provavelmente só
   `infer_font_styles: true` no `ingest/manifests/pf-2018.yaml`, já que a opção existe no
   `main`), fazer merge de `ciclo/2026-10-13-credito-justificado`, `make gates`, reprocessar
   `pf-2018/agente` e o papiloscopista, amostra com `--also 15 19 20 22`; minos revisa. Depois,
   reprocessar só no texto PF 2012 agente/papiloscopista g12/g8 e CBM/AL 2017 básicos (créditos).
2. Deploy passo 3 (caronte): tópico `emmoni-budget` e budget `emmoni-monthly`.
3. Ligar `infer_font_styles` nas 80 provas publicadas que ganham estilo (742 questões; lista em
   comparação do hefesto): reprocessar e reamostrar em lotes.
4. Taxonomia: assuntos para PF 2012 agente q60, q62, q65, escrivão q63 ("Cultura
   organizacional"), delegado q110 ("Relações diplomáticas e consulares") e q117 ("Evolução
   histórica do direito comercial").
5. Manifestos dos demais concursos policiais do `cespe-unb`: DPF 2009, DPRF 2013, PC/DF 2013,
   DEPEN 2013.
6. `review sample` com semente (hoje o sorteio é fixo por prova) e impressão digital que veja
   formatação (hoje mudança só de formatação não devolve a prova a `review`).
7. Começar o crawler e o parser de outra banca.
8. `pcpe-2016` e `pcientifica-pe-2016`: calibrar o parser e ingerir.
9. Crawl diário pelo ciclo autônomo (`make crawl` uma vez por dia).
10. Etapa `structure` e imagens para as questões em `review` por figura, fórmula e layout
    (inclui "PvQ" do PF 2012 q40 e agente q53).
11. PC/PB 2021 CG1A1-III: "matrícula n.º" | "1.234-56" partido e endereço juntado.
12. PM/MA 2017: 6 documentos fora do manifesto (decisão 0009): confirmar e silenciar.

## Bloqueios e perguntas em aberto
- **Permissão da sessão para o passo 3 do deploy**: `gcloud billing budgets list` foi negado
  neste ciclo; o `billing budgets create` do passo 3 provavelmente também será. Sem ele o deploy
  para no passo 3. O dono decide liberar ou rodar o passo à mão.
- **Remoções na nuvem (dono, R$ 0)**, `emmoni-prod`:
  - E-003: `gcloud projects remove-iam-policy-binding emmoni-prod --role=roles/cloudbuild.builds.builder --member=serviceAccount:27333211980@cloudbuild.gserviceaccount.com`
  - E-002: `gcloud services disable source.googleapis.com --project=emmoni-prod`
  - E-010 (depois do passo 4): tirar `roles/artifactregistry.writer` da `emmoni-build` no projeto.
  - E-009 (depois do passo 6): tirar `emmoniIngressCap` da `emmoni-budget-cap` no projeto.
  Os comandos completos estão no `DEPLOY.md`, passo 2. E-009 e E-010 são pré-condição do passo 7.
- `stash@{0}` ("ciclo 2026-10-13-1443: sobra"): o próximo ciclo aproveita o que o PF 2018 precisa;
  descartar o stash depois é do dono.
- Plantão lendo a API em vez do snapshot real (decisão 0028): pedido enviado à sessão do Plantão
  em 2026-10-13; a escolha é de lá.
- DPF 2012 perito: o cargo não está em `db/catalog.yaml`.
- CBM/AL 2017 básicos cargo 1 e PC/PB 2021 cargo 8 item 80 seguem fora.
- DPF 2014 e DEPEN 2015: API do Cebraspe dá erro 500 (tentar pelo site antigo).

## Números
- Questões visíveis no esquema `api`: 5.341 reais, sem duplicatas e sem o seed (`docs/coverage.md`)
- Reais: 6.994 carregadas · 5.869 `published` · 1.119 `review` · 6 `draft`; provas: 119
  publicadas, 1 em `review` (`pf-2018/agente`)
- Registros de aprovação em `ingest/approvals/`: 115 (o do `pf-2018/agente` não vale mais)
- Propostas do crawler pendentes: 0 · rejeitados: 1
- Taxonomia: 57 disciplinas, 911 assuntos
- Contrato do front-end: **v1.4**
