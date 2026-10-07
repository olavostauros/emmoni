"""Fábricas de dados para testes. Tudo roda dentro da transação do teste e é desfeito no fim."""

import itertools
from typing import Any

import psycopg

from ingest.content import statement_hash

Conn = psycopg.Connection[tuple[object, ...]]
_seq = itertools.count(1)


def scalar(conn: Conn, query: Any, params: Any = None) -> Any:
    row = conn.execute(query, params).fetchone()
    assert row is not None
    return row[0]


def exam(conn: Conn, *, agency: str = "pf", board: str = "cebraspe", published: bool = True) -> int:
    n = next(_seq)
    contest_id = scalar(
        conn,
        "insert into contest (slug, agency_id, exam_board_id, year, name)"
        " select %s, a.id, b.id, 2020, 'teste' from agency a, exam_board b"
        " where a.slug = %s and b.slug = %s returning id",
        (f"zz-test-{n}", agency, board),
    )
    return int(
        scalar(
            conn,
            "insert into exam (contest_id, slug, name, publish_status) values (%s, 'prova', 'Prova', %s)"
            " returning id",
            (contest_id, "published" if published else "draft"),
        )
    )


def question(conn: Conn, exam_id: int, **fields: Any) -> str:
    """Insere uma questão certo/errado válida, em rascunho; `fields` sobrescreve colunas."""
    statement = fields.pop("statement_md", f"Enunciado de teste {next(_seq)}.")
    values: dict[str, Any] = {
        "exam_id": exam_id,
        "number": next(_seq),
        "type": "true_false",
        "subject_id": scalar(conn, "select id from subject where slug = 'direito-penal'"),
        "statement_md": statement,
        "answer_preliminary": "C",
        "answer_final": "C",
        "statement_hash": statement_hash(statement),
        "source_page": 1,
        "extracted_by": "test",
        **fields,
    }
    columns = ", ".join(values)
    placeholders = ", ".join(["%s"] * len(values))
    return str(
        scalar(
            conn,
            f"insert into question ({columns}) values ({placeholders}) returning id",  # type: ignore[arg-type]
            list(values.values()),
        )
    )


def options(conn: Conn, question_id: str, letters: str = "ABCDE") -> None:
    for letter in letters:
        conn.execute(
            "insert into question_option (question_id, letter, body_md) values (%s, %s, %s)",
            (question_id, letter, f"Alternativa {letter}."),
        )


def check_deferred(conn: Conn) -> None:
    """Dispara agora os constraint triggers diferidos (senão só rodariam no commit)."""
    conn.execute("set constraints all immediate")
