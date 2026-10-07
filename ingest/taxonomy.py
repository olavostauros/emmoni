"""Taxonomia curada em db/taxonomy/*.yaml (SPECIFICATIONS.md §4.4).

Formato de cada arquivo:

    subject: direito-penal
    name: Direito Penal
    topics:
      - slug: crimes-contra-o-patrimonio
        name: Crimes contra o patrimônio
        children:
          - {slug: furto, name: Furto}

O caminho de um assunto é o slug da disciplina seguido dos slugs dos ancestrais, com '-' trocado
por '_': `direito_penal.crimes_contra_o_patrimonio.furto`.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
import yaml

TAXONOMY_DIR = Path(__file__).resolve().parent.parent / "db" / "taxonomy"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class TaxonomyError(ValueError):
    pass


@dataclass(frozen=True)
class Topic:
    path: str
    name: str


@dataclass(frozen=True)
class Subject:
    slug: str
    name: str
    topics: list[Topic]  # pais antes dos filhos


@dataclass
class SyncReport:
    subjects: int = 0
    topics: int = 0
    # Assuntos no banco que não estão mais nos arquivos. Não são apagados: podem ter questões.
    orphans: list[str] = field(default_factory=list)


def label(slug: str) -> str:
    return slug.replace("-", "_")


def _slug(value: Any, where: str) -> str:
    if not isinstance(value, str) or not SLUG.match(value):
        raise TaxonomyError(f"{where}: slug inválido {value!r}")
    return value


def _name(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaxonomyError(f"{where}: nome ausente")
    return value.strip()


def parse(source: Path) -> Subject:
    data = yaml.safe_load(source.read_text())
    if not isinstance(data, dict) or set(data) - {"subject", "name", "topics"}:
        raise TaxonomyError(f"{source.name}: esperado subject, name e topics")
    slug = _slug(data.get("subject"), source.name)
    topics: list[Topic] = []

    def walk(nodes: Any, parent: str) -> None:
        if not isinstance(nodes, list):
            raise TaxonomyError(f"{source.name}: {parent}: topics/children deve ser uma lista")
        for node in nodes:
            if not isinstance(node, dict) or set(node) - {"slug", "name", "children"}:
                raise TaxonomyError(f"{source.name}: {parent}: esperado slug, name e children")
            path = f"{parent}.{label(_slug(node.get('slug'), f'{source.name}: {parent}'))}"
            if any(t.path == path for t in topics):
                raise TaxonomyError(f"{source.name}: assunto repetido {path}")
            topics.append(Topic(path, _name(node.get("name"), f"{source.name}: {path}")))
            walk(node.get("children", []), path)

    walk(data.get("topics", []), label(slug))
    return Subject(slug, _name(data.get("name"), source.name), topics)


def load_dir(directory: Path = TAXONOMY_DIR) -> list[Subject]:
    subjects = [parse(path) for path in sorted(directory.glob("*.yaml"))]
    slugs = [s.slug for s in subjects]
    if len(slugs) != len(set(slugs)):
        raise TaxonomyError("disciplina repetida em mais de um arquivo")
    return subjects


def sync(conn: psycopg.Connection[tuple[object, ...]], subjects: list[Subject]) -> SyncReport:
    """Insere ou atualiza disciplinas e assuntos por slug/caminho. Idempotente."""
    report = SyncReport()
    with conn.transaction(), conn.cursor() as cur:
        for subject in subjects:
            cur.execute(
                "insert into subject (slug, name) values (%s, %s)"
                " on conflict (slug) do update set name = excluded.name"
                " where subject.name is distinct from excluded.name"
                " returning id",
                (subject.slug, subject.name),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute("select id from subject where slug = %s", (subject.slug,))
                row = cur.fetchone()
            assert row is not None
            subject_id = row[0]
            report.subjects += 1
            for topic in subject.topics:
                cur.execute(
                    "insert into topic (subject_id, path, name) values (%s, %s::ext.ltree, %s)"
                    " on conflict (path) do update set name = excluded.name"
                    " where topic.name is distinct from excluded.name",
                    (subject_id, topic.path, topic.name),
                )
                report.topics += 1
            cur.execute(
                "select path::text from topic where subject_id = %s"
                " and not path::text = any(%s) order by path",
                (subject_id, [t.path for t in subject.topics]),
            )
            report.orphans += [str(r[0]) for r in cur.fetchall()]
    return report
