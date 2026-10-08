"""Parser do Cebraspe contra PDFs oficiais em fixtures/ (snapshot JSON, SPECIFICATIONS.md §9)."""

import os
from pathlib import Path

import pytest

from ingest.extract import Figure, Line, Page, extract
from ingest.parsers import cebraspe
from ingest.staging import Segmented

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
EXAM_PDF = FIXTURES / "pdf/cebraspe/pf-2021-agente-p2-3.pdf"
KEY_PDF = FIXTURES / "pdf/cebraspe/pf-2021-agente-gabarito-definitivo.pdf"
SNAPSHOT = FIXTURES / "expected/cebraspe/pf-2021-agente-p2-3.json"


@pytest.fixture(scope="module")
def segmented() -> Segmented:
    return cebraspe.segment(extract(EXAM_PDF))


def test_snapshot(segmented: Segmented) -> None:
    actual = segmented.model_dump_json(indent=1)
    if os.environ.get("UPDATE_SNAPSHOTS"):
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(actual + "\n", encoding="utf-8")
    assert actual + "\n" == SNAPSHOT.read_text(encoding="utf-8")


def test_items_are_numbered_and_linked_to_passages(segmented: Segmented) -> None:
    numbers = [q.number for q in segmented.questions]
    assert numbers == list(range(1, 31))
    assert {q.type for q in segmented.questions} == {"true_false"}
    by_number = {q.number: q for q in segmented.questions}
    assert by_number[1].passage_key == "2A1-I"
    assert by_number[9].passage_key == "2A1-II"
    assert by_number[19].passage_key is None
    assert by_number[25].passage_key == "g25"  # situação hipotética sem rótulo


def test_command_opens_each_statement(segmented: Segmented) -> None:
    first = segmented.questions[0].statement_md
    command, item = first.split("\n\n")
    assert command.startswith("Com referência às ideias e aos aspectos linguísticos do texto 2A1-I")
    assert command.endswith("julgue os itens a seguir.")
    assert item.startswith("Infere-se do texto que a personagem")


def test_passages_keep_paragraphs_and_formatting(segmented: Segmented) -> None:
    passages = {p.key: p for p in segmented.passages}
    text = passages["2A1-I"].body_md
    assert text.startswith("Tinha de deixar aquela casa.")
    assert text.count("\n\n") >= 3  # parágrafos + citação
    assert "**Com vocês, Antônio Maria**" in text
    assert "julgue" not in text  # o comando não vaza para o texto-base
    assert passages["g25"].body_md.startswith("Determinado agente da Polícia Federal")


def test_no_header_or_item_number_leaks(segmented: Segmented) -> None:
    for question in segmented.questions:
        assert "CEBRASPE" not in question.statement_md
        assert "Aplicação: 2021" not in question.statement_md


def test_answer_key() -> None:
    key = cebraspe.parse_answer_key(extract(KEY_PDF))
    assert sorted(key.answers) == list(range(1, 121))
    assert [n for n, mark in key.answers.items() if mark == "X"] == [28, 92, 106, 108, 119]
    assert "".join(key.answers[n] for n in range(1, 11)) == "ECEEECECCE"
    assert "".join(key.answers[n] for n in range(111, 121)) == "ECCEEECCXC"


# --- casos sintéticos: o que deve ir para revisão ---------------------------------------------


def _line(text: str, x0: float, y0: float, x1: float = 290.0, size: float = 10.0) -> Line:
    plain = text.replace("**", "")
    return Line(text=text, plain=plain, x0=x0, y0=y0, x1=x1, y1=y0 + 11, column=1, size=size)


def _page(lines: list[Line], figures: list[Figure] | None = None) -> Page:
    head = Line(
        text="-- PROVA OBJETIVA --",
        plain="-- PROVA OBJETIVA --",
        x0=217,
        y0=10,
        x1=380,
        y1=25,
        column=0,
        size=15,
    )
    return Page(
        number=1,
        width=595,
        height=842,
        has_text=True,
        lines=[head, *lines],
        figures=figures or [],
    )


def test_figure_after_item_text_flags_the_item() -> None:
    page = _page(
        [
            _line("Acerca de planilhas, julgue o item a seguir.", 28, 50),
            _line("**1** Na planilha a seguir, a fórmula da célula B5 soma", 28, 70),
            _line("os valores da coluna B.", 46, 82, x1=150),
            _line("Julgue o próximo item.", 28, 200),
            _line("**2** Texto sem figura.", 28, 220),
        ],
        [Figure(kind="image", x0=46, y0=100, x1=250, y1=180)],
    )
    questions = cebraspe.segment([page]).questions
    assert questions[0].flags == ["figure"]
    assert questions[1].flags == []


