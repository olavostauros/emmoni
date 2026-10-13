"""Modo --cloud do deploy/audit.py (achados E-002, E-004, E-005, E-006, E-009 e E-010). Sem rede nem banco: o `gcloud`
é falso."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
_spec = importlib.util.spec_from_file_location("deploy_audit", ROOT / "deploy" / "audit.py")
assert _spec and _spec.loader
audit = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = audit  # o @dataclass procura o módulo em sys.modules
_spec.loader.exec_module(audit)

PROJECT = "emmoni-prod"
NUMBER = "27333211980"
NOT_FOUND_SVC = "ERROR: (gcloud.run.services.describe) Cannot find service [emmoni-api]"
KEYS_ERR = "ERROR: (gcloud.iam.service-accounts.keys.list) PERMISSION_DENIED: denied"

ROLE_NOT_FOUND = "ERROR: (gcloud.iam.roles.describe) NOT_FOUND: The role ... was not found."
TOPIC_NOT_FOUND = "ERROR: (gcloud.pubsub.topics.describe) NOT_FOUND: Resource not found"
FN_NOT_FOUND = "ERROR: (gcloud.functions.describe) ResponseError: status=[404], code=[]"
REPO_NOT_FOUND = (
    "ERROR: (gcloud.artifacts.repositories.describe) NOT_FOUND: Requested entity was not found."
)

Answer = tuple[int, object]


def fake_gcloud(overrides: dict[str, Answer]) -> Callable[[list[str]], tuple[int, str]]:
    """Responde pelo prefixo mais longo do comando; o padrão é um projeto sem serviço e sem problemas."""
    answers: dict[str, Answer] = {
        "projects describe": (
            0,
            {"projectId": PROJECT, "projectNumber": NUMBER, "labels": {"emmoni": "prod"}},
        ),
        "run services describe": (1, NOT_FOUND_SVC),
        "run services get-iam-policy": (0, {"etag": "ACAB"}),
        "projects get-iam-policy": (0, {"bindings": []}),
        "iam service-accounts list": (
            0,
            [{"email": f"emmoni-api@{PROJECT}.iam.gserviceaccount.com"}],
        ),
        "iam service-accounts keys list": (0, []),
        "iam service-accounts get-iam-policy": (0, {"etag": "ACAB"}),
        "iam roles list": (0, []),
        "iam roles describe": (1, ROLE_NOT_FOUND),
        "billing budgets list": (0, []),
        "pubsub topics describe": (1, TOPIC_NOT_FOUND),
        "functions describe": (1, FN_NOT_FOUND),
        "artifacts repositories describe": (1, REPO_NOT_FOUND),
        "services list": (0, [{"config": {"name": a}} for a in sorted(audit.ALLOWED_APIS)]),
        "billing projects describe": (
            0,
            {"billingAccountName": "billingAccounts/01F985-1C44C6-40CDE9"},
        ),
        **overrides,
    }

    def run(cmd: list[str]) -> tuple[int, str]:
        assert cmd[0] == "gcloud"
        line = " ".join(cmd[1:])
        hits = [prefix for prefix in answers if line.startswith(prefix)]
        if not hits:
            raise AssertionError(f"comando inesperado: {line}")
        code, out = answers[max(hits, key=len)]  # o prefixo mais longo vence
        return code, out if isinstance(out, str) else json.dumps(out)

    return run


def cloud(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, Answer] | None = None,
    done: frozenset[int] | None = frozenset({0, 1}),
) -> dict[str, tuple[str, str]]:
    """Roda o --cloud com o `gcloud` falso; `done` são os passos do §4 marcados feitos."""
    monkeypatch.setattr(audit, "run", fake_gcloud(overrides or {}))
    monkeypatch.setattr(audit, "deploy_steps_done", lambda: None if done is None else set(done))
    rep = audit.Report()
    audit.audit_cloud(PROJECT, rep)
    return {c.name: (c.status, c.evidence) for c in rep.checks}


# --- E-005 ----------------------------------------------------------------------------------


def test_servico_ausente_pula_allusers_em_vez_de_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    got = cloud(monkeypatch)
    assert got["serviço emmoni-api existe"][0] == "skip"
    status, evidence = got["invocação pública (allUsers) — só com o sim do dono"]
    assert (status, evidence) == ("skip", "serviço não existe")


def test_describe_com_erro_que_nao_e_ausencia_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    err = "ERROR: (gcloud.run.services.describe) PERMISSION_DENIED: denied"
    got = cloud(monkeypatch, {"run services describe": (1, err)})
    assert got["serviço emmoni-api legível"] == ("FAIL", err)
    assert got["invocação pública (allUsers) — só com o sim do dono"][0] == "skip"


def test_servico_existente_sem_allusers_e_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = {
        "metadata": {"labels": {"emmoni": "prod"}},
        "spec": {
            "template": {
                "metadata": {"annotations": {"autoscaling.knative.dev/maxScale": "1"}},
                "spec": {
                    "serviceAccountName": f"emmoni-api@{PROJECT}.iam.gserviceaccount.com",
                    "containers": [{"image": "x/emmoni-api@sha256:abc"}],
                },
            }
        },
    }
    got = cloud(monkeypatch, {"run services describe": (0, svc)})
    assert got["invocação pública (allUsers) — só com o sim do dono"] == ("ok", "privado")


def test_iam_do_servico_com_erro_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    err = "ERROR: (gcloud.run.services.get-iam-policy) PERMISSION_DENIED: denied"
    got = cloud(
        monkeypatch,
        {
            "run services describe": (0, {"spec": {}}),
            "run services get-iam-policy": (1, err),
        },
    )
    assert got["invocação pública (allUsers) — só com o sim do dono"] == ("FAIL", err)


def test_listagem_de_chaves_com_erro_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    got = cloud(monkeypatch, {"iam service-accounts keys list": (1, KEYS_ERR)})
    assert got["sem chave de usuário em emmoni-api"] == ("FAIL", KEYS_ERR)


def test_chave_de_usuario_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    got = cloud(monkeypatch, {"iam service-accounts keys list": (0, [{"name": "k"}])})
    assert got["sem chave de usuário em emmoni-api"] == ("FAIL", "1 chave(s)")


def test_sem_chave_e_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    assert cloud(monkeypatch)["sem chave de usuário em emmoni-api"][0] == "ok"


@pytest.mark.parametrize(
    ("prefix", "name"),
    [
        ("iam service-accounts list", "contas de serviço legíveis"),
        ("services list", "nenhuma API além das previstas"),
        ("billing projects describe", "faturamento na conta prevista"),
        ("projects get-iam-policy", "política IAM legível"),
    ],
)
def test_gcloud_com_erro_vira_falha_e_nao_some(
    monkeypatch: pytest.MonkeyPatch, prefix: str, name: str
) -> None:
    got = cloud(monkeypatch, {prefix: (1, "ERROR: denied")})
    assert got[name] == ("FAIL", "ERROR: denied")


# --- E-004 ----------------------------------------------------------------------------------


def _section3_apis() -> set[str]:
    text = (ROOT / "docs" / "DEPLOY.md").read_text()
    section = text.split("## 3.", 1)[1].split("\n## ", 1)[0]
    apis: set[str] = set()
    for label in ("APIs", "Dependências de API"):
        row = next(line for line in section.splitlines() if line.startswith(f"| {label} |"))
        names = row.split("|")[2]
        apis |= {f"{n}.googleapis.com" for n in re.findall(r"`([a-z0-9-]+)`", names)}
    return apis


def test_lista_de_apis_e_a_do_deploy_md_secao_3() -> None:
    assert _section3_apis() == audit.ALLOWED_APIS
    assert len(audit.PLANNED_APIS) == 8


@pytest.mark.parametrize(
    "api",
    [
        "compute.googleapis.com",
        "oslogin.googleapis.com",
        "bigquery.googleapis.com",
        "bigquerystorage.googleapis.com",
        "cloudtrace.googleapis.com",
        "dataform.googleapis.com",
        "source.googleapis.com",
        "monitoring.googleapis.com",
        "storage.googleapis.com",
    ],
)
def test_api_fora_do_secao_3_falha(monkeypatch: pytest.MonkeyPatch, api: str) -> None:
    enabled = [{"config": {"name": a}} for a in sorted(audit.ALLOWED_APIS | {api})]
    status, evidence = cloud(monkeypatch, {"services list": (0, enabled)})[
        "nenhuma API além das previstas"
    ]
    assert status == "FAIL"
    assert api in evidence


def test_so_apis_do_secao_3_e_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    assert cloud(monkeypatch)["nenhuma API além das previstas"][0] == "ok"


def test_serviceusage_documentada_e_source_nao(monkeypatch: pytest.MonkeyPatch) -> None:
    """E-002: com as 16 APIs do relatório de 2026-10-13, só o `source` (remoção do dono) falha."""
    assert "serviceusage.googleapis.com" in _section3_apis()
    enabled = sorted(audit.ALLOWED_APIS | {"source.googleapis.com"})
    got = cloud(monkeypatch, {"services list": (0, [{"config": {"name": a}} for a in enabled])})
    assert got["nenhuma API além das previstas"] == ("FAIL", "['source.googleapis.com']")


# --- E-006 ----------------------------------------------------------------------------------

ALL_STEPS = frozenset(range(0, 8))
CAP = f"serviceAccount:emmoni-budget-cap@{PROJECT}.iam.gserviceaccount.com"
BUILD = f"serviceAccount:emmoni-build@{PROJECT}.iam.gserviceaccount.com"
OWNER = "user:olavostauros@gmail.com"


def sa(name: str) -> dict[str, str]:
    return {"email": f"{name}@{PROJECT}.iam.gserviceaccount.com"}


def bindings(*pairs: tuple[str, str]) -> dict[str, object]:
    return {"bindings": [{"role": r, "members": [mem]} for r, mem in pairs]}


INGRESS_CAP = f"projects/{PROJECT}/roles/emmoniIngressCap"
# Vínculos do projeto que o passo 2 antigo criou e o §3 trocou por vínculos no recurso.
REPLACED = (
    (INGRESS_CAP, CAP),  # E-009: no serviço emmoni-api
    ("roles/artifactregistry.writer", BUILD),  # E-010: no repositório gcf-artifacts
)
PLANNED = (
    ("roles/eventarc.eventReceiver", CAP),
    ("roles/logging.logWriter", BUILD),
    ("roles/storage.objectViewer", BUILD),
    ("roles/owner", OWNER),
    (
        "roles/run.serviceAgent",
        f"serviceAccount:service-{NUMBER}@serverless-robot-prod.iam.gserviceaccount.com",
    ),
    (
        "roles/pubsub.serviceAgent",
        f"serviceAccount:service-{NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com",
    ),
    (
        "roles/cloudfunctions.standardServiceAgent",
        f"serviceAccount:service-{NUMBER}@gcf-admin-robot.iam.gserviceaccount.com",
    ),
)

BUDGET = {
    "displayName": "emmoni-monthly",
    "amount": {"specifiedAmount": {"currencyCode": "BRL", "units": "40"}},
    "budgetFilter": {
        "projects": [f"projects/{NUMBER}"],
        "creditTypesTreatment": "EXCLUDE_ALL_CREDITS",
    },
    "thresholdRules": [
        {"thresholdPercent": 0.5},
        {"thresholdPercent": 0.9},
        {"thresholdPercent": 1.0},
        {"thresholdPercent": 1.0, "spendBasis": "FORECASTED_SPEND"},
    ],
    "notificationsRule": {"pubsubTopic": f"projects/{PROJECT}/topics/emmoni-budget"},
}

FUNCTION = {
    "state": "ACTIVE",
    "labels": {"emmoni": "prod"},
    "serviceConfig": {
        "maxInstanceCount": 1,
        "ingressSettings": "ALLOW_INTERNAL_ONLY",
        "serviceAccountEmail": f"emmoni-budget-cap@{PROJECT}.iam.gserviceaccount.com",
    },
    "eventTrigger": {
        "pubsubTopic": f"projects/{PROJECT}/topics/emmoni-budget",
        "serviceAccountEmail": f"emmoni-budget-cap@{PROJECT}.iam.gserviceaccount.com",
    },
    "buildConfig": {
        "runtime": "python312",
        "serviceAccount": (
            f"projects/{PROJECT}/serviceAccounts/emmoni-build@{PROJECT}.iam.gserviceaccount.com"
        ),
    },
}


def complete(**overrides: Answer) -> dict[str, Answer]:
    """O projeto depois dos passos 2–4, tudo como no §3."""
    return {
        "projects get-iam-policy": (0, bindings(*PLANNED)),
        "iam service-accounts list": (
            0,
            [sa("emmoni-api"), sa("emmoni-budget-cap"), sa("emmoni-build")],
        ),
        "iam service-accounts get-iam-policy emmoni-api@": (
            0,
            bindings(("roles/iam.serviceAccountUser", CAP)),
        ),
        "iam service-accounts get-iam-policy": (0, {"etag": "ACAB"}),
        "iam roles list": (0, [{"name": f"projects/{PROJECT}/roles/emmoniIngressCap"}]),
        "iam roles describe": (
            0,
            {"includedPermissions": ["run.services.get", "run.services.update"]},
        ),
        "billing budgets list": (0, [BUDGET]),
        "pubsub topics describe": (0, {"labels": {"emmoni": "prod"}}),
        "functions describe": (0, FUNCTION),
        "artifacts repositories describe": (0, {"format": "DOCKER"}),
        "artifacts repositories get-iam-policy gcf-artifacts": (
            0,
            bindings(("roles/artifactregistry.writer", BUILD)),
        ),
        "artifacts repositories get-iam-policy emmoni": (0, {"etag": "ACAB"}),
        **overrides,
    }


E006 = [
    "label emmoni=prod no projeto",
    "vínculos do projeto só os do DEPLOY.md §3",
    "roles/owner só para user:olavostauros@gmail.com",
    "vínculos do §3 presentes",
    "contas de serviço só as do DEPLOY.md §3",
    "contas padrão do Google (sem uso; tirar o editor, E-001)",
    "contas de serviço do §3 existem",
    "IAM da conta emmoni-api como no §3",
    "IAM da conta emmoni-budget-cap como no §3",
    "IAM da conta emmoni-build como no §3",
    "papel customizado só o emmoniIngressCap",
    "papel emmoniIngressCap só com run.services.get/update",
    "budget emmoni-monthly como no §3",
    "tópico emmoni-budget com label emmoni=prod",
    "função emmoni-budget-cap como no §3",
]
E009_E010 = [
    "nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)",
    "IAM do repositório gcf-artifacts como no §3",
    "IAM do repositório emmoni como no §3",
]


def test_passos_feitos_lidos_do_deploy_md() -> None:
    done = audit.deploy_steps_done(ROOT / "docs" / "DEPLOY.md")
    assert done is not None and {0, 1} <= done


def test_passos_feitos_de_tabela_sintetica(tmp_path: Path) -> None:
    md = tmp_path / "DEPLOY.md"
    md.write_text(
        "## 3. x\n| 3 | nada | feito |\n## 4. Passos\n| # | P | F | Estado |\n|---|---|---|---|\n"
        "| 1 | a | b | feito em 2026-10-13 |\n| 2 | a | b | pendente |\n"
        "| 3 | a | b | feito |\n## 5. y\n| 4 | a | b | feito |\n"
    )
    assert audit.deploy_steps_done(md) == {1, 3}
    assert audit.deploy_steps_done(tmp_path / "nao-existe.md") is None


def test_projeto_completo_e_tudo_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    got = cloud(monkeypatch, complete(), done=ALL_STEPS)
    names = E006 + E009_E010
    assert {n: got[n][0] for n in names} == {n: "ok" for n in names}
    assert got["IAM do serviço emmoni-api como no §3"] == ("skip", "serviço não existe")


def test_estado_de_hoje_acusa_e003_e_pula_o_que_e_pendente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Verificação do E-006: no estado do relatório de 2026-10-13 (passo 1 feito)."""
    compute = f"serviceAccount:{NUMBER}-compute@developer.gserviceaccount.com"
    appspot = f"serviceAccount:{PROJECT}@appspot.gserviceaccount.com"
    legacy = f"serviceAccount:{NUMBER}@cloudbuild.gserviceaccount.com"
    iam = bindings(
        ("roles/cloudbuild.builds.builder", legacy),
        ("roles/editor", compute),
        ("roles/editor", appspot),
        ("roles/owner", OWNER),
        (
            "roles/cloudbuild.serviceAgent",
            f"serviceAccount:service-{NUMBER}@gcp-sa-cloudbuild.iam.gserviceaccount.com",
        ),
        (
            "roles/containerregistry.ServiceAgent",
            f"serviceAccount:service-{NUMBER}@containerregistry.iam.gserviceaccount.com",
        ),
    )
    sas = [{"email": compute.split(":")[1]}, {"email": appspot.split(":")[1]}]
    got = cloud(
        monkeypatch,
        {"projects get-iam-policy": (0, iam), "iam service-accounts list": (0, sas)},
    )
    status, evidence = got["vínculos do projeto só os do DEPLOY.md §3"]
    assert status == "FAIL"
    assert f"roles/cloudbuild.builds.builder={legacy}" in evidence
    assert "ServiceAgent" not in evidence and "serviceAgent" not in evidence
    assert got["roles/owner só para user:olavostauros@gmail.com"][0] == "ok"
    assert got["contas de serviço só as do DEPLOY.md §3"][0] == "ok"
    assert got["contas padrão do Google (sem uso; tirar o editor, E-001)"][0] == "skip"
    for name, step in [
        ("vínculos do §3 presentes", 2),
        ("contas de serviço do §3 existem", 2),
        ("papel emmoniIngressCap só com run.services.get/update", 2),
        ("budget emmoni-monthly como no §3", 3),
        ("tópico emmoni-budget com label emmoni=prod", 3),
        ("função emmoni-budget-cap como no §3", 4),
        ("IAM do repositório gcf-artifacts como no §3", 4),
        ("IAM do repositório emmoni como no §3", 5),
    ]:
        status, evidence = got[name]
        assert status == "skip", name
        assert evidence.startswith(f"passo {step} do DEPLOY.md §4 pendente"), name
    assert got["label emmoni=prod no projeto"][0] == "ok"


