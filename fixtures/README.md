# Fixtures

Amostras pequenas para testes. Nenhum teste acessa a rede (SPECIFICATION.md §9).

## `pdf/cebraspe/`

Trechos de documentos oficiais do Cebraspe, usados só para testar o parser. A própria banca autoriza
"a reprodução deste material apenas para fins didáticos, desde que citada a fonte".

| Arquivo | Origem |
|---|---|
| `pf-2021-agente-p2-3.pdf` | Páginas 2 e 3 de `CARGO_2_AGENTE_DE_POLCIA_FEDERAL.PDF` — PF 2021, Agente. https://cdn.cebraspe.org.br/concursos/PF_21/arquivos/CARGO_2_AGENTE_DE_POLCIA_FEDERAL.PDF |
| `pf-2021-delegado-p3.pdf` | Página 3 de `CARGO_1_DELEGADO_DE_POLCIA_FEDERAL.PDF` — PF 2021, Delegado (fontes "TT…o00" sem nome de estilo; itálico de "habeas corpus"). https://cdn.cebraspe.org.br/concursos/PF_21/arquivos/CARGO_1_DELEGADO_DE_POLCIA_FEDERAL.PDF |
| `pf-2018-agente-p1.pdf` | Página 1 de `MATRIZ_408_DGPPF012__PAG_9.PDF` — PF 2018, Agente. https://cdn.cebraspe.org.br/concursos/PF_18/arquivos/MATRIZ_408_DGPPF012__PAG_9.PDF |
| `pf-2018-papiloscopista-p4.pdf` | Página 4 de `MATRIZ_408_DGPPF014__PAG_9.PDF` — PF 2018, Papiloscopista (fonte de símbolos sem mapeamento). https://cdn.cebraspe.org.br/concursos/PF_18/arquivos/MATRIZ_408_DGPPF014__PAG_9.PDF |
| `pmal-2021-oficial-p1-2.pdf` | Páginas 1 e 2 de `596_PMAL_001_MATRIZ.PDF` — PM/AL 2021, Oficial (capa e "PROVAS OBJETIVAS"). https://cdn.cebraspe.org.br/concursos/PM_AL_21/arquivos/596_PMAL_001_MATRIZ.PDF |
| `cbmto-2021-soldado-p7.pdf` | Página 7 de `MATRIZ_581_CBMTO_002_00.PDF` — CBM/TO 2021, Soldado (itálico simulado pelo Distiller, fonte "TT14422oI00": "Gerenciador de *downloads*"). https://cdn.cebraspe.org.br/concursos/CBM_TO_21/arquivos/MATRIZ_581_CBMTO_002_00.PDF |
| `pcpb-2021-escrivao-p7.pdf` | Página 7 de `628_PCPB_002_01.PDF` — PC/PB 2021, Escrivão, conhecimentos específicos (ordinal "o" sobrescrito: "Lei n.º 8.072/1990"). https://cdn.cebraspe.org.br/concursos/PC_PB_21/arquivos/628_PCPB_002_01.PDF |
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
