# Deploy da API no Google Cloud

Contrato do agente **atlas** (`.claude/agents/atlas.md`). Decisões 0022 e 0026. Os passos 1–7
rodam sem perguntar, um por ciclo autônomo; o passo 8, as remoções e o que o §1 proíbe continuam
dependendo do sim do dono. Todo comando leva `--project=emmoni-prod` por extenso: o projeto padrão
do `gcloud` nesta máquina é o `usher-prod`.

## 1. Dinheiro

| | |
|---|---|
| Conta de faturamento | `01F985-1C44C6-40CDE9` ("Minha conta de faturamento"), **Free Trial, compartilhada com o Usher** |
| Crédito | R$ 1.779,29, de 2026-10-07 a **2027-01-06** (o Usher planeja ~R$ 410 dele) |
| Teto do emmoni | **R$ 40/mês** (budget `emmoni-monthly`, sem créditos), com corte automático a 100% |
| Esperado | ~R$ 0–5/mês |

Regras:

- **Nunca** fazer upgrade da conta, adicionar forma de pagamento, comprar compromisso, pedir
  cota, mudar administradores da conta. É do dono, no console.
- Os budgets, o tópico e a função de corte (passos 2–4) existem **antes** do serviço (passo 6).
- Não criar: VM, Cloud SQL, Memorystore, GKE, balanceador, IP estático, Cloud NAT, Cloud Armor,
  `min-instances ≥ 1`, CPU sempre alocada (`--no-cpu-throttling`), domínio próprio mapeado,
  Ops Agent, exportação de logs, segunda região. Cada um é custo fixo; entra só por mudança neste
  arquivo com o custo, aprovada pelo dono.
- Todo recurso fica no projeto `emmoni-prod` e leva a label `emmoni=prod`. Nunca tocar em
  `usher-prod`, `My First Project` nem outro projeto.

## 2. Estimativa (preços do Billing Catalog, BRL, verificados em 2026-10-08 e reconferidos em 2026-10-13)

Fonte: `cloudbilling.googleapis.com/v1/services/<id>/skus?currencyCode=BRL` (Cloud Run
`152E-C115-5142`, Artifact Registry `149C-F9EC-3994`).

| Item | Preço | Uso esperado | R$/mês |
|---|---|---|---:|
| Cloud Run CPU (Tier 2, por requisição) | R$ 0,000199279 / vCPU·s | ~2.000 s (partidas a frio + consultas) | ~0,40 |
| Cloud Run memória (Tier 2) | R$ 0,000020758 / GiB·s | 0,5 GiB × ~2.000 s | ~0,02 |
| Requisições | grátis até 2 M; depois R$ 2,37 / milhão | < 100 mil | 0 |
| Saída de rede (internet, América do Sul) | R$ 0,71 / GiB (SKU `3C96-B34E-58BC`) | < 100 mil respostas × ~20–50 KB ≈ 2–5 GiB | ~1,40–3,60 |
| Imagem da função de corte (`gcf-artifacts`) e fonte no Cloud Storage | soma nos 0,5 GiB grátis do Artifact Registry; depois R$ 0,59 / GiB·mês | ~0,1–0,3 GiB | ~0–0,20 |
| Artifact Registry | grátis até 0,5 GiB; depois R$ 0,59 / GiB·mês | 2 versões (~200 MB comprimidos, camadas compartilhadas) | 0 |
| Pub/Sub, função de corte, budgets, Cloud Build (< 2.500 min), Cloud Logging (< 50 GiB) | nível gratuito | | 0 |
| **Total esperado** | | | **< 5** |
| **Pior caso** (abuso 24 h, 1 instância de 1 vCPU) | | 2,63 M s | ~550, **cortado a R$ 40** |

O pior caso é o motivo de `max-instances=1` e do corte: com o atraso do faturamento (até ~1 dia)
o mês fecha perto de R$ 80, não de R$ 550.

