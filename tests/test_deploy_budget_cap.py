"""Corte de gasto do deploy (deploy/budget-cap/main.py, decisão 0022). Sem rede: o HTTP é falso."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_spec = importlib.util.spec_from_file_location(
    "budget_cap_main", Path(__file__).parents[1] / "deploy" / "budget-cap" / "main.py"
)
assert _spec and _spec.loader
cap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cap)


class FakeHTTP:
    def __init__(self, ingress: str) -> None:
        self.ingress = ingress
        self.calls: list[tuple[str, str, Any]] = []

    def __call__(self, req: Any, timeout: float = 0) -> Any:
        method = req.get_method()
        body = json.loads(req.data) if req.data else None
        self.calls.append((method, req.full_url, body))
        if "metadata.google.internal" in req.full_url:
            out: dict[str, Any] = {"access_token": "t"}
        elif method == "PATCH":
            self.ingress = body["ingress"]
            out = {}
        else:
            out = {"ingress": self.ingress}
        data = json.dumps(out).encode()
        return _Resp(data)


class _Resp:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *a: object) -> None:
        return None


@pytest.fixture
def http(monkeypatch: pytest.MonkeyPatch) -> FakeHTTP:
    fake = FakeHTTP("INGRESS_TRAFFIC_ALL")
    monkeypatch.setattr(cap.urllib.request, "urlopen", fake)
    return fake


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"costAmount": 60.0, "budgetAmount": 60.0}, True),
        ({"costAmount": 61, "budgetAmount": 60}, True),
        ({"costAmount": 59.9, "budgetAmount": 60.0}, False),
        # previsão acima não corta: só gasto real
        ({"costAmount": 10, "budgetAmount": 60, "forecastThresholdExceeded": 1.0}, False),
        ({"budgetAmount": 60}, False),
        ({"costAmount": "x", "budgetAmount": 60}, False),
        ({"costAmount": 1, "budgetAmount": 0}, False),
    ],
)
def test_over_budget(payload: dict[str, Any], expected: bool) -> None:
    assert cap.over_budget(payload) is expected


def test_below_budget_does_not_call_google(http: FakeHTTP) -> None:
    assert "nada a fazer" in cap.handle({"costAmount": 1, "budgetAmount": 60})
    assert http.calls == []


def test_over_budget_sets_ingress_internal(http: FakeHTTP) -> None:
    msg = cap.handle({"budgetDisplayName": "emmoni-monthly", "costAmount": 60, "budgetAmount": 60})
    assert "passou a interno" in msg
    patch = [c for c in http.calls if c[0] == "PATCH"]
    assert len(patch) == 1
    assert patch[0][1].endswith(
        "/projects/emmoni-prod/locations/southamerica-east1/services/emmoni-api?updateMask=ingress"
    )
    assert patch[0][2] == {"ingress": "INGRESS_TRAFFIC_INTERNAL_ONLY"}


def test_already_internal_is_idempotent(http: FakeHTTP) -> None:
    http.ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"
    assert "já está interno" in cap.handle({"costAmount": 70, "budgetAmount": 60})
    assert not [c for c in http.calls if c[0] == "PATCH"]


def test_pubsub_entry_point(http: FakeHTTP, capsys: pytest.CaptureFixture[str]) -> None:
    data = base64.b64encode(json.dumps({"costAmount": 80, "budgetAmount": 60}).encode())
    cap.budget_cap(SimpleNamespace(data={"message": {"data": data}}))
    assert "passou a interno" in capsys.readouterr().out
