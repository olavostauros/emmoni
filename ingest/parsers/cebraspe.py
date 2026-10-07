"""Parser do Cebraspe: provas de itens certo/errado e gabaritos (SPECIFICATIONS.md §7.3).

Modelo de uma prova objetiva do Cebraspe:

- Itens numerados em sequência (1..N), número em negrito na margem da coluna, continuação com recuo.
- Antes de cada grupo de itens vem a **abertura**: um texto-base rotulado ("Texto 2A1-I"), uma
  situação hipotética e/ou o **comando** ("Com relação a X, julgue os itens a seguir.").
- Pela regra da banca, cada item está vinculado ao comando que o antecede. Por isso o comando abre
  o enunciado de cada item do grupo; o texto rotulado ou a situação vira texto-base (`passage`).

Tudo o que as regras não conseguem reproduzir com fidelidade (figuras, fórmulas com glifos não
mapeados, layout especial) é marcado em `flags` e a questão vai para revisão.
"""

import re
from dataclasses import dataclass, field

from ingest.extract import Figure, Line, Page
from ingest.staging import AnswerKey, AnswerMark, RawPassage, RawQuestion, Segmented

PARSER = "cebraspe-parser@1"

START = re.compile(r"^-+ ?PROVA OBJETIVA ?-+$")
STOP = re.compile(r"^-+ ?PROVA DISCURSIVA ?-+$")
SKIP = re.compile(r"^(BLOCO [IVX]+|Espaço livre|-+ ?PROVA OBJETIVA ?-+|\d+_[A-Z0-9_]+)$", re.I)
ITEM = re.compile(r"^(\d{1,3})\s+\S")
ITEM_MD = re.compile(r"^(?:\*\*)?\d{1,3}(?:\*\*)?\s+")
TEXT_LABEL = re.compile(r"^Texto\s+([0-9A-Z][\w.]*(?:-[IVX]+)?)$")
TEXT_REF = re.compile(r"\btexto\s+([0-9][\w.]*-[IVX]+|[0-9][A-Z0-9.]+)", re.I)
COMMAND = re.compile(r"\bjulg", re.I)
SENTENCE_END = re.compile(r"(?<=[.!?:])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ“])")
# Glifos de fontes matemáticas sem mapeamento Unicode correto (Cambria Math exportada pelo
# Distiller sai como etíope, malaiala, oriá...) e letras matemáticas (𝑋, 𝛾).
BROKEN_MATH = re.compile(r"[଀-୿ഀ-ൿሀ-፿\U0001D400-\U0001D7FF]")

SENTENCE_STOP = (".", ":", ";", "?", "!")
ITEM_INDENT = 6.0  # número do item fica na margem da coluna
HANGING_MIN = 8.0  # continuação do item tem recuo (~18)
HANGING_MAX = 24.0
PARAGRAPH_INDENT = 15.0  # primeira linha de parágrafo de texto-base
PARAGRAPH_INDENT_AT = 29.0  # recuo típico de parágrafo (a continuação de item fica em ~18)
SHORT_LINE = 40.0  # linha que termina antes disso da margem direita quebra de propósito
ODD_INDENT = 30.0  # recuo maior que isso dentro de item = layout especial (código, tabela)


@dataclass
class _Entry:
    page: int
    line: Line
    left: float  # margem esquerda da coluna desta linha
    short: bool = False  # termina bem antes da margem direita da coluna
    flags: set[str] = field(default_factory=set)


@dataclass
class _Unit:
    entries: list[_Entry] = field(default_factory=list)

    @property
    def flags(self) -> set[str]:
        return set().union(*(entry.flags for entry in self.entries)) if self.entries else set()


def segment(pages: list[Page]) -> Segmented:
    stream = _stream(pages)
    passages: dict[str, RawPassage] = {}
    questions: list[RawQuestion] = []
    expected = 1
    lead = _Unit()
    item: _Unit | None = None
    group_command = ""
    group_passage: str | None = None
    group_flags: set[str] = set()

    def close_item() -> None:
        if item is None:
            return
        questions.append(_question(expected - 1, item, group_command, group_passage, group_flags))

    for entry in stream:
        line = entry.line
        starts_item = (
            (match := ITEM.match(line.plain)) is not None
            and int(match.group(1)) == expected
            and line.x0 <= entry.left + ITEM_INDENT
        )
        if starts_item:
            close_item()
            if lead.entries:
                group_command, group_passage, group_flags = _open_group(lead, expected, passages)
                lead = _Unit()
            item = _Unit([entry])
            expected += 1
        elif item is not None and _continues(item, entry):
            item.entries.append(entry)
        else:
            if item is not None:
                close_item()
                item = None
            lead.entries.append(entry)
    close_item()
    if lead.entries and questions:
        # Texto depois do último item que não abriu grupo nenhum: não descartamos em silêncio.
        questions[-1].flags = sorted({*questions[-1].flags, "orphan_text"})
    return Segmented(parser=PARSER, passages=list(passages.values()), questions=questions)


