"""Manifestos, catálogo, validate e load (SPECIFICATIONS.md §7.2, §7.3, §9)."""

from pathlib import Path

import psycopg
import pytest

from ingest import catalog, manifest, taxonomy
from ingest.extract import extract
from ingest.load import DocumentIds, LoadError, TopicAssignment, load_exam
from ingest.manifest import Manifest
from ingest.parsers import cebraspe
from ingest.staging import AnswerKey, RawOption, RawQuestion, Segmented
from ingest.validate import validate
from tests.factories import scalar

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures/pdf/cebraspe"
Conn = psycopg.Connection[tuple[object, ...]]

# --- manifestos -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", sorted(manifest.MANIFESTS_DIR.glob("*.yaml")), ids=lambda p: p.stem
)
def test_manifests_are_valid_and_use_known_slugs(path: Path) -> None:
    loaded = manifest.load(path)
    assert loaded.contest == path.stem
    known = catalog.load()
    agencies = {a.slug: a for a in known.agencies}
    assert loaded.exam_board in {b.slug for b in known.exam_boards}
    assert loaded.agency in agencies
    positions = {p.slug for p in agencies[loaded.agency].positions}
    subjects = {s.slug for s in taxonomy.load_dir(taxonomy.TAXONOMY_DIR)}
    for exam in loaded.exams:
        assert set(exam.positions) <= positions
        assert {r.subject for r in exam.subjects_by_range} <= subjects
        for url in (exam.documents.exam, exam.documents.answer_key_final):
            assert url is None or url.startswith("https://")


def test_manifest_requires_an_answer_key() -> None:
    with pytest.raises(ValueError, match="gabarito"):
        manifest.Documents(exam="https://x/prova.pdf")


# --- validate ---------------------------------------------------------------------------------


def _manifest() -> Manifest:
    return Manifest.model_validate(
        {
            "contest": "zz-pf-2021",
            "name": "PF 2021 (teste)",
            "agency": "pf",
            "exam_board": "cebraspe",
            "year": 2021,
            "exams": [
                {
                    "slug": "agente",
                    "name": "Agente",
                    "positions": ["agente"],
                    "documents": {"exam": "https://x/p.pdf", "answer_key_final": "https://x/g.pdf"},
                    "subjects_by_range": [
                        {"from": 1, "to": 24, "subject": "lingua-portuguesa"},
                        {"from": 25, "to": 27, "subject": "direito-administrativo"},
                        {"from": 28, "to": 30, "subject": "direito-constitucional"},
                    ],
                }
            ],
        }
    )


def _tf(number: int, **fields: object) -> RawQuestion:
    data: dict[str, object] = {
        "number": number,
        "type": "true_false",
        "statement_md": f"Item {number}.",
        "page": 1,
    }
    data.update(fields)
    return RawQuestion.model_validate(data)


def _segmented(*questions: RawQuestion) -> Segmented:
    return Segmented(parser="teste@1", passages=[], questions=list(questions))


def test_validate_derives_answer_status() -> None:
    exam = _manifest().exams[0]
    seg = _segmented(_tf(1), _tf(2), _tf(3))
    pre = AnswerKey(answers={1: "C", 2: "C", 3: "E"})
    fin = AnswerKey(answers={1: "C", 2: "E", 3: "X"})
    q1, q2, q3 = validate(exam, seg, pre, fin).questions
    assert (q1.answer_status, q1.answer_final) == ("valid", "C")
    assert (q2.answer_status, q2.answer_preliminary, q2.answer_final) == ("changed", "C", "E")
    assert (q3.answer_status, q3.answer_final) == ("annulled", None)
    assert not (q1.review_reasons or q2.review_reasons or q3.review_reasons)


def test_validate_records_reasons_instead_of_dropping() -> None:
    exam = _manifest().exams[0]
    seg = _segmented(
        _tf(1, flags=["figure"]),
        _tf(2, options=[{"letter": "A", "body_md": "x"}]),
        _tf(3, statement_md=" "),
    )
    fin = AnswerKey(answers={1: "C", 2: "C", 3: "A"})
    q1, q2, q3 = validate(exam, seg, None, fin).questions
    assert q1.review_reasons == ["figura ou tabela não extraída"]
    assert "certo/errado com alternativas" in q2.review_reasons
    assert "enunciado vazio" in q3.review_reasons
    assert "gabarito 'A' inválido para certo/errado" in q3.review_reasons


def test_validate_multiple_choice_rules() -> None:
    exam = _manifest().exams[0]
    four = [RawOption(letter=letter, body_md=letter.lower()) for letter in "ABCD"]  # type: ignore[arg-type]
    seg = _segmented(
        RawQuestion(number=1, type="multiple_choice", statement_md="?", options=four, page=1),
        RawQuestion(number=2, type="multiple_choice", statement_md="?", options=four[:3], page=1),
    )
    q1, q2 = validate(exam, seg, None, AnswerKey(answers={1: "E", 2: "A"})).questions
    assert "gabarito 'E' sem alternativa correspondente" in q1.review_reasons
    assert "múltipla escolha com 3 alternativas" in q2.review_reasons


def test_validate_exam_level_problems() -> None:
    exam = _manifest().exams[0]
    seg = _segmented(_tf(1), _tf(3))
    result = validate(exam, seg, None, AnswerKey(answers={1: "C", 2: "E", 3: "C"}))
    assert any("numeração" in reason for reason in result.exam_reasons)
    assert any("gabarito definitivo" in reason for reason in result.exam_reasons)


