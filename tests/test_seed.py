"""O seed cobre o que o front-end precisa (SPECIFICATION.md §6) e pode ser recarregado."""

import os
import subprocess
from pathlib import Path

import psycopg

from tests import factories as f

Conn = psycopg.Connection[tuple[object, ...]]
SEED = Path(__file__).resolve().parent.parent / "db" / "seed" / "seed.sql"


def test_seed_minimums(web: Conn) -> None:
    def n(sql: str) -> int:
        return int(f.scalar(web, sql))

    assert n("select count(distinct exam_board_slug) from api.question") >= 3
    assert n("select count(distinct agency_slug) from api.question") >= 4
    assert n("select count(*) from api.question") >= 60
    assert n("select count(distinct type) from api.question") == 2
    assert (
        n(
            "select count(*) from (select passage_id from api.question where passage_id is not null"
            " group by 1 having count(*) > 1) x"
        )
        >= 1
    )
    assert n("select count(*) from api.question where jsonb_array_length(assets) > 0") >= 1
    assert (
        n(
            "select count(*) from api.question where statement_md like '%|---%'"
            " or passage_md like '%|---%'"
        )
        >= 1
    )
    assert n("select count(*) from api.question where answer_status = 'annulled'") >= 1
    assert n("select count(*) from api.question where answer_status = 'changed'") >= 1
    assert n("select count(*) from api.question where contest_slug not like 'seed-%'") == 0


def test_seed_reloads_to_the_same_state(ingest_url: str, web: Conn) -> None:
    def snapshot() -> list[tuple[object, ...]]:
        return web.execute(
            "select id, answer, topics, options from api.question order by id"
        ).fetchall()

    before = snapshot()
    subprocess.run(
        ["psql", ingest_url, "-v", "ON_ERROR_STOP=1", "-q", "-f", str(SEED)],
        check=True,
        env=os.environ | {"PGOPTIONS": "--client-min-messages=warning"},
    )
    web.rollback()
    assert snapshot() == before
