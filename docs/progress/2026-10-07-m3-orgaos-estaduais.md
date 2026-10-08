# 2026-10-07 — M3: órgãos estaduais no catálogo e correções do crawl diário

**Marco:** M3 (fechamento)

## O que foi feito
- `db/catalog.yaml`: 25 órgãos novos (PC, PM, CBM, DEPEN, SEAP-MA) com `aliases`; cargos das
  forças militares com `aliases` (`Position.aliases` em `ingest/catalog.py`).
- `ingest/crawlers/cebraspe.py`: `Caderno de provas` → prova; `SEM EFEITO` e `CURSO DE INSTRUÇÃO`
  excluídos; prova de rótulo genérico vale para todos os cargos do concurso; apelidos de cargo.
- `ingest/crawl.py` + `ingest/cli.py`: erro de configuração (contato) aborta sem gravar estado.
  `Makefile`: exporta `EMMONI_CRAWL_CONTACT` (o `make crawl` agendado nunca funcionaria sem isso).
- Execução real: 47 requisições; **35 propostas** em `ingest/manifests/_pending/`; reexecução
  com 0 requisições. 13 fixtures novas; listagem de fixture reduzida; 8 testes novos.
- Decisão 0008; SPECIFICATION.md §4.1 (apelidos de cargo).
- A pedido do humano: **36 propostas aprovadas** sem ajuste (`emmoni manifests approve`) e
  `pmto-2020-qps` rejeitada (proposta antiga de regra corrigida, que o crawler não remove de
  `_pending/`). Os testes passam a usar como "manuais" os manifestos aprovados com fixture.

## Verificação
- `make gates`: **passou** — 268 testes; ruff, mypy e checagem do seed limpos; roundtrip das
  migrações ok; 7 checks sem violação.
- As 12 propostas cobertas pelas fixtures reproduzem a execução real (a diferença de slug em
  `pmpa-2023`, `cbmpa-2023` e `pmsc-2023` é o desempate da decisão 0007, item 8: na listagem
  reduzida não há evento irmão no mesmo ano).
- **Não verificado:** nenhuma proposta nova foi conferida contra os PDFs; timer do systemd não
  instalado.

## Decisões
- [0008](../decisions/0008-orgaos-estaduais-no-catalogo.md)

## Problemas encontrados
- PCDF 2019 (um caderno, dois gabaritos) continua limitado pelo modelo de um gabarito por prova.
- DEPEN 2015 e DPF 2014: API responde 500.

## Próximo passo
- Ingerir os manifestos aprovados um a um (parser e `subjects_by_range`); depois M4.
