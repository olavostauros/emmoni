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
from collections import Counter
from dataclasses import dataclass, field

from ingest.extract import Figure, Line, Page
from ingest.staging import AnswerKey, AnswerMark, RawPassage, RawQuestion, Segmented

PARSER = "cebraspe-parser@1"

START = re.compile(r"^-* ?PROVA OBJETIVA ?-*$")
STOP = re.compile(r"^-* ?PROVA DISCURSIVA ?-*$")
SKIP = re.compile(r"^(BLOCO [IVX]+|Espaço livre|-+ ?PROVA OBJETIVA ?-+|\d+_[A-Z0-9_]+)$", re.I)
ITEM = re.compile(r"^(\d{1,3})(?:\s+\S|$)")  # número sozinho: item que é só figura
ITEM_MD = re.compile(r"^(?:\*\*)?\d{1,3}(?:\*\*)?(?:\s+|$)")
TEXT_LABEL = re.compile(r"^Texto\s+([0-9A-Z][\w.]*(?:-[IVX]+)?)$")
TEXT_REF = re.compile(r"\btexto\s+([0-9][\w.]*-[IVX]+|[0-9][A-Z0-9.]+)", re.I)
COMMAND = re.compile(r"\b(julg|judge|juzg)", re.I)  # português, inglês, espanhol
SENTENCE_END = re.compile(r"(?<=[.!?:])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ“])")
# Glifos de fontes matemáticas sem mapeamento Unicode correto (Cambria Math exportada pelo
# Distiller sai como etíope, malaiala, oriá...) e letras matemáticas (𝑋, 𝛾).
BROKEN_MATH = re.compile(r"[଀-୿ഀ-ൿሀ-፿\U0001D400-\U0001D7FF]")

SENTENCE_STOP = (".", ":", ";", "?", "!")
SENTENCE_STOP_FULL = (".", "?", "!")
LINE_NUMBER = re.compile(
    r"^(?:[*\\/t]{0,10}?)\d{1,3}\*{0,2}\s+"
)  # "*4* ", "*\\t/**1* " (glifo decorativo)
LINE_NUMBER_GAP = 8.0
ITEM_INDENT = 6.0  # número do item fica na margem da coluna
HANGING_MIN = 8.0  # continuação do item tem recuo (~18)
HANGING_MAX = 24.0
PARAGRAPH_INDENT = 15.0  # primeira linha de parágrafo de texto-base
PARAGRAPH_INDENT_AT = 29.0  # recuo típico de parágrafo (a continuação de item fica em ~18)
SHORT_LINE = 40.0  # linha que termina antes disso da margem direita quebra de propósito
ODD_INDENT = 30.0
CITATION_SIZE = 9.0  # letra menor que isso: citação da fonte do texto  # recuo maior que isso dentro de item = layout especial (código, tabela)


@dataclass
class _Entry:
    page: int
    line: Line
    left: float  # margem esquerda da coluna desta linha
    short: bool = False  # termina bem antes da margem direita da coluna
    after_gap: bool = False  # veio depois de um "Espaço livre" ou de um título de bloco
    flags: set[str] = field(default_factory=set)


@dataclass
class _Unit:
    entries: list[_Entry] = field(default_factory=list)

    @property
    def flags(self) -> set[str]:
        return set().union(*(entry.flags for entry in self.entries)) if self.entries else set()


