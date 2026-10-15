"""Cadernos do PF 2012 no site antigo do Cebraspe (delegado, escrivão, papiloscopista; decisão 0020):
rodapé com o número da página, "julgador" no texto-base e número de item fora da linha numa página
de uma coluna só."""

from ingest import extract as ex
from ingest.extract import Figure, Line, Page
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


def test_letter_vocative_and_closing_keep_their_lines() -> None:
    """PF 2012 escrivão 21–22, papiloscopista 14 e 17: vocativo e fecho da correspondência ficam
    na própria linha (quebra de linha do Markdown), e o item não vai para revisão por `layout`."""
    page = _page(
        [
            _line("Julgue os fragmentos a seguir quanto à correção gramatical.", 28, 50),
            _line("**1** Senhor Delegado,", 28, 70, x1=120),
            _line("Segue para divulgação o relatório das investigações", 46, 82),
            _line("realizadas no órgão.", 46, 94, x1=150),
            _line("**2** Informamos que a ata não foi assinada por todos os", 28, 110),
            _line("presentes.", 46, 122, x1=100),
            _line("Atenciosamente,", 46, 134, x1=110),
            _line("José da Silva", 46, 146, x1=110),
        ]
    )
    first, second = cebraspe.segment([page]).questions
    assert first.statement_md.endswith(
        "\n\nSenhor Delegado,\\\nSegue para divulgação o relatório das investigações realizadas"
        " no órgão."
    )
    assert second.statement_md.endswith("todos os presentes.\\\nAtenciosamente,\\\nJosé da Silva")
    assert "layout" not in first.flags and "layout" not in second.flags


def test_short_line_without_letter_shape_is_still_layout() -> None:
    """Linha curta sem pontuação que não é vocativo nem fecho continua indo para revisão."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** O comando abaixo", 28, 70, x1=120),
            _line("lista os arquivos do diretório.", 46, 82, x1=200),
        ]
    )
    assert "layout" in cebraspe.segment([page]).questions[0].flags


def test_generic_expediente_is_not_a_missing_passage() -> None:
    """PF 2012 escrivão 18, papiloscopista 19, agente 26: "o memorando", "o expediente" num grupo
    cujo comando não aponta documento são o gênero, não um texto-base que faltou."""
    page = _page(
        [
            _line("Com relação às correspondências oficiais, julgue os itens seguintes.", 28, 50),
            _line("**1** A menos que o expediente seja de mero encaminhamento,", 28, 70),
            _line("o texto deve conter introdução, desenvolvimento e conclusão.", 46, 82, x1=200),
            _line("Com base no expediente acima, julgue o item a seguir.", 28, 100),
            _line("**2** O fecho do expediente está adequado.", 28, 120, x1=200),
        ]
    )
    first, second = cebraspe.segment([page]).questions
    assert "missing_passage" not in first.flags
    assert "missing_passage" in second.flags  # o comando aponta um documento que não veio


def test_discursive_title_in_the_middle_column_stops_the_objective_test() -> None:
    """PF 2012 escrivão e papiloscopista: "PROVA DISCURSIVA" centrado, em corpo grande, cai na
    coluna 1; as instruções da discursiva não podem virar texto solto depois do último item."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 50),
            _line("**1** O documento deve ser preservado.", 28, 70, x1=200),
        ]
    )
    discursive = Page(
        number=2,
        width=595,
        height=842,
        has_text=True,
        lines=[
            _line("PROVA DISCURSIVA", 226, 52, x1=370, size=15),
            _line("Nesta prova, faça o que se pede.", 46, 70, column=0),
        ],
        figures=[],
    )
    question = cebraspe.segment([page, discursive]).questions[-1]
    assert "orphan_text" not in question.flags


