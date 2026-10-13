"""Cadernos do site antigo do Cebraspe (decisão 0020): fontes sem nome e sem mapeamento Unicode."""

import re
from pathlib import Path

import pymupdf
import pytest

from ingest import extract as ex

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/pdf/cebraspe/pf-2012-agente-p2-3.pdf"


def _items(pages: list[ex.Page]) -> list[int]:
    """Números de item: linha de coluna em corpo de texto que começa com número e maiúscula."""
    return [
        int(m.group(1))
        for page in pages
        for line in page.lines
        if line.column in (1, 2) and line.size > 8 and (m := re.match(r"(\d{1,3}) [A-ZÀ-Ú“]", line.plain))
    ]  # fmt: skip


def _text(pages: list[ex.Page]) -> str:
    return "\n".join(line.text for page in pages for line in page.lines)


def test_legacy_decodes_item_numbers() -> None:
    items = _items(ex.extract(FIXTURE, legacy=True))
    # Os números de linha do texto-base (1, 4, 22, 25...) também casam; os itens vêm todos, em ordem.
    assert [n for n in items if n not in (1, 4, 10, 22, 25)][:5] == [2, 3, 5, 6, 7]
    assert all(n in items for n in range(1, 27))
    plain = _items(ex.extract(FIXTURE))  # sem decodificar, só os números de linha do texto-base
    assert not any(n in plain for n in (2, 3, 5, 6, 7, 8, 9, 11, 12))


def test_legacy_columns_follow_the_page() -> None:
    """A coluna da esquerda vai até 312 pt numa página de 595: passa do meio."""
    line = "“se alguém é executado” (ℓ.12), que expressa uma hipótese, poderia"
    page = ex.extract(FIXTURE, legacy=True)[1]
    assert [entry.column for entry in page.lines if entry.text == line] == [1]
    plain = [
        entry for entry in ex.extract(FIXTURE)[1].lines if "se alguém é executado" in entry.text
    ]
    assert [entry.column for entry in plain] == [0]


def test_legacy_line_reference_and_bold() -> None:
    text = _text(ex.extract(FIXTURE, legacy=True))
    assert "(ℓ.12)" in text and "(R.12)" not in text
    assert "**caso se execute alguém**" in text
    plain = _text(ex.extract(FIXTURE))
    # o ℓ vale para todo caderno; o estilo pelas larguras, só para o site antigo
    assert "(ℓ.12)" in plain and "**caso se execute alguém**" not in plain


def test_gutter_moves_only_when_the_middle_is_crossed() -> None:
    left = [(28.0, y, 312.0, y + 10) for y in range(0, 300, 12)]
    right = [(325.0, y, 567.0, y + 10) for y in range(0, 300, 12)]
    assert ex._gutter(left + right, 595.0) == 318.5
    centered = [(28.0, y, 280.0, y + 10) for y in range(0, 300, 12)] + right
    assert ex._gutter(centered, 595.0) == 297.5  # a metade não é cruzada: fica
    single = [(60.0, y, 535.0, y + 10) for y in range(0, 300, 12)]
    assert ex._gutter(single, 595.0) == 297.5


def _span(text: str, font: str, x: float, y: float) -> dict[str, object]:
    return {"text": text, "font": font, "bbox": (x, y, x + 5, y + 8)}


def test_digit_font_table_only_for_a_run_of_items() -> None:
    codes = "\x02\x03\x04\x05\x06\x07\x08\t\n"  # 1..9; \x0b é o 0
    spans = [_span(c, "TTD0B2o00", 28, 10 * i) for i, c in enumerate(codes)]
    spans += [_span("\x02\x0b", "TTD0B2o00", 28, 100), _span("\x02\x02", "TTD0B2o00", 28, 110)]
    lines = [{"spans": [span], "bbox": span["bbox"]} for span in spans]
    table = ex._digit_fonts([(lines, 297.5)])["TTD0B2o00"]
    assert table["\x02"] == "1" and table["\n"] == "9" and table["\x0b"] == "0"
    # O "10" antes do "1" (fonte de símbolos, não número de item): sem tabela.
    first = _span("\x02\x0b", "TTD0B2o00", 28, -10)
    moved = [{"spans": [first], "bbox": first["bbox"]}, *lines]
    assert ex._digit_fonts([(moved, 297.5)]) == {}


def test_font_styles_from_widths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Times normal, negrito e itálico: o estilo sai das larguras das letras, não do nome."""
    monkeypatch.setattr(ex, "UNNAMED_FONT", re.compile(".*"))
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    page = document.new_page()  # type: ignore[no-untyped-call]
    sample = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod"
    for y, font in enumerate(("tiro", "tibo", "tiit")):
        page.insert_text((40, 60 + 20 * y), sample, fontname=font, fontsize=10)
    assert sorted(ex._font_styles(document).values()) == [0, ex.ITALIC, ex.BOLD]
