# 2026-10-08 — Auditoria do contexto do agente

**Marco:** M5

## O que foi feito
- Auditoria do que entra no contexto de uma sessão: não há `CLAUDE.md` no repositório, nos
  diretórios acima nem em `~/.claude`, e a memória do projeto está vazia — o `AGENTS.md` é o único
  arquivo de instruções carregado.
- `AGENTS.md`:
  - crawling: 429/503 → recua respeitando `Retry-After` (até 3 tentativas) e para se persistir;
    403/captcha → para (antes dizia "403, 429 ou captcha: para", contra o §7.1); a implementação
    fica só no SPECIFICATION.md §7.1; fixtures em `fixtures/crawl/<fonte>/`;
  - status com os nomes do enum (`draft`, `review`, `published`);
  - formato do enunciado aponta para `docs/content-format.md`;
  - amostra de assuntos: subagente que lê só `amostra.{md,json}` e a taxonomia (como no M4);
  - leitura inicial: `docs/contract.md` sem "(quando existir)"; `content-format.md`,
    `operations.md` e decisões conforme a tarefa;
  - passo 7: `STATUS.md` é sobrescrito, não acumula histórico;
  - seção nova "Sessões paralelas e worktrees".
- `docs/decisions/0019-sessoes-paralelas-e-contexto-do-agente.md`.
- `docs/progress/STATUS.md` reescrito no formato do README (só o estado atual; o histórico já
  estava nos registros de sessão).
- Fora do repositório (configuração do dono, com backup em
  `~/.claude/backups/settings.json.2026-10-08-pre-automode-trim`): `autoMode.environment` do
  `~/.claude/settings.json` descrevia `~/Work`/oikos ("this project's CLAUDE.md", knick/knack,
  repositório confiável `/home/olavostauros/Work`); as linhas foram reescritas para valer em
  qualquer projeto.

## Verificação
- Antes do `make gates`, conferido que nenhuma outra sessão rodava pytest, `emmoni` ou dbmate.
- `make gates`: passou — 341 testes, 7 checks sem violações, "gates: ok".
- Não verificado: o efeito do novo `autoMode.environment` no classificador (só vale em sessões
  novas).

## Decisões
- [0019](../decisions/0019-sessoes-paralelas-e-contexto-do-agente.md)

## Problemas encontrados
- Os agentes de usuário de outros projetos (`argus`, `caesar`, `narcise`, `vulcan` do ticket;
  `knick`, `knack` do oikos) aparecem em toda sessão do emmoni; `vulcan` se descreve como dono do
  esquema e das migrações do Postgres. O dono decidiu mantê-los globais; o agente do emmoni não os
  usa — o banco do emmoni é deste agente (`AGENTS.md`, "Divisão de trabalho").
- O shell da sessão herda `VIRTUAL_ENV` do checkout principal; o `uv` avisa e usa o `.venv` do
  worktree, sem efeito nos gates.

## Próximo passo
- Se duas sessões colidirem no banco, isolar por worktree ou pôr trava no Makefile (decisão 0019).
