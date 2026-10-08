"""Contrato com o front-end (SPECIFICATION.md §6, docs/contract.md), contra o seed.

Os números esperados vêm de scripts/build_seed.py: 65 questões publicadas, 1 anulada.
"""

import base64
import json
import unicodedata
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from psycopg.errors import InsufficientPrivilege, InvalidParameterValue
from psycopg.types.json import Jsonb

from tests import factories as f

Conn = psycopg.Connection[tuple[object, ...]]

ALL = 65
NOT_ANNULLED = 64


def search(
    conn: Conn,
    filters: dict[str, Any] | None = None,
    query: str | None = None,
    page_size: int = 100,
    cursor: str | None = None,
) -> dict[str, Any]:
    result = f.scalar(
        conn,
        "select api.search_questions(%s, %s, %s, %s)",
        (Jsonb(filters or {}), query, page_size, cursor),
    )
    assert isinstance(result, dict)
    return result


def facets(
    conn: Conn, filters: dict[str, Any] | None = None, query: str | None = None
) -> dict[str, Any]:
    result = f.scalar(conn, "select api.facet_counts(%s, %s)", (Jsonb(filters or {}), query))
    assert isinstance(result, dict)
    return result


def counts(facet: list[dict[str, Any]], key: str = "slug") -> dict[Any, int]:
    return {item[key]: item["count"] for item in facet}


def plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


# --- Busca e filtros -----------------------------------------------------------------------------


def test_annulled_hidden_by_default(web: Conn) -> None:
    assert search(web)["total"] == NOT_ANNULLED
    assert search(web, {"include_annulled": True})["total"] == ALL


@pytest.mark.parametrize(
    ("filters", "total"),
    [
        ({"exam_board": ["cebraspe"]}, 26),
        ({"agency": ["pf", "prf"]}, 26),
        ({"career": ["policia_civil"]}, 26),
        ({"position": ["soldado"]}, 12),
        ({"year": {"from": 2025}}, 27),
        ({"year": {"from": 2024, "to": 2024}}, 37),
        ({"subject": ["lingua-portuguesa"]}, 14),
        ({"type": ["true_false"]}, 26),
        ({"type": ["multiple_choice"]}, 38),
        ({"topic": ["direito_penal.crimes_contra_o_patrimonio"]}, 4),  # inclui subassuntos
        ({"topic": ["direito_penal.crimes_contra_o_patrimonio.furto"]}, 2),
        ({"agency": ["pf"], "subject": ["direito-penal"]}, 3),  # chaves diferentes: E
        ({"agency": []}, NOT_ANNULLED),  # lista vazia não filtra
        ({"agency": ["inexistente"]}, 0),
    ],
)
def test_filters(web: Conn, filters: dict[str, Any], total: int) -> None:
    result = search(web, filters)
    assert result["total"] == total
    assert len(result["items"]) == total


def test_text_search_ignores_accents_and_reaches_options(web: Conn) -> None:
    with_accent = search(web, query="inquérito")
    without = search(web, query="inquerito")
    assert with_accent == without
    assert with_accent["total"] == 6
    for item in with_accent["items"]:
        text = plain(item["statement_md"] + " ".join(o["body_md"] for o in item["options"]))
        assert "inquerito" in text


def test_text_search_combines_with_filters(web: Conn) -> None:
    assert search(web, {"agency": ["pc-sp"]}, query="inquérito")["total"] == 4


def test_hostile_input_is_data(web: Conn) -> None:
    assert search(web, {"agency": ["pf'); drop table question; --"]})["total"] == 0
    assert search(web, query="'; drop table question; --")["total"] == 0
    assert search(web)["total"] == NOT_ANNULLED


@pytest.mark.parametrize(
    "filters",
    [
        {"banca": ["cebraspe"]},
        {"agency": "pf"},
        {"agency": [1]},
        {"career": ["policia_federal"]},
        {"type": ["objetiva"]},
        {"topic": ["direito penal"]},
        {"year": 2024},
        {"year": {"from": "2024"}},
        {"year": {"desde": 2024}},
        {"include_annulled": "sim"},
    ],
)
def test_invalid_filters_are_rejected(web: Conn, filters: dict[str, Any]) -> None:
    with pytest.raises(InvalidParameterValue):
        search(web, filters)


def test_filters_must_be_an_object(web: Conn) -> None:
    with pytest.raises(InvalidParameterValue):
        f.scalar(web, "select api.search_questions('[]'::jsonb)")


