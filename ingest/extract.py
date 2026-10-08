"""Etapa `extract`: PDF → linhas em ordem de leitura (SPECIFICATIONS.md §7.3).

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
from pathlib import Path
from typing import Any

import pymupdf
import yaml
from pydantic import BaseModel, ConfigDict

ITALIC = 2
BOLD = 16
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
    odd_glyph: bool = False  # dígito solto em fonte própria entre letras: símbolo sem mapeamento


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
    pdf_path: Path, *, ocr_dir: Path | None = None, fixes_dir: Path = FIXES_DIR
) -> list[Page]:
    """Páginas do PDF. Com `ocr_dir`, páginas sem texto passam pelo OCR (cache em `ocr_dir`)."""
    pages = _read(pdf_path)
    scanned = {page.number for page in pages if not page.has_text}
    if ocr_dir is not None and scanned:
        pages = _read(ocr(pdf_path, ocr_dir))
        for page in pages:
            if page.number in scanned:
                page.figures = _without_glyphs(page)
                _steady_sizes(page)
        _recover_item_numbers(pdf_path, pages, scanned)
        fixes_path = fixes_dir / f"{pdf_path.stem}.yaml"
        fixes = None
        if fixes_path.exists():
            fixes = OcrFixes.model_validate(yaml.safe_load(fixes_path.read_text("utf-8")))
            apply_fixes(pages, fixes)
        reader = OCR_ENGINE + (f"+revisado:{fixes.proofread_by}" if fixes else "")
        for page in pages:
            if page.number in scanned:
                page.ocr = reader
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


def _read(pdf_path: Path) -> list[Page]:
    with pymupdf.open(pdf_path) as document:  # type: ignore[no-untyped-call]
        return [_page(page) for page in document]


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


def _page(page: Any) -> Page:
    width, height = float(page.rect.width), float(page.rect.height)
    middle = width / 2
    lines: list[Line] = []
    for block in page.get_text("dict")["blocks"]:
        for raw in block.get("lines", []):
            line = _line(raw, middle)
            if line is not None:
                lines.append(line)
    return Page(
        number=page.number + 1,
        width=width,
        height=height,
        has_text=bool(lines),
        lines=_reading_order(lines),
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


def _line(raw: dict[str, Any], middle: float) -> Line | None:
    spans = [s for s in raw["spans"] if s["text"].strip(" \xa0")]
    if not spans or max(float(s["size"]) for s in spans) < MIN_SIZE:
        return None  # texto invisível (marcas de diagramação em corpo 1)
    x0, y0, x1, y1 = (float(v) for v in raw["bbox"])
    plain = _clean("".join(s["text"] for s in raw["spans"]))
    markdown = _clean("".join(_markdown(s) for s in raw["spans"]))
    if x0 >= middle:
        column = 2  # começa na metade direita (vale para números estreitos de item)
    elif x1 <= middle + COLUMN_SLACK:
        column = 1  # inclui o fim de linha da esquerda que encosta no meio ("a")
    elif x0 >= middle - COLUMN_SLACK:
        column = 2
    else:
        column = 0
    sizes = Counter(round(float(s["size"]), 1) for s in spans for _ in s["text"])
    main = sizes.most_common(1)[0][0]
    # O número do item no começo da linha costuma vir em corpo menor: não é índice.
    body = list(spans)
    while body and LEADING_MARK.match(body[0]["text"].strip(" \xa0")):
        body.pop(0)  # número do item ou de linha, glifo decorativo
    scripts = any(
        float(s["size"]) < main - SCRIPT_DROP
        and s["text"].strip(" \xa0")
        and not ORDINAL.match(s["text"].strip(" \xa0"))
        for s in body
    )
    # "P→Q" vira "P6Q" quando a seta vem de uma fonte sem mapeamento Unicode (CBM/AL 2017).
    odd_glyph = any(
        len(s["text"].strip()) == 1
        and s["text"].strip().isdigit()
        and s["font"] != spans[i - 1]["font"]
        and s["font"] != spans[i + 1]["font"]
        and spans[i - 1]["text"].rstrip()[-1:].isalpha()
        and spans[i + 1]["text"].lstrip()[:1].isalpha()
        for i, s in enumerate(spans)
        if 0 < i < len(spans) - 1
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


def _markdown(span: dict[str, Any]) -> str:
    text: str = span["text"]
    core = text.strip(" \xa0")
    if not core or not span["flags"] & (ITALIC | BOLD):
        return text
    mark = "**" if span["flags"] & BOLD else "*"
    start = text.index(core)
    return f"{text[:start]}{mark}{core}{mark}{text[start + len(core) :]}"


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
    text = re.sub(r"\*\\t/\*|\\t/", "", text)  # span de lixo "\t/" em itálico (PC/SE 2018)
    # Glifo de fonte matemática sem mapeamento sai como caractere de controle (\x0c para "μ"): vira
    # U+FFFD antes de normalizar espaços, para o parser marcar fórmula em vez de sumir com ele.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "\ufffd", text)
    return re.sub(r"\s+", " ", text).strip()


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
