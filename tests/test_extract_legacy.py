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


DELEGADO = FIXTURE.with_name("pf-2021-delegado-p3.pdf")


def test_styles_only_recovers_italic_in_new_booklets() -> None:
    """PF 2021 delegado: fontes "TT…o00" sem nome de estilo; o itálico sai pelas larguras com
    `styles`, sem o resto do `legacy` (decisão 0020, emenda de 2026-10-13)."""
    text = _text(ex.extract(DELEGADO, styles=True))
    assert "recurso ordinário de *habeas corpus*" in text
    assert "julgar *habeas data*" in text
    assert "*habeas corpus*" not in _text(ex.extract(DELEGADO))  # desligado: como antes


def test_styles_only_keeps_the_rest_of_legacy_off() -> None:
    """No PF 2012, `styles` dá o negrito, mas as colunas e os números de item seguem sem `legacy`."""
    styled, plain = ex.extract(FIXTURE, styles=True), ex.extract(FIXTURE)
    assert "**caso se execute alguém**" in _text(styled)
    assert [[(e.plain, e.column) for e in p.lines] for p in styled] == [
        [(e.plain, e.column) for e in p.lines] for p in plain
    ]


PF_2018 = (
    Path(__file__).resolve().parent.parent / "fixtures/pdf/cebraspe/pf-2018-papiloscopista-p1.pdf"
)


def test_credit_font_with_too_few_letters_is_italic() -> None:
    """PF 2018 (`styles`, fora do site antigo): "et al" e "In" numa fonte própria, com letras de
    menos para as larguras, mas o "In" antes de ":" no crédito diz que é a itálica."""
    pages = ex.extract(PF_2018, styles=True)
    credit = next(line.text for page in pages for line in page.lines if "Nateghian" in line.text)
    assert credit.startswith("Z. Nateghian *et al*.")
    assert "*In*:" in _text(pages)
    assert "*et al*" not in _text(ex.extract(PF_2018))  # sem `styles`, nada muda


CEBRASPE = Path(__file__).resolve().parent.parent / "fixtures/pdf/cebraspe"


def test_small_font_inherits_style_from_same_outlines() -> None:
    """PM/PA 2023 CFP (decisão 0020, emenda de 2026-10-14): "chip" numa fonte própria de 4 letras,
    que desenha os glifos como a itálica deduzida pelas larguras ("*habeas corpus*"): herda o
    itálico. Pelas larguras não daria: c, h, i, p medem o mesmo no Times normal e no itálico."""
    pages = ex.extract(CEBRASPE / "pmpa-2023-cfp-especificos-p1-2.pdf", styles=True)
    text = _text(pages)
    assert "a *chip* telefônico" in text
    assert "*habeas corpus* e *habeas data*" in text
    assert "*chip*" not in _text(ex.extract(CEBRASPE / "pmpa-2023-cfp-especificos-p1-2.pdf"))


def test_small_font_style_with_clear_margin() -> None:
    """PM/PA 2023 CFO: o título do crédito numa fonte de 19 letras, abaixo das 20 do item 4, mas
    com o negrito bem mais perto que os outros estilos."""
    pages = ex.extract(CEBRASPE / "pmpa-2023-cfo-basicos-p1.pdf", styles=True)
    assert "Marshall Rosenberg. **Comunicação não violenta**." in _text(pages)


def test_small_font_style_needs_evidence() -> None:
    """Letras de menos, letras repetidas ou letras que medem o mesmo nos dois estilos: nada."""
    refs = {name: pymupdf.Font(name) for name in ex.STYLE_FONTS}  # type: ignore[no-untyped-call]

    def widths(text: str, ref: str) -> list[tuple[str, float]]:
        return [(c, refs[ref].glyph_advance(ord(c))) for c in text]  # type: ignore[no-untyped-call]

    assert ex._small_font_style(widths("ComunicaonoviolentaT", "tibo"), refs) == ex.BOLD
    assert ex._small_font_style(widths("chip", "tiit"), refs) is None  # poucas letras
    assert ex._small_font_style(widths("chipchip", "tiit"), refs) is None  # sem margem
    assert ex._small_font_style(widths("NnNnNnNn", "tibo"), refs) is None  # letras repetidas


