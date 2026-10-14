# Auditoria 2026-10-14 — projeto `emmoni-prod` (depois do passo 3 parcial)

| | |
|---|---|
| Data | 2026-10-14, ~02:10 -03 |
| Auditor | cerberus (claude-opus-5-5), só leitura |
| Commit | `976607e` (`main`; árvore com três manifestos em `ingest/manifests/` modificados por outra sessão, nada em `deploy/` nem `docs/`) |
| Imagem | nenhuma em produção (passo 5 pendente). `--image` **pulado** |
| URL | nenhuma (serviço `emmoni-api` não existe, passos 6–7 pendentes). `--public` **pulado** |
| Modos rodados | `python3 -I deploy/audit.py --cloud emmoni-prod --json data/security/cloud.json` → 30 verificações, 3 falhas, 8 skip, saída 1 |
| Relatório anterior | `docs/security/reports/2026-10-13-cloud-passo2.md` (depois do passo 2) |

## Saída do `audit.py --cloud`

```
ok    cloud  label emmoni=prod no projeto
skip  cloud  serviço emmoni-api existe  — ERROR: (gcloud.run.services.describe) Cannot find service [emmoni-api]
skip  cloud  invocação pública (allUsers) — só com o sim do dono  — serviço não existe
skip  cloud  IAM do serviço emmoni-api como no §3  — serviço não existe
ok    cloud  nenhuma conta de serviço com owner/editor
ok    cloud  nenhum papel do projeto para allUsers
FAIL  cloud  vínculos do projeto só os do DEPLOY.md §3  — ['roles/cloudbuild.builds.builder=serviceAccount:27333211980@cloudbuild.gserviceaccount.com']
FAIL  cloud  nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)  — remoção do dono: ['projects/emmoni-prod/roles/emmoniIngressCap=serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com (E-009, vai no serviço emmoni-api)', 'roles/artifactregistry.writer=serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com (E-010, vai no repositório gcf-artifacts)']
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
skip  cloud  IAM do repositório gcf-artifacts como no §3  — passo 4 do DEPLOY.md §4 pendente: ERROR: (gcloud.artifacts.repositories.describe) NOT_FOUND ...
skip  cloud  IAM do repositório emmoni como no §3  — passo 5 do DEPLOY.md §4 pendente: ERROR: (gcloud.artifacts.repositories.describe) NOT_FOUND ...
skip  cloud  budget emmoni-monthly como no §3  — passo 3 do DEPLOY.md §4 pendente: nenhum budget emmoni-monthly na conta 01F985-1C44C6-40CDE9
ok    cloud  tópico emmoni-budget com label emmoni=prod
skip  cloud  função emmoni-budget-cap como no §3  — passo 4 do DEPLOY.md §4 pendente: ERROR: (gcloud.functions.describe) ResponseError: status=[404] ...
FAIL  cloud  nenhuma API além das previstas  — ['source.googleapis.com']
ok    cloud  faturamento na conta prevista
30 verificação(ões), 3 falha(s)
```

(A linha do segundo FAIL vem inteira do `data/security/cloud.json`; o console corta a evidência
em 160 caracteres.) As três falhas são E-003, E-009 + E-010 (uma verificação para os dois) e
E-002, todos abertos e na fila do dono no `STATUS.md`. Os skips valem: passos 3 (budget), 4, 5 e
6 pendentes e serviço inexistente.

## Conferência à mão

