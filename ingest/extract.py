"""Etapa `extract`: PDF → linhas em ordem de leitura (SPECIFICATION.md §7.3).

Saída em `pages.json`: uma lista de páginas, cada uma com as linhas já ordenadas. Layout em duas
colunas é resolvido por bandas: linhas que ocupam a largura toda separam bandas; dentro de cada
banda vem a coluna esquerda e depois a direita. Itálico e negrito viram Markdown restrito
(docs/content-format.md). Cabeçalhos e rodapés repetidos são descartados.

PDF digitalizado (página sem texto) passa antes pelo `ocrmypdf` com Tesseract `por` (decisão 0018):
só as páginas sem texto recebem a camada de OCR; o resultado fica em cache ao lado do original. As
linhas de OCR são revisadas pelo agente contra a imagem da página, e as correções ficam versionadas
em `ingest/ocr/<sha256>.yaml`.
"""

import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf
import yaml
from pydantic import BaseModel, ConfigDict

from ingest.content import escape_md

ITALIC = 2
BOLD = 16
# Fonte sem nome de família: TrueType convertida em Type 1 pelo Distiller ("TTD0ABo00", PF 2012).
UNNAMED_FONT = re.compile(r"^TT[0-9A-F]+o00$")
# Fontes-padrão do PDF (embutidas no PyMuPDF) usadas para deduzir o estilo pelas larguras.
STYLE_FONTS = {
    "tiro": 0, "tibo": BOLD, "tiit": ITALIC, "tibi": BOLD | ITALIC,
    "helv": 0, "hebo": BOLD, "heit": ITALIC, "hebi": BOLD | ITALIC,
}  # fmt: skip
UPRIGHT = {"tiit": "tiro", "tibi": "tibo", "heit": "helv", "hebi": "hebo"}
STYLE_TIE = 0.002  # diferença média de largura (em corpos) abaixo da qual itálico = normal
MAX_STYLE_DISTANCE = 0.02  # mais longe que isso de todas: fonte de símbolos, estilo desconhecido
MIN_STYLE_CHARS = 20
# Folga, em pontos, para considerar que a linha está de um lado do meio da página.
COLUMN_SLACK = 12.0
REPEATED_SHARE = 0.5  # linha presente em mais da metade das páginas = cabeçalho/rodapé
MARGIN_SHARE = 0.08  # faixa de cima e de baixo da página onde ficam cabeçalho e rodapé
MIN_SIZE = 3.0  # corpo menor que isso é marca invisível de diagramação
SCRIPT_DROP = 1.5  # pontos a menos que a fonte da linha: índice ou expoente
ITEM_NUMBER = re.compile(r"^\d{1,3}$")
LEADING_MARK = re.compile(r"^[\d\\/t*¦.]*$")
ORDINAL = re.compile(r"^[oaº]s?\.?$")  # "n.os", "1.a": abreviatura sobrescrita, não índice
FULL_WIDTH_SHARE = 0.8  # desenho mais largo que isso é moldura/faixa, não figura
MIN_RULE = 40.0  # régua horizontal mais curta que isso costuma ser sublinhado
SEPARATOR_SHARE = 0.4  # régua com ~ a largura da coluna
TABLE_ROW_GAP = 40.0  # réguas largas mais próximas que isso = linhas de tabela
DOUBLE_RULE_GAP = 6.0  # réguas mais próximas que isso formam um separador duplo


class Line(BaseModel):
    text: str  # texto com marcação Markdown (itálico, negrito)
    plain: str  # texto puro, para as regras do parser
    x0: float
    y0: float
    x1: float
    y1: float
    column: int  # 0 = largura total, 1 = esquerda, 2 = direita
    size: float  # tamanho da fonte predominante
    scripts: bool = False  # trechos em fonte bem menor no meio da linha (índices, expoentes)
    # Símbolo sem mapeamento: dígito solto em fonte própria entre letras, ou glifo de fonte de
    # símbolos que só tem pontuação ASCII na página.
    odd_glyph: bool = False


class Figure(BaseModel):
    """Imagem ou desenho vetorial (gráfico, tabela, ícone). Ainda não exportado como asset."""

    kind: str  # "image" | "drawing"
    x0: float
    y0: float
    x1: float
    y1: float


class Page(BaseModel):
    number: int  # 1-based
    width: float
    height: float
    has_text: bool
    lines: list[Line]
    figures: list[Figure]
    ocr: str | None = None  # quem leu e quem revisou o texto da página digitalizada


class LineFix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int
    ocr: str  # a linha como o OCR leu (texto puro)
    text: str  # a linha como está na página, em Markdown restrito (itálico, negrito)


class OcrFixes(BaseModel):
    """Revisão do OCR de um PDF pelo agente (`ingest/ocr/<sha256>.yaml`)."""

    model_config = ConfigDict(extra="forbid")

    document: str  # URL, para conferência
    proofread_by: str  # modelo/versão do agente revisor
    lines: list[LineFix] = []


