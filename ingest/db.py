"""Conexão com o banco."""

import os

import psycopg


def connect(url: str | None = None) -> psycopg.Connection[tuple[object, ...]]:
    """Conecta em `url` ou, se omitida, em DATABASE_URL (papel emmoni_ingest)."""
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não definida (veja .env.example)")
    return psycopg.connect(url)