def test_figure_with_credit_below_opens_the_next_group() -> None:
    """PF 2012 papiloscopista 58–59 (e PF 2018 papiloscopista 107–108): figura entre o fim de um
    item e o crédito dela; é da abertura do grupo seguinte, não do item de cima."""
    page = Page(
        number=1,
        width=595,
        height=842,
        has_text=True,
        lines=[
            _line("-- PROVA OBJETIVA --", 217, 10, x1=380, size=15, column=0),
            _line("Julgue os itens seguintes, acerca da papiloscopia.", 28, 50),
            _line("**1** O princípio da imutabilidade diz respeito à", 28, 70),
            _line("completa putrefação cadavérica.", 46, 82, x1=200),
            _line("Juan Vucetich. Dactiloscopia comparada. La Plata:", 150, 210, size=6),
            _line("Jacobo Peuser, 1904 (com adaptações).", 150, 218, size=6),
            _line("A partir das ilustrações acima, julgue os itens seguintes.", 28, 240),
            _line("**2** O tipo fundamental da figura B é a presilha interna.", 28, 260, x1=250),
        ],
        figures=[Figure(kind="image", x0=40, y0=100, x1=290, y1=200)],
    )
    first, second = cebraspe.segment([page]).questions
    assert "figure" not in first.flags
    assert "figure" in second.flags


def _span(text: str, font: str = "TT331o00", size: float = 9.98) -> dict[str, object]:
    return {"text": text, "font": font, "size": size, "flags": 4}


def _raw(spans: list[dict[str, object]], x0: float, x1: float) -> dict[str, object]:
    return {"spans": spans, "bbox": (x0, 498.1, x1, 508.0)}


def test_item_number_does_not_set_the_size_of_a_justified_line() -> None:
    """PF 2012 delegado, item 106: na linha justificada cada palavra vem numa linha própria, e a
    primeira ("106" em 8 pt + "É" em 10 pt) tinha mais letras no corpo do número. Unida às
    vizinhas, parecia índice ou expoente e o item caía em `review` por fórmula."""
    fonts = ex._Fonts(digits={}, styles={})
    first = ex._line(
        _raw([_span("106", "TT334o00", 8.05), _span(" "), _span("É ")], 28.3, 55.3), 297, fonts
    )
    assert first is not None
    assert first.size == 10.0
    words = [ex._line(_raw([_span(w)], x, x + 40), 297, fonts) for w, x in (("legalmente ", 63.6),)]
    merged = ex._merge([first, *(w for w in words if w is not None)])
    assert not merged.scripts


def test_unmapped_glyph_of_the_ell_font_is_a_formula() -> None:
    """A fonte de símbolos do "ℓ" (o glifo sai "R") traz também "∧", que sai "v": "P∧Q" virava
    "PvQ" sem aviso (PF 2012 agente 53, papiloscopista 40). Fora de "(ℓ.N)", outro glifo dela no
    meio do texto marca a linha; glifo sozinho na linha (a tecla Enter, "<") não."""
    ell = "TTFF21o00"
    spans = [_span("(", "TTFF18o00"), _span("R", ell), _span(".12)", "TTFF18o00")]
    line_spans = [
        _span("representada por P", "TTFF18o00"),
        _span("v", ell),
        _span("Q.", "TTFF18o00"),
    ]
    assert ex._ell_fonts([[{"spans": spans}]]) == frozenset({ell})
    fonts = ex._Fonts(digits={}, styles={}, ell=frozenset({ell}))
    ref = ex._line(_raw(spans, 28, 60), 297, fonts)
    pvq = ex._line(_raw(line_spans, 28, 200), 297, fonts)
    enter = ex._line(_raw([_span("<", ell)], 400, 410), 297, fonts)
    assert ref is not None and ref.plain == "(ℓ.12)" and not ref.odd_glyph
    assert pvq is not None and pvq.odd_glyph
    assert enter is not None and not enter.odd_glyph


def test_rascunho_frame_in_pieces_is_not_a_figure() -> None:
    """PF 2012 escrivão, item 57: o quadro do "RASCUNHO" logo abaixo do item vem em quatro traços e
    um filete à direita, nenhum com a palavra inteira dentro; o item ganhava `figure`."""
    frame = [
        Figure(kind="drawing", x0=304.4, y0=437.6, x1=360.8, y1=446.2),
        Figure(kind="drawing", x0=304.4, y0=437.6, x1=360.8, y1=438.6),
        Figure(kind="drawing", x0=304.4, y0=446.2, x1=360.8, y1=451.8),
        Figure(kind="drawing", x0=304.4, y0=450.8, x1=360.8, y1=451.8),
        Figure(kind="drawing", x0=360.8, y0=446.2, x1=566.9, y1=447.1),
    ]
    page = Page(
        number=1,
        width=595,
        height=842,
        has_text=True,
        lines=[
            _line("-- PROVA OBJETIVA --", 217, 10, x1=380, size=15, column=0),
            _line(
                "Considerando essa situação hipotética, julgue os itens.", 304, 380, 566, column=2
            ),
            _line(
                "**1** Com base nas proposições P1 e P2, é correto concluir",
                304,
                400,
                566,
                column=2,
            ),
            _line("que a organização deseja obter informações.", 322, 412, 500, column=2),
            Line(
                text="RASCUNHO",
                plain="RASCUNHO",
                x0=311.8,
                y0=441.8,
                x1=353.4,
                y1=448.8,
                column=2,
                size=7.0,
            ),
        ],
        figures=frame,
    )
    (question,) = cebraspe.segment([page]).questions
    assert "figure" not in question.flags
    # Sem o RASCUNHO, os mesmos traços seguem sendo figura do item de cima.
    page.lines = page.lines[:-1]
    (question,) = cebraspe.segment([page]).questions
    assert "figure" in question.flags


