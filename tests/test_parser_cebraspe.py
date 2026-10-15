"""Parser do Cebraspe contra PDFs oficiais em fixtures/ (snapshot JSON, SPECIFICATION.md §9)."""

import os
from pathlib import Path

import pytest

from ingest import extract as extract_module
from ingest.extract import Figure, Line, Page, extract
from ingest.parsers import cebraspe
from ingest.staging import RawQuestion, Segmented

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


def test_command_page_is_where_the_group_opens(segmented: Segmented) -> None:
    """A página do comando vai para a amostra (o item pode estar na página seguinte)."""
    by_number = {q.number: q for q in segmented.questions}
    assert all(q.command_page is not None for q in segmented.questions)
    assert all(q.command_page <= q.page for q in segmented.questions)  # type: ignore[operator]
    # Itens 9–14 na página 2; o texto 2A1-II e o comando deles começam na página 1.
    assert (by_number[9].page, by_number[9].command_page) == (2, 1)
    assert by_number[14].command_page == 1
    assert (by_number[19].page, by_number[19].command_page) == (2, 2)


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


def test_command_citing_figure_not_extracted_flags_every_item() -> None:
    """PF 2018 agente 81–83: o diagrama ER fica entre o item 80 e o comando "Considerando o modelo
    entidade-relacionamento (ER) precedente, julgue..."; sem a figura, os itens do grupo vão para
    revisão, e não só o item de cima (decisão 0030)."""
    page = _page(
        [
            _line("Julgue o próximo item.", 28, 50),
            _line("**1** Item anterior à figura.", 28, 70),
            _line("Considerando o modelo entidade-relacionamento (ER)", 28, 200),
            _line("precedente, julgue os seguintes itens.", 28, 212, x1=200),
            _line("**2** Um produto tem um preço.", 28, 230),
            _line("**3** Um tipo de produto tem um código.", 28, 250),
            _line("Julgue o próximo item.", 28, 280),
            _line("**4** Item sem figura.", 28, 300),
        ],
        [Figure(kind="image", x0=46, y0=100, x1=250, y1=180)],
    )
    questions = cebraspe.segment([page]).questions
    assert [q.number for q in questions] == [1, 2, 3, 4]
    assert "figure" in questions[0].flags  # a linha acima da figura continua marcada
    assert questions[1].flags == ["figure"]
    assert questions[2].flags == ["figure"]
    assert questions[3].flags == []


@pytest.mark.parametrize(
    ("statement", "flag"),
    [
        (
            "Considerando o diagrama e a situação hipotética apresentados, julgue.\n\nItem.",
            "figure",
        ),
        (
            "Considerando o modelo entidade-relacionamento (ER) precedente, julgue.\n\nItem.",
            "figure",
        ),
        (
            "Em um computador, cuja estrutura geral é mostrada anteriormente, o registrador",
            "figure",
        ),
        ("O tipo de virtualização antes ilustrado é conhecido como", "figure"),
        ("Considerando o quadro a seguir, julgue os itens.\n\nItem.", "figure"),
        (
            "Considerando que os dados acima correspondem ao balanço, julgue.\n\nItem.",
            "missing_passage",
        ),
        ("Julgue os itens subsequentes, relativos ao direito penal.\n\nItem.", None),
        ("Com referência ao caso clínico, o quadro apresentado e a gravidade desse quadro", None),
        ("Segundo o modelo apresentado, após dez anos, o número de acidentes será", None),
        ("Considere a equação química mostrada a seguir, que é", None),
    ],
)
def test_reference_to_figure_or_to_something_before_the_command(
    statement: str, flag: str | None
) -> None:
    question = RawQuestion(
        number=1,
        type="true_false" if "\n\n" in statement else "multiple_choice",
        statement_md=statement,
        options=[],
        passage_key=None,
        page=1,
        flags=[],
    )
    flags = cebraspe._reference_flags(question, {})
    assert flags == ({flag} if flag else set())


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


BLUE = 0x0000FF


def test_justification_without_prefix_is_found_by_color() -> None:
    """PCDF 2020 item 84: a justificativa (em azul) começa com "ERRADO." sem "JUSTIFICATIVA -";
    a primeira linha do texto-base seguinte, com recuo de parágrafo de 15, grudava no item."""
    blue = {"color": BLUE}
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** O Hyper-V não suporta máquinas virtuais Linux.", 28, 70),
            _line("JUSTIFICATIVA - ERRADO. Suporta, com dispositivos", 46, 82).model_copy(
                update=blue
            ),
            _line("emulados.", 46, 94, x1=100).model_copy(update=blue),
            _line("**2** Caso o programa fosse compatível somente com o", 28, 110),
            _line("Linux, seria impossível executá-lo no Windows 10.", 46, 122, x1=200),
            _line("ERRADO. O Hyper-V dá suporte a dispositivos emulados e", 46, 134).model_copy(
                update=blue
            ),
            _line("específicos para máquinas virtuais Linux.", 46, 146, x1=200).model_copy(
                update=blue
            ),
            _line("[...]”", 46, 158, x1=80).model_copy(update=blue),  # sem letras
            _line("<FimJust>", 46, 170, x1=90).model_copy(update={"color": 0xFFFFFF}),  # PCDF 2026
            _line("Uma agente, a partir do computador de sua casa, necessitava", 43, 300),
            _line("acessar, com segurança, os serviços de PaaS na nuvem.", 28, 312, x1=200),
            _line("Considerando essa situação hipotética, julgue o item a seguir.", 28, 330),
            _line("**3** A VPN cifra o tráfego.", 28, 350),
        ]
    )
    segmented = cebraspe.segment([page])
    questions = segmented.questions
    assert [q.number for q in questions] == [1, 2, 3]
    assert questions[1].statement_md.endswith("seria impossível executá-lo no Windows 10.")
    assert not any("ERRADO" in q.statement_md or "Uma agente" in q.statement_md for q in questions)
    passage = next(p for p in segmented.passages if p.key == questions[2].passage_key)
    assert passage.body_md.startswith("Uma agente, a partir do computador de sua casa, necessitava")


def test_line_color_is_the_color_of_most_letters() -> None:
    """A cor da linha é a da maioria das letras; sem letras, a dos caracteres visíveis."""
    spans = [
        {"text": "Linux. ", "color": 0},
        {"text": "ERRADO. O Hyper-V", "color": BLUE},
    ]
    assert extract_module._main_color(spans) == BLUE
    assert extract_module._main_color([{"text": "[...]”", "color": BLUE}]) == BLUE
    assert (
        extract_module._main_color([{"text": "Texto", "color": 0}, {"text": " ", "color": BLUE}])
        == 0
    )