@pytest.mark.parametrize("page_size", [0, 101])
def test_page_size_bounds(web: Conn, page_size: int) -> None:
    with pytest.raises(InvalidParameterValue):
        search(web, page_size=page_size)


@pytest.mark.parametrize(
    "cursor",
    ["lixo", base64.b64encode(b'{"y": 2025}').decode(), base64.b64encode(b"[1]").decode()],
)
def test_invalid_cursor(web: Conn, cursor: str) -> None:
    with pytest.raises(InvalidParameterValue):
        search(web, cursor=cursor)


# --- Paginação -----------------------------------------------------------------------------------


def pages(
    conn: Conn, filters: dict[str, Any], query: str | None, size: int
) -> Iterator[dict[str, Any]]:
    cursor = None
    while True:
        page = search(conn, filters, query, size, cursor)
        yield page
        cursor = page["next_cursor"]
        if cursor is None:
            return


def sort_key(item: dict[str, Any]) -> tuple[int, str, str, int]:
    return (-item["year"], item["contest_slug"], item["exam_slug"], item["number"])


@pytest.mark.parametrize(
    ("filters", "query"),
    [({"include_annulled": True}, None), ({"subject": ["direito-penal"]}, None), ({}, "polícia")],
)
@pytest.mark.parametrize("size", [1, 7, 100])
def test_keyset_pagination_walks_everything_once_in_order(
    web: Conn, filters: dict[str, Any], query: str | None, size: int
) -> None:
    all_pages = list(pages(web, filters, query, size))
    items = [item for page in all_pages for item in page["items"]]
    assert len(items) == all_pages[0]["total"] > 0
    assert len({item["id"] for item in items}) == len(items)
    assert items == sorted(items, key=sort_key)
    assert all(len(page["items"]) == size for page in all_pages[:-1])


def test_cursor_is_opaque_base64_json(web: Conn) -> None:
    cursor = search(web, page_size=1)["next_cursor"]
    assert set(json.loads(base64.b64decode(cursor))) == {"y", "c", "e", "n"}


# --- Documento da questão ------------------------------------------------------------------------

DOC_KEYS = {
    "id",
    "number",
    "type",
    "statement_md",
    "passage_id",
    "passage_md",
    "options",
    "answer",
    "answer_preliminary",
    "answer_status",
    "exam_board_slug",
    "exam_board_name",
    "exam_board_short_name",
    "agency_slug",
    "agency_name",
    "agency_short_name",
    "career",
    "government_level",
    "state",
    "contest_slug",
    "contest_name",
    "year",
    "exam_slug",
    "exam_name",
    "applied_on",
    "positions",
    "subject_slug",
    "subject_name",
    "topics",
    "assets",
    "source_url",
    "source_page",
}


def test_get_question_matches_search_item(web: Conn) -> None:
    item = search(web, page_size=1)["items"][0]
    assert set(item) == DOC_KEYS
    assert f.scalar(web, "select api.get_question(%s)", (item["id"],)) == item
    assert f.scalar(web, "select api.get_question(gen_random_uuid())") is None


def test_documents_of_special_questions(web: Conn) -> None:
    items = search(web, {"include_annulled": True})["items"]

    annulled = [i for i in items if i["answer_status"] == "annulled"]
    assert [(i["answer"], i["answer_preliminary"]) for i in annulled] == [(None, "E")]

    changed = [i for i in items if i["answer_status"] == "changed"]
    assert [(i["answer"], i["answer_preliminary"]) for i in changed] == [("E", "C")]

    with_image = [i for i in items if i["assets"]]
    assert len(with_image) == 2
    for item in with_image:
        (asset,) = item["assets"]
        assert f"asset:{asset['sha256']}" in item["statement_md"]
        assert asset["url"] == f"/assets/{asset['sha256']}.svg"
        assert f.scalar(web, "select api.asset_url(%s)", (asset["sha256"],)) == asset["url"]

    shared = [i for i in items if i["passage_id"]]
    assert {i["passage_id"] for i in shared} == {
        str(r[0]) for r in web.execute("select id from api.passage").fetchall()
    }
    assert any("|---" in i["passage_md"] for i in shared)  # tabela


def test_asset_url_unknown(web: Conn) -> None:
    assert f.scalar(web, "select api.asset_url(%s)", ("0" * 64,)) is None


# --- Facetas -------------------------------------------------------------------------------------