def test_official_justifications_are_dropped() -> None:
    """Cadernos "com justificativa" (PCDF 2020): a justificativa vem depois de cada item, às vezes
    grudada na última linha; "ITEM ANULADO." substitui a justificativa dos anulados."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** A penalidade aplicada é incabível, uma vez que não", 28, 70),
            _line("há previsão legal.", 46, 82, x1=120),
            _line("JUSTIFICATIVA - ERRADO. A pena é cabível porquanto o", 46, 94),
            _line("artigo 117 prevê a proibição.", 46, 106, x1=160),
            _line("**2** A punição configura exercício do poder de", 28, 120),
            _line("polícia.JUSTIFICATIVA - ERRADO. Configura poder", 46, 132),
            _line("disciplinar.", 46, 144, x1=100),
            _line("**3** A variância de X é igual a S. ITEM ANULADO.", 28, 160),
            _line("Julgue o próximo item.", 28, 200),
            _line("**4** Texto sem justificativa.", 28, 220),
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert [q.number for q in questions] == [1, 2, 3, 4]
    assert questions[0].statement_md.endswith("uma vez que não há previsão legal.")
    assert questions[1].statement_md.endswith("exercício do poder de polícia.")
    assert questions[2].statement_md.endswith("A variância de X é igual a S.")
    assert questions[3].statement_md == "Julgue o próximo item.\n\nTexto sem justificativa."
    assert not any("JUSTIFICATIVA" in q.statement_md for q in questions)


def test_multiple_choice_questions_with_options_and_shared_text() -> None:
    """Provas de múltipla escolha (PC/CE 2025, PC/RJ 2021): título "Questão N", enunciado,
    alternativas A–E na margem com continuação recuada; texto rotulado entre questões vira
    texto-base; a capa (antes da primeira questão) não."""
    page = _page(
        [
            _line("Nas questões a seguir, marque a única opção correta.", 28, 20),
            _line("Questão 1", 51, 50),
            _line("Nos termos da Constituição, o Conselho de Segurança", 28, 70),
            _line("Pública é órgão com funções", 28, 82, x1=150),
            _line("A deliberativas e fiscalizadoras, e goza de autonomia", 28, 94),
            _line("administrativa.", 42, 106, x1=100),
            _line("B consultivas e deliberativas.", 28, 118, x1=150),
            _line("C consultivas e fiscalizadoras.", 28, 130, x1=150),
            _line("D A e B estão certas.", 28, 142, x1=120),
            _line("E nenhuma das anteriores.", 28, 154, x1=140),
            _line("**Texto 1A1-I**", 28, 180, x1=80),
            _line("A segurança pública é dever do Estado.", 56, 192, x1=200),
            _line("Questão 2", 51, 220),
            _line("Segundo o texto 1A1-I, a segurança pública", 28, 240, x1=200),
            _line("A é dever do Estado.", 28, 252, x1=120),
            _line("B é dever da família.", 28, 264, x1=120),
            _line("C é facultativa.", 28, 276, x1=100),
            _line("D não existe.", 28, 288, x1=100),
            _line("E é um mito.", 28, 300, x1=100),
        ]
    )
    segmented = cebraspe.segment([page])
    first, second = segmented.questions
    assert (first.number, first.type, first.passage_key) == (1, "multiple_choice", None)
    assert first.statement_md == (
        "Nos termos da Constituição, o Conselho de Segurança Pública é órgão com funções"
    )
    assert [o.letter for o in first.options] == ["A", "B", "C", "D", "E"]
    assert (
        first.options[0].body_md
        == "deliberativas e fiscalizadoras, e goza de autonomia administrativa."
    )
    assert first.options[3].body_md == "A e B estão certas."
    assert first.flags == []  # a capa não é texto-base nem contamina a questão
    assert second.passage_key == "1A1-I"
    assert [p.key for p in segmented.passages] == ["1A1-I"]
    assert second.options[0].body_md == "é dever do Estado."


def _choice(number: int, statement: str, y: float) -> list[Line]:
    return [
        _line(f"Questão {number}", 51, y),
        _line(statement, 28, y + 12, x1=200),
        *(
            _line(f"{letter} opção {letter}.", 28, y + 24 + 12 * i, x1=100)
            for i, letter in enumerate("ABCDE")
        ),
    ]


def test_choice_passage_only_for_the_first_question_or_who_cites_it() -> None:
    """Múltipla escolha: o texto-base vale para a primeira questão depois dele e para as que o
    citam (pelo rótulo ou pelo título "Figura 5A2"); as outras não o herdam. A tabela de
    justificativas (PC/PE 2023) não vira texto-base, e título de bloco em negrito também não."""
    lines = [
        *_choice(1, "Primeira questão sem texto.", 20),
        _line("||JUSTIFICATIVAS||", 28, 100, x1=120),
        _line("||A|| - 1 Constituição. CORRETA porque sim.", 28, 112),
        *_choice(2, "Segunda questão sem texto.", 140),
        _line("**Texto 1A1-I**", 28, 230, x1=80),
        _line("A segurança pública é dever do Estado.", 56, 242, x1=200),
        *_choice(3, "A ideia central do texto é", 260),
        *_choice(4, "Questão de outra matéria.", 350),
        _line("Figura 5A2", 28, 440, x1=80),
        _line("Perfis genéticos de dois indivíduos.", 56, 452, x1=200),
        *_choice(5, "Segundo a figura 5A2, os perfis", 470),
        *_choice(6, "Ainda de acordo com o texto 1A1-I,", 560),
        *_choice(7, "Mais uma questão de outra matéria.", 650),
        _line("**Atualidades**", 28, 740, x1=80),
        *_choice(8, "Questão do bloco de atualidades.", 760),
    ]
    segmented = cebraspe.segment([_page(lines)])
    keys = {q.number: q.passage_key for q in segmented.questions}
    assert keys == {1: None, 2: None, 3: "1A1-I", 4: None, 5: "g5", 6: "1A1-I", 7: None, 8: None}
    assert [p.key for p in segmented.passages] == ["1A1-I", "g5"]


def test_choice_labels_bullets_and_unresolved_references() -> None:
    """Rótulo de texto um pouco fora da margem encerra a última alternativa; "Proposição X" é
    rótulo; "C" como marcador de lista no enunciado vira "•"; remissão não resolvida e figura da
    própria questão viram motivo de revisão."""
    lines = [
        *_choice(1, "Primeira questão.", 20),
        _line("Texto 1A7-I", 35, 100, x1=90),
        _line("Considere o conjunto V.", 56, 112, x1=200),
        *_choice(2, "A partir do texto 1A7-I, assinale.", 130),
        _line("Proposição CG1A5AAA", 28, 210, x1=120),
        _line("A educação sobe ou a violência cai.", 56, 222, x1=200),
        *_choice(3, "A tabela-verdade da proposição CG1A5AAA tem", 240),
        *_choice(4, "Questão de outra matéria.", 320),
        *_choice(5, "A negação da proposição CG1A5AAA é", 400),
        _line("Questão 6", 51, 480),
        _line("Nas eleições de 2016,", 28, 492, x1=200),
        _line("C Fernanda foi candidata;", 28, 504, x1=200),
        _line("C Paulo foi mesário.", 28, 516, x1=200),
        *(
            _line(f"{letter} opção {letter}.", 28, 528 + 12 * i, x1=100)
            for i, letter in enumerate("ABCDE")
        ),
        *_choice(7, "Considerando o conteúdo do expediente, assinale.", 600),
        *_choice(8, "Com base no texto 9Z9-I, assinale.", 680),
        *_choice(9, "A figura precedente mostra um pórtico.", 760),
    ]
    questions = {q.number: q for q in cebraspe.segment([_page(lines)]).questions}
    assert questions[1].options[-1].body_md == "opção E."
    assert [questions[n].passage_key for n in (2, 3, 4, 5)] == ["1A7-I", "g3", None, "g3"]
    assert (
        questions[6].statement_md
        == "Nas eleições de 2016,\n\n• Fernanda foi candidata;\n\n• Paulo foi mesário."
    )
    assert [o.letter for o in questions[6].options] == ["A", "B", "C", "D", "E"]
    assert "missing_passage" in questions[7].flags and "missing_passage" in questions[8].flags
    assert "figure" in questions[9].flags
    assert not {"missing_passage", "figure"} & {*questions[2].flags, *questions[5].flags}


def test_choice_text_after_justification_and_section_title() -> None:
    """PC/PE 2023: texto-base logo depois da tabela de justificativas abre o grupo seguinte.
    PC/RO 2022: título de disciplina em caixa alta não gruda na alternativa E."""
    lines = [
        *_choice(1, "Primeira questão.", 20),
        _line("||JUSTIFICATIVAS||", 28, 100, x1=120),
        _line("||A|| - 1 Lei. INCORRETA.", 28, 112),
        _line("Situação hipotética 1A3-I", 28, 130, x1=150),
        _line("Foram investigados 90 casos.", 56, 142, x1=200),
        *_choice(2, "Quantos casos foram investigados?", 160),
        *_choice(3, "Na situação hipotética 1A3-I, os roubos", 250),
        _line("DIREITO FINANCEIRO E TRIBUTÁRIO", 120, 340, x1=250),
        *_choice(4, "Questão de direito financeiro.", 360),
    ]
    segmented = cebraspe.segment([_page(lines)])
    questions = {q.number: q for q in segmented.questions}
    assert questions[1].options[-1].body_md == "opção E."
    assert [questions[n].passage_key for n in (2, 3, 4)] == ["g2", "g2", None]
    assert questions[3].options[-1].body_md == "opção E."
    assert [p.key for p in segmented.passages] == ["g2"]


def test_code_lines_flag_layout() -> None:
    page = _page(
        [
            _line("Julgue o item seguinte.", 28, 50),
            _line("**1** O código Python a seguir imprime True.", 28, 70),
            _line("x = bool(-3)", 46, 82, x1=110),
            _line("print(x)", 46, 94, x1=90),
        ]
    )
    assert cebraspe.segment([page]).questions[0].flags == ["layout"]


def test_broken_math_glyphs_flag_formula() -> None:
    page = _page(
        [
            _line("Julgue o item seguinte.", 28, 50),
            _line("**1** 𝑃ሺ𝑋ൌ5ሻ൐ 𝛾.", 28, 70),
        ]
    )
    assert "formula" in cebraspe.segment([page]).questions[0].flags


def test_out_of_sequence_number_is_not_an_item() -> None:
    page = _page(
        [
            _line("Julgue o item seguinte.", 28, 50),
            _line("**1** Em 2020, foram registradas", 28, 70),
            _line("5 ocorrências no total.", 28, 82),  # "5" na margem, mas o esperado é 2
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert [q.number for q in questions] == [1]
    assert questions[0].flags == ["orphan_text"]  # a linha não some em silêncio


def test_free_space_and_bold_title_end_the_item() -> None:
    page = _page(
        [
            _line("Julgue o item seguinte.", 28, 50),
            _line("**1** O ciclo de Krebs ocorre nos ribossomos.", 28, 70),
            _line("Espaço livre", 300, 90),
            _line("**Título do texto seguinte**", 42, 110),  # recuo dentro da faixa de continuação
            _line("Corpo do texto.", 57, 130),
            _line("Com base no texto, julgue o item.", 28, 150),
            _line("**2** Item do texto.", 28, 170),
        ]
    )
    segmented = cebraspe.segment([page])
    first, second = segmented.questions
    assert first.statement_md.endswith("ribossomos.")
    passage = next(p for p in segmented.passages if p.key == second.passage_key)
    assert passage.body_md.startswith("**Título do texto seguinte**")


def test_pf_2018_line_numbered_passage_without_marker() -> None:
    """PF 2018: sem "PROVA OBJETIVA" com tracinhos, texto com numeração de linhas na margem."""
    segmented = cebraspe.segment(extract(FIXTURES / "pdf/cebraspe/pf-2018-agente-p1.pdf"))
    assert [q.number for q in segmented.questions] == list(range(1, 12))
    body = segmented.passages[0].body_md
    assert body.startswith("Imagine uma operação de busca na selva.")
    assert "facão. Assim eram feitas" in body  # número de linha "4" removido no meio do texto
    assert body.count("\n\n") == 7  # parágrafo que começa no número de linha "7" não se funde
    assert segmented.questions[0].statement_md.endswith(
        "Infere-se do texto que o Nudetective foi desenvolvido especificamente para o combate à"
        " pornografia infantil."
    )


def test_item_completing_an_unfinished_opening() -> None:
    page = _page(
        [
            _line("Considere que W tenha média 10 e desvio padrão 4.", 28, 50),
            _line("Nessa situação hipotética,", 28, 62, x1=140),
            _line("1 se W1 e W2 forem independentes, a soma terá média 20.", 28, 74),
            _line("2 P(W > 10) = 0,5.", 28, 86, x1=150),
        ]
    )
    segmented = cebraspe.segment([page])
    first, second = segmented.questions
    assert first.statement_md == (
        "Nessa situação hipotética, se W1 e W2 forem independentes, a soma terá média 20."
    )
    assert second.statement_md == "Nessa situação hipotética, P(W > 10) = 0,5."
    assert first.passage_key == "g1"
    assert "no_command" not in first.flags


def test_segment_can_start_after_one_and_accepts_figure_only_items() -> None:
    page = _page(
        [
            _line("Com base nas figuras, julgue os itens.", 28, 50),
            _line("**9**", 28, 70, x1=40),  # item que é só figura
            _line("**10** Texto do item.", 28, 160),
        ]
    )
    questions = cebraspe.segment([page], first=9).questions
    assert [q.number for q in questions] == [9, 10]
    assert "empty_item" in questions[0].flags


def test_items_before_first_do_not_leak_into_the_first_passage() -> None:
    """PC/AL 2021: o PDF traz os itens 1–50 (básicos) antes da prova, que começa no 51. O texto
    desses itens, inclusive a continuação do último, não vira texto-base do primeiro grupo."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** Item básico um.", 28, 70),
            _line("**2** Item básico dois, que continua", 28, 90),
            _line("na linha seguinte.", 46, 102, x1=150),
            _line("Determinado órgão público publicou edital.", 57, 130),
            _line("A partir dessa situação hipotética, julgue os itens.", 28, 150),
            _line("**3** Item da prova.", 28, 170),
        ]
    )
    segmented = cebraspe.segment([page], first=3)
    (question,) = segmented.questions
    passage = next(p for p in segmented.passages if p.key == question.passage_key)
    assert passage.body_md == "Determinado órgão público publicou edital."