class OcrFixError(Exception):
    """Correção de OCR que não casa com nenhuma linha: o OCR mudou, revisar de novo."""


OCR_LANGUAGE = "por"
OCR_ENGINE = "ocrmypdf+tesseract-por"
FIXES_DIR = Path(__file__).with_name("ocr")


GUTTER_WIDTH = 20.0  # pontos à direita da margem da coluna onde fica o número do item
GUTTER_DPI = 300
MIN_ITEM_SIZE = 5.0
GLYPH_SIZE = 14.0
SIZE_JITTER = 2.0  # o OCR dá corpos 7,5 a 8,9 para linhas do mesmo parágrafo  # desenho menor que isso nos dois lados é letra em curvas, não figura
NUMBERED = re.compile(r"^(\d{1,3})(?:\s|$)")


def extract(
    pdf_path: Path,
    *,
    ocr_dir: Path | None = None,
    fixes_dir: Path = FIXES_DIR,
    legacy: bool = False,
    styles: bool = False,
) -> list[Page]:
    """Páginas do PDF. Com `ocr_dir`, páginas sem texto passam pelo OCR (cache em `ocr_dir`).

    `legacy`: caderno do site antigo do Cebraspe (decisão 0020) — o vão entre as colunas, os
    números de item, o negrito/itálico e o "ℓ" são deduzidos do documento.
    `styles`: só o negrito/itálico das fontes sem nome ("TT…o00") é deduzido pelas larguras
    (decisão 0020, emenda de 2026-10-13); o resto segue como sem `legacy`. Sem fonte sem nome no
    documento, não muda nada.
    """
    pages = _read(pdf_path, legacy, styles)
    scanned = {page.number for page in pages if not page.has_text}
    if ocr_dir is not None and scanned:
        pages = _read(ocr(pdf_path, ocr_dir), legacy, styles)
        for page in pages:
            if page.number in scanned:
                page.figures = _without_glyphs(page)
                _steady_sizes(page)
        _recover_item_numbers(pdf_path, pages, scanned)
    # Correções revisadas pelo agente: linhas do OCR e, em página com texto, linhas numa fonte sem
    # mapeamento Unicode (o "PROVA OBJETIVA" do PF 2012 sai como "�������� ����").
    fixes_path = fixes_dir / f"{pdf_path.stem}.yaml"
    fixes = None
    if fixes_path.exists() and (ocr_dir is not None or not scanned):
        fixes = OcrFixes.model_validate(yaml.safe_load(fixes_path.read_text("utf-8")))
        apply_fixes(pages, fixes)
    if ocr_dir is not None and scanned:
        reader = OCR_ENGINE + (f"+revisado:{fixes.proofread_by}" if fixes else "")
        for page in pages:
            if page.number in scanned:
                page.ocr = reader
    if fixes:
        fixed = {fix.page for fix in fixes.lines} - scanned
        for page in pages:
            if page.number in fixed:
                page.ocr = f"revisado:{fixes.proofread_by}"
    _drop_repeated(pages)
    return pages


def apply_fixes(pages: list[Page], fixes: OcrFixes) -> None:
    """Troca cada linha lida pelo OCR pelo texto revisado. Correção sem linha → OcrFixError."""
    by_number = {page.number: page for page in pages}
    for fix in fixes.lines:
        page = by_number.get(fix.page)
        line = next((c for c in page.lines if c.plain == fix.ocr), None) if page else None
        if line is None:
            raise OcrFixError(f"página {fix.page}: linha não encontrada: {fix.ocr!r}")
        line.text = fix.text
        line.plain = fix.text.replace("*", "")


def _read(pdf_path: Path, legacy: bool = False, styles: bool = False) -> list[Page]:
    with pymupdf.open(pdf_path) as document:  # type: ignore[no-untyped-call]
        raws = []
        for page in document:
            lines = [
                raw for block in page.get_text("dict")["blocks"] for raw in block.get("lines", [])
            ]
            width = float(page.rect.width)
            middle = _gutter([raw["bbox"] for raw in lines], width) if legacy else width / 2
            raws.append((page, lines, middle))
        fonts = None
        if legacy:
            fonts = _Fonts(
                digits=_digit_fonts([(lines, middle) for _, lines, middle in raws]),
                styles=_font_styles(document),
                ell=_ell_fonts([lines for _, lines, _ in raws]),
                mono=_mono_fonts(document),
            )
        elif styles:
            fonts = _Fonts(digits={}, styles=_font_styles(document), legacy=False)
        decoded = frozenset(fonts.digits) if fonts else frozenset()  # dígitos já têm tradução
        return [
            _page(page, lines, middle, fonts, _symbol_fonts(lines) - decoded)
            for page, lines, middle in raws
        ]


def _ell_fonts(pages: list[list[dict[str, Any]]]) -> frozenset[str]:
    """Fontes de símbolos sem mapeamento em que o glifo do "ℓ" sai como "R" (decisão 0020): as que
    trazem um "R" sozinho entre "(" e ".<dígito>"."""
    fonts: set[str] = set()
    for raws in pages:
        for raw in raws:
            spans = raw["spans"]
            for before, span, after in zip(spans, spans[1:], spans[2:], strict=False):
                if _is_ell(before, span, after):
                    fonts.add(span["font"])
    return frozenset(fonts)


