"""Manifesto de concurso (`ingest/manifests/<concurso>.yaml`, SPECIFICATION.md §7.2)."""

import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

MANIFESTS_DIR = Path(__file__).with_name("manifests")
SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Documents(_Strict):
    exam: str
    # Um gabarito pode vir em mais de um PDF (PCDF 2019: um caderno, gabaritos de básicos e de
    # específicos separados): lista de URLs, na ordem dos itens (decisão 0009).
    answer_key_preliminary: str | list[str] | None = None
    answer_key_final: str | list[str] | None = None

    @model_validator(mode="after")
    def _needs_key(self) -> "Documents":
        if not (self.answer_key_preliminary or self.answer_key_final):
            raise ValueError("a prova precisa de ao menos um gabarito")
        return self

    def urls(self, kind: str) -> list[str]:
        """URLs do tipo (`exam`, `answer_key_preliminary`, `answer_key_final`), na ordem."""
        value = getattr(self, kind)
        if value is None:
            return []
        return [value] if isinstance(value, str) else list(value)


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
    # Negrito/itálico das fontes sem nome ("TT…o00") deduzidos pelas larguras no caderno (decisão
    # 0020, emenda de 2026-10-13). Por prova: ligar muda o texto de provas já aprovadas, que então
    # precisam de reprocessamento e amostra nova.
    infer_font_styles: bool = False
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
    # Preenchido pelo crawler nas propostas (SPECIFICATION.md §7.1): de onde veio cada campo e com
    # que confiança. O pipeline ignora; pode ficar no manifesto aprovado ou ser apagado.
    evidence: dict[str, Any] = {}

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
