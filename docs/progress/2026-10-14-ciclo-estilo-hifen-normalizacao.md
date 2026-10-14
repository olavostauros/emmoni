# 2026-10-14 — Ciclo autônomo das 05:28: estilo, figura citada, hífen, normalização

**Marco:** M5

Ciclo autônomo (decisão 0026), sem o dono. O último `make crawl` era de 2026-10-13 10:24, com menos
de 24 h quando o ciclo começou, então não houve crawl. O próximo ciclo deve rodá-lo.

## Retomada do ciclo das 02:05
O ciclo das 02:05 commitou `976607e`, `f4875bb` e `91e759a`, mas não fez push, não escreveu
registro nem `STATUS.md`. O motivo: os subagentes estavam em segundo plano e o `claude -p`
encerrou-os 10 min depois da última resposta da coordenadora. O trabalho do hefesto ficou no
`stash@{0}` ("ciclo 2026-10-14-0227: sobra"). Neste ciclo, os subagentes rodaram em primeiro plano.
Os gates passaram, o push dos 3 commits foi feito e o stash foi aplicado com `apply`. O stash
continua lá, e descartá-lo é do dono.

## O que foi feito (hefesto produz, minos aprova; um por vez no banco)
- **Lote 2 do estilo, reprovações** (`9c5715b`):
  - estilo de fonte com poucas letras, pelo desenho dos glifos (CFF) ou pelas larguras com margem;
  - fonte monoespaçada vira código inline no modo `styles`;
  - emenda de 2026-10-14 da decisão 0020; `fonttools` virou dependência direta.
  - O minos aprovou `pcgo-2016` básicos cargos 1 e 2, `pmpa-2023-cfp` específicos e
    `pmpa-2023-cfo` básicos p1. Por marcação nova, aprovou também `pcal-2022` gerais p1, `pces-2022`
    gerais e `pf-2018` escrivão. Reprovou `pf-2018` agente: q81–83 sem o diagrama ER.
- **Figura citada sem imagem** (decisão 0030) e **`review sample --seed`** (decisão 0031)
  (`3ce0aa2`):
  - q81–83 do PF 2018 agente, q85–86 do PC/DF 2020 e q51 e q54 do PC/PB 2021 cargo 7 foram para
    `review`.
  - O minos reaprovou o PF 2018 agente. AGENTS.md e `minos.md` agora citam o `--seed`.
- **Justificativa pela cor** (emenda da 0009) e **estilo no `pcpb-2021`** (`0a93785`, `fae6dd8`):
  - o g85 do PC/DF 2020 recuperou a primeira linha, e o g27 da PRF 2018 o início;
  - o minos reaprovou PC/DF 2020 específicos, PC/PB cargo 7 e PRF 2018 policial.
- **Hífen de fim de linha é do original** (decisão 0032) e **crédito num parágrafo** (`7ce0948`):
  - nas 70 linhas do corpus que terminam em letra + "-", nenhuma é separação silábica;
  - 28 junções erradas foram corrigidas ("pós-morte", "aplica-se", "boa-fé"…);
  - 16 provas voltaram a `review`. O minos reaprovou 8 delas (`4974c37`).
- **Estilo em PC/RJ 2021, PC/RO 2022, CBM/TO 2022 oficial e PM/RO 2022**, "*In*:" e crédito entre
  parênteses (`24398cd`). O minos reaprovou PC/RO gerais 1 e 4, PC/PB gerais 4–13 e PC/RJ
  (`d9c6ebd`).
- **Normalização na gravação** (`8950d84`):
  - `normalize_md` (NFC e strip) no load;
  - check 080 (15 casos em 5 provas; recarga sem mudar impressão digital);
  - "o" sobrescrito entre número e "C" vira "º".
  - O minos reaprovou PC/PB cargo 11 e CBM/TO 2022 oficial (este commit).

Sementes do minos: `minos-2026-10-14-r2` a `r6`. Todas as aprovações: minos (claude-opus-5-5).

## Ficou de fora / sem verificar
- `pmro-2022/objetiva` (q41, q100) e `pmdf-2025/p2` (q76): o comando fica colado no parágrafo
  anterior. A causa provável é que `_choice_paragraphs` não usa o `_block_gap`. A correção atinge
  todas as provas de múltipla escolha e pede varredura em lote. As duas provas seguem em `review`.
- `cbmto-2022/soldado` e `pcro-2022` cargo 3 específicos continuam sem `infer_font_styles`: com o
  estilo, o título de disciplina sai da alternativa E e as pendências mudam.
- Provas publicadas que ganharam marcação ou parágrafo novo sem nova amostra, porque a impressão
  digital ignora formatação:
  - as demais 15 provas do `pcpb-2021`;
  - `pcro-2022` específicos cargos 1 e 4 e gerais cargo 3;
  - `cbmro-2022` oficial (q36, q38);
  - `cbmto-2021` oficial (q47);
  - `pcce-2025` (q64);
  - `pcpb-2021` cargos 4 e 13 (q60, q65);
  - `pcpb-2021` cargo 6 e gerais delegado e `cbmal-2021` soldado (só espaço/NFC).
- `pmma-2017` gerais cargo 5: o `passage_key` diverge em 4 questões ao reprocessar, por causa não
  investigada.
- PF 2018 agente q93–96: o programa em várias linhas virou spans de código soltos (em `review`).

## `make gates`
`gates: ok` antes de cada commit; no último, 569 testes, 8 checks e 0 violações.

## Números
5.806 `published` · 1.123 `review`; provas: 113 publicadas, 2 em `review`; 5.310 no esquema `api`.
