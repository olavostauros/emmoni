"""Conteúdo das questões em Markdown restrito (docs/content-format.md)."""

import hashlib
import re
import unicodedata
from collections.abc import Sequence

# ![texto alternativo](asset:<sha256>)
ASSET_REF = re.compile(r"!\[([^\]]*)\]\(asset:([0-9a-f]{64})\)")


def asset_refs(md: str) -> list[str]:
    """sha256 dos assets referenciados, na ordem em que aparecem."""
    return [sha for _, sha in ASSET_REF.findall(md)]


def _normalize(md: str) -> str:
    text = unicodedata.normalize("NFC", md).lower()
    text = ASSET_REF.sub(lambda m: f" {m.group(2)} ", text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"</?u>", " ", text)
    text = re.sub(r"[\W_]+", " ", text)
    return " ".join(text.split())


def statement_hash(statement: str, options: Sequence[str] = (), passage: str | None = None) -> str:
    """sha256 da questão normalizada (SPECIFICATION.md §5), usado na deduplicação.

    Entram o enunciado, as alternativas em ordem e o texto-base: enunciados genéricos
    ("Assinale a alternativa correta", "De acordo com o texto, ...") se repetem entre questões
    diferentes. Normalização: NFC → minúsculas → sem acentos → sem markdown e pontuação →
    espaços colapsados. Uma imagem vale pelo seu sha256, não pelo texto alternativo.
    """
    parts = [_normalize(statement), *(_normalize(o) for o in options)]
    if passage is not None:
        parts.append(_normalize(passage))
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()
