"""`emmoni coverage`: relatório de cobertura em `docs/coverage.md` (SPECIFICATION.md §8).

- questões publicadas (as visíveis no esquema `api`: questão e prova publicadas, sem duplicatas)
  por banca × órgão × ano e por disciplina;
- provas dos manifestos aprovados que ainda não estão no banco, e as carregadas sem publicação;
- propostas do crawler pendentes de aprovação;
- por fonte, a última requisição do crawler e os hosts que responderam 403/429.
"""

import datetime
from dataclasses import dataclass
from pathlib import Path

import psycopg

from ingest import manifest, proposals

Conn = psycopg.Connection[tuple[object, ...]]
COVERAGE_FILE = Path(__file__).parent.parent / "docs" / "coverage.md"
VISIBLE = """q.publish_status = 'published' and e.publish_status = 'published'
             and q.duplicate_of is null and c.slug not like 'seed-%%'"""
BLOCKED_STATUSES = (403, 429)


@dataclass(frozen=True)
class Coverage:
    generated_at: datetime.datetime
    by_board_agency_year: list[
        tuple[str, str, int, int, int]
    ]  # banca, órgão, ano, provas, questões
    by_subject: list[tuple[str, int]]
    not_loaded: list[tuple[str, str]]  # concurso, prova
    not_published: list[tuple[str, str, str]]  # concurso, prova, status
    pending: list[str]
    sources: list[
        tuple[str, datetime.datetime | None, int, list[str]]
    ]  # fonte, última, páginas, bloqueios

    @property
    def total(self) -> int:
        return sum(row[4] for row in self.by_board_agency_year)


def collect(conn: Conn, manifests_dir: Path = manifest.MANIFESTS_DIR) -> Coverage:
    by_group = conn.execute(
        f"""select b.short_name, a.short_name, c.year, count(distinct e.id), count(*)
              from question q
              join exam e on e.id = q.exam_id
              join contest c on c.id = e.contest_id
              join exam_board b on b.id = c.exam_board_id
              join agency a on a.id = c.agency_id
             where {VISIBLE}
             group by 1, 2, 3 order by 1, 2, 3"""
    ).fetchall()
    by_subject = conn.execute(
        f"""select s.name, count(*)
              from question q
              join exam e on e.id = q.exam_id
              join contest c on c.id = e.contest_id
              join subject s on s.id = q.subject_id
             where {VISIBLE}
             group by 1 order by 2 desc, 1"""
    ).fetchall()
    loaded = {
        (str(r[0]), str(r[1])): str(r[2])
        for r in conn.execute(
            """select c.slug, e.slug, e.publish_status::text
                 from exam e join contest c on c.id = e.contest_id"""
        ).fetchall()
    }
    not_loaded = []
    for path in sorted(manifests_dir.glob("*.yaml")):
        approved = manifest.load(path)
        not_loaded += [
            (approved.contest, exam.slug)
            for exam in approved.exams
            if (approved.contest, exam.slug) not in loaded
        ]
    not_published = sorted(
        (contest, exam, status)
        for (contest, exam), status in loaded.items()
        if status != "published" and not contest.startswith("seed-")
    )
    pending = [path.stem for path in proposals.list_pending(manifests_dir)]
    sources = [
        (
            str(r[0]),
            r[1] if isinstance(r[1], datetime.datetime) else None,
            int(str(r[2])),
            list(r[3]),  # type: ignore[call-overload]
        )
        for r in conn.execute(
            """select source_slug, max(last_fetched_at), count(*),
                      coalesce(array_agg(distinct split_part(url, '/', 3) order by split_part(url, '/', 3))
                                 filter (where http_status = any(%s)), '{}')
                 from crawl.page group by 1 order by 1""",
            (list(BLOCKED_STATUSES),),
        ).fetchall()
    ]
    return Coverage(
        generated_at=datetime.datetime.now(datetime.UTC),
        by_board_agency_year=[
            (str(r[0]), str(r[1]), int(str(r[2])), int(str(r[3])), int(str(r[4]))) for r in by_group
        ],
        by_subject=[(str(r[0]), int(str(r[1]))) for r in by_subject],
        not_loaded=not_loaded,
        not_published=not_published,
        pending=pending,
        sources=sources,
    )


def render(cov: Coverage) -> str:
    lines = [
        "# Cobertura",
        "",
        f"Gerado por `emmoni coverage` em {cov.generated_at:%Y-%m-%d %H:%M} UTC. Não edite à mão.",
        "",
        f"**{cov.total} questões publicadas** (visíveis no esquema `api`, sem duplicatas e sem o"
        " seed).",
        "",
        "## Por banca, órgão e ano",
        "",
        "| Banca | Órgão | Ano | Provas | Questões |",
        "|---|---|---:|---:|---:|",
    ]
    lines += [f"| {b} | {a} | {y} | {e} | {q} |" for b, a, y, e, q in cov.by_board_agency_year]
    lines += ["", "## Por disciplina", "", "| Disciplina | Questões |", "|---|---:|"]
    lines += [f"| {s} | {n} |" for s, n in cov.by_subject]
    lines += ["", "## Provas de manifestos aprovados fora do banco", ""]
    lines += [f"- `{c}/{e}`" for c, e in cov.not_loaded] or ["Nenhuma."]
    lines += ["", "## Provas carregadas e não publicadas", ""]
    lines += [f"- `{c}/{e}` ({s})" for c, e, s in cov.not_published] or ["Nenhuma."]
    lines += ["", "## Propostas do crawler pendentes", ""]
    lines += [f"- `{p}`" for p in cov.pending] or ["Nenhuma."]
    lines += [
        "",
        "## Crawler por fonte",
        "",
        "| Fonte | Última requisição (UTC) | Páginas | Hosts com 403/429 |",
        "|---|---|---:|---|",
    ]
    lines += [
        f"| {s} | {last:%Y-%m-%d %H:%M} | {pages} | {', '.join(blocked) or '—'} |"
        if last
        else f"| {s} | — | {pages} | {', '.join(blocked) or '—'} |"
        for s, last, pages, blocked in cov.sources
    ]
    return "\n".join(lines) + "\n"


def write(conn: Conn, path: Path = COVERAGE_FILE) -> Coverage:
    cov = collect(conn)
    path.write_text(render(cov), encoding="utf-8")
    return cov