def _is_ell(before: dict[str, Any], span: dict[str, Any], after: dict[str, Any]) -> bool:
    return (
        span["text"] == "R"
        and span["font"] != before["font"]
        and span["font"] != after["font"]
        and before["text"].endswith("(")
        and re.match(r"\.\s?\d", after["text"]) is not None
    )


@dataclass
class _Fonts:
    """O que o PDF não diz das fontes e foi deduzido do documento (PF 2012)."""

    digits: dict[str, dict[str, str]]  # fonte → código → dígito
    styles: dict[str, int]  # fonte → BOLD/ITALIC
    ell: frozenset[str] = frozenset()  # fontes de símbolos do "ℓ" de "(ℓ.12)"
    mono: frozenset[str] = frozenset()  # fontes monoespaçadas (caminhos, comandos): código inline
    # False: só o estilo foi deduzido (`styles`); números de item, "ℓ", "*In*" e o dígito em negrito
    # seguem as regras de quem não é `legacy`.
    legacy: bool = True


MONO_MIN_LETTERS = 8  # letras distintas para afirmar que a fonte é monoespaçada
MONO_SPREAD = 0.01  # diferença máxima de largura (em corpos) entre as letras


def _mono_fonts(document: Any) -> frozenset[str]:
    """Fontes sem nome em que toda letra tem a mesma largura (Courier convertida pelo Distiller,
    PF 2012 escrivão: "C:\\Users\\joao_jose", "print://<IP_da_impressora>"). O original usa a
    fonte monoespaçada para caminhos, endereços e comandos: no Markdown viram código inline
    (docs/content-format.md). Com letras de menos, a largura não prova nada e a fonte fica de fora."""
    widths: dict[str, dict[str, list[float]]] = {}
    for page in document:
        for block in page.get_text("rawdict")["blocks"]:
            for raw in block.get("lines", []):
                for span in raw["spans"]:
                    if not UNNAMED_FONT.match(span["font"]):
                        continue
                    for char in span["chars"]:
                        if char["c"].isascii() and char["c"].isalpha():
                            width = (char["bbox"][2] - char["bbox"][0]) / span["size"]
                            widths.setdefault(span["font"], {}).setdefault(char["c"], []).append(
                                width
                            )
    mono: set[str] = set()
    for font, letters in widths.items():
        means = [sum(ws) / len(ws) for ws in letters.values()]
        if len(means) >= MONO_MIN_LETTERS and max(means) - min(means) <= MONO_SPREAD:
            mono.add(font)
    return frozenset(mono)


def _font_styles(document: Any) -> dict[str, int]:
    """Negrito e itálico de fontes sem nome (PF 2012: "TTD0ACo00", descritor sem peso nem ângulo).

    A largura de cada letra denuncia o estilo: comparada com a das fontes-padrão do PDF (Times e
    Helvetica, normal, negrito, itálico, negrito itálico), a mais próxima dá o estilo. Helvetica
    normal e oblíqua têm as mesmas larguras: no empate fica a normal.
    """
    advances: dict[str, list[tuple[str, float]]] = {}
    credit_in: set[str] = set()  # fontes do "*In*:" do crédito
    for page in document:
        for block in page.get_text("rawdict")["blocks"]:
            for raw in block.get("lines", []):
                spans = raw["spans"]
                for i, span in enumerate(spans):
                    if not UNNAMED_FONT.match(span["font"]):
                        continue
                    if 0 < i < len(spans) - 1 and _credit_in(spans[i - 1], span, spans[i + 1]):
                        credit_in.add(span["font"])
                    for char in span["chars"]:
                        if char["c"].isascii() and char["c"].isalpha():
                            width = (char["bbox"][2] - char["bbox"][0]) / span["size"]
                            advances.setdefault(span["font"], []).append((char["c"], width))
    if not advances:
        return {}
    references = {name: pymupdf.Font(name) for name in STYLE_FONTS}  # type: ignore[no-untyped-call]
    styles: dict[str, int] = {}
    for font, chars in advances.items():
        if len(chars) < MIN_STYLE_CHARS:
            continue
        distance = {
            name: sum(
                abs(width - ref.glyph_advance(ord(c)))  # type: ignore[no-untyped-call]
                for c, width in chars
            )
            / len(chars)
            for name, ref in references.items()
        }
        best = min(distance, key=lambda name: distance[name])
        upright = UPRIGHT.get(best)
        if upright and distance[upright] - distance[best] < STYLE_TIE:
            best = upright
        if distance[best] <= MAX_STYLE_DISTANCE:
            styles[font] = STYLE_FONTS[best]
    # Fonte com letras de menos para as larguras, mas que escreve o "In" de "*In*:" do crédito: é a
    # itálica miúda do crédito, e o resto dela também é itálico ("*et al*.", PF 2018).
    for font in credit_in - styles.keys():
        if len(advances.get(font, [])) < MIN_STYLE_CHARS:
            styles[font] = ITALIC
    return styles


