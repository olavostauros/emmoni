"""Parser do Cebraspe: provas de itens certo/errado e gabaritos (SPECIFICATION.md §7.3).

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
from pathlib import Path
from typing import Literal, cast

from ingest.extract import Figure, Line, Page
from ingest.staging import AnswerKey, AnswerMark, RawOption, RawPassage, RawQuestion, Segmented

PARSER = "cebraspe-parser@1"

START = re.compile(
    r"^-* ?PROVAS? OBJETIVAS?( P\d)? ?-*$"
)  # "-- PROVA OBJETIVA P1 --" (2025), "-- PROVAS OBJETIVAS --"
STOP = re.compile(r"^-* ?PROVA DISCURSIVA( P\d)? ?-*$")
# Número da página no rodapé, "– 3 –" (cadernos do site antigo: PF 2012 delegado, escrivão e
# papiloscopista); só vale no fim da página (`PAGE_FOOTER_AT` da altura).
PAGE_FOOTER = re.compile(r"^[–-] ?\d{1,3} ?[–-]$")
PAGE_FOOTER_AT = 0.9
# "PROVA DISCURSIVA" centrado em corpo grande no site antigo (PF 2012 escrivão e papiloscopista)
# cai na coluna 1; sem parar ali, as instruções da discursiva viravam texto solto após o item 120.
STOP_TITLE_SIZE = 12.0
# Título de seção que abre a prova quando não há "PROVA OBJETIVA" (CBM/AL e PM/AL 2017).
SECTION_START = re.compile(r"^-* ?CONHECIMENTOS (B[ÁA]SICOS|GERAIS|ESPEC[ÍI]FICOS) ?-*$", re.I)
SKIP = re.compile(  # títulos de bloco, rascunho, código do caderno, cabeçalho da banca
    r"^(BLOCO [IVX]+|Espaço livre|RASCUNHO|-+ ?PROVAS? OBJETIVAS? ?-+|\d+_[A-Z0-9_]+|CEBRASPE [–-] .*"
    # título de seção no meio do caderno (PM/AL 2021, PCDF 2019), código da matriz, lixo "! !"
    r"|-* ?CONHECIMENTOS (?:B[ÁA]SICOS|GERAIS|ESPEC[ÍI]FICOS)(?: P\d)? ?-*|›* ?Matriz_\S*|P[áa]gina: ?\d+|[!\s]+)$",
    re.I,
)
# Nomes de disciplina (db/taxonomy): faixa de título de seção em negrito ("**Língua Portuguesa**",
# "**Geografia Geral e do Brasil**", Cebraspe 2021) não é texto-base nem enunciado.
SUBJECT_NAMES = tuple(
    sorted(
        {
            m.group(1).strip().strip('"').casefold()
            for f in (Path(__file__).resolve().parents[2] / "db" / "taxonomy").glob("*.yaml")
            if (m := re.search(r"^name:\s*(.+)$", f.read_text(encoding="utf-8"), re.M))
        },
        key=len,
        reverse=True,
    )
)
ITEM = re.compile(r"^(\d{1,3})(?:\s+\S|$)")  # número sozinho: item que é só figura
# Provas de múltipla escolha do Cebraspe: título "Questão N" (ou "QUESTÃO N"), enunciado,
# alternativas "A ...", "B ..." na margem com continuação recuada.
# "Questão 7", "QUESTÃO 21 E" (2017, lixo), "QUESTÃO 1 <PMDF064CG1A01E1035>" (2025, código).
QUESTION_TITLE = re.compile(r"^QUEST[ÃA]O\s+(\d{1,3})(?:\s+(?:\S{1,2}|<[^>]*>))?\s*$", re.I)
OPTION = re.compile(r"^([A-E])(?:\s+\S|$)")
OPTION_MD = re.compile(r"^(?:\*\*)?[A-E](?:\*\*)?(?:\s+|$)")
ROMAN_ITEM = re.compile(r"^(?:[IVX]+|[a-e]\))\s+\S")
ITEM_MD = re.compile(r"^(?:\*\*)?\d{1,3}(?:\*\*)?(?:\s+|$)")
TEXT_LABEL = re.compile(r"^Texto?\s+([0-9A-Z][\w.]*(?:-[IVX]+)?)$")  # "Text" nas provas de inglês
# Título de texto-base de múltipla escolha, citado pelas questões que o usam ("Figura 5A2",
# "Caso hipotético 1A06-II", "situação hipotética 12A3-I").
_TITLE_WORDS = (
    r"(?:Texto?|Figura|Tabela|Quadro|Gr[áa]fico|Proposi[çc][ãa]o|Caso hipot[ée]tico"
    r"|Situa[çc][ãa]o hipot[ée]tica)"
)
# Código da banca: dígito seguido de letra (2A1-I, CG1A5AAA, 12A3-I, 5A2); "P3" não é rótulo.
_LABEL = r"([0-9A-Z]*\d[A-Z][A-Z0-9]*(?:-[IVX]+)?)"
PASSAGE_TITLE = re.compile(rf"^\W*{_TITLE_WORDS}\s+{_LABEL}", re.I)
TITLE_LINE = re.compile(rf"^\W*{_TITLE_WORDS}\s+{_LABEL}\W*$", re.I)  # linha que é só o título
# Remissão a um texto-base pelo rótulo, dentro da questão ("texto 1A7-I", "proposição CG1A5AAA").
LABEL_REF = re.compile(rf"\b{_TITLE_WORDS}\s+{_LABEL}", re.I)
# Questão que remete a um texto sem rótulo ("do expediente", "no texto") e ficou sem texto-base.
IMPLICIT_REF = re.compile(
    r"\b(?:d[oa]s?|n[oa]s?|[oa]s?|dess[ea]s?|nest[ea]s?|ness[ea]s?|pel[oa]s?|ao)\s+"
    r"(?:expediente|of[íi]cio|memorando|poema|tirinha|charge)\b"
    # "do expediente forense": horário do fórum, não um documento (PCDF 2020 item 41)
    r"(?!\s+(?:anterior|precedente|a seguir|abaixo|acima|seguinte|forense|de\b|[0-9A-Z]+\d))",
    re.I,
)
# Comando que aponta um documento mostrado na prova ("o expediente acima", "o ofício hipotético
# apresentado"). "Itens a seguir/seguintes/que se seguem" fala dos itens, não de um documento.
SHOWN_DOCUMENT = re.compile(
    r"\b(?:acima|precedentes?|anteriores?|abaixo|a seguir|seguintes?|apresentad[oa]s?"
    r"|transcrit[oa]s?|reproduzid[oa]s?|hipot[ée]tic[oa]s?|texto|trecho|fragmento|excerto)\b",
    re.I,
)
ITEMS_PHRASE = re.compile(
    r"\bite(?:ns|m)\s+(?:a seguir|seguintes?|subsequentes?|que se seguem|que segue)\b", re.I
)
# Figura da própria questão ("a figura precedente", "o gráfico a seguir"): sem imagem extraída, a
# questão não se sustenta.
FIGURE_REF = re.compile(
    r"\b(?:figuras?|gr[áa]ficos?|imagens?|ilustra[çc][ãa]o|esquemas?|mapas?|planilhas?|circuitos?|cartogramas?|tabelas?)\s+"
    r"(?:precedentes?|anteriore?s?|a seguir|abaixo|acima|seguintes?|que segue|apresentad[ao]s?|mostrad[ao]s?|ilustrad[ao]s?)\b",
    re.I,
)
# Figura citada com palavras entre o nome e a remissão ("o modelo entidade-relacionamento (ER)
# precedente", "o diagrama e a situação hipotética apresentados", PF 2018 agente 81–83, PC/DF 2020
# 85–86) ou só pelo particípio ("cuja estrutura geral é mostrada anteriormente", "o tipo de
# virtualização antes ilustrado", PC/PB 2021 cargo 7, 51 e 54). Decisão 0030.
FIGURE_NOUNS = (
    r"figuras?|gr[áa]ficos?|imagens?|ilustra[çc][õoã](?:es|o)|esquemas?|mapas?|planilhas?"
    r"|circuitos?|cartogramas?|tabelas?|diagramas?|fluxogramas?|organogramas?"
)
FIGURE_REF_WIDE = re.compile(
    rf"\b(?:{FIGURE_NOUNS})\b(?:\s+[^\s.,;:]+){{0,5}}?\s+(?:(?:é|são|foi|foram|está|estão)\s+)?"
    r"(?:antes\s+)?(?:precedentes?|anteriore?s?|anteriormente|a seguir|abaixo|acima"
    r"|apresentad[ao]s?|mostrad[ao]s?|ilustrad[ao]s?)\b",
    re.I,
)
DEPICTED = re.compile(
    r"\b(?:(?:antes|acima|anteriormente)\s+(?:ilustrad|mostrad|esquematizad|representad)[oa]s?"
    r"|(?:ilustrad|mostrad|esquematizad)[oa]s?\s+(?:anteriormente|acima))\b"
    # "quadro" e "modelo" só com remissão de lugar: "o quadro apresentado" é também o quadro
    # clínico (PC/MA 2017 perito, 49) e "o modelo apresentado", uma função (PRF 2018, 27).
    r"|\bquadros?\s+(?:precedentes?|anteriore?s?|a seguir|abaixo|acima|seguintes?)\b"
    r"|\bmodelos?\b(?:\s+[^\s.,;:]+){0,5}?\s+(?:precedentes?|anteriore?s?|anteriormente|a seguir"
    r"|abaixo|acima)\b",
    re.I,
)
# Comando de grupo certo/errado que remete a algo antes dele ("Considerando o modelo ... precedente,
# julgue", "Considerando que os dados acima ..."): sem texto-base, o que ele aponta não foi
# extraído. Decisão 0030.
BACK_REF = re.compile(
    r"\b(?:precedentes?|anteriores?|anteriormente|acima"
    r"|antes\s+(?:ilustrad|apresentad|mostrad|descrit)[oa]s?)\b",
    re.I,
)
# Título de disciplina em caixa alta entre questões ("DIREITO FINANCEIRO E TRIBUTÁRIO",
# "35. HISTÓRIA E GEOGRAFIA DE RONDÔNIA" em PC/RO 2022): encerra a alternativa e não é texto-base.
SECTION_TITLE = re.compile(r"^(?:\d+\.\s+)?[A-ZÀ-Ú][A-ZÀ-Ú ,.()–-]{3,}$")
# Remissão a linha de texto ("(ℓ.18)", que algumas fontes entregam como "(R.18)").
LINE_REF = re.compile(r"\((?:ℓ|R|l)\.\s?\d")
# Texto-base que é só a legenda/crédito de uma imagem (tirinha, charge): o conteúdo ficou na figura.
CREDIT_ONLY = re.compile(
    r"^(?:Fonte:.*|Internet:.*|.*\((?:com adaptações|adapted|adaptado)\)\.?|Quino\..*)$",
    re.I | re.S,
)
BULLET_C = re.compile(r"^C\s+(?=\S)")  # marcador "•" de fonte decorativa extraído como "C"
TEXT_REF = re.compile(rf"\btexto?\s+{_LABEL}", re.I)  # "texto CG1A1-I", "text 1A2-II"
COMMAND = re.compile(r"\b(julg|jug|judge|juzg)", re.I)  # português, inglês, espanhol
# No corte entre texto-base e comando, "julgador" e "julgamento" são substantivos do texto, não o
# comando (PF 2012 papiloscopista, itens 111–113: "... para auxiliar o julgador.").
COMMAND_VERB = re.compile(r"\b(julg(?!ador|amento)|jug|judge|juzg)", re.I)
# "Os itens a seguir apresentam, de forma consecutiva, os períodos que compõem um parágrafo" (PF
# 2018): cada item é um período do mesmo parágrafo e depende dos anteriores ("Nessas situações").
CONSECUTIVE_ITEMS = re.compile(r"\bitens\b[^.]{0,60}\b(consecutiv|sucessiv)", re.I)
# Cadernos "com justificativa" (PCDF 2020, PF 2025...): depois de cada item vem a justificativa
# oficial do gabarito, às vezes grudada na última linha do item ("...administrativo.JUSTIFICATIVA").
# PC/PE 2023 traz, depois de cada questão, uma tabela "||JUSTIFICATIVAS||".
JUSTIFICATION = re.compile(r"JUSTIFICATIVAS?\b|\bITEM ANULADO\b")  # sempre em maiúsculas
# Justificativa sem o prefixo ("ERRADO. O Hyper-V dá suporte...", PCDF 2020 item 84): só é
# reconhecida pela cor das justificativas do caderno (azul), nunca pelo texto sozinho.
VERDICT = re.compile(r"^(?:CERTO|ERRADO)\b")
BARE_NUMBER = re.compile(r"^\d{1,3}$")
WHITE = 0xFFFFFF  # texto invisível
SENTENCE_END = re.compile(r"(?<=[.!?:])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ“])")
# Glifos de fontes matemáticas sem mapeamento Unicode correto (Cambria Math exportada pelo
# Distiller sai como etíope, malaiala, oriá...) e letras matemáticas (𝑋, 𝛾).
BROKEN_MATH = re.compile(  # inclui caracteres de controle: glifo sem mapeamento
    "[\x00-\x08\x0b\x0c\x0e-\x1f\u0b00-\u0b7f\u0d00-\u0d7f\u1200-\u137f\ue000-\uf8ff\ufffd\U0001d400-\U0001d7ff]"
)

# Última linha do crédito de um texto ("Internet: <www.x.br> (com adaptações)."; também "(tradução
# livre, com adaptações)", PF 2018): o que vem depois é outro parágrafo (o comando da questão),
# mesmo na margem e sem recuo (PM/TO 2020 q22, q23).
CREDIT_END = re.compile(
    r"(?:\([^()]*\b(?:com adaptações|adaptado|adapted)\)|^(?:Internet|Fonte):.*>)\.?$", re.I
)

SENTENCE_STOP = (".", ":", ";", "?", "!")
# Linha que termina em hífen colado a letra ou algarismo, seguida de linha que começa por letra ou
# algarismo: a palavra composta continua sem espaço, com o hífen (decisão 0032).
HYPHEN_END = re.compile(r"[^\W_]-$")
HYPHEN_NEXT = re.compile(r"[^\W_]")
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
# Vocativo ou fecho de correspondência sozinho na linha ("Senhor Delegado,", "Atenciosamente,").
LETTER_LINE = re.compile(
    r"^(?:(?:Excelent[íi]ssim[oa]|Ilustr[íi]ssim[oa]|Magn[íi]fic[oa]|Prezad[oa]s?|Car[oa]s?)\s+)?"
    r"(?:Senhora?|Senhores|Senhoras|Atenciosamente|Respeitosamente|Cordialmente)\b[^.;:!?]{0,60},$"
)
FIGURE_CREDIT_GAP = 20.0  # crédito da figura logo abaixo dela
CITATION_SIZE = 9.0  # letra menor que isso: citação da fonte do texto  # recuo maior que isso dentro de item = layout especial (código, tabela)


@dataclass
class _Entry:
    page: int
    line: Line
    left: float  # margem esquerda da coluna desta linha
    short: bool = False  # termina bem antes da margem direita da coluna
    after_gap: bool = False  # veio depois de um "Espaço livre" ou de um título de bloco
    flags: set[str] = field(default_factory=set)
    # Veio logo depois de uma justificativa do gabarito: a justificativa fecha o item, então esta
    # linha não o continua (PCDF 2020: o texto-base com recuo de parágrafo de 15 grudava no item).
    after_justification: bool = False


@dataclass
class _Unit:
    entries: list[_Entry] = field(default_factory=list)

    @property
    def flags(self) -> set[str]:
        return set().union(*(entry.flags for entry in self.entries)) if self.entries else set()


def segment(pages: list[Page], first: int = 1) -> Segmented:
    """`first`: número do primeiro item do caderno (PRF 2021: caderno que começa no item 9)."""
    stream = _stream(pages)
    if any(QUESTION_TITLE.match(entry.line.plain) for entry in stream):
        return _segment_choice(stream, first)
    passages: dict[str, RawPassage] = {}
    questions: list[RawQuestion] = []
    expected = first
    lead = _Unit()
    item: _Unit | None = None
    group_command = ""
    group_command_page: int | None = None
    group_passage: str | None = None
    group_flags: set[str] = set()
    skipped_items = 0  # itens anteriores a `first` (PC/AL 2021: os básicos no mesmo PDF)
    skipped: _Unit | None = None  # o último deles, para descartar também as linhas de continuação

    def close_item() -> None:
        if item is None:
            return
        questions.append(
            _question(
                expected - 1, item, group_command, group_passage, group_flags, group_command_page
            )
        )

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
                group_command_page = _command_page(lead) if group_command else None
                lead = _Unit()
            item = _Unit([entry])
            expected += 1
        elif item is not None and _continues(item, entry):
            item.entries.append(entry)
        else:
            if item is not None:
                close_item()
                item = None
            if skipped is not None and _continues(skipped, entry):
                skipped.entries.append(entry)
                continue
            skipped = None
            earlier = ITEM.match(line.plain) if not questions and first > 1 else None
            if (
                earlier is not None
                and int(earlier.group(1)) == skipped_items + 1 < first
                and line.x0 <= entry.left + ITEM_INDENT
            ):
                # Item de antes da prova: o que veio até aqui não é abertura do primeiro grupo.
                skipped_items += 1
                skipped = _Unit([entry])
                lead = _Unit()
                continue
            lead.entries.append(entry)
    close_item()
    if lead.entries and questions:
        # Texto depois do último item que não abriu grupo nenhum: não descartamos em silêncio.
        questions[-1].flags = sorted({*questions[-1].flags, "orphan_text"})
    # Certo/errado: remissões não resolvidas e figura citada também vão para revisão.
    labels = {label: p.key for p in passages.values() for label in _passage_labels(p)}
    for question in questions:
        question.flags = sorted({*question.flags, *_reference_flags(question, labels)})
    _passage_flags(questions, passages)
    return Segmented(parser=PARSER, passages=list(passages.values()), questions=questions)


# --- múltipla escolha --------------------------------------------------------------------------


def _segment_choice(stream: list[_Entry], first: int) -> Segmented:
    """Provas de múltipla escolha: cada questão vai do título "Questão N" ao próximo título.
    O que sobra depois da última alternativa (texto rotulado, instrução) abre o grupo seguinte.

    Na múltipla escolha a questão cita o texto-base que usa ("texto 2A1-I", "figura 5A2"). O texto
    vale para a questão que o cita e para a primeira questão depois dele; as demais do grupo não
    herdam o texto (o texto-base não se estende até a próxima abertura)."""
    passages: dict[str, RawPassage] = {}
    questions: list[RawQuestion] = []
    expected = first
    lead = _Unit()
    block: list[_Entry] = []
    number = 0
    group_passage: str | None = None
    group_first = 0
    labels: dict[str, str] = {}  # rótulo citado pelas questões → chave do texto-base

    def close() -> None:
        nonlocal lead
        if not block:
            return
        question, rest = _choice_question(number, block, None, set())
        key = _referenced_passage(question, labels) or (
            group_passage if number == group_first else None
        )
        if key:
            question.passage_key = key
            question.flags = sorted({*question.flags, *passages[key].flags})
        question.flags = sorted({*question.flags, *_reference_flags(question, labels)})
        questions.append(question)
        lead = _Unit(rest)

    skipping = False  # justificativas das alternativas (PMDF 2025), até o próximo título
    for entry in stream:
        match = QUESTION_TITLE.match(entry.line.plain)
        if match and int(match.group(1)) == expected:
            close()
            if lead.entries:
                # Antes da primeira questão, texto sem rótulo é a capa (instruções): não é texto-base.
                cover = not questions and not any(
                    TEXT_LABEL.match(e.line.plain) for e in lead.entries
                )
                group_passage = None if cover else _open_group_choice(lead, expected, passages)
                group_first = expected
                for key, passage in passages.items():
                    for label in _passage_labels(passage):
                        labels.setdefault(label, key)
                lead = _Unit()
            block = []
            number = expected
            expected += 1
            skipping = False
        elif skipping and not TITLE_LINE.match(entry.line.plain):
            continue  # a justificativa termina no próximo título de questão ou de texto-base
        elif skipping:
            skipping = False  # título de texto-base (PC/PE 2023): abre o grupo seguinte
            block.append(entry)
        elif number and JUSTIFICATION.match(entry.line.plain.lstrip("|* ")):
            skipping = True
        elif number:
            block.append(entry)
        else:
            lead.entries.append(entry)
    close()
    if lead.entries and questions:
        questions[-1].flags = sorted({*questions[-1].flags, "orphan_text"})
    _passage_flags(questions, passages)
    return Segmented(parser=PARSER, passages=list(passages.values()), questions=questions)


def _at_margin(entry: _Entry) -> bool:
    return entry.line.x0 <= entry.left + ITEM_INDENT


def _find_options(block: list[_Entry]) -> list[int] | None:
    """Índices das linhas que começam as alternativas, procurando de trás para a frente a
    sequência A..E (ou A..D) na margem da coluna."""
    for last in ("E", "D"):
        letters = [chr(c) for c in range(ord("A"), ord(last) + 1)]
        starts: list[int] = []
        position = len(block)
        for letter in reversed(letters):
            found = next(
                (
                    i
                    for i in range(position - 1, -1, -1)
                    if _at_margin(block[i])
                    and (m := OPTION.match(block[i].line.plain))
                    and m.group(1) == letter
                ),
                None,
            )
            if found is None:
                break
            starts.append(found)
            position = found
        if len(starts) == len(letters):
            return sorted(starts)
    return None


def _choice_question(
    number: int, block: list[_Entry], passage: str | None, group_flags: set[str]
) -> tuple[RawQuestion, list[_Entry]]:
    starts = _find_options(block)
    flags: set[str] = set(group_flags)
    options: list[RawOption] = []
    if starts is None:
        statement_entries, rest = block, []
        flags.add("no_options")
    else:
        statement_entries = block[: starts[0]]
        # A última alternativa termina na primeira linha de margem depois dela: o que vem a
        # seguir é a abertura do próximo grupo (texto rotulado, instrução).
        end = len(block)
        for i in range(starts[-1] + 1, len(block)):
            plain = block[i].line.plain
            starts_text = TITLE_LINE.match(plain) is not None or _section_title(plain)
            if starts_text or (_at_margin(block[i]) and not block[i].line.plain[:1].islower()):
                end = i
                break
        rest = block[end:]
        bounds = [*starts, end]
        for letter_index, (start, stop) in enumerate(zip(bounds, bounds[1:], strict=False)):
            lines = [OPTION_MD.sub("", block[start].line.text, count=1)] + [
                e.line.text for e in block[start + 1 : stop]
            ]
            letter = cast(Literal["A", "B", "C", "D", "E"], chr(ord("A") + letter_index))
            options.append(RawOption(letter=letter, body_md=_join(lines)))
            flags |= set().union(*(e.flags for e in block[start:stop]))
    flags |= set().union(*(e.flags for e in statement_entries)) if statement_entries else set()
    statement_entries = _bullets(statement_entries)
    statement = "\n\n".join(_choice_paragraphs(statement_entries))
    if not statement.strip():
        flags.add("empty_item")
    if re.search(r"sublinhad", statement, re.I) and "<u>" not in statement:
        flags.add("underline")
    page = block[0].page if block else 0
    return (
        RawQuestion(
            number=number,
            type="multiple_choice",
            statement_md=statement,
            options=options,
            passage_key=passage,
            page=page,
            flags=sorted(flags),
        ),
        rest,
    )


def _bullets(entries: list[_Entry]) -> list[_Entry]:
    """Lista com marcador "•" que a fonte decorativa entrega como "C" (PC/GO 2016): duas ou mais
    linhas do enunciado começando por "C" na margem são itens de lista, não a alternativa C."""
    marked = [e for e in entries if _at_margin(e) and BULLET_C.match(e.line.plain)]
    if len(marked) < 2:
        return entries
    for entry in marked:
        line = entry.line
        entry.line = line.model_copy(
            update={
                "plain": BULLET_C.sub("• ", line.plain, count=1),
                "text": re.sub(r"^(\*{0,2})C\s+", r"\1• ", line.text, count=1),
            }
        )
    return entries


def _choice_paragraphs(entries: list[_Entry]) -> list[str]:
    """Parágrafos do enunciado: recuo de primeira linha, linha curta anterior ou item
    enumerado (I, II, III; a), b)...) começam parágrafo novo. O crédito em letra miúda, alinhado à
    direita e quebrado em várias linhas, é um parágrafo só, até a linha que o encerra (PC/PB 2021
    cargo 13, questão 65), como no certo/errado (`_paragraphs`)."""
    paragraphs: list[list[str]] = []
    previous: _Entry | None = None
    for index, entry in enumerate(entries):
        indented = entry.line.x0 > entry.left + PARAGRAPH_INDENT
        enumerated = _at_margin(entry) and (
            ROMAN_ITEM.match(entry.line.plain) is not None or entry.line.plain.startswith("• ")
        )
        credit_done = previous is not None and (
            CREDIT_END.search(previous.line.plain.strip()) or _paren_credit_end(entries, index - 1)
        )
        broken = (indented or (previous is not None and previous.short)) and not _credit_goes_on(
            entries, index
        )
        new = previous is None or broken or enumerated or bool(credit_done)
        if new:
            paragraphs.append([])
        paragraphs[-1].append(entry.line.text)
        previous = entry
    return [_join(lines) for lines in paragraphs if lines]


def _passage_labels(passage: RawPassage) -> list[str]:
    """Rótulos pelos quais as questões citam o texto-base: a chave (quando é rótulo da banca) e o
    título da primeira linha ("Figura 5A2" num texto anônimo)."""
    labels = [] if re.fullmatch(r"g\d+", passage.key) else [passage.key]
    title = PASSAGE_TITLE.match(passage.body_md)
    if title and title.group(1) not in labels:
        labels.append(title.group(1))
    return labels


def _referenced_passage(question: RawQuestion, labels: dict[str, str]) -> str | None:
    """O último texto-base cujo rótulo aparece no enunciado ou nas alternativas."""
    text = " ".join([question.statement_md, *(o.body_md for o in question.options)])
    cited = [
        key
        for label, key in labels.items()
        if re.search(rf"(?<![\w-]){re.escape(label)}(?![\w-])", text)
    ]
    return cited[-1] if cited else None


def _reference_flags(question: RawQuestion, labels: dict[str, str]) -> set[str]:
    """Remissões que o parser não resolveu: rótulo citado sem texto-base com esse rótulo, texto sem
    rótulo citado por questão sem texto-base, figura da própria questão (não há imagens), comando
    que remete ao que vem antes dele sem texto-base."""
    text = " ".join([question.statement_md, *(o.body_md for o in question.options)])
    flags: set[str] = set()
    cited = {m.group(1) for m in LABEL_REF.finditer(text)}
    if any(label not in labels for label in cited):
        flags.add("missing_passage")
    if question.passage_key is None and (
        (IMPLICIT_REF.search(question.statement_md) and not _generic_command(question))
        or LINE_REF.search(text)
    ):
        flags.add("missing_passage")
    if FIGURE_REF.search(text) or FIGURE_REF_WIDE.search(text) or DEPICTED.search(text):
        flags.add("figure")
    elif question.passage_key is None and _command_points_back(question):
        flags.add("missing_passage")
    return flags


def _command_points_back(question: RawQuestion) -> bool:
    """Comando de grupo certo/errado que remete ao que vem antes dele ("os dados acima"), numa
    questão sem texto-base: o que o comando aponta ficou de fora."""
    if question.type != "true_false" or "\n\n" not in question.statement_md:
        return False
    command = question.statement_md.split("\n\n")[0]
    return BACK_REF.search(ITEMS_PHRASE.sub(" ", command)) is not None


def _generic_command(question: RawQuestion) -> bool:
    """Item certo/errado cujo comando não aponta documento nenhum ("Com relação à função e à
    linguagem das correspondências oficiais, julgue os itens seguintes."): "o expediente" e "o
    memorando" do item são o gênero, não um texto que faltou (PF 2012 escrivão 18, papiloscopista
    19, agente 26). Múltipla escolha não tem comando separado e segue a regra antiga."""
    if question.type != "true_false" or "\n\n" not in question.statement_md:
        return False
    command = question.statement_md.split("\n\n")[0]
    return SHOWN_DOCUMENT.search(ITEMS_PHRASE.sub(" ", command)) is None


def _section_title(plain: str) -> bool:
    return SECTION_TITLE.match(plain) is not None and len(plain.split()) >= 2


def _bold_title(paragraph: str) -> bool:
    text = paragraph.strip()
    return (
        text.startswith("**")
        and text.endswith("**")
        and text.count("**") == 2
        and len(text.split()) <= 8
        and not text.rstrip("*").endswith((".", ":", "?"))
    )


def _passage_flags(questions: list[RawQuestion], passages: dict[str, RawPassage]) -> None:
    """Texto-base que cita figura/tabela ou que é só o crédito de uma imagem: a questão depende de
    uma figura que não foi extraída. Itens que são períodos consecutivos de um parágrafo: cada um
    depende dos outros itens, que não ficam no texto-base."""
    for question in questions:
        passage = passages.get(question.passage_key or "")
        opening = question.statement_md.split("\n\n")[0]
        if CONSECUTIVE_ITEMS.search(opening) or (
            passage is not None and CONSECUTIVE_ITEMS.search(passage.body_md)
        ):
            question.flags = sorted({*question.flags, "consecutive_items"})
        if passage is None:
            continue
        body = passage.body_md.strip()
        if (
            FIGURE_REF.search(body)
            or FIGURE_REF_WIDE.search(body)
            or DEPICTED.search(body)
            or (len(body) < 250 and CREDIT_ONLY.match(body))
        ):
            question.flags = sorted({*question.flags, "figure"})


def _bold_heading(entries: list[_Entry]) -> bool:
    """Título de bloco em negrito ("**Atualidades e conhecimentos...**") ou em caixa alta: não é
    texto-base."""
    return len(entries) <= 2 and all(
        (e.line.text.strip().startswith("**") and e.line.text.strip().endswith("**"))
        or _section_title(e.line.plain)
        for e in entries
    )


def _open_group_choice(lead: _Unit, first: int, passages: dict[str, RawPassage]) -> str | None:
    """Abertura entre questões de múltipla escolha: textos rotulados viram textos-base; texto sem
    rótulo vira texto-base anônimo ("g<primeira questão>"), salvo título de bloco em negrito.
    Não há comando a separar. Devolve a chave do último texto da abertura."""
    segments: list[tuple[str | None, list[_Entry]]] = [(None, [])]
    for entry in lead.entries:
        match = TEXT_LABEL.match(entry.line.plain)
        if match:
            segments.append((match.group(1), []))
        else:
            segments[-1][1].append(entry)
    key: str | None = None
    for label, entries in segments:
        if not entries or (label is None and _bold_heading(entries)):
            continue
        key = label or f"g{first}"
        _add_passage(passages, key, _text_paragraphs(entries), entries)
    return key


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
    if entry.after_justification:
        return False
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
    # Item que é só o número (as opções são figuras, PRF 2018 item 26): não há frase em aberto, e
    # o parágrafo recuado que vem depois é o texto-base seguinte, não continuação.
    bare_number = len(item.entries) == 1 and BARE_NUMBER.match(previous) is not None
    sentence_done = previous.endswith((".", "?", "!")) or bare_number
    title = entry.line.text.startswith("**") and entry.line.text.endswith("**")
    if sentence_done and (entry.after_gap or title):
        return False  # "Espaço livre" ou título em negrito encerram o item
    starts_paragraph = abs(indent - PARAGRAPH_INDENT_AT) < 4 and entry.line.plain[:1].isupper()
    if starts_paragraph and (previous.endswith((".", "?", "!", ":")) or bare_number):
        return False
    # Primeira linha de parágrafo com recuo maior que o de costume (varia entre provas): longa,
    # começando com maiúscula, depois de frase terminada. Fórmula centralizada é curta e fica.
    new_paragraph = indent > HANGING_MAX and entry.line.plain[:1].isupper() and not entry.short
    return not (new_paragraph and sentence_done)


def _stream(pages: list[Page]) -> list[_Entry]:
    """Linhas da prova objetiva em ordem de leitura, com figuras atribuídas às linhas vizinhas."""
    stream: list[_Entry] = []
    gap = False
    in_justification = False
    justification_color = _justification_color(pages)
    # Sem o marcador "PROVA OBJETIVA", começa do início; instruções numeradas da capa não viram
    # itens porque item só começa depois de um comando ("julgue").
    started = not any(START.search(line.plain) for page in pages for line in page.lines)
    if started and any(
        line.column == 0 and SECTION_START.search(line.plain)
        for page in pages
        for line in page.lines
    ):
        started = False  # cadernos de 2017 sem "PROVA OBJETIVA": começa no título da seção
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
        start_y = 0.0  # figuras acima do marcador são cabeçalho da prova
        for line in page.lines:
            if not started:
                started = line.column == 0 and bool(
                    START.search(line.plain) or SECTION_START.search(line.plain)
                )
                start_y = line.y1
                continue
            if STOP.search(line.plain) and (line.column == 0 or line.size >= STOP_TITLE_SIZE):
                stream.extend(_with_figures(page, entries, skipped, start_y))
                return stream
            if PAGE_FOOTER.match(line.plain.strip()) and line.y0 > page.height * PAGE_FOOTER_AT:
                continue
            if (
                SKIP.match(line.plain)
                or _subject_heading(line)
                or (skipped and _heading_continuation(skipped[-1], line))
            ):
                skipped.append(line)
                gap = True
                continue
            if any(_contains(image, line) for image in images) and not QUESTION_TITLE.match(
                line.plain
            ):
                continue  # rótulos de gráfico desenhados sobre a imagem (título de questão não)
            table = line.plain.startswith("||")
            closed = False  # esta linha vem logo depois de uma justificativa
            if in_justification:
                if justification_color is not None:
                    # Caderno com cor: a justificativa vai até a primeira linha de outra cor. O
                    # marcador "<FimJust>" em branco (invisível, PCDF 2026) ainda é dela.
                    if line.color in (justification_color, WHITE) and not JUSTIFICATION.search(
                        line.plain
                    ):
                        continue
                else:
                    indent = line.x0 - lefts[line.column]
                    # Sem cor (OCR): a continuação da justificativa fica no recuo de continuação
                    # de item (~18); recuo de parágrafo (~29) é o começo de um texto-base (PCDF
                    # 2019/2020): não é justificativa.
                    if ITEM_INDENT < indent < PARAGRAPH_INDENT_AT - 4:
                        continue
                in_justification = False  # próximo item, comando ou texto-base
                closed = True
            # Tabela de justificativas (PC/PE 2023): fica no fluxo, e a múltipla escolha pula
            # tudo até o próximo título de questão (as linhas da tabela estão na margem).
            cut = None if table else JUSTIFICATION.search(line.plain)
            if cut is not None:
                in_justification = True
                if not line.plain[: cut.start()].strip():
                    continue
                line = _before(line, cut.start())
            elif (
                not table
                and justification_color is not None
                and line.color == justification_color
                and VERDICT.match(line.plain)
            ):
                in_justification = True  # justificativa sem o prefixo "JUSTIFICATIVA -"
                continue
            entry = _Entry(
                page.number,
                line,
                lefts[line.column],
                short=line.x1 < rights[line.column] - SHORT_LINE,
                after_gap=gap,
                after_justification=closed,
            )
            gap = False
            if BROKEN_MATH.search(line.plain):
                entry.flags.add("formula")
            if line.x0 > entry.left + ODD_INDENT and entry.short and line.size >= CITATION_SIZE:
                entry.flags.add("layout")  # linha recuada e curta: código, tabela, fórmula
            if line.odd_glyph:
                entry.flags.add("formula")  # símbolo que saiu como dígito ("P6Q")
            if line.scripts:
                entry.flags.add("formula")  # índices/expoentes que o texto puro achata
            entries.append(entry)
        stream.extend(_with_figures(page, entries, skipped, start_y))
    return stream


def _justification_color(pages: list[Page]) -> int | None:
    """Cor das justificativas do caderno: a das linhas que começam com "JUSTIFICATIVA", se não
    for preta (PCDF: azul). Sem cor (OCR, cadernos em preto) a justificativa sai pelo recuo."""
    colors = Counter(
        line.color
        for page in pages
        for line in page.lines
        if line.plain.lstrip("|* ").startswith("JUSTIFICATIVA")
    )
    if not colors:
        return None
    color = colors.most_common(1)[0][0]
    return color or None


# Título de seção sem negrito, em corpo maior ("Conhecimentos acerca do Estado do Tocantins",
# CBM/TO 2022, 12 pt contra 10 pt do texto): no alto da coluna, grudava na última alternativa.
KNOWLEDGE_TITLE = re.compile(r"^Conhecimentos\b(?:\s+\S+){0,7}$", re.I)
KNOWLEDGE_TITLE_MIN_SIZE = 11.5


def _subject_heading(line: Line) -> bool:
    """Linha só em negrito, curta, sem pontuação final, que começa com nome de disciplina; ou
    título de seção "Conhecimentos ..." em negrito ou em corpo maior."""
    plain_text = line.plain.strip()
    if (
        KNOWLEDGE_TITLE.match(plain_text)
        and not plain_text.endswith((".", ":", "?", ","))
        and (line.text.strip().startswith("**") or (line.size or 0) >= KNOWLEDGE_TITLE_MIN_SIZE)
    ):
        return True
    text = line.text.strip()
    if not (text.startswith("**") and text.endswith("**")) or len(line.plain.split()) > 6:
        return False
    plain = line.plain.strip().casefold()
    return not plain.endswith((".", ":", "?")) and any(
        plain == name or plain.startswith(name + " ") for name in SUBJECT_NAMES
    )


def _heading_continuation(heading: Line, line: Line) -> bool:
    """Segunda linha de um título "Conhecimentos ..." em corpo maior ("Conhecimentos acerca do
    estado" / "do Tocantins", CBM/TO 2021): mesma coluna, mesmo corpo, logo abaixo, curta."""
    return (
        KNOWLEDGE_TITLE.match(heading.plain.strip()) is not None
        and (heading.size or 0) >= KNOWLEDGE_TITLE_MIN_SIZE
        and line.column == heading.column
        and abs((line.size or 0) - (heading.size or 0)) < 0.5
        and 0 < line.y0 - heading.y1 < (heading.size or 0)
        and len(line.plain.split()) <= 4
        and not line.plain.rstrip().endswith((".", ":", "?", ","))
    )


def _before(line: Line, index: int) -> Line:
    """A linha até `index` do texto puro (a justificativa grudada no fim do item cai fora)."""
    plain = line.plain[:index].rstrip()
    text = line.text
    marker = JUSTIFICATION.search(text)
    if marker is not None:
        text = text[: marker.start()].rstrip()
        if text.count("**") % 2:
            text += "**"
        if text.count("*") % 2:
            text += "*"
    return line.model_copy(update={"plain": plain, "text": text})


def _with_figures(
    page: Page, entries: list[_Entry], skipped: list[Line], start_y: float = 0.0
) -> list[_Entry]:
    """Marca com 'figure' a linha que antecede cada figura (no Cebraspe, o texto que a apresenta
    vem antes dela); se a figura abre a coluna, marca a linha seguinte."""
    middle = page.width / 2
    titles = [e.line for e in entries if QUESTION_TITLE.match(e.line.plain)]
    frames = _skipped_frames(page.figures, skipped)
    for figure in page.figures:
        if (
            figure.y1 <= start_y
            or id(figure) in frames
            or any(_overlaps(figure, line) for line in titles)
        ):
            continue  # faixa de fundo de título ("BLOCO II", "Questão 7")
        column = 1 if figure.x1 <= middle + 12 else 2 if figure.x0 >= middle - 12 else 0
        same = [e for e in entries if column == 0 or e.line.column in (column, 0)]
        above = [e for e in same if e.line.y0 < figure.y0]
        below = [e for e in same if e.line.y0 >= figure.y0 - 2]
        first_below = min(below, key=lambda e: e.line.y0) if below else None
        if (
            above
            and first_below is not None
            and first_below.line.y0 - figure.y1 <= FIGURE_CREDIT_GAP
            and _credit_below(below, first_below)
            and max(above, key=lambda e: e.line.y0).line.plain.rstrip().endswith(SENTENCE_STOP_FULL)
        ):
            # Figura com crédito logo abaixo: é a abertura do grupo seguinte, não fim do item de
            # cima (PF 2012 papiloscopista: impressões digitais entre o item 58 e o comando).
            first_below.flags.add("figure")
        elif above:
            max(above, key=lambda e: e.line.y0).flags.add("figure")
        elif below:
            min(below, key=lambda e: e.line.y0).flags.add("figure")
    return entries


def _credit_below(below: list[_Entry], first: _Entry) -> bool:
    """Logo abaixo da figura vem o crédito dela: linhas miúdas, do mesmo corpo, até a que o
    encerra ("... (com adaptações)."), em no máximo `CREDIT_MAX_LINES` linhas."""
    size = first.line.size
    if size >= CITATION_SIZE:
        return False
    lines = sorted(below, key=lambda e: e.line.y0)
    for entry in lines[:CREDIT_MAX_LINES]:
        if entry.line.size != size:
            return False
        if CREDIT_END.search(entry.line.plain.strip()):
            return True
    return False


FRAME_TOUCH = 1.5  # pt entre traços de um mesmo quadro desenhado


def _skipped_frames(figures: list[Figure], skipped: list[Line]) -> set[int]:
    """Desenhos que formam o quadro de uma linha ignorada ("RASCUNHO", "BLOCO II"): os traços que
    se tocam são juntados, e o grupo cuja caixa contém a linha ignorada não é figura. No site antigo
    do Cebraspe o quadro do "RASCUNHO" vem em quatro traços e um filete à direita, nenhum com a
    linha inteira dentro (PF 2012 escrivão, item 57)."""
    groups: list[list[Figure]] = []
    for figure in figures:
        touching = [g for g in groups if any(_touch(figure, other) for other in g)]
        merged = [figure, *(f for g in touching for f in g)]
        groups = [g for g in groups if not any(g is t for t in touching)] + [merged]
    frames: set[int] = set()
    for group in groups:
        box = Figure(
            kind="drawing",
            x0=min(f.x0 for f in group),
            y0=min(f.y0 for f in group),
            x1=max(f.x1 for f in group),
            y1=max(f.y1 for f in group),
        )
        if any(_contains(box, line) for line in skipped):
            frames.update(id(f) for f in group)
    return frames


def _touch(a: Figure, b: Figure) -> bool:
    return (
        a.x0 <= b.x1 + FRAME_TOUCH
        and b.x0 <= a.x1 + FRAME_TOUCH
        and a.y0 <= b.y1 + FRAME_TOUCH
        and b.y0 <= a.y1 + FRAME_TOUCH
    )


def _contains(figure: Figure, line: Line) -> bool:
    return (
        figure.x0 - 2 <= line.x0
        and line.x1 <= figure.x1 + 2
        and figure.y0 - 2 <= line.y0
        and line.y1 <= figure.y1 + 2
    )


def _overlaps(figure: Figure, line: Line) -> bool:
    """Figura na altura da linha e na mesma coluna: caixa de fundo, ícones e filetes decorativos
    do título "Questão N" (PC/RJ 2021 desenha ícones ao lado do título)."""
    vertical = min(figure.y1, line.y1) - max(figure.y0, line.y0)
    same_side = figure.x0 < line.x1 + 300 and figure.x1 > line.x0 - 300
    thin_rule = figure.y1 - figure.y0 <= 3 and (
        abs(figure.y0 - line.y0) <= 6 or abs(figure.y1 - line.y1) <= 6
    )  # filete logo acima ou abaixo do título
    return same_side and (vertical > 0.5 * (line.y1 - line.y0) or thin_rule)


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
    if len(situation) == 1 and _bold_title(situation[0]):
        situation = []  # título de seção em negrito ("**Legislação pertinente ao CBMAL**")
    if situation:
        key = f"g{first}"
        _add_passage(passages, key, situation, last_entries)
        return command, key, flags
    return command, referenced, flags


def _command_page(lead: _Unit) -> int:
    """Página onde começa o comando do grupo (para a amostra mostrar a página certa).

    O comando sai do último trecho da abertura (depois do último rótulo de texto) ou, sem rótulo,
    da abertura inteira; a primeira linha desse trecho dá a página. Quando há situação antes do
    comando no mesmo trecho, a página é a do início da situação, que é anterior ou igual: a
    amostra mostra uma página a mais, nunca uma a menos.
    """
    labeled = [i for i, e in enumerate(lead.entries) if TEXT_LABEL.match(e.line.plain)]
    if labeled and labeled[0] > 0:
        return lead.entries[0].page  # texto antes do primeiro rótulo abre o comando
    start = labeled[-1] + 1 if labeled else 0
    rest = lead.entries[start:] or lead.entries
    return rest[0].page


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
    number: int,
    item: _Unit,
    command: str,
    passage: str | None,
    group_flags: set[str],
    command_page: int | None = None,
) -> RawQuestion:
    first = item.entries[0]
    text_lines = [ITEM_MD.sub("", first.line.text, count=1)] + [
        e.line.text for e in item.entries[1:]
    ]
    breaks = _letter_breaks(item.entries)
    pieces: list[list[str]] = [[]]
    for index, text in enumerate(text_lines):
        pieces[-1].append(text)
        if index in breaks:
            pieces.append([])
    # Vocativo e fecho de correspondência ficam na própria linha ("Senhor Delegado," |
    # "Atenciosamente," | "José da Silva"): quebra de linha do Markdown (docs/content-format.md).
    body = "\\\n".join(_join(piece) for piece in pieces if piece)
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
    if any(
        e.short and not e.line.plain.endswith(SENTENCE_STOP) and i not in breaks
        for i, e in enumerate(item.entries[:-1])
    ):
        flags.add("layout")  # quebras de linha com significado (código, versos, listas)
    if re.search(r"sublinhad", statement, re.I) and "<u>" not in statement:
        flags.add("underline")
    if command[:1].islower():
        # Comando que começa no meio de uma frase: o corte entre texto e comando errou (lista com
        # recuo deslocado, "III recebimento ... | prestados no mês ...", PF 2012 itens 83 e 84).
        flags.add("layout")
    return RawQuestion(
        number=number,
        type="true_false",
        statement_md=statement,
        passage_key=passage,
        page=first.page,
        command_page=command_page if command else None,
        flags=sorted(flags),
    )


