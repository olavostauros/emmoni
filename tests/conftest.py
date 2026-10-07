"""Fixtures compartilhadas. O banco de testes é recriado por `make test-db`."""

import os
from collections.abc import Iterator

import psycopg
import pytest


def _url(var: str, role: str) -> str:
    port = os.environ.get("EMMONI_DB_PORT", "55432")
    default = f"postgres://{role}:{role}@localhost:{port}/emmoni_test?sslmode=disable"
    return os.environ.get(var, default)


@pytest.fixture(scope="session")
def owner_url() -> str:
    return _url("DATABASE_URL_TEST_OWNER", "emmoni_owner")


@pytest.fixture(scope="session")
def ingest_url() -> str:
    return _url("DATABASE_URL_TEST", "emmoni_ingest")


@pytest.fixture(scope="session")
def web_url() -> str:
    return _url("DATABASE_URL_TEST_WEB", "emmoni_web")


@pytest.fixture
def owner(owner_url: str) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    with psycopg.connect(owner_url, autocommit=True) as conn:
        yield conn


@pytest.fixture
def ingest(ingest_url: str) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    with psycopg.connect(ingest_url) as conn:
        yield conn


@pytest.fixture
def web(web_url: str) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    with psycopg.connect(web_url) as conn:
        yield conn
