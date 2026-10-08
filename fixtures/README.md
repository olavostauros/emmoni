# Fixtures

Amostras pequenas para testes. Nenhum teste acessa a rede (SPECIFICATION.md §9).

## `pdf/cebraspe/`

Trechos de documentos oficiais do Cebraspe, usados só para testar o parser. A própria banca autoriza
"a reprodução deste material apenas para fins didáticos, desde que citada a fonte".

| Arquivo | Origem |
|---|---|
| `pf-2021-agente-p2-3.pdf` | Páginas 2 e 3 de `CARGO_2_AGENTE_DE_POLCIA_FEDERAL.PDF` — PF 2021, Agente. https://cdn.cebraspe.org.br/concursos/PF_21/arquivos/CARGO_2_AGENTE_DE_POLCIA_FEDERAL.PDF |
| `pf-2018-agente-p1.pdf` | Página 1 de `MATRIZ_408_DGPPF012__PAG_9.PDF` — PF 2018, Agente. https://cdn.cebraspe.org.br/concursos/PF_18/arquivos/MATRIZ_408_DGPPF012__PAG_9.PDF |
| `pf-2021-agente-gabarito-definitivo.pdf` | `GAB_DEFINITIVO_MATRIZ_577_PF_002_00.PDF` — gabarito definitivo, PF 2021, Agente. https://cdn.cebraspe.org.br/concursos/PF_21/arquivos/GAB_DEFINITIVO_MATRIZ_577_PF_002_00.PDF |

## `expected/`

Snapshots da saída dos parsers. Para regenerar depois de uma mudança intencional no parser:
`UPDATE_SNAPSHOTS=1 uv run pytest tests/test_parser_cebraspe.py` — e revise o diff antes de commitar.

## `crawl/cebraspe/`

Respostas da API JSON do Cebraspe (decisão 0004) gravadas em 2026-10-07 pelo cliente de cortesia,
para testar o crawler sem rede. `listing.json` é `eventos/tipo/concursos/` reduzido aos eventos
com prefixo policial (PF, PRF, DPF, PC, PM, CBM, DEPEN, SEAP, SDS) e a alguns outros, para testar
o escopo. Os demais arquivos são `eventos/<eventoURL>` com `aplicativos` removido e
`arquivosEdital` reduzido a quatro entradas; `arquivosGabarito` e `eventoCargos` estão completos.
`DPF_14_AGENTE` não tem fixture de propósito: a API real responde 500 e o teste cobre esse caso.