def _continues(item: _Unit, entry: _Entry) -> bool:
    """Linha com recuo continua o item, salvo recuo de parágrafo depois de frase terminada."""
    indent = entry.line.x0 - entry.left
    if indent <= HANGING_MIN:
        return False
    last = item.entries[-1]
    moved = last.page != entry.page or last.line.column != entry.line.column
    if moved and indent > HANGING_MAX:
        return False  # em coluna nova, só o recuo típico de continuação prende ao item
    previous = last.line.plain
    starts_paragraph = abs(indent - PARAGRAPH_INDENT_AT) < 4 and entry.line.plain[:1].isupper()
    return not (starts_paragraph and previous.rstrip().endswith((".", "?", "!", ":")))


def _stream(pages: list[Page]) -> list[_Entry]:
    """Linhas da prova objetiva em ordem de leitura, com figuras atribuídas às linhas vizinhas."""
    stream: list[_Entry] = []
    started = not any(START.search(line.plain) for page in pages for line in page.lines)
    for page in pages:
        lefts = {
            column: min((line.x0 for line in page.lines if line.column == column), default=0.0)
            for column in (0, 1, 2)
        }
        rights = {
            column: max((line.x1 for line in page.lines if line.column == column), default=0.0)
            for column in (0, 1, 2)
        }
        images = [f for f in page.figures if f.kind == "image"]
        entries: list[_Entry] = []
        skipped: list[Line] = []
        for line in page.lines:
            if not started:
                started = line.column == 0 and bool(START.search(line.plain))
                continue
            if line.column == 0 and STOP.search(line.plain):
                stream.extend(_with_figures(page, entries, skipped))
                return stream
            if SKIP.match(line.plain):
                skipped.append(line)
                continue
            if any(_contains(image, line) for image in images):
                continue  # rótulos de gráfico desenhados sobre a imagem
            entry = _Entry(
                page.number,
                line,
                lefts[line.column],
                short=line.x1 < rights[line.column] - SHORT_LINE,
            )
            if BROKEN_MATH.search(line.plain):
                entry.flags.add("formula")
            if line.x0 > entry.left + ODD_INDENT and not _is_passage_indent(line, entry.left):
                entry.flags.add("layout")
            entries.append(entry)
        stream.extend(_with_figures(page, entries, skipped))
    return stream


def _is_passage_indent(line: Line, left: float) -> bool:
    """Recuo esperado: primeira linha de parágrafo ou citação da fonte (letra pequena)."""
    return abs(line.x0 - left - PARAGRAPH_INDENT_AT) < 4 or line.size < 9


def _with_figures(page: Page, entries: list[_Entry], skipped: list[Line]) -> list[_Entry]:
    """Marca com 'figure' a linha que antecede cada figura (no Cebraspe, o texto que a apresenta
    vem antes dela); se a figura abre a coluna, marca a linha seguinte."""
    middle = page.width / 2
    for figure in page.figures:
        if any(_contains(figure, line) for line in skipped):
            continue  # faixa de fundo de título ("BLOCO II")
        column = 1 if figure.x1 <= middle + 12 else 2 if figure.x0 >= middle - 12 else 0
        same = [e for e in entries if column == 0 or e.line.column in (column, 0)]
        above = [e for e in same if e.line.y0 < figure.y0]
        below = [e for e in same if e.line.y0 >= figure.y0 - 2]
        if above:
            max(above, key=lambda e: e.line.y0).flags.add("figure")
        elif below:
            min(below, key=lambda e: e.line.y0).flags.add("figure")
    return entries


def _contains(figure: Figure, line: Line) -> bool:
    return (
        figure.x0 - 2 <= line.x0
        and line.x1 <= figure.x1 + 2
        and figure.y0 - 2 <= line.y0
        and line.y1 <= figure.y1 + 2
    )


def _open_group(
    lead: _Unit, first: int, passages: dict[str, RawPassage]
) -> tuple[str, str | None, set[str]]:
    """Abertura de um grupo → (comando, chave do texto-base, flags do grupo).

    A abertura pode ter: textos rotulados ("Texto 2A1-I" + corpo), uma situação sem rótulo e, no
    fim, o comando. O comando é separado pelo primeiro trecho com "julg" do último parágrafo.
    """
    segments: list[tuple[str | None, list[_Entry]]] = [(None, [])]
    for entry in lead.entries:
        match = TEXT_LABEL.match(entry.line.plain)
        if match:
            segments.append((match.group(1), []))
        else:
            segments[-1][1].append(entry)
    (_, prefix), *labeled = segments
    if labeled:
        *texts, (last_label, last_entries) = labeled
    else:
        texts, last_label, last_entries, prefix = [], None, prefix, []
    paragraphs = _paragraphs(last_entries)
    situation, command = _split_command(paragraphs)
    if not command:
        for entry in last_entries:
            entry.flags.add("no_command")
    if prefix:  # texto antes do primeiro rótulo (raro): abre o enunciado
        command = "\n\n".join([*_paragraphs(prefix), command])
    flags = set().union(*(e.flags for e in last_entries)) if last_entries else set()

    for label, entries in texts:
        if label and entries:
            _add_passage(passages, label, _paragraphs(entries), entries)
    if last_label:
        # O último texto rotulado termina onde começa o comando.
        if situation:
            _add_passage(passages, last_label, situation, last_entries)
        return command, last_label, set()
    # Sem rótulo: o que vem antes do comando é situação hipotética (texto-base anônimo)...
    referenced = next(
        (ref for ref in TEXT_REF.findall(" ".join([*situation, command])) if ref in passages),
        None,
    )
    if situation and referenced:
        # ...a menos que remeta a um texto rotulado: aí o rotulado é o texto-base e a situação
        # abre o enunciado junto com o comando.
        return "\n\n".join([*situation, command] if command else situation), referenced, flags
    if situation:
        key = f"g{first}"
        _add_passage(passages, key, situation, last_entries)
        return command, key, flags
    return command, referenced, flags


