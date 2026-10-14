# 2026-10-14 — Ciclo autônomo das 10:01: parágrafo na múltipla escolha e rodadas de reamostragem

**Marco:** M5

Ciclo autônomo (decisão 0026), sem o dono. Coordenadora → hefesto/minos em turnos, nunca os
dois ao mesmo tempo no banco. Tudo carregado a partir do checkout principal (`main`), sem
worktree; cada carga foi feita sobre o HEAD indicado mais as mudanças que viraram o commit seguinte.

## O que foi feito
- **Crawl diário** (hefesto, 10:25): 3 requisições, 0 bloqueios, 0 propostas novas. Os mesmos
  HTTP 500 de `DEPEN_15` e `DPF_14_AGENTE`. Documentos fora do manifesto, já vistos em 2026-10-13:
  `pces-2022` (gabarito preliminar CG1_01) e `pmma-2017` (cadernos e gabaritos 359_PMMA_001–003).
- **Parágrafo por espaço vertical na múltipla escolha** (`ae2d144`): `_block_gap` em
  `_choice_paragraphs`; 115 quebras novas em 48 provas, só parágrafo.
- **Correções das reprovações do minos**, em quatro rodadas:
  - `21dec80`: citação e item recuados num parágrafo só (`_indented_block_goes_on`); estilo em
    `pcce-2025`, `pcpe-2023` e `pcro-2022` cargo 3 (este perde o título colado na alternativa E).
  - `cdf11a2`: referência alinhada à direita (`_credit_right_aligned`), travessão no item, título
    em duas linhas; estilo no `pcma-2017-apc` e no `pcma-2017-delegado`.
  - `5a2fda2`: foto logo abaixo do título "Questão N" marca a questão (`figure`); linha de código
    do item em parágrafo próprio; URL partida juntada sem espaço; estilo em `pmal-2021` oficial e
    `cbmro-2022` oficial. Cinco questões publicadas com imagem não extraída foram para `review`.
  - `7110239`: crédito à direita com a 1ª linha na margem; "out.–dez." sem espaço; régua de
    cabeçalho de disciplina não é figura (20 questões perdem a falsa pendência).
  - `05b1a8f`: estilo nas 6 provas do `pf-2025`.
  - Emendas: 0020 (3)–(7), 0030 (1)–(2), 0032 (1)–(2); SPECIFICATION.md §5 e §7.3;
    `docs/content-format.md` (URL).
- **Aprovações do minos** (claude-opus-5-5):
  - r7 (`1787d5b`): `pmro-2022/objetiva`, `pmdf-2025/p2` (saem de `review`).
  - r8 (`410aaea`): `pcrj-2021`, `pcce-2025`, `pcpe-2023` P1 cargo 2 e P2 cargo 3, `pcma-2017-delegado`.
  - r9 (`b01cdeb`): `pcma-2017-delegado`, `pcma-2017-apc` (4 provas), `pcro-2022` cargo 3, `pcpe-2023` P2 cargo 1.
  - r10 (`12d09e6`): `cbmro-2022` oficial, `pcpb-2021` cargo 4, `pcro-2022` cargo 1, `pmto-2020-qpe`, `pf-2018/agente`.
  - r11 (`d7ee5c3`): `pmal-2021` oficial, `pmro-2022`, `pcro-2022` (5 provas).
  - r12 (`b497a69`): `pf-2025` básicos I e II, delegado, papiloscopista.

## Verificação
- `make gates` final (HEAD `b497a69`): ok — lint, roundtrip das migrações, 586 testes, `emmoni check`
  8 checagens com 0 violações.
- Não verificado: as quebras de parágrafo novas fora das amostras não foram conferidas contra a
  página; o minos só viu as amostras (r7–r12).
- Publicadas com conteúdo mudado (só parágrafo/marcação) e sem amostra nova neste ciclo: as 45
  provas da varredura do `ae2d144` que não estão na lista acima; `pcgo-2016` (3 provas),
  `pcma-2017-apc` gerais cargos 2 e 5, `pcpb-2021` gerais 14–17 e cargo 12, `cbmto-2022` oficial,
  `pmpa-2023-cfp` básicos, `pf-2025/agente-especificos`.

## Decisões
- Emendas listadas acima, em `docs/decisions/0020-*.md`, `0030-*.md` e `0032-*.md`.
- Conservador: `pf-2025/agente-especificos` segue publicada pela aprovação antiga (as questões do
  g107 já estão em `review`); só ganhou marcação.

## Problemas encontrados
- `cbmro-2022/oficial` reprovada (r11): o texto-base das q28–q30 (tabela das ligações, pág. 4) não
  se liga às questões; q26 sem o texto da árvore; o texto-base da q23 começa no meio da frase. A
  prova está em `review`, fora do `api`.
- `pcma-2017-apc` gerais cargos 1/2 q14 e cargo 5 q17 publicadas com "teclas � e �" (U+FFFD); nenhum
  check pega.
- O minos não lê o `.env`; roda o `emmoni` pelo ambiente do Makefile.

## Próximo passo
- Hefesto: texto-base no início de coluna do `cbmro-2022/oficial` (q23, q26, q28–q30), depois
  amostra nova.
