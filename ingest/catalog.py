"""Catálogo curado de bancas, órgãos e cargos (`db/catalog.yaml`, decisão 0005)."""

from pathlib import Path
from typing import Literal

import psycopg
import yaml
from pydantic import BaseModel, ConfigDict

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
    positions: list[Position] = []


class Catalog(_Strict):
    exam_boards: list[ExamBoard]
    agencies: list[Agency]


def load(path: Path = CATALOG_FILE) -> Catalog:
    return Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


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
