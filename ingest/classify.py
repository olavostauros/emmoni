"""Etapa `classify`: questões → assuntos da taxonomia, classificadas pelo agente (SPECIFICATIONS.md
§7.3, §7.4; decisão 0006).

Não há chamada a API nenhuma. A etapa trabalha com dois arquivos no staging da prova:

- `classify-tasks.json` (saída da etapa): as questões que ainda não têm resposta, cada uma com a
  disciplina, os assuntos permitidos e o texto a classificar, mais as instruções
  (`ingest/prompts/classify@1.md`). O agente lê este arquivo e classifica.
- `classify-answers.json` (entrada da etapa, escrita pelo agente): respostas por número de questão,
  no formato `{"12": {"topics": [{"path": ..., "confidence": ...}], "suggested_topic": ""}}`.

A disciplina vem do manifesto; só são aceitos assuntos **dessa** disciplina que existam em
`db/taxonomy/`. Resposta inválida (assunto de outra disciplina, confiança fora de [0, 1]) é
rejeitada e a questão fica `review` com o motivo. Confiança < 0,6 → `review`. Sem resposta → a
questão fica `draft` no `load`. As respostas ficam no staging: reprocessar não repete trabalho.
"""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ingest.taxonomy import Subject
from ingest.validate import StagedQuestion, Validated

PROMPT_NAME = "classify@1"
PROMPT_FILE = Path(__file__).with_name("prompts") / f"{PROMPT_NAME}.md"
DEFAULT_CLASSIFIER = "agent"
MIN_CONFIDENCE = 0.6
MAX_TOPICS = 3
MAX_PASSAGE_CHARS = 6000
TASKS_FILE = "classify-tasks.json"
ANSWERS_FILE = "classify-answers.json"


class Assigned(BaseModel):
    path: str
    origin: str = "llm"
    confidence: float


class Classified(BaseModel):
    """`topics.json`: assuntos aceitos e pendências por número de questão."""

    model: str  # quem classificou (`EMMONI_CLASSIFIER`), gravado para rastreabilidade
    prompt: str
    topics: dict[int, list[Assigned]]
    review: dict[int, str]  # número → motivo
    suggestions: dict[int, str]  # número → assunto sugerido (para curadoria da taxonomia)


class TopicAnswer(BaseModel):
    path: str
    confidence: float = Field(ge=0, le=1)


class Answer(BaseModel):
    """Uma resposta em `classify-answers.json`."""

    topics: list[TopicAnswer]
    suggested_topic: str = ""


class Task(BaseModel):
    """Uma questão a classificar em `classify-tasks.json`."""

    number: int
    subject: str
    subject_name: str
    allowed_topics: dict[str, str]  # path → nome
    passage_md: str | None
    statement_md: str


class Tasks(BaseModel):
    prompt: str
    instructions: str
    answers_file: str
    answer_format: dict[str, Any]
    tasks: list[Task]


def classifier_name() -> str:
    return os.environ.get("EMMONI_CLASSIFIER") or DEFAULT_CLASSIFIER


def task_for(question: StagedQuestion, passage: str | None, subject: Subject) -> Task:
    return Task(
        number=question.number,
        subject=subject.slug,
        subject_name=subject.name,
        allowed_topics={t.path: t.name for t in subject.topics},
        passage_md=passage[:MAX_PASSAGE_CHARS] if passage else None,
        statement_md=question.statement_md,
    )


def read_answers(path: Path) -> dict[int, Answer]:
    """Lê `classify-answers.json`; chave inválida ou resposta malformada derruba a etapa."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"{path.name}: esperado um objeto {{número: resposta}}")
    answers: dict[int, Answer] = {}
    for key, value in raw.items():
        try:
            answers[int(key)] = Answer.model_validate(value)
        except (ValueError, ValidationError) as error:
            raise RuntimeError(
                f"{path.name}: resposta inválida para a questão {key}: {error}"
            ) from error
    return answers


def classify(
    validated: Validated,
    subjects: dict[str, Subject],
    answers: dict[int, Answer],
    classifier: str | None = None,
) -> tuple[Classified, list[Task]]:
    """Aplica as respostas existentes e devolve as tarefas que ainda faltam."""
    classifier = classifier or classifier_name()
    passages = {p.key: p.body_md for p in validated.passages}
    result = Classified(model=classifier, prompt=PROMPT_NAME, topics={}, review={}, suggestions={})
    pending: list[Task] = []
    for question in validated.questions:
        if question.subject is None or question.subject not in subjects:
            continue
        subject = subjects[question.subject]
        if not subject.topics:
            result.review[question.number] = "disciplina sem assuntos na taxonomia"
            continue
        answer = answers.get(question.number)
        if answer is None:
            passage = passages.get(question.passage_key) if question.passage_key else None
            pending.append(task_for(question, passage, subject))
            continue
        allowed = {t.path for t in subject.topics}
        outside = [t.path for t in answer.topics if t.path not in allowed]
        if outside:
            result.review[question.number] = (
                f"classificação com assunto fora da disciplina {subject.slug}: {', '.join(outside)}"
            )
        else:
            accepted = [
                Assigned(path=t.path, confidence=t.confidence)
                for t in answer.topics
                if t.confidence >= MIN_CONFIDENCE
            ]
            if accepted:
                result.topics[question.number] = accepted[:MAX_TOPICS]
            else:
                result.review[question.number] = (
                    f"classificação com confiança abaixo de {MIN_CONFIDENCE} (assunto)"
                )
        if answer.suggested_topic:
            result.suggestions[question.number] = answer.suggested_topic
    return result, pending


def tasks_document(pending: list[Task]) -> Tasks:
    return Tasks(
        prompt=PROMPT_NAME,
        instructions=PROMPT_FILE.read_text(encoding="utf-8"),
        answers_file=ANSWERS_FILE,
        answer_format={
            "<número>": {
                "topics": [{"path": "<path em allowed_topics>", "confidence": "<0 a 1>"}],
                "suggested_topic": "<nome de assunto que falta na lista, ou vazio>",
            }
        },
        tasks=pending,
    )