def test_vertical_space_between_blocks_opens_a_paragraph() -> None:
    """PF 2012 escrivão, item 57: a situação tem quatro blocos separados por espaço vertical
    (introdução | P1 e P2 | "Diante dessa situação..." | P3 e P4), com linhas que vão até a margem
    e sem recuo. A introdução e P1 viravam um parágrafo, P2 e "Diante dessa situação" outro."""
    right = 566.0
    rows = [
        ("Suspeita-se de que um chefe de organização criminosa", 339.7, 50.8, right),
        ("tenha assumido as despesas de determinado candidato em curso de", 304.4, 63.1, right),
        ("preparação para concurso para provimento de vagas do órgão X.", 304.4, 75.4, right),
        ("P1: Existe a convicção por parte dos servidores do órgão X de que,", 304.4, 95.1, right),
        ("se um chefe pagou o curso, ou o chefe é amigo de infância do", 304.4, 107.3, right),
        ("candidato ou então esse candidato foi recrutado pela organização", 304.4, 119.7, right),
        ("criminosa para ser aprovado no concurso;", 304.4, 131.9, right - 5),
        (
            "P2: Há, ainda, entre os servidores do órgão X, a certeza de que, se",
            304.4,
            144.3,
            right,
        ),
        ("o candidato foi recrutado, então essa organização deseja obter", 304.4, 156.5, right),
        ("informações sigilosas ou influenciar as decisões do órgão X.", 304.4, 168.9, right),
        ("Diante dessa situação, o candidato, inquirido a respeito, disse o", 304.4, 184.9, right),
        ("seguinte:", 304.4, 197.1, 345.0),
        ("P3: Ele é meu amigo de infância, e eu não sabia que ele é chefe de", 304.4, 216.8, right),
        ("organização criminosa;", 304.4, 229.1, 410.0),
        ("P4: Pedi a ele que pagasse meu curso de preparação, mas ele não", 304.4, 241.4, right),
        ("pagou.", 304.4, 253.7, 335.0),
        (
            "Considerando essa situação hipotética, julgue os itens subsecutivos.",
            304.4,
            273.4,
            right,
        ),
        ("**55** Com fundamento nas proposições P1, P2, P3 e P4, confirma-se", 304.4, 293.1, right),
        ("a suspeita.", 322.8, 305.3, 380.0),
    ]
    page = _page([_line(text, x0, y0, x1, column=2) for text, x0, y0, x1 in rows])
    segmented = cebraspe.segment([page], first=55)
    paragraphs = segmented.passages[0].body_md.split("\n\n")
    assert [p.split(" ")[0] for p in paragraphs] == [
        "Suspeita-se",
        "P1:",
        "P2:",
        "Diante",
        "P3:",
        "P4:",
    ]
    assert paragraphs[0].endswith("do órgão X.")
    assert (
        paragraphs[3]
        == "Diante dessa situação, o candidato, inquirido a respeito, disse o seguinte:"
    )
    assert segmented.questions[0].statement_md.startswith("Considerando essa situação hipotética")


