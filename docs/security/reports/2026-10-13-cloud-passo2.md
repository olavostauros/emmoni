# Auditoria 2026-10-13 (segunda) — projeto `emmoni-prod` (depois do passo 2)

| | |
|---|---|
| Data | 2026-10-13, ~18:00 -03 |
| Auditor | cerberus (claude-opus-5-5), só leitura |
| Commit | `73afe18` (`main`; árvore com `docs/DEPLOY.md` modificado, a nota do segundo ciclo do passo 2, não commitada) |
| Imagem | nenhuma em produção (passo 5 pendente). `--image` **pulado** |
| URL | nenhuma (serviço `emmoni-api` não existe, passos 6–7 pendentes). `--public` **pulado** |
| Modos rodados | `python3 -I deploy/audit.py --cloud emmoni-prod --json data/security/cloud.json` → 26 verificações, 2 falhas, 5 skip, saída 1 |
| Relatório anterior | `docs/security/reports/2026-10-13-cloud.md` (depois do passo 1) |

## Saída do `audit.py --cloud`

```
ok    cloud  label emmoni=prod no projeto
skip  cloud  serviço emmoni-api existe  — ERROR: (gcloud.run.services.describe) Cannot find service [emmoni-api]
skip  cloud  invocação pública (allUsers) — só com o sim do dono  — serviço não existe
ok    cloud  nenhuma conta de serviço com owner/editor
ok    cloud  nenhum papel do projeto para allUsers
FAIL  cloud  vínculos do projeto só os do DEPLOY.md §3  — ['roles/cloudbuild.builds.builder=serviceAccount:27333211980@cloudbuild.gserviceaccount.com']
ok    cloud  roles/owner só para user:olavostauros@gmail.com
ok    cloud  vínculos do §3 presentes
ok    cloud  sem chave de usuário em emmoni-budget-cap
ok    cloud  sem chave de usuário em emmoni-build
ok    cloud  sem chave de usuário em emmoni-prod
ok    cloud  sem chave de usuário em 27333211980-compute
ok    cloud  sem chave de usuário em emmoni-api
ok    cloud  contas de serviço só as do DEPLOY.md §3
skip  cloud  contas padrão do Google (sem uso; tirar o editor, E-001)  — ['27333211980-compute@developer.gserviceaccount.com', 'emmoni-prod@appspot.gserviceaccount.com']
ok    cloud  contas de serviço do §3 existem
ok    cloud  IAM da conta emmoni-api como no §3
ok    cloud  IAM da conta emmoni-budget-cap como no §3
ok    cloud  IAM da conta emmoni-build como no §3
ok    cloud  papel customizado só o emmoniIngressCap
ok    cloud  papel emmoniIngressCap só com run.services.get/update
skip  cloud  budget emmoni-monthly como no §3  — passo 3 do DEPLOY.md §4 pendente: nenhum budget emmoni-monthly na conta 01F985-1C44C6-40CDE9
skip  cloud  tópico emmoni-budget com label emmoni=prod  — passo 3 do DEPLOY.md §4 pendente: ERROR: (gcloud.pubsub.topics.describe) NOT_FOUND ...
skip  cloud  função emmoni-budget-cap como no §3  — passo 4 do DEPLOY.md §4 pendente: ERROR: (gcloud.functions.describe) ResponseError: status=[404] ...
FAIL  cloud  nenhuma API além das previstas  — ['serviceusage.googleapis.com', 'source.googleapis.com']
ok    cloud  faturamento na conta prevista
26 verificação(ões), 2 falha(s)
```

As duas falhas são E-003 e E-002, já abertos. Conferi à mão os "ok" de IAM (abaixo); os skips de
budget, tópico e função valem porque os passos 3–4 estão pendentes e o serviço não existe.

## Conferência à mão