def _letter_breaks(entries: list[_Entry]) -> set[int]:
    """Índices das linhas do item depois das quais vem quebra de linha: o vocativo ou o fecho de
    uma correspondência, curto e terminado em vírgula, e a linha curta terminada em ponto que
    antecede o fecho (PF 2012 escrivão 21–22, papiloscopista 14 e 17)."""
    breaks: set[int] = set()
    for index, entry in enumerate(entries[:-1]):
        plain = entry.line.plain.strip()
        if index == 0:
            plain = re.sub(r"^\d{1,3}\s+", "", plain)  # número do item
        if entry.short and LETTER_LINE.match(plain):
            breaks.add(index)
            previous = entries[index - 1] if index else None
            if (
                previous is not None
                and previous.short
                and previous.line.plain.rstrip().endswith(SENTENCE_STOP_FULL)
            ):
                breaks.add(index - 1)
    return breaks


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
    leading = _leading(entries)
    for index, entry in enumerate(entries):
        indented = entry.line.x0 > (base or entry.left) + PARAGRAPH_INDENT
        title_goes_on = previous is not None and _is_title(previous) and _is_title(entry)
        # Crédito do texto em letra miúda, alinhado à direita e quebrado em duas linhas ou mais
        # (PF 2012, PM/MA 2017): segue até a linha que o encerra ("(com adaptações).").
        credit_goes_on = _credit_goes_on(entries, index)
        title_goes_on = title_goes_on or credit_goes_on
        # Linha anterior curta também fecha o parágrafo: com numeração de linhas na margem, o
        # recuo de "7 Em 2016, ..." se perde quando o número sai (PC/MA 2017).
        new = (
            previous is None
            or (indented and not title_goes_on)
            or (previous.short and not title_goes_on)
            or abs(entry.line.size - previous.line.size) >= 1
            or bool(CREDIT_END.search(previous.line.plain.strip()))
            or (not title_goes_on and _block_gap(previous, entry, leading))
            or (
                bool(PROPOSITION.match(entry.line.plain))
                and previous.line.plain.rstrip().endswith(SENTENCE_STOP)
            )
        )
        if new:
            paragraphs.append([])
        paragraphs[-1].append(entry.line.text)
        previous = entry
    return [_join(lines) for lines in paragraphs]