**Ressalva de 2026-10-13:** o pior caso acima conta só CPU. A saída de rede também escala com o
abuso e não tem nível gratuito na América do Sul: a ~100 respostas/s de ~50 KB seriam ~400 GiB
por dia, ~R$ 300/dia, bem acima dos ~R$ 18/dia de CPU. A vazão real de uma instância (1 vCPU,
concorrência 40) e o tamanho real das respostas não foram medidos; até serem, o atraso de ~1 dia
do faturamento pode deixar o mês passar bastante de R$ 80 antes do corte.
Os preços de CPU e memória (Tier 2, por requisição, inclui `southamerica-east1`), requisições e
Artifact Registry conferem com os de 2026-10-08. O nível gratuito do Cloud Run (180 mil vCPU·s,
360 mil GiB·s) é por conta de faturamento e não foi descontado acima.

## 3. Arquitetura e recursos

```
Plantão (navegador) ──HTTPS──▶ emmoni-api (Cloud Run, *.run.app)
                                  └─ container: PostgREST :8080 ─socket─▶ Postgres 17 (dados no build)
budget emmoni-monthly ─▶ Pub/Sub emmoni-budget ─▶ função emmoni-budget-cap ─▶ ingresso = interno
```

| Recurso | Nome | Observação |
|---|---|---|
| Projeto | `emmoni-prod` | novo, ligado à conta acima |
| APIs | `run`, `artifactregistry`, `pubsub`, `cloudfunctions`, `cloudbuild`, `eventarc`, `billingbudgets`, `iam` | nada além (o `audit.py --cloud` confere) |
| Repositório | `southamerica-east1-docker.pkg.dev/emmoni-prod/emmoni` | política de limpeza: manter as 2 mais novas |
| Conta de serviço | `emmoni-api` | runtime do serviço; **nenhum papel** |
| Conta de serviço | `emmoni-budget-cap` | papel customizado `emmoniIngressCap` (`run.services.get`, `run.services.update`) + `iam.serviceAccountUser` só na `emmoni-api` + `eventarc.eventReceiver` + `run.invoker` na própria função |
| Conta de serviço | `emmoni-build` | build da função: `logging.logWriter`, `artifactregistry.writer`, `storage.objectViewer` |
| Serviço | `emmoni-api` | 1 vCPU, 512 MiB, `min 0`, `max 1`, concorrência 40, timeout 10 s, imagem **por digest** |
| Budget | `emmoni-monthly` | R$ 40, `exclude-all-credits`, alertas 50/90/100% real e 100% previsto, publica em `emmoni-budget` |
| Tópico | `emmoni-budget` | |
| Função | `emmoni-budget-cap` | `deploy/budget-cap/`, gen2, Python 3.12, `max-instances=1`, só interna |

Não há VM, disco, rede, firewall, SSH, túnel nem segredo. O que o Usher protege com IAP, OS Login,
usuário do agente e hook de guarda aqui simplesmente não existe.

## 4. Passos

Cada passo: o atlas confere as pré-condições, registra o comando, o custo e a label no registro da
sessão, roda, confere e marca aqui. O passo 7 só roda depois do teste do corte (passo 4) e da
medição da ressalva do §2 (tamanho real das respostas e vazão de uma instância, com o serviço
privado), com o pior caso diário recalculado no §2; acima de R$ 100/dia, vai para a fila do dono.
Variáveis: `P=emmoni-prod R=southamerica-east1 BA=01F985-1C44C6-40CDE9`.

