# 2026-10-08 — API HTTP para o Plantão e preparação do deploy no Google Cloud

**Marco:** M5 (fora da linha principal: pedido do dono)

## O que foi feito
- **API HTTP local** (decisão 0021, commit `da4e0ff`, PR #3 empilhado no #2): serviço `api` do
  docker compose no perfil `api` (PostgREST v12.2.3 como `emmoni_web`, só o esquema `api`,
  `127.0.0.1:53000`, máx. 100 linhas por view); `make api-up/api-down/api-smoke`;
  `scripts/api-smoke.sh`; contrato **v1.3** (seção "Acesso por HTTP", sem mudança no esquema).
- **Canal com o agente do Plantão** testado: mensagem para a sessão `plantao-f7` pelo
  `SendMessage`, resposta recebida (ele confirma, atualiza a cópia do contrato e o
  `CONTRACT_VERSION` quando o emmoni fizer merge, e vai usar a API para os casos de paridade do F2).
- **Deploy no Google Cloud preparado, nada criado na nuvem** (decisão 0022):
  - `deploy/Dockerfile`, `deploy/bake.sh`, `deploy/entrypoint.sh`, `deploy/build.sh`: imagem
    imutável com Postgres 17 + PostgREST e os dados dentro (seed ou all), bases por digest,
    Postgres só no socket, `emmoni_web` sem senha, só leitura, `statement_timeout` 3 s.
  - `deploy/audit.py` (`--image`, `--public`, `--cloud`, `--header`): as verificações que o Usher
    fazia à mão.
  - `deploy/budget-cap/` + `tests/test_deploy_budget_cap.py`: corte de gasto que muda o ingresso
    do Cloud Run para interno quando o gasto real alcança o budget.
  - `docs/DEPLOY.md` (dinheiro, estimativa com preços verificados no Billing Catalog em BRL,
    recursos, passos com os comandos exatos, rollback, registro de gasto), `docs/CYBERSECURITY.md`
    (ameaças, regras, verificações, contrato de correção com ids estáveis),
    `.claude/agents/atlas.md` e `.claude/agents/cerberus.md`.
  - SPECIFICATION.md §1, §2, §6, §9 e AGENTS.md (divisão de trabalho) atualizados.
- Base: estudo da operação Usher (`~/Work/usher`: `docs/DEPLOY.md`, `docs/CYBERSECURITY.md`,
  `ops/gcp/`, agentes atlas/cerberus/usher-ops). O que foi feito melhor está na decisão 0022.

## Verificação
- `make gates`: ok — 362 testes (351 + 11 do corte), lint, roundtrip, checks.
- `make api-smoke` contra o compose: 7/7. Contra a imagem de produção seed rodando como no Cloud
  Run (512 MiB, `--cap-drop=ALL`, `PORT=8080`): 7/7.
- `deploy/audit.py --image <seed> --public http://127.0.0.1:58080`: 34 verificações, 0 falhas.
- **Não verificado**: `audit.py --cloud` (o projeto não existe; rodar contra `usher-prod` para
  exercitar o código foi negado, corretamente); a imagem `all` (só a seed foi construída); a
  função de corte no Google Cloud (só testes locais com HTTP falso); a sintaxe exata de
  `gcloud functions deploy --build-service-account` e da política de limpeza do Artifact
  Registry na versão do gcloud instalada (o atlas confere no passo); partida a frio no Cloud Run.

## Decisões
- [0021](../decisions/0021-api-http-postgrest.md) — API HTTP local por PostgREST.
- [0022](../decisions/0022-producao-no-cloud-run.md) — produção no Cloud Run com imagem imutável (proposta).

## Problemas encontrados
- `pg_restore --create` restaura com o nome do banco de origem (`emmoni_test` no escopo seed):
  trocado por `create database emmoni` + `alter database ... set search_path` + restore.
- O `COPY` do Dockerfile recria `/srv/pgdata` com 0755 e o Postgres recusa: `chmod 0700` na entrada.
- `pg_dump` do host é 18; o dump sai do container (17) para o `pg_restore` 17 da imagem ler.
- O crédito do Free Trial é o mesmo do Usher, e o `CYBERSECURITY.md` do Usher trata projeto novo
  na conta de faturamento como achado: o dono precisa registrar lá que `emmoni-prod` é esperado.

## Próximo passo
- Dono: conferir a estimativa (`docs/DEPLOY.md` §2) e dizer "vai" para o passo 1 (projeto
  `emmoni-prod`), depois chamar o atlas passo a passo.