def test_verdict_in_black_is_item_text() -> None:
    """Sem a cor das justificativas, "CERTO."/"ERRADO." no começo da linha é texto do item."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** No exemplo, a resposta do aluno foi marcada como", 28, 70),
            _line("ERRADO. Essa marcação está correta.", 46, 82, x1=200),
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert questions[0].statement_md.endswith("marcada como ERRADO. Essa marcação está correta.")


def test_paragraph_after_bare_number_item_is_next_passage() -> None:
    """PRF 2018 item 26: item que é só o número (opções em figura); o parágrafo recuado depois
    dele abre o texto-base seguinte, não continua o item."""
    page = _page(
        [
            _line("A partir das figuras, julgue os itens a seguir.", 28, 50),
            _line("**25**", 28, 70, x1=50),
            _line("**26**", 28, 150, x1=50),
            _line("Para avaliar a resposta dos motoristas a uma campanha", 57, 250),
            _line("educativa promovida pela PRF, foi proposta a função f.", 28, 262, x1=250),
            _line("Com referência a essa situação hipotética, julgue o item.", 28, 280),
            _line("**27** Após dez anos haverá menos de 300 acidentes.", 28, 300),
        ]
    )
    segmented = cebraspe.segment([page], first=25)
    questions = segmented.questions
    assert [q.number for q in questions] == [25, 26, 27]
    by_number = {q.number: q for q in questions}
    assert "Para avaliar" not in by_number[26].statement_md
    passage = next(p for p in segmented.passages if p.key == by_number[27].passage_key)
    assert passage.body_md.startswith("Para avaliar a resposta dos motoristas a uma campanha")


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


def test_choice_option_justification_without_header_is_not_a_passage() -> None:
    """Justificativa de alternativa sem o cabeçalho "JUSTIFICATIVAS" depois da alternativa E (PMDF
    2025 P2 q79: passou para a página seguinte) não vira texto-base da questão seguinte; na cor
    das justificativas é pulada até o próximo título de questão."""
    red = 0x993300

    def colored(line: Line) -> Line:
        return line.model_copy(update={"color": red})

    lines = [
        *_choice(1, "Primeira questão.", 20),
        colored(_line("||JUSTIFICATIVAS||", 28, 100, x1=120)),
        colored(_line("||A|| - Correta. Conforme o artigo 1.*/", 28, 112)),
        *_choice(2, "Segunda questão.", 140),
        colored(_line("||A|| - Incorreta. Conforme o artigo 10, alínea a, do CPPM, a", 28, 220)),
        colored(_line("forma descrita na opção é das formas legítimas.*/", 28, 232)),
        colored(_line("||E|| - Correta. O STM pode determinar a instauração.*/", 28, 244)),
        *_choice(3, "Terceira questão.", 270),
    ]
    segmented = cebraspe.segment([_page(lines)])
    assert [q.passage_key for q in segmented.questions] == [None, None, None]
    assert segmented.passages == []
    assert not any("CPPM" in q.statement_md for q in segmented.questions)


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


def test_choice_reference_glued_to_the_label() -> None:
    """PM/SC 2023 soldado q37 e q39: "do texto1A5-I", sem espaço no próprio caderno, cita o texto
    1A5-I como "texto 1A5-I"; o rótulo colado em minúsculas ("texto1a") não é remissão, e o
    enunciado guarda a grafia do caderno."""
    lines = [
        _line("Texto 1A5-I", 28, 20, x1=90),
        _line("Os algoritmos estão em toda parte.", 56, 32, x1=200),
        *_choice(1, "A afirmação que inicia o texto 1A5-I é", 50),
        *_choice(2, "Questão de outra matéria.", 130),
        *_choice(3, "A correção gramatical do texto1A5-I seria mantida", 210),
        *_choice(4, "Questão sobre o texto1a5 de outra matéria.", 290),
        *_choice(5, "Segundo a Figura5A2, assinale.", 370),
    ]
    questions = {q.number: q for q in cebraspe.segment([_page(lines)]).questions}
    keys = [questions[n].passage_key for n in (1, 2, 3, 4, 5)]
    assert keys == ["1A5-I", None, "1A5-I", None, None]
    assert questions[3].statement_md == "A correção gramatical do texto1A5-I seria mantida"
    assert "missing_passage" in questions[5].flags  # rótulo citado sem texto-base


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


def test_choice_unlabeled_text_after_last_option_holds_for_who_takes_it_up() -> None:
    """CBM/RO 2022 (decisão 0013, emenda de 2026-10-14): o texto sem rótulo começa com recuo de
    parágrafo logo depois da alternativa E e não gruda nela; vale para a primeira questão e para
    as seguintes que retomam termos dele, até a primeira que não retoma ou que abre a sua própria
    situação (enunciado com recuo de parágrafo)."""

    def text(lines: list[str], y: float) -> list[Line]:
        return [_line(line, 56 if i == 0 else 28, y + 12 * i) for i, line in enumerate(lines)]

    lines = [
        *_choice(1, "Primeira questão.", 20),
        *text(
            [
                "Para cortar uma árvore de 20 m de altura, duas cordas foram",
                "amarradas na árvore em um ponto P e nos pontos A e B do solo,",
                "formando os triângulos AOB e APB, com o caule perpendicular ao solo.",
            ],
            100,
        ),
        *_choice(2, "A distância entre os pontos P e A é", 140),
        *_choice(3, "A respeito dos triângulos AOB e APB, assinale.", 220),
        *_choice(4, "Considere que o caule tenha caído.", 300),
        _line("Questão 5", 51, 380),
        _line("Um tanque de água com altura de 5 m foi inclinado até", 56, 392),
        _line("um ângulo de 45° com a vertical.", 28, 404, x1=200),
        *(
            _line(f"{letter} opção {letter}.", 28, 416 + 12 * i, x1=100)
            for i, letter in enumerate("ABCDE")
        ),
        *_choice(6, "As cordas amarradas na árvore medem", 480),
        *text(
            [
                "Considere que, em uma central telefônica, tenha sido registrado o",
                "tempo das ligações em segundos, conforme a tabela a seguir, e que",
                "nenhuma das ligações tenha ultrapassado dois minutos de duração.",
            ],
            560,
        ),
        *_choice(7, "Considerando essas informações, a média é", 600),
        *_choice(8, "A mediana do tempo das ligações é", 680),
        *_choice(9, "Questão de outra matéria.", 760),
        *_choice(10, "Das ligações registradas, a moda é", 840),
    ]
    segmented = cebraspe.segment([_page(lines)])
    questions = {q.number: q for q in segmented.questions}
    keys = {n: q.passage_key for n, q in questions.items()}
    assert keys == {
        1: None, 2: "g2", 3: "g2", 4: "g2", 5: None, 6: None,
        7: "g7", 8: "g7", 9: None, 10: None,
    }  # fmt: skip
    assert questions[1].options[-1].body_md == "opção E."
    assert questions[6].options[-1].body_md == "opção E."
    passages = {p.key: p.body_md for p in segmented.passages}
    assert passages["g2"].startswith("Para cortar uma árvore")
    assert passages["g7"].startswith("Considere que, em uma central")


def test_heading_in_title_size_or_split_in_caps_is_not_a_passage() -> None:
    """CBM/TO 2021: "Normas relativas ao CBMTO" em corpo de título; PM/SC 2023: título em caixa
    alta quebrado em duas linhas. Nenhum dos dois é texto-base da questão seguinte."""
    lines = [
        *_choice(1, "Primeira questão.", 20),
        _line("Normas relativas ao CBMTO", 60, 100, size=15),
        *_choice(2, "A idoneidade moral do candidato é comprovada por", 130),
        _line("NOÇÕES DE DIREITO PROCESSUAL PENAL", 60, 210),
        _line("COMUM", 120, 222, x1=160),
        *_choice(3, "Assinale a opção correta acerca do processo penal.", 240),
    ]
    segmented = cebraspe.segment([_page(lines)])
    assert segmented.passages == []
    assert [q.passage_key for q in segmented.questions] == [None, None, None]
    assert segmented.questions[0].options[-1].body_md == "opção E."


def test_bold_figure_title_is_a_passage_and_flags_the_figure() -> None:
    """CBM/PA 2023 CFP (questões 36–40) e PM/TO 2020 QPE (51–57): com o estilo ligado, o título
    "**Figura 1A03**" não é título de bloco; vira o texto-base de quem o cita e, sendo só o título
    (o conteúdo era imagem), manda a questão para revisão."""
    lines = [
        *_choice(1, "Primeira questão.", 20),
        _line("**Figura 1A03**", 28, 100, x1=85),
        *_choice(2, "O elemento A, na tabela periódica da figura 1A03, é um", 130),
    ]
    segmented = cebraspe.segment([_page(lines)])
    assert [(p.key, p.body_md) for p in segmented.passages] == [("g2", "**Figura 1A03**")]
    assert segmented.questions[1].passage_key == "g2"
    assert "figure" in segmented.questions[1].flags
    assert "missing_passage" not in segmented.questions[1].flags


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


def test_second_foreign_language_restarts_the_skipped_items() -> None:
    """CBM/AL 2017: espanhol e inglês trazem os itens 1 a 5 cada antes do item 6 da prova. O bloco
    da segunda língua não vira abertura do primeiro grupo; o "1" do número de linha do texto-base
    seguinte (sem comando antes) não recomeça a contagem."""
    page = _page(
        [
            _line("Basándose en el texto, juzgue los ítems siguientes.", 28, 50),
            _line("1 Ítem uno.", 28, 62),
            _line("2 Ítem dos.", 28, 74),
            _line("LÍNGUA INGLESA", 87, 100, x1=200),
            _line("1 Learning a second language is difficult.", 34, 112),
            _line("Based on the text above, judge the following items.", 28, 130),
            _line("1 Item one.", 28, 142),
            _line("2 Item two, which goes", 28, 154),
            _line("on here.", 47, 166, x1=120),
            _line("Texto CB2A1AAA", 28, 190, x1=110),
            _line("1 O açúcar arrasou o Nordeste.", 34, 202),
            _line("Com relação às ideias do texto CB2A1AAA, julgue os itens.", 28, 220),
            _line("3 Item da prova.", 28, 240),
        ]
    )
    segmented = cebraspe.segment([page], first=3)
    (question,) = segmented.questions
    assert question.statement_md == (
        "Com relação às ideias do texto CB2A1AAA, julgue os itens.\n\nItem da prova."
    )
    passage = next(p for p in segmented.passages if p.key == question.passage_key)
    assert passage.key == "CB2A1AAA"
    assert passage.body_md.endswith("O açúcar arrasou o Nordeste.")
    assert "Learning" not in passage.body_md


def test_figure_source_below_item_figure_stays_with_the_item() -> None:
    """CBM/AL 2017 específicos cargo 1, item 93: "Fonte: IBGE" em letra miúda, à direita, logo
    abaixo do mapa do item, é o crédito do mapa; os itens 94–96 seguem no mesmo comando."""
    page = _page(
        [
            _line("Julgue os próximos itens, acerca do território.", 28, 50),
            _line("93 O mapa a seguir representa Tordesilhas.", 28, 70),
            _line("Fonte: IBGE", 250, 300, x1=285, size=6.0),
            _line("94 Os estados da região Norte são agrários.", 28, 320),
        ],
        figures=[Figure(kind="image", x0=46, y0=90, x1=285, y1=295)],
    )
    first, second = cebraspe.segment([page], first=93).questions
    assert "figure" in first.flags
    assert first.statement_md.endswith("Tordesilhas. Fonte: IBGE")
    assert second.statement_md == (
        "Julgue os próximos itens, acerca do território.\n\nOs estados da região Norte são agrários."
    )
    assert "figure" not in second.flags


def test_invisible_white_text_is_dropped() -> None:
    """PC/SE 2018: "Texto" em branco, 5 pt, sem fundo, acima de cada texto-base: não está na página
    impressa. Texto branco sobre um fundo desenhado fica."""
    hidden = _line("Texto", 28, 40, x1=44, size=5.0).model_copy(update={"color": cebraspe.WHITE})
    boxed = _line("Quadro", 28, 120, x1=80).model_copy(update={"color": cebraspe.WHITE})
    page = _page(
        [
            hidden,
            _line("1 A existência da polícia se justifica.", 29, 52),
            _line("Acerca do texto, julgue os itens a seguir.", 28, 70),
            _line("1 De acordo com o texto, a polícia atua.", 28, 86),
            boxed,
            _line("2 Outro item.", 28, 140),
        ],
        figures=[Figure(kind="drawing", x0=26, y0=118, x1=90, y1=133)],
    )
    segmented = cebraspe.segment([page])
    first, second = segmented.questions
    assert first.statement_md == (
        "Acerca do texto, julgue os itens a seguir.\n\nDe acordo com o texto, a polícia atua."
    )
    passage = next(p for p in segmented.passages if p.key == first.passage_key)
    assert "Texto" not in passage.body_md
    assert "Quadro" in first.statement_md or "Quadro" in second.statement_md


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


def _gap_entry(text: str, y0: float, x0: float = 28.3, short: bool = False) -> cebraspe._Entry:
    """Linha de 11 pt da coluna 1 (PM/DF 2025, P2): `y0` dá o espaço até a linha anterior."""
    line = Line(text=text, plain=text, x0=x0, y0=y0, x1=290, y1=y0 + 11, column=1, size=10.0)
    return cebraspe._Entry(12, line, left=28.3, short=short)


def test_choice_command_after_vertical_space_is_its_own_paragraph() -> None:
    """Múltipla escolha: o comando separado por espaço vertical da situação ou da lista que vem
    antes dele abre parágrafo (`_block_gap`), mesmo com a linha anterior indo até a margem. PM/DF
    2025 P2, questão 76 ("III ... cometidos por civis." | "Assinale a opção correta."): o
    "julgar" do item III não é comando de certo/errado. PM/RO 2022, questão 41: situação |
    "Considerando a situação hipotética apresentada, assinale a opção correta." """
    entries = [
        _gap_entry("De acordo com o disposto na Constituição Federal de 1988 (CF)", 276.8),
        _gap_entry("e com a jurisprudência dos tribunais superiores, compete à justiça", 287.8),
        _gap_entry("militar da União", 298.8, short=True),
        _gap_entry("I processar e julgar os militares dos estados nos crimes", 315.8),
        _gap_entry("militares definidos em lei.", 326.8, x0=42.5, short=True),
        _gap_entry("II decidir sobre a perda do posto e da patente dos oficiais e da", 337.8),
        _gap_entry("graduação das praças.", 348.8, x0=42.5, short=True),
        _gap_entry("III processar e julgar os crimes militares cometidos por civis.", 359.8),
        _gap_entry("Assinale a opção correta.", 376.8, short=True),
    ]
    assert cebraspe._choice_paragraphs(entries) == [
        "De acordo com o disposto na Constituição Federal de 1988 (CF) e com a jurisprudência dos"
        " tribunais superiores, compete à justiça militar da União",
        "I processar e julgar os militares dos estados nos crimes militares definidos em lei.",
        "II decidir sobre a perda do posto e da patente dos oficiais e da graduação das praças.",
        "III processar e julgar os crimes militares cometidos por civis.",
        "Assinale a opção correta.",
    ]
    situation = [
        _gap_entry("Túlio, agente de polícia civil, recebeu ordem para", 62.5, x0=56.8),
        _gap_entry("investigar a venda de entorpecentes. O delegado orientou", 74.3),
        _gap_entry("Túlio a não agir, num primeiro momento, em relação aos", 86.1),
        _gap_entry("portadores e vendedores de drogas.", 97.9),
        _gap_entry("Considerando a situação hipotética apresentada, assinale a opção", 115.9),
        _gap_entry("correta.", 127.7, short=True),
    ]
    assert cebraspe._choice_paragraphs(situation) == [
        "Túlio, agente de polícia civil, recebeu ordem para investigar a venda de entorpecentes."
        " O delegado orientou Túlio a não agir, num primeiro momento, em relação aos portadores e"
        " vendedores de drogas.",
        "Considerando a situação hipotética apresentada, assinale a opção correta.",
    ]
    # Sem o espaço, a frase segue no mesmo parágrafo; frase que continua em minúscula também.
    glued = [*situation[:4], _gap_entry(situation[4].line.text, 109.7), situation[5]]
    assert len(cebraspe._choice_paragraphs(glued)) == 1
    lower = [
        *situation[:3],
        _gap_entry("portadores e vendedores de", 97.9),
        _gap_entry("drogas, assinale a opção correta.", 115.9, short=True),
    ]
    assert len(cebraspe._choice_paragraphs(lower)) == 1


def _quote_entry(
    text: str,
    y0: float,
    x0: float = 56.8,
    size: float = 9.0,
    short: bool = False,
    x1: float = 293.4,
) -> cebraspe._Entry:
    """Linha da coluna 1 do PC/RJ 2021 (margem 28,4): a citação da lei vem em 9 pt, recuada."""
    line = Line(text=text, plain=text, x0=x0, y0=y0, x1=x1, y1=y0 + size, column=1, size=size)
    return cebraspe._Entry(12, line, left=28.4, short=short)


def test_choice_indented_quote_is_one_paragraph_per_block() -> None:
    """Citação recuada em bloco, em letra menor: só a primeira linha de cada bloco abre parágrafo;
    as seguintes, com o mesmo recuo, continuam a frase (PC/RJ 2021, questão 39, incisos II e IX do
    art. 7.º da Lei n.º 8.137/1990, que viravam um parágrafo por linha)."""
    entries = [
        _quote_entry(
            "A autoridade policial autuou Juvenal no art. 7.º, II e IX,", 207.5, size=10.0
        ),
        _quote_entry("da Lei n.º 8.137/90, in verbis:", 218.4, x0=28.4, size=10.0, short=True),
        _quote_entry("Art. 7.º Constitui crime contra as relações de consumo:", 229.1, short=True),
        _quote_entry("[...]", 238.9, short=True),
        _quote_entry("II – vender ou expor à venda mercadoria cuja embalagem, tipo,", 248.7),
        _quote_entry("especificação, peso ou composição esteja em desacordo com as", 258.5),
        _quote_entry("prescrições legais, ou que não corresponda à respectiva", 268.3),
        _quote_entry("classificação oficial;", 278.0, short=True),
        _quote_entry("[...]", 287.8, short=True),
        _quote_entry("IX – vender, ter em depósito para vender ou expor à venda ou,", 297.7),
        _quote_entry("de qualquer forma, entregar matéria-prima ou mercadoria, em", 307.4),
        _quote_entry("condições impróprias ao consumo;", 317.2, short=True),
        _quote_entry("Pena – detenção, de 2 (dois) a 5 (cinco) anos, ou multa.", 327.0, short=True),
        _quote_entry("Nessa situação hipotética,", 342.9, x0=28.4, size=10.0, short=True),
    ]
    assert cebraspe._choice_paragraphs(entries) == [
        "A autoridade policial autuou Juvenal no art. 7.º, II e IX, da Lei n.º 8.137/90, in verbis:",
        "Art. 7.º Constitui crime contra as relações de consumo:",
        "[...]",
        "II – vender ou expor à venda mercadoria cuja embalagem, tipo, especificação, peso ou"
        " composição esteja em desacordo com as prescrições legais, ou que não corresponda à"
        " respectiva classificação oficial;",
        "[...]",
        "IX – vender, ter em depósito para vender ou expor à venda ou, de qualquer forma, entregar"
        " matéria-prima ou mercadoria, em condições impróprias ao consumo;",
        "Pena – detenção, de 2 (dois) a 5 (cinco) anos, ou multa.",
        "Nessa situação hipotética,",
    ]


def test_choice_hanging_item_continues_its_item() -> None:
    """Item I, II... (ou •) na margem com as linhas seguintes em recuo pendente maior que o de
    parágrafo: o item é um parágrafo só (PC/MA 2017 investigador, questão 31; PC/GO 2016,
    questão 32). Linha de tabela, recuada e terminada em número, segue separada (PC/RO 2022
    específicos, questão 57)."""
    entries = [
        _quote_entry(
            "III São objetivos fundamentais da República Federativa do Brasil",
            146.7,
            x0=28.4,
            size=10.0,
        ),
        _quote_entry(
            "a erradicação da pobreza e da marginalização e a redução das",
            157.0,
            x0=46.1,
            size=10.0,
        ),
        _quote_entry("desigualdades sociais.", 167.3, x0=46.1, size=10.0, short=True),
        _quote_entry(
            "• Júlia, professora de ensino fundamental, teve conhecimento de",
            177.7,
            x0=28.4,
            size=10.0,
        ),
        _quote_entry(
            "caso que envolvia suspeita de maus-tratos contra uma aluna de",
            188.0,
            x0=46.1,
            size=10.0,
        ),
        _quote_entry("competente.", 198.3, x0=46.1, size=10.0, short=True),
    ]
    assert cebraspe._choice_paragraphs(entries) == [
        "III São objetivos fundamentais da República Federativa do Brasil a erradicação da pobreza"
        " e da marginalização e a redução das desigualdades sociais.",
        "• Júlia, professora de ensino fundamental, teve conhecimento de caso que envolvia"
        " suspeita de maus-tratos contra uma aluna de competente.",
    ]
    table = [
        _quote_entry("fornecedores 22.000", 300.0, x0=60.0, size=10.0),
        _quote_entry("ativo imobilizado 35.000", 311.0, x0=60.0, size=10.0),
        _quote_entry("estoques 24.000", 322.0, x0=60.0, size=10.0),
    ]
    assert len(cebraspe._choice_paragraphs(table)) == 3


def test_choice_hanging_item_continues_after_closing_quote() -> None:
    """PC/PB 2021 gerais 14 a 17, questão 5: o item III termina a linha na aspa de fechamento e a
    localização "(décimo segundo período)." vem na linha seguinte, no recuo pendente. É o mesmo
    item; depois da aspa, linha que começa com maiúscula ou aspa nova segue separada."""
    entries = [
        _quote_entry(
            "III “a cultura da violência que nos desumaniza a todos”", 641.5, x0=304.3, size=10.0
        ),
        _quote_entry("(décimo segundo período).", 653.6, x0=325.7, size=10.0, short=True),
    ]
    for entry in entries:
        entry.left = 304.3
    assert cebraspe._choice_paragraphs(entries) == [
        "III “a cultura da violência que nos desumaniza a todos” (décimo segundo período)."
    ]
    quotes = [
        entries[0],
        _quote_entry("“Outra citação”", 653.6, x0=325.7, size=10.0, short=True),
    ]
    quotes[1].left = 304.3
    assert len(cebraspe._choice_paragraphs(quotes)) == 2


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


def test_three_line_credit_is_one_paragraph() -> None:
    """Crédito em letra miúda quebrado em três linhas (PM/MA 2017 g39, PM/SC 2023 1A9-I): antes só
    as duas últimas se emendavam e a primeira ficava num parágrafo à parte."""
    page = _page(
        [
            _line("Texto 1A1-I", 28, 30),
            _line("Corpo do texto-base com uma frase completa e bem longa.", 28, 50),
            _line(
                "Bernardo Mançano. Educação do campo e território. Núcleo de Estudos,",
                99,
                70,
                size=6.0,
            ),
            _line(
                "Pesquisas e Projetos de Reforma Agrária – NERA, Universidade Estadual Paulista",
                99,
                77,
                size=6.0,
            ),
            _line(
                "– UNESP, campus de Presidente Prudente – SP, 2017 (com adaptações).",
                99,
                84,
                size=6.0,
            ),
            _line("Com base no texto 1A1-I, julgue o item a seguir.", 28, 100),
            _line("**1** Item sobre o texto.", 28, 120),
        ]
    )
    body = cebraspe.segment([page]).passages[0].body_md
    assert body.endswith(
        "uma frase completa e bem longa.\n\nBernardo Mançano. Educação do campo e território. "
        "Núcleo de Estudos, Pesquisas e Projetos de Reforma Agrária – NERA, Universidade Estadual "
        "Paulista – UNESP, campus de Presidente Prudente – SP, 2017 (com adaptações)."
    )


def test_justified_credit_without_closing_line_is_one_paragraph() -> None:
    """PF 2018 agente, texto 12A1AAA (Poe): crédito sem "(com adaptações)", justificado em duas
    linhas que começam no mesmo x; a primeira vai até a margem e para no meio do nome ("Victor" |
    "Civita"). Com numeração de linhas a segunda parecia recuo de parágrafo e o crédito se partia."""
    page = _page(
        [
            _line("Texto 12A1AAA", 28, 30),
            _line("55 Corpo do texto-base com uma frase completa que segue", 31, 40),
            _line("adiante na linha seguinte, sem recuo, até a margem e", 46, 47),
            _line("mais uma linha do corpo, que continua a mesma frase", 46, 54),
            _line("muito considerada como a razão par excellence.", 46, 61, x1=238),
            _line(
                "Edgar Allan Poe. **A carta roubada**. *In*: **Histórias extraordinárias**. Victor",
                116.5,
                75,
                size=6.0,
            ),
            _line("Civita, 1981. Tradução de Brenno Silveira e outros.", 116.5, 86.5, size=6.0),
            _line("Com base no texto 12A1AAA, julgue o item a seguir.", 28, 105),
            _line("**1** Item sobre o texto.", 28, 125),
        ]
    )
    body = cebraspe.segment([page]).passages[0].body_md
    assert body.endswith(
        "\n\nEdgar Allan Poe. **A carta roubada**. *In*: **Histórias extraordinárias**. Victor "
        "Civita, 1981. Tradução de Brenno Silveira e outros."
    )


def test_chart_legend_in_small_print_is_not_a_credit() -> None:
    """Legendas de gráfico em letra miúda, uma embaixo da outra no mesmo x e até perto da margem
    (PF 2021 g77, "40 a 49 anos" | "50 a 59 anos"): o espaço entre elas não é o de linhas de um
    mesmo crédito, e cada uma fica no seu parágrafo."""
    page = _page(
        [
            _line("Texto 1A1-I", 28, 30),
            _line("Corpo do texto-base com uma frase completa e bem longa.", 28, 50),
            _line("40 a 49 anos", 222.6, 70, x1=268.6, size=8.0),
            _line("50 a 59 anos", 222.6, 89, x1=268.6, size=8.0),
            _line("Com base no texto 1A1-I, julgue o item a seguir.", 28, 110),
            _line("**1** Item sobre o texto.", 28, 130),
        ]
    )
    body = cebraspe.segment([page]).passages[0].body_md
    assert body.endswith("40 a 49 anos\n\n50 a 59 anos")


def test_credit_closed_by_translation_note_is_one_paragraph() -> None:
    """ "(tradução livre, com adaptações)" também fecha o crédito (PF 2018 papiloscopista, texto dos
    itens 1–5): antes cada linha do crédito virava um parágrafo."""
    page = _page(
        [
            _line("Texto 1A1-I", 28, 30),
            _line("Corpo do texto-base com uma frase completa e bem longa.", 28, 50),
            _line("Z. Nateghian *et al*. **Frontal sinus pattern and evaluation of right**", 99, 70, size=6.0),
            _line("**and left frontal sinus volume according to gender, using multi**", 99, 77, size=6.0),
            _line("**detector CT scan**. *In*: **Journal of Forensic Science & Criminology**:", 99, 84, size=6.0),
            _line("vol. 4, issue 4, ISSN: 2348-9804 (tradução livre, com adaptações).", 99, 91, size=6.0),
            _line("Com base no texto 1A1-I, julgue o item a seguir.", 28, 110),
            _line("**1** Item sobre o texto.", 28, 130),
        ]
    )  # fmt: skip
    body = cebraspe.segment([page]).passages[0].body_md
    assert body.endswith(
        "bem longa.\n\nZ. Nateghian *et al*. **Frontal sinus pattern and evaluation of right and"
        " left frontal sinus volume according to gender, using multi detector CT scan**. *In*:"
        " **Journal of Forensic Science & Criminology**: vol. 4, issue 4, ISSN: 2348-9804"
        " (tradução livre, com adaptações)."
    )


def test_credit_run_without_closing_line_stays_split() -> None:
    """Linhas miúdas à direita que não terminam no fecho do crédito não se emendam: sem o
    "(com adaptações)" ou o "Internet: <...>" não há como saber que são um crédito só."""
    page = _page(
        [
            _line("Texto 1A1-I", 28, 30),
            _line("Corpo do texto-base com uma frase completa e bem longa.", 28, 50),
            _line("Primeira nota em letra miúda.", 150, 70, size=6.0),
            _line("Segunda nota em letra miúda.", 150, 77, size=6.0),
            _line("Terceira nota em letra miúda.", 150, 84, size=6.0),
            _line("Com base no texto 1A1-I, julgue o item a seguir.", 28, 100),
            _line("**1** Item sobre o texto.", 28, 120),
        ]
    )
    body = cebraspe.segment([page]).passages[0].body_md
    assert body.endswith(
        "Primeira nota em letra miúda.\n\nSegunda nota em letra miúda.\n\n"
        "Terceira nota em letra miúda."
    )


def test_pmal_2021_cover_stays_out_of_the_first_command() -> None:
    """PM/AL 2021: "-- PROVAS OBJETIVAS --" no plural abre a prova; a capa (fonte quebrada) não
    entra no comando dos itens 1–4."""
    segmented = cebraspe.segment(extract(FIXTURES / "pdf/cebraspe/pmal-2021-oficial-p1-2.pdf"))
    assert segmented.questions[0].number == 1
    for question in segmented.questions[:4]:
        assert question.statement_md.startswith(
            "Considerando as ideias do texto CB1A1-I, julgue os itens que se seguem."
        )
        assert question.flags == []


def test_pf_2018_symbol_font_without_mapping_flags_formula() -> None:
    """PF 2018 papiloscopista: "≤ −" e "≥" saem como "# !" e "$" de uma fonte de símbolos; no item
    49 a linha ainda se junta ao número do item, e a marca tem de sobreviver à junção."""
    pages = extract(FIXTURES / "pdf/cebraspe/pf-2018-papiloscopista-p4.pdf")
    odd = [line.plain for line in pages[0].lines if line.odd_glyph]
    assert any("P(Z # !2)" in plain for plain in odd)
    assert "49 P(X < 60 litros) = P(X $ 40 litros)." in odd
    questions = {q.number: q for q in cebraspe.segment(pages, first=41).questions}
    assert "formula" in questions[48].flags
    assert "formula" in questions[49].flags
    assert questions[49].statement_md.endswith(r"P(X \< 60 litros) = P(X \$ 40 litros).")


def test_line_reference_symbol_is_ell_outside_the_old_site() -> None:
    """PF 2018: o "ℓ" de "(ℓ.2)" vem de uma fonte de símbolos que mapeia para "R", também fora dos
    cadernos do site antigo."""
    text = " ".join(
        line.text
        for page in extract(FIXTURES / "pdf/cebraspe/pf-2018-agente-p1.pdf")
        for line in page.lines
    )
    assert "“Assim” (ℓ.2)" in text
    assert "(R." not in text


@pytest.mark.parametrize(
    ("lines", "joined"),
    [
        # Composto e ênclise quebrados no hífen (PC/PB 2021 cargo 12 q66, cargo 11 q73): o hífen
        # é do original e fica (decisão 0032).
        (["para espécies-", "alvo, sendo"], "para espécies-alvo, sendo"),
        (["o intervalo pós-", "morte de um cadáver."], "o intervalo pós-morte de um cadáver."),
        (["função aplica-", "se nas lesões"], "função aplica-se nas lesões"),
        (["consiste em limpá-", "la de voos"], "consiste em limpá-la de voos"),
        # Maiúscula e algarismo depois do hífen também emendam, sem espaço (CBM/RO 2022 q38,
        # CBM/TO 2022 q7, PC/RO 2022 cargo 1 q26).
        (["o trajeto de Jaci-", "Paraná até"], "o trajeto de Jaci-Paraná até"),
        (["no texto 1A1-", "I, julgue"], "no texto 1A1-I, julgue"),
        (["(1956-", "1960)."], "(1956-1960)."),
        # Traço solto (espaço antes) não é hífen de palavra: a linha emenda com espaço.
        (["uma pausa -", "e segue"], "uma pausa - e segue"),
        # Intervalo de meses partido no travessão (PM/AL 2021 oficial, g14): sem espaço. Sem mês
        # abreviado dos dois lados, o travessão no fim da linha emenda com espaço.
        (["Brasília, out.–", "dez./2009. Internet:"], "Brasília, out.–dez./2009. Internet:"),
        (["de jul.-", "dez./2013"], "de jul.-dez./2013"),
        (["o resultado –", "dez. dias depois"], "o resultado – dez. dias depois"),
        (["no mês de out.–", "Em seguida"], "no mês de out.– Em seguida"),
    ],
)
def test_line_ending_hyphen_is_kept(lines: list[str], joined: str) -> None:
    assert cebraspe._join(lines) == joined


def test_choice_statement_credit_is_one_paragraph() -> None:
    """Crédito alinhado à direita, em três linhas que começam em x diferentes, no enunciado da
    múltipla escolha (PC/PB 2021 cargo 13, q65): um parágrafo só, com a URL inteira."""
    page = _page(
        [
            _line("Questão 1", 51, 50),
            _line("Atualmente, o combustível contém 27% de etanol misturado à gasolina.", 28, 70),
            _line("F. Amarato e F. Matoso. **Mistura de etanol na gasolina**.", 152, 90, size=6.0),
            _line(
                "Internet: <http://g1.globo.com/2015/03/mistura-de-etanol-na-", 100, 97, size=6.0
            ),
            _line("gasolina-sobe-para-27.html> (com adaptações).", 121, 104, size=6.0),
            _line("A densidade do combustível é", 28, 120, x1=150),
            *(
                _line(f"{letter} {i},7 g/mL.", 28, 132 + 12 * i, x1=100)
                for i, letter in enumerate("ABCDE")
            ),
        ]
    )
    question = cebraspe.segment([page]).questions[0]
    assert question.statement_md.split("\n\n") == [
        "Atualmente, o combustível contém 27% de etanol misturado à gasolina.",
        "F. Amarato e F. Matoso. **Mistura de etanol na gasolina**. Internet: "
        "<http://g1.globo.com/2015/03/mistura-de-etanol-na-gasolina-sobe-para-27.html> "
        "(com adaptações).",
        "A densidade do combustível é",
    ]


def test_parenthesized_credit_before_the_command_is_one_paragraph() -> None:
    """Crédito entre parênteses, alinhado à direita em duas linhas, antes do comando (PC/PB 2021
    cargo 11, q66): o ")" que fecha o "(" da primeira linha encerra o crédito, que sai num parágrafo
    só, e o comando começa outro."""
    page = _page(
        [
            _line("Questão 1", 51, 50),
            _line('"É o processo de destruição celular, de forma rápida e intensa".', 28, 70),
            _line(
                "(FRANÇA, Genival Veloso de. *Medicina Legal*, 11.ª ed., reimpr.", 134, 90, size=6.0
            ),
            _line("Rio de Janeiro: Guanabara Koogan, 2021, p. 474).", 170, 97, size=6.0),
            _line("O conceito descrito no texto precedente refere-se ao fenômeno", 28, 112),
            _line("denominado de", 28, 124, x1=100),
            *(
                _line(f"{letter} opção {i}.", 28, 136 + 12 * i, x1=100)
                for i, letter in enumerate("ABCDE")
            ),
        ]
    )
    question = cebraspe.segment([page]).questions[0]
    assert question.statement_md.split("\n\n") == [
        '"É o processo de destruição celular, de forma rápida e intensa".',
        "(FRANÇA, Genival Veloso de. *Medicina Legal*, 11.ª ed., reimpr. Rio de Janeiro: Guanabara"
        " Koogan, 2021, p. 474).",
        "O conceito descrito no texto precedente refere-se ao fenômeno denominado de",
    ]


def test_parenthesis_closed_mid_credit_does_not_close_it() -> None:
    """O ")" do fim tem de fechar o "(" do começo: "(Org.)" no meio de outra linha não basta."""
    page = _page(
        [
            _line("Questão 1", 51, 50),
            _line("Um texto qualquer termina aqui.", 28, 70),
            _line("(Org.) Sociologia. São Paulo: Ática,", 134, 90, size=6.0),
            _line("2020 (Coleção X)", 170, 97, size=6.0),
            _line("Assinale a opção correta.", 28, 112, x1=150),
            *(
                _line(f"{letter} opção {i}.", 28, 124 + 12 * i, x1=100)
                for i, letter in enumerate("ABCDE")
            ),
        ]
    )
    entries_closed = cebraspe.segment([page]).questions[0].statement_md
    assert "(Org.) Sociologia. São Paulo: Ática,\n\n2020 (Coleção X)" in entries_closed


def test_superscript_o_between_number_and_c_is_degree_sign() -> None:
    """PC/PB 2021 cargo 11 q75: "800 " + "o" sobrescrito + "C." → "800 ºC." (não "800 oC")."""
    spans = [
        {"text": "temperatura limite de 800 ", "size": 10.0, "flags": 4},
        {"text": "o", "size": 6.5, "flags": 5},
        {"text": "C.  ", "size": 10.0, "flags": 4},
    ]
    assert "".join(s["text"] for s in extract_module._degree_signs(spans)).startswith(
        "temperatura limite de 800 ºC."
    )
    # "n.o" sobrescrito e "o" sem número antes ficam como estão
    other = [spans[0] | {"text": "n."}, spans[1], spans[2]]
    assert extract_module._degree_signs(other)[1]["text"] == "o"


def _credit_entry(text: str, x0: float, y0: float, x1: float, size: float = 6.0) -> cebraspe._Entry:
    """Linha da coluna 1 (margem 28,4; direita 294,4)."""
    line = Line(text=text, plain=text, x0=x0, y0=y0, x1=x1, y1=y0 + size, column=1, size=size)
    return cebraspe._Entry(12, line, left=28.4)


def test_right_aligned_reference_without_closing_line_is_one_paragraph() -> None:
    """Referência em letra miúda alinhada à direita, em linhas coladas que terminam no mesmo x e
    começam em x diferentes, sem "(com adaptações)": um parágrafo só, mesmo com a linha de cima
    terminando em ponto (PC/RO 2022 específicos cargo 3, questão 63)."""
    entries = [
        _gap_entry("particular na sua utilização.", 155.4, short=True),
        _credit_entry("Hely Lopes Meirelles. **Direito Administrativo Brasileiro**.", 148.0, 175.6, 294.4),
        _credit_entry("Editora Malheiros. 27.ª ed. São Paulo, 2002. p. 156.", 166.7, 184.3, 292.8),
        _gap_entry("O trecho citado descreve o atributo do ato administrativo relativo à", 203.5),
    ]  # fmt: skip
    assert cebraspe._choice_paragraphs(entries) == [
        "particular na sua utilização.",
        "Hely Lopes Meirelles. **Direito Administrativo Brasileiro**. Editora Malheiros. 27.ª ed."
        " São Paulo, 2002. p. 156.",
        "O trecho citado descreve o atributo do ato administrativo relativo à",
    ]


def test_right_aligned_reference_with_wide_first_line_is_one_paragraph() -> None:
    """PC/PE 2023 P2 cargo 1, texto 1A1-I: a primeira linha da referência quase enche a coluna
    (recuo de 16 pt), as outras duas são recuadas; as três terminam na margem direita e o texto
    não se partia depois de "no Brasil**."."""
    entries = [
        _gap_entry("comerciais (-15,6%) e a residências (-13,3%).", 760.5, short=True),
        _credit_entry("Renato Sérgio de Lima e Samira Bueno. **As novas configurações**.", 44.3, 781.7, 294.4),
        _credit_entry("*In:* **Anuário Brasileiro de Segurança Pública**.", 70.3, 788.5, 294.4),
        _credit_entry("São Paulo: FBSP, 2023, pp. 90-91 (com adaptações).", 163.7, 795.5, 292.7),
    ]  # fmt: skip
    assert cebraspe._paragraphs(entries) == [
        "comerciais (-15,6%) e a residências (-13,3%).",
        "Renato Sérgio de Lima e Samira Bueno. **As novas configurações**. *In:* **Anuário"
        " Brasileiro de Segurança Pública**. São Paulo: FBSP, 2023, pp. 90-91 (com adaptações).",
    ]


def test_right_aligned_reference_starting_at_the_margin_is_one_paragraph() -> None:
    """PM/AL 2021 oficial, texto CB1A1-I: a primeira linha da referência enche a coluna, da margem
    à direita, e a de baixo, recuada e alinhada à direita, encerra o crédito ("\\<corteidh.or.cr>
    (com adaptações)."). Um parágrafo só. Sem o fecho, linha miúda na margem fica separada."""
    entries = [
        _gap_entry("na construção da cidadania.", 505.0, short=True),
        _credit_entry("Manoel Carlos Mendonça Filho *et al*. **Polícia**. Internet:", 28.4, 519.6, 293.5),
        _credit_entry("\\<corteidh.or.cr> (com adaptações).", 207.7, 527.2, 293.5),
    ]  # fmt: skip
    assert cebraspe._paragraphs(entries) == [
        "na construção da cidadania.",
        "Manoel Carlos Mendonça Filho *et al*. **Polícia**. Internet: \\<corteidh.or.cr> (com"
        " adaptações).",
    ]
    loose = [
        entries[0],
        _credit_entry("Nota do quadro: valores em milhares de reais, sem correção.", 28.4, 519.6, 293.5),
        _credit_entry("Dados de 2020.", 207.7, 527.2, 293.5),
    ]  # fmt: skip
    assert len(cebraspe._paragraphs(loose)) == 3


def test_right_aligned_chart_labels_stay_apart() -> None:
    """Legendas de gráfico alinhadas à direita, uma por linha, com espaço de 3/4 do corpo entre
    elas (PF 2021 g77, "9% 15 a 19 anos" | "20 a 29 anos"): não são uma referência."""
    entries = [
        _credit_entry("9% 15 a 19 anos", 81.6, 102.3, 268.6, size=8.0),
        _credit_entry("20 a 29 anos", 222.6, 116.3, 268.6, size=8.0),
    ]
    assert len(cebraspe._paragraphs(entries)) == 2
    assert len(cebraspe._choice_paragraphs(entries)) == 2


def test_hanging_item_line_starting_with_dash_continues_the_item() -> None:
    """Linha do item que começa com o travessão do aposto continua a frase (PC/MA 2017
    investigador, questões 26 e 47: "...especializadas" | "— polícias civis e militares —, ...";
    "— mistas ou híbridas" | "—, aplica-se ...")."""
    entries = [
        _quote_entry(
            "III A polícia judiciária é privativa de corporações especializadas",
            470.5,
            x0=28.4,
            size=10.0,
        ),
        _quote_entry(
            "— polícias civis e militares —, enquanto a polícia", 482.2, x0=46.1, size=10.0
        ),
        _quote_entry("administração.", 494.0, x0=46.1, size=10.0, short=True),
        _quote_entry(
            "II Em caso de normas processuais materiais — mistas ou híbridas",
            505.7,
            x0=28.4,
            size=10.0,
        ),
        _quote_entry(
            "—, aplica-se a retroatividade da lei mais benéfica.", 517.4, x0=46.1, size=10.0
        ),
    ]
    assert cebraspe._choice_paragraphs(entries) == [
        "III A polícia judiciária é privativa de corporações especializadas — polícias civis e"
        " militares —, enquanto a polícia administração.",
        "II Em caso de normas processuais materiais — mistas ou híbridas —, aplica-se a"
        " retroatividade da lei mais benéfica.",
    ]


def test_bold_subject_title_in_two_lines_is_a_heading() -> None:
    """Título de disciplina em negrito e corpo maior quebrado em duas linhas ("DIREITO TRIBUTÁRIO
    E DIREITO" | "EMPRESARIAL", PC/MA 2017 delegado): a segunda linha também é título e não gruda
    na alternativa E da questão anterior. Rótulo em negrito no corpo do texto, abaixo de um título
    do mesmo corpo, não é continuação."""
    first = _title_line("**DIREITO TRIBUTÁRIO E DIREITO**", 55.4, 14)
    first = first.model_copy(update={"plain": "DIREITO TRIBUTÁRIO E DIREITO"})
    second = _title_line("**EMPRESARIAL**", 71.8, 14).model_copy(update={"plain": "EMPRESARIAL"})
    assert cebraspe._subject_heading(first)
    assert cebraspe._heading_continuation(first, second)
    small = first.model_copy(update={"size": 10.0, "y1": 65.4})
    label = _title_line("**Texto 1A1-I**", 69.0, 10).model_copy(update={"plain": "Texto 1A1-I"})
    assert not cebraspe._heading_continuation(small, label)


def test_photo_below_question_title_flags_the_question() -> None:
    """CBM/RO 2022, questões 38 e 40: a fotografia vem logo abaixo do título "Questão N", e só a
    legenda e o comando são texto. A linha acima da figura é o título, que não entra na questão; a
    marca passa do título à questão. Desenho no mesmo lugar (moldura do título, PC/GO 2016) não
    marca nada (decisão 0030, emenda de 2026-10-14)."""

    def lines() -> list[Line]:
        return [
            *_choice(1, "Primeira questão.", 20),
            _line("Questão 2", 51, 110),
            _line("Trecho em construção da ferrovia.", 150, 230, x1=290, size=6),
            _line("Relacionando a hidrografia, assinale a opção correta.", 28, 245),
            *(
                _line(f"{letter} opção {letter}.", 28, 260 + 12 * i, x1=100)
                for i, letter in enumerate("ABCDE")
            ),
        ]

    photo = Figure(kind="image", x0=40, y0=125, x1=280, y1=225)
    questions = {q.number: q for q in cebraspe.segment([_page(lines(), [photo])]).questions}
    assert questions[2].flags == ["figure"]
    assert questions[1].flags == []
    frame = Figure(kind="drawing", x0=40, y0=125, x1=280, y1=225)
    questions = {q.number: q for q in cebraspe.segment([_page(lines(), [frame])]).questions}
    assert questions[2].flags == []


def test_subject_heading_rules_do_not_flag_the_question_above() -> None:
    """CBM/RO 2022 oficial, questão 15: o cabeçalho "MATEMÁTICA" vem entre duas réguas desenhadas.
    As réguas são moldura do cabeçalho, não figura da questão de cima. Desenho grande no mesmo
    lugar continua marcando."""
    lines = [
        *_choice(1, "Primeira questão.", 20),
        _line("**MATEMÁTICA**", 124, 113, x1=198),
        *_choice(2, "Segunda questão.", 135),
    ]
    rules = [
        Figure(kind="drawing", x0=29, y0=109.5, x1=290, y1=110.0),
        Figure(kind="drawing", x0=29, y0=127.0, x1=290, y1=128.0),
    ]
    questions = {q.number: q for q in cebraspe.segment([_page(lines, rules)]).questions}
    assert questions[1].flags == []
    assert questions[2].flags == []
    box = Figure(kind="drawing", x0=29, y0=100.0, x1=290, y1=110.0)
    questions = {q.number: q for q in cebraspe.segment([_page(lines, [box])]).questions}
    assert questions[1].flags == ["figure"]


def test_band_behind_a_title_is_not_a_figure_of_the_question_above() -> None:
    """CBM/TO 2021 soldado, questão 30 (pág. 6): o título "Noções de Informática" em corpo de
    título vem numa faixa cinza desenhada, logo depois da alternativa D. A faixa é fundo do título,
    não figura da questão de cima (emenda (20) da 0020). Desenho que passa bem do título, ou atrás
    de linha em corpo de texto, continua marcando."""
    lines = [
        *_choice(1, "Primeira questão.", 20),
        _line("**Noções de Informática**", 80, 102, x1=240, size=15),
        *_choice(2, "Segunda questão.", 125),
    ]
    band = Figure(kind="drawing", x0=29, y0=100.0, x1=290, y1=115.5)
    questions = {q.number: q for q in cebraspe.segment([_page(lines, [band])]).questions}
    assert questions[1].flags == []
    assert questions[2].flags == []
    tall = Figure(kind="drawing", x0=29, y0=80.0, x1=290, y1=115.5)
    questions = {q.number: q for q in cebraspe.segment([_page(lines, [tall])]).questions}
    assert questions[1].flags == ["figure"]
    small = [*lines[:7], _line("Noções de Informática", 80, 102, x1=240), *lines[8:]]
    questions = {q.number: q for q in cebraspe.segment([_page(small, [band])]).questions}
    assert "figure" in questions[1].flags


def test_code_line_of_the_item_is_a_paragraph() -> None:
    """PM/AL 2021 oficial, item 37: o comando em fonte monoespaçada, numa linha à parte depois da
    frase terminada, é um parágrafo; código em várias linhas segue num bloco só."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** Para visualizar as primeiras linhas de um arquivo de", 28, 70),
            _line("nome `messages.log`, pode ser utilizado o comando a", 46, 82),
            _line("seguir.", 46, 94, x1=80),
            _line("`head messages.log`", 46, 116, x1=140, size=9),
            _line("**2** Considere o programa a seguir.", 28, 140, x1=200),
            _line("`x <- 1`", 46, 152, x1=100, size=9),
            _line("`print(x)`", 46, 164, x1=100, size=9),
            _line("O resultado será 1.", 46, 176, x1=150),
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert questions[0].statement_md == (
        "Julgue os itens a seguir.\n\nPara visualizar as primeiras linhas de um arquivo de nome"
        " `messages.log`, pode ser utilizado o comando a seguir.\n\n`head messages.log`"
    )
    assert questions[1].statement_md.endswith(
        "Considere o programa a seguir.\n\n`x <- 1 print(x)`\n\nO resultado será 1."
    )


def test_url_broken_across_lines_is_joined_without_space() -> None:
    """CBM/RO 2022, questões 38 e 40: o endereço partido no crédito da figura não ganha espaço na
    junção; a palavra comum depois do endereço continua separada."""
    assert (
        cebraspe._join(
            [
                "Internet: https://s3.amazonaws.com/files/",
                "ferrovia\\_do\\_diabo\\_-\\_construcao\\_-",
                "\\_obras.jpg.",
            ]
        )
        == "Internet: https://s3.amazonaws.com/files/ferrovia\\_do\\_diabo\\_-\\_construcao\\_-\\_obras.jpg."
    )
    assert (
        cebraspe._join(
            ["Internet: https://www.soldepando.com/wp-content/uploads/", "2016/11/Tratado.jpg."]
        )
        == "Internet: https://www.soldepando.com/wp-content/uploads/2016/11/Tratado.jpg."
    )
    assert cebraspe._join(["Disponível em: https://www.gov.br/pf/", "Acesso em 3/2/2021."]) == (
        "Disponível em: https://www.gov.br/pf/ Acesso em 3/2/2021."
    )
    assert cebraspe._join(["Internet: \\<http://funag.gov.br>", "(com adaptações)."]) == (
        "Internet: \\<http://funag.gov.br> (com adaptações)."
    )


def test_bold_caps_subject_title_in_body_size_keeps_its_second_line() -> None:
    """PM/SC 2023 soldado, antes da questão 17: "NOÇÕES DE DIREITO PROCESSUAL PENAL" | "COMUM",
    em negrito, caixa alta e corpo do texto. Com o estilo ligado, a primeira linha sai como título
    e a segunda grudava na alternativa E da questão 16. Linha com número ou em caixa baixa abaixo
    do título do mesmo corpo não é continuação."""
    first = _title_line("**NOÇÕES DE DIREITO PROCESSUAL PENAL**", 50.0, 10)
    first = first.model_copy(update={"plain": "NOÇÕES DE DIREITO PROCESSUAL PENAL"})
    second = _title_line("**COMUM**", 60.7, 10).model_copy(update={"plain": "COMUM"})
    assert cebraspe._subject_heading(first)
    assert cebraspe._heading_continuation(first, second)
    label = _title_line("**TEXTO 1A1-I**", 60.7, 10).model_copy(update={"plain": "TEXTO 1A1-I"})
    assert not cebraspe._heading_continuation(first, label)
    lower = _title_line("**Comum**", 60.7, 10).model_copy(update={"plain": "Comum"})
    assert not cebraspe._heading_continuation(first, lower)


def test_labeled_definitions_are_one_paragraph_each() -> None:
    """PM/SC 2023 soldado, texto 1A7-I: as sentenças abertas "c(x): ...", "l(x): ...", "w(x): ..."
    vêm em linhas seguidas, sem ponto nem recuo, e saíam num parágrafo só. Cada linha com rótulo
    abre parágrafo quando o parágrafo aberto também começa com rótulo; a continuação sem rótulo
    ("expressão confunde...") fica na definição. Vale também para as premissas "P1: “...”" e a
    conclusão "C: “...”", que terminam em aspas (PC/PE 2023 P2 cargo 1, situação 1A3-II)."""
    entries = [
        _gap_entry("no conjunto universo V de todos os cidadãos de determinada", 127.0),
        _gap_entry("cidade.", 140.0, short=True),
        _gap_entry("c(x): a pessoa confunde crime com liberdade de expressão", 155.8),
        _gap_entry("l(x): a pessoa confunde liberdade de expressão com crime", 168.8),
        _gap_entry("w(x): a pessoa que confunde crime com liberdade de", 181.6),
        _gap_entry("expressão confunde liberdade de expressão com crime", 194.5),
    ]
    expected = [
        "no conjunto universo V de todos os cidadãos de determinada cidade.",
        "c(x): a pessoa confunde crime com liberdade de expressão",
        "l(x): a pessoa confunde liberdade de expressão com crime",
        "w(x): a pessoa que confunde crime com liberdade de expressão confunde liberdade de"
        " expressão com crime",
    ]
    assert cebraspe._paragraphs(entries) == expected
    assert cebraspe._choice_paragraphs(entries) == expected
    premises = [
        _gap_entry("P4: “Se não preciso tentar roubá-lo, não cometi esse crime.”", 469.9),
        _gap_entry("C: “Logo, não cometi esse crime.”", 483.4, short=True),
    ]
    assert len(cebraspe._paragraphs(premises)) == 2
    # Linha comum que só começa com parênteses e dois-pontos no meio da frase não é rótulo.
    prose = [
        _gap_entry("a pessoa (x) disse que a função f(x) dada por", 100.0),
        _gap_entry("f(x): definida no texto, é contínua", 111.0),
    ]
    assert len(cebraspe._paragraphs(prose)) == 1


def test_bold_heading_after_the_last_option_ends_it() -> None:
    """CBM/TO 2022 soldado, questão 10: o título "**Normas relativas ao CBMTO**" (12 pt,
    centrado) grudava na alternativa D. Linha só em negrito, curta e sem pontuação depois de
    alternativa terminada encerra a alternativa; negrito no meio da frase, não."""
    option = _gap_entry("D referencial.", 608.5)
    heading = cebraspe._Entry(
        2,
        Line(
            text="**Normas relativas ao CBMTO**",
            plain="Normas relativas ao CBMTO",
            x0=84.5,
            y0=622.6,
            x1=238.4,
            y1=634.6,
            column=1,
            size=12.0,
        ),
        left=28.3,
    )
    assert cebraspe._heading_after_option(option, heading)
    open_sentence = _gap_entry("D a pessoa que confunde", 608.5)
    assert not cebraspe._heading_after_option(open_sentence, heading)
    sentence = cebraspe._Entry(
        2, heading.line.model_copy(update={"text": "**Normas.**", "plain": "Normas."}), left=28.3
    )
    assert not cebraspe._heading_after_option(option, sentence)
    # CBM/TO 2021 soldado, questão 40: "D Facebook" sem ponto e o título em corpo de título
    # (15 pt) no alto da coluna seguinte também encerra a alternativa; em corpo de texto, não.
    facebook = _gap_entry("D Facebook", 794.1)
    big = cebraspe._Entry(2, heading.line.model_copy(update={"size": 15.0}), left=28.3)
    assert cebraspe._heading_after_option(facebook, big)
    assert not cebraspe._heading_after_option(facebook, heading)


def test_poem_is_one_stanza_with_line_breaks() -> None:
    """PM/AL 2021 soldado, pág. 3 (só o poema e os itens 20–24 da coluna 1): "À procura da
    infância" é uma estrofe só; cada verso termina em quebra de linha (`\\`), não em parágrafo, e o
    verso longo que vai até a margem continua na linha seguinte."""
    pages = extract(FIXTURES / "pdf/cebraspe/pmal-2021-soldado-p3.pdf", styles=True)
    segmented = cebraspe.segment(pages, first=20)
    assert [(q.number, q.passage_key) for q in segmented.questions] == [
        (n, "g20") for n in range(20, 25)
    ]
    title, stanza, credit = segmented.passages[0].body_md.split("\n\n")
    assert title == "**À procura da infância**"
    verses = stanza.split("\\\n")
    assert len(verses) == 19
    assert verses[:2] == ["Procuro ouvir na voz do vento", "o eco perdido da minha infância."]
    assert verses[11] == (
        "tão lindas, de tranças sedosas, a bonequinha de trapo que eu embalei nos meus braços."
    )
    assert verses[-1] == "que os anos guardaram no seu abismo."
    assert credit.startswith("Anilda Leão.")


def _verse(text: str, y0: float, x0: float = 28.4, x1: float | None = None) -> cebraspe._Entry:
    """Linha de 10 pt com entrelinha de 13,2 (PM/AL 2021 soldado); curta se `x1` não vem."""
    right = x1 if x1 is not None else x0 + 6 * len(text)
    line = Line(text=text, plain=text, x0=x0, y0=y0, x1=right, y1=y0 + 10, column=1, size=10.0)
    return cebraspe._Entry(3, line, left=28.4, short=right < 294.4 - 40)


def test_stanzas_split_only_on_vertical_space() -> None:
    """Estrofe nova só com espaço vertical maior que o entrelinha; versos centralizados também são
    estrofe (CBM/AL 2017 soldado, "O Xote das meninas")."""
    first = [
        "Disse ele que agora",
        "Só me amava como esposa",
        "Não como star",
        "Me amassou as rosas",
    ]
    second = ["Nunca mais romance", "Nunca mais cinema", "Nunca mais cheese", "Nunca mais feliz"]
    entries = [_verse(t, 100 + 13.2 * i) for i, t in enumerate(first)]
    entries += [_verse(t, 170 + 13.2 * i) for i, t in enumerate(second)]
    assert cebraspe._paragraphs(entries) == ["\\\n".join(first), "\\\n".join(second)]
    assert cebraspe._choice_paragraphs(entries) == ["\\\n".join(first), "\\\n".join(second)]
    xote = [
        ("Mandacaru quando fulora na seca", 368.3, 502.9),
        ("É o siná que a chuva chega no sertão", 362.3, 509.0),
        ("Toda menina que enjoa da boneca", 367.4, 503.7),
        ("É siná que o amor já chegou no coração...", 352.2, 518.9),
    ]
    centered = [
        cebraspe._Entry(
            4,
            Line(
                text=t,
                plain=t,
                x0=x0,
                y0=88 + 18.3 * i,
                x1=x1,
                y1=98 + 18.3 * i,
                column=2,
                size=10.0,
            ),
            left=304.4,
            short=True,
        )
        for i, (t, x0, x1) in enumerate(xote)
    ]
    assert cebraspe._paragraphs(centered) == ["\\\n".join(t for t, _, _ in xote)]


def test_short_lines_that_are_not_verse_stay_paragraphs() -> None:
    """Não é verso: linhas curtas que fecham a frase (prosa), item de lista, linha de tabela que
    termina em número ou em letra solta (tabela-verdade), código e a correspondência oficial."""
    prose = [
        "Primeiro parágrafo curto.",
        "Segundo parágrafo curto.",
        "Terceiro parágrafo.",
        "Quarto parágrafo curto.",
    ]
    listing = [
        "I fazer massagem cardíaca",
        "II desobstruir as vias aéreas",
        "III imobilizar",
        "IV transportar a vítima",
    ]
    accounts = [
        "caixa e equivalentes R$ 10.000",
        "estoques para revenda R$ 250.000",
        "veículos R$ 120.000",
        "fornecedores R$ 80.000",
    ]
    truth = ["V V V", "V V F", "V F V", "V F F", "F V V"]
    code = ["`CREATE TABLE catalogo (`", "`id_tabela INT,`", "`descricao TEXT,`", "`colunas TEXT,`"]
    letter = [
        "Governo do Estado da Paraíba",
        "Delegacia Geral de Polícia Civil",
        "Superintendência Regional de Polícia",
        "Senhora gerente,",
        "Encaminho a solicitação",
    ]
    for lines in (prose, listing, accounts, truth, code, letter):
        entries = [_verse(t, 100 + 13.2 * i) for i, t in enumerate(lines)]
        assert cebraspe._paragraphs(entries) == lines, lines


def test_option_letter_with_style_leaves_the_body() -> None:
    """A letra da alternativa em fonte com estilo ("*E* intranet.", PC/PB 2021) não fica no corpo."""
    for line in ("E intranet.", "*E* intranet.", "**E** intranet."):
        assert cebraspe.OPTION_MD.sub("", line, count=1) == "intranet."
    assert cebraspe.OPTION_MD.sub("", "A *h*/2.", count=1) == "*h*/2."


def test_propositions_p_and_q_stay_in_the_item() -> None:
    """CBM/AL 2017 básicos cargo 1, item 48: "P: ..." e "Q: ..." recuados, depois de frase fechada.
    O "Q:" abria o texto-base seguinte e os itens 49 e 50 se perdiam (gabarito com 45 itens para
    43 questões); proposição alinhada com outra do mesmo item continua o item (emenda (15) da
    0020)."""
    pages = extract(FIXTURES / "pdf/cebraspe/cbmal-2017-basicos-cargo-1-p4.pdf", styles=True)
    segmented = cebraspe.segment(pages, first=45)
    assert [q.number for q in segmented.questions] == [45, 46, 47, 48, 49, 50]
    by_number = {q.number: q for q in segmented.questions}
    assert "orphan_text" not in by_number[48].flags
    # Cada proposição e o texto depois delas em parágrafo próprio (emenda (21) da 0020).
    assert by_number[48].statement_md.endswith(
        "degradar a vida no planeta.\n\nQ: A humanidade diminui a produção de material plástico e"
        " encontra uma solução para o problema do lixo desse material ou o acúmulo de plástico no"
        " meio ambiente degradará a vida no planeta.\n\nNesse caso, é correto afirmar que as"
        " proposições P e Q são equivalentes."
    )
    assert "proposições:\n\nP: Se a humanidade" in by_number[48].statement_md
    assert by_number[49].statement_md.startswith(
        "A respeito de proposições lógicas, julgue os itens a seguir.\n\nA sentença Soldado,"
    )


def test_credit_closing_split_across_lines_is_one_paragraph() -> None:
    """CBM/AL 2017 básicos cargo 1, texto CB1A1AAA: o crédito começa no mesmo x nas três linhas,
    a primeira termina em ponto e o "(com" fica no fim da segunda, com o "adaptações)." na
    terceira. O fecho casa juntando as duas últimas (`_credit_closes`), e o crédito é um parágrafo
    só, não partido antes de "*In*:"."""
    entries = [
        _gap_entry("concretas de desarmamento nuclear.", 564.3, x0=46.0, short=True),
        _credit_entry("Sergio de Queiroz Duarte. **Esforços internacionais em prol do desarmamento**.", 81.2, 583.3, 290.8),
        _credit_entry("*In*: **Desarmamento e temas correlatos**. Brasília: FUNAG, 2014, p. 23-5 (com", 81.2, 590.8, 290.7),
        _credit_entry("adaptações).", 81.2, 598.1, 111.2),
        _gap_entry("Julgue os itens a seguir.", 620.0),
    ]  # fmt: skip
    assert cebraspe._paragraphs(entries) == [
        "concretas de desarmamento nuclear.",
        "Sergio de Queiroz Duarte. **Esforços internacionais em prol do desarmamento**. *In*:"
        " **Desarmamento e temas correlatos**. Brasília: FUNAG, 2014, p. 23-5 (com adaptações).",
        "Julgue os itens a seguir.",
    ]
    # Sem o "(com" em cima, "adaptações)." sozinho não fecha nada e a nota solta fica separada.
    loose = [entries[0], entries[1], _credit_entry("Dados de 2016.", 81.2, 590.8, 140.0)]
    assert len(cebraspe._paragraphs(loose)) == 3
    assert not cebraspe._credit_closes(loose, 2)


def test_figure_opening_the_next_column_starts_the_next_passage() -> None:
    """CBM/AL 2017 básicos cargo 1: o item 40 termina em frase fechada no pé da página 3; a página
    4 abre com a figura e, abaixo dela, "Na figura precedente, o retângulo ABCD tem as seguintes",
    com o recuo de parágrafo (17,7 pt) igual ao de continuação de item. A linha é do texto-base
    das questões 41 a 44, não do item 40."""
    item_line = Line(
        text="objeto apresentado.", plain="objeto apresentado.",
        x0=322.8, y0=777.6, x1=400.7, y1=787.6, column=2, size=10.0,
    )  # fmt: skip
    opener = Line(
        text="Na figura precedente, o retângulo ABCD tem as seguintes",
        plain="Na figura precedente, o retângulo ABCD tem as seguintes",
        x0=46.0, y0=214.5, x1=290.7, y1=224.5, column=1, size=10.0,
    )  # fmt: skip
    page = Page(
        number=4, width=595.0, height=842.0, has_text=True, lines=[opener],
        figures=[Figure(kind="drawing", x0=49.0, y0=54.0, x1=271.0, y1=198.0)],
    )  # fmt: skip
    entry = cebraspe._Entry(4, opener, left=28.3)
    cebraspe._with_figures(page, [entry], [])
    assert entry.below_figure and "figure" in entry.flags
    item = cebraspe._Unit(entries=[cebraspe._Entry(3, item_line, left=304.4, short=True)])
    assert not cebraspe._continues(item, entry)
    # Sem a figura acima, a linha com esse recuo segue no item, como antes.
    plain = cebraspe._Entry(4, opener, left=28.3)
    assert cebraspe._continues(item, plain)


def test_hanging_labeled_item_in_passage_is_one_paragraph() -> None:
    """Texto-base do certo/errado com itens de recuo pendente (emenda (17) da 0020). PM/MA 2017
    específicos cargo 5, situações I a III: o rótulo na margem e as linhas seguintes recuadas;
    cada item é um parágrafo. CBM/AL 2017 básicos cargo 1, texto das questões 41 a 44: o
    marcador "•" já recuado, a continuação mais recuada. Linhas recuadas sem item rotulado
    (tabela, título) seguem separadas."""
    entries = [
        _gap_entry("A seguir são apresentadas três situações hipotéticas.", 343.0, short=True),
        _gap_entry("I Um usuário, após sequestro de seus dados, recebeu a", 363.1),
        _gap_entry("informação de que, para reavê-los, seria necessário realizar", 375.7, x0=46.0),
        _gap_entry("um pagamento ao sequestrador.", 388.2, x0=46.0, short=True),
        _gap_entry("II Um usuário recebeu informação, por meio do setor de", 408.2),
        _gap_entry("segurança da informação do seu órgão, de que seu computador,", 420.8, x0=46.0),
        _gap_entry("rede de outro órgão.", 433.3, x0=46.0, short=True),
    ]
    assert cebraspe._paragraphs(entries) == [
        "A seguir são apresentadas três situações hipotéticas.",
        "I Um usuário, após sequestro de seus dados, recebeu a informação de que, para reavê-los,"
        " seria necessário realizar um pagamento ao sequestrador.",
        "II Um usuário recebeu informação, por meio do setor de segurança da informação do seu"
        " órgão, de que seu computador, rede de outro órgão.",
    ]
    bullets = [
        _gap_entry("• o ponto E sobre o lado AB é tal que AE = 2 cm;", 256.9, x0=46.0, short=True),
        _gap_entry("• o ponto F sobre o lado BD é tal que o ângulo entre EB e", 268.6, x0=46.0),
        _gap_entry("EF mede 45º;", 280.4, x0=63.6, short=True),
    ]
    assert cebraspe._paragraphs(bullets) == [
        "• o ponto E sobre o lado AB é tal que AE = 2 cm;",
        "• o ponto F sobre o lado BD é tal que o ângulo entre EB e EF mede 45º;",
    ]
    table = [
        _gap_entry("Pb vermelho cinza rosa incolor incolor incolor", 100.0, x0=46.0),
        _gap_entry("Ba laranja incolor incolor incolor incolor incolor", 112.0, x0=46.0),
    ]
    assert len(cebraspe._paragraphs(table)) == 2


def _pf2012_entry(text: str, y0: float, x0: float = 28.3, x1: float = 290.8) -> cebraspe._Entry:
    """Linha de 10 pt da coluna 1 do PF 2012 agente, página 8 (geometria do caderno)."""
    line = Line(text=text, plain=text, x0=x0, y0=y0, x1=x1, y1=y0 + 10, column=1, size=10.0)
    return cebraspe._Entry(8, line, left=28.3, short=x1 < 290.8 - cebraspe.SHORT_LINE)


def test_list_items_split_and_command_after_list() -> None:
    """PF 2012 agente, itens 83 e 84 (reprovação do minos, semente r26): texto-base com a
    introdução e os eventos I a IV, cada um em seu parágrafo, e o comando "À luz ..." à parte.
    O item II partido antes de um número ("... abril de" | "2012, no valor ...") continua o item;
    o IV abre parágrafo mesmo com o III indo até a margem; a crase maiúscula separa o comando."""
    entries = [
        _pf2012_entry("Determinada entidade apresentou os seguintes eventos no mês de", 135.8),
        _pf2012_entry("abril de 2012.", 149.5, x1=83.9),
        _pf2012_entry("I pagamento de R\\$ 4.200,00, no mês de abril de 2012, referentes", 171.2),
        _pf2012_entry("a aluguel dos meses de abril e maio de 2012;", 184.9, x0=46.0, x1=224.8),
        _pf2012_entry("II consumo e pagamento de despesas, em abril de 2012, com", 198.4),
        _pf2012_entry(
            "serviços de limpeza e conservação, relativos ao mês de abril de", 212.1, x0=46.0
        ),
        _pf2012_entry("2012, no valor de R\\$ 1.800,00;", 225.7, x0=46.0, x1=170.9),
        _pf2012_entry("III recebimento, em abril de 2012, em dinheiro, por serviços", 239.4),
        _pf2012_entry(
            "prestados no mês de março de 2012, no valor de R\\$ 3.600,00;", 252.9, x0=46.0
        ),
        _pf2012_entry("IV prestação de serviços, no mês de abril de 2012, para", 266.6),
        _pf2012_entry(
            "recebimento em maio de 2012, no valor de R\\$ 5.700,00.", 280.2, 46.0, 271.3
        ),
        _pf2012_entry("À luz do regime de caixa e do regime de competência, julgue os", 302.0),
        _pf2012_entry(
            "itens seguintes, relativos à apuração de resultado do mês de abril de", 315.6
        ),
        _pf2012_entry("2012 da entidade considerada.", 329.2, x1=149.7),
    ]
    situation, command = cebraspe._split_command(cebraspe._text_paragraphs(entries))
    assert situation == [
        "Determinada entidade apresentou os seguintes eventos no mês de abril de 2012.",
        "I pagamento de R\\$ 4.200,00, no mês de abril de 2012, referentes a aluguel dos meses de"
        " abril e maio de 2012;",
        "II consumo e pagamento de despesas, em abril de 2012, com serviços de limpeza e"
        " conservação, relativos ao mês de abril de 2012, no valor de R\\$ 1.800,00;",
        "III recebimento, em abril de 2012, em dinheiro, por serviços prestados no mês de março de"
        " 2012, no valor de R\\$ 3.600,00;",
        "IV prestação de serviços, no mês de abril de 2012, para recebimento em maio de 2012, no"
        " valor de R\\$ 5.700,00.",
    ]
    assert command.startswith("À luz do regime de caixa")
    # Fora da sequência (II depois de IV), noutra margem ou sem fechar o item: não abre parágrafo.
    third, fourth = entries[7], entries[9]
    assert cebraspe._next_list_item(third, entries[8], fourth)
    assert not cebraspe._next_list_item(fourth, entries[10], entries[4])
    assert not cebraspe._next_list_item(third, entries[7], fourth)  # "serviços" não fecha o III


def test_choice_centered_formula_is_its_own_paragraph() -> None:
    """PM/SC 2023 oficial, questão 66: a fórmula centralizada em linha própria, que não termina
    em ponto nem fica curta, é um parágrafo; o comando na margem abaixo dela abre outro. Linha
    só recuada (primeira linha de parágrafo) não é centralizada. Emenda (19) da 0020."""
    page = _page(
        [
            _line("Questão 66", 51, 50),
            _line("((P ˄ S) → (Q ˅ R)) → ((~R ˅ P) → (~Q ˅ ~S)", 62.4, 68, x1=259.7),
            _line("O número de linhas da tabela-verdade da proposição lógica", 28.4, 89, x1=293.6),
            _line("precedente é igual a", 28.4, 103, x1=110),
            *(
                _line(f"{letter} {2**i}.", 28.4, 125 + 14 * i, x1=60)
                for i, letter in enumerate("ABCDE", start=1)
            ),
            _line("Questão 67", 51, 210),
            _line("Uma pesquisa revelou que 45% dos policiais militares de", 56.9, 222, x1=293.6),
            _line("Santa Catarina haviam sido surfistas e, entre esses policiais", 28.4, 236),
            _line("militares surfistas, construíam suas próprias pranchas", 28.4, 250, x1=293.6),
            _line("Qual o percentual?", 28.4, 264, x1=120),
            *(
                _line(f"{letter} {i}%.", 28.4, 280 + 14 * i, x1=60)
                for i, letter in enumerate("ABCDE", start=1)
            ),
        ]
    )
    first, second = cebraspe.segment([page], first=66).questions
    assert first.statement_md == (
        "((P ˄ S) → (Q ˅ R)) → ((~R ˅ P) → (~Q ˅ ~S)\n\n"
        "O número de linhas da tabela-verdade da proposição lógica precedente é igual a"
    )
    assert [o.body_md for o in first.options] == ["2.", "4.", "8.", "16.", "32."]
    assert second.statement_md.startswith(
        "Uma pesquisa revelou que 45% dos policiais militares de Santa Catarina haviam"
    )
    assert "\n\n" not in second.statement_md  # o recuo de parágrafo não é centralização


def test_bold_sentence_after_item_stays_in_the_item() -> None:
    """PRF 2021, item 26: a frase inteira em negrito que o item anuncia ("... conforme o exemplo a
    seguir." | "**Assunto: Realização de concurso público.**") termina em ponto, não é título de
    bloco: fica no item, em parágrafo próprio. Emenda (19) da 0020."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50, x1=150),
            _line("**26** O assunto das comunicações oficiais deve seguir as", 28, 70),
            _line("orientações do MRPR, conforme o exemplo a seguir.", 46, 82, x1=200),
            _line("**Assunto: Realização de concurso público.**", 46, 100, x1=230),
            _line("**27** Outro item.", 28, 120, x1=100),
        ]
    )
    first, second = cebraspe.segment([page], first=26).questions
    assert first.statement_md.endswith(
        "conforme o exemplo a seguir.\n\n**Assunto: Realização de concurso público.**"
    )
    assert second.statement_md.endswith("Outro item.")


