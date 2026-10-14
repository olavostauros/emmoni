# Deploy da API no Google Cloud

Contrato do agente **caronte** (`.claude/agents/caronte.md`). Decisões 0022 e 0026. Os passos 1–7
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
| APIs | `run`, `artifactregistry`, `pubsub`, `cloudfunctions`, `cloudbuild`, `eventarc`, `billingbudgets`, `iam` | nada além destas e das dependências abaixo (o `audit.py --cloud` confere, com a mesma lista em `ALLOWED_APIS`) |
| Dependências de API | `logging`, `telemetry`, `storage-api`, `storage-component`, `iamcredentials`, `containerregistry`, `serviceusage` | declaradas pelo Google para as APIs acima (Service Usage v2beta, `services/<api>/groups/dependencies/members`, recursivo nos grupos aninhados, lido em 2026-10-13): `logging` de `run`, `cloudfunctions` e `cloudbuild` (logs); `telemetry` do `logging`; `storage-api` de `cloudfunctions` e `cloudbuild` (fonte e logs de build); `storage-component` de `cloudfunctions` (fonte enviada); `iamcredentials` do `iam` (tokens de acesso e JWT); `containerregistry` do `cloudbuild`, pelo grupo aninhado `services/containerregistry.googleapis.com/groups/dependencies` (imagens de contêiner; o grupo traz só `pubsub` e `storage-api`, já na lista). Ligam junto; não se desligam sem desligar quem depende delas. A exceção é o `serviceusage` (achado E-002): não é dependência declarada, é a API de gestão das APIs; o `gcloud services list/enable/disable`, inclusive o do `audit.py --cloud`, passa por ela |
| Repositório | `southamerica-east1-docker.pkg.dev/emmoni-prod/emmoni` | política de limpeza: manter as 2 mais novas; **nenhum papel** no repositório |
| Repositório | `gcf-artifacts` (`southamerica-east1`) | criado pelo deploy da função (passo 4), guarda a imagem dela; `artifactregistry.writer` só para a `emmoni-build` |
| Conta de serviço | `emmoni-api` | runtime do serviço; **nenhum papel** |
| Conta de serviço | `emmoni-budget-cap` | papel customizado `emmoniIngressCap` (`run.services.get`, `run.services.update`) **só no serviço `emmoni-api`** + `iam.serviceAccountUser` só na `emmoni-api` + `eventarc.eventReceiver` no projeto + `run.invoker` na própria função |
| Conta de serviço | `emmoni-build` | build da função: `logging.logWriter` e `storage.objectViewer` no projeto; `artifactregistry.writer` **só no repositório `gcf-artifacts`** |
| Serviço | `emmoni-api` | 1 vCPU, 512 MiB, `min 0`, `max 1`, concorrência 40, timeout 10 s, imagem **por digest** |
| Budget | `emmoni-monthly` | R$ 40, `exclude-all-credits`, alertas 50/90/100% real e 100% previsto, publica em `emmoni-budget` |
| Tópico | `emmoni-budget` | |
| Função | `emmoni-budget-cap` | `deploy/budget-cap/`, gen2, Python 3.12, `max-instances=1`, só interna |

Escopo dos papéis (achados E-009 e E-010, 2026-10-13): papel que dá para pôr no recurso vai no
recurso, não no projeto. O `run.services.update` do `emmoniIngressCap` não se limita ao ingresso:
no projeto, a `emmoni-budget-cap` trocaria imagem e configuração de qualquer serviço do Cloud Run
(as funções gen2 também são serviços); no `emmoni-api`, só dele, que é o único que ela precisa
cortar. Do mesmo modo, o `artifactregistry.writer` da `emmoni-build` no projeto a deixaria
retaguear imagens no repositório `emmoni`, de onde sai a API; no `gcf-artifacts`, só a imagem da
função. Os dois vínculos no recurso só podem ser criados depois que o recurso existe: o do
`gcf-artifacts` no passo 4, o do serviço no passo 6. O `audit.py --cloud` confere a política do
serviço e dos dois repositórios, e acusa os vínculos de projeto antigos numa verificação própria.

Não há VM, disco, rede, firewall, SSH, túnel nem segredo. O que o Usher protege com IAP, OS Login,
usuário do agente e hook de guarda aqui simplesmente não existe.

## 4. Passos