def _span_text(span: dict[str, Any]) -> str:
    if "text" in span:
        return str(span["text"])
    return "".join(char["c"] for char in span.get("chars", []))


def _credit_in(before: dict[str, Any], span: dict[str, Any], after: dict[str, Any]) -> bool:
    """O "In" de "*In*:" do crédito, numa fonte própria entre vizinhas de outra fonte."""
    return (
        _span_text(span) == "In"
        and span["font"] != before["font"]
        and span["font"] != after["font"]
        and _span_text(after).startswith(":")
    )


def _gutter(boxes: list[Any], width: float) -> float:
    """Meio do vão entre as colunas.

    Em geral é a metade da largura. Há cadernos em que não é (PF 2012: colunas de 28–312 e 325–567
    pt numa página de 595, e a coluna da esquerda passava do meio): se alguma linha cruza a metade
    e outra posição entre 35% e 65% da largura é cruzada por menos linhas, o vão é a faixa menos
    cruzada mais perto do meio. Página de uma coluna só: tudo empata e fica a metade.
    """
    middle = width / 2
    xs = range(round(width * 0.35), round(width * 0.65) + 1)
    crossing = {x: sum(1 for x0, _, x1, _ in boxes if x0 < x < x1) for x in xs}
    fewest = min(crossing.values(), default=0)
    if sum(1 for x0, _, x1, _ in boxes if x0 < middle < x1) == fewest:
        return middle
    runs: list[list[int]] = []
    for x in xs:
        if crossing[x] != fewest:
            continue
        if runs and runs[-1][-1] == x - 1:
            runs[-1].append(x)
        else:
            runs.append([x])
    best = min(runs, key=lambda run: min(abs(x - middle) for x in run))
    return (best[0] + best[-1]) / 2


def _digit_fonts(pages: list[tuple[list[dict[str, Any]], float]]) -> dict[str, dict[str, str]]:
    """Fontes de número de item sem mapeamento Unicode → tabela código → dígito.

    O PF 2012 escreve os números de item numa fonte subconjunto, com nomes de glifo opacos ("g20")
    e sem ToUnicode: o texto sai em códigos de controle ("\\x02\\x0b" para 10). Os itens seguem 1,
    2, 3..., então, na ordem de leitura, os nove primeiros números de um glifo só são os códigos de
    1 a 9 e o código que sobra é o 0. A tabela só vale se todos os números da fonte virarem uma
    sequência de um em um; senão a fonte é outra coisa (fórmula, símbolo) e fica como está.
    """
    tokens: dict[str, list[tuple[int, int, float, float, str]]] = {}
    for index, (lines, middle) in enumerate(pages):
        for raw in lines:
            for span in raw["spans"]:
                text = span["text"]
                if not text or len(text) > 3 or any(ord(c) >= 32 for c in text):
                    continue
                x0, y0, x1, _ = (float(v) for v in span["bbox"])
                key = (index, _column(x0, x1, middle), y0, x0, text)
                tokens.setdefault(span["font"], []).append(key)
    tables: dict[str, dict[str, str]] = {}
    for font, found in tokens.items():
        texts = [text for *_, text in sorted(found)]
        singles = list(dict.fromkeys(text for text in texts if len(text) == 1))
        zero = {c for text in texts for c in text} - set(singles)
        if len(singles) != 9 or len(zero) != 1:
            continue
        table = {code: str(i + 1) for i, code in enumerate(singles)} | {zero.pop(): "0"}
        numbers = [int("".join(table[c] for c in text)) for text in texts]
        if numbers == list(range(numbers[0], numbers[0] + len(numbers))):
            tables[font] = table
    return tables


def ocr(pdf_path: Path, ocr_dir: Path) -> Path:
    """Cópia do PDF com camada de texto nas páginas sem texto. Reaproveita a cópia já feita."""
    target = ocr_dir / pdf_path.name
    if target.exists():
        return target
    ocr_dir.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial.pdf")
    subprocess.run(
        [
            sys.executable, "-m", "ocrmypdf", "--skip-text", "--language", OCR_LANGUAGE,
            "--output-type", "pdf", "--quiet", str(pdf_path), str(partial),
        ],
        check=True,
    )  # fmt: skip
    partial.rename(target)
    return target


