"""Propostas de manifesto: escrita, aprovação e rejeição (SPECIFICATION.md §7.1, decisão 0007)."""

import datetime
from pathlib import Path

import pytest

from ingest import crawl, manifest, proposals


def _contest(
    slug: str = "pf-2030", agency: str = "pf"
) -> tuple[crawl.ContestFound, list[crawl.ExamFound]]:
    exam_doc = crawl.FoundDocument(
        url=f"https://cdn.cebraspe.org.br/concursos/X/arquivos/{slug}-prova.pdf",
        found_on_url="https://www.cebraspe.org.br/concursos/X",
        link_text="PROVA OBJETIVA - CARGO 2: AGENTE",
        kind="exam",
        guessed={"kind": {"value": "exam", "confidence": 1.0, "rule": "teste"}},
    )
    key_doc = crawl.FoundDocument(
        url=f"https://cdn.cebraspe.org.br/concursos/X/arquivos/{slug}-gab.pdf",
        found_on_url=exam_doc.found_on_url,
        link_text="GABARITO DEFINITIVO - CARGO 2: AGENTE",
        kind="answer_key_final",
    )
    contest = crawl.ContestFound(
        url=exam_doc.found_on_url,
        found_on_url="https://apis.cebraspe.org.br/cebraspe/eventos/tipo/concursos/",
        link_text="X 2030",
        name="Teste 2030",
        scope="in_scope",
        agency=agency,
        year=2030,
        slug=slug,
        documents=[exam_doc, key_doc],
    )
    exam = crawl.ExamFound(
        slug="agente",
        name=exam_doc.link_text,
        positions=["agente"],
        documents={"exam": exam_doc, "answer_key_final": key_doc},
    )
    return contest, [exam]


def test_write_pending_only_when_changed(tmp_path: Path) -> None:
    contest, exams = _contest()
    built = proposals.build(contest, exams, "cebraspe")
    assert proposals.write_pending(built, tmp_path) == "nova"
    assert proposals.write_pending(built, tmp_path) == "sem mudança"
    loaded = manifest.load(proposals.pending_path("pf-2030", tmp_path))
    assert loaded.exams[0].documents.answer_key_final == exams[0].documents["answer_key_final"].url
    assert loaded.evidence["exams"]["agente"]["documents"]["exam"]["rule"] == "teste"
    exams[0].positions = ["escrivao"]
    assert (
        proposals.write_pending(proposals.build(contest, exams, "cebraspe"), tmp_path)
        == "atualizada"
    )


def test_approve_moves_the_file_and_checks_the_catalog(tmp_path: Path) -> None:
    contest, exams = _contest()
    proposals.write_pending(proposals.build(contest, exams, "cebraspe"), tmp_path)
    with pytest.raises(proposals.ProposalError, match="não há proposta"):
        proposals.approve("outro", tmp_path)
    target = proposals.approve("pf-2030", tmp_path)
    assert target == tmp_path / "pf-2030.yaml" and target.exists()
    assert not proposals.pending_path("pf-2030", tmp_path).exists()
    assert proposals.is_approved("pf-2030", tmp_path)
    assert set(proposals.approved_documents(tmp_path)) == {
        d.url for d in exams[0].documents.values()
    }
    with pytest.raises(proposals.ProposalError, match="já está aprovado"):
        proposals.approve("pf-2030", tmp_path)

    bad, bad_exams = _contest("zz-2031", agency="pf")
    bad_exams[0].positions = ["cargo-inexistente"]
    proposals.write_pending(proposals.build(bad, bad_exams, "cebraspe"), tmp_path)
    with pytest.raises(proposals.ProposalError, match="fora do catálogo"):
        proposals.approve("zz-2031", tmp_path)


def test_reject_records_the_reason(tmp_path: Path) -> None:
    contest, exams = _contest()
    proposals.write_pending(proposals.build(contest, exams, "cebraspe"), tmp_path)
    with pytest.raises(proposals.ProposalError, match="motivo"):
        proposals.reject("pf-2030", "  ", tmp_path)
    when = datetime.datetime(2026, 10, 7, tzinfo=datetime.UTC)
    target = proposals.reject(
        "pf-2030", "concurso de cargos administrativos", tmp_path, by="eu", now=when
    )
    assert target == tmp_path / "_rejected" / "pf-2030.yaml"
    assert not proposals.pending_path("pf-2030", tmp_path).exists()
    assert proposals.rejection("pf-2030", tmp_path) == "concurso de cargos administrativos"
    assert proposals.rejection("pf-2031", tmp_path) is None
    assert "by: eu" in target.read_text()
