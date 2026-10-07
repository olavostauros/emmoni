"""Modelos do staging (`data/staging/<concurso>/<prova>/`), comuns a todas as etapas."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["multiple_choice", "true_false", "essay"]
AnswerMark = Literal["A", "B", "C", "D", "E", "X"]  # X = anulada


class RawPassage(BaseModel):
    key: str  # rótulo da banca ("2A1-I") ou "g<primeiro item>" para situações sem rótulo
    body_md: str
    page: int
    flags: list[str] = []  # motivos para revisão (figura, fórmula...)


class RawOption(BaseModel):
    letter: Literal["A", "B", "C", "D", "E"]
    body_md: str


class RawQuestion(BaseModel):
    number: int = Field(gt=0)
    type: QuestionType
    statement_md: str
    options: list[RawOption] = []
    passage_key: str | None = None
    page: int
    flags: list[str] = []


class Segmented(BaseModel):
    parser: str  # "<banca>-parser@<versão>", vai para question.extracted_by
    passages: list[RawPassage]
    questions: list[RawQuestion]


class AnswerKey(BaseModel):
    """Gabarito de uma prova: número → letra (C/E ou A–E), X = anulada."""

    answers: dict[int, AnswerMark]


def write(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=1), encoding="utf-8")