Cada passo: o caronte confere as pré-condições, registra o comando, o custo e a label no registro da
sessão, roda, confere e marca aqui. O passo 7 só roda depois do teste do corte (passo 4) e da
medição da ressalva do §2 (tamanho real das respostas e vazão de uma instância, com o serviço
privado), com o pior caso diário recalculado no §2; acima de R$ 100/dia, vai para a fila do dono.
Variáveis: `P=emmoni-prod R=southamerica-east1 BA=01F985-1C44C6-40CDE9`.

| # | Passo | Feito quando | Estado |
|---|---|---|---|
| 0 | Estimativa (§2) conferida pelo dono | dono disse "vai" | feito em 2026-10-13 ("vai" repassado pela sessão coordenadora; saída de rede somada ao §2) |
| 1 | Projeto e APIs | `gcloud projects describe $P` tem `emmoni=prod`; conta ligada | feito em 2026-10-13 (número 27333211980; ver a nota do passo 1) |
| 2 | Contas de serviço e papel customizado | 3 contas, 0 chaves; Compute padrão sem `editor` | feito em 2026-10-13 (3 contas, 0 chaves, Compute padrão sem `editor`; papel `emmoniIngressCap` e os seis vínculos no segundo ciclo; ver a nota do passo 2) |
| 3 | Tópico e budget | budget lista o tópico | parcial em 2026-10-13: tópico criado; `billing budgets create` negado pela permissão da sessão (ver a nota do passo 3) |
| 4 | Função de corte + teste | `emmoni-build` com `artifactregistry.writer` no `gcf-artifacts`; teste com 100% muda o ingresso; voltar com `--ingress=all` | pendente |
| 5 | Repositório e primeira imagem (seed) | `audit.py --image` 0 falhas; push por digest | pendente |
| 6 | Serviço privado (seed) | `emmoniIngressCap` da `emmoni-budget-cap` no serviço; `audit.py --public` (com token) 0 falhas | pendente |
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

O ID `emmoni-prod` é global; se estiver tomado, o caronte propõe outro e atualiza este arquivo.

Nota de 2026-10-13 (passo feito): o `gcloud projects create` liga sozinho o
`cloudapis.googleapis.com`, que traz um pacote de APIs fora do §3 (BigQuery e afins, Dataform,
Dataplex, Datastore, `sql-component`, `storage-api`/`storage-component`, `source`,
`iamcredentials`, `servicemanagement`, `telemetry`, `apptopology`, `analyticshub`). Ligadas e sem
uso, não cobram nada. Dessas, `storage-api`, `storage-component`, `iamcredentials` e `telemetry`
(mais o `logging` e o `containerregistry`) são dependências declaradas das APIs do §3 e ficam (§3, "Dependências de API"). O projeto também nasceu com `roles/editor` para a conta padrão do Compute
(`27333211980-compute@developer.gserviceaccount.com`) **e** para a do App Engine
(`emmoni-prod@appspot.gserviceaccount.com`). `audit.py --cloud emmoni-prod` logo depois do passo:
8 verificações, 2 falhas (essas duas). Desligar APIs e tirar os vínculos são remoções: estão na
fila do dono no `STATUS.md`.

### 2. Contas de serviço

```sh
for sa in emmoni-api emmoni-budget-cap emmoni-build; do
  gcloud iam service-accounts create $sa --project=$P
done
gcloud iam roles create emmoniIngressCap --project=$P --title="emmoni ingress cap" \
  --permissions=run.services.get,run.services.update
# o emmoniIngressCap é vinculado no serviço, no passo 6 (E-009), não no projeto
gcloud projects add-iam-policy-binding $P --role=roles/eventarc.eventReceiver \
  --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com --condition=None
gcloud iam service-accounts add-iam-policy-binding emmoni-api@$P.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountUser --project=$P \
  --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com
for role in logging.logWriter storage.objectViewer; do
  gcloud projects add-iam-policy-binding $P --role=roles/$role --condition=None \
    --member=serviceAccount:emmoni-build@$P.iam.gserviceaccount.com
done
# o artifactregistry.writer é vinculado no repositório gcf-artifacts, no passo 4 (E-010)
```

Depois: `gcloud projects get-iam-policy $P`. Se a conta padrão do Compute
(`<número>-compute@developer.gserviceaccount.com`) aparecer com `roles/editor`, o caronte propõe
`gcloud projects remove-iam-policy-binding $P --role=roles/editor --member=serviceAccount:<ela>`.

