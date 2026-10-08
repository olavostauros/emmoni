"""Hash de deduplicação e referências a assets (SPECIFICATION.md §5)."""

from ingest.content import asset_refs, statement_hash

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