def test_vertical_space_does_not_cut_the_command_nor_a_sentence() -> None:
    """O espaço entre blocos não parte o comando ("julgue ..., acerca da seguinte proposição:" |
    "P: ...", PF 2018 papiloscopista, item 51) nem uma frase que segue na linha de baixo (fórmula
    no meio da linha empurra a seguinte, PF 2012 papiloscopista, item 109)."""
    rows = [
        ("A figura ilustra o espectro na região da luz visível. No caso de", 28.0, 50.0, 290.0),
        ("átomos hidrogenoides, o comprimento de onda é expresso por , em", 28.0, 62.3, 290.0),
        ("que N é o", 28.0, 74.6, 290.0),
        ("número de prótons no núcleo atômico e m e n são números inteiros.", 28.0, 92.0, 290.0),
        ("A constante de Rydberg é dada no próprio texto da questão.", 28.0, 104.3, 290.0),
        ("Julgue os próximos itens, acerca da seguinte proposição:", 28.0, 124.0, 260.0),
        ("P: “A nomeação ocorre para reposição de vacância”.", 28.0, 143.7, 250.0),
        ("**1** A proposição P é uma disjunção.", 28.0, 163.4, 220.0),
    ]
    page = _page([_line(text, x0, y0, x1) for text, x0, y0, x1 in rows])
    segmented = cebraspe.segment([page])
    (question,) = segmented.questions
    assert question.statement_md.startswith(
        "Julgue os próximos itens, acerca da seguinte proposição: P: “A nomeação"
    )
    assert "no_command" not in question.flags
    assert segmented.passages[0].body_md.startswith(
        "A figura ilustra o espectro na região da luz visível. No caso de átomos hidrogenoides,"
        " o comprimento de onda é expresso por , em que N é o número de prótons"
    )


class _RawDocument:
    """Documento falso para `_mono_fonts`: uma página com os spans dados (rawdict)."""

    def __init__(self, spans: list[tuple[str, str, float]]) -> None:
        self.spans = spans

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter([self])

    def get_text(self, kind: str) -> dict[str, object]:
        assert kind == "rawdict"
        spans = [
            {
                "font": font,
                "size": 9.0,
                "chars": [
                    {"c": c, "bbox": (i * width * 9.0, 0, (i + 1) * width * 9.0, 9)}
                    for i, c in enumerate(text)
                ],
            }
            for text, font, width in self.spans
        ]
        return {"blocks": [{"lines": [{"spans": spans}]}]}


def test_monospaced_font_with_few_letters() -> None:
    """Menos de 8 letras: só com 3 ou mais distintas, todas com a largura da Courier (0,6 corpo)."""
    assert ex._mono_fonts(_RawDocument([("Bcc", "TT61o00", 0.599), ("no", "TT61o00", 0.599)])) == {
        "TT61o00"
    }
    assert ex._mono_fonts(_RawDocument([(".bat", "TT62o00", 0.6)])) == {"TT62o00"}
    # Duas letras ("V"/"F" de tabela-verdade) não provam nada.
    assert ex._mono_fonts(_RawDocument([("VVFF", "TT63o00", 0.6)])) == frozenset()
    # Mesma largura, mas fora da Courier (0,611 é o "F"/"L" da Times): fica de fora.
    assert ex._mono_fonts(_RawDocument([("FLT", "TT64o00", 0.611)])) == frozenset()
    assert ex._mono_fonts(_RawDocument([("abc", "TT65o00", 0.5)])) == frozenset()


def test_monospaced_font_becomes_inline_code() -> None:
    """PF 2012 escrivão, item 32: "joao_jose", "Bibliotecas > Documentos > Projetos" e os caminhos
    "C:\\..." vêm numa fonte sem nome monoespaçada (Courier convertida, toda letra com 0,6 corpo) e
    viravam texto comum; docs/content-format.md pede código inline para comandos e caminhos."""
    document = _RawDocument(
        [
            ("C:UsersjoaojoseDocumentsProjetos", "TT55o00", 0.6),
            ("Considere que um usuário de login", "TT49o00", 0.45),
            ("ilmw", "TT49o00", 0.3),
        ]
    )
    assert ex._mono_fonts(document) == frozenset({"TT55o00"})
    fonts = ex._Fonts(digits={}, styles={}, mono=frozenset({"TT55o00"}))
    first = ex._line(
        _raw(
            [
                _span("de login ", "TT49o00"),
                _span("joao_jose", "TT55o00", 9.0),
                _span(" observa: ", "TT49o00"),
                _span("Bibliotecas >", "TT55o00", 9.0),
            ],
            304,
            566,
        ),
        297,
        fonts,
    )
    second = ex._line(
        _raw(
            [
                _span("Documentos > Projetos", "TT55o00", 9.0),
                _span(" e não ", "TT49o00"),
                _span("C:\\Users\\joao_jose", "TT55o00", 9.0),
                _span(".", "TT49o00"),
            ],
            304,
            566,
        ),
        297,
        fonts,
    )
    assert first is not None and second is not None
    assert first.text == "de login `joao_jose` observa: `Bibliotecas >`"
    assert first.plain == "de login joao_jose observa: Bibliotecas >"
    assert cebraspe._join([first.text, second.text]) == (
        "de login `joao_jose` observa: `Bibliotecas > Documentos > Projetos` e não"
        " `C:\\Users\\joao_jose`."
    )