```
$ gcloud pubsub topics list --project=emmoni-prod --format=json
[{"labels": {"emmoni": "prod"}, "name": "projects/emmoni-prod/topics/emmoni-budget"}]
$ gcloud pubsub topics describe emmoni-budget --project=emmoni-prod --format=json
{"labels": {"emmoni": "prod"}, "name": "projects/emmoni-prod/topics/emmoni-budget"}
   (sem kmsKeyName, sem messageRetentionDuration, sem schemaSettings, sem ingestão externa)
$ gcloud pubsub topics get-iam-policy emmoni-budget --project=emmoni-prod --format=json
{"etag": "ACAB"}                                  (política vazia: nenhum vínculo no tópico)
$ gcloud pubsub topics list-subscriptions emmoni-budget --project=emmoni-prod
Listed 0 items.
$ gcloud pubsub subscriptions list / snapshots list / schemas list --project=emmoni-prod
(vazios)

$ gcloud projects get-iam-policy emmoni-prod --format=json   (papel, membros, condição)
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
auditConfigs: None
   (idêntica à do relatório anterior)

$ gcloud services list --enabled --project=emmoni-prod --format="value(config.name)" | sort
artifactregistry billingbudgets cloudbuild cloudfunctions containerregistry eventarc iamcredentials iam
logging pubsub run serviceusage source storage-api storage-component telemetry   (16; sufixo omitido)

$ gcloud iam service-accounts list --project=emmoni-prod --format="value(email,disabled)"
emmoni-budget-cap False | emmoni-build False | emmoni-prod@appspot True | 27333211980-compute False | emmoni-api False
$ gcloud iam service-accounts get-iam-policy <conta>@emmoni-prod.iam.gserviceaccount.com --project=emmoni-prod
emmoni-api:        roles/iam.serviceAccountUser → serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com
emmoni-budget-cap: {"etag":"ACAB"}   emmoni-build: {"etag":"ACAB"}
$ gcloud iam roles list --project=emmoni-prod --show-deleted   → só projects/emmoni-prod/roles/emmoniIngressCap
$ gcloud iam roles describe emmoniIngressCap --project=emmoni-prod --format="value(includedPermissions)"
run.services.get;run.services.update

$ gcloud run services list / run jobs list / functions list / artifacts repositories list (southamerica-east1) /
  storage buckets list / eventarc triggers list (southamerica-east1) / builds list --limit=5 /
  builds triggers list   (todos com --project=emmoni-prod)
→ todos vazios
```

**O tópico não tem exposição indevida.** A política dele é vazia; publicar ou assinar só vem de
papel no projeto, e no projeto quem tem `pubsub.topics.publish`/`pubsub.subscriptions.create` é só
o `roles/owner` do dono (o `eventarc.eventReceiver` da `emmoni-budget-cap` dá só
`eventarc.events.receive*`; o `pubsub.serviceAgent` é o agente do próprio Pub/Sub). Nenhum
`allUsers`/`allAuthenticatedUsers`, nenhuma assinatura, nenhuma chave de criptografia de
terceiros. Isso importa porque, depois do passo 4, quem publica no tópico dispara a função de
corte (o próprio teste do passo 4 faz isso com um `topics publish` à mão): publicar no tópico é
derrubar a API. Hoje só o dono consegue. O que falta é a ferramenta conferir isso (E-011).

## Achados abertos

### E-011 — `audit.py --cloud` não confere a política nem as assinaturas do tópico `emmoni-budget`
Severidade: BAIXA
Componente: `deploy/audit.py` (`audit_topic`)
Evidência:
```
$ grep -n "def audit_topic" -A 11 deploy/audit.py
873:def audit_topic(project: str, absent: Absent, rep: Report) -> None:
...
876:    topic, err = gcloud_json(["pubsub", "topics", "describe", TOPIC, f"--project={project}"])
...
883:        rep.add(m, name, labels.get("emmoni") == "prod", f"{labels}")
   (só o describe e a label; nenhum get-iam-policy nem list-subscriptions)
$ gcloud pubsub topics get-iam-policy emmoni-budget --project=emmoni-prod --format=json
{"etag": "ACAB"}
```
Impacto: depois do passo 4, um `roles/pubsub.publisher` concedido a mais no tópico (ou um `allUsers`) deixaria terceiros dispararem o corte e tirar a API do ar, e uma assinatura extra leria os valores de gasto da conta compartilhada com o Usher, sem que a auditoria acuse; hoje a política está vazia e não há caminho.
Correção (agente, PR `fix/E-011-iam-do-topico`):
1. Em `deploy/audit.py`, `audit_topic`: depois do `describe`, ler `gcloud pubsub topics get-iam-policy emmoni-budget --project=<projeto> --format=json` e comparar com `compare_bindings` contra os vínculos previstos. Previsto, depois do passo 3 com o budget: só `roles/pubsub.publisher` para `serviceAccount:billing-budget-alert@system.gserviceaccount.com` (a conta que o Cloud Billing usa para publicar as notificações do budget, segundo a documentação dele; conferir o nome real na primeira execução depois do `budgets create`). Antes do budget, a política tem de estar vazia. Qualquer outro vínculo, `allUsers` ou `allAuthenticatedUsers` é FAIL.
2. No mesmo lugar: `gcloud pubsub topics list-subscriptions emmoni-budget --project=<projeto>`; previsto, depois do passo 4, só a assinatura que o Eventarc cria para o gatilho da `emmoni-budget-cap` (prefixo `eventarc-southamerica-east1-emmoni-budget-cap-`); antes do passo 4, nenhuma. Outra assinatura é FAIL.
3. Em `docs/DEPLOY.md` §3, linha "Tópico `emmoni-budget`": registrar a política esperada (publicador só a conta do Cloud Billing; nenhuma assinatura além da do gatilho). Em `docs/CYBERSECURITY.md` §4, linha `--cloud`: acrescentar "política e assinaturas do tópico".
4. Em `tests/test_deploy_audit.py`: casos para política vazia (ok antes do budget), publicador extra (FAIL), `allUsers` (FAIL) e assinatura extra (FAIL).
Verificação: `python3 -I deploy/audit.py --cloud emmoni-prod` mostra `ok    cloud  IAM do tópico emmoni-budget como no §3` e `ok    cloud  assinaturas do tópico emmoni-budget como no §3`; `make gates` verde.
Exige nova imagem: não
Estado: corrigido no código (aguarda commit)