def test_command_split_across_columns_is_rejoined() -> None:
    """PM/AL 2018: o comando começa no fim do texto ("...aos sentidos do") e continua na outra
    coluna ("texto 1A1-I, julgue"); a frase inacabada volta para o comando."""
    page = _page(
        [
            _line("Texto 1A1-I", 28, 40, x1=90),
            _line("A violência cresce nas cidades.", 57, 52),
            _line("No que concerne aos aspectos linguísticos do", 28, 64),
            _line("texto 1A1-I, julgue os itens a seguir.", 28, 76),
            _line("**1** O texto é narrativo.", 28, 96),
        ]
    )
    segmented = cebraspe.segment([page])
    (question,) = segmented.questions
    assert question.statement_md.startswith(
        "No que concerne aos aspectos linguísticos do texto 1A1-I"
    )
    assert segmented.passages[0].body_md == "A violência cresce nas cidades."


def test_command_split_before_the_label_is_rejoined() -> None:
    """PF 2018 (escrivão): o comando começa no fim do texto e a outra coluna começa no rótulo
    ("13A1AAA, julgue"), não em minúscula; a frase inacabada volta para o comando."""
    segmented = cebraspe.segment(extract(FIXTURES / "pdf/cebraspe/pf-2018-escrivao-p1-2.pdf"))
    question = next(q for q in segmented.questions if q.number == 15)
    assert question.passage_key == "13A1AAA"
    assert question.statement_md.startswith(
        "Com relação aos aspectos linguísticos e aos sentidos do texto 13A1AAA, julgue"
    )
    passage = next(p for p in segmented.passages if p.key == "13A1AAA")
    assert passage.body_md.endswith("(com adaptações).")