def _item_line(text: str, x0: float, y0: float, x1: float) -> Line:
    """Linha de 10 pt da coluna 1 (margem 28,4; direita 294,4)."""
    plain = text.replace("**", "")
    return Line(text=text, plain=plain, x0=x0, y0=y0, x1=x1, y1=y0 + 11.1, column=1, size=10.0)


def test_labeled_sentences_in_the_item_are_paragraphs() -> None:
    """CBM/AL 2021 soldado, item 86 (pág. 7): "Considere as seguintes sentenças." | "S1: ..." |
    "S2: ..." (partida em duas linhas) | "Sendo as sentenças S1 e S2 verdadeiras, ...". Cada
    sentença rotulada e o texto seguinte em parágrafo próprio; antes saía tudo num parágrafo só
    (o item não olhava rótulos). Emenda (21) da 0020."""
    lines = [
        _item_line("Considerando os conectivos lógicos usuais, julgue os itens a seguir.", 28.4, 700.0, 294.0),
        _item_line("**86** Considere as seguintes sentenças.", 28.4, 739.7, 183.3),
        _item_line("S1: Todo bombeiro tem bom condicionamento físico.", 46.4, 751.3, 263.1),
        _item_line("S2: Toda pessoa que dorme bem tem bom condicionamento", 46.4, 762.9, 294.3),
        _item_line("físico.", 46.4, 774.5, 73.6),
        _item_line("Sendo as sentenças S1 e S2 verdadeiras, então se pode", 46.4, 786.1, 294.4),
        _item_line("concluir que todo bombeiro dorme bem.", 46.4, 797.7, 210.0),
    ]  # fmt: skip
    question = cebraspe.segment([_page(lines)], first=86).questions[0]
    assert question.number == 86
    assert question.statement_md.split("\n\n")[1:] == [
        "Considere as seguintes sentenças.",
        "S1: Todo bombeiro tem bom condicionamento físico.",
        "S2: Toda pessoa que dorme bem tem bom condicionamento físico.",
        "Sendo as sentenças S1 e S2 verdadeiras, então se pode concluir que todo bombeiro dorme bem.",
    ]


