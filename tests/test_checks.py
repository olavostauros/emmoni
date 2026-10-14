"""`emmoni check` e o runner de checks (SPECIFICATION.md §8)."""

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg.errors import ReadOnlySqlTransaction

from ingest import checks, cli
from tests import factories as f

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


def test_repository_checks_pass_on_seed(ingest: Conn) -> None:
    assert [r.name for r in checks.run_checks(ingest) if not r.ok] == []


# Cada check do repositório pega a violação que descreve.


@pytest.fixture
def tx(ingest: Conn) -> Iterator[Conn]:
    with ingest.transaction(force_rollback=True):
        yield ingest


def failing(tx: Conn) -> set[str]:
    with tx.cursor() as cur:
        return {r.name for r in checks.run_with_cursor(cur) if not r.ok}


def seed_question(tx: Conn, contest: str, number: int) -> str:
    return str(
        f.scalar(
            tx,
            "select q.id from question q join exam e on e.id = q.exam_id"
            " join contest c on c.id = e.contest_id where c.slug = %s and q.number = %s",
            (contest, number),
        )
    )


def test_check_multiple_choice_options(tx: Conn) -> None:
    qid = seed_question(tx, "seed-pmsp-2024", 1)  # A-D, gabarito C
    tx.execute("delete from question_option where question_id = %s and letter = 'B'", (qid,))
    assert failing(tx) == {"010_multiple_choice_options"}


def test_check_numbering_gaps(tx: Conn) -> None:
    tx.execute("delete from question where id = %s", (seed_question(tx, "seed-pmsp-2024", 5),))
    assert failing(tx) == {"020_numbering_gaps"}


def test_check_numbering_may_start_after_one(tx: Conn) -> None:
    """Caderno que começa no meio (PRF 2021: itens 9 a 120) não é buraco."""
    tx.execute("delete from question where id = %s", (seed_question(tx, "seed-pmsp-2024", 1),))
    assert failing(tx) == set()


def test_check_missing_assets(tx: Conn) -> None:
    tx.execute("delete from question_asset")
    assert failing(tx) == {"030_missing_assets"}


def test_check_unmarked_duplicates(tx: Conn) -> None:
    a, b = seed_question(tx, "seed-pf-2025", 11), seed_question(tx, "seed-pf-2025", 12)
    tx.execute(
        "update question set statement_hash = (select statement_hash from question where id = %s)"
        " where id = %s",
        (a, b),
    )
    assert failing(tx) == {"040_unmarked_duplicates"}
    tx.execute("update question set duplicate_of = %s where id = %s", (a, b))
    assert "040_unmarked_duplicates" not in failing(tx)


def test_check_published_without_topic(tx: Conn) -> None:
    tx.execute(
        "delete from question_topic where question_id = %s", (seed_question(tx, "seed-pf-2025", 1),)
    )
    assert failing(tx) == {"050_published_without_topic"}


def test_check_passage_without_questions(tx: Conn) -> None:
    tx.execute(
        "insert into passage (exam_id, body_md, source_page)"
        " select exam_id, 'texto solto', 1 from question where id = %s",
        (seed_question(tx, "seed-pf-2025", 1),),
    )
    assert failing(tx) == {"060_passage_without_questions"}


def test_check_position_agency_mismatch(tx: Conn) -> None:
    tx.execute(
        "insert into exam_position (exam_id, position_id)"
        " select q.exam_id, p.id from question q, position p where q.id = %s and p.slug = 'soldado'",
        (seed_question(tx, "seed-pf-2025", 1),),
    )
    assert failing(tx) == {"070_position_agency_mismatch"}


@pytest.mark.parametrize("body", ["texto\n\n", " texto", "texto\u00a0", "ac\u0327a\u0303o"])
def test_check_unnormalized_text(tx: Conn, body: str) -> None:
    tx.execute(
        "update question set statement_md = %s where id = %s",
        (body, seed_question(tx, "seed-pf-2025", 1)),
    )
    assert failing(tx) == {"080_unnormalized_text"}


def test_cli_exit_code(
    checks_dir: Path, ingest_url: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", ingest_url)
    assert cli.main(["check", "--checks-dir", str(checks_dir)]) == 1
    (checks_dir / "002_falha.sql").unlink()
    assert cli.main(["check", "--checks-dir", str(checks_dir)]) == 0


@pytest.mark.parametrize("column", ["statement", "option", "passage"])
def test_check_replacement_character(tx: Conn, column: str) -> None:
    """U+FFFD em questão publicada: no enunciado, numa alternativa ou no texto-base dela."""
    qid = seed_question(tx, "seed-pmsp-2024", 1)
    if column == "statement":
        tx.execute(
            "update question set statement_md = statement_md || ' teclas � e �' where id = %s",
            (qid,),
        )
    elif column == "option":
        tx.execute(
            "update question_option set body_md = body_md || ' �'"
            " where question_id = %s and letter = 'A'",
            (qid,),
        )
    else:
        tx.execute(
            "insert into passage (exam_id, body_md, source_page)"
            " select exam_id, 'texto com �', 1 from question where id = %s",
            (qid,),
        )
        tx.execute(
            "update question set passage_id = (select max(id::text)::uuid from passage"
            " where body_md = 'texto com �') where id = %s",
            (qid,),
        )
    assert failing(tx) == {"090_replacement_character"}
    tx.execute("update question set publish_status = 'review' where id = %s", (qid,))
    assert "090_replacement_character" not in failing(tx)