| # | Passo | Feito quando | Estado |
|---|---|---|---|
| 0 | Estimativa (§2) conferida pelo dono | dono disse "vai" | feito em 2026-10-13 ("vai" repassado pela sessão coordenadora; saída de rede somada ao §2) |
| 1 | Projeto e APIs | `gcloud projects describe $P` tem `emmoni=prod`; conta ligada | pendente |
| 2 | Contas de serviço e papel customizado | 3 contas, 0 chaves; Compute padrão sem `editor` | pendente |
| 3 | Tópico e budget | budget lista o tópico | pendente |
| 4 | Função de corte + teste | teste com 100% muda o ingresso; voltar com `--ingress=all` | pendente |
| 5 | Repositório e primeira imagem (seed) | `audit.py --image` 0 falhas; push por digest | pendente |
| 6 | Serviço privado (seed) | `audit.py --public` (com token) 0 falhas | pendente |
| 7 | Público com seed | `allUsers` invoker; `audit.py --public` e `--cloud` 0 falhas; Plantão avisado | pendente |
| 8 | Imagem `all` | **só com o sim do dono para publicar as questões reais**; é o único caminho delas para o público (decisão 0028) | pendente; sim do dono dado em 2026-10-13, vale depois do passo 7 |
| 9 | Três dias de observação, cerberus re-audita, decisão 0022 aceita | relatório em `docs/security/reports/` | pendente |

### 1. Projeto e APIs

```sh
gcloud projects create $P --name=emmoni-prod --labels=emmoni=prod
gcloud billing projects link $P --billing-account=$BA
gcloud services enable run.googleapis.com artifactregistry.googleapis.com pubsub.googleapis.com \
  cloudfunctions.googleapis.com cloudbuild.googleapis.com eventarc.googleapis.com \
  billingbudgets.googleapis.com iam.googleapis.com --project=$P
```

O ID `emmoni-prod` é global; se estiver tomado, o atlas propõe outro e atualiza este arquivo.

### 2. Contas de serviço

```sh
for sa in emmoni-api emmoni-budget-cap emmoni-build; do
  gcloud iam service-accounts create $sa --project=$P
done
gcloud iam roles create emmoniIngressCap --project=$P --title="emmoni ingress cap" \
  --permissions=run.services.get,run.services.update
gcloud projects add-iam-policy-binding $P --role=projects/$P/roles/emmoniIngressCap \
  --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com --condition=None
gcloud projects add-iam-policy-binding $P --role=roles/eventarc.eventReceiver \
  --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com --condition=None
gcloud iam service-accounts add-iam-policy-binding emmoni-api@$P.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountUser --project=$P \
  --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com
for role in logging.logWriter artifactregistry.writer storage.objectViewer; do
  gcloud projects add-iam-policy-binding $P --role=roles/$role --condition=None \
    --member=serviceAccount:emmoni-build@$P.iam.gserviceaccount.com
done
```

Depois: `gcloud projects get-iam-policy $P`. Se a conta padrão do Compute
(`<número>-compute@developer.gserviceaccount.com`) aparecer com `roles/editor`, o atlas propõe
`gcloud projects remove-iam-policy-binding $P --role=roles/editor --member=serviceAccount:<ela>`.

### 3. Tópico e budget

```sh
gcloud pubsub topics create emmoni-budget --project=$P --labels=emmoni=prod
gcloud billing budgets create --billing-account=$BA --display-name=emmoni-monthly \
  --budget-amount=40BRL --filter-projects=projects/$P --credit-types-treatment=exclude-all-credits \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 \
  --threshold-rule=percent=1.0,basis=forecasted-spend \
  --notifications-rule-pubsub-topic=projects/$P/topics/emmoni-budget
```

### 4. Função de corte

```sh
gcloud functions deploy emmoni-budget-cap --gen2 --project=$P --region=$R \
  --runtime=python312 --source=deploy/budget-cap --entry-point=budget_cap \
  --trigger-topic=emmoni-budget \
  --service-account=emmoni-budget-cap@$P.iam.gserviceaccount.com \
  --trigger-service-account=emmoni-budget-cap@$P.iam.gserviceaccount.com \
  --build-service-account=projects/$P/serviceAccounts/emmoni-build@$P.iam.gserviceaccount.com \
  --memory=256Mi --max-instances=1 --no-allow-unauthenticated --ingress-settings=internal-only \
  --update-labels=emmoni=prod
gcloud functions add-invoker-policy-binding emmoni-budget-cap --project=$P --region=$R \
  --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com
```

