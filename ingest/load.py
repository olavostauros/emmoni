"""Etapa `load`: staging → banco, uma transação por prova (SPECIFICATION.md §7.3).

Idempotente: concurso e prova por slug, texto-base por `(exam_id, source_key)`, questão por
`(exam_id, number)`. Rodar duas vezes produz o mesmo estado, com os mesmos ids.

Status de publicação da questão: `review` se há motivo de revisão; `published` se não há motivo e
há ao menos um assunto; senão `draft` (aguardando classificação). A **prova** nunca é publicada
aqui: isso só acontece depois da amostragem (`emmoni review approve`).
"""

from dataclasses import dataclass, field

import psycopg

from ingest.content import statement_hash
from ingest.manifest import Exam, Manifest
from ingest.staging import RawOption
from ingest.validate import Validated

Conn = psycopg.Connection[tuple[object, ...]]


EMPTY_OPTION = "*(alternativa sem texto extraído: figura ou fórmula)*"


@dataclass(frozen=True)
class DocumentIds:
    exam: int
    answer_key_preliminary: int | None  # primeiro PDF de cada tipo (colunas históricas de exam)
    answer_key_final: int | None
    all: list[tuple[str, int]] = field(default_factory=list)  # (tipo, id) de todos → exam_document


@dataclass(frozen=True)
class TopicAssignment:
    path: str  # ltree do assunto
    origin: str  # 'llm' | 'rule' | 'manual'
    confidence: float | None


@dataclass(frozen=True)
class LoadReport:
    exam_id: int
    questions: int
    published: int
    review: int
    draft: int
    duplicates: int
    removed: int


class LoadError(Exception):
    pass


def load_exam(
    conn: Conn,
    manifest: Manifest,
    exam: Exam,
    documents: DocumentIds,
    validated: Validated,
    topics: dict[int, list[TopicAssignment]] | None = None,
    extra_reasons: dict[int, str] | None = None,
) -> LoadReport:
    """`extra_reasons`: motivos de revisão de etapas posteriores ao validate (classify)."""
    topics = topics or {}
    extra_reasons = extra_reasons or {}
    if validated.exam_reasons:
        raise LoadError("; ".join(validated.exam_reasons))
    with conn.transaction():
        contest_id = _contest(conn, manifest)
        exam_id = _exam(conn, contest_id, manifest, exam, documents)
        passage_ids = _passages(conn, exam_id, validated)
        subject_ids = _subjects(conn, validated)
        counts = {"published": 0, "review": 0, "draft": 0}
        duplicates = 0
        numbers = []
        for question in validated.questions:
            numbers.append(question.number)
            passage_id = passage_ids.get(question.passage_key) if question.passage_key else None
            passage_md = (
                next(p.body_md for p in validated.passages if p.key == question.passage_key)
                if passage_id
                else None
            )
            options = [option.body_md for option in question.options]
            assigned = topics.get(question.number, [])
            reasons = list(question.review_reasons)
            if question.number in extra_reasons:
                reasons.append(extra_reasons[question.number])
            if reasons:
                status = "review"
            elif assigned:
                status = "published"
            else:
                status = "draft"
            counts[status] += 1
            digest = statement_hash(question.statement_md, options, passage_md)
            row = conn.execute(
                """insert into question
                     (exam_id, number, type, subject_id, passage_id, statement_md,
                      answer_preliminary, answer_final, answer_status, statement_hash,
                      source_page, extracted_by, publish_status, review_reasons)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   on conflict (exam_id, number) do update set
                     type = excluded.type, subject_id = excluded.subject_id,
                     passage_id = excluded.passage_id, statement_md = excluded.statement_md,
                     answer_preliminary = excluded.answer_preliminary,
                     answer_final = excluded.answer_final, answer_status = excluded.answer_status,
                     statement_hash = excluded.statement_hash, source_page = excluded.source_page,
                     extracted_by = excluded.extracted_by,
                     publish_status = excluded.publish_status,
                     review_reasons = excluded.review_reasons
                   returning id""",
                (
                    exam_id,
                    question.number,
                    question.type,
                    subject_ids.get(question.subject) if question.subject else None,
                    passage_id,
                    question.statement_md,
                    question.answer_preliminary,
                    question.answer_final,
                    question.answer_status,
                    digest,
                    question.page,
                    question.extracted_by,
                    status,
                    reasons,
                ),
            ).fetchone()
            assert row is not None
            question_id = row[0]
            _options(conn, question_id, question.options)
            _topics(conn, question_id, assigned)
            # Em revisão o conteúdo extraído está incompleto (figura, fórmula): o hash não serve
            # para dizer que é a mesma questão.
            duplicates += _mark_duplicate(conn, question_id, None if status == "review" else digest)
        removed = conn.execute(
            "delete from question where exam_id = %s and number <> all(%s)", (exam_id, numbers)
        ).rowcount
        conn.execute(
            """delete from passage p where p.exam_id = %s
                 and not exists (select 1 from question q where q.passage_id = p.id)""",
            (exam_id,),
        )
    return LoadReport(
        exam_id=exam_id,
        questions=len(numbers),
        duplicates=duplicates,
        removed=removed,
        **counts,
    )


def _one(conn: Conn, sql: str, params: tuple[object, ...]) -> int:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise LoadError(f"nenhuma linha: {sql.split()[0:6]} {params}")
    return int(str(row[0]))


