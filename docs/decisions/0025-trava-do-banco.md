# 0025 — Trava do banco

**Data:** 2026-10-13 · **Marco:** M5

## Contexto

O Postgres do docker compose é um só por máquina e todos os worktrees o compartilham (decisão
0019). Até aqui, "um comando que escreve no banco por vez" era regra de processo, com "em dúvida,
pergunte ao dono". O dono quer os agentes trabalhando sozinhos, num ciclo rodado por timer, sem
perguntar a ninguém; a decisão 0019 já previa, como próximo passo, uma trava (`flock`).

## Decisão

1. **Uma trava por máquina**: o arquivo `${XDG_RUNTIME_DIR:-/tmp}/emmoni-db.lock`
   (`EMMONI_DB_LOCK` sobrescreve), travado com `flock(2)`. O kernel solta a trava quando o processo
   termina; o arquivo nunca é apagado, e o conteúdo (PID, hora e comando de quem segura) é só
   informativo.
2. **Makefile**: pedido um alvo que escreve no banco (`gates`, `test`, `test-db`, `migrate`,
   `seed`, `catalog`, `db-reset`, `db-down`, `migrations-roundtrip`, `crawl`, `bench`, e
   `prod-image`, que lê o `emmoni_test` recriado pelo `test`), o make de fora roda a si mesmo sob
   `scripts/db-lock.sh` (`flock(1)`), com `EMMONI_DB_LOCKED=1` no ambiente.
3. **Comando `emmoni`**: `ingest`, `crawl`, `catalog load`, `taxonomy load`, `review approve` e
   `review restore` tomam a mesma trava (`ingest/dblock.py`, `fcntl.flock`). Leituras e os
   comandos que só mexem em arquivos (`manifests`, `review sample`, `review topics`) não travam.
4. **Sem trava dupla**: com `EMMONI_DB_LOCKED` definido, um processo pai já segura a trava, e nem
   o make de dentro nem o `emmoni` travam de novo.
5. **Esperar, não perguntar**: quem chega com o banco ocupado imprime uma linha ("banco ocupado
   (pid … desde …: make gates); esperando…") e espera até `EMMONI_DB_LOCK_WAIT` segundos (padrão
   1800). Estourou: sai com código 75 (`EX_TEMPFAIL`) e mensagem clara. Nunca remove a trava de
   outro processo.

## Consequências

- A regra de processo da decisão 0019 vira código: a pergunta ao dono sai, a espera entra.
- A trava serializa só quem passa pelo Makefile ou pelo `emmoni`. `psql`, `dbmate` ou `pytest`
  chamados direto não travam: quem os usa fora do make segura a trava com
  `scripts/db-lock.sh "<descrição>" <comando>`.
- Comandos longos (`make gates`, `emmoni ingest` com OCR) seguram o banco o tempo todo; quem
  espera mais de 30 min falha e tenta no próximo ciclo.
- Um processo que fique para trás não prende a trava: o descritor não é herdado pelo comando
  que o `db-lock.sh` roda.