### E-002 — API fora do `DEPLOY.md` §3: resta `source`
Severidade: MÉDIA
Componente: Service Usage (projeto)
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
FAIL  cloud  nenhuma API além das previstas  — ['source.googleapis.com']
$ gcloud services list --enabled --project=emmoni-prod --format="value(config.name)" | sort
(16 ligadas: as 8 do §3, as 7 "Dependências de API" do §3, mais source)
```
Desde o relatório anterior: a parte de agente está feita (`serviceusage` documentado no §3 e em
`API_DEPENDENCIES` do `deploy/audit.py`, commit `f86f360`), e o `audit.py` deixou de acusá-lo.
Impacto: `source` (Cloud Source Repositories) fica utilizável por quem tem papel no projeto, sem uso previsto.
Correção: do **dono** (remoção, já na fila do `STATUS.md`): `gcloud services disable source.googleapis.com --project=emmoni-prod`.
Verificação: `python3 -I deploy/audit.py --cloud emmoni-prod` → `ok    cloud  nenhuma API além das previstas`.
Exige nova imagem: não
Estado: aberto (parte de agente corrigida em `f86f360`; falta a remoção do dono)

### E-003 — conta legada do Cloud Build com `roles/cloudbuild.builds.builder`
Severidade: BAIXA
Componente: IAM (projeto)
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
FAIL  cloud  vínculos do projeto só os do DEPLOY.md §3  — ['roles/cloudbuild.builds.builder=serviceAccount:27333211980@cloudbuild.gserviceaccount.com']
$ gcloud builds list --project=emmoni-prod --limit=5   → vazio;  gcloud builds triggers list → vazio
```
Impacto: um build que caia na conta legada escreve no Cloud Storage e no Artifact Registry do projeto. Hoje não há caminho: nenhum gatilho nem build, e o passo 4 usa `emmoni-build` explicitamente.
Correção: sem mudança. Do **dono** (na fila): `gcloud projects remove-iam-policy-binding emmoni-prod --role=roles/cloudbuild.builds.builder --member=serviceAccount:27333211980@cloudbuild.gserviceaccount.com --condition=None`, de preferência depois do passo 4 conferido.
Verificação: `gcloud projects get-iam-policy emmoni-prod --flatten=bindings --filter='bindings.role=roles/cloudbuild.builds.builder' --format='value(bindings.members)'` → vazio.
Exige nova imagem: não
Estado: aberto

