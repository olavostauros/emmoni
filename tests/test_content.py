"""Hash de deduplicação e referências a assets (SPECIFICATION.md §5)."""

from ingest.content import asset_refs, escape_md, normalize_md, statement_hash

SHA = "a" * 64
OTHER_SHA = "b" * 64


def test_hash_ignores_case_accents_punctuation_and_markdown() -> None:
    assert statement_hash("A **Polícia** Federal, órgão permanente.") == statement_hash(
        "a policia  federal orgao permanente"
    )
    assert statement_hash("O termo <u>ontem</u> é adjunto.") == statement_hash(
        "O termo ontem e adjunto"
    )


def test_hash_distinguishes_options_and_passage() -> None:
    stem = "Assinale a alternativa correta."
    assert statement_hash(stem, ["um", "dois"]) != statement_hash(stem, ["um", "três"])
    assert statement_hash(stem, ["um", "dois"]) != statement_hash(stem, ["dois", "um"])
    assert statement_hash(stem, passage="Texto 1") != statement_hash(stem, passage="Texto 2")
    assert statement_hash(stem) != statement_hash(stem, passage="")


def test_hash_uses_image_identity_not_alt_text() -> None:
    assert statement_hash(f"Veja ![figura](asset:{SHA}).") == statement_hash(
        f"Veja ![outra descrição](asset:{SHA})."
    )
    assert statement_hash(f"![x](asset:{SHA})") != statement_hash(f"![x](asset:{OTHER_SHA})")


def test_asset_refs_in_order() -> None:
    md = f"![a](asset:{OTHER_SHA}) texto ![b](asset:{SHA}) ![c](https://exemplo.com/x.png)"
    assert asset_refs(md) == [OTHER_SHA, SHA]


def test_escape_keeps_literal_text_literal() -> None:
    assert escape_md("R$ 10,00 e R$ 20,00") == r"R\$ 10,00 e R\$ 20,00"
    assert escape_md("Austrália* e nome_do_arquivo") == r"Austrália\* e nome\_do\_arquivo"
    assert escape_md(r"C:\Temp `x` <b>") == r"C:\\Temp \`x\` \<b>"
    assert escape_md("sem nada especial (A) 1.") == "sem nada especial (A) 1."


def test_escape_does_not_change_the_hash() -> None:
    text = "Pagou R$ 10,00 pelo arquivo_final.txt*"
    assert statement_hash(escape_md(text)) == statement_hash(text)


def test_normalize_md_nfc_and_ends() -> None:
    """Gravação: NFC e sem espaço nas pontas; o miolo (parágrafos) fica (docs/content-format.md)."""
    assert normalize_md("Texto 1A1-I.\n\nSegundo parágrafo.\n\n") == (
        "Texto 1A1-I.\n\nSegundo parágrafo."
    )
    assert normalize_md(" ac\u0327a\u0303o\u00a0") == "ação"
