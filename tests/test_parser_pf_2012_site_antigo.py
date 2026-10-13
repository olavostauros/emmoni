"""Cadernos do PF 2012 no site antigo do Cebraspe (delegado, escrivão, papiloscopista; decisão 0020):
rodapé com o número da página, "julgador" no texto-base e número de item fora da linha numa página
de uma coluna só."""

from ingest import extract as ex
from ingest.extract import Line, Page
from ingest.parsers import cebraspe


def _line(
    text: str, x0: float, y0: float, x1: float = 290.0, size: float = 10.0, column: int = 1
) -> Line:
    plain = text.replace("**", "")
    return Line(text=text, plain=plain, x0=x0, y0=y0, x1=x1, y1=y0 + 10, column=column, size=size)


def _page(lines: list[Line]) -> Page:
    head = _line("-- PROVA OBJETIVA --", 217, 10, x1=380, size=15, column=0)
    return Page(number=1, width=595, height=842, has_text=True, lines=[head, *lines], figures=[])


def test_page_number_footer_is_dropped() -> None:
    """Número da página ("– 3 –") no pé da página não entra no fim do item nem no texto-base."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** O prefeito dispensou licitação fora das hipóteses", 28, 70),
            _line("previstas em lei.", 46, 82, x1=120),
            _line("– 3 –", 547, 806, x1=567, size=7, column=2),
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert questions[0].statement_md.endswith("previstas em lei.")
    assert "– 3 –" not in questions[0].statement_md


def test_julgador_in_the_passage_is_not_the_command() -> None:
    """PF 2012 papiloscopista, itens 111–113: "... auxiliar o julgador." no texto-base não abre o
    comando; o texto-base é o parágrafo e o comando começa em "Tendo o texto acima"."""
    page = _page(
        [
            _line("A finalidade da identificação humana é fornecer provas para", 64, 50),
            _line("auxiliar o julgador. Sua origem é remota na história.", 28, 62),
            _line("Tendo o texto acima como referência inicial, julgue os", 28, 82),
            _line("próximos itens.", 28, 94, x1=100),
            _line("**1** A genitália externa define-se na oitava semana.", 28, 110),
        ]
    )
    segmented = cebraspe.segment([page])
    question = segmented.questions[0]
    assert question.passage_key == "g1"
    assert question.statement_md.startswith("Tendo o texto acima como referência inicial")
    assert segmented.passages[0].body_md.endswith("Sua origem é remota na história.")


def test_item_number_beside_a_full_width_line_opens_it() -> None:
    """Página de química do PF 2012 papiloscopista, em uma coluna só: o número do item vem em fonte
    menor, numa linha à parte 1 pt abaixo do texto, e caía depois dele na ordem de leitura."""
    lines = [
        _line("A decantação é o método mais indicado.", 46.7, 160.6, x1=520, column=0),
        _line("91", 28.3, 161.8, x1=37.3, size=8, column=1),
        _line("A eventual dissolução de nitrato de amônio.", 46.7, 175.9, x1=520, column=0),
        _line("92", 28.3, 177.0, x1=37.3, size=8, column=1),
        _line("100 O volume molar do vapor de iodo.", 28.3, 777.7, x1=520, column=1),
    ]
    attached = ex._attach_item_numbers(lines)
    plains = [line.plain for line in ex._reading_order(attached)]
    assert plains == [
        "91 A decantação é o método mais indicado.",
        "92 A eventual dissolução de nitrato de amônio.",
        "100 O volume molar do vapor de iodo.",
    ]
    assert attached[0].x0 == 28.3 and attached[0].column == 0


def test_number_far_from_the_text_stays_apart() -> None:
    """Número de linha de texto-base ou número solto longe do texto não é juntado."""
    lines = [
        _line("Texto de largura total.", 120, 100, x1=520, column=0),
        _line("5", 28, 101, x1=33, size=8, column=1),
    ]
    assert ex._attach_item_numbers(lines) == lines