def test_prose_comma_leaves_the_code() -> None:
    """PC/PB 2021 gerais 4 a 13, q12: ".gif, " em monoespaçada, vírgula e espaço no mesmo trecho; a
    vírgula é da frase. Linha de código terminada em vírgula (SQL do PF 2025) fica como está."""
    fonts = ex._Fonts(digits={}, styles={}, mono=frozenset({"TT55o00"}))

    def text(*spans: dict[str, object]) -> str:
        line = ex._line(_raw(list(spans), 304, 566), 297, fonts)
        assert line is not None
        return line.text

    prose = text(
        _span("em formato ", "TT49o00"),
        _span(".gif, ", "TT55o00", 9.0),
        _span("para então", "TT49o00"),
    )
    assert prose == "em formato `.gif`, para então"
    assert text(_span("id_tabela INT, ", "TT55o00", 9.0)) == "`id_tabela INT,`"


def test_declared_range_reaches_every_item_across_commands() -> None:
    """O "Texto para os itens de 1 a 3" (PC/DF 2013 agente, PF 2009 escrivão): o texto vale para os
    itens da faixa também depois de um comando novo; o item 4, fora da faixa, fica sem ele e, como
    o comando remete a "o texto", vai para revisão. Emenda (33) da 0020."""
    page = _page(
        [
            _line("**Texto para os itens de 1 a 3**", 28, 40, x1=150),
            _line("A prisão fabrica delinquentes pelo tipo de existência que", 43, 55),
            _line("impõe aos detentos.", 28, 67, x1=120),
            _line("Com base no texto, julgue os itens seguintes.", 28, 85),
            _line("**1** O texto é argumentativo.", 28, 100, x1=180),
            _line("**2** O texto é narrativo.", 28, 115, x1=170),
            _line("Acerca de aspectos linguísticos do texto, julgue os itens a", 28, 130),
            _line("seguir.", 28, 142, x1=60),
            _line("**3** O termo “prisão” é sujeito.", 28, 157, x1=190),
            _line("**4** O termo “detentos” é objeto.", 28, 172, x1=190),
        ]
    )
    segmented = cebraspe.segment([page])
    keys = [q.passage_key for q in segmented.questions]
    assert keys == ["g1", "g1", "g1", None]
    assert segmented.questions[2].statement_md.startswith("Acerca de aspectos linguísticos")
    assert "missing_passage" in segmented.questions[3].flags
    assert "missing_passage" not in segmented.questions[2].flags


def test_declared_range_ends_where_another_passage_starts() -> None:
    """Outro texto-base que começa dentro da faixa encerra a faixa: os itens seguintes ficam com
    o texto novo."""
    page = _page(
        [
            _line("**Texto para os itens de 1 a 3**", 28, 40, x1=150),
            _line("A prisão fabrica delinquentes pelo tipo de existência que", 43, 55),
            _line("impõe aos detentos.", 28, 67, x1=120),
            _line("Com base no texto, julgue os itens seguintes.", 28, 85),
            _line("**1** O texto é argumentativo.", 28, 100, x1=180),
            _line("Um policial apreendeu um veículo sem documentos.", 28, 115),
            _line("Considerando essa situação, julgue os itens a seguir.", 28, 130),
            _line("**2** A apreensão foi legal.", 28, 145, x1=170),
            _line("**3** O veículo deve ser devolvido.", 28, 160, x1=190),
        ]
    )
    keys = [q.passage_key for q in cebraspe.segment([page]).questions]
    assert keys == ["g1", "g2", "g2"]


