"""Restrições do modelo de dados (SPECIFICATION.md §4). Cada uma é violada de propósito."""

from collections.abc import Iterator

import psycopg
import pytest
from psycopg.errors import (
    CheckViolation,
    ForeignKeyViolation,
    IntegrityError,
)

from tests import factories as f

Conn = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def tx(ingest: Conn) -> Iterator[Conn]:
    """Conexão como emmoni_ingest numa transação que é sempre desfeita."""
    with ingest.transaction(force_rollback=True):
        yield ingest


@pytest.fixture
def exam_id(tx: Conn) -> int:
    return f.exam(tx)


def violates(tx: Conn, error: type[Exception], statement: str, params: object = None) -> None:
    with pytest.raises(error), tx.transaction():
        tx.execute(statement, params)  # type: ignore[arg-type]
        f.check_deferred(tx)


# --- Gabarito × tipo ----------------------------------------------------------------------------


def test_valid_questions_of_each_type(tx: Conn, exam_id: int) -> None:
    f.question(tx, exam_id)
    mc = f.question(tx, exam_id, type="multiple_choice", answer_preliminary="B", answer_final="B")
    f.options(tx, mc, "ABCD")
    f.question(tx, exam_id, type="essay", answer_preliminary=None, answer_final=None)
    f.check_deferred(tx)


@pytest.mark.parametrize(
    ("qtype", "answer"),
    [("true_false", "A"), ("true_false", "c"), ("multiple_choice", "F"), ("multiple_choice", "C ")],
)
def test_answer_must_match_type(tx: Conn, exam_id: int, qtype: str, answer: str) -> None:
    with pytest.raises(CheckViolation), tx.transaction():
        f.question(tx, exam_id, type=qtype, answer_preliminary=answer, answer_final=answer)


def test_essay_has_no_answer(tx: Conn, exam_id: int) -> None:
    with pytest.raises(CheckViolation), tx.transaction():
        f.question(tx, exam_id, type="essay", answer_preliminary=None, answer_final="C")


def test_true_false_has_no_options(tx: Conn, exam_id: int) -> None:
    qid = f.question(tx, exam_id)
    violates(
        tx,
        CheckViolation,
        "insert into question_option (question_id, letter, body_md) values (%s, 'A', 'x')",
        (qid,),
    )


def test_multiple_choice_answer_must_be_an_option(tx: Conn, exam_id: int) -> None:
    with pytest.raises(CheckViolation), tx.transaction():
        qid = f.question(
            tx, exam_id, type="multiple_choice", answer_preliminary="E", answer_final="E"
        )
        f.options(tx, qid, "ABCD")
        f.check_deferred(tx)


def test_cannot_delete_the_option_that_is_the_answer(tx: Conn, exam_id: int) -> None:
    qid = f.question(tx, exam_id, type="multiple_choice", answer_preliminary="B", answer_final="B")
    f.options(tx, qid, "ABCD")
    f.check_deferred(tx)
    violates(
        tx,
        CheckViolation,
        "delete from question_option where question_id = %s and letter = 'B'",
        (qid,),
    )


def test_option_letter_range(tx: Conn, exam_id: int) -> None:
    qid = f.question(
        tx, exam_id, type="multiple_choice", answer_preliminary=None, answer_final=None
    )
    violates(
        tx,
        CheckViolation,
        "insert into question_option (question_id, letter, body_md) values (%s, 'F', 'x')",
        (qid,),
    )


# --- Status do gabarito após recursos -----------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "preliminary", "final", "ok"),
    [
        ("valid", "C", "C", True),
        ("valid", "C", None, True),
        ("valid", "C", "E", False),
        ("changed", "C", "E", True),
        ("changed", "C", "C", False),
        ("changed", None, "E", False),
        ("annulled", "C", None, True),
        ("annulled", "C", "C", False),
    ],
)
def test_answer_status(
    tx: Conn, exam_id: int, status: str, preliminary: str | None, final: str | None, ok: bool
) -> None:
    def insert() -> None:
        f.question(
            tx, exam_id, answer_status=status, answer_preliminary=preliminary, answer_final=final
        )

    if ok:
        insert()
    else:
        with pytest.raises(CheckViolation), tx.transaction():
            insert()


# --- Publicação ----------------------------------------------------------------------------------


def test_published_needs_final_answer_unless_annulled(tx: Conn, exam_id: int) -> None:
    with pytest.raises(CheckViolation), tx.transaction():
        f.question(tx, exam_id, publish_status="published", answer_final=None)
    f.question(tx, exam_id, publish_status="published", answer_final=None, answer_status="annulled")


def test_published_needs_subject(tx: Conn, exam_id: int) -> None:
    f.question(tx, exam_id, subject_id=None)
    with pytest.raises(CheckViolation), tx.transaction():
        f.question(tx, exam_id, subject_id=None, publish_status="published")


# --- Integridade ---------------------------------------------------------------------------------


def test_passage_must_belong_to_same_exam(tx: Conn, exam_id: int) -> None:
    other_exam = f.exam(tx)
    passage = f.scalar(
        tx,
        "insert into passage (exam_id, body_md, source_page) values (%s, 'texto', 1) returning id",
        (other_exam,),
    )
    with pytest.raises(ForeignKeyViolation), tx.transaction():
        f.question(tx, exam_id, passage_id=passage)


