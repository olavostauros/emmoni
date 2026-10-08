"""M0: extensões, esquemas e papéis (SPECIFICATION.md §1 e §4.6)."""

from collections.abc import Iterator

import psycopg
import pytest
from psycopg.errors import InsufficientPrivilege

Conn = psycopg.Connection[tuple[object, ...]]

SCHEMAS = ("public", "crawl", "api")


def test_extensions_live_in_ext(owner: Conn) -> None:
    rows = owner.execute(
        "select e.extname, n.nspname from pg_extension e"
        " join pg_namespace n on n.oid = e.extnamespace where e.extname <> 'plpgsql'"
    ).fetchall()
    assert dict(rows) == {name: "ext" for name in ("unaccent", "pg_trgm", "ltree", "pgcrypto")}


@pytest.mark.parametrize("role", ["owner", "ingest", "web"])
def test_extensions_reachable_by_every_role(role: str, request: pytest.FixtureRequest) -> None:
    conn: Conn = request.getfixturevalue(role)
    row = conn.execute(
        "select unaccent('Ação Penal'), similarity('homicidio', 'homicídio') > 0,"
        " 'direito_penal.homicidio'::ltree <@ 'direito_penal'::ltree,"
        " length(gen_random_uuid()::text)"
    ).fetchone()
    assert row == ("Acao Penal", True, True, 36)


@pytest.fixture
def probes(owner: Conn) -> Iterator[None]:
    """Uma tabela e uma função por esquema, criadas pelo owner como numa migração."""
    for schema in SCHEMAS:
        owner.execute(f"create table {schema}.zz_probe (id int)")
        owner.execute(f"insert into {schema}.zz_probe values (1)")
        owner.execute(
            f"create function {schema}.zz_probe_fn() returns int language sql as 'select 1'"
        )
    yield
    for schema in SCHEMAS:
        owner.execute(f"drop table {schema}.zz_probe")
        owner.execute(f"drop function {schema}.zz_probe_fn()")


@pytest.mark.usefixtures("probes")
@pytest.mark.parametrize("schema", SCHEMAS)
def test_ingest_reads_and_writes_internal_and_reads_api(ingest: Conn, schema: str) -> None:
    assert ingest.execute(f"select id from {schema}.zz_probe").fetchone() == (1,)
    assert ingest.execute(f"select {schema}.zz_probe_fn()").fetchone() == (1,)
    if schema == "api":
        with pytest.raises(InsufficientPrivilege):
            ingest.execute("insert into api.zz_probe values (2)")
    else:
        ingest.execute(f"insert into {schema}.zz_probe values (2)")
    ingest.rollback()


@pytest.mark.usefixtures("probes")
def test_web_reads_only_api(web: Conn) -> None:
    assert web.execute("select id from api.zz_probe").fetchone() == (1,)
    assert web.execute("select api.zz_probe_fn()").fetchone() == (1,)
    for statement in ("insert into api.zz_probe values (2)", "delete from api.zz_probe"):
        with pytest.raises(InsufficientPrivilege):
            web.execute(statement)
        web.rollback()


@pytest.mark.usefixtures("probes")
@pytest.mark.parametrize("schema", ["public", "crawl"])
@pytest.mark.parametrize("what", ["table", "function"])
def test_web_cannot_touch_internal_schemas(web: Conn, schema: str, what: str) -> None:
    if what == "table":
        query = f"select * from {schema}.zz_probe"
    else:
        query = f"select {schema}.zz_probe_fn()"
    with pytest.raises(InsufficientPrivilege):
        web.execute(query)


@pytest.mark.parametrize("role", ["ingest", "web"])
@pytest.mark.parametrize("schema", SCHEMAS)
def test_only_owner_creates_objects(role: str, schema: str, request: pytest.FixtureRequest) -> None:
    conn: Conn = request.getfixturevalue(role)
    with pytest.raises(InsufficientPrivilege):
        conn.execute(f"create table {schema}.zz_intruder (id int)")
