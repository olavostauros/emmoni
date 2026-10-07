"""Carga da taxonomia (SPECIFICATIONS.md §4.4)."""

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from ingest import taxonomy
from tests import factories as f

Conn = psycopg.Connection[tuple[object, ...]]

GOOD = """
subject: zz-teste
name: Teste
topics:
  - slug: pai
    name: Pai
    children:
      - {slug: filho-um, name: Filho um}
"""


def write(tmp_path: Path, text: str, name: str = "zz-teste.yaml") -> Path:
    (tmp_path / name).write_text(text)
    return tmp_path


def test_parse_builds_paths_parents_first(tmp_path: Path) -> None:
    (subject,) = taxonomy.load_dir(write(tmp_path, GOOD))
    assert subject.slug == "zz-teste"
    assert [t.path for t in subject.topics] == ["zz_teste.pai", "zz_teste.pai.filho_um"]


@pytest.mark.parametrize(
    "text",
    [
        "subject: Zz\nname: x\n",
        "subject: zz\n",
        "subject: zz\nname: x\ntopics:\n  - {slug: a_b, name: x}\n",
        "subject: zz\nname: x\ntopics:\n  - {slug: a, name: x}\n  - {slug: a, name: y}\n",
        "subject: zz\nname: x\ntopics:\n  - {slug: a, nome: x}\n",
        "subject: zz\nname: x\nextra: 1\n",
    ],
)
def test_parse_rejects(tmp_path: Path, text: str) -> None:
    with pytest.raises(taxonomy.TaxonomyError):
        taxonomy.load_dir(write(tmp_path, text))


def test_repository_taxonomy_parses() -> None:
    assert len(taxonomy.load_dir()) >= 9


@pytest.fixture
def tx(ingest: Conn) -> Iterator[Conn]:
    with ingest.transaction(force_rollback=True):
        yield ingest


def test_sync_is_idempotent_and_reports_orphans(tx: Conn, tmp_path: Path) -> None:
    subjects = taxonomy.load_dir(write(tmp_path, GOOD))
    first = taxonomy.sync(tx, subjects)
    second = taxonomy.sync(tx, subjects)
    assert (first.subjects, first.topics, first.orphans) == (1, 2, [])
    assert (second.subjects, second.topics, second.orphans) == (1, 2, [])
    assert f.scalar(tx, "select count(*) from topic where path <@ 'zz_teste'") == 2

    renamed = taxonomy.load_dir(write(tmp_path, GOOD.replace("name: Pai", "name: Pai novo")))
    taxonomy.sync(tx, renamed)
    assert f.scalar(tx, "select name from topic where path = 'zz_teste.pai'") == "Pai novo"

    pruned = taxonomy.load_dir(write(tmp_path, GOOD.split("    children:")[0]))
    assert taxonomy.sync(tx, pruned).orphans == ["zz_teste.pai.filho_um"]
