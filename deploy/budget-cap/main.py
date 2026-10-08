"""Corte de gasto do emmoni no Google Cloud (docs/DEPLOY.md §3, decisão 0022).

Recebe as notificações dos budgets pelo Pub/Sub. Quando o gasto **real** (nunca a previsão)
alcança o valor do budget, muda o ingresso do serviço Cloud Run `emmoni-api` para
`INGRESS_TRAFFIC_INTERNAL_ONLY`: o tráfego público para na borda, as instâncias escalam a zero
e o gasto para. Nada é apagado; voltar é `gcloud run services update emmoni-api --ingress=all`.

Só biblioteca padrão: o token vem do servidor de metadados, com a conta de serviço da função.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request
from typing import Any

PROJECT = os.environ.get("EMMONI_PROJECT", "emmoni-prod")
REGION = os.environ.get("EMMONI_REGION", "southamerica-east1")
SERVICE = os.environ.get("EMMONI_SERVICE", "emmoni-api")
INTERNAL = "INGRESS_TRAFFIC_INTERNAL_ONLY"
METADATA_TOKEN = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


def over_budget(payload: dict[str, Any]) -> bool:
    """Gasto real ≥ budget. A previsão (`forecastThresholdExceeded`) nunca corta."""
    try:
        cost = float(payload["costAmount"])
        budget = float(payload["budgetAmount"])
    except (KeyError, TypeError, ValueError):
        return False
    return budget > 0 and cost >= budget


def _token() -> str:
    req = urllib.request.Request(METADATA_TOKEN, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return str(json.load(r)["access_token"])


def _service_url() -> str:
    return f"https://run.googleapis.com/v2/projects/{PROJECT}/locations/{REGION}/services/{SERVICE}"


def current_ingress(token: str) -> str:
    req = urllib.request.Request(_service_url(), headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return str(json.load(r).get("ingress", ""))


def set_internal(token: str) -> None:
    req = urllib.request.Request(
        _service_url() + "?updateMask=ingress",
        data=json.dumps({"ingress": INTERNAL}).encode(),
        method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def handle(payload: dict[str, Any]) -> str:
    """Decide e age. Devolve o que fez, para o log."""
    name = payload.get("budgetDisplayName", "?")
    if not over_budget(payload):
        return f"{name}: abaixo do budget, nada a fazer"
    token = _token()
    if current_ingress(token) == INTERNAL:
        return f"{name}: acima do budget, {SERVICE} já está interno"
    set_internal(token)
    return f"{name}: acima do budget, {SERVICE} passou a interno"


def budget_cap(cloud_event: Any) -> None:
    """Entrada da Cloud Run function (gatilho Pub/Sub)."""
    data = cloud_event.data["message"]["data"]
    payload = json.loads(base64.b64decode(data))
    print(handle(payload))