def test_single_proposition_stays_in_the_item_paragraph() -> None:
    """Proposição solta, sem outra rotulada alinhada no item ("... a seguinte proposição:" |
    "P: ..."), não abre parágrafo: uma linha só com rótulo não é lista."""
    lines = [
        _item_line("Julgue os itens a seguir.", 28.4, 700.0, 140.0),
        _item_line("**1** Considere a seguinte proposição:", 28.4, 720.0, 200.0),
        _item_line("P: Se chove, então a rua fica molhada. Nesse caso, a", 46.4, 731.6, 294.4),
        _item_line("negação de P é equivalente a chover e a rua não ficar molhada.", 46.4, 743.2, 290.0),
    ]  # fmt: skip
    statement = cebraspe.segment([_page(lines)]).questions[0].statement_md
    assert statement.split("\n\n")[1].startswith("Considere a seguinte proposição: P: Se chove")


def test_ocr_credit_with_jittering_size_is_one_paragraph() -> None:
    """PC/DF 2020 básicos (OCR), crédito do texto da pág. 2: duas linhas miúdas no mesmo x, com
    corpos 5,2 e 4,7 (o corpo vem da altura da caixa do OCR). No OCR é o mesmo corpo, e o crédito
    é um parágrafo só, com o título em negrito inteiro. No PDF com texto, corpos diferentes
    continuam separados. Emenda (21) da 0020."""

    def entries(ocr: bool) -> list[cebraspe._Entry]:
        found = [
            _credit_entry("se sentir embalado pelo mundo.", 29.0, 602.9, 157.1, size=7.5),
            _credit_entry(
                "Raduan Nassar. **Aí pelas três da tarde**. *In*: Ítalo Moriconi (Org.). **Os cem melhores**",
                71.3, 618.9, 292.8, size=5.2,
            ),
            _credit_entry(
                "**contos brasileiros do século**. Rio de Janeiro: Objetiva, 2001 (com adaptações).",
                71.3, 627.2, 263.7, size=4.7,
            ),
            _credit_entry("No que se refere às ideias e aos aspectos linguísticos do texto", 28.4, 641.2, 293.4, size=7.5),
        ]  # fmt: skip
        found[0].short = True
        for entry in found:
            entry.ocr = ocr
        return found

    assert cebraspe._paragraphs(entries(ocr=True)) == [
        "se sentir embalado pelo mundo.",
        "Raduan Nassar. **Aí pelas três da tarde**. *In*: Ítalo Moriconi (Org.). **Os cem melhores"
        " contos brasileiros do século**. Rio de Janeiro: Objetiva, 2001 (com adaptações).",
        "No que se refere às ideias e aos aspectos linguísticos do texto",
    ]
    assert len(cebraspe._paragraphs(entries(ocr=False))) == 4


