# 2026-10-08 — Reprocessamento das provas aprovadas com o parser da decisão 0020

**Marco:** M5

Worktree `credit-end-reprocess`, a partir do commit `21acad8`. Carga no banco `emmoni` feita deste
worktree: 41 manifestos (todos os do staging, menos `pf-2012`, `pcpe-2016` e
`pcientifica-pe-2016`), etapas `segment` → `load`.

## O que foi feito
- Backup antes: `pg_dump` do banco `emmoni`, cópia do `data/staging` e status + `statement_hash` das
  6.634 questões.
- `segment`, `answer-key`, `validate` e `classify` rerodados nos 41 manifestos (o `extract` não muda
  fora da fonte `cespe-unb`, decisão 0020) e comparados com o staging anterior:
  - 45 provas mudam; em 41 só os textos-base (crédito emendado);
  - questões mudam em 4 provas, só ganhando motivo de revisão, todas **já em `review`**: PF 2021
    agente q97–101 (`layout`), PC/PE 2023 p2-cargo-1 q54 e PC/SE 2021 q27–30 (`figure`), PM/MA 2017
    soldado q5–8 (texto-base "CG2A1BBB" não encontrado, motivo que já tinham);
  - CBM/AL 2021 e PM/TO 2020 não mudaram em questões: os flags falsos do "RASCUNHO" já não estavam no
    staging.
- `load` dos 41 manifestos: as 117 provas seguem `published` pela impressão digital; nenhuma volta
  para `review`, nenhuma precisa de reamostragem.
- No banco, 67 textos-base mudaram de texto: 65 só em espaço (crédito em um parágrafo) e 2 com o
  negrito do título emendado (`**Álbum Lado B Lado A**`, `**Diário das Coincidências**`). Conferido
  por script: removidos espaços e quebras, o resto é idêntico.
- `docs/coverage.md` regerado: 5.152 questões publicadas (sem mudança).

## Verificação
- `make gates`: **passou** — 351 testes, `emmoni check` com 7 checks e 0 violações.
- Status e `statement_hash` das 6.634 questões antes × depois: 0 diferenças.
- **Não verificado:** os 67 créditos foram conferidos só no texto, não contra a página do PDF
  (mesmo critério da sessão `2026-10-08-credit-end.md`).

## Problemas encontrados
- Crédito em três linhas ou mais só emenda as duas últimas: segue a quebra no meio do crédito, por
  exemplo PM/MA 2017 g39 ("Núcleo de Estudos," | "Pesquisas e Projetos…")
  e o INFOPEN do DEPEN ("Tatiana W. de Moura e Natália C. T. Ribeiro." | "Levantamento…").
- CBM/AL 2017 cargo 1 e PC/PB 2021 cargo 8 seguem com erro de gabarito (bloqueios conhecidos).

## Próximo passo
- Integrar o branch `worktree-credit-end-reprocess` ao `main`.
- Crédito em três linhas ou mais (acima), depois o estilo `legacy` nos cadernos com fontes "TT…o00".