def _recover_item_numbers(pdf_path: Path, pages: list[Page], scanned: set[int]) -> None:
    """Devolve números de item que o OCR da página inteira perdeu.

    O Tesseract descarta dígitos isolados na margem (o número em negrito, longe do texto). Para
    cada coluna de página digitalizada, a faixa onde ficam os números já reconhecidos passa por um
    OCR só de dígitos; o número entra na linha da mesma altura que ainda não tem número, e só se
    cabe na sequência entre os números vizinhos já conhecidos (o que barra lixo do OCR).
    """
    found: list[tuple[Line, int, float]] = []  # (linha, número, x do número)
    with pymupdf.open(pdf_path) as document:  # type: ignore[no-untyped-call]
        for page in pages:
            if page.number not in scanned:
                continue
            for column in (1, 2):
                numbered = [
                    line for line in page.lines
                    if line.column == column and NUMBERED.match(line.plain)
                ]  # fmt: skip
                if not numbered:
                    continue
                left = min(line.x0 for line in numbered) - 3
                for x, y, number in _gutter_digits(document[page.number - 1], left):
                    for line in page.lines:
                        if line.column == column and line.y0 - 2 <= y <= line.y1 + 2:
                            if not NUMBERED.match(line.plain):
                                found.append((line, number, x))
                            break
    if not found:
        return
    targets = {id(line): (number, x) for line, number, x in found}
    order = [line for page in pages for line in page.lines]
    known = [  # fonte miúda: número de página no rodapé, não item
        (i, int(m.group(1)))
        for i, line in enumerate(order)
        if (m := NUMBERED.match(line.plain)) and line.column in (1, 2) and line.size > MIN_ITEM_SIZE
    ]
    for i, line in enumerate(order):
        target = targets.get(id(line))
        if target is None:
            continue
        number, x = target
        before = max((n for j, n in known if j < i), default=0)
        after = min((n for j, n in known if j > i), default=10**3)
        if before < number < after:
            line.text = f"{number} {line.text}"
            line.plain = f"{number} {line.plain}"
            line.x0 = x
            known.append((i, number))
            known.sort()


