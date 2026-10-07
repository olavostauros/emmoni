"""Fontes permitidas e denylist (`ingest/sources.yaml`, SPECIFICATIONS.md §7.1)."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field

SOURCES_FILE = Path(__file__).with_name("sources.yaml")


class Recrawl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing: str
    contest_open: str
    contest_closed: str


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    kind: Literal["exam_board", "agency"]
    base_url: str
    allowed_prefixes: list[str] = Field(min_length=1)
    crawler: str
    js: bool = False
    max_depth: int = Field(ge=0)
    recrawl: Recrawl
    auto_approve: bool = False
    # Tipos além de PDF e HTML, para fontes cujo site carrega a lista por API (decisão 0004).
    extra_content_types: list[str] = []


class SourceList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[Source]
    denylist: list[str]

    def is_denied(self, url: str) -> bool:
        """Domínio da denylist ou subdomínio dele."""
        host = (urlsplit(url).hostname or "").lower()
        return any(host == domain or host.endswith("." + domain) for domain in self.denylist)

    def source_for(self, url: str) -> Source | None:
        """A fonte cujo prefixo permitido cobre `url`, ou None."""
        for source in self.sources:
            if any(url.startswith(prefix) for prefix in source.allowed_prefixes):
                return source
        return None


def load(path: Path = SOURCES_FILE) -> SourceList:
    return SourceList.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