### E-009 — `emmoniIngressCap` concedido no projeto, não no serviço `emmoni-api`
Severidade: BAIXA
Componente: IAM (papel customizado, conta `emmoni-budget-cap`)
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
FAIL  cloud  nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)  — remoção do dono: ['projects/emmoni-prod/roles/emmoniIngressCap=serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com (E-009, vai no serviço emmoni-api)', ...]
```
Desde o relatório anterior: a parte de agente está feita em `f86f360` (`DEPLOY.md` §3 e passos 2 e
6; `audit.py` com `replaced_bindings` e `audit_service_iam`). O vínculo de projeto continua.
Impacto: quem executar código como `emmoni-budget-cap` troca imagem e configuração de qualquer serviço do Cloud Run do projeto. Hoje não há caminho: não há função, chave nem serviço.
Correção: do **dono** (na fila), depois do passo 6 com o vínculo no serviço: `gcloud projects remove-iam-policy-binding emmoni-prod --role=projects/emmoni-prod/roles/emmoniIngressCap --member=serviceAccount:emmoni-budget-cap@emmoni-prod.iam.gserviceaccount.com --condition=None`.
Verificação: `python3 -I deploy/audit.py --cloud emmoni-prod` → a evidência da verificação "nenhum vínculo de projeto trocado..." não cita mais E-009, e `ok    cloud  IAM do serviço emmoni-api como no §3`.
Exige nova imagem: não
Estado: aberto (parte de agente corrigida em `f86f360`; falta a remoção do dono, pré-condição do passo 7)

### E-010 — `emmoni-build` com `artifactregistry.writer` no projeto inteiro
Severidade: BAIXA
Componente: IAM (conta `emmoni-build`)
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
FAIL  cloud  nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)  — remoção do dono: [..., 'roles/artifactregistry.writer=serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com (E-010, vai no repositório gcf-artifacts)']
$ gcloud artifacts repositories list --project=emmoni-prod --location=southamerica-east1   → vazio
```
Desde o relatório anterior: parte de agente feita em `f86f360` (passo 4 cria o vínculo no
`gcf-artifacts`; `audit.py` com `audit_repositories`).
Impacto: depois do passo 5, a conta de build da função poderia retaguear imagens no repositório `emmoni`; mitigado pelo deploy por digest. Hoje não há caminho: nenhum repositório.
Correção: do **dono** (na fila), depois do passo 4 conferido: `gcloud projects remove-iam-policy-binding emmoni-prod --role=roles/artifactregistry.writer --member=serviceAccount:emmoni-build@emmoni-prod.iam.gserviceaccount.com --condition=None`.
Verificação: `python3 -I deploy/audit.py --cloud emmoni-prod` → `ok    cloud  nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)` (com E-009 também removido) e `ok    cloud  IAM do repositório gcf-artifacts como no §3`.
Exige nova imagem: não
Estado: aberto (parte de agente corrigida em `f86f360`; falta a remoção do dono)

### E-007 — nenhum budget cobre o `emmoni-prod`
Severidade: INFO
Componente: Faturamento
Evidência:
```
$ python3 -I deploy/audit.py --cloud emmoni-prod
skip  cloud  budget emmoni-monthly como no §3  — passo 3 do DEPLOY.md §4 pendente: nenhum budget emmoni-monthly na conta 01F985-1C44C6-40CDE9
$ gcloud run services list / functions list / artifacts repositories list / storage buckets list --project=emmoni-prod → vazios
```
Desde o relatório anterior: o tópico `emmoni-budget` existe, mas o budget não (o `billing budgets
create` do passo 3 foi negado pela permissão da sessão do caronte e está na fila do dono). O
tópico sem mensagens não cobra (Pub/Sub no nível gratuito).
Impacto: nenhum hoje; nada que cobre existe no projeto.
Aceito por: `docs/DEPLOY.md` §1 ("Os budgets, o tópico e a função de corte (passos 2–4) existem antes do serviço (passo 6)") e §4 (passo 3 parcial). Vira **ALTA** se qualquer recurso pago (função, repositório, serviço) for criado antes do budget `emmoni-monthly`.
Correção: do **dono** (na fila): o `gcloud billing budgets create` do `DEPLOY.md` §4 passo 3, ou liberar o comando para o caronte.
Verificação: `python3 -I deploy/audit.py --cloud emmoni-prod` → `ok    cloud  budget emmoni-monthly como no §3`.
Exige nova imagem: não
Estado: aberto

### E-008 — `emmoni-prod` na conta de faturamento do Usher
Severidade: INFO
Componente: Faturamento
Evidência: `python3 -I deploy/audit.py --cloud emmoni-prod` → `ok    cloud  faturamento na conta prevista` (conta `01F985-1C44C6-40CDE9`). A leitura à mão (`gcloud billing projects describe/list`) foi negada de novo pela permissão desta sessão.
Impacto: nenhum para o emmoni; para o Usher, é o "projeto novo na conta" que a auditoria dele lista como achado.
Aceito por: decisão 0022, Consequências ("o dono precisa registrar lá que esse projeto é esperado").
Correção: do **dono**, no repositório do Usher (nenhum agente do emmoni mexe lá).
Verificação: a auditoria do Usher não acusa `emmoni-prod`.
Exige nova imagem: não
Estado: aberto