Teste (depois do passo 6, com o serviço no ar):

```sh
gcloud pubsub topics publish emmoni-budget --project=$P \
  --message='{"budgetDisplayName":"teste","costAmount":40,"budgetAmount":40}'
gcloud run services describe emmoni-api --project=$P --region=$R --format='value(spec.ingress)'
#   esperado: internal  → depois, voltar:
gcloud run services update emmoni-api --project=$P --region=$R --ingress=all
```

### 5. Imagem

```sh
gcloud artifacts repositories create emmoni --project=$P --location=$R --repository-format=docker \
  --labels=emmoni=prod
gcloud artifacts repositories set-cleanup-policies emmoni --project=$P --location=$R \
  --policy=deploy/artifact-cleanup.json
gcloud auth configure-docker $R-docker.pkg.dev       # credencial pelo gcloud; nenhuma chave
make prod-image SCOPE=seed                            # imprime a tag local
python3 -I deploy/audit.py --image <tag>              # 0 falhas, senão não sobe
docker tag <tag> $R-docker.pkg.dev/$P/emmoni/emmoni-api:<build>
docker push $R-docker.pkg.dev/$P/emmoni/emmoni-api:<build>   # anotar o digest sha256
```

### 6. Serviço (privado)

```sh
gcloud run deploy emmoni-api --project=$P --region=$R \
  --image=$R-docker.pkg.dev/$P/emmoni/emmoni-api@sha256:<digest> \
  --service-account=emmoni-api@$P.iam.gserviceaccount.com \
  --cpu=1 --memory=512Mi --concurrency=40 --min-instances=0 --max-instances=1 --timeout=10 \
  --port=8080 --no-allow-unauthenticated --ingress=all --labels=emmoni=prod
URL=$(gcloud run services describe emmoni-api --project=$P --region=$R --format='value(status.url)')
python3 -I deploy/audit.py --public "$URL" \
  --header "X-Serverless-Authorization: Bearer $(gcloud auth print-identity-token)"
```

Com o serviço privado, o token vai em `X-Serverless-Authorization`, não em `Authorization`: o
PostgREST trataria um `Authorization` como JWT dele e recusaria.

### 7. Público (seed)

```sh
gcloud run services add-iam-policy-binding emmoni-api --project=$P --region=$R \
  --member=allUsers --role=roles/run.invoker
python3 -I deploy/audit.py --public "$URL" --cloud $P
```

O contrato ganha a URL pública; o aviso ao Plantão vai para a fila do dono no `STATUS.md` (decisão 0026).

### 8. Questões reais

Só com o sim do dono, nesta sessão, para publicar as questões reais: `make prod-image SCOPE=all`,
`audit.py --image`, push, `gcloud run deploy ... --image=...@sha256:<novo>`, `audit.py --public`.

## 5. Liberações e rollback

Nova versão dos dados ou do código = passos 5 e 6 com a imagem nova (o serviço continua com a
mesma URL e o mesmo IAM). A tag local diz de onde veio: `<commit>[-dirty]-<escopo>-<hash do
dump>`; uma imagem `-dirty` não vai para produção.

Rollback: `gcloud run revisions list --service=emmoni-api --project=$P --region=$R` e
`gcloud run services update-traffic emmoni-api --project=$P --region=$R --to-revisions=<anterior>=100`.

## 6. Registro de gasto

Uma linha por sessão do atlas: data, gasto do mês (`emmoni-prod`), crédito restante da conta,
dias restantes, observação. Fonte: console de faturamento (só leitura) ou o relatório de custos.

| Data | Gasto no mês | Crédito restante | Dias | Observação |
|---|---:|---:|---:|---|
| 2026-10-08 | — | R$ 1.779,29 (última leitura do Usher, 2026-10-07) | 90 | nada criado ainda |
| 2026-10-13 | R$ 0 (`emmoni-prod` não existe) | R$ 1.752,45 (98%, console, Créditos) | 85 | passo 0; nada criado; R$ 26,84 usados, todos do Usher |