def _add_passage(
    passages: dict[str, RawPassage], key: str, paragraphs: list[str], entries: list[_Entry]
) -> None:
    passages[key] = RawPassage(
        key=key,
        body_md="\n\n".join(paragraphs),
        page=entries[0].page,
        flags=sorted(set().union(*(e.flags for e in entries))),
    )


def _question(
    number: int, item: _Unit, command: str, passage: str | None, group_flags: set[str]
) -> RawQuestion:
    first = item.entries[0]
    text_lines = [ITEM_MD.sub("", first.line.text, count=1)] + [
        e.line.text for e in item.entries[1:]
    ]
    body = _join(text_lines)
    statement = f"{command}\n\n{body}" if command else body
    flags = item.flags | group_flags
    if any(e.short and not e.line.plain.endswith(SENTENCE_STOP) for e in item.entries[:-1]):
        flags.add("layout")  # quebras de linha com significado (código, versos, listas)
    if re.search(r"sublinhad", statement, re.I) and "<u>" not in statement:
        flags.add("underline")
    return RawQuestion(
        number=number,
        type="true_false",
        statement_md=statement,
        passage_key=passage,
        page=first.page,
        flags=sorted(flags),
    )


def _paragraphs(entries: list[_Entry]) -> list[str]:
    paragraphs: list[list[str]] = []
    previous: _Entry | None = None
    for entry in entries:
        indented = entry.line.x0 > entry.left + PARAGRAPH_INDENT
        new = previous is None or indented or abs(entry.line.size - previous.line.size) >= 1
        if new:
            paragraphs.append([])
        paragraphs[-1].append(entry.line.text)
        previous = entry
    return [_join(lines) for lines in paragraphs]


def _split_command(paragraphs: list[str]) -> tuple[list[str], str]:
    """Separa o comando (do primeiro trecho com "julg" no último parágrafo) do contexto."""
    if not paragraphs:
        return [], ""
    *rest, last = paragraphs
    sentences = SENTENCE_END.split(last)
    for index, sentence in enumerate(sentences):
        if COMMAND.search(sentence):
            before = " ".join(sentences[:index]).strip()
            command = " ".join(sentences[index:]).strip()
            return [*rest, before] if before else rest, command
    return paragraphs, ""


def _join(lines: list[str]) -> str:
    text = ""
    for line in lines:
        if not text:
            text = line
        elif re.search(r"[a-záéíóúâêôãõç]-$", text) and re.match(r"[a-záéíóúâêôãõç]", line):
            text = text[:-1] + line  # hifenização de fim de linha
        else:
            text = f"{text} {line}"
    return _normalize(text)


def _normalize(text: str) -> str:
    text = re.sub(r"\*\*\s+\*\*", " ", text)  # negrito quebrado em pedaços
    text = re.sub(r"(?<!\*)\*\s+\*(?!\*)", " ", text)  # itálico quebrado em pedaços
    return re.sub(r"\s+", " ", text).strip()


# --- gabarito ---------------------------------------------------------------------------------

KEY_MARK = re.compile(r"^[CEX]$")
KEY_NUMBER = re.compile(r"^\d{1,3}$")


def parse_answer_key(pages: list[Page]) -> AnswerKey:
    """Gabarito do Cebraspe: grade de linhas "Item" (números) e "Gabarito" (C, E ou X).

    Cada linha de números é pareada com a linha de marcas que vem logo depois dela (na mesma
    coluna, pela ordem de leitura). Linhas que não fecham o par são ignoradas.
    """
    answers: dict[int, AnswerMark] = {}
    previous: list[int] | None = None
    for page in pages:
        for line in page.lines:
            tokens = [t for t in line.plain.split() if t not in ("Item", "Gabarito")]
            if tokens and all(KEY_NUMBER.match(t) for t in tokens):
                numbers = [int(t) for t in tokens]
                previous = numbers if numbers[0] > 0 and _consecutive(numbers) else None
                continue
            pairs = previous is not None and len(tokens) == len(previous)
            if pairs and all(KEY_MARK.match(t) for t in tokens):
                for number, mark in zip(previous or [], tokens, strict=True):
                    answers[number] = mark  # type: ignore[assignment]
            previous = None
    return AnswerKey(answers=dict(sorted(answers.items())))


def _consecutive(numbers: list[int]) -> bool:
    return numbers == list(range(numbers[0], numbers[0] + len(numbers)))