def test_range_title_name_and_author_get_their_own_paragraphs() -> None:
    """PC/DF 2013 agente, p. 2: "**Texto para os itens de 1 a 10**" | "**Pavio do destino**"
    (centrado) | "Sérgio Sampaio" (à direita) | versos numerados. O nome não se junta ao título nem
    o autor ao primeiro verso. Emenda (33) da 0020."""
    page = _page(
        [
            _line("**Texto para os itens de 1 a 2**", 28, 40, x1=150),
            _line("**Pavio do destino**", 99, 55, x1=169),
            _line("Sérgio Sampaio", 169, 70, x1=233),
            _line("1 O bandido e o mocinho", 40, 85, x1=157),
            _line("São os dois do mesmo ninho", 64, 97, x1=178),
            _line("Correm nos estreitos trilhos", 64, 109, x1=174),
            _line("4 Lá no morro dos aflitos", 40, 121, x1=170),
            _line("Na Favela do Esqueleto", 64, 133, x1=160),
            _line("São filhos do primo pobre", 64, 145, x1=170),
            _line("7 A parcela do silêncio", 40, 157, x1=150),
            _line("A respeito do texto, julgue os itens seguintes.", 28, 175, x1=233),
            _line("**1** O texto é poético.", 28, 190, x1=150),
            _line("**2** O texto é narrativo.", 28, 205, x1=150),
        ]
    )
    body = cebraspe.segment([page]).passages[0].body_md
    assert body.startswith(
        "**Texto para os itens de 1 a 2**\n\n**Pavio do destino**\n\nSérgio Sampaio\n\n"
        "O bandido e o mocinho"
    )


def test_premises_one_per_line() -> None:
    """PF 2009 escrivão, itens 80 e 81: as premissas, uma por linha no PDF, ficam uma por linha;
    a frase que vem depois da lista abre outro parágrafo. Emenda (33) da 0020."""
    page = _page(
        [
            _line("Julgue os itens a seguir.", 28, 40),
            _line("**1** Considere que as proposições da sequência a seguir sejam", 28, 55),
            _line("verdadeiras.", 46, 67, x1=95),
            _line("Se Fred é policial, então ele tem porte de arma.", 46, 79, x1=240),
            _line("Fred mora em São Paulo ou ele é engenheiro.", 46, 91, x1=230),
            _line("Se Fred mora em São Paulo, então ele é policial.", 46, 103, x1=290),
            _line("Fred não tem porte de arma.", 46, 115, x1=170),
            _line("Nesse caso, é correto inferir que Fred não mora em São", 46, 127),
            _line("Paulo.", 46, 139, x1=80),
            _line("**2** Uma frase só. Outra frase que continua na linha de", 28, 155),
            _line("baixo. E mais uma frase inteira que termina aqui.", 46, 167),
            _line("Fim.", 46, 179, x1=70),
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert questions[0].statement_md == (
        "Julgue os itens a seguir.\n\n"
        "Considere que as proposições da sequência a seguir sejam verdadeiras.\n\n"
        "Se Fred é policial, então ele tem porte de arma.\\\n"
        "Fred mora em São Paulo ou ele é engenheiro.\\\n"
        "Se Fred mora em São Paulo, então ele é policial.\\\n"
        "Fred não tem porte de arma.\n\n"
        "Nesse caso, é correto inferir que Fred não mora em São Paulo."
    )
    assert "\\\n" not in questions[1].statement_md


def test_command_about_the_text_without_passage_goes_to_review() -> None:
    """Comando "Ainda com relação ao texto, julgue" sem texto-base: o texto ficou de fora. "O formato do
    texto às correspondências oficiais" é o gênero e não conta. Emenda (33) da 0020."""
    page = _page(
        [
            _line("Ainda com relação ao texto, julgue os itens seguintes.", 28, 40),
            _line("**1** A proposição é verdadeira.", 28, 55, x1=190),
            _line("Julgue os itens a seguir, referentes à adequação do formato do", 28, 70),
            _line("texto às correspondências oficiais.", 28, 82, x1=200),
            _line("**2** O aviso é expedido por ministro.", 28, 97, x1=220),
        ]
    )
    questions = cebraspe.segment([page]).questions
    assert "missing_passage" in questions[0].flags
    assert "missing_passage" not in questions[1].flags