def _passage(segmented: Segmented, key: str) -> list[str]:
    return next(p for p in segmented.passages if p.key == key).body_md.split("\n\n")


def test_first_line_indent_on_numbered_line_opens_paragraph() -> None:
    """PM/AL 2018, texto 1A1-I (reprovação do minos, semente r34): a linha 13 ("Há que
    experimentar...") tem o número na margem e o texto com recuo de primeira linha, depois de uma
    linha que vai até a margem direita. O número levava o x0 da linha para a margem e o recuo se
    perdia: o 2.º e o 3.º parágrafos saíam juntos. O x0 do texto (`body_x0`) guarda o recuo."""
    pages = extract(FIXTURES / "pdf/cebraspe/pmal-2018-p1.pdf", styles=True)
    numbered = next(line for line in pages[0].lines if line.plain.startswith("13 Há que"))
    assert numbered.x0 < 40 and numbered.body_x0 is not None and numbered.body_x0 > 80
    paragraphs = _passage(cebraspe.segment(pages), "1A1-I")
    assert [p[:20] for p in paragraphs[:4]] == [
        "Dói. Dói muito. Dói ",
        "No princípio, se um ",
        "Há que experimentar ",
        "Sem a mãe, a casa ve",
    ]
    assert paragraphs[1].endswith("mãe, beija aqui!")
    assert len(paragraphs) == 5  # 4 parágrafos + o crédito


