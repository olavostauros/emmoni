# 2026-10-14 — Ciclo autônomo das 14:53: texto-base sem rótulo, estilo em lote e impressão digital v2

**Marco:** M5

Ciclo autônomo (decisão 0026), sem o dono. Coordenadora → hefesto/minos em turnos, nunca os
dois ao mesmo tempo no banco. Tudo carregado a partir do checkout principal (`main`), sem
worktree; cada carga foi feita sobre o HEAD anterior mais as mudanças que viraram o commit seguinte.
Crawl não rodou: o último foi 2026-10-14 10:25 (menos de 24 h). Deploy parado no budget (fila do
dono); `deploy/` e nuvem sem mudança, sem auditoria nova.

## O que foi feito
- **Correções do hefesto** (cada uma com testes e varredura em lote):
  - `d7b8650`: texto sem rótulo depois da alternativa E deixa de ser engolido por ela; vale para as
    questões seguintes que retomam termo dele; título em corpo grande ou em caixa alta partida não
    vira texto-base (emenda da 0013). Fecha a reprovação r11 do `cbmro-2022/oficial`.
  - `36a23af`: linha com rótulo ("P1:", "c(x):") abre parágrafo; título em negrito encerra a
    alternativa E; estilo em `pmsc-2023-soldado`, `pcse-2021`, `pmal-2021` soldado,
    `cbmto-2022/soldado`; check `090_replacement_character` (emenda (8) da 0020).
  - `f454d52`: remissão com rótulo colado ("texto1A5-I"); versos numa estrofe com `\` (emendas da
    0013 e (9) da 0020).
  - `9c7f90e`: segunda língua estrangeira recomeça os itens pulados (CBM/AL 2017); texto branco
    invisível sai do fluxo (PC/SE 2018); fonte de figura fica no item; estilo no `cbmal-2017`
    (emenda (10)).
  - `1e99a50`: **impressão digital v2** da aprovação com o texto gravado (marcação, parágrafos,
    assets) e aviso do `--also` (decisão 0033). Aprovações antigas seguem na v1 até a próxima
    amostra; nada reaprovado em massa.
  - `22fdddf`: estilo no `cbmto-2021`; título em corpo grande encerra alternativa sem ponto; item
    continua depois de aspa de fechamento (emenda (11)).
  - `4939f77`: estilo pelo nome da fonte simulada do Distiller (`TT…oI00`); letra da alternativa
    com estilo sai do corpo (emenda (12)).
  - `33ba645`: estilo no `cbmpa-2023-cfp`; título de figura em negrito é texto-base e marca
    `figure` (emenda (13)).
- **Aprovações do minos** (claude-opus-5-5), 39 registros:
  - r13 (`98a1bec`): `cbmro-2022/oficial`, `pcgo-2016` cargo 1 (3), `pcma-2017-apc` gerais cargos 2
    e 5, `cbmto-2022/oficial`, `pmpa-2023-cfp` básicos.
  - r14 (`15817a6`): `cbmto-2022/soldado`, `cbmro-2022/oficial`, `pmto-2020-qpe`, `pcse-2021`
    específicos cargos 1 e 2.
  - r15 (`3ccd32c`): `pmsc-2023-soldado/objetiva` (sai de `review`), `pmal-2021/soldado`.
  - r16 (`a1c27ef`): `cbmal-2017` básicos cargo 2, específicos cargos 1 e 2; `pcse-2018` gerais.
  - r17 (`a996003`): `pcpb-2021` cargos 12 e 13, `pf-2025/agente-especificos`.
  - r18 (`f3144c0`): `cbmto-2021/oficial`, `pcpb-2021` gerais 14–17.
  - r19 (`30e71df`): `cbmto-2021` soldado e oficial, `cbmal-2017` básicos cargo 2, `pf-2012-escrivao`.
  - r20 (`9a40d66`): `pcgo-2016` gerais cargo 2, `pcpb-2021` cargos 1 e 3 e gerais delegado,
    `pcse-2021` gerais.
  - r21 (`28d64e2`): `cbmpa-2023-cfp/p1`.
  - r22 (`50dc961`): `pcpb-2021` gerais agente e escrivão, cargos 6 e 9; `pcro-2022` gerais cargo 3.
  - Reprovações fechadas no ciclo: r11 cbmro, r13 pmsc, r14 pmsc e pmal, r15 cbmal ×2 e pcse-2018,
    r17 pcpb 14–17 e cbmto-2021 oficial, r18 cbmto-2021 soldado, r20 cbmpa-2023-cfp.

## Verificação
- `make gates` final (HEAD `50dc961`): ok — lint, roundtrip das migrações, 611 testes, `emmoni
  check` 9 checagens com 0 violações.
- Não verificado: marcação nova fora das amostras (PC/SE 2021, CBM/AL 2017, CBM/TO 2021, CBM/PA
  2023) não foi conferida página a página; as varreduras do hefesto confiam no staging (o
  `pmma-2017` está fora de sincronia).

## Decisões
- Decisão 0033 (impressão v2); emendas da 0013 (2) e da 0020 (8)–(13); SPECIFICATION.md §7.3 e §8.
- Conservador: versos centralizados do `cbmal-2017` específicos cargo 2 (q114–116) seguem em
  `review` pela marca "layout"; teclas desenhadas do `pcma-2017-apc` (U+FFFD) seguem em `review`
  (já estavam; o STATUS anterior as dava como publicadas, o que estava errado).

## Problemas encontrados
- `pcpb-2021/conhecimentos-especificos-para-o-cargo-de-escrivao-de-policia` reprovada (r22): q52
  (pág. 7) "Lei n.o 10.826/2003" com o "o" sobrescrito lido como "o" comum; q50 tem o mesmo. Segue
  publicada pela aprovação v1. Mesma grafia no staging de `pcpb-2021` cargos 1 e 3, `pf-2025`
  escrivão, `pcdf-2020` básicos e `cbmal-2021` oficial (não conferido contra o PDF).
- CBM/AL 2017 básicos cargo 1 segue fora: itens 49–50 perdidos depois de "P:"/"Q:" do item 48.

## Próximo
- Hefesto: sobrescrito "n.o" → "n.º" (e "ª"), em lote; minos reamostra as provas afetadas.
