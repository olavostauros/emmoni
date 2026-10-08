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


def test_approve_records_reviewer(tx: Conn, tmp_path: Path) -> None:
    ref, _ = _exam(tx)
    review.write_sample(tx, ref, 3, tmp_path)
    review.approve(tx, ref, tmp_path, by="claude-opus-5-5")
    record = json.loads(
        (review.sample_dir(tmp_path, ref) / "sample.json").read_text(encoding="utf-8")
    )
    assert record["approved_by"] == "claude-opus-5-5"


def test_topic_sample_is_deterministic_and_counts_verdicts(tx: Conn, tmp_path: Path) -> None:
    ref, exam_id = _exam(tx)
    for number in (1, 2, 5):
        question_id = scalar(
            tx, "select id from question where exam_id = %s and number = %s", (exam_id, number)
        )
        tx.execute(
            "insert into question_topic (question_id, topic_id, origin)"
            " select %s, id, 'manual' from topic where path = 'direito_penal.crimes_contra_o_patrimonio.furto'",
            (question_id,),
        )
    first = review.sample_topics(tx, 2, seed="teste")
    assert first == review.sample_topics(tx, 2, seed="teste") and len(first) == 2
    assert all(
        i.topics == ["direito_penal.crimes_contra_o_patrimonio.furto — Furto"] for i in first
    )

    with pytest.raises(review.ReviewError, match="gere a amostra"):
        review.topic_sample_report(tmp_path)
    page = review.write_topic_sample(tx, 2, tmp_path, seed="teste")
    assert "Assuntos atribuídos" in page.read_text(encoding="utf-8")
    record_path = page.parent / "amostra.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert [i["verdict"] for i in record["items"]] == [None, None]
    record["items"][0]["verdict"] = "ok"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    report = review.topic_sample_report(tmp_path)
    assert (report.total, report.judged, report.ok, report.accuracy) == (2, 1, 1, 1.0)
    record["items"][1]["verdict"] = "talvez"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(review.ReviewError, match="veredito inválido"):
        review.topic_sample_report(tmp_path)
