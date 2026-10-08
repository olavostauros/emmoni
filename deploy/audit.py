#!/usr/bin/env python3
"""Auditoria da API de produção do emmoni (docs/CYBERSECURITY.md, decisão 0022).

Só leitura. Três modos, combináveis:

  --public URL      sondas HTTP na superfície pública (CORS, escrita negada, esquemas
                    internos fora, limite de linhas, tamanho de página, JWT, cabeçalhos)
  --image TAG       confere a imagem num container descartável (usuário, rede do Postgres,
                    pg_hba, papéis, configuração do emmoni_web, segredos no ambiente)
  --cloud PROJETO   confere o projeto no Google Cloud com `gcloud` só de leitura
                    (serviço Cloud Run, IAM, contas de serviço, chaves, budgets, APIs)

Saída: uma linha por verificação (`ok`/`FAIL`/`skip`) e, com --json, o relatório em JSON
para o cerberus triar. Código de saída: 0 tudo ok, 1 alguma falha, 2 não conseguiu rodar.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field

SITE_ORIGIN = "https://olavostauros.github.io"
# Cabeçalhos em toda sonda (--header), ex.: X-Serverless-Authorization com o serviço privado.
EXTRA_HEADERS: dict[str, str] = {}
REGION = "southamerica-east1"
SERVICE = "emmoni-api"
RUNTIME_SA = "emmoni-api"
ALLOWED_APIS = {
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "pubsub.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "eventarc.googleapis.com",
    "billingbudgets.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
}


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


def audit_cloud(project: str, rep: Report) -> None:
    m = "cloud"
    svc, err = gcloud_json(
        ["run", "services", "describe", SERVICE, f"--project={project}", f"--region={REGION}"]
    )
    if not isinstance(svc, dict):
        rep.add(m, f"serviço {SERVICE} existe", None, err)
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

    pol, err = gcloud_json(
        ["run", "services", "get-iam-policy", SERVICE, f"--project={project}", f"--region={REGION}"]
    )
    if isinstance(pol, dict):
        public = any("allUsers" in b.get("members", []) for b in pol.get("bindings", []))
        rep.add(
            m,
            "invocação pública (allUsers) — só com o sim do dono",
            None if public else True,
            "allUsers presente" if public else "privado",
        )

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
    else:
        rep.add(m, "política IAM legível", False, err)

    sas, err = gcloud_json(["iam", "service-accounts", "list", f"--project={project}"])
    if isinstance(sas, list):
        for sa in sas:
            email = sa["email"]
            keys, _ = gcloud_json(
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
            rep.add(
                m,
                f"sem chave de usuário em {email.split('@')[0]}",
                not keys,
                f"{len(keys or [])} chave(s)",
            )

    apis, err = gcloud_json(["services", "list", "--enabled", f"--project={project}"])
    if isinstance(apis, list):
        extra = sorted(
            {a["config"]["name"] for a in apis}
            - ALLOWED_APIS
            - {
                "cloudresourcemanager.googleapis.com",
                "serviceusage.googleapis.com",
                "cloudtrace.googleapis.com",
                "containerregistry.googleapis.com",
                "artifactregistry.googleapis.com",
                "bigquery.googleapis.com",
                "bigquerystorage.googleapis.com",
                "compute.googleapis.com",
                "oslogin.googleapis.com",
            }
        )
        rep.add(m, "nenhuma API além das previstas", not extra, f"{extra}")

    info, _ = gcloud_json(["billing", "projects", "describe", project])
    if isinstance(info, dict):
        rep.add(
            m,
            "faturamento na conta prevista",
            info.get("billingAccountName", "").endswith("01F985-1C44C6-40CDE9"),
            info.get("billingAccountName", ""),
        )


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