```
$ gcloud projects get-iam-policy emmoni-prod --project=emmoni-prod --format=json   (papel, membros, condição)
projects/emmoni-prod/roles/emmoniIngressCap ['serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com'] None
roles/artifactregistry.writer ['serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com'] None
roles/cloudbuild.builds.builder ['serviceAccount:27333211980@cloudbuild.gserviceaccount.com'] None
roles/cloudbuild.serviceAgent ['serviceAccount:service-27333211980@gcp-sa-cloudbuild.iam.gserviceaccount.com'] None
roles/cloudfunctions.standardServiceAgent ['serviceAccount:service-27333211980@gcf-admin-robot.iam.gserviceaccount.com'] None
roles/containerregistry.ServiceAgent ['serviceAccount:service-27333211980@containerregistry.iam.gserviceaccount.com'] None
roles/eventarc.eventReceiver ['serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com'] None
roles/logging.logWriter ['serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com'] None
roles/owner ['user:olavostauros@gmail.com'] None
roles/pubsub.serviceAgent ['serviceAccount:service-27333211980@gcp-sa-pubsub.iam.gserviceaccount.com'] None
roles/run.serviceAgent ['serviceAccount:service-27333211980@serverless-robot-prod.iam.gserviceaccount.com'] None
roles/storage.objectViewer ['serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com'] None

$ gcloud iam roles describe emmoniIngressCap --project=emmoni-prod --format=json
includedPermissions: run.services.get, run.services.update; stage: ALPHA; title: "emmoni ingress cap"
$ gcloud iam roles list --project=emmoni-prod --show-deleted   → só projects/emmoni-prod/roles/emmoniIngressCap

$ gcloud iam service-accounts get-iam-policy <conta>@emmoni-prod.iam.gserviceaccount.com --project=emmoni-prod
emmoni-api:        roles/iam.serviceAccountUser → serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com
emmoni-budget-cap: { "etag": "ACAB" }   (vazio)
emmoni-build:      { "etag": "ACAB" }   (vazio)

$ gcloud iam service-accounts list --project=emmoni-prod --format="value(email,disabled)"
emmoni-budget-cap@...  False | emmoni-build@...  False | emmoni-api@...  False
emmoni-prod@appspot.gserviceaccount.com  True | 27333211980-compute@developer.gserviceaccount.com  False

$ gcloud services list --enabled --project=emmoni-prod --format="value(config.name)" | sort
artifactregistry billingbudgets cloudbuild cloudfunctions containerregistry eventarc iamcredentials iam
logging pubsub run serviceusage source storage-api storage-component telemetry   (16; sufixo omitido)

$ gcloud run services list / functions list / artifacts repositories list (southamerica-east1) /
  storage buckets list / pubsub topics list / eventarc triggers list (southamerica-east1) /
  builds list --limit=5   (todos com --project=emmoni-prod)
→ todos vazios
```

Os seis vínculos novos são exatamente os do bloco do passo 2 (`DEPLOY.md` §4), sem condição, e o
`iam.serviceAccountUser` da `emmoni-budget-cap` está só na conta `emmoni-api`, não no projeto.

## Achados abertos

### E-002 — APIs fora do `DEPLOY.md` §3: restam `serviceusage` e `source`
Severidade: MÉDIA
Componente: Service Usage (projeto)
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
FAIL  cloud  nenhuma API além das previstas  — ['serviceusage.googleapis.com', 'source.googleapis.com']
$ gcloud services list --enabled --project=emmoni-prod --format="value(config.name)" | sort
(16 ligadas: as 8 do §3, as 6 "Dependências de API" do §3, mais serviceusage e source)
```
Desde o relatório anterior: de 26 fora para 2. O pacote `cloudapis` (BigQuery e afins, Dataform,
Dataplex, Datastore, `sql-component`, `analyticshub`, `apptopology`), `monitoring`, `storage`,
`cloudtrace` e `servicemanagement` foram desligados; `iamcredentials`, `telemetry`, `storage-api`,
`storage-component`, `logging` e `containerregistry` passaram a constar do §3 como dependências.
Impacto: `source` (Cloud Source Repositories) fica utilizável por quem tem papel no projeto, sem uso previsto; `serviceusage` é a API de gestão de APIs e é necessária para o próprio `audit.py` listar as ligadas, mas não está documentada.
Correção:
1. De agente (PR `fix/E-002-serviceusage`): em `docs/DEPLOY.md` §3, linha "Dependências de API", acrescentar `serviceusage` com o motivo (gestão das APIs; o `gcloud services list` do `audit.py` depende dela), e o mesmo em `API_DEPENDENCIES` de `deploy/audit.py`, com comentário.
2. Do **dono** (remoção): `gcloud services disable source.googleapis.com --project=emmoni-prod`.
Verificação: `python3 -I deploy/audit.py --cloud emmoni-prod` → `ok    cloud  nenhuma API além das previstas`.
Exige nova imagem: não
Estado: aberto (parcialmente corrigido: 24 das 26 fora do §3 resolvidas)

### E-003 — conta legada do Cloud Build com `roles/cloudbuild.builds.builder`
Severidade: BAIXA
Componente: IAM (projeto)
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
FAIL  cloud  vínculos do projeto só os do DEPLOY.md §3  — ['roles/cloudbuild.builds.builder=serviceAccount:27333211980@cloudbuild.gserviceaccount.com']
$ gcloud builds list --project=emmoni-prod --limit=5   → vazio
```
Impacto: um build que caia na conta legada escreve no Cloud Storage e no Artifact Registry do projeto. Hoje não há caminho: não existe gatilho nem build, e o passo 4 usa `emmoni-build` explicitamente.
Correção: sem mudança em relação ao relatório anterior. Do **dono**: `gcloud projects remove-iam-policy-binding emmoni-prod --role=roles/cloudbuild.builds.builder --member=serviceAccount:27333211980@cloudbuild.gserviceaccount.com --condition=None` depois do passo 4 conferido. Alternativa: PR de agente registrando o vínculo no §3, e o dono marca `aceito`.
Verificação: `gcloud projects get-iam-policy emmoni-prod --flatten=bindings --filter='bindings.role=roles/cloudbuild.builds.builder' --format='value(bindings.members)'` → vazio.
Exige nova imagem: não
Estado: aberto

