"""Manifesto de concurso (`ingest/manifests/<concurso>.yaml`, SPECIFICATIONS.md §7.2)."""

import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

MANIFESTS_DIR = Path(__file__).with_name("manifests")
SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Documents(_Strict):
    exam: str
    answer_key_preliminary: str | None = None
    answer_key_final: str | None = None

    @model_validator(mode="after")
    def _needs_key(self) -> "Documents":
        if not (self.answer_key_preliminary or self.answer_key_final):
            raise ValueError("a prova precisa de ao menos um gabarito")
        return self


class SubjectRange(_Strict):
    from_: int = Field(alias="from", gt=0)
    to: int = Field(gt=0)
    subject: str = Field(pattern=SLUG)


class Exam(_Strict):
    slug: str = Field(pattern=SLUG)
    name: str
    positions: list[str] = Field(min_length=1)
    applied_on: datetime.date | None = None
    shift: str | None = None
    canonical_booklet: str | None = None
    first_number: int = Field(default=1, gt=0)  # caderno que começa no meio (PRF 2021: item 9)
    documents: Documents
    subjects_by_range: list[SubjectRange] = []

    def subject_for(self, number: int) -> str | None:
        for item in self.subjects_by_range:
            if item.from_ <= number <= item.to:
                return item.subject
        return None


class Manifest(_Strict):
    contest: str = Field(pattern=SLUG)
    name: str
    agency: str = Field(pattern=SLUG)
    exam_board: str = Field(pattern=SLUG)
    year: int = Field(ge=1980, le=2100)
    notice_number: str | None = None
    source_url: str | None = None  # página oficial do concurso, para conferência
    exams: list[Exam] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_exams(self) -> "Manifest":
        slugs = [exam.slug for exam in self.exams]
        if len(slugs) != len(set(slugs)):
            raise ValueError("slugs de prova repetidos")
        return self

    def exam(self, slug: str) -> Exam:
        for exam in self.exams:
            if exam.slug == slug:
                return exam
        raise KeyError(f"{self.contest}: prova {slug!r} não está no manifesto")


def load(path: Path) -> Manifest:
    return Manifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def resolve(name: str) -> Path:
    """Aceita caminho ou slug do concurso (`pf-2021`)."""
    path = Path(name)
    if path.suffix in (".yaml", ".yml") and path.exists():
        return path
    return MANIFESTS_DIR / f"{name}.yaml"