def test_command_atop_next_column_after_numbered_text() -> None:
    """PM/AL 2017 básicos, texto CB1A1AAA: o comando "Com relação às ideias do texto CB1A1AAA,
    julgue os itens que se" | "seguem." abre a coluna da direita. Medidas contra a margem do texto
    numerado da coluna da esquerda, as duas linhas pareciam recuadas e viravam parágrafos
    separados; o comando ficava no texto-base, e os itens 1 a 6 sem comando (`no_command`)."""
    segmented = cebraspe.segment(
        extract(FIXTURES / "pdf/cebraspe/pmal-2017-basicos-soldado-p1.pdf", styles=True)
    )
    paragraphs = _passage(segmented, "CB1A1AAA")
    assert not any("julgue" in p for p in paragraphs)
    assert paragraphs[2].startswith("Lançadas com o intuito")  # linha 13, recuada
    assert paragraphs[3].startswith("O mito da criminalidade")  # linha 22, recuada
    first = segmented.questions[0]
    assert first.statement_md.split("\n\n")[0] == (
        "Com relação às ideias do texto CB1A1AAA, julgue os itens que se seguem."
    )
    assert not next(p for p in segmented.passages if p.key == "CB1A1AAA").flags


def test_line_numbers_in_the_next_column_are_stripped() -> None:
    """PC/MA 2017 delegado, texto CG1A1AAA: o texto numerado continua no alto da coluna da
    direita, com margem própria. Contra a margem da coluna da esquerda os números 46, 49 e 52
    não saíam, e cada linha virava um parágrafo; contra a margem dali, seguindo a numeração (45 <
    46), saem, e o texto fica em dois parágrafos."""
    segmented = cebraspe.segment(
        extract(FIXTURES / "pdf/cebraspe/pcma-2017-delegado-p1.pdf", styles=True)
    )
    paragraphs = _passage(segmented, "CG1A1AAA")
    assert paragraphs[-3].startswith("Outro passo é tentar erradicar a pobreza")
    assert paragraphs[-3].endswith("preservando a diversidade cultural e o ambiente.")
    assert paragraphs[-2] == (
        "É, então, no entrelaçamento “paz — desenvolvimento — direitos humanos — democracia” que"
        " podemos vislumbrar a educação para a paz."
    )
    assert not any(p[:3].strip().isdigit() for p in paragraphs)


