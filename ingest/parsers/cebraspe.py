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
OPTION_MD = re.compile(r"^(?:\*\*?)?[A-E](?:\*\*?)?(?:\s+|$)")  # "*E* intranet." (PC/PB 2021)
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
# Remissão grafada sem espaço no próprio caderno ("do texto1A5-I", PM/SC 2023 soldado q37 e q39):
# o rótulo colado à palavra do título, sempre em maiúsculas, ganha o espaço antes da busca.
GLUED_REF = re.compile(rf"\b({_TITLE_WORDS})(?=(?-i:[0-9A-Z]*\d[A-Z]))", re.I)


def _spaced_refs(text: str) -> str:
    """O texto com "texto1A5-I" lido como "texto 1A5-I" (só para achar a remissão)."""
    return GLUED_REF.sub(r"\1 ", text)


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
# Justificativa de alternativa sem o cabeçalho "JUSTIFICATIVAS" ("||A|| - Incorreta. Conforme o
# artigo 10...", PMDF 2025 P2 q79: a justificativa passou para a página seguinte, depois da
# alternativa E, sem o cabeçalho). Como o VERDICT, só vale na cor das justificativas do caderno.
OPTION_JUSTIFICATION = re.compile(r"^\|\|[A-E]\|\|\s*[-–]")
BARE_NUMBER = re.compile(r"^\d{1,3}$")
WHITE = 0xFFFFFF  # texto invisível
# Inclui a crase maiúscula ("... R$ 5.700,00. À luz do regime de caixa, julgue ...", PF 2012 agente,
# itens 83 e 84): sem ela, a frase do comando engolia o item IV da lista que vem antes.
SENTENCE_END = re.compile(r"(?<=[.!?:])\s+(?=[A-ZÀÁÉÍÓÚÂÊÔÃÕÇ“])")
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
FIGURE_SOURCE = re.compile(r"^Fonte\s*:", re.I)  # crédito de figura ("Fonte: IBGE")
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
    invisible: bool = False  # texto branco sem fundo (`_visible`)
    # Na cor das justificativas do caderno (`_justification_color`); falso sem cor (OCR, preto).
    justification_color: bool = False
    # Primeira linha da coluna logo abaixo de uma figura que abre a coluna (`_with_figures`).
    below_figure: bool = False


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
            number = int(earlier.group(1)) if earlier is not None else 0
            if (
                earlier is not None
                # A numeração recomeça em 1 na outra língua estrangeira, depois do comando dela
                # (CBM/AL 2017: espanhol e inglês, itens 1 a 5 cada, antes do item 6 da prova); sem
                # comando, o "1" é número de linha do texto-base.
                and (
                    number == skipped_items + 1
                    or (
                        number == 1
                        and skipped_items > 0
                        and any(COMMAND.search(e.line.plain) for e in lead.entries)
                    )
                )
                and number < first
                and line.x0 <= entry.left + ITEM_INDENT
            ):
                # Item de antes da prova: o que veio até aqui não é abertura do primeiro grupo.
                skipped_items = number
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
    herdam o texto (o texto-base não se estende até a próxima abertura). O texto sem rótulo não
    pode ser citado: vale também para as questões seguintes que retomam termos dele, até a
    primeira que não retoma ou que abre a sua própria situação (decisão 0013, emenda de
    2026-10-14)."""
    passages: dict[str, RawPassage] = {}
    questions: list[RawQuestion] = []
    expected = first
    lead = _Unit()
    block: list[_Entry] = []
    number = 0
    group_passage: str | None = None
    group_first = 0
    labels: dict[str, str] = {}  # rótulo citado pelas questões → chave do texto-base
    # Figura logo abaixo do título "Questão N" (a fotografia que abre a questão, CBM/RO 2022
    # questões 38 e 40): `_with_figures` marca a linha acima dela, que é o título; o título não
    # entra no bloco da questão, e a marca passa para a questão (decisão 0030, emenda).
    title_flags: set[str] = set()
    chain: str | None = None  # texto sem rótulo que ainda vale para as questões seguintes
    chain_terms: set[str] = set()
    seen_terms: set[str] = set()  # termos das questões já lidas

    def close() -> None:
        nonlocal lead, chain
        if not block:
            return
        question, rest = _choice_question(number, block, None, title_flags)
        key = _referenced_passage(question, labels) or (
            group_passage if number == group_first else None
        )
        if number > group_first and chain:
            if (
                not key
                and _terms(_question_text(question)) & chain_terms
                and not _own_situation(block)
            ):
                key = chain
            else:
                chain = None
        seen_terms.update(_terms(_question_text(question)))
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
                chain = group_passage if _unlabeled_situation(passages, group_passage) else None
                if chain:  # termos que o texto introduz: não apareceram nas questões anteriores
                    chain_terms = _terms(passages[chain].body_md) - seen_terms
                for key, passage in passages.items():
                    for label in _passage_labels(passage):
                        labels.setdefault(label, key)
                lead = _Unit()
            block = []
            number = expected
            expected += 1
            skipping = False
            title_flags = entry.flags & {"figure"}
        elif skipping and not TITLE_LINE.match(entry.line.plain):
            continue  # a justificativa termina no próximo título de questão ou de texto-base
        elif skipping:
            skipping = False  # título de texto-base (PC/PE 2023): abre o grupo seguinte
            block.append(entry)
        elif number and (
            JUSTIFICATION.match(entry.line.plain.lstrip("|* "))
            or (entry.justification_color and OPTION_JUSTIFICATION.match(entry.line.plain))
        ):
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
        # seguir é a abertura do próximo grupo (texto rotulado, instrução). Também termina no
        # recuo de parágrafo depois de frase terminada: o texto-base sem rótulo que abre o grupo
        # seguinte começa recuado, às vezes no alto da coluna seguinte (CBM/RO 2022, antes das
        # questões 23 e 28; decisão 0013, emenda de 2026-10-14).
        end = len(block)
        for i in range(starts[-1] + 1, len(block)):
            plain = block[i].line.plain
            starts_text = TITLE_LINE.match(plain) is not None or _section_title(plain)
            if (
                starts_text
                or (_at_margin(block[i]) and not block[i].line.plain[:1].islower())
                or _paragraph_after_option(block[i - 1], block[i])
                or _heading_after_option(block[i - 1], block[i])
            ):
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


# Termos de enunciado comuns a qualquer questão: não ligam a questão a um texto sem rótulo.
_GENERIC_WORDS = (
    "considere considerando considerando-se correto correta afirmar assinale opção opções seguir"
    " seguinte seguintes acima abaixo informações situação questão questões respectivamente"
    " conforme apresentado apresentada texto figura tabela então sobre entre ainda dessa nessa"
    " essas esses desse nesse sendo tenha tenham sejam seria igual valor mesma mesmo forma"
    " quando sabendo-se julgue itens acerca respeito relação base"
)


def _term(word: str) -> str:
    return word.casefold()[:5]


_GENERIC_TERMS = {_term(w) for w in _GENERIC_WORDS.split()}
UNLABELED_MIN_WORDS = 20  # texto sem rótulo mais curto que isso é título ou instrução


def _terms(text: str) -> set[str]:
    """Termos de um texto: palavras de 5 letras ou mais pelo radical (as 5 primeiras letras, que
    juntam "ligação" e "ligações") e siglas de 2 a 4 maiúsculas ("AOB")."""
    out: set[str] = set()
    for word in re.findall(r"[^\W\d_]+", text):
        if 2 <= len(word) <= 4 and word.isupper():
            out.add(word)
        elif len(word) >= 5 and _term(word) not in _GENERIC_TERMS:
            out.add(_term(word))
    return out


def _question_text(question: RawQuestion) -> str:
    return " ".join([question.statement_md, *(o.body_md for o in question.options)])


def _unlabeled_situation(passages: dict[str, RawPassage], key: str | None) -> bool:
    """Texto-base sem rótulo nem título, com corpo de texto (não é título de bloco)."""
    if key is None or not re.fullmatch(r"g\d+", key):
        return False
    passage = passages[key]
    return not _passage_labels(passage) and len(passage.body_md.split()) >= UNLABELED_MIN_WORDS


def _own_situation(block: list[_Entry]) -> bool:
    """A questão abre a sua própria situação: o enunciado começa com recuo de parágrafo ou traz
    figura (CBM/RO 2022 questão 27, o tanque, logo depois das questões da árvore)."""
    starts = _find_options(block)
    statement = block[: starts[0]] if starts else block
    if not statement:
        return False
    return statement[0].line.x0 - statement[0].left > HANGING_MAX or any(
        "figure" in e.flags for e in statement
    )


def _paragraph_after_option(previous: _Entry, entry: _Entry) -> bool:
    """Primeira linha de parágrafo depois da última alternativa: recuo maior que o da
    continuação, maiúscula, linha longa, e a alternativa terminou a frase. Fórmula ou tabela
    centralizada dentro da alternativa é curta ou não vem depois de frase terminada."""
    indent = entry.line.x0 - entry.left
    return (
        indent > HANGING_MAX
        and entry.line.plain[:1].isupper()
        and not entry.short
        and previous.line.plain.rstrip().endswith(SENTENCE_STOP_FULL)
    )


def _heading_after_option(previous: _Entry, entry: _Entry) -> bool:
    """Título de bloco em negrito depois da última alternativa: linha só em negrito, curta, sem
    pontuação final, e a alternativa terminou a frase ("**Normas relativas ao CBMTO**" e
    "**Noções de Informática**", CBM/TO 2022 soldado, depois das questões 10 e 30; com o estilo
    ligado o título fica em negrito, e sem isso grudava na alternativa D). O título vai para a
    abertura seguinte, onde `_bold_heading` o tira. Em corpo de título (`HEADING_MIN_SIZE`), o
    título encerra a alternativa mesmo sem ponto nela ("D Facebook" | "**Normas relativas ao
    CBMTO**" no alto da coluna seguinte, CBM/TO 2021 soldado, questão 40)."""
    plain = entry.line.plain.strip()
    return (
        _bold_only(entry.line)
        and 0 < len(plain.split()) <= 8
        and not plain.endswith((".", ":", "?", ",", ";"))
        and (
            previous.line.plain.rstrip().endswith(SENTENCE_STOP_FULL)
            or (entry.line.size or 0) >= HEADING_MIN_SIZE > (previous.line.size or 0)
        )
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
    """Parágrafos do enunciado: recuo de primeira linha, linha curta anterior, espaço vertical
    entre blocos (`_block_gap`) ou item
    enumerado (I, II, III; a), b)...) começam parágrafo novo. O crédito em letra miúda, alinhado à
    direita e quebrado em várias linhas, é um parágrafo só, até a linha que o encerra (PC/PB 2021
    cargo 13, questão 65), como no certo/errado (`_paragraphs`)."""
    paragraphs: list[list[list[str]]] = []
    previous: _Entry | None = None
    opener: _Entry | None = None  # primeira linha do parágrafo aberto
    leading = _leading(entries)
    verses = _verse_breaks(entries, leading)
    for index, entry in enumerate(entries):
        if index - 1 in verses:  # verso seguinte da mesma estrofe: quebra de linha
            paragraphs[-1].append([entry.line.text])
            previous = entry
            continue
        # Citação recuada em bloco (lei transcrita em letra menor): todas as linhas têm o mesmo
        # recuo, e só a primeira abre parágrafo (`_indented_block_goes_on`).
        indented = entry.line.x0 > entry.left + PARAGRAPH_INDENT and not (
            previous is not None and _indented_block_goes_on(previous, entry)
        )
        enumerated = _at_margin(entry) and (
            ROMAN_ITEM.match(entry.line.plain) is not None or entry.line.plain.startswith("• ")
        )
        credit_done = previous is not None and (
            _credit_closes(entries, index - 1) or _paren_credit_end(entries, index - 1)
        )
        # Espaço vertical entre blocos (`_block_gap`): o comando ("Assinale a opção correta.",
        # "Nessa situação hipotética, ...") separado da situação ou da lista que vem antes dele
        # (PM/RO 2022 questões 41 e 100, PM/DF 2025 P2 questão 76).
        gap = previous is not None and _block_gap(previous, entry, leading, command_rule=False)
        broken = (
            indented or (previous is not None and previous.short) or gap
        ) and not _credit_goes_on(entries, index)
        new = (
            previous is None
            or broken
            or enumerated
            or bool(credit_done)
            or _labeled_line_opens(opener, previous, entry)
        )
        if new:
            paragraphs.append([[]])
            opener = entry
        paragraphs[-1][-1].append(entry.line.text)
        previous = entry
    return [_join_verses(pieces) for pieces in paragraphs if any(pieces)]


# Diferença de recuo, em pt, que ainda conta como o mesmo recuo de bloco.
BLOCK_INDENT_TOLERANCE = 1.5


def _hanging_item_goes_on(opener: _Entry | None, previous: _Entry | None, entry: _Entry) -> bool:
    """No texto-base do certo/errado, a linha continua o item rotulado aberto (I, II; a), b); •),
    com recuo pendente: o item abre na margem ou num recuo de lista ("• o ponto F ... entre EB e",
    CBM/AL 2017 básicos cargo 1) e as linhas seguintes ficam todas no mesmo recuo, além do rótulo
    (`ITEM_INDENT` a `ODD_INDENT`); a anterior vai até a margem direita e deixa a frase aberta
    (termina em letra, vírgula ou travessão) e a linha começa por letra. Emenda (17) da 0020."""
    if opener is None or previous is None or previous.short:
        return False
    plain = opener.line.plain
    if not (ROMAN_ITEM.match(plain) or plain.startswith("• ")):
        return False
    if previous.page != entry.page or previous.line.column != entry.line.column:
        return False
    if opener.page != entry.page or opener.line.column != entry.line.column:
        return False
    hang = entry.line.x0 - opener.line.x0
    if not ITEM_INDENT < hang <= ODD_INDENT:
        return False
    if previous is not opener and abs(entry.line.x0 - previous.line.x0) > BLOCK_INDENT_TOLERANCE:
        return False
    last = previous.line.plain.rstrip()[-1:]
    first = entry.line.plain.lstrip()[:1]
    if last.isalpha() and first.isdigit():
        # A frase partida antes de um número ("... relativos ao mês de abril de" | "2012, no valor
        # de R$ 1.800,00;", PF 2012 agente, item II do texto dos itens 83 e 84). Emenda (18) da 0020.
        return True
    return (last.isalpha() or last in BLOCK_LINE_BREAKS) and (first.isalpha() or first in DASHES)


def _labeled_item_at_margin(entry: _Entry) -> bool:
    """Começo de item enumerado na margem (I, II; a), b); •)."""
    return _at_margin(entry) and (
        ROMAN_ITEM.match(entry.line.plain) is not None or entry.line.plain.startswith("• ")
    )


def _indented_block_goes_on(previous: _Entry, entry: _Entry) -> bool:
    """A linha continua a anterior dentro de um bloco recuado inteiro — as duas com o mesmo recuo
    (além do de parágrafo), ou a anterior é o começo de um item (I, II; a), b); •) na margem e esta
    tem o recuo pendente —, a anterior indo até a margem direita e a frase partida no meio — a
    anterior termina em palavra, vírgula ou travessão e a seguinte começa por letra ou travessão. Sem isso, cada
    linha da citação vira um parágrafo: PC/RJ 2021, questão 39, incisos II e IX do art. 7.º da Lei
    n.º 8.137/1990; itens I, II, III com recuo pendente (PC/MA 2017, PC/GO 2016). Linha de tabela
    ou de equação termina em número ou parêntese e continua separada (PC/RO 2022 específicos,
    questão 57; PC/PB 2021 cargo 12, questão 80; CBM/TO 2021 oficial, questão 32)."""
    if previous.page != entry.page or previous.line.column != entry.line.column or previous.short:
        return False
    offset = previous.line.x0 - previous.left
    indent = entry.line.x0 - entry.left
    if offset > PARAGRAPH_INDENT:
        if abs(indent - offset) > BLOCK_INDENT_TOLERANCE:
            return False
    elif not _labeled_item_at_margin(previous):
        # Recuo pendente: a primeira linha do item ("III São objetivos...") fica na margem e as
        # seguintes, recuadas além do recuo de parágrafo.
        return False
    elif indent > ODD_INDENT:
        return False
    last = previous.line.plain.rstrip()[-1:]
    first = entry.line.plain.lstrip()[:1]
    if last in CLOSING_QUOTES:
        # Trecho citado e, na linha seguinte, a localização dele ("III “a cultura da violência
        # que nos desumaniza a todos”" | "(décimo segundo período).", PC/PB 2021 gerais 14 a 17,
        # questão 5): a aspa fecha a citação, não o item.
        return first == "(" or first.islower()
    return (last.isalpha() or last in BLOCK_LINE_BREAKS) and (
        first.isalpha() or first in '“"(' or first in DASHES
    )


# Aspa de fechamento no fim da linha: o item segue se a linha seguinte abre parêntese ou minúscula.
CLOSING_QUOTES = ("”", '"')
# Fim de linha que deixa a frase aberta dentro de um bloco recuado.
BLOCK_LINE_BREAKS = (",", "-", "–", "—")
# Começo de linha que continua a frase: o travessão do aposto ("...especializadas" | "— polícias
# civis e militares —, enquanto...", PC/MA 2017 investigador, questões 26 e 47).
DASHES = ("—", "–")


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
    text = _spaced_refs(" ".join([question.statement_md, *(o.body_md for o in question.options)]))
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
    text = _spaced_refs(" ".join([question.statement_md, *(o.body_md for o in question.options)]))
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
    uma figura que não foi extraída; texto-base que é só o título também. Itens que são períodos
    consecutivos de um parágrafo: cada um depende dos outros itens, que não ficam no texto-base."""
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
            # só o título ("**Figura 1A5-I**", PM/TO 2020 QPE): o conteúdo era imagem
            or TITLE_LINE.match(body.replace("*", "").strip())
        ):
            question.flags = sorted({*question.flags, "figure"})


def _bold_heading(entries: list[_Entry]) -> bool:
    """Título de bloco em negrito ("**Atualidades e conhecimentos...**"), em caixa alta ou em
    corpo de título, sem pontuação final ("Normas relativas ao CBMTO", CBM/TO 2021 oficial, antes
    da questão 36): não é texto-base. Linha que é o título de um texto-base ("**Figura 1A03**",
    CBM/PA 2023 CFP, antes da questão 36) não é título de bloco, mesmo em negrito."""
    if any(TITLE_LINE.match(e.line.plain.strip()) for e in entries):
        return False
    if len(entries) == 2 and _section_title(entries[0].line.plain):
        # título em caixa alta quebrado em duas linhas ("NOÇÕES DE DIREITO PROCESSUAL PENAL" /
        # "COMUM", PM/SC 2023 soldado, antes da questão 17)
        tail = entries[1].line.plain.strip()
        if tail.isupper() and len(tail.split()) <= 3 and not tail.endswith((".", ":", "?", ",")):
            return True
    return len(entries) <= 2 and all(
        (e.line.text.strip().startswith("**") and e.line.text.strip().endswith("**"))
        or _section_title(e.line.plain)
        or (
            (e.line.size or 0) >= HEADING_MIN_SIZE
            and not e.line.plain.rstrip().endswith((".", ":", "?", ",", ";"))
        )
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
    if (
        "figure" in last.flags
        and entry.line.size < CITATION_SIZE
        and FIGURE_SOURCE.match(entry.line.plain)
    ):
        # "Fonte: IBGE" em letra miúda logo abaixo da figura do item é o crédito dela, não a
        # abertura do grupo seguinte (CBM/AL 2017 específicos cargo 1, item 93).
        return True
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
    if moved and sentence_done and entry.below_figure and entry.line.plain[:1].isupper():
        # Coluna nova que abre com figura e, abaixo dela, frase com maiúscula depois do item
        # terminado: é o texto-base do grupo seguinte ("Na figura precedente, o retângulo ABCD
        # tem as seguintes" | "propriedades:", CBM/AL 2017 básicos cargo 1, depois do item 40),
        # mesmo com o recuo de parágrafo igual ao de continuação (decisão 0020, emenda (16)).
        return False
    if sentence_done and (entry.after_gap or title):
        return False  # "Espaço livre" ou título em negrito encerram o item
    starts_paragraph = abs(indent - PARAGRAPH_INDENT_AT) < 4 and entry.line.plain[:1].isupper()
    if starts_paragraph and (previous.endswith((".", "?", "!", ":")) or bare_number):
        return False
    if ITEM_PROPOSITION.match(entry.line.plain) and any(
        ITEM_PROPOSITION.match(e.line.plain)
        and e.page == entry.page
        and e.line.column == entry.line.column
        and abs(e.line.x0 - entry.line.x0) <= LABEL_ALIGN
        for e in item.entries[1:]
    ):
        # Proposição rotulada alinhada com outra do mesmo item: a lista continua ("P: ..." |
        # "Q: ...", CBM/AL 2017 básicos cargo 1, item 48), mesmo com o recuo e a frase fechada
        # que abririam o texto-base seguinte (decisão 0020, emenda (15)).
        return True
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
                justification_color=justification_color is not None
                and line.color == justification_color,
            )
            # Texto branco sem fundo desenhado é invisível: não está na página impressa (PC/SE
            # 2018: "Texto" em 5 pt acima de cada texto-base). Sai depois de as figuras serem
            # atribuídas, para não mudar a que linha cada figura se liga.
            entry.invisible = line.color == WHITE and not any(
                _behind(figure, line) for figure in page.figures
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
        stream.extend(_visible(_with_figures(page, entries, skipped, start_y)))
    return stream


def _visible(entries: list[_Entry]) -> list[_Entry]:
    """Tira as linhas invisíveis; as marcas que receberam (a figura logo abaixo) passam à linha
    seguinte da mesma coluna, ou à anterior quando não há seguinte."""
    kept: list[_Entry] = []
    for index, entry in enumerate(entries):
        if not entry.invisible:
            kept.append(entry)
            continue
        if not entry.flags:
            continue
        column = entry.line.column
        after = [e for e in entries[index + 1 :] if not e.invisible and e.line.column == column]
        before = [e for e in kept if e.line.column == column]
        heir = after[0] if after else before[-1] if before else None
        if heir is not None:
            heir.flags |= entry.flags
    return kept


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
HEADING_MIN_SIZE = 13.5  # título de bloco em corpo de título (o texto corre em 10–11)


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
    estado" / "do Tocantins", CBM/TO 2021), ou de um título de disciplina em negrito quebrado em
    duas linhas, a segunda também só em negrito ("DIREITO TRIBUTÁRIO E DIREITO" / "EMPRESARIAL",
    PC/MA 2017 delegado, antes da questão 16; sem isso a segunda linha grudava na alternativa E
    da questão 15): em corpo maior, mesma coluna, mesmo corpo, logo abaixo, curta.

    No corpo do texto, só o título de disciplina em caixa alta e negrito cuja segunda linha também
    é caixa alta e só negrito, sem número ("NOÇÕES DE DIREITO PROCESSUAL PENAL" / "COMUM", PM/SC
    2023 soldado, antes da questão 17: com o estilo ligado, a primeira linha sai como título e a
    segunda grudava na alternativa E da questão 16); a linha de baixo de outro título no corpo do
    texto é rótulo ("Texto 1A1-I")."""
    subject = _subject_heading(heading) and _bold_only(heading) and _bold_only(line)
    if (heading.size or 0) < KNOWLEDGE_TITLE_MIN_SIZE:
        plain = line.plain.strip()
        if not (
            subject
            and heading.plain.strip().isupper()
            and plain.isupper()
            and not any(ch.isdigit() for ch in plain)
            and len(plain.split()) <= 3
        ):
            return False
    knowledge = KNOWLEDGE_TITLE.match(heading.plain.strip()) is not None
    return (
        (knowledge or subject)
        and line.column == heading.column
        and abs((line.size or 0) - (heading.size or 0)) < 0.5
        and 0 < line.y0 - heading.y1 < (heading.size or 0)
        and len(line.plain.split()) <= 4
        and not line.plain.rstrip().endswith((".", ":", "?", ","))
    )


def _bold_only(line: Line) -> bool:
    text = line.text.strip()
    return text.startswith("**") and text.endswith("**") and "**" not in text[2:-2]


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
            or _heading_rule(figure, skipped)
        ):
            continue  # faixa de fundo de título ("BLOCO II", "Questão 7") ou régua de cabeçalho
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
            _mark_figure(first_below, figure)
        elif above:
            _mark_figure(max(above, key=lambda e: e.line.y0), figure)
        elif below:
            first = min(below, key=lambda e: e.line.y0)
            first.below_figure = True
            _mark_figure(first, figure)
    return entries


HEADING_RULE_GAP = 6.0  # pt entre a régua e a linha do cabeçalho de disciplina


def _heading_rule(figure: Figure, skipped: list[Line]) -> bool:
    """Filete desenhado logo acima ou logo abaixo de uma linha ignorada (cabeçalho de disciplina
    "MATEMÁTICA" entre duas réguas, CBM/RO 2022 oficial, página 3): é moldura do cabeçalho, não
    figura da questão de cima. Só traço fino (até 3 pt de altura) que cruza a linha na horizontal."""
    if figure.kind != "drawing" or figure.y1 - figure.y0 > 3:
        return False
    return any(
        figure.x0 < line.x1
        and figure.x1 > line.x0
        and (
            0 <= line.y0 - figure.y1 <= HEADING_RULE_GAP
            or 0 <= figure.y0 - line.y1 <= HEADING_RULE_GAP
        )
        for line in skipped
    )


def _mark_figure(entry: _Entry, figure: Figure) -> None:
    """Marca a linha vizinha da figura. No título "Questão N", só a imagem (fotografia, mapa, o
    ícone de um botão) é da questão; os desenhos ali são a moldura do título ou a régua do
    cabeçalho de disciplina (PC/GO 2016, PC/PE 2023) e seguem ignorados. A marca do título passa à
    questão em `_segment_choice` (decisão 0030, emenda de 2026-10-14)."""
    if figure.kind == "image" or not QUESTION_TITLE.match(entry.line.plain):
        entry.flags.add("figure")


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


def _behind(figure: Figure, line: Line) -> bool:
    """Figura que cruza a caixa da linha: o fundo sobre o qual um texto branco fica visível."""
    return (
        figure.x0 <= line.x1
        and line.x0 <= figure.x1
        and figure.y0 <= line.y1
        and line.y0 <= figure.y1
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
        (
            ref
            for ref in TEXT_REF.findall(_spaced_refs(" ".join([*situation, command])))
            if ref in passages
        ),
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
    code_breaks = _code_line_breaks(text_lines)
    paragraphs: list[list[list[str]]] = [[[]]]
    for index, text in enumerate(text_lines):
        if index in code_breaks and paragraphs[-1] != [[]]:
            paragraphs.append([[]])
        paragraphs[-1][-1].append(text)
        if index in breaks:
            paragraphs[-1].append([])
    # Vocativo e fecho de correspondência ficam na própria linha ("Senhor Delegado," |
    # "Atenciosamente," | "José da Silva"): quebra de linha do Markdown (docs/content-format.md).
    # O comando que o item mostra numa linha só em fonte monoespaçada é um parágrafo à parte.
    body = "\n\n".join(
        "\\\n".join(_join(piece) for piece in pieces if piece)
        for pieces in paragraphs
        if any(pieces)
    )
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


CODE_LINE = re.compile(r"^`[^`]+`$|^`` [^`].*[^`] ``$")


def _code_line_breaks(lines: list[str]) -> set[int]:
    """Índices das linhas do item que abrem parágrafo por causa de uma linha só de código: o
    comando que o item mostra à parte ("...pode ser utilizado o comando a seguir." |
    "`head messages.log`", PM/AL 2021 oficial, item 37). Abre parágrafo a linha de código depois de
    frase terminada e a primeira linha de texto que vem depois do código."""
    found: set[int] = set()
    for index, text in enumerate(lines):
        if index == 0 or not CODE_LINE.match(text.strip()):
            continue
        if lines[index - 1].rstrip().endswith(SENTENCE_STOP):
            found.add(index)
            following = index + 1
            while following < len(lines) and CODE_LINE.match(lines[following].strip()):
                following += 1  # código em várias linhas: um bloco só, como antes
            if following < len(lines):
                found.add(following)
    return found


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
    paragraphs: list[list[list[str]]] = []
    previous: _Entry | None = None
    opener: _Entry | None = None  # primeira linha do parágrafo aberto
    leading = _leading(entries)
    verses = _verse_breaks(entries, leading, base)
    for index, entry in enumerate(entries):
        if index - 1 in verses:  # verso seguinte da mesma estrofe: quebra de linha
            paragraphs[-1].append([entry.line.text])
            previous = entry
            continue
        # Item rotulado com recuo pendente ("I Um usuário, após sequestro de seus dados, recebeu a"
        # | "informação de que, ..."; "• o ponto F ... entre EB e" | "EF mede 45º;"): a linha
        # recuada continua o item, como na múltipla escolha (`_indented_block_goes_on`; PM/MA 2017
        # específicos cargo 5, situações I a III; CBM/AL 2017 básicos cargo 1, texto das questões
        # 41 a 44). Só dentro de item rotulado: tabela e título recuados seguem separados. Com
        # numeração de linhas (`base`) a margem é outra, e a regra não vale.
        indented = entry.line.x0 > (base or entry.left) + PARAGRAPH_INDENT and not (
            base is None and previous is not None and _hanging_item_goes_on(opener, previous, entry)
        )
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
            or _credit_closes(entries, index - 1)
            or (not title_goes_on and _block_gap(previous, entry, leading))
            or _labeled_line_opens(opener, previous, entry)
            or _next_list_item(opener, previous, entry)
        )
        if new:
            paragraphs.append([[]])
            opener = entry
        paragraphs[-1][-1].append(entry.line.text)
        previous = entry
    return [_join_verses(pieces) for pieces in paragraphs]


ROMAN_VALUES = {"I": 1, "V": 5, "X": 10}


def _roman(numeral: str) -> int | None:
    """Valor de um numeral romano curto (I a XXXIX); None se não é numeral bem formado."""
    if not numeral or any(ch not in ROMAN_VALUES for ch in numeral):
        return None
    total = 0
    for index, ch in enumerate(numeral):
        value = ROMAN_VALUES[ch]
        following = ROMAN_VALUES[numeral[index + 1]] if index + 1 < len(numeral) else 0
        total += -value if value < following else value
    return total if total > 0 else None


def _list_label(plain: str) -> tuple[str, int] | None:
    """Rótulo de item de lista no começo da linha → (tipo, ordem): "III recebimento" → ("roman",
    3); "b) o ponto" → ("letter", 2)."""
    match = re.match(r"^([IVX]+|[a-e]\))\s+\S", plain)
    if not match:
        return None
    label = match.group(1)
    if label.endswith(")"):
        return "letter", ord(label[0]) - ord("a") + 1
    value = _roman(label)
    return ("roman", value) if value else None


def _next_list_item(opener: _Entry | None, previous: _Entry | None, entry: _Entry) -> bool:
    """A linha abre o item seguinte da lista aberta (I → II, III → IV; a) → b)) na mesma margem do
    item aberto, e a anterior fecha o item (";", "."). Sem isso, item cuja última linha vai até a
    margem direita grudava no seguinte (PF 2012 agente, itens 83 e 84: "III recebimento ...
    3.600,00;" | "IV prestação de serviços ..."). Emenda (18) da 0020."""
    if opener is None or previous is None:
        return False
    opened, label = _list_label(opener.line.plain), _list_label(entry.line.plain)
    if opened is None or label is None or opened[0] != label[0] or label[1] != opened[1] + 1:
        return False
    if abs((entry.line.x0 - entry.left) - (opener.line.x0 - opener.left)) > BLOCK_INDENT_TOLERANCE:
        return False
    return previous.line.plain.rstrip().endswith(SENTENCE_STOP)


# Proposição rotulada no começo da linha ("P1: Existe...", "P3: Ele é...") ou a conclusão do
# argumento ("C: Logo, ..."): abre parágrafo.
PROPOSITION = re.compile(r"^(?:P\d{1,2}|C)\s?:\s")
# Proposição rotulada dentro do item, também sem índice ("P: ..." | "Q: ...", CBM/AL 2017 básicos,
# item 48): só para decidir se a linha continua o item (`_continues`), não abre parágrafo.
ITEM_PROPOSITION = re.compile(r"^(?:[PQRS]\d{0,2}|C)\s?:\s")
LABEL_ALIGN = 2.0  # pt: proposições da mesma lista começam na mesma margem
# Sentença aberta ou função definida no começo da linha ("c(x): a pessoa...", "P(x, y): ...").
DEFINITION = re.compile(
    r"^[A-Za-z]{1,3}\d{0,2}\s?\(\s?[^\s(),]{1,12}(?:,\s?[^\s(),]{1,12})*\s?\)\s?:\s"
)


def _labeled(entry: _Entry) -> bool:
    """A linha começa com rótulo de proposição ou de sentença aberta seguido de dois-pontos."""
    plain = entry.line.plain
    return bool(PROPOSITION.match(plain) or DEFINITION.match(plain))


def _labeled_line_opens(opener: _Entry | None, previous: _Entry | None, entry: _Entry) -> bool:
    """Linha com rótulo ("P1: ...", "c(x): ...") abre parágrafo quando a anterior fecha a frase ou
    quando o parágrafo aberto também começa com rótulo: as definições em linhas seguidas são uma
    lista, mesmo que a anterior não termine em ponto nem seja curta (PM/SC 2023 soldado, texto
    1A7-I: "c(x): a pessoa confunde..." | "l(x): ..." | "w(x): ..."; PC/PE 2023 P2 cargo 1,
    situação 1A3-II: "P1: “...”" | "P2: ..." | "C: “Logo, ...”", que terminam em aspas)."""
    if previous is None or not _labeled(entry):
        return False
    if previous.line.plain.rstrip().endswith(SENTENCE_STOP):
        return True
    return opener is not None and _labeled(opener)


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


def _block_gap(
    previous: _Entry, entry: _Entry, leading: float | None, command_rule: bool = True
) -> bool:
    """Espaço vertical entre as duas linhas bem maior que o entrelinha do trecho: o original
    separa ali dois blocos, mesmo que a linha anterior vá até a margem e a seguinte não tenha
    recuo (PF 2012 escrivão, item 57: introdução | P1 e P2 | "Diante dessa situação..." | P3 e P4).
    Linha com índice ou expoente tem a caixa mais alta e não conta; frase que segue de uma linha à
    outra também não (fórmula ou figura no meio da linha empurra a seguinte: PF 2012
    papiloscopista, item 109).

    `command_rule`: no certo/errado, o corte antes do comando ("julgue") é de `_split_command`.
    Na múltipla escolha não há esse corte, e o espaço vale também ali (`_choice_paragraphs`); o
    "julgar" de uma alternativa ou de um item romano não é comando."""
    if leading is None or previous.line.scripts or entry.line.scripts:
        return False
    if not previous.line.plain.rstrip().endswith(SENTENCE_STOP) or entry.line.plain[:1].islower():
        return False
    if command_rule and (COMMAND.search(entry.line.plain) or COMMAND.search(previous.line.plain)):
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
    if _credit_closes(entries, index - 1) or _paren_credit_end(entries, index - 1):
        return False
    before = entries[index - 2] if index >= 2 else None
    if _credit_right_aligned(previous, entries[index], before):
        return True
    if not _credit_line(previous, size):
        return False
    if _credit_line_wraps(previous, entries[index]):
        return True
    for offset, entry in enumerate(entries[index : index - 1 + CREDIT_MAX_LINES]):
        if not _credit_line(entry, size):
            return False
        if _credit_closes(entries, index + offset):
            return True
        if _paren_credit_end(entries, index + offset):
            return True
    return False


def _credit_closes(entries: list[_Entry], index: int) -> bool:
    """A linha `index` encerra o crédito: casa `CREDIT_END` sozinha ou, com o "(com" no fim da
    linha de cima e o "adaptações)." nesta, junto da anterior, as duas linhas de crédito do mesmo
    corpo ("... Brasília: FUNAG, 2014, p. 23-5 (com" | "adaptações).", CBM/AL 2017 básicos,
    texto CB1A1AAA)."""
    if index < 0:
        return False
    entry = entries[index]
    plain = entry.line.plain.strip()
    if CREDIT_END.search(plain):
        return True
    if index == 0:
        return False
    previous = entries[index - 1]
    size = entry.line.size
    if not (_credit_line(previous, size) and _credit_line(entry, size)):
        return False
    upper = previous.line.plain.strip()
    if CREDIT_END.search(upper):
        return False
    match = CREDIT_END.search(f"{upper} {plain}")
    return match is not None and match.start() < len(upper)


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


# pt: linhas de um crédito alinhado à direita terminam no mesmo x (o ponto final pode sobrar).
CREDIT_RIGHT_ALIGN = 2.0
# Espaço máximo entre as linhas do crédito alinhado à direita, em fração do corpo (PC/PB 2021
# cargos 14 a 17, questão 47: 3,5 pt em 6). As legendas de gráfico do PF 2021 g77, também
# alinhadas à direita, têm 6 pt em 8.
CREDIT_RIGHT_GAP = 0.65


def _credit_right_aligned(previous: _Entry, entry: _Entry, before: _Entry | None = None) -> bool:
    """Referência em letra miúda alinhada à direita, quebrada em linhas coladas e sem fecho
    reconhecível ("Hely Lopes Meirelles. **Direito Administrativo Brasileiro**." | "Editora
    Malheiros. 27.ª ed. São Paulo, 2002. p. 156.", PC/RO 2022 específicos cargo 3, questão 63; a
    referência do texto 1A1-I do PC/PE 2023 P2 cargo 1, cuja primeira linha quase enche a coluna):
    as duas linhas do mesmo corpo miúdo, a de baixo colada (espaço de até 0,65 do corpo), as
    duas terminando no mesmo x e começando em x diferentes, e a de baixo recuada como crédito. A
    linha anterior pode terminar em ponto: a referência tem várias frases. Linhas miúdas que
    começam no mesmo x não contam (`_credit_line_wraps` cuida delas, e as notas soltas ficam
    separadas); espaço maior também não (legendas de gráfico).

    A primeira linha pode começar na margem quando enche a coluna e a de baixo encerra o crédito
    ("Manoel Carlos Mendonça Filho *et al*. ... Internet:" | "\\<corteidh.or.cr> (com
    adaptações).", PM/AL 2021 oficial, texto CB1A1-I), e a linha de cima dela (`before`) é de outro
    corpo: a referência abre ali, depois do texto, e não é a última linha de um texto em letra
    miúda. Sem o fecho, linha miúda na margem seguida de outra recuada pode ser nota ou legenda, e
    fica separada."""
    gap = _vertical_gap(previous, entry)
    size = previous.line.size
    opens = before is not None and before.line.size != size
    return (
        size < CITATION_SIZE
        and entry.line.size == size
        and gap is not None
        and gap <= size * CREDIT_RIGHT_GAP
        and (
            previous.line.x0 > previous.left + PARAGRAPH_INDENT
            or (opens and bool(CREDIT_END.search(entry.line.plain.strip())))
        )
        and entry.line.x0 > entry.left + ODD_INDENT
        and abs(entry.line.x1 - previous.line.x1) <= CREDIT_RIGHT_ALIGN
        and abs(entry.line.x0 - previous.line.x0) > CREDIT_ALIGN
        and not previous.short
    )


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


def _join_verses(pieces: list[list[str]]) -> str:
    """Junta os versos de uma estrofe com quebra de linha (`\\` no fim da linha,
    docs/content-format.md); cada verso junta as suas linhas com `_join`."""
    return "\\\n".join(_join(piece) for piece in pieces if piece)


# Começo de linha que não é verso: item de lista (I, II; a), b); •; travessão; número), rótulo.
NOT_VERSE_START = re.compile(r"^(?:[IVX]+\b|[a-e]\)|•|[–—-]|\d|\(|\[)")
VERSE_OPEN_END = re.compile(r"[^\W\d_]{2},?$")
VERSE_MIN_LINES = 4  # estrofe mais curta que isso não se distingue de linhas curtas soltas
VERSE_MIN_OPEN = 2  # versos que terminam sem fechar a frase (em palavra ou vírgula)


def _verse_open(entry: _Entry) -> bool:
    """A linha acaba sem fechar a frase: em palavra ou vírgula (não em ponto, dois-pontos, ponto e
    vírgula, aspas, parêntese nem número, que é coluna de tabela: PF 2018 agente, g100; nem em letra
    solta, que é linha de tabela-verdade: "F F V", PF 2025 bloco I, g54)."""
    return VERSE_OPEN_END.search(entry.line.plain.rstrip()) is not None


def _verse_link(previous: _Entry, entry: _Entry, leading: float, base: float | None) -> bool:
    """As duas linhas seguem uma à outra no mesmo bloco de linhas alinhadas: mesma página, coluna,
    corpo e margem sem recuo (ou o mesmo meio, recuadas: versos centralizados), sem espaço vertical
    maior que o entrelinha, nenhuma delas título, item de lista, linha com rótulo ou código."""
    gap = _vertical_gap(previous, entry)
    if gap is None or gap > leading + BLOCK_GAP:
        return False
    if abs(entry.line.size - previous.line.size) >= 1 or entry.line.size < CITATION_SIZE:
        return False
    margin = (base or entry.left) + PARAGRAPH_INDENT
    aligned = abs(entry.line.x0 - previous.line.x0) <= BLOCK_INDENT_TOLERANCE
    # Versos centralizados (CBM/AL 2017 soldado específicos, "O Xote das meninas", g114): o meio
    # das linhas coincide, todas recuadas.
    centered = (
        abs(_center(entry) - _center(previous)) <= 2 * BLOCK_INDENT_TOLERANCE
        and min(entry.line.x0, previous.line.x0) > margin
    )
    if not ((aligned and entry.line.x0 <= margin) or centered):
        return False
    for line in (previous, entry):
        if _is_title(line) or _labeled(line) or NOT_VERSE_START.match(line.line.plain):
            return False
        if line.line.text.lstrip().startswith("`"):  # código não é verso (PF 2025 bloco II, g91)
            return False
    return not CREDIT_END.search(previous.line.plain.strip())


def _center(entry: _Entry) -> float:
    return (entry.line.x0 + entry.line.x1) / 2


def _verse_breaks(
    entries: list[_Entry], leading: float | None, base: float | None = None
) -> set[int]:
    """Índices das linhas de verso depois das quais vem quebra de linha, não parágrafo novo
    (PM/AL 2021 soldado, "À procura da infância": uma estrofe de 21 versos, cada um virava um
    parágrafo).

    Estrofe é um bloco de linhas alinhadas, sem espaço vertical maior que o entrelinha
    (`_verse_link`), com pelo menos `VERSE_MIN_LINES` linhas, três linhas curtas no meio e, entre
    elas, pelo menos `VERSE_MIN_OPEN` que acabam sem fechar a frase e não menos que as que fecham.
    Na prosa a linha curta fecha o parágrafo com ponto; no verso ela acaba em palavra ou vírgula.
    Verso longo que vai até a margem continua na linha seguinte (junta com espaço). Estrofe nova
    só com espaço vertical maior (`_block_gap`). Correspondência oficial fica de fora."""
    if leading is None:
        return set()
    if any(LETTER_LINE.match(entry.line.plain.strip()) for entry in entries):
        # Correspondência oficial (vocativo ou fecho, "Senhora gerente,"): o cabeçalho centralizado
        # e o endereçamento têm regra própria, não são estrofe (PC/PB 2021 CG1A1-III).
        return set()
    breaks: set[int] = set()
    start = 0
    for end in range(1, len(entries) + 1):
        if end < len(entries) and _verse_link(entries[end - 1], entries[end], leading, base):
            continue
        run = range(start, end - 1)  # quebras entre as linhas do bloco [start, end)
        shorts = [i for i in run if entries[i].short]
        opened = sum(1 for i in shorts if _verse_open(entries[i]))
        if (
            end - start >= VERSE_MIN_LINES
            and len(shorts) >= 3
            and opened >= VERSE_MIN_OPEN
            and 2 * opened >= len(shorts)
        ):
            breaks.update(shorts)
        start = end
    return breaks


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
        elif (
            (HYPHEN_END.search(text) and HYPHEN_NEXT.match(line))
            or _url_goes_on(text, line)
            or (MONTH_RANGE_END.search(text) and MONTH_RANGE_NEXT.match(line))
        ):
            # hífen do original (decisão 0032), endereço partido (decisão 0030) ou intervalo de
            # meses partido no travessão ("out.–" | "dez./2009", PM/AL 2021 oficial, g14)
            text += line
        else:
            text = f"{text} {line}"
    return _normalize(text)


# Intervalo de meses abreviados partido no travessão ou hífen de fim de linha ("out.–" |
# "dez./2009"): o traço liga os dois meses, sem espaço. Só mês abreviado dos dois lados.
MONTHS = r"(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\."
MONTH_RANGE_END = re.compile(rf"(?<![^\W_]){MONTHS}[–-]$", re.I)
MONTH_RANGE_NEXT = re.compile(rf"{MONTHS}", re.I)


# Endereço da internet ainda aberto no fim da linha ("Internet: https://…/files/"): começa com
# "http(s)://" ou "www." e não foi fechado (">", espaço). O Markdown escapa "_" e "<" ("\\_").
URL_OPEN = re.compile(r"(?:https?://|\bwww\.)[^\s<>]*$")
URL_BREAK = ("/", "-", "_", "=", "&", "?", "#", "%", "~", ".")  # onde o endereço quebra de linha
URL_PIECE = re.compile(r"[/_=?&%]|\.\w")  # o pedaço seguinte tem cara de endereço


def _url_goes_on(text: str, line: str) -> bool:
    """A linha anterior termina dentro de um endereço da internet, num separador ("/", "-", "_",
    ".", "="...), e a seguinte começa com o resto dele: junta sem espaço ("…amazonaws.com/files/" |
    "ferrovia\\_do\\_diabo…", "…wp-content/uploads/" | "2016/11/…", CBM/RO 2022 questões 38 e 40).
    Linha seguinte que começa com palavra comum ("Acesso em…", "(com adaptações).") fica separada."""
    match = URL_OPEN.search(text)
    if match is None or not text.endswith(URL_BREAK):
        return False
    first = line.split(maxsplit=1)[0] if line.strip() else ""
    return (
        bool(first)
        and line[:1] not in (" ", "(", "*")
        and bool(URL_PIECE.search(first.rstrip(".,;:")))
    )


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