# Proposição rotulada no começo da linha ("P1: Existe...", "P3: Ele é..."): abre parágrafo.
PROPOSITION = re.compile(r"^P\d{1,2}\s?:\s")
# Espaço, em pt, além do entrelinha comum: blocos separados (PF 2012 escrivão, item 57).
BLOCK_GAP = 3.0


def _vertical_gap(previous: _Entry, entry: _Entry) -> float | None:
    """Espaço entre duas linhas seguidas da mesma coluna e página; None se não dá para medir."""
    if previous.page != entry.page or previous.line.column != entry.line.column:
        return None
    gap = entry.line.y0 - previous.line.y1
    return gap if gap >= 0 else None


def _leading(entries: list[_Entry]) -> float | None:
    """Espaço comum entre as linhas do trecho (a mediana); None com poucas linhas para medir."""
    gaps = sorted(
        gap
        for previous, entry in zip(entries, entries[1:], strict=False)
        if (gap := _vertical_gap(previous, entry)) is not None
    )
    if len(gaps) < 3:
        return None
    return gaps[len(gaps) // 2]


def _block_gap(previous: _Entry, entry: _Entry, leading: float | None) -> bool:
    """Espaço vertical entre as duas linhas bem maior que o entrelinha do trecho: o original
    separa ali dois blocos, mesmo que a linha anterior vá até a margem e a seguinte não tenha
    recuo (PF 2012 escrivão, item 57: introdução | P1 e P2 | "Diante dessa situação..." | P3 e P4).
    Linha com índice ou expoente tem a caixa mais alta e não conta; frase que segue de uma linha à
    outra também não (fórmula ou figura no meio da linha empurra a seguinte: PF 2012
    papiloscopista, item 109)."""
    if leading is None or previous.line.scripts or entry.line.scripts:
        return False
    if not previous.line.plain.rstrip().endswith(SENTENCE_STOP) or entry.line.plain[:1].islower():
        return False
    if COMMAND.search(entry.line.plain) or COMMAND.search(previous.line.plain):
        # O corte entre a situação e o comando tem regra própria (`_split_command`); o espaço não
        # a substitui. No PF 2012 agente (itens 83 e 84) ele tirava do comando o pedaço de lista
        # partido na troca de coluna, que era o que mandava os itens para revisão; no PF 2018
        # papiloscopista (item 51) separava "julgue ..., acerca da seguinte proposição:" de "P: ...".
        return False
    gap = _vertical_gap(previous, entry)
    return gap is not None and gap > leading + BLOCK_GAP


CREDIT_MAX_LINES = 6  # crédito mais longo que isso não é crédito


def _credit_line(entry: _Entry, size: float) -> bool:
    """Linha de crédito: letra miúda, do mesmo tamanho das outras, alinhada à direita."""
    return (
        entry.line.size < CITATION_SIZE
        and entry.line.size == size
        and entry.line.x0 > entry.left + ODD_INDENT
    )


def _credit_goes_on(entries: list[_Entry], index: int) -> bool:
    """A linha `index` continua o crédito aberto na anterior: as duas e as seguintes são linhas de
    crédito, e alguma delas, até `CREDIT_MAX_LINES`, o encerra. Sem a linha de fecho não emenda.
    Também fecha o crédito o ")" que fecha o "(" da primeira linha dele (`_paren_credit_end`)."""
    if index == 0:
        return False
    previous = entries[index - 1]
    size = previous.line.size
    if not _credit_line(previous, size) or CREDIT_END.search(previous.line.plain.strip()):
        return False
    if _paren_credit_end(entries, index - 1):
        return False
    if _credit_line_wraps(previous, entries[index]):
        return True
    for offset, entry in enumerate(entries[index : index - 1 + CREDIT_MAX_LINES]):
        if not _credit_line(entry, size):
            return False
        if CREDIT_END.search(entry.line.plain.strip()):
            return True
        if _paren_credit_end(entries, index + offset):
            return True
    return False


def _paren_credit_end(entries: list[_Entry], index: int) -> bool:
    """A linha `index` encerra um crédito entre parênteses ("(FRANÇA, Genival Veloso de. *Medicina
    Legal*, 11.ª ed., reimpr." | "Rio de Janeiro: Guanabara Koogan, 2021, p. 474).", PC/PB 2021
    cargo 11, questão 66): ela e as anteriores, até a que abre com "(", são linhas de crédito do
    mesmo corpo, no máximo `CREDIT_MAX_LINES`, e o ")" do fim fecha o "(" do começo."""
    if index < 0:
        return False
    last = entries[index]
    size = last.line.size
    if not _credit_line(last, size) or not last.line.plain.strip().endswith((")", ").")):
        return False
    for start in range(index, max(-1, index - CREDIT_MAX_LINES), -1):
        if not _credit_line(entries[start], size):
            return False
        if entries[start].line.plain.lstrip().startswith("("):
            text = " ".join(e.line.plain.strip() for e in entries[start : index + 1])
            depth = 0
            for position, char in enumerate(text):
                depth += {"(": 1, ")": -1}.get(char, 0)
                if depth <= 0 and position < len(text.rstrip(".")) - 1:
                    return False  # o "(" do começo fecha antes do fim: não é um crédito só
            return depth == 0
    return False


CREDIT_ALIGN = 1.0  # pt: linhas do mesmo bloco de crédito começam no mesmo x
# Espaço máximo entre as linhas de um crédito, em fração do corpo da letra (PF 2012: 3,4 pt em 6).
CREDIT_GAP = 0.75


def _credit_line_wraps(previous: _Entry, entry: _Entry) -> bool:
    """Crédito sem fecho reconhecível ("... Victor Civita, 1981. Tradução de Brenno Silveira e
    outros.", PF 2018 agente, texto 12A1AAA): a linha anterior vai até a margem direita (justificada,
    não é a última do parágrafo), não termina frase, e a seguinte é linha de crédito do mesmo corpo
    começando no mesmo x, logo abaixo (espaço de até 3/4 do corpo). Só então é a mesma frase
    quebrada pela justificação. O espaço separa as legendas de gráfico, em letra miúda, uma embaixo
    da outra no mesmo x ("40 a 49 anos" | "50 a 59 anos", PF 2021 g77)."""
    gap = _vertical_gap(previous, entry)
    return (
        _credit_line(entry, previous.line.size)
        and gap is not None
        and gap <= previous.line.size * CREDIT_GAP
        and abs(entry.line.x0 - previous.line.x0) <= CREDIT_ALIGN
        and not previous.short
        and not previous.line.plain.rstrip().endswith(SENTENCE_STOP)
    )


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
        if COMMAND_VERB.search(sentence):
            before = " ".join(sentences[:index]).strip()
            command = " ".join(sentences[index:]).strip()
            if (
                not before
                and rest
                and not command[:1].isupper()
                and not rest[-1].rstrip().endswith(SENTENCE_STOP_FULL)
            ):
                # Comando partido na troca de coluna (PM/AL 2018): "No que concerne aos ... do" |
                # "texto 1A1-I, julgue" (ou "13A1AAA, julgue", PF 2018). A frase inacabada do
                # parágrafo anterior abre o comando.
                *done, unfinished = SENTENCE_END.split(rest[-1])
                rest = [*rest[:-1], " ".join(done).strip()] if done else rest[:-1]
                command = f"{unfinished.strip()} {command}"
            return [*rest, before] if before else [p for p in rest if p], command
    if not last.rstrip().endswith(SENTENCE_STOP_FULL):
        # Sem "julgue": frase inacabada no fim ("Nessa situação hipotética,") que cada item completa.
        before = " ".join(sentences[:-1]).strip()
        return [*rest, before] if before else rest, sentences[-1].strip()
    return paragraphs, ""


def _join(lines: list[str]) -> str:
    """Junta as linhas de um parágrafo com espaço.

    Hífen colado no fim da linha é do original e fica, sem espaço depois: o Cebraspe não separa
    palavra por sílaba, e a linha só quebra no hífen de composto, ênclise ou rótulo ("pós-" |
    "morte", "aplica-" | "se", "Jaci-" | "Paraná", "1A1-" | "I"). Decisão 0032.
    """
    text = ""
    for line in lines:
        if not text:
            text = line
        elif HYPHEN_END.search(text) and HYPHEN_NEXT.match(line):
            text += line
        else:
            text = f"{text} {line}"
    return _normalize(text)


def _normalize(text: str) -> str:
    text = re.sub(r"\*\*\s+\*\*", " ", text)  # negrito quebrado em pedaços
    text = re.sub(r"(?<!\*)\*\s+\*(?!\*)", " ", text)  # itálico quebrado em pedaços
    # Código inline quebrado na troca de linha ("`Bibliotecas >`" | "`Documentos > Projetos`").
    text = re.sub(r"(?<![`\\])`([^`]+)` `([^`]+)`(?!`)", r"`\1 \2`", text)
    return re.sub(r"\s+", " ", text).strip()


# --- gabarito ---------------------------------------------------------------------------------

KEY_MARK = re.compile(r"^[A-EX]$")  # C/E/X (certo/errado) ou A–E/X (múltipla escolha)
KEY_NUMBER = re.compile(r"^\d{1,3}$")
KEY_HEADERS = ("Item", "Gabarito", "Questão", "Questao", "QUESTÃO", "ITEM", "GABARITO")


def parse_answer_key(pages: list[Page]) -> AnswerKey:
    """Gabarito do Cebraspe: grade de linhas "Item" (números) e "Gabarito" (C, E ou X).

    Cada linha de números é pareada com a linha de marcas que vem logo depois dela (na mesma
    coluna, pela ordem de leitura). Linhas que não fecham o par são ignoradas.
    """
    answers: dict[int, AnswerMark] = {}
    previous: list[int] | None = None
    for page in pages:
        for line in page.lines:
            # "*E": gabarito preliminar alterado (PM/AL 2017); o asterisco não é parte da marca.
            tokens = [t.lstrip("*") for t in line.plain.split() if t not in KEY_HEADERS]
            tokens = [t for t in tokens if t]
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
