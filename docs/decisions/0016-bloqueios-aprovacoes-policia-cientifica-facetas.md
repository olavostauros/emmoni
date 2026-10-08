# 0016 — Bloqueios: aprovações versionadas, Polícia Científica, facetas numa passada

**Data:** 2026-10-08 · **Marco:** antes do M5

## Contexto

O STATUS listava bloqueios e perguntas em aberto. O dono do projeto decidiu três deles
(2026-10-08): versionar as aprovações de prova, incluir a Polícia Científica de PE no catálogo e
incluir `cespe.unb.br` nas fontes. Os demais eram de engenharia.

## Decisões

1. **Aprovação de prova versionada** em `ingest/approvals/<concurso>/<prova>.json`: questões
   sorteadas, quem aprovou, quando, e a **impressão digital** do conteúdo aprovado — por questão,
   número, `statement_hash` (enunciado, alternativas e texto-base), gabarito final, status do
   gabarito, disciplina e se está em `review`. Assuntos ficam de fora: têm amostragem própria.
   - Depois de cada `load`, `review.reconcile` acerta `exam.publish_status`: conteúdo com a
     impressão aprovada → `published`; prova publicada cujo conteúdo mudou (ou sem registro) →
     `review` até nova amostragem (aplica automaticamente o item 1 da decisão 0015).
   - `emmoni review restore` republica, num banco novo, as provas que conferem.
   - As 108 provas aprovadas ganharam registro com a impressão do conteúdo atual do banco, que é o
     conteúdo aprovado (decisões 0014 e 0015). `data/review/` continua fora do git (amostras, PNGs).
2. **Polícia Científica de Pernambuco** (`pcientifica-pe`) entra no catálogo como órgão próprio,
   fora da PC-PE, com o alias de evento `SDS_PE_16_CIENTIFICA` e os cargos de perito criminal,
   médico legista e os três auxiliares (nível médio).
   - Nova carreira **`policia_cientifica`** (perícia oficial fora da Polícia Civil). Mudança
     compatível no contrato: **v1.2**.
   - Crawler: rótulo "CONHECIMENTOS GERAIS PARA TODAS AS ÁREAS" é prova comum; quando o concurso
     tem mais de uma série de cadernos (prefixo numérico do arquivo: 259 nível médio, 260 nível
     superior), a prova comum vai só para os cargos das outras provas da mesma série, e a série
     entra no slug. Era o ajuste feito à mão no `pcpe-2016` (séries 257/258).
   - Proposta `pcientifica-pe-2016` aprovada pelo agente (claude-opus-5-5), com as provas comuns
     corrigidas à mão (a proposta era anterior à regra das séries). Ingestão pendente: falta
     calibrar `first_number` e `subjects_by_range`, como no `pcpe-2016`.
3. **`cespe.unb.br`: não entra ainda.** O host `www.cespe.unb.br` só aceita HTTP (porta 80; a 443
   recusa conexão) e o cliente é só HTTPS (decisão 0003). Incluir exige uma exceção à regra do
   HTTPS, que fica para o dono do projeto decidir; nenhuma requisição HTTP foi feita ao host.
4. **`facet_counts` numa passada** (prevista na decisão 0002): as linhas que atendem a todos os
   filtros são materializadas uma vez, só com ids; cada faceta cujo filtro não está ativo é
   contada sobre elas, e os nomes entram depois da agregação. Facetas com filtro ativo
   (contagem disjuntiva) leem as tabelas de novo. Resultado idêntico ao da função anterior em 30
   combinações de filtros e texto no banco de desenvolvimento.

## Consequências

- `make bench` (100 mil questões): `facet_counts` sem filtros p50 275 → 175 ms, p95 2.185 →
  194 ms; com banca p95 1.455 → 89 ms. Os picos de p95 da função antiga (8 consultas por chamada)
  sumiram.
- Reprocessar uma prova aprovada agora a tira do esquema `api` se o conteúdo mudar. As 17 provas
  cujo staging diverge do parser atual (decisão 0015) podem ser reprocessadas sem risco de
  publicar conteúdo não conferido.
- `emmoni coverage` implementado (SPECIFICATION.md §8); `docs/coverage.md` é gerado.

## Adendo (mesma data): reprocessamento, DEPEN 2020 e títulos de seção

5. **Impressão digital só do que o `api` mostra.** Questão em `review` entra só com o número e a
   pendência: corrigir o texto de uma questão escondida não tira a prova do ar; sair da revisão
   tira (muda o que o `api` mostra). Os 109 registros foram migrados conferindo antes a impressão
   antiga contra o banco; o único que não conferia (CBM/TO 2022 soldado, reprovado) ficou como
   estava.
6. **`emmoni review sample --also N...`**: questões além do sorteio. Na reamostragem de prova
   reprocessada entram as questões que mudaram e são publicáveis — o sorteio determinístico
   repetiria as já conferidas.
7. **DEPEN 2020**: o cargo 8 (agente federal de execução penal) é de **nível médio**. Os itens
   81–120 são os complementares de nível médio (gabarito `..._CG2_00`, 81–120), não os de nível
   superior (`..._CG1_00`, 91–120) que o manifesto usava — daí os "itens 81–90 sem gabarito".
   Manifesto e catálogo (`education_level: medio`) corrigidos; a prova carrega inteira.
8. **Título de seção "Conhecimentos ..." sem negrito, em corpo maior** (CBM/TO 2021 e 2022, 12–15
   pt contra 10 pt), inclusive quebrado em duas linhas, é título: não gruda mais na última
   alternativa da coluna anterior. Com o parser antes e depois, só mudam as 4 questões visadas.