### E-009 — `emmoniIngressCap` concedido no projeto, não no serviço `emmoni-api`
Severidade: BAIXA
Componente: IAM (papel customizado, conta `emmoni-budget-cap`)
Evidência:
```
$ gcloud projects get-iam-policy emmoni-prod --project=emmoni-prod --format=json
projects/emmoni-prod/roles/emmoniIngressCap ['serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com'] None
$ gcloud iam roles describe emmoniIngressCap --project=emmoni-prod --format=json
"includedPermissions": ["run.services.get", "run.services.update"]
$ gcloud iam service-accounts get-iam-policy emmoni-api@emmoni-prod.iam.gserviceaccount.com --project=emmoni-prod
roles/iam.serviceAccountUser → serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com
```
Origem: `docs/DEPLOY.md` §4 passo 2 (`gcloud projects add-iam-policy-binding $P --role=projects/$P/roles/emmoniIngressCap`).
`run.services.update` não se limita ao ingresso: com o `actAs` na `emmoni-api`, a `emmoni-budget-cap`
consegue trocar a imagem, as variáveis e a configuração do `emmoni-api`, e, por ser no projeto, de
qualquer serviço do Cloud Run que vier a existir (as funções gen2 também são serviços do Cloud Run).
Impacto: quem conseguir executar código como `emmoni-budget-cap` (código da função ou token dela) troca a imagem da API pública, inclusive por uma com as questões reais ou conteúdo arbitrário. Hoje não há caminho: a função não existe, não há chave, e só o dono pode agir como essa conta.
Correção:
1. De agente (PR `fix/E-009-ingress-cap-no-servico`), em `docs/DEPLOY.md` §4: no passo 2, trocar o `projects add-iam-policy-binding ... emmoniIngressCap` por uma nota de que o vínculo vai no serviço; no passo 6, depois do `gcloud run deploy`, acrescentar `gcloud run services add-iam-policy-binding emmoni-api --project=$P --region=$R --role=projects/$P/roles/emmoniIngressCap --member=serviceAccount:emmoni-budget-cap@$P.iam.gserviceaccount.com`; no §3, linha `emmoni-budget-cap`, dizer "no serviço `emmoni-api`".
2. No mesmo PR, em `deploy/audit.py` `audit_cloud`: tirar o `emmoniIngressCap` da lista de vínculos esperados do projeto e conferir, quando o serviço existir, o vínculo na política do serviço (`gcloud run services get-iam-policy emmoni-api`).
3. Do **dono** (remoção, depois do passo 6 com o vínculo novo no serviço): `gcloud projects remove-iam-policy-binding emmoni-prod --role=projects/emmoni-prod/roles/emmoniIngressCap --member=serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com --condition=None`.
4. Opcional, no corpo da função (`deploy/budget-cap/`): ela só altera o campo `ingress`; já é a defesa que resta contra o resto do `run.services.update`, e vale um teste que confira isso.
Verificação: `gcloud projects get-iam-policy emmoni-prod --flatten=bindings --filter='bindings.role:emmoniIngressCap' --format='value(bindings.members)'` → vazio; `gcloud run services get-iam-policy emmoni-api --project=emmoni-prod --region=southamerica-east1` → `projects/emmoni-prod/roles/emmoniIngressCap` para `emmoni-budget-cap`; o teste do passo 4 ainda muda o ingresso para `internal`.
Exige nova imagem: não
Estado: aberto

