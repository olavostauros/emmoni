# 2026-10-13 — Lab oficina e fechamento do ciclo das 10:22

**Marco:** M5

## O que foi feito
- Lab `oficina` em `labs/oficina/` com steward, hefesto, minos, caronte e cerberus; atlas vira
  caronte; regras de domínio e quatro loosenings; `agent-env` sem assinatura; gancho
  `agent-identity` instalado; negações da decisão 0026 no `.claude/settings.json` (decisão 0029,
  commit `9b109bc`, merge `1051709`). Sessão do dono, com o sim dele.
- O ciclo das 10:22 bateu no limite de sessão e deixou a sobra em `git stash`; a linha
  `CLOUDSDK_ACTIVE_CONFIG_NAME` do `mise.toml` voltou e o resto do stash foi aplicado no `main`:
  parser e `extract.py` do site antigo para o PF 2012, manifestos de delegado, escrivão e
  papiloscopista (aprovados pelo minos naquele ciclo), correções do E-004/E-005/E-006 e dois furos
  no `deploy/audit.py` com `tests/test_deploy_audit.py`, relatório
  `docs/security/reports/2026-10-13-cloud.md`, `DEPLOY.md` e `CYBERSECURITY.md`.
- Amostra por prova do PF 2012 (10 questões em cada, sorteios de 2026-10-13T16:48Z): as três
  aprovadas por minos (claude-opus-5-5); registros em `ingest/approvals/pf-2012-*/`.
- `docs/coverage.md` regenerado: 5.426 questões publicadas.
- Worktree esquecido `.claude/worktrees/agent-a9da…` removido (branch já no `main`).

## Verificação
- `make gates`: passou duas vezes, antes e depois dos approves (473 testes; 7 checagens, 0 com
  violações).
- `lab doctor`: healthy; `mise run test` do lab: 15/15.
- Não verificado: as 51 questões do PF 2012 em `review`/`draft` (3 delegado, 11 escrivão, 37
  papiloscopista) não entram na amostra, que sai só das publicáveis.

## Decisões
- [0029 — Lab oficina](../decisions/0029-lab-oficina.md).

## Problemas encontrados
- O ciclo só tinha registro no stash; o `STATUS.md` dizia que o timer estava desligado (estava
  ligado) e que o PR #130 do Usher faltava (merge em 2026-10-13T13:21Z).
- `review sample` não aceita nem grava semente; o sorteio fica nos números e no `created_at`.
- O `emmoni` fora do `make` precisa do `.env` carregado (`DATABASE_URL`).

## Próximo passo
- Hefesto: por que 37 das 120 questões do papiloscopista 2012 ficaram em `review`.
- Primeira varredura do steward (`oficina`).
