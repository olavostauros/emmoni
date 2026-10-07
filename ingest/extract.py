"""Etapa `extract`: PDF → linhas em ordem de leitura (SPECIFICATIONS.md §7.3).

Saída em `pages.json`: uma lista de páginas, cada uma com as linhas já ordenadas. Layout em duas
colunas é resolvido por bandas: linhas que ocupam a largura toda separam bandas; dentro de cada
banda vem a coluna esquerda e depois a direita. Itálico e negrito viram Markdown restrito
(docs/content-format.md). Cabeçalhos e rodapés repetidos são descartados.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Any

import pymupdf
from pydantic import BaseModel

ITALIC = 2
BOLD = 16
# Folga, em pontos, para considerar que a linha está de um lado do meio da página.
COLUMN_SLACK = 12.0
REPEATED_SHARE = 0.5  # linha presente em mais da metade das páginas = cabeçalho/rodapé
MARGIN_SHARE = 0.08  # faixa de cima e de baixo da página onde ficam cabeçalho e rodapé
SCRIPT_DROP = 1.5  # pontos a menos que a fonte da linha: índice ou expoente
ITEM_NUMBER = re.compile(r"^\d{1,3}$")
ORDINAL = re.compile(r"^[oaº]s?\.?$")  # "n.os", "1.a": abreviatura sobrescrita, não índice
FULL_WIDTH_SHARE = 0.8  # desenho mais largo que isso é moldura/faixa, não figura
MIN_RULE = 40.0  # régua horizontal mais curta que isso costuma ser sublinhado
SEPARATOR_SHARE = 0.4  # régua com ~ a largura da coluna
TABLE_ROW_GAP = 40.0  # réguas largas mais próximas que isso = linhas de tabela


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


def extract(pdf_path: Path) -> list[Page]:
    with pymupdf.open(pdf_path) as document:  # type: ignore[no-untyped-call]
        pages = [_page(page) for page in document]
    _drop_repeated(pages)
    return pages


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
        and abs(other.y0 - figure.y0) < TABLE_ROW_GAP
        for other in figures
    )


def _box(rect: Any) -> dict[str, float]:
    x0, y0, x1, y1 = (float(v) for v in rect)
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


def _line(raw: dict[str, Any], middle: float) -> Line | None:
    spans = [s for s in raw["spans"] if s["text"].strip(" \xa0")]
    if not spans:
        return None
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
    body = spans[1:] if ITEM_NUMBER.match(spans[0]["text"].strip(" \xa0")) else spans
    scripts = any(
        float(s["size"]) < main - SCRIPT_DROP
        and s["text"].strip(" \xa0")
        and not ORDINAL.match(s["text"].strip(" \xa0"))
        for s in body
    )
    return Line(
        text=markdown,
        plain=plain,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        column=column,
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


def _clean(text: str) -> str:
    text = text.replace("\xa0", " ").replace("­", "")
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
            line.size < main.size - SCRIPT_DROP and not ITEM_NUMBER.match(line.plain)
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