def _steady_sizes(page: Page) -> None:
    """Na página digitalizada o corpo da linha vem da altura da caixa do OCR e oscila: o corpo
    perto da mediana vira a mediana, e não há índice nem expoente reconhecíveis. Número miúdo
    solto (número de página no rodapé) é ruído."""
    page.lines = [
        line for line in page.lines
        if not (line.size < MIN_ITEM_SIZE and re.fullmatch(r"\d{1,3}", line.plain))
    ]  # fmt: skip
    if not page.lines:
        return
    sizes = sorted(line.size for line in page.lines)
    median = sizes[len(sizes) // 2]
    for line in page.lines:
        line.scripts = False
        if abs(line.size - median) < SIZE_JITTER:
            line.size = median


def _without_glyphs(page: Page) -> list[Figure]:
    """Em página digitalizada com texto em curvas, cada letra é um desenho: fora com eles."""

    def glyph(figure: Figure) -> bool:
        small = figure.x1 - figure.x0 < GLYPH_SIZE and figure.y1 - figure.y0 < GLYPH_SIZE
        inside = any(
            line.x0 - 2 <= figure.x0 and figure.x1 <= line.x1 + 2
            and line.y0 - 2 <= figure.y0 and figure.y1 <= line.y1 + 2
            for line in page.lines
        )  # fmt: skip
        return small or inside

    return [f for f in page.figures if f.kind == "image" or not glyph(f)]


def _gutter_digits(page: Any, left: float) -> list[tuple[float, float, int]]:
    """(x, altura do centro, número) dos dígitos na faixa de margem que começa em `left`."""
    clip = pymupdf.Rect(left, 0, left + GUTTER_WIDTH, page.rect.height)  # type: ignore[no-untyped-call]
    image = page.get_pixmap(dpi=GUTTER_DPI, clip=clip).tobytes("png")
    result = subprocess.run(
        [
            "tesseract", "-", "-", "--psm", "6", "-l", "eng",
            "-c", "tessedit_char_whitelist=0123456789", "tsv",
        ],
        input=image, capture_output=True, check=True,
    )  # fmt: skip
    scale = 72 / GUTTER_DPI
    digits = []
    for row in result.stdout.decode().splitlines()[1:]:
        cells = row.split("\t")
        if len(cells) == 12 and re.fullmatch(r"\d{1,3}", cells[11].strip()):
            x, top, height = int(cells[6]), int(cells[7]), int(cells[9])
            digits.append((left + x * scale, (top + height / 2) * scale, int(cells[11])))
    return digits


def _page(
    page: Any,
    raws: list[dict[str, Any]],
    middle: float,
    fonts: _Fonts | None,
    symbol_fonts: frozenset[str],
) -> Page:
    width, height = float(page.rect.width), float(page.rect.height)
    lines: list[Line] = []
    for raw in raws:
        line = _line(raw, middle, fonts, symbol_fonts)
        if line is not None:
            lines.append(line)
    return Page(
        number=page.number + 1,
        width=width,
        height=height,
        has_text=bool(lines),
        lines=_reading_order(
            _attach_item_numbers(lines) if fonts is not None and fonts.legacy else lines
        ),
        figures=_figures(page, width),
    )


def _figures(page: Any, width: float) -> list[Figure]:
    """Imagens e desenhos, menos as faixas de largura total (fundo de títulos, réguas)."""
    figures = [Figure(kind="image", **_box(info["bbox"])) for info in page.get_image_info()]
    for drawing in page.get_drawings():
        box = _box(drawing["rect"])
        w, h = box["x1"] - box["x0"], box["y1"] - box["y0"]
        if w > FULL_WIDTH_SHARE * width:
            continue
        # Retângulos (células, barras) ou réguas horizontais longas (tabelas sem fundo).
        if (w > 3 and h > 3) or (h <= 3 and w > MIN_RULE):
            figures.append(Figure(kind="drawing", **box))
    figures = [f for f in figures if f.x1 > 0 and f.x0 < width]
    return [f for f in figures if not _is_separator(f, figures, width)]


def _is_separator(figure: Figure, figures: list[Figure], width: float) -> bool:
    """Régua isolada da largura de uma coluna: separa grupos de itens, não é tabela."""
    if figure.y1 - figure.y0 > 3 or figure.x1 - figure.x0 < SEPARATOR_SHARE * width:
        return False
    return not any(
        other is not figure
        and other.y1 - other.y0 <= 3
        and other.x1 - other.x0 >= SEPARATOR_SHARE * width
        and abs(other.x0 - figure.x0) < 10
        and DOUBLE_RULE_GAP < abs(other.y0 - figure.y0) < TABLE_ROW_GAP
        for other in figures
    )


def _box(rect: Any) -> dict[str, float]:
    x0, y0, x1, y1 = (float(v) for v in rect)
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


# Fonte de símbolos matemáticos sem mapeamento Unicode que sai como pontuação ASCII: "P(Z ≤ −2)"
# vira "P(Z # !2)" e "≥" vira "$" (PF 2018). O nome embutido não diz qual fonte é, então o glifo não
# tem tradução segura: a linha fica marcada como fórmula e a questão vai para revisão.
SYMBOL_ASCII = frozenset(
    "!\"#$%&'*+/<=>@[\\]^_`{|}~þ"
)  # "þ": reticências da mesma fonte (ver SYMBOL_PUA)


def _symbol_fonts(raws: list[dict[str, Any]]) -> frozenset[str]:
    """Fontes da página cujo texto inteiro é pontuação ASCII isolada: símbolos sem mapeamento."""
    chars: dict[str, set[str]] = {}
    for raw in raws:
        for span in raw["spans"]:
            chars.setdefault(span["font"], set()).update(span["text"].replace("\xa0", " "))
    return frozenset(
        font for font, used in chars.items() if (used - {" "}) and used - {" "} <= SYMBOL_ASCII
    )


def _line(
    raw: dict[str, Any],
    middle: float,
    fonts: _Fonts | None = None,
    symbol_fonts: frozenset[str] = frozenset(),
) -> Line | None:
    if fonts and any(
        s["font"] in fonts.digits or s["font"] in fonts.styles or s["font"] in fonts.mono
        for s in raw["spans"]
    ):
        decoded = []
        for s in raw["spans"]:
            if s["font"] in fonts.digits:
                s = s | {"text": "".join(fonts.digits[s["font"]].get(c, c) for c in s["text"])}
            if s["font"] in fonts.mono:
                s = s | {"mono": True}
            elif s["font"] in fonts.styles and any(c.isalnum() for c in s["text"]):
                # Só pontuação ("Austrália*.*"): o estilo não aparece e só suja o Markdown.
                s = s | {"flags": s["flags"] | fonts.styles[s["font"]]}
            decoded.append(s)
        raw = raw | {"spans": decoded}
    raw = raw | {"spans": _line_refs(raw["spans"], legacy=fonts is not None and fonts.legacy)}
    spans = [s for s in raw["spans"] if s["text"].strip(" \xa0")]
    if not spans or max(float(s["size"]) for s in spans) < MIN_SIZE:
        return None  # texto invisível (marcas de diagramação em corpo 1)
    x0, y0, x1, y1 = (float(v) for v in raw["bbox"])
    plain = _clean("".join(s["text"] for s in raw["spans"]))
    markdown = _clean("".join(_markdown(s) for s in raw["spans"]))
    column = _column(x0, x1, middle)
    # O número do item no começo da linha costuma vir em corpo menor: não é índice.
    body = list(spans)
    while body and LEADING_MARK.match(body[0]["text"].strip(" \xa0")):
        body.pop(0)  # número do item ou de linha, glifo decorativo
    # O corpo da linha sai do texto, sem o número do item: em linha justificada, cada palavra pode
    # vir numa linha própria, e "106 É" tinha mais letras no corpo do número (8 pt) que no do texto
    # (10 pt); unida às vizinhas, a linha parecia um índice (PF 2012 delegado, item 106).
    sizes = Counter(round(float(s["size"]), 1) for s in (body or spans) for _ in s["text"])
    main = sizes.most_common(1)[0][0]
    scripts = any(
        float(s["size"]) < main - SCRIPT_DROP
        and s["text"].strip(" \xa0")
        and not ORDINAL.match(s["text"].strip(" \xa0"))
        for s in body
    )
    # "P→Q" vira "P6Q" quando a seta vem de uma fonte sem mapeamento Unicode (CBM/AL 2017).
    odd_glyph = (
        any(
            len(s["text"].strip()) == 1
            and s["text"].strip().isdigit()
            # "julgue os itens de **5** a **11**" (PF 2012)
            and not (fonts and fonts.legacy and s["flags"] & BOLD)
            and s["font"] != spans[i - 1]["font"]
            and s["font"] != spans[i + 1]["font"]
            and spans[i - 1]["text"].rstrip()[-1:].isalpha()
            and spans[i + 1]["text"].lstrip()[:1].isalpha()
            for i, s in enumerate(spans)
            if 0 < i < len(spans) - 1
        )
        or any(s["font"] in symbol_fonts and s["text"].strip(" \xa0þ") for s in spans)
        or (fonts is not None and fonts.legacy and _odd_ell_glyph(spans, fonts.ell))
    )
    return Line(
        text=markdown,
        plain=plain,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        column=column,
        odd_glyph=odd_glyph,
        size=main,
        scripts=scripts,
    )


def _odd_ell_glyph(spans: list[dict[str, Any]], ell: frozenset[str]) -> bool:
    """Outro glifo da fonte do "ℓ" no meio do texto: símbolo sem mapeamento ("P∧Q" sai "PvQ",
    "kJ·mol" sai "kJ@mol", "Cℓ" fora de "(ℓ.N)" sai "CR"; PF 2012). Glifo sozinho na linha (a
    tecla Enter desenhada como "<") não é texto."""
    if not any(s["font"] not in ell for s in spans):
        return False
    return any(s["font"] in ell and s["text"].strip(" \xa0") not in ("", "ℓ") for s in spans)


def _line_refs(spans: list[dict[str, Any]], legacy: bool = False) -> list[dict[str, Any]]:
    """ "(ℓ.12)": o "ℓ" vem numa fonte de símbolos própria cujo glifo se chama "R" e que mapeia para
    "R" (PF 2012, PF 2018, PM/AL 2017...). Um "R" sozinho em fonte diferente das vizinhas, entre "("
    e ".<dígito>", é o ℓ. O "*In*" só vale no site antigo (`legacy`)."""
    result = list(spans)
    for i in range(1, len(spans) - 1):
        before, span, after = spans[i - 1], spans[i], spans[i + 1]
        if _is_ell(before, span, after):
            result[i] = span | {"text": "ℓ"}
        elif legacy and _credit_in(before, span, after):
            # "*In*:" do crédito numa fonte própria, com letras de menos para deduzir o estilo.
            result[i] = span | {"flags": span["flags"] | ITALIC}
    return result


def _column(x0: float, x1: float, middle: float) -> int:
    if x0 >= middle:
        return 2  # começa na metade direita (vale para números estreitos de item)
    if x1 <= middle + COLUMN_SLACK:
        return 1  # inclui o fim de linha da esquerda que encosta no meio ("a")
    if x0 >= middle - COLUMN_SLACK:
        return 2
    return 0


def _markdown(span: dict[str, Any]) -> str:
    if span.get("mono"):
        return _code(span["text"])
    text = escape_md(span["text"])
    core = text.strip(" \xa0")
    if not core or not span["flags"] & (ITALIC | BOLD):
        return text
    mark = "**" if span["flags"] & BOLD else "*"
    start = text.index(core)
    return f"{text[:start]}{mark}{core}{mark}{text[start + len(core) :]}"


def _code(text: str) -> str:
    """Trecho em fonte monoespaçada → código inline. Dentro do código o Markdown não tem escape:
    o texto vai como está, e a crase do original pede delimitador mais longo."""
    core = text.strip(" \xa0")
    if not core:
        return text
    start = text.index(core)
    fence = "``" if "`" in core else "`"
    inner = f" {core} " if fence == "``" else core
    return f"{text[:start]}{fence}{inner}{fence}{text[start + len(core) :]}"


# Fonte Symbol embutida sem mapeamento Unicode: o glifo sai na área de uso privado (U+F0xx), com o
# código da fonte Symbol no byte baixo. Os que aparecem nas provas viram o caractere certo; o resto
# fica como está e cai na regra de fórmula do parser.
SYMBOL_PUA = str.maketrans(
    {
        0xF020: " ",
        0xF02D: "−",
        0xF044: "Δ",
        0xF065: "ε",
        0xF06D: "μ",
        0xF071: "θ",
        0xF0AE: "→",
        0xF0B4: "×",
        0xF0B7: "•",
        0xF0D7: "·",
        0xF0DA: "∨",
        0x00FE: "…",  # "þ": reticências de fonte sem mapeamento (CBM/AL 2017); não existe em português
    }
)


def _clean(text: str) -> str:
    text = text.translate(SYMBOL_PUA).replace("\xa0", " ").replace("­", "")
    text = text.replace("FimDoTexto", " ")  # marcador invisível de fim de texto (Cebraspe)
    # span de lixo "\t/" em itálico (PC/SE 2018); no Markdown a barra vem escapada
    text = re.sub(r"\*\\{1,2}t/\*|\\{1,2}t/", "", text)
    # Glifo de fonte matemática sem mapeamento sai como caractere de controle (\x0c para "μ"): vira
    # U+FFFD antes de normalizar espaços, para o parser marcar fórmula em vez de sumir com ele.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "\ufffd", text)
    return re.sub(r"\s+", " ", text).strip()


ITEM_NUMBER_ONLY = re.compile(r"^\d{1,3}$")
ITEM_NUMBER_GAP = 25.0  # pt entre o número na margem e o começo do texto do item


def _attach_item_numbers(lines: list[Line]) -> list[Line]:
    """Número de item sozinho na margem, ao lado de uma linha de largura total (site antigo do
    Cebraspe, decisão 0020: página de química do PF 2012 papiloscopista em uma coluna só).

    O número vem em fonte menor, numa linha própria um pouco abaixo do topo do texto; na ordem de
    leitura ele caía depois da linha do item, e cada item ficava com o texto do seguinte. Na mesma
    altura e logo à esquerda do texto, o número passa a abrir a linha de largura total."""
    wide = [line for line in lines if line.column == 0]
    attached: dict[int, Line] = {}  # id da linha de largura total → linha já com o número
    dropped: set[int] = set()
    for number in lines:
        if number.column == 0 or not ITEM_NUMBER_ONLY.match(number.plain.strip()):
            continue
        target = next(
            (
                line
                for line in wide
                if _same_row(line, number)
                and 0 <= line.x0 - number.x1 <= ITEM_NUMBER_GAP
                and number.size <= line.size
                and id(line) not in attached
            ),
            None,
        )
        if target is None:
            continue
        attached[id(target)] = target.model_copy(
            update={
                "text": f"{number.text} {target.text}",
                "plain": f"{number.plain.strip()} {target.plain}",
                "x0": number.x0,
                "y0": min(number.y0, target.y0),
                "y1": max(number.y1, target.y1),
            }
        )
        dropped.add(id(number))
    return [attached.get(id(line), line) for line in lines if id(line) not in dropped]


def _reading_order(lines: list[Line]) -> list[Line]:
    """Bandas separadas por linhas de largura total; em cada banda, coluna 1 e depois 2."""
    lines = sorted(lines, key=lambda line: (line.y0, line.x0))
    ordered: list[Line] = []
    band: list[Line] = []
    for line in lines:
        if line.column == 0:
            ordered.extend(_rows(band))
            band = []
            ordered.append(line)
        else:
            band.append(line)
    ordered.extend(_rows(band))
    return ordered


def _rows(lines: list[Line]) -> list[Line]:
    """Por coluna, junta numa linha só os pedaços na mesma altura (número do item, índices)."""
    result: list[Line] = []
    for column in (1, 2):
        row: list[Line] = []
        for line in sorted((item for item in lines if item.column == column), key=_top):
            if row and not _same_row(row[0], line):
                result.append(_merge(row))
                row = []
            row.append(line)
        if row:
            result.append(_merge(row))
    return result


def _top(line: Line) -> tuple[float, float]:
    return (line.y0, line.x0)


def _same_row(first: Line, line: Line) -> bool:
    """Sobreposição vertical de mais da metade da linha menor."""
    overlap = min(first.y1, line.y1) - max(first.y0, line.y0)
    return overlap > 0.5 * min(first.y1 - first.y0, line.y1 - line.y0)


def _merge(row: list[Line]) -> Line:
    if len(row) == 1:
        return row[0]
    row = sorted(row, key=lambda line: line.x0)
    main = max(row, key=lambda line: line.size)
    return Line(
        text=" ".join(line.text for line in row),
        plain=" ".join(line.plain for line in row),
        x0=row[0].x0,
        y0=min(line.y0 for line in row),
        x1=max(line.x1 for line in row),
        y1=max(line.y1 for line in row),
        column=row[0].column,
        odd_glyph=any(line.odd_glyph for line in row),
        size=main.size,
        scripts=any(line.scripts for line in row)
        or any(
            line.size < main.size - SCRIPT_DROP and not LEADING_MARK.match(line.plain)
            for line in row
        ),
    )


def _drop_repeated(pages: list[Page]) -> None:
    """Remove cabeçalhos e rodapés: texto repetido em várias páginas, sempre nas margens."""
    if len(pages) < 2:
        return
    counts: Counter[str] = Counter()
    outside: set[str] = set()  # textos que aparecem fora das margens em alguma página
    for page in pages:
        counts.update({line.plain for line in page.lines})
        margin = MARGIN_SHARE * page.height
        outside.update(
            line.plain for line in page.lines if margin < line.y0 and line.y1 < page.height - margin
        )
    needed = max(2, int(REPEATED_SHARE * len(pages)) + 1)
    repeated = {
        text
        for text, count in counts.items()
        if count >= needed and text not in outside and not re.fullmatch(r"\d+", text)
    }
    for page in pages:
        page.lines = [line for line in page.lines if line.plain not in repeated]
