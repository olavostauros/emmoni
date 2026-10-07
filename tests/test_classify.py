"""Etapa classify com respostas gravadas: nenhum teste chama a API (SPECIFICATIONS.md §9)."""

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


@pytest.fixture(scope="module")
def subjects() -> dict[str, taxonomy.Subject]:
    return {s.slug: s for s in taxonomy.load_dir(taxonomy.TAXONOMY_DIR)}


def test_request_restricts_topics_to_the_subject(subjects: dict[str, taxonomy.Subject]) -> None:
    passage = "Texto-base longo."
    params = classify.request_for(_question(1), passage, subjects["lingua-portuguesa"], "modelo-x")
    schema = params["output_config"]["format"]["schema"]
    allowed = schema["properties"]["topics"]["items"]["properties"]["path"]["enum"]
    assert allowed and all(path.startswith("lingua_portuguesa") for path in allowed)
    content = params["messages"][0]["content"]
    assert "Língua Portuguesa" in content and "Texto-base longo." in content
    assert params["model"] == "modelo-x"
    assert "tool_choice" not in params  # Sonnet 5.5 não aceita tool_choice forçado


def test_classify_accepts_confident_topics_and_flags_the_rest(
    tmp_path: Path, subjects: dict[str, taxonomy.Subject]
) -> None:
    answers = {
        1: {
            "topics": [{"path": "lingua_portuguesa.pontuacao", "confidence": 0.92}],
            "suggested_topic": "",
        },
        2: {
            "topics": [{"path": "lingua_portuguesa.crase", "confidence": 0.3}],
            "suggested_topic": "Semântica",
        },
    }
    calls: list[dict[str, Any]] = []

    def fake(params: dict[str, Any]) -> dict[str, Any]:
        calls.append(params)
        number = int(params["messages"][0]["content"].rsplit("Item ", 1)[1].strip().rstrip("."))
        return answers[number]

    validated = Validated(
        exam_reasons=[],
        passages=[RawPassage(key="t", body_md="x", page=1)],
        questions=[_question(1), _question(2), _question(3, subject=None)],
    )
    result = classify.classify(validated, subjects, tmp_path, fake, model="modelo-x")
    assert [t.path for t in result.topics[1]] == ["lingua_portuguesa.pontuacao"]
    assert 2 not in result.topics and "confiança" in result.review[2]
    assert result.suggestions == {2: "Semântica"}
    assert len(calls) == 2  # sem disciplina não vai ao LLM

    # Segunda rodada: tudo vem do cache, nenhuma chamada nova (e funciona sem acesso à API).
    again = classify.classify(validated, subjects, tmp_path, None, model="modelo-x")
    assert again == result and len(calls) == 2


def test_without_api_and_without_cache_it_fails_loudly(
    tmp_path: Path, subjects: dict[str, taxonomy.Subject]
) -> None:
    validated = Validated(exam_reasons=[], passages=[], questions=[_question(1)])
    with pytest.raises(RuntimeError, match="cache"):
        classify.classify(validated, subjects, tmp_path, None, model="modelo-x")


def test_paths_outside_the_subject_are_ignored(
    tmp_path: Path, subjects: dict[str, taxonomy.Subject]
) -> None:
    validated = Validated(exam_reasons=[], passages=[], questions=[_question(1)])
    result = classify.classify(
        validated,
        subjects,
        tmp_path,
        lambda p: {
            "topics": [{"path": "direito_penal.x", "confidence": 1.0}],
            "suggested_topic": "",
        },
        model="modelo-x",
    )
    assert result.topics == {} and 1 in result.review
