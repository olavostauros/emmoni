"""Catálogo curado de bancas, órgãos e cargos (`db/catalog.yaml`, decisão 0005)."""

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import psycopg
import yaml
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from ingest.manifest import Manifest

CATALOG_FILE = Path(__file__).resolve().parent.parent / "db" / "catalog.yaml"

Career = Literal[
    "pf",
    "prf",
    "policia_civil",
    "policia_militar",
    "bombeiro_militar",
    "policia_penal",
    "policia_legislativa",
    "guarda_municipal",
    "outra",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExamBoard(_Strict):
    slug: str
    name: str
    short_name: str


class Position(_Strict):
    slug: str
    name: str
    education_level: Literal["fundamental", "medio", "superior"] | None = None


class Agency(_Strict):
    slug: str
    name: str
    short_name: str
    career: Career
    level: Literal["federal", "estadual", "distrital", "municipal"]
    state: str | None = None
    # Como as fontes escrevem o órgão nas URLs e nos nomes de evento (ex.: PF_21, DPF_14, PC_DF_20):
    # prefixos em maiúsculas, com `_` separando as partes. Só o crawler usa (decisão 0007).
    aliases: list[str] = []
    positions: list[Position] = []


class Catalog(_Strict):
    exam_boards: list[ExamBoard]
    agencies: list[Agency]


def load(path: Path = CATALOG_FILE) -> Catalog:
    return Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def agency_by_slug(catalog: Catalog, slug: str) -> Agency | None:
    return next((a for a in catalog.agencies if a.slug == slug), None)


def manifest_problems(catalog: Catalog, manifest: "Manifest") -> list[str]:
    """Slugs do manifesto que não existem no catálogo (banca, órgão, cargos)."""
    problems = []
    if manifest.exam_board not in {b.slug for b in catalog.exam_boards}:
        problems.append(f"banca {manifest.exam_board!r} não está no catálogo")
    agency = agency_by_slug(catalog, manifest.agency)
    if agency is None:
        return [*problems, f"órgão {manifest.agency!r} não está no catálogo"]
    known = {p.slug for p in agency.positions}
    for exam in manifest.exams:
        for position in exam.positions:
            if position not in known:
                problems.append(
                    f"prova {exam.slug}: cargo {position!r} não existe em {agency.slug}"
                )
    return problems


def sync(conn: psycopg.Connection[tuple[object, ...]], catalog: Catalog) -> tuple[int, int, int]:
    """Upsert por slug. Devolve (bancas, órgãos, cargos)."""
    positions = 0
    with conn.transaction(), conn.cursor() as cur:
        for board in catalog.exam_boards:
            cur.execute(
                """insert into exam_board (slug, name, short_name) values (%s, %s, %s)
                   on conflict (slug) do update
                     set name = excluded.name, short_name = excluded.short_name""",
                (board.slug, board.name, board.short_name),
            )
        for agency in catalog.agencies:
            cur.execute(
                """insert into agency (slug, name, short_name, career, level, state)
                   values (%s, %s, %s, %s, %s, %s)
                   on conflict (slug) do update
                     set name = excluded.name, short_name = excluded.short_name,
                         career = excluded.career, level = excluded.level, state = excluded.state""",
                (
                    agency.slug,
                    agency.name,
                    agency.short_name,
                    agency.career,
                    agency.level,
                    agency.state,
                ),
            )
            for position in agency.positions:
                cur.execute(
                    """insert into position (agency_id, slug, name, education_level)
                       select id, %s, %s, %s from agency where slug = %s
                       on conflict (agency_id, slug) do update
                         set name = excluded.name, education_level = excluded.education_level""",
                    (position.slug, position.name, position.education_level, agency.slug),
                )
                positions += 1
    return len(catalog.exam_boards), len(catalog.agencies), positions
