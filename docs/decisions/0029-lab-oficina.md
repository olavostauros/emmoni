# 0029 — Os agentes formam o lab oficina, com um steward

**Data:** 2026-10-13 · **Marco:** M5

## Contexto

O ciclo das 10:22 de 2026-10-13 bateu no limite de sessão no meio do trabalho: a ingestão do DPF
2012, as correções do E-006 no `deploy/audit.py` e o parser ficaram num `git stash`, junto com a
linha `CLOUDSDK_ACTIVE_CONFIG_NAME` do dono no `mise.toml`, e nada no registro dizia isso. O
`STATUS.md` afirmava que o timer do ciclo não estava ligado; estava. Ninguém tinha a função de
medir o registro contra o disco.

O dono usa o framework `lab` (`lab init` / `lab doctor`) em outro projeto, com um steward: um
agente sem voz para fora cujo trabalho permanente é manter o registro verdadeiro.

## Decisão

1. Os agentes do emmoni formam o lab **oficina**, embutido em `labs/oficina/` (`lab init oficina
   --embedded`, a partir do `lab` em `d9f5e5e`, que corrige o `WORK_DIR` de um lab embutido abaixo da raiz). Roster: `steward`, `hefesto` (builder, `ingest/`),
   `minos` (judge), `caronte` (builder, `deploy/`), `cerberus` (judge). Homes em
   `~/agents/<nome>/home/`; a do steward em `~/agents/oficina/home/`.
2. O agente de deploy **atlas** passa a se chamar **caronte**: `~/agents/atlas/` já é de outro
   lab da máquina. Decisões e registros anteriores mantêm o nome antigo.
3. Autoridade (tiers, loosenings, regras de domínio) fica em `labs/oficina/AGENTS.md`. A decisão 0026
   continua valendo como a linha 1 dos loosenings: o ciclo é o assento do dono e faz push no
   `main` só com gates verdes. As linhas 2–4 dão ao hefesto, ao minos e ao caronte o que eles já
   faziam pelas decisões 0024, 0026 e 0028.
4. A definição do steward para o runner é `.claude/agents/oficina.md`, com o nome do lab.

## Consequências

- O contrato do lab vem do framework em inglês; as partes do emmoni (regras de domínio,
  loosenings) estão em português.
- O `agent-env` desta versão do lab não desligava a assinatura, e o repositório tem
  `commit.gpgsign=true`: um commit de agente pediria a senha do dono. Com o sim do dono
  (2026-10-13), o `agent-env` do oficina desliga a assinatura no shell do agente, como o do outro
  lab da máquina; o teste `agent_env.bats` cobre isso.
- O gancho `hooks/agent-identity` está instalado como pre-commit do emmoni: commit sem identidade
  de agente precisa de `OFICINA_OWNER_COMMIT=1`, inclusive os do dono e os do ciclo
  (`scripts/ciclo-prompt.md` diz como o assento faz commit, sem assinatura).
- As negações da decisão 0026 entraram no `.claude/settings.json`.