@pytest.mark.parametrize(
    ("name", "step"),
    [
        ("vínculos do §3 presentes", 2),
        ("contas de serviço do §3 existem", 2),
        ("papel emmoniIngressCap só com run.services.get/update", 2),
        ("budget emmoni-monthly como no §3", 3),
        ("tópico emmoni-budget com label emmoni=prod", 3),
        ("função emmoni-budget-cap como no §3", 4),
        ("IAM do repositório gcf-artifacts como no §3", 4),
        ("IAM do repositório emmoni como no §3", 5),
    ],
)
def test_ausente_com_passo_feito_falha(
    monkeypatch: pytest.MonkeyPatch, name: str, step: int
) -> None:
    got = cloud(monkeypatch, done=ALL_STEPS)
    status, evidence = got[name]
    assert status == "FAIL"
    assert evidence.startswith(f"passo {step} marcado feito e ausente")


def test_corte_ausente_com_servico_no_ar_falha_mesmo_com_passo_pendente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DEPLOY.md §1: budget, tópico e função antes do serviço."""
    got = cloud(monkeypatch, {"run services describe": (0, {"spec": {}})})
    for name in (
        "budget emmoni-monthly como no §3",
        "tópico emmoni-budget com label emmoni=prod",
        "função emmoni-budget-cap como no §3",
    ):
        status, evidence = got[name]
        assert (status, evidence.split(" e ausente")[0]) == ("FAIL", "serviço no ar"), name


def test_deploy_md_ilegivel_nao_pula(monkeypatch: pytest.MonkeyPatch) -> None:
    got = cloud(monkeypatch, done=None)
    status, evidence = got["budget emmoni-monthly como no §3"]
    assert status == "FAIL" and evidence.startswith("DEPLOY.md ilegível")


@pytest.mark.parametrize(
    ("role", "member"),
    [
        ("roles/viewer", f"serviceAccount:emmoni-api@{PROJECT}.iam.gserviceaccount.com"),
        ("roles/run.admin", CAP),
        ("roles/iam.serviceAccountTokenCreator", BUILD),
        ("roles/editor", "user:outra@example.com"),
        ("roles/owner", "user:outra@example.com"),
        ("roles/editor", f"serviceAccount:service-{NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"),
        (
            "roles/run.serviceAgent",
            "serviceAccount:service-1@serverless-robot-prod.iam.gserviceaccount.com",
        ),
        ("roles/pubsub.serviceAgent", "serviceAccount:service-1@evil.iam.gserviceaccount.com"),
        (
            "roles/compute.serviceAgent",
            f"serviceAccount:service-{NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com",
        ),
        (
            "roles/run.serviceAgent",
            f"serviceAccount:service-{NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com",
        ),
        (
            "roles/compute.serviceAgent",
            f"serviceAccount:service-{NUMBER}@compute-system.iam.gserviceaccount.com",
        ),
    ],
)
def test_vinculo_fora_do_secao_3_falha(
    monkeypatch: pytest.MonkeyPatch, role: str, member: str
) -> None:
    iam = bindings(*PLANNED, (role, member))
    got = cloud(monkeypatch, complete(**{"projects get-iam-policy": (0, iam)}), done=ALL_STEPS)
    status, evidence = got["vínculos do projeto só os do DEPLOY.md §3"]
    assert status == "FAIL" and f"{role}={member}" in evidence


AGENT_PUBSUB = f"serviceAccount:service-{NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"


@pytest.mark.parametrize(
    ("role", "member", "number", "expected"),
    [
        ("roles/pubsub.serviceAgent", AGENT_PUBSUB, NUMBER, True),
        ("roles/compute.serviceAgent", AGENT_PUBSUB, NUMBER, False),
        ("roles/run.serviceAgent", AGENT_PUBSUB, NUMBER, False),
        ("roles/pubsub.serviceAgent", AGENT_PUBSUB, "1", False),
        ("roles/pubsub.serviceAgent", AGENT_PUBSUB, None, False),
        ("roles/pubsub.serviceAgent", AGENT_PUBSUB, "", False),
        (
            "roles/foo.serviceAgent",
            f"serviceAccount:service-{NUMBER}@gcp-sa-foo.iam.gserviceaccount.com",
            NUMBER,
            False,
        ),
    ],
)
def test_agente_de_servico_so_com_o_papel_do_dominio(
    role: str, member: str, number: str | None, expected: bool
) -> None:
    assert audit.is_service_agent(role, member, number) is expected


def test_mapa_de_agentes_cobre_os_vinculos_reais() -> None:
    for role, member in PLANNED:
        if member.startswith("serviceAccount:service-"):
            assert audit.is_service_agent(role, member, NUMBER), member


def test_sem_numero_do_projeto_nenhum_agente_passa(monkeypatch: pytest.MonkeyPatch) -> None:
    describe_err = "ERROR: (gcloud.projects.describe) PERMISSION_DENIED: denied"
    got = cloud(
        monkeypatch,
        complete(
            **{
                "projects describe": (1, describe_err),
                "projects get-iam-policy": (0, bindings(*PLANNED)),
            }
        ),
        done=ALL_STEPS,
    )
    status, evidence = got["vínculos do projeto só os do DEPLOY.md §3"]
    assert status == "FAIL"
    assert "gcp-sa-pubsub" in evidence and "serverless-robot-prod" in evidence
    assert got["label emmoni=prod no projeto"][0] == "FAIL"


def test_segundo_owner_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    iam = bindings(*PLANNED, ("roles/owner", "user:outra@example.com"))
    got = cloud(monkeypatch, complete(**{"projects get-iam-policy": (0, iam)}), done=ALL_STEPS)
    assert got["roles/owner só para user:olavostauros@gmail.com"][0] == "FAIL"


def test_conta_de_servico_inesperada_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    sas = [sa("emmoni-api"), sa("emmoni-budget-cap"), sa("emmoni-build"), sa("intrusa")]
    got = cloud(monkeypatch, complete(**{"iam service-accounts list": (0, sas)}), done=ALL_STEPS)
    status, evidence = got["contas de serviço só as do DEPLOY.md §3"]
    assert status == "FAIL" and "intrusa@" in evidence


def test_conta_padrao_e_sinalizada_nao_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    sas = [sa("emmoni-api"), sa("emmoni-budget-cap"), sa("emmoni-build")]
    sas.append({"email": f"{NUMBER}-compute@developer.gserviceaccount.com"})
    got = cloud(monkeypatch, complete(**{"iam service-accounts list": (0, sas)}), done=ALL_STEPS)
    assert got["contas padrão do Google (sem uso; tirar o editor, E-001)"][0] == "skip"
    assert got["contas de serviço só as do DEPLOY.md §3"][0] == "ok"


def test_iam_da_conta_runtime_com_vinculo_extra_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    pol = bindings(("roles/iam.serviceAccountUser", CAP), ("roles/iam.serviceAccountUser", BUILD))
    got = cloud(
        monkeypatch,
        complete(**{"iam service-accounts get-iam-policy emmoni-api@": (0, pol)}),
        done=ALL_STEPS,
    )
    status, evidence = got["IAM da conta emmoni-api como no §3"]
    assert status == "FAIL" and BUILD in evidence


def test_iam_de_conta_com_erro_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    got = cloud(
        monkeypatch,
        complete(**{"iam service-accounts get-iam-policy": (1, "ERROR: denied")}),
        done=ALL_STEPS,
    )
    assert got["IAM da conta emmoni-build como no §3"] == ("FAIL", "ERROR: denied")


def test_papel_customizado_com_permissao_a_mais_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    role = {
        "includedPermissions": [
            "run.services.get",
            "run.services.update",
            "run.services.setIamPolicy",
        ]
    }
    got = cloud(monkeypatch, complete(**{"iam roles describe": (0, role)}), done=ALL_STEPS)
    assert got["papel emmoniIngressCap só com run.services.get/update"][0] == "FAIL"


def test_outro_papel_customizado_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    roles = [
        {"name": f"projects/{PROJECT}/roles/emmoniIngressCap"},
        {"name": f"projects/{PROJECT}/roles/outro"},
    ]
    got = cloud(monkeypatch, complete(**{"iam roles list": (0, roles)}), done=ALL_STEPS)
    assert got["papel customizado só o emmoniIngressCap"][0] == "FAIL"


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("amount", {"specifiedAmount": {"currencyCode": "BRL", "units": "400"}}, "valor"),
        (
            "budgetFilter",
            {"projects": ["projects/805713488595"], "creditTypesTreatment": "EXCLUDE_ALL_CREDITS"},
            "projetos",
        ),
        ("budgetFilter", {"projects": [f"projects/{NUMBER}"]}, "créditos"),
        ("thresholdRules", [{"thresholdPercent": 1.0}], "alertas"),
        ("notificationsRule", {}, "tópico"),
    ],
)
def test_budget_diferente_do_secao_3_falha(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object, fragment: str
) -> None:
    budget = {**BUDGET, field: value}
    got = cloud(monkeypatch, complete(**{"billing budgets list": (0, [budget])}), done=ALL_STEPS)
    status, evidence = got["budget emmoni-monthly como no §3"]
    assert status == "FAIL" and fragment in evidence


def test_budget_lido_so_na_conta_do_emmoni(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    fake = fake_gcloud(complete())

    def spy(cmd: list[str]) -> tuple[int, str]:
        calls.append(" ".join(cmd[1:]))
        return fake(cmd)

    monkeypatch.setattr(audit, "run", spy)
    monkeypatch.setattr(audit, "deploy_steps_done", lambda: set(ALL_STEPS))
    audit.audit_cloud(PROJECT, audit.Report())
    budget = [c for c in calls if c.startswith("billing budgets")]
    assert budget == [
        "billing budgets list --billing-account=01F985-1C44C6-40CDE9 "
        "--filter=displayName:emmoni --format=json"
    ]
    others = [c for c in calls if not c.startswith(("billing budgets", "billing projects"))]
    assert all(
        f"--project={PROJECT}" in c
        or c.startswith(f"projects describe {PROJECT}")
        or c.startswith(f"projects get-iam-policy {PROJECT}")
        for c in others
    )
    writes = ("create", "update", "delete", "add-", "remove-", "set-", "enable", "disable")
    assert not [c for c in calls if any(f" {w}" in f" {c}" for w in writes)]


@pytest.mark.parametrize(
    ("prefix", "name"),
    [
        ("projects describe", "label emmoni=prod no projeto"),
        ("iam roles list", "papéis customizados legíveis"),
        ("iam roles describe", "papel emmoniIngressCap só com run.services.get/update"),
        ("billing budgets list", "budget emmoni-monthly como no §3"),
        ("pubsub topics describe", "tópico emmoni-budget com label emmoni=prod"),
        ("functions describe", "função emmoni-budget-cap como no §3"),
        ("artifacts repositories describe", "IAM do repositório gcf-artifacts como no §3"),
    ],
)
def test_erro_do_gcloud_nas_verificacoes_novas_falha(
    monkeypatch: pytest.MonkeyPatch, prefix: str, name: str
) -> None:
    got = cloud(monkeypatch, {prefix: (1, "ERROR: PERMISSION_DENIED")})
    assert got[name] == ("FAIL", "ERROR: PERMISSION_DENIED")


def test_label_do_projeto_ausente_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    proj = {"projectId": PROJECT, "projectNumber": NUMBER, "labels": {}}
    assert (
        cloud(monkeypatch, {"projects describe": (0, proj)})["label emmoni=prod no projeto"][0]
        == "FAIL"
    )


def test_topico_sem_label_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    got = cloud(monkeypatch, complete(**{"pubsub topics describe": (0, {})}), done=ALL_STEPS)
    assert got["tópico emmoni-budget com label emmoni=prod"][0] == "FAIL"


@pytest.mark.parametrize(
    ("section", "key", "value", "fragment"),
    [
        ("serviceConfig", "maxInstanceCount", 2, "maxInstanceCount"),
        ("serviceConfig", "ingressSettings", "ALLOW_ALL", "ingressSettings"),
        (
            "serviceConfig",
            "serviceAccountEmail",
            f"{NUMBER}-compute@developer.gserviceaccount.com",
            "serviceAccountEmail",
        ),
        ("eventTrigger", "pubsubTopic", f"projects/{PROJECT}/topics/outro", "gatilho"),
        ("buildConfig", "serviceAccount", None, "conta do build"),
    ],
)
def test_funcao_diferente_do_secao_3_falha(
    monkeypatch: pytest.MonkeyPatch, section: str, key: str, value: object, fragment: str
) -> None:
    fn = json.loads(json.dumps(FUNCTION))
    fn[section][key] = value
    got = cloud(monkeypatch, complete(**{"functions describe": (0, fn)}), done=ALL_STEPS)
    status, evidence = got["função emmoni-budget-cap como no §3"]
    assert status == "FAIL" and fragment in evidence


# --- E-009 e E-010 --------------------------------------------------------------------------

SVC = {
    "metadata": {"labels": {"emmoni": "prod"}},
    "spec": {
        "template": {
            "metadata": {"annotations": {"autoscaling.knative.dev/maxScale": "1"}},
            "spec": {
                "serviceAccountName": f"emmoni-api@{PROJECT}.iam.gserviceaccount.com",
                "containers": [{"image": "x/emmoni-api@sha256:abc"}],
            },
        }
    },
}


def test_estado_depois_do_passo_2_acusa_e009_e_e010(monkeypatch: pytest.MonkeyPatch) -> None:
    """A política do relatório de 2026-10-13 (segundo): os dois vínculos de projeto do passo 2
    antigo falham na verificação própria, com o achado na evidência, e não na genérica."""
    iam = bindings(*PLANNED, *REPLACED)
    got = cloud(monkeypatch, complete(**{"projects get-iam-policy": (0, iam)}), done=ALL_STEPS)
    assert got["vínculos do projeto só os do DEPLOY.md §3"][0] == "ok"
    assert got["vínculos do §3 presentes"][0] == "ok"
    status, evidence = got[
        "nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)"
    ]
    assert status == "FAIL" and evidence.startswith("remoção do dono")
    assert f"{INGRESS_CAP}={CAP} (E-009" in evidence
    assert f"roles/artifactregistry.writer={BUILD} (E-010" in evidence


@pytest.mark.parametrize("pair", REPLACED)
def test_cada_vinculo_trocado_falha_sozinho(
    monkeypatch: pytest.MonkeyPatch, pair: tuple[str, str]
) -> None:
    iam = bindings(*PLANNED, pair)
    got = cloud(monkeypatch, complete(**{"projects get-iam-policy": (0, iam)}), done=ALL_STEPS)
    status, evidence = got[
        "nenhum vínculo de projeto trocado por vínculo no recurso (E-009, E-010)"
    ]
    assert status == "FAIL" and f"{pair[0]}={pair[1]}" in evidence


def test_vinculos_do_projeto_nao_esperam_mais_os_trocados() -> None:
    planned = audit.planned_bindings(PROJECT)
    assert not set(REPLACED) & planned
    assert set(audit.replaced_bindings(PROJECT)) == set(REPLACED)


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (bindings((INGRESS_CAP, CAP)), "ok"),
        (bindings((INGRESS_CAP, CAP), ("roles/run.invoker", "allUsers")), "ok"),
        ({"etag": "ACAB"}, "FAIL"),
        (bindings((INGRESS_CAP, CAP), ("roles/run.admin", CAP)), "FAIL"),
        (bindings((INGRESS_CAP, CAP), ("roles/run.invoker", BUILD)), "FAIL"),
        (bindings((INGRESS_CAP, BUILD)), "FAIL"),
    ],
)
def test_iam_do_servico(
    monkeypatch: pytest.MonkeyPatch, policy: dict[str, object], expected: str
) -> None:
    """E-009: com o serviço no ar, o `emmoniIngressCap` da `emmoni-budget-cap` está no serviço,
    e nada além dele (o `allUsers` invoker tem verificação própria)."""
    got = cloud(
        monkeypatch,
        complete(
            **{
                "run services describe": (0, SVC),
                "run services get-iam-policy": (0, policy),
            }
        ),
        done=frozenset({0, 1, 2, 3, 4, 5}),
    )
    status, evidence = got["IAM do serviço emmoni-api como no §3"]
    assert status == expected, evidence
    if policy == {"etag": "ACAB"}:
        assert evidence.startswith("serviço no ar e ausente")


@pytest.mark.parametrize(
    ("repo", "policy"),
    [
        (
            "gcf-artifacts",
            bindings(("roles/artifactregistry.writer", BUILD), ("roles/viewer", CAP)),
        ),
        ("gcf-artifacts", bindings(("roles/artifactregistry.admin", BUILD))),
        ("emmoni", bindings(("roles/artifactregistry.writer", BUILD))),
        ("emmoni", bindings(("roles/artifactregistry.reader", "allUsers"))),
    ],
)
def test_repositorio_com_vinculo_fora_do_secao_3_falha(
    monkeypatch: pytest.MonkeyPatch, repo: str, policy: dict[str, object]
) -> None:
    """E-010: a `emmoni-build` escreve só no `gcf-artifacts`; o `emmoni` não dá papel a ninguém."""
    key = f"artifacts repositories get-iam-policy {repo}"
    got = cloud(monkeypatch, complete(**{key: (0, policy)}), done=ALL_STEPS)
    status, evidence = got[f"IAM do repositório {repo} como no §3"]
    assert status == "FAIL" and evidence.startswith("fora do §3")


def test_gcf_artifacts_sem_o_vinculo_da_build(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "artifacts repositories get-iam-policy gcf-artifacts"
    over = {key: (0, {"etag": "ACAB"})}
    status, evidence = cloud(monkeypatch, complete(**over), done=ALL_STEPS)[
        "IAM do repositório gcf-artifacts como no §3"
    ]
    assert status == "FAIL" and evidence.startswith("passo 4 marcado feito e ausente")
    status, _ = cloud(monkeypatch, complete(**over), done=frozenset({0, 1, 2, 3}))[
        "IAM do repositório gcf-artifacts como no §3"
    ]
    assert status == "skip"


def test_politica_do_repositorio_com_erro_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "artifacts repositories get-iam-policy emmoni"
    got = cloud(monkeypatch, complete(**{key: (1, "ERROR: denied")}), done=ALL_STEPS)
    assert got["IAM do repositório emmoni como no §3"] == ("FAIL", "ERROR: denied")


def _deploy_block(step: int) -> str:
    """O primeiro bloco `sh` do passo no DEPLOY.md §4 (o comando do passo, sem as notas)."""
    text = (ROOT / "docs" / "DEPLOY.md").read_text()
    section = text.split(f"\n### {step}. ", 1)[1].split("\n### ", 1)[0]
    block = re.search(r"```sh\n(.*?)```", section, re.S)
    assert block, step
    return block.group(1)


def test_deploy_md_vincula_no_recurso_e_nao_no_projeto() -> None:
    """E-009 e E-010 no documento: o passo 2 não vincula mais no projeto o `emmoniIngressCap`
    nem o `artifactregistry.writer`; o passo 4 vincula o writer no `gcf-artifacts` e o passo 6,
    o papel no serviço."""
    step2 = re.sub(r"#[^\n]*", "", _deploy_block(2))  # sem os comentários
    assert "roles/emmoniIngressCap" not in step2
    assert "artifactregistry.writer" not in step2
    assert "iam roles create emmoniIngressCap" in step2
    step4 = re.sub(r"\s*\\\n\s*", " ", _deploy_block(4))
    assert re.search(
        r"artifacts repositories add-iam-policy-binding gcf-artifacts --project=\$P "
        r"--location=\$R --role=roles/artifactregistry.writer "
        r"--member=serviceAccount:emmoni-build@",
        step4,
    )
    step6 = re.sub(r"\s*\\\n\s*", " ", _deploy_block(6))
    assert re.search(
        r"run services add-iam-policy-binding emmoni-api --project=\$P --region=\$R "
        r"--role=projects/\$P/roles/emmoniIngressCap "
        r"--member=serviceAccount:emmoni-budget-cap@",
        step6,
    )