def test_validate_without_final_key_or_subject() -> None:
    exam = _manifest().exams[0]
    (q,) = validate(exam, _segmented(_tf(1)), AnswerKey(answers={1: "C"}), None).questions
    assert "sem gabarito definitivo" in q.review_reasons
    exam.subjects_by_range = []
    (q,) = validate(exam, _segmented(_tf(1)), None, AnswerKey(answers={1: "C"})).questions
    assert "sem disciplina no manifesto" in q.review_reasons


# --- catálogo e load (banco de testes) ---------------------------------------------------------


@pytest.fixture
def tx(ingest: Conn) -> Conn:
    """Conexão do papel de ingestão; tudo é desfeito no fim do teste."""
    yield ingest  # type: ignore[misc]
    ingest.rollback()


def test_catalog_sync_is_idempotent(tx: Conn) -> None:
    loaded = catalog.load()
    catalog.sync(tx, loaded)
    before = scalar(tx, "select count(*) from position")
    catalog.sync(tx, loaded)
    assert scalar(tx, "select count(*) from position") == before
    assert (
        scalar(
            tx,
            "select p.name from position p join agency a on a.id = p.agency_id"
            " where a.slug = 'pf' and p.slug = 'escrivao'",
        )
        == "Escrivão de Polícia Federal"
    )


def _documents(tx: Conn) -> DocumentIds:
    ids = []
    for n, kind in enumerate(("exam", "answer_key_final")):
        ids.append(
            scalar(
                tx,
                "insert into source_document (kind, url, sha256, fetched_at)"
                " values (%s, %s, %s, now()) returning id",
                (kind, f"https://x/{kind}.pdf", f"{n + 1:064x}"),
            )
        )
    return DocumentIds(ids[0], None, ids[1])


@pytest.fixture(scope="module")
def real_exam() -> tuple[Segmented, AnswerKey]:
    segmented = cebraspe.segment(extract(FIXTURES / "pf-2021-agente-p2-3.pdf"))
    key = cebraspe.parse_answer_key(extract(FIXTURES / "pf-2021-agente-gabarito-definitivo.pdf"))
    key = AnswerKey(answers={n: m for n, m in key.answers.items() if n <= 30})
    return segmented, key


def _state(tx: Conn) -> list[tuple[object, ...]]:
    return tx.execute(
        """select q.id, q.number, q.passage_id, q.publish_status, q.answer_final, q.answer_status,
                  q.statement_hash, p.source_key
             from question q join exam e on e.id = q.exam_id
             join contest c on c.id = e.contest_id
             left join passage p on p.id = q.passage_id
            where c.slug = 'zz-pf-2021' order by q.number"""
    ).fetchall()


def test_load_is_idempotent_and_keeps_ids(tx: Conn, real_exam: tuple[Segmented, AnswerKey]) -> None:
    catalog.sync(tx, catalog.load())
    m = _manifest()
    validated = validate(m.exams[0], real_exam[0], None, real_exam[1])
    docs = _documents(tx)
    topics = {1: [TopicAssignment("lingua_portuguesa.interpretacao_de_texto", "llm", 0.9)]}
    first = load_exam(tx, m, m.exams[0], docs, validated, topics)
    state = _state(tx)
    second = load_exam(tx, m, m.exams[0], docs, validated, topics)
    assert _state(tx) == state
    assert first == second
    assert first.questions == 30 and first.removed == 0
    rows = {row[1]: row for row in state}
    assert rows[1][3] == "published"  # sem pendência e com assunto
    assert rows[2][3] == "draft"  # sem assunto
    assert rows[28][5] == "annulled" and rows[28][4] is None
    assert rows[1][7] == "2A1-I" and rows[25][7] == "g25"
    assert (
        scalar(
            tx,
            "select publish_status from exam e join contest c on c.id = e.contest_id"
            " where c.slug = 'zz-pf-2021'",
        )
        == "draft"
    )  # a prova só é publicada depois da amostragem


def test_load_marks_duplicates_and_removes_stale_questions(
    tx: Conn, real_exam: tuple[Segmented, AnswerKey]
) -> None:
    catalog.sync(tx, catalog.load())
    m = _manifest()
    validated = validate(m.exams[0], real_exam[0], None, real_exam[1])
    load_exam(tx, m, m.exams[0], _documents(tx), validated)
    # A mesma prova carregada em outro concurso: todas viram duplicatas da primeira.
    other = m.model_copy(update={"contest": "zz-pf-2021-copia"})
    report = load_exam(tx, other, m.exams[0], _documents_again(tx), validated)
    assert report.duplicates == 30
    # Recarregar com menos questões remove as que sobraram.
    shorter = validated.model_copy(update={"questions": validated.questions[:10]})
    assert load_exam(tx, m, m.exams[0], _documents_again(tx), shorter).removed == 20


def _documents_again(tx: Conn) -> DocumentIds:
    exam_doc, key_doc = (
        scalar(tx, "select id from source_document where url = %s", (f"https://x/{kind}.pdf",))
        for kind in ("exam", "answer_key_final")
    )
    return DocumentIds(exam_doc, None, key_doc)


def test_load_refuses_exam_level_problems(tx: Conn) -> None:
    m = _manifest()
    validated = validate(
        m.exams[0], _segmented(_tf(1), _tf(3)), None, AnswerKey(answers={1: "C", 3: "C"})
    )
    with pytest.raises(LoadError, match="numeração"):
        load_exam(tx, m, m.exams[0], _documents(tx), validated)
