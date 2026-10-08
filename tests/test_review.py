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


def test_sample_also_includes_publishable_changed_questions(tx: Conn, tmp_path: Path) -> None:
    ref, _ = _exam(tx)
    drawn = review.sample_numbers(tx, ref, 3)
    extra = next(n for n in (1, 2, 5, 6, 7, 8) if n not in drawn)
    review.write_sample(tx, ref, 3, tmp_path, also=[extra, 3])  # 3 está em revisão: fica de fora
    record = json.loads(
        (review.sample_dir(tmp_path, ref) / "sample.json").read_text(encoding="utf-8")
    )
    assert record["numbers"] == sorted({*drawn, extra})


def test_approve_requires_sample_then_publishes_exam(tx: Conn, tmp_path: Path) -> None:
    ref, exam_id = _exam(tx)
    with pytest.raises(review.ReviewError, match="amostra"):
        review.approve(tx, ref, tmp_path, approvals=tmp_path / "approvals")
    page = review.write_sample(tx, ref, 4, tmp_path)
    assert "Amostra" in page.read_text(encoding="utf-8")
    markdown = (page.parent / "amostra.md").read_text(encoding="utf-8")
    assert markdown.startswith(f"# Amostra — {ref}") and markdown.count("## Questão") == 4
    review.approve(tx, ref, tmp_path, approvals=tmp_path / "approvals")
    assert scalar(tx, "select publish_status from exam where id = %s", (exam_id,)) == "published"
    record = json.loads((page.parent / "sample.json").read_text(encoding="utf-8"))
    assert record["approved_at"] and record["approved_by"]


def test_approve_records_reviewer(tx: Conn, tmp_path: Path) -> None:
    ref, _ = _exam(tx)
    review.write_sample(tx, ref, 3, tmp_path)
    review.approve(tx, ref, tmp_path, by="claude-opus-5-5", approvals=tmp_path / "approvals")
    record = json.loads(
        (review.sample_dir(tmp_path, ref) / "sample.json").read_text(encoding="utf-8")
    )
    assert record["approved_by"] == "claude-opus-5-5"
    approval = json.loads(
        review.approval_path(tmp_path / "approvals", ref).read_text(encoding="utf-8")
    )
    assert approval["approved_by"] == "claude-opus-5-5"
    assert approval["numbers"] == record["numbers"]
    assert len(approval["fingerprint"]) == 64


def _status(tx: Conn, exam_id: int) -> object:
    return scalar(tx, "select publish_status from exam where id = %s", (exam_id,))


def test_reconcile_keeps_approved_content_and_demotes_changed(tx: Conn, tmp_path: Path) -> None:
    ref, exam_id = _exam(tx)
    approvals = tmp_path / "approvals"
    review.write_sample(tx, ref, 3, tmp_path)
    review.approve(tx, ref, tmp_path, approvals=approvals)
    # Classificação não conta: mudar o assunto não tira a prova do ar.
    tx.execute(
        "update question set publish_status = 'published' where exam_id = %s and number = 1",
        (exam_id,),
    )
    assert review.reconcile(tx, ref, approvals) == "publicada"
    # Gabarito mudou depois da aprovação → volta para review.
    tx.execute(
        "update question set answer_final = 'E', answer_preliminary = 'E'"
        " where exam_id = %s and number = 2",
        (exam_id,),
    )
    assert review.reconcile(tx, ref, approvals).startswith("volta para review")
    assert _status(tx, exam_id) == "review"


def test_reconcile_ignores_content_of_questions_in_review(tx: Conn, tmp_path: Path) -> None:
    ref, exam_id = _exam(tx)
    approvals = tmp_path / "approvals"
    review.write_sample(tx, ref, 3, tmp_path)
    review.approve(tx, ref, tmp_path, approvals=approvals)
    # A questão 3 está em revisão: fora do `api` e da amostra. Corrigir o texto dela não muda nada.
    tx.execute(
        "update question set statement_hash = repeat('1', 64) where exam_id = %s and number = 3",
        (exam_id,),
    )
    assert review.reconcile(tx, ref, approvals) == "publicada"
    # Sair da revisão muda o que o `api` mostra: reamostrar.
    tx.execute(
        "update question set publish_status = 'published', review_reasons = '{}'"
        " where exam_id = %s and number = 3",
        (exam_id,),
    )
    assert review.reconcile(tx, ref, approvals).startswith("volta para review")


def test_restore_publishes_matching_exams_from_records(tx: Conn, tmp_path: Path) -> None:
    ref, exam_id = _exam(tx)
    approvals = tmp_path / "approvals"
    review.write_sample(tx, ref, 3, tmp_path)
    review.approve(tx, ref, tmp_path, approvals=approvals)
    tx.execute("update exam set publish_status = 'draft' where id = %s", (exam_id,))  # banco novo
    results = dict(review.restore(tx, approvals))
    assert results[str(ref)].startswith("publicada")
    assert _status(tx, exam_id) == "published"


def test_reconcile_without_record_demotes_published_exam(tx: Conn, tmp_path: Path) -> None:
    ref, exam_id = _exam(tx)
    assert review.reconcile(tx, ref, tmp_path) == "draft"
    tx.execute("update exam set publish_status = 'published' where id = %s", (exam_id,))
    assert "sem registro" in review.reconcile(tx, ref, tmp_path)
    assert _status(tx, exam_id) == "review"


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
