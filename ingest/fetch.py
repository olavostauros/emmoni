"""Etapa `fetch`: documentos do manifesto → `data/raw/<sha256>.pdf` + `source_document`.

Um índice `data/raw/index.json` (URL → sha256) evita baixar de novo o que já está em disco: a etapa
só vai à rede para URLs novas. Toda requisição passa pelo cliente de cortesia (decisão 0003).
"""

import datetime
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pymupdf

from ingest.crawlers.http import PoliteClient

DocumentKind = str  # 'exam' | 'answer_key_preliminary' | 'answer_key_final' | ...


def data_dir() -> Path:
    return Path(os.environ.get("EMMONI_DATA_DIR") or "data")


@dataclass(frozen=True)
class Fetched:
    url: str
    sha256: str
    path: Path
    page_count: int
    downloaded: bool  # False = já estava em disco


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.index_path = root / "index.json"
        self.index: dict[str, str] = (
            json.loads(self.index_path.read_text()) if self.index_path.exists() else {}
        )

    def get(self, url: str, client: PoliteClient | None) -> Fetched:
        sha = self.index.get(url)
        if sha and (path := self.root / f"{sha}.pdf").exists():
            return Fetched(url, sha, path, _page_count(path), downloaded=False)
        if client is None:
            raise RuntimeError(f"{url} não está em {self.root} e não há cliente HTTP")
        response = client.get(url)
        if response.content_type != "application/pdf":
            raise RuntimeError(f"{url}: esperado PDF, veio {response.content_type}")
        sha = hashlib.sha256(response.content).hexdigest()
        path = self.root / f"{sha}.pdf"
        self.root.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        self.index[url] = sha
        self.index_path.write_text(json.dumps(self.index, indent=1, sort_keys=True))
        return Fetched(url, sha, path, _page_count(path), downloaded=True)


def _page_count(path: Path) -> int:
    with pymupdf.open(path) as document:  # type: ignore[no-untyped-call]
        return int(document.page_count)


def record(conn: psycopg.Connection[tuple[object, ...]], kind: DocumentKind, doc: Fetched) -> int:
    """Upsert em `source_document` pelo sha256; devolve o id."""
    row = conn.execute(
        """insert into source_document (kind, url, sha256, local_path, page_count, fetched_at)
           values (%s, %s, %s, %s, %s, %s)
           on conflict (sha256) do update
             set local_path = excluded.local_path, page_count = excluded.page_count
           returning id""",
        (
            kind,
            doc.url,
            doc.sha256,
            str(doc.path),
            doc.page_count,
            datetime.datetime.now(datetime.UTC),
        ),
    ).fetchone()
    assert row is not None
    return int(str(row[0]))
