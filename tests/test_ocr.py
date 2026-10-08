"""OCR na etapa extract (decisão 0018). O teste de ponta a ponta exige Tesseract com `por`."""

import shutil
import subprocess
from pathlib import Path

import pymupdf
import pytest

from ingest import extract as ex
from ingest.extract import Figure, Line, LineFix, OcrFixError, OcrFixes, Page

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures/pdf/cebraspe"


def line(plain: str, y: float, column: int = 2, x0: float = 323.0, size: float = 7.6) -> Line:
    return Line(text=plain, plain=plain, x0=x0, y0=y, x1=560.0, y1=y + 8, column=column, size=size)


def page(number: int, lines: list[Line], figures: list[Figure] | None = None) -> Page:
    return Page(
        number=number, width=595, height=842, has_text=True, lines=lines, figures=figures or []
    )


def test_fixes_replace_ocr_lines() -> None:
    pages = [page(2, [line("de três unidades da Federação: Distrito Federal, Golás e", 100)])]
    fixes = OcrFixes(
        document="https://x/a.pdf",
        proofread_by="claude-opus-5-5",
        lines=[
            LineFix(
                page=2,
                ocr="de três unidades da Federação: Distrito Federal, Golás e",
                text="de três unidades da Federação: Distrito Federal, Goiás e",
            )
        ],
    )
    ex.apply_fixes(pages, fixes)
    assert pages[0].lines[0].plain.endswith("Goiás e")
    assert pages[0].lines[0].text == pages[0].lines[0].plain


def test_fix_keeps_markdown_out_of_plain() -> None:
    pages = [page(2, [line("severos, dê um largo ciao ao trabalho", 100)])]
    fix = LineFix(
        page=2, ocr=pages[0].lines[0].plain, text="severos, dê um largo *ciao* ao trabalho"
    )
    ex.apply_fixes(pages, OcrFixes(document="u", proofread_by="m", lines=[fix]))
    assert pages[0].lines[0].text == "severos, dê um largo *ciao* ao trabalho"
    assert pages[0].lines[0].plain == "severos, dê um largo ciao ao trabalho"


def test_fix_without_matching_line_fails() -> None:
    fixes = OcrFixes(
        document="u", proofread_by="m", lines=[LineFix(page=1, ocr="não existe", text="x")]
    )
    with pytest.raises(OcrFixError, match="não encontrada"):
        ex.apply_fixes([page(1, [line("outra", 10)])], fixes)


def test_glyph_drawings_are_not_figures() -> None:
    text = line("A sequência de ações do texto", 100)
    figures = [
        Figure(kind="drawing", x0=330, y0=101, x1=335, y1=107),  # letra dentro da linha
        Figure(kind="drawing", x0=40, y0=500, x1=46, y1=506),  # letra que o OCR não leu
        Figure(kind="drawing", x0=40, y0=600, x1=300, y1=700),  # gráfico de verdade
        Figure(kind="image", x0=330, y0=101, x1=335, y1=107),
    ]
    kept = ex._without_glyphs(page(1, [text], figures))
    assert [(f.kind, f.y0) for f in kept] == [("drawing", 600), ("image", 101)]


def test_item_numbers_recovered_only_in_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [
        line("3 O texto apresenta uma espécie de roteiro", 100, x0=305),
        line("A sequência de ações do texto se organiza", 200),  # item 4 sem número
        line("JUSTIFICATIVA - CERTO. O modo imperativo", 230),  # lixo do OCR na altura
        line("A expressão “homem moderno” faz", 300),  # item 5 sem número
        line("6 No primeiro período do texto", 400, x0=305),
        line("9", 830, x0=336, size=3.7),  # número da página no rodapé: não é item
    ]
    digits = [(306.0, 204.0, 4), (306.0, 234.0, 77), (306.0, 304.0, 5)]
    monkeypatch.setattr(ex, "_gutter_digits", lambda _page, _left: digits)
    pages = [page(1, lines)]
    ex._recover_item_numbers(FIXTURES / "pf-2021-agente-p2-3.pdf", pages, {1})
    plains = [entry.plain.split()[0] for entry in pages[0].lines]
    assert plains == ["3", "4", "JUSTIFICATIVA", "5", "6", "9"]
    assert pages[0].lines[1].x0 == 306.0  # o número volta para a margem da coluna


def _has_portuguese_ocr() -> bool:
    if shutil.which("tesseract") is None:
        return False
    langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
    return "por" in langs.split()


@pytest.mark.skipif(not _has_portuguese_ocr(), reason="Tesseract com `por` não instalado")
def test_scanned_pdf_goes_through_ocr(tmp_path: Path) -> None:
    scanned = tmp_path / "abc123.pdf"
    with pymupdf.open(FIXTURES / "pf-2021-agente-gabarito-definitivo.pdf") as source:
        pix = source[0].get_pixmap(dpi=200)
        out = pymupdf.open()
        target = out.new_page(width=source[0].rect.width, height=source[0].rect.height)
        target.insert_image(target.rect, pixmap=pix)
        out.save(scanned)
    fixes_dir = tmp_path / "fixes"
    fixes_dir.mkdir()
    pages = ex.extract(scanned, ocr_dir=tmp_path / "ocr", fixes_dir=fixes_dir)
    assert pages[0].has_text
    assert pages[0].ocr == ex.OCR_ENGINE
    assert "GABARITO" in " ".join(entry.plain for entry in pages[0].lines).upper()
    assert (tmp_path / "ocr" / "abc123.pdf").exists()
