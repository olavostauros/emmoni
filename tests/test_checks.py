"""`emmoni check` e o runner de checks (SPECIFICATIONS.md §8)."""

from pathlib import Path

import psycopg
import pytest
from psycopg.errors import ReadOnlySqlTransaction

from ingest import checks, cli

Conn = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def checks_dir(tmp_path: Path) -> Path:
    (tmp_path / "001_passa.sql").write_text("select 1 as x where false")
    (tmp_path / "002_falha.sql").write_text("select 'q1' as questao, 'sem gabarito' as motivo")
    return tmp_path


def test_run_checks_reports_violations_in_order(ingest: Conn, checks_dir: Path) -> None:
    results = checks.run_checks(ingest, checks_dir)
    assert [(r.name, r.ok) for r in results] == [("001_passa", True), ("002_falha", False)]
    assert results[1].columns == ["questao", "motivo"]
    assert results[1].violations == [("q1", "sem gabarito")]


def test_checks_cannot_write(ingest: Conn, tmp_path: Path) -> None:
    (tmp_path / "001_escreve.sql").write_text("create temp table zz (id int)")
    with pytest.raises(ReadOnlySqlTransaction):
        checks.run_checks(ingest, tmp_path)


def test_repository_checks_pass_on_empty_database(ingest: Conn) -> None:
    assert all(result.ok for result in checks.run_checks(ingest))


def test_cli_exit_code(
    checks_dir: Path, ingest_url: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", ingest_url)
    assert cli.main(["check", "--checks-dir", str(checks_dir)]) == 1
    (checks_dir / "002_falha.sql").unlink()
    assert cli.main(["check", "--checks-dir", str(checks_dir)]) == 0