### E-010 — `emmoni-build` com `artifactregistry.writer` no projeto inteiro
Severidade: BAIXA
Componente: IAM (conta `emmoni-build`)
Evidência:
```
$ gcloud projects get-iam-policy emmoni-prod --project=emmoni-prod --format=json
roles/artifactregistry.writer ['serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com'] None
roles/storage.objectViewer   ['serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com'] None
$ gcloud artifacts repositories list --project=emmoni-prod   → vazio (passos 4–5 pendentes)
```
Origem: `docs/DEPLOY.md` §4 passo 2 (laço `for role in logging.logWriter artifactregistry.writer storage.objectViewer`).
Impacto: depois do passo 5, a conta de build da função também pode enviar e retaguear imagens no repositório `emmoni`, de onde sai a imagem da API. Mitigado: o deploy do serviço é por digest, então uma tag trocada não chega sozinha à produção. Hoje não há caminho: o repositório não existe e só o dono age como `emmoni-build`.
Correção:
1. De agente (PR `fix/E-010-build-no-repositorio`), em `docs/DEPLOY.md` §4: no passo 4, depois do primeiro `gcloud functions deploy` (que cria o repositório `gcf-artifacts`), acrescentar `gcloud artifacts repositories add-iam-policy-binding gcf-artifacts --project=$P --location=$R --role=roles/artifactregistry.writer --member=serviceAccount:emmoni-build@$P.iam.gserviceaccount.com`; no §3, linha `emmoni-build`, dizer "`artifactregistry.writer` só no `gcf-artifacts`". Ajustar a lista de vínculos esperados em `deploy/audit.py` no mesmo PR.
2. Do **dono** (remoção, depois do teste do passo 4 com o vínculo novo): `gcloud projects remove-iam-policy-binding emmoni-prod --role=roles/artifactregistry.writer --member=serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com --condition=None`.
3. Se o primeiro build da função falhar sem o vínculo no projeto (ordem: o repositório nasce no próprio deploy), manter o vínculo no projeto até o passo 4 e só então mover. Registrar isso no passo.
Verificação: `gcloud projects get-iam-policy emmoni-prod --flatten=bindings --filter='bindings.role=roles/artifactregistry.writer' --format='value(bindings.members)'` → vazio; `gcloud artifacts repositories get-iam-policy emmoni --project=emmoni-prod --location=southamerica-east1` sem `emmoni-build`.
Exige nova imagem: não
Estado: aberto