def test_consecutive_period_items_go_to_review() -> None:
    """PF 2018 (papiloscopista): os itens 6–11 são os períodos consecutivos de um parágrafo;
    isolado, o item 8 ("Nessas situações...") não se julga. Os itens 1–5 seguem publicáveis."""
    segmented = cebraspe.segment(extract(FIXTURES / "pdf/cebraspe/pf-2018-papiloscopista-p1.pdf"))
    flagged = [q.number for q in segmented.questions if "consecutive_items" in q.flags]
    assert flagged == list(range(6, 12))


def _title_line(plain: str, y0: float, size: float, column: int = 2) -> Line:
    return Line(
        text=plain, plain=plain, x0=316, y0=y0, x1=555, y1=y0 + size, column=column, size=size
    )


def test_large_knowledge_title_is_a_heading_with_its_second_line() -> None:
    # CBM/TO 2022 (12 pt) e 2021 (15 pt, em duas linhas) contra 10 pt do texto: o título no alto
    # da coluna grudava na última alternativa da questão anterior.
    one_line = _title_line("Conhecimentos acerca do Estado do Tocantins", 48, 12)
    assert cebraspe._subject_heading(one_line)
    first = _title_line("Conhecimentos acerca do estado", 51, 15)
    second = _title_line("do Tocantins", 68, 15)
    assert cebraspe._subject_heading(first)
    assert cebraspe._heading_continuation(first, second)
    # Texto comum no corpo da prova não é título, nem a linha seguinte a ele.
    body = _title_line("Conhecimentos de informática são exigidos", 48, 10)
    assert not cebraspe._subject_heading(body)
    assert not cebraspe._heading_continuation(body, _title_line("no edital", 59, 10))
    assert not cebraspe._subject_heading(_title_line("Conhecimentos gerais.", 48, 12))


