"""Etapa `validate`: questões segmentadas + gabaritos → `questions.json` (SPECIFICATIONS.md §7.3).

Nada é descartado: toda regra que falha vira um motivo em `review_reasons`, e a questão é carregada
como `review`. Só questões sem motivo podem ser publicadas.
"""

from typing import Literal

from pydantic import BaseModel

from ingest.manifest import Exam
from ingest.staging import AnswerKey, QuestionType, RawOption, RawPassage, Segmented

AnswerStatus = Literal["valid", "changed", "annulled"]

# Motivos vindos do parser (flags) → texto do motivo.
FLAG_REASONS = {
    "figure": "figura ou tabela não extraída",
    "formula": "fórmula com glifos não mapeados (precisa de LaTeX)",
    "layout": "layout especial (código, tabela, versos ou quebras com significado)",
    "underline": "enunciado cita sublinhado, mas o sublinhado não foi extraído",
    "no_command": "grupo de itens sem comando reconhecido",
    "orphan_text": "texto solto depois do último item (pode ser continuação perdida)",
}


class StagedQuestion(BaseModel):
    number: int
    type: QuestionType
    statement_md: str
    options: list[RawOption]
    passage_key: str | None
    page: int
    subject: str | None
    answer_preliminary: str | None
    answer_final: str | None
    answer_status: AnswerStatus
    review_reasons: list[str]
    extracted_by: str


class Validated(BaseModel):
    exam_reasons: list[str]  # problemas da prova inteira (numeração, gabarito)
    passages: list[RawPassage]
    questions: list[StagedQuestion]


def validate(
    exam: Exam,
    segmented: Segmented,
    preliminary: AnswerKey | None,
    final: AnswerKey | None,
) -> Validated:
    exam_reasons: list[str] = []
    numbers = [q.number for q in segmented.questions]
    if numbers != list(range(1, len(numbers) + 1)):
        exam_reasons.append(f"numeração não contínua: {numbers[:5]}...")
    for name, key in (("preliminar", preliminary), ("definitivo", final)):
        if key is not None and sorted(key.answers) != list(range(1, len(numbers) + 1)):
            exam_reasons.append(
                f"gabarito {name} com {len(key.answers)} itens para {len(numbers)} questões"
            )
    passages = {p.key: p for p in segmented.passages}

    staged = []
    for question in segmented.questions:
        reasons = [FLAG_REASONS.get(flag, flag) for flag in question.flags]
        if question.passage_key:
            passage = passages.get(question.passage_key)
            if passage is None:
                reasons.append(f"texto-base {question.passage_key!r} não encontrado")
            else:
                reasons.extend(
                    f"texto-base: {FLAG_REASONS.get(flag, flag)}"
                    for flag in passage.flags
                    if FLAG_REASONS.get(flag, flag) not in reasons
                )
        if not question.statement_md.strip():
            reasons.append("enunciado vazio")
        subject = exam.subject_for(question.number)
        if subject is None:
            reasons.append("sem disciplina no manifesto")

        pre = _mark(preliminary, question.number)
        fin = _mark(final, question.number)
        reasons.extend(_answer_problems(question.type, question.options, pre, fin))
        status: AnswerStatus = "valid"
        if fin == "X":
            status, fin = "annulled", None
        elif pre and fin and pre != fin and pre != "X":
            status = "changed"
        if pre == "X":
            pre = None
        if fin is None and status != "annulled":
            reasons.append("sem gabarito definitivo")

        staged.append(
            StagedQuestion(
                number=question.number,
                type=question.type,
                statement_md=question.statement_md,
                options=question.options,
                passage_key=question.passage_key,
                page=question.page,
                subject=subject,
                answer_preliminary=pre,
                answer_final=fin,
                answer_status=status,
                review_reasons=sorted(set(reasons)),
                extracted_by=segmented.parser,
            )
        )
    return Validated(exam_reasons=exam_reasons, passages=segmented.passages, questions=staged)


def _mark(key: AnswerKey | None, number: int) -> str | None:
    return key.answers.get(number) if key else None


def _answer_problems(
    qtype: QuestionType, options: list[RawOption], *marks: str | None
) -> list[str]:
    problems = []
    letters = {option.letter for option in options}
    if qtype == "true_false" and options:
        problems.append("certo/errado com alternativas")
    if qtype == "multiple_choice" and len(options) not in (4, 5):
        problems.append(f"múltipla escolha com {len(options)} alternativas")
    for mark in marks:
        if mark is None or mark == "X":
            continue
        if qtype == "true_false" and mark not in ("C", "E"):
            problems.append(f"gabarito {mark!r} inválido para certo/errado")
        if qtype == "multiple_choice" and mark not in letters:
            problems.append(f"gabarito {mark!r} sem alternativa correspondente")
    return problems