def test_facets_without_filters(web: Conn) -> None:
    result = facets(web)
    assert result["total"] == NOT_ANNULLED
    assert counts(result["exam_board"]) == {"cebraspe": 26, "vunesp": 25, "fgv": 13}
    assert counts(result["type"], "value") == {"multiple_choice": 38, "true_false": 26}
    assert counts(result["year"], "value") == {2025: 27, 2024: 37}
    assert [y["value"] for y in result["year"]] == [2025, 2024]
    for facet in ("exam_board", "agency", "career", "subject", "type", "year"):
        assert sum(item["count"] for item in result[facet]) == NOT_ANNULLED, facet


def test_facets_are_disjunctive(web: Conn) -> None:
    result = facets(web, {"exam_board": ["cebraspe"]})
    assert result["total"] == 26
    # A própria faceta ignora o próprio filtro, para o site mostrar as outras opções...
    assert counts(result["exam_board"]) == {"cebraspe": 26, "vunesp": 25, "fgv": 13}
    # ...e as demais respeitam o filtro.
    assert counts(result["agency"]) == {"pf": 14, "prf": 12}  # 1 anulada na PRF


def test_topic_facet_counts_ancestors(web: Conn) -> None:
    topic = counts(facets(web)["topic"], "path")
    assert topic["direito_penal.crimes_contra_o_patrimonio"] == 4
    assert topic["direito_penal.crimes_contra_o_patrimonio.furto"] == 2
    assert topic["direito_penal.crimes_contra_o_patrimonio.roubo"] == 3


def test_facets_match_search(web: Conn) -> None:
    filters = {"subject": ["direito-constitucional"], "year": {"from": 2025}}
    result = facets(web, filters, "polícia")
    assert result["total"] == search(web, filters, "polícia")["total"]


# --- Catálogos -----------------------------------------------------------------------------------


def test_catalog_views(web: Conn) -> None:
    def rows(sql: str) -> dict[Any, Any]:
        return {r[0]: r[1] for r in web.execute(sql).fetchall()}  # type: ignore[arg-type]

    assert rows("select slug, question_count from api.exam_board") == {
        "cebraspe": 27,
        "fgv": 13,
        "vunesp": 25,
    }
    assert rows("select slug, question_count from api.agency")["pm-sp"] == 12
    assert rows("select slug, question_count from api.position")["soldado"] == 12
    assert rows("select slug, question_count from api.subject")["lingua-portuguesa"] == 14
    topics = rows("select path, question_count from api.topic")
    assert topics["direito_penal.crimes_contra_o_patrimonio"] == 4
    assert rows("select contest_slug, question_count from api.exam") == {
        "seed-pf-2025": 14,
        "seed-prf-2024": 13,
        "seed-pcsp-2025": 13,
        "seed-pcrj-2024": 13,
        "seed-pmsp-2024": 12,
    }
    parent = web.execute(
        "select parent_path, depth from api.topic where path = 'direito_penal.crimes_contra_o_patrimonio.furto'"
    ).fetchone()
    assert parent == ("direito_penal.crimes_contra_o_patrimonio", 2)


# --- Visibilidade --------------------------------------------------------------------------------


@pytest.fixture
def tx(ingest: Conn) -> Iterator[Conn]:
    with ingest.transaction(force_rollback=True):
        yield ingest


def test_only_published_non_duplicate_questions_are_visible(tx: Conn) -> None:
    seed_exam = f.scalar(
        tx,
        "select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'",
    )
    original = f.scalar(
        tx, "select id from question where exam_id = %s and number = 1", (seed_exam,)
    )
    f.question(tx, seed_exam, number=90)  # rascunho
    dup = f.question(tx, seed_exam, number=91, publish_status="published", duplicate_of=original)
    assert search(tx, {"include_annulled": True})["total"] == ALL
    assert f.scalar(tx, "select api.get_question(%s)", (dup,)) is None

    tx.execute("update exam set publish_status = 'review' where id = %s", (seed_exam,))
    assert search(tx, {"include_annulled": True})["total"] == ALL - 14
    assert f.scalar(tx, "select count(*) from api.question") == ALL - 14


# --- Permissões ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "select * from public.question",
        "select * from public.published_question",
        "select public.search_condition('{}', null)",
        "select public.question_docs('{}')",
        "select * from crawl.page",
    ],
)
def test_web_sees_only_the_api(web: Conn, statement: str) -> None:
    with pytest.raises(InsufficientPrivilege):
        web.execute(statement)  # type: ignore[arg-type]
