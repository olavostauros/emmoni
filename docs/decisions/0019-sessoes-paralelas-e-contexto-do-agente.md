# 0019 — Sessões paralelas em worktrees e contexto do agente

**Data:** 2026-10-08 · **Marco:** M5

## Contexto

As sessões do agente passaram a rodar em paralelo, cada uma num worktree do git
(`.claude/worktrees/<nome>`). O `docker-compose.yml` tem nome de projeto e porta fixos (`emmoni`,
55432), então todos os worktrees falam com o mesmo Postgres: `make test` de uma sessão recria o
`emmoni_test` que outra está usando, e um `load` feito de um worktree muda o banco `emmoni` a partir
de um `data/` que o checkout principal não tem (o `data/` do worktree é uma cópia, fora do git).

Uma auditoria do contexto do agente achou também divergências no `AGENTS.md`: a regra de 429
("recua e para") contrariava o §7.1 do SPECIFICATION.md (backoff com `Retry-After`, até 3
tentativas); os status apareciam como `rascunho`/`revisar`/`publicada`, mas o enum é
`draft`/`review`/`published`; e o `STATUS.md` tinha virado histórico, contra o formato de
`docs/progress/README.md`. O `AGENTS.md` é o único arquivo de instruções carregado (não há
`CLAUDE.md`), então essas divergências chegam a toda sessão.

## Decisões

1. **Um banco por máquina, uma sessão por vez nos comandos que escrevem nele** (`make gates`,
   `make test`, `make migrate`, `make seed`, `make db-reset`, `emmoni ingest`,
   `emmoni review approve`, `emmoni crawl`). Por enquanto é regra de processo no `AGENTS.md`, sem
   trava no código.
2. **O que precisa sobreviver ao worktree vai para o git** (aprovações, revisões de OCR,
   `classify-answers.json`, manifestos). O resto de `data/` é reproduzível.
3. **O registro da sessão diz de qual worktree e commit veio uma carga no banco.**
4. **`AGENTS.md` alinhado ao SPECIFICATION.md**: as regras inegociáveis de crawling ficam no
   `AGENTS.md`, e a implementação (limites, backoff) só no §7.1; status com os nomes do enum.
5. **`STATUS.md` volta ao formato do README**: só o estado atual. O histórico fica nos registros
   de sessão.

O SPECIFICATION.md não muda.

## Consequências

- Duas sessões ainda podem colidir se a regra não for seguida. Se acontecer, o próximo passo é
  isolar por worktree (`COMPOSE_PROJECT_NAME` e `EMMONI_DB_PORT` próprios no `.env` do worktree) ou
  pôr uma trava (`flock`) nos alvos do Makefile, com nova decisão.
- O `STATUS.md` fica curto; quem quer saber o que mudou e quando lê `docs/progress/AAAA-MM-DD-*.md`.