def test_styles_turn_monospaced_font_into_inline_code() -> None:
    """PC/GO 2016 básicos, q15: comandos e caminhos em fonte monoespaçada sem nome viram código
    inline também com `styles` (decisão 0020, emenda de 2026-10-14)."""
    text = _text(ex.extract(CEBRASPE / "pcgo-2016-basicos-p4.pdf", styles=True))
    assert "o programa `xpto`, gravado no" in text
    assert "diretório `/home/fulano/`" in text
    assert "`ls /home/fulano/xpto| proc`." in text
    assert "`" not in _text(ex.extract(CEBRASPE / "pcgo-2016-basicos-p4.pdf"))  # desligado


def test_styles_monospaced_short_words() -> None:
    """PF 2018 papiloscopista, pág. 5: "Bcc" (q61) e "no" (q65) vêm numa fonte sem nome monoespaçada
    que só tem essas 4 letras, todas com a largura da Courier; viravam texto comum porque a regra
    pedia 8 letras distintas (emenda (15) da 0020)."""
    text = _text(ex.extract(CEBRASPE / "pf-2018-papiloscopista-p5.pdf", styles=True))
    assert "a opção `Bcc` (" in text
    assert "preposição `no`, sendo utilizado" in text


def test_credit_in_at_line_start_or_with_colon() -> None:
    """O "In" do crédito também no começo da linha ("In" | ": Renato S. de Lima…", PC/PB 2021) e com
    os dois-pontos na própria fonte ("In:" | " " | "Revista da EMERJ", PC/RO 2022)."""

    def spans(*parts: tuple[str, str]) -> list[dict[str, str]]:
        return [{"font": font, "text": text} for font, text in parts]

    line_start = spans(("TT1ADC2o00", "In"), ("TT1ACA2o00", ": Renato S. de Lima (Org.)."))
    assert ex._credit_in_at(line_start, 0)
    with_colon = spans(("TT641E2o00", "In:"), ("TT641A2o00", " "), ("TT641C2o00", "Revista"))
    assert ex._credit_in_at(with_colon, 0)
    middle = spans(("A", "violência. "), ("B", "In"), ("A", ": Renato"))
    assert ex._credit_in_at(middle, 1)
    # Mesma fonte que a vizinha, "In" sem dois-pontos depois ou nada depois: não é o do crédito.
    assert not ex._credit_in_at(spans(("A", "In"), ("A", ": Renato")), 0)
    assert not ex._credit_in_at(spans(("B", "In"), ("A", " the beginning")), 0)
    assert not ex._credit_in_at(spans(("B", "In:")), 0)
    assert not ex._credit_in_at(spans(("A", "x "), ("A", "In:"), ("B", " Revista")), 1)


CBMTO_SOLDADO = FIXTURE.with_name("cbmto-2021-soldado-p7.pdf")


def test_style_from_the_distiller_name() -> None:
    """Fonte "TT14422oI00": itálico simulado pelo Distiller, com as larguras da face normal (sem serifa) e
    só 9 letras; o estilo vem do nome (CBM/TO 2021 soldado q36, emenda de 2026-10-14 da 0020)."""
    assert ex._name_style("TT14422oI00") == ex.ITALIC
    assert ex._name_style("TT14422oB00") == ex.BOLD
    assert ex._name_style("TT14422oBI00") == ex.BOLD | ex.ITALIC
    assert ex._name_style("TT14402o00") == 0
    assert ex._name_style("Swiss721BT-RomanCondense") == 0
    text = _text(ex.extract(CBMTO_SOLDADO, styles=True))
    assert "D Gerenciador de *downloads*" in text
    assert "dos *cookies* das páginas" in text
    assert "*Favoritos*" not in text  # a sem serifa normal das alternativas segue normal
    assert "*downloads*" not in _text(ex.extract(CBMTO_SOLDADO))  # desligado: como antes


PCPB_ESCRIVAO = FIXTURE.with_name("pcpb-2021-escrivao-p7.pdf")


def test_superscript_ordinal_becomes_ordinal_sign() -> None:
    """Lei n.º 8.072/1990": o "o" sobrescrito do original (corpo 6,5 sobre 10, marca de
    sobrescrito) é o "º" (PC/PB 2021 escrivão, pág. 7; emenda (14) da 0020)."""
    text = _text(ex.extract(PCPB_ESCRIVAO))
    assert "conforme previsão da Lei n.º 8.072/1990" in text
    assert "Estatuto do Desarmamento (Lei n.º" in text
    assert "n.o" not in text


