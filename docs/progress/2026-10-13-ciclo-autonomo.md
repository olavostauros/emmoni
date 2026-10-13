# 2026-10-13 — Trava do banco e ciclo autônomo

**Marco:** M5

Checkout principal, branch `main`, sobre o commit `660d77d`. Nada carregado no banco nesta sessão
além do que o `make gates` recria.

## O que foi feito
- Trava do banco (decisão 0025): `ingest/dblock.py`, `scripts/db-lock.sh`, alvos do `Makefile`
  que escrevem no banco rodam sob a trava, comandos do `emmoni` que escrevem tomam a mesma trava
  (`ingest/cli.py`); testes em `tests/test_dblock.py`.
- Ciclo autônomo (decisão 0026): `scripts/ciclo.sh`, `scripts/ciclo-prompt.md`,
  `scripts/systemd/emmoni-ciclo.{service,timer}`; AGENTS.md ("Ciclo autônomo"), agentes
  hefesto, minos, atlas e cerberus, `MISSION.md`, `SPECIFICATION.md`, `docs/operations.md` e
  `docs/DEPLOY.md` ajustados para trabalhar sem perguntar ao dono.
- `docs/DEPLOY.md`: passo 0 feito (o dono disse "vai"); saída de rede e imagem da função de corte
  somadas à estimativa do §2, com a ressalva do pior caso; leitura do crédito no §9.
- `.claude/settings.json` do projeto: allowlist com leituras frequentes (`ffprobe`, `git grep`,
  `gh search prs`, `gh run watch`), tiradas dos transcripts.
- O `CYBERSECURITY.md` do Usher passa a esperar o `emmoni-prod` na conta de faturamento: PR #130
  do Usher, aberto pela sessão do Usher com automerge.

## Verificação
- `make gates`: **passou** — 381 testes, `emmoni check` com 7 checks e 0 violações.
- Não verificado: o timer não foi instalado nem rodou; nenhum ciclo autônomo rodou de ponta a
  ponta.

## Decisões
- [0025 — Trava do banco](../decisions/0025-trava-do-banco.md)
- [0026 — Ciclo autônomo](../decisions/0026-ciclo-autonomo.md)

## Problemas encontrados
- A decisão 0026 diz que o `.claude/settings.json` nega `usher-prod`, `gcloud projects delete`,
  `gcloud billing accounts` e `git push --force`. Essas negações **ainda não estão** no arquivo:
  o modo automático bloqueia o agente de editar as próprias permissões, então o dono aplica.

## Próximo passo
- Dono: negações no `.claude/settings.json`, ligar o `emmoni-ciclo.timer` e escrever no
  `STATUS.md` o sim para as questões reais, se for o caso.
