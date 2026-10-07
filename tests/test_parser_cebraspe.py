"""Parser do Cebraspe contra PDFs oficiais em fixtures/ (snapshot JSON, SPECIFICATIONS.md §9)."""

import os
from pathlib import Path

import pytest

from ingest.extract import Figure, Line, Page, extract
from ingest.parsers import cebraspe
from ingest.staging import Segmented

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
EXAM_PDF = FIXTURES / "pdf/cebraspe/pf-2021-agente-p2-3.pdf"
KEY_PDF = FIXTURES / "pdf/cebraspe/pf-2021-agente-gabarito-definitivo.pdf"
SNAPSHOT = FIXTURES / "expected/cebraspe/pf-2021-agente-p2-3.json"


@pytest.fixture(scope="module")
def segmented() -> Segmented:
    return cebraspe.segment(extract(EXAM_PDF))


def test_snapshot(segmented: Segmented) -> None:
    actual = segmented.model_dump_json(indent=1)
    if os.environ.get("UPDATE_SNAPSHOTS"):
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(actual + "\n", encoding="utf-8")
    assert actual + "\n" == SNAPSHOT.read_text(encoding="utf-8")


def test_items_are_numbered_and_linked_to_passages(segmented: Segmented) -> None:
    numbers = [q.number for q in segmented.questions]
    assert numbers == list(range(1, 31))
    assert {q.type for q in segmented.questions} == {"true_false"}
    by_number = {q.number: q for q in segmented.questions}
    assert by_number[1].passage_key == "2A1-I"
    assert by_number[9].passage_key == "2A1-II"
    assert by_number[19].passage_key is None
    assert by_number[25].passage_key == "g25"  # situação hipotética sem rótulo


def test_command_opens_each_statement(segmented: Segmented) -> None:
    first = segmented.questions[0].statement_md
    command, item = first.split("\n\n")
    assert command.startswith("Com referência às ideias e aos aspectos linguísticos do texto 2A1-I")
    assert command.endswith("julgue os itens a seguir.")
    assert item.startswith("Infere-se do texto que a personagem")


def test_passages_keep_paragraphs_and_formatting(segmented: Segmented) -> None:
    passages = {p.key: p for p in segmented.passages}
    text = passages["2A1-I"].body_md
    assert text.startswith("Tinha de deixar aquela casa.")
    assert text.count("\n\n") >= 3  # parágrafos + citação
    assert "**Com vocês, Antônio Maria**" in text
    assert "julgue" not in text  # o comando não vaza para o texto-base
    assert passages["g25"].body_md.startswith("Determinado agente da Polícia Federal")


def test_no_header_or_item_number_leaks(segmented: Segmented) -> None:
    for question in segmented.questions:
        assert "CEBRASPE" not in question.statement_md
        assert "Aplicação: 2021" not in question.statement_md


def test_answer_key() -> None:
    key = cebraspe.parse_answer_key(extract(KEY_PDF))
    assert sorted(key.answers) == list(range(1, 121))
    assert [n for n, mark in key.answers.items() if mark == "X"] == [28, 92, 106, 108, 119]
    assert "".join(key.answers[n] for n in range(1, 11)) == "ECEEECECCE"
    assert "".join(key.answers[n] for n in range(111, 121)) == "ECCEEECCXC"


# --- casos sintéticos: o que deve ir para revisão ---------------------------------------------


def _line(text: str, x0: float, y0: float, x1: float = 290.0, size: float = 10.0) -> Line:
    plain = text.replace("**", "")
    return Line(text=text, plain=plain, x0=x0, y0=y0, x1=x1, y1=y0 + 11, column=1, size=size)


def _page(lines: list[Line], figures: list[Figure] | None = None) -> Page:
    head = Line(
        text="-- PROVA OBJETIVA --",
        plain="-- PROVA OBJETIVA --",
        x0=217,
        y0=10,
        x1=380,
        y1=25,
        column=0,
        size=15,
    )
    return Page(
        number=1,
        width=595,
        height=842,
        has_text=True,
        lines=[head, *lines],
        figures=figures or [],
    )


def test_figure_after_item_text_flags_the_item() -> None:
    page = _page(
        [
            _line("Acerca de planilhas, julgue o item a seguir.", 28, 50),
            _line("**1** Na planilha a seguir, a fórmula da célula B5 soma", 28, 70),
            _line("os valores da coluna B.", 46, 82, x1=150),
            _line("Julgue o próximo item.", 28, 200),
            _line("**2** Texto sem figura.", 28, 220),
        ],
        [Figure(kind="image", x0=46, y0=100, x1=250, y1=180)],
    )
    questions = cebraspe.segment([page]).questions
    assert questions[0].flags == ["figure"]
    assert questions[1].flags == []


def test_code_lines_flag_layout() -> None:
    page = _page(
        [
            _line("Julgue o item seguinte.", 28, 50),
            _line("**1** O código Python a seguir imprime True.", 28, 70),
            _line("x = bool(-3)", 46, 82, x1=110),
            _line("print(x)", 46, 94, x1=90),
        ]
    )
    assert cebraspe.segment([page]).questions[0].flags == ["layout"]


def test_broken_math_glyphs_flag_formula() -> None:
    page = _page(
        [
            _line("Julgue o item seguinte.", 28, 50),
            _line("**1** 𝑃ሺ𝑋ൌ5ሻ൐ 𝛾.", 28, 70),
        ]
    )
    assert "formula" in cebraspe.segment([page]).questions[0].flags


def test_out_of_sequence_number_is_not_an_item() -> None:
    page = _page(
        [
            _line("Julgue o item seguinte.", 28, 50),
            _line("**1** Em 2020, foram registradas", 28, 70),
            _line("5 ocorrências no total.", 28, 82),  # "5" na margem, mas o esperado é 2
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert [q.number for q in questions] == [1]
    assert questions[0].flags == ["orphan_text"]  # a linha não some em silêncio