def segment(pages: list[Page], first: int = 1) -> Segmented:
    """`first`: número do primeiro item do caderno (PRF 2021: caderno que começa no item 9)."""
    stream = _stream(pages)
    passages: dict[str, RawPassage] = {}
    questions: list[RawQuestion] = []
    expected = first
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
        # Item só começa logo depois de outro item ou depois de um comando: assim os números de
        # linha dos textos-base ("1", "4", "7"...) e listas numeradas não viram itens.
        ready = (item is not None and not lead.entries) or (
            bool(lead.entries)
            and not _inside_labeled_text(lead)
            and (
                any(COMMAND.search(e.line.plain) for e in lead.entries)
                # "Nessa situação hipotética, 48 se W1..." — o item completa a frase da abertura.
                or not lead.entries[-1].line.plain.rstrip().endswith((".", "?", "!"))
            )
        )
        starts_item = (
            ready
            and (match := ITEM.match(line.plain)) is not None
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


def _inside_labeled_text(lead: _Unit) -> bool:
    """A abertura está dentro de um texto-base que ainda não chegou ao comando: números na margem
    são de linha. Texto-base = rótulo "Texto X" ou duas ou mais linhas numeradas (1, 4, 7...)."""
    inside = False
    numbered = 0
    for entry in lead.entries:
        if TEXT_LABEL.match(entry.line.plain):
            inside = True
        elif COMMAND.search(entry.line.plain) or entry.line.size < CITATION_SIZE:
            inside, numbered = False, 0  # comando ou citação da fonte encerram o texto
        elif LINE_NUMBER.match(entry.line.text):
            numbered += 1
    return inside or numbered >= 2


def _continues(item: _Unit, entry: _Entry) -> bool:
    """Linha com recuo continua o item, salvo recuo de parágrafo depois de frase terminada."""
    indent = entry.line.x0 - entry.left
    last = item.entries[-1]
    if indent <= HANGING_MIN:
        # Só continua se a frase claramente segue (linha começa com minúscula).
        unfinished = not last.line.plain.rstrip().endswith((".", "?", "!", ":"))
        return unfinished and entry.line.plain[:1].islower() and indent < 0
    moved = last.page != entry.page or last.line.column != entry.line.column
    if moved and indent > HANGING_MAX:
        return False  # em coluna nova, só o recuo típico de continuação prende ao item
    previous = last.line.plain.rstrip()
    sentence_done = previous.endswith((".", "?", "!"))
    title = entry.line.text.startswith("**") and entry.line.text.endswith("**")
    if sentence_done and (entry.after_gap or title):
        return False  # "Espaço livre" ou título em negrito encerram o item
    starts_paragraph = abs(indent - PARAGRAPH_INDENT_AT) < 4 and entry.line.plain[:1].isupper()
    if starts_paragraph and previous.endswith((".", "?", "!", ":")):
        return False
    # Primeira linha de parágrafo com recuo maior que o de costume (varia entre provas): longa,
    # começando com maiúscula, depois de frase terminada. Fórmula centralizada é curta e fica.
    new_paragraph = indent > HANGING_MAX and entry.line.plain[:1].isupper() and not entry.short
    return not (new_paragraph and sentence_done)


def _stream(pages: list[Page]) -> list[_Entry]:
    """Linhas da prova objetiva em ordem de leitura, com figuras atribuídas às linhas vizinhas."""
    stream: list[_Entry] = []
    gap = False
    # Sem o marcador "PROVA OBJETIVA", começa do início; instruções numeradas da capa não viram
    # itens porque item só começa depois de um comando ("julgue").
    started = not any(START.search(line.plain) for page in pages for line in page.lines)
    for page in pages:
        middle = page.width / 2
        lefts = {
            0: min((line.x0 for line in page.lines if line.column == 0), default=0.0),
            1: min((line.x0 for line in page.lines if line.column == 1), default=0.0),
            # Linhas que começam um pouco antes do meio também vão para a coluna 2, mas a margem
            # da coluna é medida só com as que começam depois do meio.
            2: min(
                (line.x0 for line in page.lines if line.column == 2 and line.x0 >= middle),
                default=min((line.x0 for line in page.lines if line.column == 2), default=0.0),
            ),
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
                gap = True
                continue
            if any(_contains(image, line) for image in images):
                continue  # rótulos de gráfico desenhados sobre a imagem
            entry = _Entry(
                page.number,
                line,
                lefts[line.column],
                short=line.x1 < rights[line.column] - SHORT_LINE,
                after_gap=gap,
            )
            gap = False
            if BROKEN_MATH.search(line.plain):
                entry.flags.add("formula")
            if line.x0 > entry.left + ODD_INDENT and entry.short and line.size >= CITATION_SIZE:
                entry.flags.add("layout")  # linha recuada e curta: código, tabela, fórmula
            if line.scripts:
                entry.flags.add("formula")  # índices/expoentes que o texto puro achata
            entries.append(entry)
        stream.extend(_with_figures(page, entries, skipped))
    return stream


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
    situation, command = _split_command(_text_paragraphs(last_entries))
    if not command:
        for entry in last_entries:
            entry.flags.add("no_command")
    if prefix:  # texto antes do primeiro rótulo (raro): abre o enunciado
        command = "\n\n".join([*_paragraphs(prefix), command])
    flags = set().union(*(e.flags for e in last_entries)) if last_entries else set()

    for label, entries in texts:
        if label and entries:
            _add_passage(passages, label, _text_paragraphs(entries), entries)
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
    empty = not body.strip()
    if not command:
        statement = body
    elif command.rstrip().endswith(SENTENCE_STOP_FULL):
        statement = f"{command}\n\n{body}"
    else:
        statement = f"{command} {body}"  # o item completa a frase do comando
    flags = item.flags | group_flags
    if empty:
        flags.add("empty_item")  # o item é só uma figura
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


def _text_paragraphs(entries: list[_Entry]) -> list[str]:
    """Parágrafos de um texto rotulado, sem a numeração de linhas da margem."""
    stripped, numbered = _strip_line_numbers(entries)
    return _paragraphs(stripped, base=_base_x(stripped) if numbered else None)


def _strip_line_numbers(entries: list[_Entry]) -> tuple[list[_Entry], bool]:
    """Tira a numeração de linhas da margem dos textos-base (1, 4, 7...).

    Só quando o corpo do texto fica recuado em relação à margem da coluna e o número está à
    esquerda dele; um parágrafo que começa com número ("2020 foi...") fica intacto."""
    base = _base_x(entries)
    stripped = []
    numbered = False
    for entry in entries:
        match = LINE_NUMBER.match(entry.line.text)
        if match and entry.line.x0 < base - LINE_NUMBER_GAP:
            line = entry.line.model_copy(
                update={
                    "text": entry.line.text[match.end() :],
                    "plain": LINE_NUMBER.sub("", entry.line.plain, count=1),
                    "x0": base,
                }
            )
            entry = _Entry(entry.page, line, entry.left, entry.short, entry.after_gap, entry.flags)
            numbered = True
        stripped.append(entry)
    return stripped, numbered


def _base_x(entries: list[_Entry]) -> float:
    """Margem do corpo do texto: o x0 mais comum."""
    counts = Counter(round(entry.line.x0) for entry in entries)
    return float(counts.most_common(1)[0][0]) if counts else 0.0


def _paragraphs(entries: list[_Entry], base: float | None = None) -> list[str]:
    """Junta linhas em parágrafos. `base` é a margem do corpo do texto quando ela não coincide
    com a da coluna (textos com numeração de linhas)."""
    paragraphs: list[list[str]] = []
    previous: _Entry | None = None
    for entry in entries:
        indented = entry.line.x0 > (base or entry.left) + PARAGRAPH_INDENT
        title_goes_on = previous is not None and _is_title(previous) and _is_title(entry)
        new = (
            previous is None
            or (indented and not title_goes_on)
            or abs(entry.line.size - previous.line.size) >= 1
        )
        if new:
            paragraphs.append([])
        paragraphs[-1].append(entry.line.text)
        previous = entry
    return [_join(lines) for lines in paragraphs]


def _is_title(entry: _Entry) -> bool:
    text = entry.line.text
    return text.startswith("**") and text.endswith("**")


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
    if not last.rstrip().endswith(SENTENCE_STOP_FULL):
        # Sem "julgue": frase inacabada no fim ("Nessa situação hipotética,") que cada item completa.
        before = " ".join(sentences[:-1]).strip()
        return [*rest, before] if before else rest, sentences[-1].strip()
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
            # Células vazias da grade vêm preenchidas com "0" ("119 120 0 0", "C E 0 0").
            while len(tokens) > 1 and tokens[-1] == "0":
                tokens.pop()
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