def _sup(
    text: str, size: float = 6.5, flags: int = ex.SUPERSCRIPT, y: float = 95.4
) -> dict[str, object]:
    return {"text": text, "size": size, "flags": flags, "origin": (0.0, y)}


def _body(text: str) -> dict[str, object]:
    return {"text": text, "size": 10.0, "flags": 0, "origin": (0.0, 100.0)}


def _ordinal(*spans: dict[str, object]) -> str:
    return "".join(str(s["text"]) for s in ex._ordinal_signs(list(spans)))


def test_ordinal_sign_only_after_number_sign_or_numbered_abbreviation() -> None:
    assert _ordinal(_body("Lei n."), _sup("o"), _body(" 9.296/1996")) == "Lei n.º 9.296/1996"
    assert (
        _ordinal(_body("das Leis n."), _sup("os"), _body(" 9.605/1998"))
        == "das Leis n.ºs 9.605/1998"
    )
    assert _ordinal(_body("12."), _sup("a"), _body(" ed.")) == "12.ª ed."
    assert _ordinal(_body("compra: 1."), _sup("o"), _body("/7/20x0.")) == "compra: 1.º/7/20x0."
    assert _ordinal(_body("no § 1"), _sup("o"), _body(" do art.")) == "no § 1º do art."
    assert _ordinal(_body("OFÍCIO N"), _sup("o"), _body(" 000/ano")) == "OFÍCIO Nº 000/ano"
    # Sem a marca de sobrescrito, vale o corpo menor com a linha de base acima.
    assert _ordinal(_body("Lei n."), _sup("o", flags=0), _body(" 1")) == "Lei n.º 1"
    # Corpo menor na mesma linha de base é índice ("Vo", "n" com índice), não ordinal.
    assert _ordinal(_body("Lei n."), _sup("o", flags=0, y=100.0), _body(" 1")) == "Lei n.o 1"
    assert _ordinal(_body("V"), _sup("o"), _body(" é")) == "Vo é"
    # Número sem ponto pode ser ângulo ("30o"): fica como está.
    assert _ordinal(_body("que 30"), _sup("o"), _body(" foi")) == "que 30o foi"
    # "o" do mesmo corpo é letra comum; "o" sobrescrito colado em palavra seguinte não é ordinal.
    assert _ordinal(_body("Lei n."), _body("o"), _body(" 1")) == "Lei n.o 1"
    assert _ordinal(_body("n."), _sup("o"), _body("utra")) == "n.outra"


def test_few_letters_font_drawn_unlike_upright_takes_style_from_widths() -> None:
    """PC/PE 2023 P1 cargo 1, q14 (pág. 7): "*blitz*" numa fonte própria de 5 letras, abaixo das 6
    da margem por larguras e sem itálica deduzida na página para casar o desenho. Os glifos de
    mesmo nome da face normal têm outro desenho, e as larguras ("z" de 0,384) são as do Times
    itálico (emenda (17) da 0020). Só com `styles`."""
    pdf = CEBRASPE / "pcpe-2023-p1-cargo-1-p7.pdf"
    assert "Durante uma *blitz* de trânsito" in _text(ex.extract(pdf, styles=True))
    assert "*blitz*" not in _text(ex.extract(pdf))


def test_few_letters_style_needs_margin_from_upright() -> None:
    """Itálico e negrito itálico do Times medem igual "blitz": fica o estilo comum, o itálico.
    Larguras da face normal ou letras distintas de menos: nada."""
    refs = {name: pymupdf.Font(name) for name in ex.STYLE_FONTS}  # type: ignore[no-untyped-call]

    def widths(text: str, ref: str) -> list[tuple[str, float]]:
        return [(c, refs[ref].glyph_advance(ord(c))) for c in text]  # type: ignore[no-untyped-call]

    assert ex._few_letters_style(widths("blitz", "tiit"), refs) == ex.ITALIC
    assert ex._few_letters_style(widths("blitz", "tiro"), refs) == 0
    assert ex._few_letters_style(widths("zzt", "tiit"), refs) == 0