def test_number_out_of_sequence_in_another_column_stays() -> None:
    """Na coluna com margem própria, só o número que segue a numeração já tirada sai: um "2020"
    que abre a linha fica no texto."""

    def entry(text: str, x0: float, y0: float, column: int) -> cebraspe._Entry:
        line = Line(text=text, plain=text, x0=x0, y0=y0, x1=x0 + 240, y1=y0 + 10, column=column,
                    size=10.0)  # fmt: skip
        return cebraspe._Entry(1, line, 28.3 if column == 1 else 304.4)

    entries = [
        entry("1 Primeira linha do texto que vai até a margem", 34.0, 100, 1),
        entry("segunda linha do texto que vai até a margem", 46.0, 112, 1),
        entry("terceira linha do texto que vai até a margem", 46.0, 124, 1),
        entry("4 quarta linha do texto que vai até a margem", 34.0, 136, 1),
        entry("e outra linha do texto que vai até a margem", 46.0, 148, 1),
        entry("quinta linha do texto que vai até a margem", 322.1, 100, 2),
        entry("sexta linha do texto que vai até a margem", 322.1, 112, 2),
        entry("7 sétima linha do texto que vai até a margem", 307.9, 124, 2),
        entry("2020 foi o ano em que a linha começa por número", 307.9, 136, 2),
    ]
    stripped, numbered = cebraspe._strip_line_numbers(entries)
    assert [e.line.plain.split()[0] for e in stripped] == [
        "Primeira", "segunda", "terceira", "quarta", "e", "quinta", "sexta", "sétima", "2020",
    ]  # fmt: skip
    assert numbered == {(1, 1), (1, 2)}