### E-007 — nenhum budget cobre o `emmoni-prod`
Severidade: INFO
Componente: Faturamento
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
skip  cloud  budget emmoni-monthly como no §3  — passo 3 do DEPLOY.md §4 pendente: nenhum budget emmoni-monthly na conta 01F985-1C44C6-40CDE9
$ gcloud run services list / functions list / artifacts repositories list / storage buckets list --project=emmoni-prod → vazios
```
Impacto: nenhum hoje; nada que cobre existe no projeto (contas de serviço, papéis e vínculos são grátis).
Aceito por: `docs/DEPLOY.md` §1 ("Os budgets, o tópico e a função de corte (passos 2–4) existem antes do serviço (passo 6)") e §4 (passo 3 pendente). Vira **ALTA** se qualquer recurso pago for criado antes do budget `emmoni-monthly`.
Correção: passo 3 do `DEPLOY.md` (caronte), que é o próximo.
Verificação: `python3 -I deploy/audit.py --cloud emmoni-prod` → `ok    cloud  budget emmoni-monthly como no §3`.
Exige nova imagem: não
Estado: aberto

### E-008 — `emmoni-prod` na conta de faturamento do Usher
Severidade: INFO
Componente: Faturamento
Evidência: `python3 -I deploy/audit.py --cloud emmoni-prod` → `ok    cloud  faturamento na conta prevista` (conta `01F985-1C44C6-40CDE9`). A listagem à mão dos projetos da conta (`gcloud billing projects list`) foi negada pela permissão desta sessão; a evidência da lista vem do relatório anterior.
Impacto: nenhum para o emmoni; para o Usher, é o "projeto novo na conta" que o `CYBERSECURITY.md` §6 dele lista como achado.
Aceito por: decisão 0022, Consequências ("o dono precisa registrar lá que esse projeto é esperado").
Correção: do **dono**, no repositório do Usher (nenhum agente do emmoni mexe lá).
Verificação: a auditoria do Usher não acusa `emmoni-prod`.
Exige nova imagem: não
Estado: aberto

## Resolvidos

- **E-001** (`roles/editor` nas contas padrão do Compute e do App Engine): **resolvido**. Nenhum
  vínculo `roles/editor` na política do projeto (lista completa acima); `audit.py` →
  `ok    cloud  nenhuma conta de serviço com owner/editor`. A conta `emmoni-prod@appspot` está
  desativada (`disabled: True`); a do Compute segue ativa, sem papel e sem chave.
- **E-004**, **E-005**, **E-006** (defeitos do `audit.py --cloud`): corrigidos no ciclo anterior
  (commit `1beb3cc`) e confirmados nesta execução: a falha de APIs não tolera nada fora do §3,
  `allUsers` dá skip com o serviço ausente, e vínculos, contas, papel customizado, budget, tópico e
  função são conferidos.

## Notas de ferramenta

- Nenhum falso positivo nesta execução: os 2 FAIL (E-002, E-003) e os 5 skip conferem com a leitura
  à mão.
- O `audit.py` confere as permissões do `emmoniIngressCap` e quem o tem, mas não **onde** ele está
  vinculado (projeto ou serviço). A correção de E-009 inclui essa mudança no script.
- O papel está no estágio `ALPHA`, o padrão do `gcloud iam roles create`. O estágio não muda
  permissões e não vira achado.

## Notas do analista

- **O que mudou desde o relatório anterior**: papel `emmoniIngressCap` criado e seis vínculos
  (passo 2), todos iguais ao bloco do `DEPLOY.md` §4 e sem condição. Saíram os dois `roles/editor`
  (E-001) e 24 das 26 APIs fora do §3 (E-002); o §3 ganhou a linha "Dependências de API". As três
  contas do §3 existem, sem chave de usuário. Nenhum serviço, função, tópico, repositório, bucket,
  gatilho do Eventarc nem build.
- **Novos neste relatório**: E-009 e E-010, os dois endurecimentos de escopo nos vínculos que o
  passo 2 criou. Os dois seguem o `DEPLOY.md` §3 à risca: o defeito está no documento, não na execução.
- **`deploy/` e migrações do `api`**: nenhum commit em `deploy/` nem em `db/` depois de `1beb3cc`
  (`git log 1beb3cc..HEAD`: só parser, aprovações e `docs/DEPLOY.md`). Nada a auditar ali.
- **`allUsers`**: nenhum vínculo no projeto nem nas contas de serviço; não há serviço.
- **Não verificado (permissão da sessão negou)**: a leitura à mão de `gcloud billing projects
  describe/list`, `gcloud billing budgets list` e `gcloud projects get-ancestors`. Não tentei outro
  caminho. A conta de faturamento e a ausência do budget `emmoni-monthly` ficam com a evidência do
  `audit.py`, que leu as duas nesta execução.
- **Não verificado (fora do alcance)**: logs de auditoria de acesso a dados, contatos essenciais,
  consumo do mês (sem console de faturamento).
- **Pulado**: `--image`, `--public`, digest em produção, `run revisions list` e cabeçalhos da
  resposta pública, porque não há imagem nem serviço (passos 5–6 pendentes).
- Nenhum comando de escrita foi rodado; só o projeto `emmoni-prod` foi lido (e a conta de
  faturamento, pelo `audit.py`).

## Ordem para o corretor

1. **E-002** passo 1 (agente, PR): documentar `serviceusage` no §3 e no `API_DEPENDENCIES`; o dono
   desliga o `source`. Com isso, e com E-003, o `audit.py --cloud` fica sem FAIL antes do passo 3.
2. **E-009** (agente, PR antes do passo 6): o vínculo `emmoniIngressCap` passa a ficar no serviço,
   com o `DEPLOY.md` e o `audit.py` ajustados; o dono remove o do projeto depois do passo 6.
3. **E-010** (agente, PR antes do passo 4): `artifactregistry.writer` da `emmoni-build` só no
   `gcf-artifacts`. E-003 (dono) depois do passo 4 conferido.
