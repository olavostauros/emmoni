"""Mede as funções do contrato com ~100 mil questões (SPECIFICATION.md §6).

Uso: bench.py <url owner> <url web>   (banco descartável, já migrado e com seed)
Multiplica as questões do seed em concursos sintéticos `bench-*` e mede, como emmoni_web,
p50/p95 de api.search_questions e api.facet_counts. Sai com 1 se alguma meta de p95 falhar.
"""

import statistics
import sys
import time
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

CONTESTS = 400
QUESTIONS_PER_EXAM = 250  # 400 × 250 = 100 mil
RUNS = 30
TARGET_MS = {"search_questions": 150.0, "facet_counts": 300.0}

GENERATE = f"""
alter table question disable trigger user;
alter table question_option disable trigger user;

insert into contest (slug, agency_id, exam_board_id, year, name)
select 'bench-' || g,
       (select id from agency order by id offset g % 5 limit 1),
       (select id from exam_board order by id offset g % 3 limit 1),
       2000 + g % 26,
       'Bench ' || g
  from generate_series(1, {CONTESTS}) g;

insert into exam (contest_id, slug, name, publish_status)
select id, 'prova', 'Prova bench', 'published' from contest where slug like 'bench-%';

insert into exam_position (exam_id, position_id)
select e.id, p.id
  from exam e join contest c on c.id = e.contest_id join position p on p.agency_id = c.agency_id
 where c.slug like 'bench-%';

create temp table tpl as
select row_number() over (order by q.id) as k, q.*
  from question q join exam e on e.id = q.exam_id join contest c on c.id = e.contest_id
 where c.slug like 'seed-%';

insert into question (exam_id, number, type, subject_id, statement_md, answer_preliminary,
                      answer_final, answer_status, statement_hash, source_page, extracted_by,
                      publish_status)
select e.id, n, t.type, t.subject_id, t.statement_md, t.answer_preliminary, t.answer_final,
       t.answer_status, encode(sha256(convert_to(e.id || '-' || n, 'utf8')), 'hex'), 1,
       'bench:' || t.k, 'published'
  from exam e
  join contest c on c.id = e.contest_id
 cross join generate_series(1, {QUESTIONS_PER_EXAM}) n
  join tpl t on t.k = 1 + (n + e.id) % (select count(*) from tpl)
 where c.slug like 'bench-%';

insert into question_option (question_id, letter, body_md)
select q.id, o.letter, o.body_md
  from question q join tpl t on q.extracted_by = 'bench:' || t.k
  join question_option o on o.question_id = t.id;

insert into question_topic (question_id, topic_id, origin)
select q.id, qt.topic_id, 'manual'
  from question q join tpl t on q.extracted_by = 'bench:' || t.k
  join question_topic qt on qt.question_id = t.id;

update question set search_vector = question_search_vector(statement_md, id, passage_id)
 where extracted_by like 'bench:%';

alter table question enable trigger user;
alter table question_option enable trigger user;
"""

SEARCHES: list[tuple[str, dict[str, Any], str | None]] = [
    ("sem filtros", {}, None),
    ("banca", {"exam_board": ["cebraspe"]}, None),
    ("órgão + disciplina", {"agency": ["pc-sp"], "subject": ["direito-penal"]}, None),
    ("assunto (com subassuntos)", {"topic": ["direito_penal"]}, None),
    ("ano + tipo", {"year": {"from": 2020}, "type": ["multiple_choice"]}, None),
    ("texto", {}, "inquérito policial"),
    ("texto + órgão", {"agency": ["pf"]}, "polícia"),
]
FACETS = SEARCHES[:2] + SEARCHES[5:6]


def timed(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...]) -> tuple[float, Any]:
    start = time.perf_counter()
    row = conn.execute(sql, params).fetchone()  # type: ignore[arg-type]
    return (time.perf_counter() - start) * 1000, row[0] if row else None


def measure(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...]) -> list[float]:
    timed(conn, sql, params)  # aquece
    return [timed(conn, sql, params)[0] for _ in range(RUNS)]


def p95(samples: list[float]) -> float:
    return statistics.quantiles(samples, n=20)[-1]


def main(owner_url: str, web_url: str) -> int:
    with psycopg.connect(owner_url, autocommit=True) as owner:
        start = time.perf_counter()
        with owner.transaction():
            owner.execute(GENERATE.encode())
        owner.execute("analyze")
        total = owner.execute("select count(*) from published_question").fetchone()
        print(
            f"bench: {total[0] if total else 0} questões publicadas "
            f"(geradas em {time.perf_counter() - start:.0f}s)\n"
        )

    failed = False
    rows: list[tuple[str, str, float, float]] = []
    with psycopg.connect(web_url, autocommit=True) as web:
        for label, filters, query in SEARCHES:
            samples = measure(
                web, "select api.search_questions(%s, %s, 20)", (Jsonb(filters), query)
            )
            rows.append(("search_questions", label, statistics.median(samples), p95(samples)))

        _, page = timed(web, "select api.search_questions('{}', null, 20)", ())
        for _ in range(49):  # página 50
            _, page = timed(
                web, "select api.search_questions('{}', null, 20, %s)", (page["next_cursor"],)
            )
        samples = measure(
            web, "select api.search_questions('{}', null, 20, %s)", (page["next_cursor"],)
        )
        rows.append(
            ("search_questions", "página 51 (cursor)", statistics.median(samples), p95(samples))
        )

        for label, filters, query in FACETS:
            samples = measure(web, "select api.facet_counts(%s, %s)", (Jsonb(filters), query))
            rows.append(("facet_counts", label, statistics.median(samples), p95(samples)))

    print(f"{'função':<18} {'caso':<28} {'p50 ms':>8} {'p95 ms':>8} {'meta':>6}")
    for function, label, p50, p95_ms in rows:
        ok = p95_ms <= TARGET_MS[function]
        failed |= not ok
        print(
            f"{function:<18} {label:<28} {p50:>8.1f} {p95_ms:>8.1f} {TARGET_MS[function]:>6.0f}"
            f"{'' if ok else '  FALHA'}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