Nota de 2026-10-13 (passo parcial): as três contas (`emmoni-api`, `emmoni-budget-cap`,
`emmoni-build`) foram criadas, com 0 chaves de usuário. O `gcloud iam roles create
emmoniIngressCap` foi negado pelo classificador de permissões da sessão do agente ("Protected-Scope
IaC Apply"); o caronte não contornou a negação, então o papel customizado e os seis vínculos
(papel customizado, `eventarc.eventReceiver`, `iam.serviceAccountUser` na `emmoni-api` e os três da
`emmoni-build`) ficaram por criar. O próximo ciclo retoma daí, ou o dono roda o resto do bloco
acima (sem os `service-accounts create`) ou libera o comando nas permissões. O
`get-iam-policy` de agora não tem mais o `roles/editor` das contas padrão do Compute e do App Engine
(nota do passo 1). Em compensação, apareceu o
`roles/cloudbuild.builds.builder` para a conta legada do Cloud Build
(`27333211980@cloudbuild.gserviceaccount.com`), concedido pelo Google ao ligar o `cloudbuild`. Ele
fica fora do §3 e o build da função usa a `emmoni-build`. Tirar o vínculo é uma remoção e vai
para a fila do dono. `audit.py --cloud emmoni-prod`: 26 verificações, 2 falhas: esse vínculo,
e as APIs `serviceusage` e `source`, que estão fora do §3 (`source` veio do `cloudapis`, nota do
passo 1; `serviceusage` é a API que lista as APIs).

Nota de 2026-10-13, segundo ciclo (passo feito): o mesmo bloco, sem os `service-accounts create`,
rodou desta vez sem negação: papel `projects/emmoni-prod/roles/emmoniIngressCap` (só
`run.services.get` e `run.services.update`, estágio `ALPHA`, o padrão do `gcloud`), vinculado à
`emmoni-budget-cap` no projeto, mais `roles/eventarc.eventReceiver` para ela,
`roles/iam.serviceAccountUser` para ela só na conta `emmoni-api`, e `roles/logging.logWriter`,
`roles/artifactregistry.writer` e `roles/storage.objectViewer` para a `emmoni-build`. Nada disso
custa. `audit.py --cloud emmoni-prod`: 26 verificações, 2 falhas, as mesmas de antes (o
`roles/cloudbuild.builds.builder` da conta legada do Cloud Build e as APIs `serviceusage` e
`source`), ambas remoções na fila do dono; "vínculos do §3 presentes", IAM das três contas e o
papel customizado passam. O `gcloud billing budgets list` de conferência foi negado pela permissão
da sessão (só leitura; o `audit.py` leu a conta e não achou budget `emmoni`, como esperado antes
do passo 3).

Nota de 2026-10-13, depois da auditoria `docs/security/reports/2026-10-13-cloud-passo2.md`
(achados E-009 e E-010, defeitos deste plano, não da execução): o bloco acima mudou. Ele não
vincula mais no projeto o `emmoniIngressCap` (vai no serviço, passo 6) nem o
`artifactregistry.writer` da `emmoni-build` (vai no `gcf-artifacts`, passo 4). Os dois vínculos de
projeto que a versão antiga criou **continuam no `emmoni-prod`** e serão trocados: o caronte cria os
novos nos passos 4 e 6; tirar os antigos é remoção, do dono, e está na fila do `STATUS.md`:

```sh
# depois do passo 4 conferido (o primeiro build da função ainda usa o vínculo de projeto)
gcloud projects remove-iam-policy-binding emmoni-prod --role=roles/artifactregistry.writer \
  --member=serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com --condition=None
# depois do passo 6, com o vínculo novo no serviço
gcloud projects remove-iam-policy-binding emmoni-prod \
  --role=projects/emmoni-prod/roles/emmoniIngressCap \
  --member=serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com --condition=None
```

Até lá, o `audit.py --cloud` falha em "nenhum vínculo de projeto trocado por vínculo no recurso
(E-009, E-010)". Como o passo 7 exige `--cloud` com 0 falhas, as duas remoções vêm antes dele.
Nenhum dos dois vínculos custa.

### 3. Tópico e budget

```sh
gcloud pubsub topics create emmoni-budget --project=$P --labels=emmoni=prod
gcloud billing budgets create --billing-account=$BA --display-name=emmoni-monthly \
  --budget-amount=40BRL --filter-projects=projects/$P --credit-types-treatment=exclude-all-credits \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 \
  --threshold-rule=percent=1.0,basis=forecasted-spend \
  --notifications-rule-pubsub-topic=projects/$P/topics/emmoni-budget
```

Nota de 2026-10-13 (passo parcial): o tópico `projects/emmoni-prod/topics/emmoni-budget`, label
`emmoni=prod`, foi criado (Pub/Sub, nível gratuito, R$ 0). O `gcloud billing budgets create` acima
(com `$P=emmoni-prod` e `$BA=01F985-1C44C6-40CDE9` por extenso) foi negado pela permissão da
sessão do agente, como o `gcloud billing budgets list` de conferência; o caronte não contornou.
Sem o budget, o passo 4 não começa (§1: budget, tópico e corte antes do serviço). O dono roda o
`budgets create` à mão ou libera o comando nas permissões; o próximo ciclo confere com
`audit.py --cloud`. `audit.py --cloud emmoni-prod` depois do tópico: 30 verificações, 3 falhas, as
já na fila do dono (`cloudbuild.builds.builder` da conta legada, vínculos de projeto de E-009/E-010
e a API `source`); "tópico emmoni-budget com label" passa; budget é skip (passo 3 pendente).

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
# o gcf-artifacts nasce no deploy acima; a escrita da emmoni-build fica só nele (E-010)
gcloud artifacts repositories add-iam-policy-binding gcf-artifacts --project=$P --location=$R \
  --role=roles/artifactregistry.writer \
  --member=serviceAccount:emmoni-build@$P.iam.gserviceaccount.com
```

Ordem (E-010): o repositório `gcf-artifacts` só existe depois do primeiro `functions deploy`, e o
build desse primeiro deploy escreve nele com o `artifactregistry.writer` de projeto que o passo 2
antigo deixou. Depois do vínculo no repositório e do teste abaixo, o dono tira o de projeto (nota
do passo 2). Se um build posterior da função falhar sem o vínculo de projeto, o caronte registra e
põe na fila do dono; não recria o vínculo no projeto.

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
# a função de corte só muda este serviço (E-009); antes do teste do passo 4
gcloud run services add-iam-policy-binding emmoni-api --project=$P --region=$R \
  --role=projects/$P/roles/emmoniIngressCap \
  --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com
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

Uma linha por sessão do caronte: data, gasto do mês (`emmoni-prod`), crédito restante da conta,
dias restantes, observação. Fonte: console de faturamento (só leitura) ou o relatório de custos.

| Data | Gasto no mês | Crédito restante | Dias | Observação |
|---|---:|---:|---:|---|
| 2026-10-08 | — | R$ 1.779,29 (última leitura do Usher, 2026-10-07) | 90 | nada criado ainda |
| 2026-10-13 | R$ 0 (`emmoni-prod` não existe) | R$ 1.752,45 (98%, console, Créditos) | 85 | passo 0; nada criado; R$ 26,84 usados, todos do Usher |
| 2026-10-13 | não lido (sessão sem Chrome); R$ 0 esperado | não lido (última leitura R$ 1.752,45) | 85 | passo 1: projeto `emmoni-prod` criado, ligado à conta, 8 APIs do §3; nada pago existe; budget `emmoni` ainda nenhum |
| 2026-10-13 | não lido (sessão sem Chrome); R$ 0 esperado | não lido (última leitura R$ 1.752,45) | 85 | passo 2 parcial: 3 contas de serviço (sem custo); papel customizado e vínculos negados pela permissão da sessão; nada pago existe; `audit.py --cloud` sem budget `emmoni-monthly` |
| 2026-10-13 | não lido (sessão sem Chrome); R$ 0 esperado | não lido (última leitura R$ 1.752,45) | 85 | passo 2 concluído: papel `emmoniIngressCap` e seis vínculos (sem custo); nada pago existe; `audit.py --cloud` 26 verificações, 2 falhas já na fila do dono |
| 2026-10-13 | não lido (sessão sem Chrome; sessão só de documento); R$ 0 esperado | não lido (última leitura R$ 1.752,45) | 85 | nenhum passo; nada criado nem lido na nuvem: E-009, E-010 e E-002 (parcial) corrigidos no plano (§3, passos 2, 4 e 6) e no `audit.py` |
| 2026-10-13 | não lido (sessão sem Chrome); R$ 0 esperado | não lido (última leitura R$ 1.752,45) | 85 | passo 3 parcial: tópico `emmoni-budget` (R$ 0); `billing budgets create` e `list` negados pela permissão da sessão; nada pago existe; `audit.py --cloud` 30 verificações, 3 falhas já na fila do dono |