## Resolvidos

Nenhum desde o relatório anterior. Já resolvidos antes: E-001 (`roles/editor` das contas padrão;
a do App Engine segue desativada, a do Compute ativa sem papel nem chave) e E-004 a E-006
(defeitos do `audit.py`).

## Notas de ferramenta

- Nenhum falso positivo: os 3 FAIL e os 8 skip conferem com a leitura à mão.
- As verificações novas de `f86f360` rodaram pela primeira vez contra a nuvem e se comportaram como
  o §4 do `CYBERSECURITY.md` descreve: a política do serviço dá skip com o serviço ausente (não toma
  o `{"etag"}` vazio por ok), os repositórios são lidos com `describe` antes do `get-iam-policy` e
  dão skip pelo passo pendente, e os dois vínculos de projeto de E-009/E-010 têm verificação própria.
- Lacuna: o tópico só tem label conferida, não política nem assinaturas (E-011).
- O console corta a evidência em 160 caracteres (`deploy/audit.py`, linha 129); o JSON tem a
  evidência inteira. Não vira achado: o JSON é a fonte da triagem.

## Notas do analista

- **O que mudou desde o relatório anterior**: na nuvem, só o tópico `emmoni-budget` (label
  `emmoni=prod`, política vazia, sem assinatura, sem retenção nem CMEK). Política do projeto, contas,
  IAM das contas, papel customizado e APIs idênticos ao relatório de 2026-10-13 18:00. Nenhum
  serviço, função, repositório, bucket, gatilho, build nem job.
- **Novo neste relatório**: E-011 (lacuna da ferramenta no tópico). Nenhum achado novo na nuvem.
- **Exposição do tópico**: nenhuma (ver "Conferência à mão"): só o `roles/owner` do dono publica ou
  assina.
- **`deploy/` e migrações do `api`**: um commit em `deploy/` desde `1beb3cc`, o `f86f360` (só
  `deploy/audit.py`: `serviceusage` em `API_DEPENDENCIES`, `replaced_bindings`, `service_bindings`,
  `repo_bindings`, `audit_service_iam`, `audit_repositories`), lido inteiro; nenhuma verificação
  ficou mais frouxa (os vínculos de E-009/E-010 saíram da lista tolerada e viraram FAIL próprio).
  Em `db/`, só YAMLs de taxonomia (`7ad4ffe`); nenhuma migração, função do `api`, `GRANT` ao
  `emmoni_web` ou CORS mudou. `Dockerfile`, `build.sh` e `budget-cap/` sem mudança.
- **`allUsers`**: nenhum no projeto, nas contas nem no tópico; não há serviço.
- **Não verificado (permissão da sessão negou)**: `gcloud billing projects describe/list`; não
  tentei outro caminho. Conta de faturamento e ausência do budget ficam com a evidência do
  `audit.py`.
- **Não verificado (fora do alcance)**: logs de auditoria de acesso a dados (`auditConfigs` vazio,
  o padrão), contatos essenciais, consumo do mês.
- **Pulado**: `--image`, `--public`, digest em produção, `run revisions list` e cabeçalhos da
  resposta pública: não há imagem nem serviço (passos 5–6 pendentes).
- Nenhum comando de escrita foi rodado; só o projeto `emmoni-prod` foi lido (e a conta de
  faturamento, pelo `audit.py`).

## Ordem para o corretor

1. **E-011** (agente, PR `fix/E-011-iam-do-topico`): política e assinaturas do tópico no
   `audit.py`, antes do passo 3 (budget) e do passo 4 (função), para a primeira execução depois
   deles já conferir o publicador do Cloud Billing e a assinatura do Eventarc.
2. **E-007 / passo 3** (dono): o `billing budgets create`; sem ele o passo 4 não começa.
3. **E-002** e **E-003** (dono): `services disable source` e a remoção do `cloudbuild.builds.builder`;
   E-010 depois do passo 4 e E-009 depois do passo 6, ambos antes do passo 7.
