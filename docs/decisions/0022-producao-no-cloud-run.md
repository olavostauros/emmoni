# 0022 — Produção da API no Google Cloud Run, com imagem imutável

**Data:** 2026-10-08 · **Marco:** M5 · **Estado:** proposta (vira aceita quando o passo 9 de
`docs/DEPLOY.md` fechar)

## Contexto

O dono pediu a API do emmoni no Google Cloud, com um agente de deploy (atlas) e um de segurança
(cerberus), reproduzindo e melhorando o que a operação Usher fez. O Usher roda uma VM Spot com
docker compose, túnel da Cloudflare e SSH só por IAP, dentro do crédito do Free Trial (conta
`01F985-1C44C6-40CDE9`, R$ 1.779,29 até 2027-01-06). As dores que ele registrou:

- ~3 h de API fora do ar depois de uma preempção da VM, sem alerta;
- disco subdimensionado duas vezes; tudo na VM feito à mão pelo dono por IAP;
- segredos de produção copiados do dev; a função de corte construída pela conta padrão com
  `roles/editor` (caminho até root na VM); segurança do agente na VM pensada depois.

O emmoni é diferente num ponto decisivo: **em produção nada escreve no banco**. A API é só
leitura e os dados só mudam quando a ingestão roda na máquina do dono.

## Decisão

1. **Imagem imutável com os dados dentro.** `deploy/build.sh seed|all` faz o `pg_dump` (sem o
   estado do crawler) e `deploy/Dockerfile` restaura no build: Postgres 17 + PostgREST v12.2.3,
   bases fixadas por digest. Atualizar os dados = nova imagem = nova revisão. Rollback = mandar o
   tráfego para a revisão anterior.
2. **Cloud Run** em `southamerica-east1`, projeto próprio **`emmoni-prod`**, label `emmoni=prod`:
   1 vCPU, 512 MiB, `min-instances=0`, **`max-instances=1`**, concorrência 40, timeout 10 s.
   Sem VM, sem SSH, sem disco, sem rede para configurar, sem túnel, TLS gerenciado (`*.run.app`).
3. **Sem segredo nenhum.** O Postgres só escuta no socket Unix (`listen_addresses = ''`,
   `pg_hba` só `local`); o `emmoni_web` entra sem senha porque não há rede; os outros papéis são
   `NOLOGIN`. `emmoni_web` com `default_transaction_read_only = on` e `statement_timeout = 3s`.
4. **Contas de serviço mínimas, criadas antes de tudo:** `emmoni-api` (runtime, sem papel
   nenhum), `emmoni-budget-cap` (papel customizado só com `run.services.get/update`) e
   `emmoni-build` (build da função). A conta padrão do Compute não é usada para nada; se aparecer
   com `roles/editor`, o vínculo é removido. Nenhuma chave de conta de serviço.
5. **Corte de gasto que funciona sem VM:** budget mensal **R$ 40** (sem créditos) → Pub/Sub →
   função `emmoni-budget-cap` que muda o ingresso do serviço para interno quando o gasto real
   alcança o budget. Pior caso (abuso 24 h com 1 instância): ~R$ 18/dia; com o atraso do
   faturamento, o teto prático fica perto de R$ 80 no mês.
6. **Publicação em dois tempos:** a primeira imagem pública é a do **seed** (fictício). A
   imagem `all` só fica pública (`allUsers` como invoker) com o sim explícito do dono, a mesma
   regra do snapshot `--scope all` do Plantão. Antes disso, o serviço é privado e testado com
   `X-Serverless-Authorization`.
7. **Auditoria automática** (`deploy/audit.py --image/--public/--cloud`), o que o Usher fazia à
   mão: CORS, escrita negada, esquemas internos fora, limites, rede do Postgres, papéis, IAM,
   chaves, APIs, conta de faturamento. O atlas roda antes de cada liberação; o cerberus tria.
8. **Agentes:** `atlas` (deploy, pede o sim do dono antes de criar, mudar ou apagar qualquer
   recurso) e `cerberus` (auditoria, só leitura, relatório no contrato de correção de
   `docs/CYBERSECURITY.md`), em `.claude/agents/`.

## Consequências

- Custo esperado ~R$ 0–5/mês (tráfego baixo; 2 M de requisições grátis; Artifact Registry dentro
  dos 0,5 GiB grátis com 2 versões). O crédito é **o mesmo do Usher**: o `emmoni-prod` entra na
  conta de faturamento, o que a §6 do `CYBERSECURITY.md` do Usher lista como achado; o dono
  precisa registrar lá que esse projeto é esperado.
- Partida a frio de ~1–2 s (Postgres + cache do PostgREST). Aceitável para a API; o site estático
  não depende dela.
- Dados ficam tão frescos quanto a última imagem publicada; publicar é um passo do atlas.
- Imagens não são servidas pela API (as questões reais publicadas não têm imagem hoje).
- Logs de requisição do Cloud Run guardam IP por 30 dias (padrão do Cloud Logging, grátis até
  50 GiB). O PostgREST só registra erros.
- Sem domínio próprio por enquanto: a URL é a `*.run.app` (domínio `.app` tem HSTS pré-carregado).