def test_source_credit_closes_its_paragraph() -> None:
    """PM/TO 2020 q23: o comando vinha colado ao crédito do texto ("... (com adaptações). O
    texto precedente refere-se ...")."""

    def entry(text: str, y: float, x0: float = 30.0) -> cebraspe._Entry:
        line = Line(text=text, plain=text, x0=x0, y0=y, x1=290, y1=y + 9, column=1, size=8.0)
        return cebraspe._Entry(1, line, left=30.0)

    entries = [
        entry("A Revolta de 1835 marcou o século XIX.", 100),
        entry("Internet: <dominiopublico.gov.br> (com adaptações).", 112, x0=150),
        entry("O texto precedente refere-se ao movimento separatista que", 124),
        entry("eclodiu no norte de Goiás.", 136),
    ]
    expected = [
        "A Revolta de 1835 marcou o século XIX.",
        "Internet: <dominiopublico.gov.br> (com adaptações).",
        "O texto precedente refere-se ao movimento separatista que eclodiu no norte de Goiás.",
    ]
    assert cebraspe._paragraphs(entries) == expected
    # Na múltipla escolha o crédito vem alinhado à direita e vai até a margem: não é "curto".
    assert cebraspe._choice_paragraphs(entries) == expected


def test_scratch_label_is_not_content() -> None:
    """Quadro "RASCUNHO" no alto da coluna vazia (PF 2012): não abre um texto-base para o grupo da
    página seguinte nem entra no item."""
    scratch = _line("RASCUNHO", 320, 40, x1=370)
    scratch.column = 2
    first = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** Primeiro item da página.", 28, 70),
            scratch,
        ]
    )
    second = _page(
        [
            _line("Julgue os itens seguintes, referentes a administração.", 28, 50),
            _line("**2** Item da página seguinte.", 28, 70),
        ]
    )
    second.number = 2
    segmented = cebraspe.segment([first, second])
    assert segmented.passages == []
    assert all("RASCUNHO" not in q.statement_md for q in segmented.questions)


