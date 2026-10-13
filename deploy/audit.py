#!/usr/bin/env python3
"""Auditoria da API de produção do emmoni (docs/CYBERSECURITY.md, decisão 0022).

Só leitura. Três modos, combináveis:

  --public URL      sondas HTTP na superfície pública (CORS, escrita negada, esquemas
                    internos fora, limite de linhas, tamanho de página, JWT, cabeçalhos)
  --image TAG       confere a imagem num container descartável (usuário, rede do Postgres,
                    pg_hba, papéis, configuração do emmoni_web, segredos no ambiente)
  --cloud PROJETO   confere o projeto no Google Cloud com `gcloud` só de leitura
                    (label, serviço Cloud Run, IAM do projeto, do serviço, dos
                    repositórios e das contas, contas de serviço, papel customizado, chaves,
                    budget, tópico, função de corte, APIs)

Saída: uma linha por verificação (`ok`/`FAIL`/`skip`) e, com --json, o relatório em JSON
para o cerberus triar. Código de saída: 0 tudo ok, 1 alguma falha, 2 não conseguiu rodar.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SITE_ORIGIN = "https://olavostauros.github.io"
# Cabeçalhos em toda sonda (--header), ex.: X-Serverless-Authorization com o serviço privado.
EXTRA_HEADERS: dict[str, str] = {}
REGION = "southamerica-east1"
SERVICE = "emmoni-api"
RUNTIME_SA = "emmoni-api"
# APIs permitidas no projeto: exatamente as linhas "APIs" e "Dependências de API" do
# docs/DEPLOY.md §3 (tests/test_deploy_audit.py confere que as duas listas batem). Nenhuma outra
# lista de tolerância: o que não está aqui falha em "nenhuma API além das previstas".
PLANNED_APIS = {
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "pubsub.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "eventarc.googleapis.com",
    "billingbudgets.googleapis.com",
    "iam.googleapis.com",
}
# Dependências declaradas pelo Google das APIs acima (Service Usage v2beta,
# `services/<api>/groups/dependencies/members`, recursivo nos grupos aninhados, lido em
# 2026-10-13). Ligam junto e não se desligam sem desligar quem depende delas.
API_DEPENDENCIES = {
    "logging.googleapis.com": "run, cloudfunctions e cloudbuild escrevem logs no Cloud Logging",
    "telemetry.googleapis.com": "o Cloud Logging depende do Cloud Telemetry",
    "storage-api.googleapis.com": "cloudfunctions e cloudbuild guardam fonte e logs de build no GCS",
    "storage-component.googleapis.com": "cloudfunctions guarda a fonte enviada no GCS",
    "iamcredentials.googleapis.com": "o iam emite tokens de acesso e JWT por ela",
    "containerregistry.googleapis.com": (
        "cloudbuild guarda imagens de contêiner nele (grupo aninhado "
        "services/containerregistry.googleapis.com/groups/dependencies)"
    ),
    # Única que não é dependência declarada (achado E-002): é a API de gestão das APIs. O
    # `gcloud services list/enable/disable`, inclusive o "nenhuma API além das previstas" abaixo,
    # passa por ela; desligada, ninguém mais lista nem liga API no projeto.
    "serviceusage.googleapis.com": "gestão das APIs; o `gcloud services list` do audit.py usa",
}
ALLOWED_APIS = PLANNED_APIS | set(API_DEPENDENCIES)

# O resto do docs/DEPLOY.md §3 (achado E-006): contas, papéis, budget, tópico e função.
BILLING_ACCOUNT = "01F985-1C44C6-40CDE9"
OWNER = "user:olavostauros@gmail.com"  # único vínculo humano: roles/owner do dono
CAP = "emmoni-budget-cap"  # conta de serviço e função de corte
BUILD_SA = "emmoni-build"
PLANNED_SAS = {RUNTIME_SA, CAP, BUILD_SA}
CUSTOM_ROLE = "emmoniIngressCap"
CUSTOM_ROLE_PERMISSIONS = {"run.services.get", "run.services.update"}
# Repositórios do Artifact Registry (§3): `gcf-artifacts` nasce no deploy da função (passo 4) e
# só a `emmoni-build` escreve nele; `emmoni` (passo 5) não dá papel a ninguém (achado E-010).
FUNCTION_REPO = "gcf-artifacts"
IMAGE_REPO = "emmoni"
BUDGET = "emmoni-monthly"
BUDGET_AMOUNT = ("BRL", "40")
BUDGET_THRESHOLDS = {
    (0.5, "CURRENT_SPEND"),
    (0.9, "CURRENT_SPEND"),
    (1.0, "CURRENT_SPEND"),
    (1.0, "FORECASTED_SPEND"),
}
TOPIC = "emmoni-budget"
# Agentes de serviço do Google: criados ao ligar as APIs do §3, cada um só com o seu papel.
# Os pares vêm de `gcloud projects get-iam-policy emmoni-prod` (2026-10-13), mais os agentes
# de artifactregistry e eventarc, APIs do §3 cujos agentes aparecem nos passos 4–5. Domínio
# fora do mapa, ou papel que não é o do domínio, é FAIL.
SERVICE_AGENT = re.compile(r"serviceAccount:service-(\d+)@([a-z0-9-]+)\.iam\.gserviceaccount\.com")
SERVICE_AGENT_ROLES = {
    "serverless-robot-prod": "roles/run.serviceAgent",
    "gcp-sa-pubsub": "roles/pubsub.serviceAgent",
    "gcf-admin-robot": "roles/cloudfunctions.standardServiceAgent",
    "gcp-sa-cloudbuild": "roles/cloudbuild.serviceAgent",
    "containerregistry": "roles/containerregistry.ServiceAgent",
    "gcp-sa-artifactregistry": "roles/artifactregistry.serviceAgent",
    "gcp-sa-eventarc": "roles/eventarc.serviceAgent",
}
# Contas padrão que o Google cria no projeto (Compute e App Engine); sem uso no emmoni (E-001).
DEFAULT_SA = re.compile(
    r"\d+-compute@developer\.gserviceaccount\.com|.+@appspot\.gserviceaccount\.com"
)
# Estado dos passos (§4): recurso ausente é skip só enquanto o passo que o cria está pendente.
DEPLOY_MD = Path(__file__).resolve().parents[1] / "docs" / "DEPLOY.md"


@dataclass
class Check:
    mode: str
    name: str
    status: str  # ok | FAIL | skip
    evidence: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, mode: str, name: str, passed: bool | None, evidence: str = "") -> None:
        status = "skip" if passed is None else ("ok" if passed else "FAIL")
        self.checks.append(Check(mode, name, status, evidence[:400]))
        print(f"{status:4}  {mode:6} {name}" + (f"  — {evidence[:160]}" if status != "ok" else ""))


# --- HTTP -----------------------------------------------------------------------------------


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: str


def http(
    method: str, url: str, body: object | None = None, headers: dict[str, str] | None = None
) -> Response:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "emmoni-audit")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in {**EXTRA_HEADERS, **(headers or {})}.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return Response(
                r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode()
            )
    except urllib.error.HTTPError as e:
        return Response(e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode())


def audit_public(base: str, rep: Report) -> None:
    m = "public"
    base = base.rstrip("/")

    r = http("GET", f"{base}/exam_board?select=slug&limit=1")
    rep.add(m, "leitura do catálogo responde 200", r.status == 200, f"{r.status} {r.body[:120]}")

    r = http("GET", f"{base}/subject?limit=1", headers={"Origin": SITE_ORIGIN})
    acao = r.headers.get("access-control-allow-origin")
    rep.add(m, f"CORS libera {SITE_ORIGIN}", acao == SITE_ORIGIN, f"allow-origin={acao!r}")

    r = http("GET", f"{base}/subject?limit=1", headers={"Origin": "https://evil.example"})
    acao = r.headers.get("access-control-allow-origin")
    rep.add(m, "CORS não libera outra origem nem *", acao in (None, ""), f"allow-origin={acao!r}")
    rep.add(
        m,
        "CORS sem credenciais",
        r.headers.get("access-control-allow-credentials", "false") != "true",
        f"allow-credentials={r.headers.get('access-control-allow-credentials')!r}",
    )

    before = http("GET", f"{base}/exam_board?select=slug").body
    for method, path, body in (
        ("POST", "/exam_board", {"slug": "audit", "name": "audit"}),
        ("PATCH", "/exam_board?slug=eq.cebraspe", {"name": "audit"}),
        ("DELETE", "/exam_board?slug=eq.cebraspe", None),
        ("PUT", "/exam_board?slug=eq.audit", {"slug": "audit", "name": "audit"}),
    ):
        r = http(method, f"{base}{path}", body)
        rep.add(
            m,
            f"{method} em view é negado",
            r.status in (401, 403, 405),
            f"{r.status} {r.body[:120]}",
        )
    after = http("GET", f"{base}/exam_board?select=slug").body
    rep.add(m, "nada mudou depois das tentativas de escrita", before == after)

    for path in ("/question_docs", "/setting", "/rpc/search_condition", "/rpc/question_docs"):
        r = http("GET", f"{base}{path}")
        rep.add(
            m, f"{path} fora do alcance", r.status in (404, 401, 403), f"{r.status} {r.body[:120]}"
        )

    r = http("GET", f"{base}/question?limit=1", headers={"Accept-Profile": "public"})
    rep.add(
        m,
        "Accept-Profile: public recusado",
        r.status in (406, 400, 404),
        f"{r.status} {r.body[:120]}",
    )
    # Content-Profile só vale para corpo (POST/PATCH); num GET o PostgREST o ignora.
    r = http(
        "POST",
        f"{base}/rpc/search_questions",
        {"page_size": 1},
        headers={"Content-Profile": "public"},
    )
    rep.add(
        m,
        "Content-Profile: public recusado",
        r.status in (406, 400, 404),
        f"{r.status} {r.body[:120]}",
    )

    r = http("GET", f"{base}/question?select=id")
    try:
        n = len(json.loads(r.body))
    except ValueError:
        n = -1
    rep.add(m, "view devolve no máximo 100 linhas", 0 <= n <= 100, f"{r.status} linhas={n}")

    r = http("POST", f"{base}/rpc/search_questions", {"page_size": 1000})
    rep.add(m, "page_size acima de 100 → 400", r.status == 400, f"{r.status} {r.body[:120]}")

    r = http("POST", f"{base}/rpc/search_questions", {"filters": {"bogus": 1}})
    rep.add(
        m,
        "erro 22023 → 400 sem detalhe interno",
        r.status == 400 and "22023" in r.body,
        r.body[:160],
    )

    r = http("GET", f"{base}/subject?limit=1", headers={"Authorization": "Bearer abc.def.ghi"})
    rep.add(m, "JWT forjado não dá acesso", r.status in (401, 500), f"{r.status} {r.body[:120]}")

    r = http("GET", f"{base}/question?select=id&limit=1", headers={"Prefer": "tx=commit"})
    rep.add(m, "Prefer tx=commit inofensivo (só leitura)", r.status in (200, 400), f"{r.status}")

    r = http("GET", f"{base}/question?select=count()")
    rep.add(m, "agregações desligadas", r.status == 400, f"{r.status} {r.body[:120]}")

    r = http("GET", f"{base}/")
    try:
        paths = sorted(json.loads(r.body).get("paths", {}))
    except ValueError:
        paths = []
    internal = [
        p
        for p in paths
        if p.strip("/").removeprefix("rpc/")
        in {"setting", "question_docs", "search_condition", "search_from"}
    ]
    rep.add(
        m,
        "OpenAPI só lista o esquema api",
        r.status == 200 and not internal,
        f"{r.status} {internal}",
    )

    if base.startswith("https://"):
        r = http("GET", "http://" + base.removeprefix("https://") + "/subject?limit=1")
        rep.add(
            m,
            "HTTP sem TLS redireciona ou recusa",
            r.status in (301, 302, 307, 308, 403, 404),
            f"{r.status}",
        )


# --- Imagem ---------------------------------------------------------------------------------


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return p.returncode, (p.stdout + p.stderr).strip()


def audit_image(tag: str, rep: Report) -> None:
    m = "image"
    code, out = run(["docker", "image", "inspect", tag, "--format", "{{json .Config}}"])
    if code != 0:
        rep.add(m, "imagem existe", False, out)
        return
    cfg = json.loads(out)
    rep.add(
        m,
        "usuário não é root",
        cfg.get("User") not in ("", "0", "root"),
        f"User={cfg.get('User')!r}",
    )
    env = cfg.get("Env") or []
    secretish = [
        e.split("=", 1)[0]
        for e in env
        if any(s in e.lower() for s in ("password", "secret", "token", "key="))
    ]
    rep.add(m, "sem segredo no ambiente da imagem", not secretish, f"{secretish}")
    uri = next((e for e in env if e.startswith("PGRST_DB_URI=")), "")
    rep.add(
        m,
        "PostgREST pelo socket, sem senha",
        "@/" in uri and ":" not in uri.split("//", 1)[-1].split("@")[0],
        uri,
    )
    # O 5432 vem do EXPOSE da imagem base (não dá para tirar); o que vale é o que escuta, abaixo.
    exposed = sorted((cfg.get("ExposedPorts") or {}).keys())
    rep.add(m, "porta da API declarada", "8080/tcp" in exposed, f"{exposed}")

    name = "emmoni-audit-image"
    run(["docker", "rm", "-f", name])
    code, out = run(["docker", "run", "-d", "--rm", "--name", name, "--cap-drop=ALL", tag])
    if code != 0:
        rep.add(m, "container sobe", False, out)
        return
    try:
        ready = False
        for _ in range(40):
            code, _ = run(["docker", "exec", name, "pg_isready", "-q", "-h", "/var/run/postgresql"])
            if code == 0:
                ready = True
                break
            run(["sleep", "0.25"])
        rep.add(m, "container sobe", ready)
        if not ready:
            return

        def sql(q: str) -> str:
            _, o = run(
                [
                    "docker",
                    "exec",
                    name,
                    "psql",
                    "-X",
                    "-At",
                    "-h",
                    "/var/run/postgresql",
                    "-U",
                    "emmoni_web",
                    "-d",
                    "emmoni",
                    "-c",
                    q,
                ]
            )
            return o

        rep.add(
            m,
            "Postgres não escuta em TCP",
            sql("show listen_addresses") == "",
            sql("show listen_addresses"),
        )
        rep.add(
            m,
            "emmoni_web em transação só de leitura",
            sql("show default_transaction_read_only") == "on",
        )
        rep.add(
            m,
            "statement_timeout do emmoni_web ≤ 3s",
            sql("show statement_timeout") in ("3s", "2s", "1s"),
            sql("show statement_timeout"),
        )
        roles = sql(
            "select string_agg(rolname || ':' || rolcanlogin || ':' || rolsuper, ',' order by rolname) from pg_roles where rolname like 'emmoni%'"
        )
        rep.add(
            m,
            "só emmoni_web faz login, nenhum emmoni_* é superusuário",
            roles == "emmoni_ingest:false:false,emmoni_owner:false:false,emmoni_web:true:false",
            roles,
        )
        denied = sql("select count(*) from public.question")
        rep.add(m, "emmoni_web não lê public", "permission denied" in denied, denied[:120])
        _, hba = run(
            [
                "docker",
                "exec",
                name,
                "sh",
                "-c",
                'grep -v "^#" "$PGDATA/pg_hba.conf" | grep -v "^$"',
            ]
        )
        rep.add(
            m,
            "pg_hba só socket local",
            all(line.split()[0] == "local" for line in hba.splitlines()),
            hba,
        )
        _, tcp = run(
            [
                "docker",
                "exec",
                name,
                "sh",
                "-c",
                "cat /proc/net/tcp /proc/net/tcp6 2>/dev/null | awk '$4==\"0A\"{print $2}'",
            ]
        )
        ports = sorted({int(a.rsplit(":", 1)[1], 16) for a in tcp.split()})
        rep.add(m, "só a porta 8080 em escuta", ports == [8080], f"{ports}")
    finally:
        run(["docker", "rm", "-f", name])


# --- Google Cloud ---------------------------------------------------------------------------


def gcloud_json(args: list[str]) -> tuple[object | None, str]:
    code, out = run(["gcloud", *args, "--format=json"])
    if code != 0:
        return None, out
    return json.loads(out or "null"), ""


def not_found(err: str) -> bool:
    """O `gcloud` falhou porque o recurso não existe (e não por permissão, rede ou outro erro)."""
    return "Cannot find service" in err or "NOT_FOUND" in err or "status=[404]" in err


def deploy_steps_done(path: Path | None = None) -> set[int] | None:
    """Passos marcados "feito" na tabela do docs/DEPLOY.md §4; None se o arquivo não for lido
    (aí nenhum passo conta como pendente e todo recurso ausente é FAIL)."""
    try:
        text = (path or DEPLOY_MD).read_text()
    except OSError:
        return None
    section = text.split("\n## 4.", 1)[-1].split("\n## ", 1)[0]
    done = set()
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit() and cells[-1].startswith("feito"):
            done.add(int(cells[0]))
    return done


def sa_email(name: str, project: str) -> str:
    return f"{name}@{project}.iam.gserviceaccount.com"


def planned_bindings(project: str) -> set[tuple[str, str]]:
    """Vínculos (papel, membro) do projeto previstos no docs/DEPLOY.md §3 e §4 passo 2. O
    `emmoniIngressCap` vai no serviço (E-009) e o `artifactregistry.writer` no repositório
    `gcf-artifacts` (E-010), não aqui."""
    cap = f"serviceAccount:{sa_email(CAP, project)}"
    build = f"serviceAccount:{sa_email(BUILD_SA, project)}"
    return {
        ("roles/eventarc.eventReceiver", cap),
        ("roles/logging.logWriter", build),
        ("roles/storage.objectViewer", build),
    }


def replaced_bindings(project: str) -> dict[tuple[str, str], str]:
    """Vínculos do projeto que a versão antiga do passo 2 criou e o §3 trocou por vínculos no
    recurso. Presentes, são FAIL numa verificação própria até o dono removê-los (não são
    tolerados: só ficam fora da lista genérica para a evidência dizer o achado)."""
    cap = f"serviceAccount:{sa_email(CAP, project)}"
    build = f"serviceAccount:{sa_email(BUILD_SA, project)}"
    return {
        (f"projects/{project}/roles/{CUSTOM_ROLE}", cap): f"E-009, vai no serviço {SERVICE}",
        ("roles/artifactregistry.writer", build): f"E-010, vai no repositório {FUNCTION_REPO}",
    }


def service_bindings(project: str) -> set[tuple[str, str]]:
    """Vínculos previstos na política do serviço `emmoni-api` (passo 6), fora o `allUsers`
    invoker do passo 7, que tem verificação própria."""
    return {(f"projects/{project}/roles/{CUSTOM_ROLE}", f"serviceAccount:{sa_email(CAP, project)}")}


def repo_bindings(project: str) -> dict[str, tuple[int, set[tuple[str, str]]]]:
    """Repositório -> (passo do §4 que o cria, vínculos previstos na política dele)."""
    build = f"serviceAccount:{sa_email(BUILD_SA, project)}"
    return {
        FUNCTION_REPO: (4, {("roles/artifactregistry.writer", build)}),
        IMAGE_REPO: (5, set()),
    }


def is_service_agent(role: str, member: str, number: str | None) -> bool:
    """Agente de serviço deste projeto com o papel do seu domínio. Sem o número do projeto
    (`projects describe` falhou) não há como saber de quem é o agente: nenhum é aceito."""
    if not number:
        return False
    agent = SERVICE_AGENT.fullmatch(member)
    return bool(
        agent and agent.group(1) == number and SERVICE_AGENT_ROLES.get(agent.group(2)) == role
    )


class Absent:
    """Recurso ausente: skip enquanto o passo do §4 que o cria está pendente e o serviço
    (passo 6) não existe; FAIL depois (o corte vem antes do serviço, DEPLOY.md §1)."""

    def __init__(self, rep: Report, done: set[int] | None, service_exists: bool) -> None:
        self.rep, self.done, self.service_exists = rep, done, service_exists

    def pending(self, step: int) -> bool:
        return self.done is not None and step not in self.done and not self.service_exists

    def add(self, name: str, step: int, evidence: str) -> None:
        if self.pending(step):
            self.rep.add("cloud", name, None, f"passo {step} do DEPLOY.md §4 pendente: {evidence}")
        elif self.done is None:
            self.rep.add("cloud", name, False, f"DEPLOY.md ilegível; ausente: {evidence}")
        else:
            why = "serviço no ar" if self.service_exists else f"passo {step} marcado feito"
            self.rep.add("cloud", name, False, f"{why} e ausente: {evidence}")


def audit_cloud(project: str, rep: Report) -> None:
    """Regra: falha do `gcloud` é FAIL com o erro; recurso que ainda não existe é skip; nunca
    "ok" sem a resposta que o comprova (achado E-005)."""
    m = "cloud"
    number: str | None = None
    proj, err = gcloud_json(["projects", "describe", project])
    if isinstance(proj, dict):
        number = str(proj.get("projectNumber") or "") or None
        labels = proj.get("labels") or {}
        rep.add(m, "label emmoni=prod no projeto", labels.get("emmoni") == "prod", f"{labels}")
    else:
        rep.add(m, "label emmoni=prod no projeto", False, err or f"resposta inesperada: {proj!r}")

    svc, err = gcloud_json(
        ["run", "services", "describe", SERVICE, f"--project={project}", f"--region={REGION}"]
    )
    service_exists = isinstance(svc, dict)
    if svc is None and not_found(err):
        rep.add(m, f"serviço {SERVICE} existe", None, err)
    elif not isinstance(svc, dict):
        rep.add(m, f"serviço {SERVICE} legível", False, err or f"resposta inesperada: {svc!r}")
    else:
        spec = svc.get("spec", {}).get("template", {}).get("spec", {})
        meta = svc.get("spec", {}).get("template", {}).get("metadata", {})
        ann = meta.get("annotations", {})
        sa = spec.get("serviceAccountName", "")
        rep.add(m, "Cloud Run roda com a conta emmoni-api", sa.startswith(f"{RUNTIME_SA}@"), sa)
        image = (spec.get("containers") or [{}])[0].get("image", "")
        rep.add(m, "imagem por digest", "@sha256:" in image, image)
        maxs = ann.get("autoscaling.knative.dev/maxScale")
        rep.add(m, "maxScale = 1", maxs == "1", f"maxScale={maxs}")
        mins = ann.get("autoscaling.knative.dev/minScale", "0")
        rep.add(m, "minScale = 0 (escala a zero)", mins == "0", f"minScale={mins}")
        labels = svc.get("metadata", {}).get("labels", {})
        rep.add(m, "label emmoni=prod", labels.get("emmoni") == "prod", f"{labels}")

    absent = Absent(rep, deploy_steps_done(), service_exists)

    invoker = "invocação pública (allUsers) — só com o sim do dono"
    pol: object = None
    if not service_exists:
        # O get-iam-policy de um serviço inexistente sai 0 com {"etag": ...}: não prova nada.
        rep.add(m, invoker, None, "serviço não existe")
    else:
        pol, err = gcloud_json(
            [
                "run",
                "services",
                "get-iam-policy",
                SERVICE,
                f"--project={project}",
                f"--region={REGION}",
            ]
        )
        if isinstance(pol, dict):
            is_public = any("allUsers" in b.get("members", []) for b in pol.get("bindings", []))
            rep.add(
                m,
                invoker,
                None if is_public else True,
                "allUsers presente" if is_public else "privado",
            )
        else:
            rep.add(m, invoker, False, err or f"resposta inesperada: {pol!r}")
    audit_service_iam(project, pol, service_exists, absent, rep)

    iam, err = gcloud_json(["projects", "get-iam-policy", project])
    if isinstance(iam, dict):
        broad = [
            f"{b['role']}={mem}"
            for b in iam.get("bindings", [])
            if b["role"] in ("roles/owner", "roles/editor")
            for mem in b.get("members", [])
            if mem.startswith("serviceAccount:")
        ]
        rep.add(m, "nenhuma conta de serviço com owner/editor", not broad, f"{broad}")
        public = [
            b["role"]
            for b in iam.get("bindings", [])
            if {"allUsers", "allAuthenticatedUsers"} & set(b.get("members", []))
        ]
        rep.add(m, "nenhum papel do projeto para allUsers", not public, f"{public}")
        audit_project_bindings(project, iam, number, absent, rep)
    else:
        rep.add(m, "política IAM legível", False, err)

    sas, err = gcloud_json(["iam", "service-accounts", "list", f"--project={project}"])
    if not isinstance(sas, list):
        rep.add(m, "contas de serviço legíveis", False, err or f"resposta inesperada: {sas!r}")
    else:
        for sa in sas:
            email = sa["email"]
            keys, err = gcloud_json(
                [
                    "iam",
                    "service-accounts",
                    "keys",
                    "list",
                    f"--iam-account={email}",
                    f"--project={project}",
                    "--managed-by=user",
                ]
            )
            name = f"sem chave de usuário em {email.split('@')[0]}"
            if not isinstance(keys, list):
                rep.add(m, name, False, err or f"resposta inesperada: {keys!r}")
            else:
                rep.add(m, name, not keys, f"{len(keys)} chave(s)")
        audit_service_accounts(project, [sa["email"] for sa in sas], absent, rep)

    audit_custom_roles(project, absent, rep)
    audit_repositories(project, absent, rep)
    audit_budget(project, number, absent, rep)
    audit_topic(project, absent, rep)
    audit_function(project, absent, rep)

    apis, err = gcloud_json(["services", "list", "--enabled", f"--project={project}"])
    if isinstance(apis, list):
        extra = sorted({a["config"]["name"] for a in apis} - ALLOWED_APIS)
        rep.add(m, "nenhuma API além das previstas", not extra, f"{extra}")
    else:
        rep.add(m, "nenhuma API além das previstas", False, err or f"resposta inesperada: {apis!r}")

    info, err = gcloud_json(["billing", "projects", "describe", project])
    if isinstance(info, dict):
        rep.add(
            m,
            "faturamento na conta prevista",
            info.get("billingAccountName", "").endswith("01F985-1C44C6-40CDE9"),
            info.get("billingAccountName", ""),
        )
    else:
        rep.add(m, "faturamento na conta prevista", False, err or f"resposta inesperada: {info!r}")


def audit_project_bindings(
    project: str, iam: dict[str, Any], number: str | None, absent: Absent, rep: Report
) -> None:
    """Vínculos do projeto: os do §3, o owner do dono e os agentes de serviço do Google com
    papéis `*serviceAgent`; qualquer outro é FAIL (E-006)."""
    m = "cloud"
    planned = planned_bindings(project)
    replaced = replaced_bindings(project)
    have = {(b["role"], mem) for b in iam.get("bindings", []) for mem in b.get("members", [])}
    extra = sorted(
        f"{role}={mem}"
        for role, mem in have
        if (role, mem) not in planned
        and (role, mem) not in replaced
        and (role, mem) != ("roles/owner", OWNER)
        and not is_service_agent(role, mem, number)
    )
    rep.add(m, "vínculos do projeto só os do DEPLOY.md §3", not extra, f"{extra}")
    stale = sorted(
        f"{role}={mem} ({why})" for (role, mem), why in replaced.items() if (role, mem) in have
    )
    rep.add(
        m,
        "nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)",
        not stale,
        f"remoção do dono: {stale}",
    )
    owners = sorted(mem for role, mem in have if role == "roles/owner")
    rep.add(m, f"roles/owner só para {OWNER}", owners == [OWNER], f"{owners}")
    missing = sorted(f"{role}={mem}" for role, mem in planned - have)
    name = "vínculos do §3 presentes"
    if missing:
        absent.add(name, 2, f"{missing}")
    else:
        rep.add(m, name, True)


def audit_service_accounts(project: str, emails: list[str], absent: Absent, rep: Report) -> None:
    """Contas de serviço: só as três do §3 (as padrão do Google sinalizadas, E-001); a
    `emmoni-api` só deixa a `emmoni-budget-cap` agir como ela; as outras duas, ninguém."""
    m = "cloud"
    planned = {sa_email(n, project) for n in PLANNED_SAS}
    defaults = sorted(e for e in emails if DEFAULT_SA.fullmatch(e))
    extra = sorted(e for e in emails if e not in planned and e not in defaults)
    rep.add(m, "contas de serviço só as do DEPLOY.md §3", not extra, f"{extra}")
    rep.add(
        m,
        "contas padrão do Google (sem uso; tirar o editor, E-001)",
        None if defaults else True,
        f"{defaults}",
    )
    missing = sorted(planned - set(emails))
    name = "contas de serviço do §3 existem"
    if missing:
        absent.add(name, 2, f"{missing}")
    else:
        rep.add(m, name, True)

    cap = f"serviceAccount:{sa_email(CAP, project)}"
    for sa in sorted(PLANNED_SAS):
        email = sa_email(sa, project)
        if email not in emails:
            continue  # a ausência já está em "contas de serviço do §3 existem"
        expected = {("roles/iam.serviceAccountUser", cap)} if sa == RUNTIME_SA else set()
        pol, err = gcloud_json(
            ["iam", "service-accounts", "get-iam-policy", email, f"--project={project}"]
        )
        name = f"IAM da conta {sa} como no §3"
        if not isinstance(pol, dict):
            rep.add(m, name, False, err or f"resposta inesperada: {pol!r}")
            continue
        have = {(b["role"], mem) for b in pol.get("bindings", []) for mem in b.get("members", [])}
        extra = sorted(f"{r}={mem}" for r, mem in have - expected)
        missing = sorted(f"{r}={mem}" for r, mem in expected - have)
        if extra:
            rep.add(m, name, False, f"fora do §3: {extra}; faltam: {missing}")
        elif missing:
            absent.add(name, 2, f"faltam: {missing}")
        else:
            rep.add(m, name, True)


def audit_custom_roles(project: str, absent: Absent, rep: Report) -> None:
    m = "cloud"
    roles, err = gcloud_json(["iam", "roles", "list", f"--project={project}"])
    if not isinstance(roles, list):
        rep.add(m, "papéis customizados legíveis", False, err or f"resposta inesperada: {roles!r}")
    else:
        names = sorted(r.get("name", "") for r in roles)
        extra = [n for n in names if n != f"projects/{project}/roles/{CUSTOM_ROLE}"]
        rep.add(m, f"papel customizado só o {CUSTOM_ROLE}", not extra, f"{extra}")

    role, err = gcloud_json(["iam", "roles", "describe", CUSTOM_ROLE, f"--project={project}"])
    name = f"papel {CUSTOM_ROLE} só com run.services.get/update"
    if role is None and not_found(err):
        absent.add(name, 2, err)
    elif not isinstance(role, dict):
        rep.add(m, name, False, err or f"resposta inesperada: {role!r}")
    elif role.get("deleted"):
        absent.add(name, 2, "papel apagado")
    else:
        perms = sorted(role.get("includedPermissions", []))
        rep.add(m, name, set(perms) == CUSTOM_ROLE_PERMISSIONS, f"{perms}")


def compare_bindings(
    pol: dict[str, Any],
    expected: set[tuple[str, str]],
    ignore: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[list[str], list[str]]:
    """(fora do previsto, faltando) entre a política lida e os vínculos previstos."""
    have = {(b["role"], mem) for b in pol.get("bindings", []) for mem in b.get("members", [])}
    extra = sorted(f"{r}={mem}" for r, mem in have - expected - ignore)
    missing = sorted(f"{r}={mem}" for r, mem in expected - have)
    return extra, missing


def audit_service_iam(
    project: str, pol: object, service_exists: bool, absent: Absent, rep: Report
) -> None:
    """Política do serviço `emmoni-api`: só o `emmoniIngressCap` da `emmoni-budget-cap` (passo 6,
    E-009) e, depois do passo 7, o `allUsers` invoker (conferido à parte)."""
    m = "cloud"
    name = f"IAM do serviço {SERVICE} como no §3"
    if not service_exists:
        rep.add(m, name, None, "serviço não existe")
        return
    if not isinstance(pol, dict):
        return  # o erro do get-iam-policy já é FAIL na verificação do allUsers
    extra, missing = compare_bindings(
        pol, service_bindings(project), frozenset({("roles/run.invoker", "allUsers")})
    )
    if extra:
        rep.add(m, name, False, f"fora do §3: {extra}; faltam: {missing}")
    elif missing:
        absent.add(name, 6, f"faltam: {missing}")
    else:
        rep.add(m, name, True)


def audit_repositories(project: str, absent: Absent, rep: Report) -> None:
    """Repositórios do Artifact Registry: existência e política (E-010). Lê o `describe` antes
    do `get-iam-policy` para não tomar a política vazia de um repositório inexistente por ok."""
    m = "cloud"
    for repo, (step, expected) in repo_bindings(project).items():
        name = f"IAM do repositório {repo} como no §3"
        where = [f"--location={REGION}", f"--project={project}"]
        info, err = gcloud_json(["artifacts", "repositories", "describe", repo, *where])
        if info is None and not_found(err):
            absent.add(name, step, err)
            continue
        if not isinstance(info, dict):
            rep.add(m, name, False, err or f"resposta inesperada: {info!r}")
            continue
        pol, err = gcloud_json(["artifacts", "repositories", "get-iam-policy", repo, *where])
        if not isinstance(pol, dict):
            rep.add(m, name, False, err or f"resposta inesperada: {pol!r}")
            continue
        extra, missing = compare_bindings(pol, expected)
        if extra:
            rep.add(m, name, False, f"fora do §3: {extra}; faltam: {missing}")
        elif missing:
            absent.add(name, step, f"faltam: {missing}")
        else:
            rep.add(m, name, True)


def audit_budget(project: str, number: str | None, absent: Absent, rep: Report) -> None:
    """Budget `emmoni-monthly` na conta do §1, lido filtrando pelo emmoni (passo 3)."""
    m = "cloud"
    name = f"budget {BUDGET} como no §3"
    budgets, err = gcloud_json(
        [
            "billing",
            "budgets",
            "list",
            f"--billing-account={BILLING_ACCOUNT}",
            "--filter=displayName:emmoni",
        ]
    )
    if not isinstance(budgets, list):
        rep.add(m, name, False, err or f"resposta inesperada: {budgets!r}")
        return
    mine = [b for b in budgets if b.get("displayName") == BUDGET]
    if not mine:
        absent.add(name, 3, f"nenhum budget {BUDGET} na conta {BILLING_ACCOUNT}")
        return
    if len(mine) > 1:
        rep.add(m, name, False, f"{len(mine)} budgets chamados {BUDGET}")
        return
    b = mine[0]
    problems = []
    amount = b.get("amount", {}).get("specifiedAmount", {})
    got = (amount.get("currencyCode"), str(amount.get("units", "")))
    if got != BUDGET_AMOUNT or amount.get("nanos"):
        problems.append(f"valor {got}")
    flt = b.get("budgetFilter", {})
    if number is None or flt.get("projects") != [f"projects/{number}"]:
        problems.append(f"projetos {flt.get('projects')} (número {number})")
    if flt.get("creditTypesTreatment") != "EXCLUDE_ALL_CREDITS":
        problems.append(f"créditos {flt.get('creditTypesTreatment')}")
    rules = {
        (float(r.get("thresholdPercent", 0)), r.get("spendBasis", "CURRENT_SPEND"))
        for r in b.get("thresholdRules", [])
    }
    if rules != BUDGET_THRESHOLDS:
        problems.append(f"alertas {sorted(rules)}")
    topic = b.get("notificationsRule", {}).get("pubsubTopic")
    if topic != f"projects/{project}/topics/{TOPIC}":
        problems.append(f"tópico {topic}")
    rep.add(m, name, not problems, "; ".join(problems))


def audit_topic(project: str, absent: Absent, rep: Report) -> None:
    m = "cloud"
    name = f"tópico {TOPIC} com label emmoni=prod"
    topic, err = gcloud_json(["pubsub", "topics", "describe", TOPIC, f"--project={project}"])
    if topic is None and not_found(err):
        absent.add(name, 3, err)
    elif not isinstance(topic, dict):
        rep.add(m, name, False, err or f"resposta inesperada: {topic!r}")
    else:
        labels = topic.get("labels") or {}
        rep.add(m, name, labels.get("emmoni") == "prod", f"{labels}")


def audit_function(project: str, absent: Absent, rep: Report) -> None:
    """Função de corte (passo 4): uma instância, só interna, conta própria, build pela
    `emmoni-build`, gatilho no tópico do budget."""
    m = "cloud"
    name = f"função {CAP} como no §3"
    fn, err = gcloud_json(
        ["functions", "describe", CAP, "--gen2", f"--region={REGION}", f"--project={project}"]
    )
    if fn is None and not_found(err):
        absent.add(name, 4, err)
        return
    if not isinstance(fn, dict):
        rep.add(m, name, False, err or f"resposta inesperada: {fn!r}")
        return
    cfg = fn.get("serviceConfig", {})
    trig = fn.get("eventTrigger", {})
    build = fn.get("buildConfig", {})
    cap = sa_email(CAP, project)
    want = {
        "state": ("ACTIVE", fn.get("state")),
        "maxInstanceCount": (1, cfg.get("maxInstanceCount")),
        "ingressSettings": ("ALLOW_INTERNAL_ONLY", cfg.get("ingressSettings")),
        "serviceAccountEmail": (cap, cfg.get("serviceAccountEmail")),
        "gatilho": (f"projects/{project}/topics/{TOPIC}", trig.get("pubsubTopic")),
        "conta do gatilho": (cap, trig.get("serviceAccountEmail")),
        "conta do build": (
            f"projects/{project}/serviceAccounts/{sa_email(BUILD_SA, project)}",
            build.get("serviceAccount"),
        ),
        "runtime": ("python312", build.get("runtime")),
        "label emmoni": ("prod", (fn.get("labels") or {}).get("emmoni")),
    }
    problems = [f"{k}={got!r} (esperado {exp!r})" for k, (exp, got) in want.items() if got != exp]
    rep.add(m, name, not problems, "; ".join(problems))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--public", metavar="URL")
    ap.add_argument("--image", metavar="TAG")
    ap.add_argument("--cloud", metavar="PROJETO")
    ap.add_argument("--json", metavar="ARQUIVO")
    ap.add_argument(
        "--header", action="append", default=[], metavar="'Nome: valor'", help="em toda sonda HTTP"
    )
    a = ap.parse_args()
    if not (a.public or a.image or a.cloud):
        ap.error("informe --public, --image ou --cloud")
    for h in a.header:
        k, _, v = h.partition(":")
        EXTRA_HEADERS[k.strip()] = v.strip()
    rep = Report()
    try:
        if a.image:
            audit_image(a.image, rep)
        if a.public:
            audit_public(a.public, rep)
        if a.cloud:
            audit_cloud(a.cloud, rep)
    except (OSError, ValueError) as e:
        print(f"não foi possível auditar: {e}", file=sys.stderr)
        return 2
    if a.json:
        with open(a.json, "w") as f:
            json.dump([asdict(c) for c in rep.checks], f, ensure_ascii=False, indent=2)
    failed = sum(c.status == "FAIL" for c in rep.checks)
    print(f"{len(rep.checks)} verificação(ões), {failed} falha(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
