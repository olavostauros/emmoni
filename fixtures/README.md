# Fixtures

Amostras pequenas para testes. Nenhum teste acessa a rede (SPECIFICATIONS.md §9).

## `pdf/cebraspe/`

Trechos de documentos oficiais do Cebraspe, usados só para testar o parser. A própria banca autoriza
"a reprodução deste material apenas para fins didáticos, desde que citada a fonte".

| Arquivo | Origem |
|---|---|
| `pf-2021-agente-p2-3.pdf` | Páginas 2 e 3 de `CARGO_2_AGENTE_DE_POLCIA_FEDERAL.PDF` — PF 2021, Agente. https://cdn.cebraspe.org.br/concursos/PF_21/arquivos/CARGO_2_AGENTE_DE_POLCIA_FEDERAL.PDF |
| `pf-2021-agente-gabarito-definitivo.pdf` | `GAB_DEFINITIVO_MATRIZ_577_PF_002_00.PDF` — gabarito definitivo, PF 2021, Agente. https://cdn.cebraspe.org.br/concursos/PF_21/arquivos/GAB_DEFINITIVO_MATRIZ_577_PF_002_00.PDF |

## `expected/`

Snapshots da saída dos parsers. Para regenerar depois de uma mudança intencional no parser:
`UPDATE_SNAPSHOTS=1 uv run pytest tests/test_parser_cebraspe.py` — e revise o diff antes de commitar.
