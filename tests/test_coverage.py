"""Relatório de cobertura (SPECIFICATIONS.md §8)."""

import shutil
from pathlib import Path

import psycopg

from ingest import coverage, manifest
from tests import factories

Conn = psycopg.Connection[tuple[object, ...]]


def test_coverage_counts_visible_questions_and_lists_gaps(ingest: Conn, tmp_path: Path) -> None:
    try:
        exam_id = factories.exam(ingest, published=True)
        for number in (1, 2, 3):
            factories.question(ingest, exam_id, number=number, publish_status="published")
        factories.question(ingest, exam_id, number=4, publish_status="review")
        hidden = factories.exam(ingest, published=False)
        factories.question(ingest, hidden, number=1, publish_status="published")
        shutil.copy(manifest.MANIFESTS_DIR / "pcpe-2016.yaml", tmp_path)
        (tmp_path / "_pending").mkdir()
        ingest.execute(
            """insert into crawl.page (url, source_slug, last_fetched_at, http_status)
               values ('https://exemplo.gov.br/a', 'teste', now(), 200),
                      ('https://bloqueado.gov.br/b', 'teste', now(), 429)"""
        )
        before = coverage.collect(ingest, tmp_path)
        text = coverage.render(before)
        assert "`pcpe-2016/delegado`" in text
        assert ("teste", 2, ["bloqueado.gov.br"]) in [(s, n, b) for s, _, n, b in before.sources]
        assert any(status == "draft" for _, _, status in before.not_published)
        # Só questões visíveis: as 3 publicadas da prova publicada.
        factories.question(ingest, exam_id, number=5, publish_status="published")
        assert coverage.collect(ingest, tmp_path).total == before.total + 1
    finally:
        ingest.rollback()