def test_number_unique_per_exam(tx: Conn, exam_id: int) -> None:
    f.question(tx, exam_id, number=1)
    with pytest.raises(IntegrityError), tx.transaction():
        f.question(tx, exam_id, number=1)


def test_not_duplicate_of_itself(tx: Conn, exam_id: int) -> None:
    qid = f.question(tx, exam_id)
    violates(tx, CheckViolation, "update question set duplicate_of = id where id = %s", (qid,))


def test_statement_hash_format(tx: Conn, exam_id: int) -> None:
    with pytest.raises(CheckViolation), tx.transaction():
        f.question(tx, exam_id, statement_hash="abc")


def test_deleting_contest_cascades(tx: Conn, exam_id: int) -> None:
    qid = f.question(tx, exam_id, type="multiple_choice", answer_preliminary="A", answer_final="A")
    f.options(tx, qid, "ABCD")
    tx.execute(
        "delete from contest where id = (select contest_id from exam where id = %s)", (exam_id,)
    )
    assert f.scalar(tx, "select count(*) from question_option where question_id = %s", (qid,)) == 0


# --- Catálogo e taxonomia ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "state"), [("federal", "DF"), ("estadual", None), ("estadual", "sp")]
)
def test_agency_state_by_level(tx: Conn, level: str, state: str | None) -> None:
    violates(
        tx,
        CheckViolation,
        "insert into agency (slug, name, short_name, career, level, state)"
        " values ('zz', 'x', 'x', 'outra', %s, %s)",
        (level, state),
    )


@pytest.mark.parametrize("slug", ["PF", "pc_sp", "-pf", "pf-", "pc--sp", ""])
def test_slug_format(tx: Conn, slug: str) -> None:
    violates(
        tx,
        CheckViolation,
        "insert into exam_board (slug, name, short_name) values (%s, 'x', 'x')",
        (slug,),
    )


def test_topic_must_start_with_subject_label(tx: Conn) -> None:
    violates(
        tx,
        CheckViolation,
        "insert into topic (subject_id, path, name)"
        " select id, 'direito_civil.contratos', 'x' from subject where slug = 'direito-penal'",
    )


def test_topic_parent_must_exist(tx: Conn) -> None:
    violates(
        tx,
        ForeignKeyViolation,
        "insert into topic (subject_id, path, name)"
        " select id, 'direito_penal.inexistente.filho', 'x' from subject where slug = 'direito-penal'",
    )


def test_topic_with_children_cannot_be_deleted(tx: Conn) -> None:
    violates(
        tx,
        ForeignKeyViolation,
        "delete from topic where path = 'direito_penal.crimes_contra_o_patrimonio'",
    )


# --- Busca textual --------------------------------------------------------------------------------


def matches(tx: Conn, qid: str, text: str) -> bool:
    return bool(
        f.scalar(
            tx,
            "select search_vector @@ websearch_to_tsquery('ext.pt_unaccent', %s)"
            " from question where id = %s",
            (text, qid),
        )
    )


def test_search_vector_follows_statement_options_and_passage(tx: Conn, exam_id: int) -> None:
    passage = f.scalar(
        tx,
        "insert into passage (exam_id, body_md, source_page) values (%s, 'Texto sobre balística.', 1)"
        " returning id",
        (exam_id,),
    )
    qid = f.question(
        tx,
        exam_id,
        statement_md="Questão sobre **perícia**.",
        type="multiple_choice",
        answer_preliminary=None,
        answer_final=None,
        passage_id=passage,
    )
    assert matches(tx, qid, "pericia")  # sem acento
    assert matches(tx, qid, "balistica")
    assert not matches(tx, qid, "papiloscopia")

    tx.execute(
        "insert into question_option (question_id, letter, body_md) values (%s, 'A', 'Papiloscopia')",
        (qid,),
    )
    assert matches(tx, qid, "papiloscopia")

    tx.execute("update passage set body_md = 'Texto sobre necropsia.' where id = %s", (passage,))
    assert matches(tx, qid, "necropsia")
    assert not matches(tx, qid, "balistica")


def test_topic_path_is_immutable(tx: Conn) -> None:
    violates(
        tx,
        CheckViolation,
        "update topic set path = 'direito_penal.outro' where path = 'direito_penal.crimes_contra_a_pessoa.homicidio'",
    )


def test_topic_ancestor_closure(tx: Conn) -> None:
    tx.execute(
        "insert into topic (subject_id, path, name)"
        " select id, 'direito_penal.crimes_contra_a_pessoa.homicidio.qualificado', 'Qualificado'"
        " from subject where slug = 'direito-penal'"
    )
    ancestors = tx.execute(
        "select a.path::text from topic_ancestor ta"
        " join topic t on t.id = ta.topic_id join topic a on a.id = ta.ancestor_id"
        " where t.path = 'direito_penal.crimes_contra_a_pessoa.homicidio.qualificado'"
        " order by a.path"
    ).fetchall()
    assert [r[0] for r in ancestors] == [
        "direito_penal.crimes_contra_a_pessoa",
        "direito_penal.crimes_contra_a_pessoa.homicidio",
        "direito_penal.crimes_contra_a_pessoa.homicidio.qualificado",
    ]
    assert (
        f.scalar(
            tx,
            "select count(*) from topic t where not exists"
            " (select 1 from topic_ancestor ta where ta.topic_id = t.id"
            " and ta.ancestor_id = t.id)",
        )
        == 0
    )
