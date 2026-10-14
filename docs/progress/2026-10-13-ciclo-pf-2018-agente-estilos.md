# 2026-10-13 — Ciclo autônomo das 22:40: PF 2018 agente, taxonomia, estilo (lote 1), deploy passo 3

**Marco:** M5

Ciclo autônomo (decisão 0026), sem o dono. O último `make crawl` era de 2026-10-13 10:24, com menos
de 24 h, então não houve crawl.

## O que foi feito
- **PF 2018 agente** (hefesto, `2d970a3`): merge de `ciclo/2026-10-13-credito-justificado`. Do
  `stash@{0}` vieram só três coisas: o `CREDIT_END` com "(tradução livre, com adaptações)", a regra
  do "*In*:" do crédito em `_font_styles` e `infer_font_styles: true` nas 4 provas do
  `pf-2018.yaml`. O `STYLED_CONTESTS`, a 0030 e o teste não versionado ficaram de fora, porque a
  emenda da 0020 já cobre isso. Houve um adendo na decisão 0020.
  - Foram reprocessadas `pf-2018/agente`, `pf-2012/agente`, `pf-2012-papiloscopista` e
    `cbmpa-2023-cfo/p1`. Nessas três últimas mudou só o crédito, e elas seguem publicadas.
  - O minos aprovou `pf-2018/agente` (`5d655b2`): amostra de 11 com as q9, 15, 19, 20 e 22, 11 ok,
    e 96 questões visíveis.
- **Deploy passo 3, parcial** (caronte, `5d655b2`): o tópico `emmoni-budget` foi criado, com label
  `emmoni=prod`. O `gcloud billing budgets create` foi negado pela permissão da sessão, e o
  comando foi para a fila do dono. O `audit.py --cloud` deu 30 verificações e 3 falhas, todas já
  na fila (E-002, E-003, E-009/E-010).
- **Taxonomia** (hefesto, `7ad4ffe`): 6 assuntos novos (911 → 917). Agente q60, q62, q65,
  escrivão q63, delegado q110 e q117 passaram de `draft` a `published`. A cobertura foi
  regenerada: 5.443 publicadas.
- **`infer_font_styles`, lote 1** (hefesto): `pcal-2022` e `pces-2022`, 4 provas. 47 questões
  ganham negrito ou itálico, e o texto não muda.
  - O minos reamostrou e aprovou as quatro: 66 conferidas, 66 ok.
  - Os registros de aprovação e os manifestos ficaram **sem commit**, porque o commit desse lote
    foi negado pelo classificador de permissões da sessão. Ver "Problemas".

Todas as cargas foram feitas no checkout principal (sem worktree), sobre o `main` de cada commit
acima. O lote 1 foi carregado sobre `7ad4ffe` mais os dois manifestos.

## Verificação
- `make gates`, no fechamento: passou. Foram 512 testes, e o `emmoni check` rodou 7 checagens com
  0 violações.
- Não foi verificado:
  - a amostra de assuntos das 6 questões novas. O `review topics` sorteia 50 questões no total e
    sobrescreveria a `amostra.json` do M4, que não está no git;
  - o gasto e o crédito do mês, que o caronte não leu porque está sem Chrome. O esperado é
    R$ 0.

## Problemas encontrados
- **Commit negado**: o commit do lote 1 (manifestos `pcal-2022.yaml` e `pces-2022.yaml`, mais 4
  arquivos em `ingest/approvals/pcal-2022/` e `ingest/approvals/pces-2022/`) foi negado pelo
  classificador de permissões (Modify Shared Resources). O banco já tem o estilo aprovado. Não
  comecei outro lote.
- **Minos, na leitura**:
  - os poemas do PF 2012 agente g12 e do papiloscopista g8 têm as colunas misturadas e os números
    de verso no texto. As q12–16 e q8–12 estão em `review`, e nada disso foi publicado;
  - o crédito do 1A6 do cbmpa-2023-cfo/p1 está sem negrito e itálico, e CH4 e CS2 estão sem
    subscrito. As q40–42 estão em `review`;
  - nas q25 do PC/AL 2022 gerais e q14 do PC/ES 2022 gerais, trechos em fonte monoespaçada estão
    sem código inline. O texto confere.
- O hefesto comparou o estilo nas 106 provas publicadas de fora do `cespe-unb`:
  - 54 provas (666 questões) mudam só a marcação;
  - 20 provas (318 questões) mudam também o texto ou as pendências, e a causa não foi
    investigada;
  - 28 provas não mudam.
- `comunicacao_e_equipes` ("…e cultura organizacional") se sobrepõe ao novo
  `cultura_organizacional`, o que fica para curadoria.

## Próximo passo
- Lote 2 do estilo: `pcgo-2016` (3 provas) e `pmpa-2023-cfp` (2 provas).