def _contest(conn: Conn, manifest: Manifest) -> int:
    agency = _one(conn, "select id from agency where slug = %s", (manifest.agency,))
    board = _one(conn, "select id from exam_board where slug = %s", (manifest.exam_board,))
    return _one(
        conn,
        """insert into contest (slug, agency_id, exam_board_id, year, notice_number, name)
           values (%s, %s, %s, %s, %s, %s)
           on conflict (slug) do update set
             agency_id = excluded.agency_id, exam_board_id = excluded.exam_board_id,
             year = excluded.year, notice_number = excluded.notice_number, name = excluded.name
           returning id""",
        (manifest.contest, agency, board, manifest.year, manifest.notice_number, manifest.name),
    )


def _exam(
    conn: Conn, contest_id: int, manifest: Manifest, exam: Exam, documents: DocumentIds
) -> int:
    exam_id = _one(
        conn,
        """insert into exam (contest_id, slug, name, applied_on, shift, canonical_booklet,
                             exam_document_id, answer_key_preliminary_document_id,
                             answer_key_final_document_id)
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           on conflict (contest_id, slug) do update set
             name = excluded.name, applied_on = excluded.applied_on, shift = excluded.shift,
             canonical_booklet = excluded.canonical_booklet,
             exam_document_id = excluded.exam_document_id,
             answer_key_preliminary_document_id = excluded.answer_key_preliminary_document_id,
             answer_key_final_document_id = excluded.answer_key_final_document_id
           returning id""",
        (
            contest_id,
            exam.slug,
            exam.name,
            exam.applied_on,
            exam.shift,
            exam.canonical_booklet,
            documents.exam,
            documents.answer_key_preliminary,
            documents.answer_key_final,
        ),
    )
    conn.execute("delete from exam_document where exam_id = %s", (exam_id,))
    linked = documents.all or [
        (kind, doc_id)
        for kind, doc_id in (
            ("exam", documents.exam),
            ("answer_key_preliminary", documents.answer_key_preliminary),
            ("answer_key_final", documents.answer_key_final),
        )
        if doc_id is not None
    ]
    for position, (kind, doc_id) in enumerate(linked, start=1):
        conn.execute(
            """insert into exam_document (exam_id, source_document_id, kind, position)
               values (%s, %s, %s, %s) on conflict do nothing""",
            (exam_id, doc_id, kind, position),
        )
    conn.execute("delete from exam_position where exam_id = %s", (exam_id,))
    for slug in exam.positions:
        position = _one(
            conn,
            """select p.id from position p join agency a on a.id = p.agency_id
                where a.slug = %s and p.slug = %s""",
            (manifest.agency, slug),
        )
        conn.execute(
            "insert into exam_position (exam_id, position_id) values (%s, %s)",
            (exam_id, position),
        )
    return exam_id


def _passages(conn: Conn, exam_id: int, validated: Validated) -> dict[str, object]:
    used = {q.passage_key for q in validated.questions if q.passage_key}
    ids: dict[str, object] = {}
    for passage in validated.passages:
        if passage.key not in used:
            continue
        row = conn.execute(
            """insert into passage (exam_id, source_key, body_md, source_page)
               values (%s, %s, %s, %s)
               on conflict (exam_id, source_key) do update set
                 body_md = excluded.body_md, source_page = excluded.source_page
               returning id""",
            (exam_id, passage.key, passage.body_md, passage.page),
        ).fetchone()
        assert row is not None
        ids[passage.key] = row[0]
    return ids


def _subjects(conn: Conn, validated: Validated) -> dict[str, int]:
    slugs = sorted({q.subject for q in validated.questions if q.subject})
    rows = conn.execute("select slug, id from subject where slug = any(%s)", (slugs,)).fetchall()
    found = {str(slug): int(str(id_)) for slug, id_ in rows}
    missing = set(slugs) - set(found)
    if missing:
        raise LoadError(f"disciplinas fora da taxonomia: {sorted(missing)}")
    return found


def _options(conn: Conn, question_id: object, options: list[RawOption]) -> None:
    conn.execute("delete from question_option where question_id = %s", (question_id,))
    for option in options:
        conn.execute(
            "insert into question_option (question_id, letter, body_md) values (%s, %s, %s)",
            # Alternativa só com figura: placeholder explícito; a questão fica em review (validate).
            (question_id, option.letter, option.body_md.strip() or EMPTY_OPTION),
        )


def _topics(conn: Conn, question_id: object, assigned: list[TopicAssignment]) -> None:
    # Classificação manual nunca é sobrescrita pela automática.
    conn.execute(
        "delete from question_topic where question_id = %s and origin <> 'manual'", (question_id,)
    )
    for topic in assigned:
        topic_id = _one(conn, "select id from topic where path = %s::ltree", (topic.path,))
        conn.execute(
            """insert into question_topic (question_id, topic_id, origin, confidence)
               values (%s, %s, %s, %s)
               on conflict (question_id, topic_id) do nothing""",
            (question_id, topic_id, topic.origin, topic.confidence),
        )


def _mark_duplicate(conn: Conn, question_id: object, digest: str | None) -> int:
    """Mesma questão já carregada de outra prova → `duplicate_of` aponta para a mais antiga."""
    if digest is None:
        conn.execute("update question set duplicate_of = null where id = %s", (question_id,))
        return 0
    row = conn.execute(
        """select id from question
            where statement_hash = %s and id <> %s and duplicate_of is null
              and publish_status <> 'review'
            order by created_at, id limit 1""",
        (digest, question_id),
    ).fetchone()
    original = row[0] if row else None
    conn.execute("update question set duplicate_of = %s where id = %s", (original, question_id))
    return 1 if original else 0