def test_command_starting_mid_sentence_flags_layout() -> None:
    """Corte errado entre texto e comando (lista com recuo deslocado, PF 2012 itens 83 e 84)."""
    page = _page(
        [
            _line("prestados no mês de março, julgue os itens seguintes.", 28, 50),
            _line("**1** Os resultados serão iguais.", 28, 70),
        ]
    )
    assert cebraspe.segment([page]).questions[0].flags == ["layout"]


def test_two_line_credit_is_one_paragraph() -> None:
    """Crédito em letra miúda quebrado em duas linhas (PF 2012 q46, CBM/AL 2017): um parágrafo só,
    com o negrito do título emendado."""
    page = _page(
        [
            _line("Texto 1A1-I", 28, 30),
            _line("Corpo do texto-base com uma frase completa e bem longa.", 28, 50),
            _line(
                "Clóvis Rossi. **Drogas, tema inescapável**. *In*: **Folha de**", 150, 70, size=6.0
            ),
            _line("**S.Paulo**, 12/4/2012, p. A14 (com adaptações).", 150, 78, size=6.0),
            _line("Com base no texto 1A1-I, julgue o item a seguir.", 28, 100),
            _line("**1** Item sobre o texto.", 28, 120),
        ]
    )
    body = cebraspe.segment([page]).passages[0].body_md
    assert body.endswith(
        "Clóvis Rossi. **Drogas, tema inescapável**. *In*: **Folha de S.Paulo**, 12/4/2012, p. A14 "
        "(com adaptações)."
    )
