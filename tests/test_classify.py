"""Etapa classify: respostas do agente em arquivo, sem API (SPECIFICATIONS.md §7.4, §9)."""

import json
from pathlib import Path
from typing import Any

import pytest

from ingest import classify, taxonomy
from ingest.staging import RawPassage
from ingest.validate import StagedQuestion, Validated


def _question(number: int, subject: str | None = "lingua-portuguesa", **kw: Any) -> StagedQuestion:
    data: dict[str, Any] = {
        "number": number,
        "type": "true_false",
        "statement_md": f"Com relação ao texto, julgue o item.\n\nItem {number}.",
        "options": [],
        "passage_key": None,
        "page": 1,
        "subject": subject,
        "answer_preliminary": None,
        "answer_final": "C",
        "answer_status": "valid",
        "review_reasons": [],
        "extracted_by": "teste@1",
    }
    data.update(kw)
    return StagedQuestion.model_validate(data)


def _answers(raw: dict[str, Any]) -> dict[int, classify.Answer]:
    return {int(k): classify.Answer.model_validate(v) for k, v in raw.items()}


@pytest.fixture(scope="module")
def subjects() -> dict[str, taxonomy.Subject]:
    return {s.slug: s for s in taxonomy.load_dir(taxonomy.TAXONOMY_DIR)}


def test_tasks_carry_subject_topics_and_text(subjects: dict[str, taxonomy.Subject]) -> None:
    task = classify.task_for(_question(1), "Texto-base longo.", subjects["lingua-portuguesa"])
    assert task.allowed_topics and all(
        p.startswith("lingua_portuguesa") for p in task.allowed_topics
    )
    assert task.subject_name == "Língua Portuguesa"
    assert task.passage_md == "Texto-base longo." and "Item 1." in task.statement_md
    doc = classify.tasks_document([task])
    assert doc.prompt == classify.PROMPT_NAME and "1 a 3 assuntos" in doc.instructions
    assert doc.answers_file == classify.ANSWERS_FILE and doc.tasks == [task]


def test_classify_accepts_confident_topics_and_flags_the_rest(
    subjects: dict[str, taxonomy.Subject],
) -> None:
    answers = _answers(
        {
            "1": {
                "topics": [{"path": "lingua_portuguesa.pontuacao", "confidence": 0.92}],
                "suggested_topic": "",
            },
            "2": {
                "topics": [{"path": "lingua_portuguesa.crase", "confidence": 0.3}],
                "suggested_topic": "Semântica",
            },
        }
    )
    validated = Validated(
        exam_reasons=[],
        passages=[RawPassage(key="t", body_md="x", page=1)],
        questions=[_question(1), _question(2), _question(3, subject=None), _question(4)],
    )
    result, pending = classify.classify(validated, subjects, answers, classifier="eu")
    assert result.model == "eu" and result.prompt == classify.PROMPT_NAME
    assert [t.path for t in result.topics[1]] == ["lingua_portuguesa.pontuacao"]
    # Sem assunto confiante: não é revisão (lacuna da taxonomia, decisão 0010); fica sem assunto
    # e volta às tarefas, com a sugestão registrada.
    assert 2 not in result.topics and result.review == {}
    assert "confiança" in result.unresolved[2]
    assert result.suggestions == {2: "Semântica"}
    # Sem disciplina não vira tarefa; sem resposta vira tarefa (e fica draft no load).
    assert [t.number for t in pending] == [2, 4]

    # Rerodar com as mesmas respostas dá o mesmo resultado.
    again, _ = classify.classify(validated, subjects, answers, classifier="eu")
    assert again == result


def test_paths_outside_the_subject_are_rejected(subjects: dict[str, taxonomy.Subject]) -> None:
    validated = Validated(exam_reasons=[], passages=[], questions=[_question(1)])
    answers = _answers(
        {"1": {"topics": [{"path": "direito_penal.x", "confidence": 1.0}], "suggested_topic": ""}}
    )
    result, pending = classify.classify(validated, subjects, answers)
    assert result.topics == {} and "fora da disciplina" in result.review[1] and pending == []


def test_read_answers_validates_the_file(tmp_path: Path) -> None:
    path = tmp_path / classify.ANSWERS_FILE
    assert classify.read_answers(path) == {}  # ainda não existe

    path.write_text(json.dumps({"7": {"topics": [{"path": "a.b", "confidence": 0.8}]}}))
    assert classify.read_answers(path) == {
        7: classify.Answer(topics=[classify.TopicAnswer(path="a.b", confidence=0.8)])
    }

    path.write_text(json.dumps({"7": {"topics": [{"path": "a.b", "confidence": 1.5}]}}))
    with pytest.raises(RuntimeError, match="questão 7"):
        classify.read_answers(path)

    path.write_text(json.dumps({"sete": {"topics": []}}))
    with pytest.raises(RuntimeError, match="sete"):
        classify.read_answers(path)
