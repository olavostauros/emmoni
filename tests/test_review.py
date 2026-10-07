"""Fila de revisão e amostragem (SPECIFICATIONS.md §8)."""

import json
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from ingest import review
from tests import factories
from tests.factories import scalar

Conn = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def tx(ingest: Conn) -> Iterator[Conn]:
    yield ingest
    ingest.rollback()


def _exam(tx: Conn) -> tuple[review.ExamRef, int]:
    exam_id = factories.exam(tx, published=False)
    contest = scalar(
        tx,
        "select c.slug from contest c join exam e on e.contest_id = c.id where e.id = %s",
        (exam_id,),
    )
    for number in range(1, 13):
        status = "review" if number in (3, 4) else "draft"
        factories.question(
            tx,
            exam_id,
            number=number,
            publish_status=status,
            review_reasons=["figura ou tabela não extraída"] if status == "review" else [],
        )
    return review.ExamRef(str(contest), "prova"), exam_id


def test_exam_ref_parse() -> None:
    assert review.ExamRef.parse("pf-2021/agente") == review.ExamRef("pf-2021", "agente")
    with pytest.raises(review.ReviewError):
        review.ExamRef.parse("pf-2021")


def test_list_shows_reasons(tx: Conn) -> None:
    ref, _ = _exam(tx)
    rows = review.list_review(tx, ref)
    assert [(n, reasons) for _, n, reasons in rows] == [
        (3, ["figura ou tabela não extraída"]),
        (4, ["figura ou tabela não extraída"]),
    ]


def test_sample_is_deterministic_and_skips_review(tx: Conn) -> None:
    ref, _ = _exam(tx)
    first = review.sample_numbers(tx, ref, 5)
    assert first == review.sample_numbers(tx, ref, 5)
    assert len(first) == 5 and not {3, 4} & set(first)


def test_approve_requires_sample_then_publishes_exam(tx: Conn, tmp_path: Path) -> None:
    ref, exam_id = _exam(tx)
    with pytest.raises(review.ReviewError, match="amostra"):
        review.approve(tx, ref, tmp_path)
    page = review.write_sample(tx, ref, 4, tmp_path)
    assert "Amostra" in page.read_text(encoding="utf-8")
    review.approve(tx, ref, tmp_path)
    assert scalar(tx, "select publish_status from exam where id = %s", (exam_id,)) == "published"
    record = json.loads((page.parent / "sample.json").read_text(encoding="utf-8"))
    assert record["approved_at"] and record["approved_by"]