def test_choice_option_made_of_loose_lines_keeps_line_breaks() -> None:
    """PC/PE 2023 P2 cargo 1, questão 50 (pág. 13): cada alternativa traz quatro lançamentos, um
    por linha, que terminam bem antes da margem direita, sem pontuação, e a primeira palavra da
    linha seguinte caberia na sobra. As linhas viram quebras de linha (`\\`). A alternativa de
    texto corrido, que quebra por falta de espaço, e a de duas linhas seguem juntas com espaço
    (emenda (23) da 0020)."""
    page = _page(
        [
            _line("Nas questões a seguir, marque a única opção correta.", 28, 8),
            _line("Questão 1", 51, 20),
            _line("Assinale a opção que apresenta corretamente a contabilização", 28, 32),
            _line("da referida operação.", 28, 44, x1=120),
            _line("A débito – despesas bancárias", 28, 56, x1=150),
            _line("débito – despesa de juros", 42, 68, x1=140),
            _line("débito – conta-corrente bancária", 42, 80, x1=170),
            _line("crédito – títulos a receber", 42, 92, x1=145),
            # texto corrido: a linha de cima vai até a margem
            _line("B débito na conta de despesas bancárias e crédito na conta", 28, 104),
            _line("de títulos descontados, pelo valor líquido da operação", 42, 116),
            _line("com o banco", 42, 128, x1=100),
            # duas linhas só: fica como está
            _line("C débito – bancos", 28, 140, x1=110),
            _line("crédito – empréstimos a pagar", 42, 152, x1=160),
            # a palavra seguinte não caberia na sobra da linha de cima
            _line("D débito – encargos financeiros a transcorrer no", 28, 164, x1=262),
            _line("transcurso do tempo da operação", 42, 176, x1=200),
            _line("crédito – títulos descontados", 42, 188, x1=160),
            # linha de cima termina a frase
            _line("E débito – bancos.", 28, 200, x1=110),
            _line("Débito – despesas bancárias.", 42, 212, x1=160),
            _line("Crédito – títulos descontados.", 42, 224, x1=160),
        ]
    )
    (question,) = cebraspe.segment([page]).questions
    bodies = [option.body_md for option in question.options]
    assert bodies[0] == (
        "débito – despesas bancárias\\\ndébito – despesa de juros\\\n"
        "débito – conta-corrente bancária\\\ncrédito – títulos a receber"
    )
    assert "\\\n" not in "".join(bodies[1:])
    assert bodies[2] == "débito – bancos crédito – empréstimos a pagar"
