"""Orquestração do crawling (SPECIFICATION.md §7.1, decisão 0007).

O crawler de cada fonte (`ingest/crawlers/<fonte>.py`) devolve o que **encontrou**: concursos com
seus documentos e provas candidatas. Este módulo cuida do que é comum a todas as fontes:

- `Fetcher`: acesso à rede pelo cliente de cortesia, com estado em `crawl.page` (`etag`,
  `last_modified`, `content_sha256`, `next_fetch_at`) e cache dos corpos em
  `data/crawl/<fonte>/<sha256>`; página que não venceu é relida do cache, sem rede;
- propostas em `ingest/manifests/_pending/<concurso>.yaml` (só reescritas quando mudam);
- sincronização de `crawl.discovered_document` com o estado dos manifestos (aprovado, rejeitado,
  proposto, pendente, fora do escopo) e um relatório da execução.

O crawler **nunca** baixa PDFs: a etapa `fetch` faz isso para manifestos aprovados.
"""

import datetime
import hashlib
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import psycopg
import yaml
from psycopg.types.json import Jsonb

from ingest import catalog as catalog_module
from ingest import manifest as manifest_module
from ingest import proposals
from ingest.catalog import Catalog
from ingest.crawlers.http import CrawlError, HostBlocked, NotAllowed, PoliteClient
from ingest.sources import Source

Conn = psycopg.Connection[tuple[object, ...]]
Policy = Literal["listing", "open", "closed"]
MAX_PAGES_PER_SOURCE = 2000
RETRY_AFTER_ERROR = datetime.timedelta(days=1)
KEY_KINDS = ("answer_key_preliminary", "answer_key_final")

# --- o que um crawler devolve ---------------------------------------------------------------------


@dataclass
class FoundDocument:
    url: str
    found_on_url: str
    link_text: str
    kind: str | None  # document_kind, ou None quando o tipo não serve/não foi reconhecido
    guessed: dict[str, Any] = field(default_factory=dict)  # campo → {value, confidence, rule}
    reason: str | None = None  # por que não entra numa proposta
    published_at: datetime.datetime | None = None


@dataclass
class ExamFound:
    slug: str
    name: str
    positions: list[str]
    documents: dict[str, FoundDocument]  # kind → documento ('exam' obrigatório)
    evidence: dict[str, Any] = field(default_factory=dict)
    # Gabaritos do mesmo tipo além do primeiro, na ordem dos itens (caderno único com um gabarito
    # por bloco, PCDF 2019; decisão 0012). O manifesto recebe a lista `[documents[k], *more[k]]`.
    more_keys: dict[str, list[FoundDocument]] = field(default_factory=dict)

    def all_documents(self) -> list[FoundDocument]:
        return [*self.documents.values(), *(d for docs in self.more_keys.values() for d in docs)]


ContestScope = Literal["in_scope", "candidate_agency", "out_of_scope"]


@dataclass
class ContestFound:
    url: str  # página do concurso na fonte (evidência; vira linha em discovered_document)
    found_on_url: str
    link_text: str
    name: str
    scope: ContestScope
    reason: str | None = None  # obrigatório fora do escopo e para órgão candidato
    agency: str | None = None  # slug do catálogo (in_scope)
    year: int | None = None
    slug_hint: str = ""  # desempate de slug quando órgão+ano colidem
    guessed: dict[str, Any] = field(default_factory=dict)
    documents: list[FoundDocument] = field(default_factory=list)
    exams: list[ExamFound] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(
        default_factory=list
    )  # provas sem cargo, documentos sem par
    note: str | None = None  # ex.: detalhe indisponível
    slug: str | None = None  # atribuído por `assign_slugs`


class Crawler(Protocol):
    def crawl(self, fetcher: "Fetcher", catalog: Catalog) -> list[ContestFound]: ...


# --- acesso à rede com estado --------------------------------------------------------------------


def parse_interval(text: str) -> datetime.timedelta | None:
    """'1d', '12h', '30m' ou 'never' (None)."""
    if text == "never":
        return None
    match = re.fullmatch(r"(\d+)([dhm])", text)
    if not match:
        raise ValueError(f"intervalo inválido: {text!r} (use 1d, 12h, 30m ou never)")
    amount, unit = int(match.group(1)), match.group(2)
    return datetime.timedelta(**{{"d": "days", "h": "hours", "m": "minutes"}[unit]: amount})


@dataclass
class _PageState:
    etag: str | None
    last_modified: str | None
    sha256: str | None
    next_fetch_at: datetime.datetime | None
    fetched: bool  # já foi buscada alguma vez
    http_status: int | None = None


class Fetcher:
    """Busca páginas de uma fonte respeitando `next_fetch_at`, com cache em disco."""

    def __init__(
        self,
        source: Source,
        conn: Conn,
        cache_dir: Path,
        client_factory: Callable[[], PoliteClient],
        *,
        now: Callable[[], datetime.datetime] | None = None,
        force: bool = False,
        log: Callable[[str], None] = print,
    ) -> None:
        self.source = source
        self.conn = conn
        self.cache_dir = cache_dir
        self._client_factory = client_factory
        self._client: PoliteClient | None = None
        self.now = now or (lambda: datetime.datetime.now(datetime.UTC))
        self.force = force
        self.log = log
        self.requests = 0
        self.from_cache = 0
        self.errors: list[str] = []
        self.blocked: dict[str, str] = {}

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _client_or_open(self) -> PoliteClient:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def get(self, url: str, policy: Policy, depth: int = 0) -> bytes | None:
        """Corpo da página (rede ou cache) ou None se não pôde ser obtida."""
        if depth > self.source.max_depth:
            self.errors.append(f"{url}: profundidade {depth} acima de max_depth")
            return None
        state = self._state(url)
        due = self.force or not state.fetched or self._is_due(state)
        cached = self._cached(state.sha256)
        if not due:
            if cached is not None:
                self.from_cache += 1
                return cached
            if state.http_status != 200:
                return None  # erro recente: espera o next_fetch_at
            # Tinha corpo (200) e o cache sumiu: busca de novo.
        if self.requests >= MAX_PAGES_PER_SOURCE:
            self.errors.append(f"{url}: limite de {MAX_PAGES_PER_SOURCE} páginas por execução")
            return cached
        return self._fetch(url, policy, state, cached)

    def _is_due(self, state: _PageState) -> bool:
        return state.next_fetch_at is not None and state.next_fetch_at <= self.now()

    def _fetch(
        self, url: str, policy: Policy, state: _PageState, cached: bytes | None
    ) -> bytes | None:
        # Erro de configuração (contato do User-Agent) aborta a execução: não é erro da página e
        # não pode gastar o `next_fetch_at` dela.
        client = self._client_or_open()
        self.requests += 1
        try:
            response = client.get(
                url,
                etag=state.etag if cached is not None else None,
                last_modified=state.last_modified if cached is not None else None,
            )
        except HostBlocked as error:
            host = url.split("/")[2]
            self.blocked[host] = str(error)
            self.errors.append(str(error))
            return cached
        except NotAllowed as error:
            self.errors.append(str(error))
            return cached
        except CrawlError as error:
            self.errors.append(str(error))
            self._record(url, _http_status(str(error)), state, self.now() + RETRY_AFTER_ERROR)
            return cached
        next_at = self._next(policy)
        if response.not_modified and cached is not None:
            self._record(url, 304, state, next_at)
            self.from_cache += 1
            return cached
        sha = hashlib.sha256(response.content).hexdigest()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / sha).write_bytes(response.content)
        state.etag, state.last_modified, state.sha256 = response.etag, response.last_modified, sha
        self._record(url, 200, state, next_at)
        return response.content

    def _next(self, policy: Policy) -> datetime.datetime | None:
        recrawl = self.source.recrawl
        text = {
            "listing": recrawl.listing,
            "open": recrawl.contest_open,
            "closed": recrawl.contest_closed,
        }
        interval = parse_interval(text[policy])
        return None if interval is None else self.now() + interval

    def _cached(self, sha256: str | None) -> bytes | None:
        if not sha256:
            return None
        path = self.cache_dir / sha256
        return path.read_bytes() if path.exists() else None

    def _state(self, url: str) -> _PageState:
        row = self.conn.execute(
            "select etag, last_modified, content_sha256, next_fetch_at, last_fetched_at, http_status"
            " from crawl.page where url = %s",
            (url,),
        ).fetchone()
        if row is None:
            return _PageState(None, None, None, None, fetched=False)
        etag, last_modified, sha, next_at, last_at, status = row
        return _PageState(
            str(etag) if etag else None,
            str(last_modified) if last_modified else None,
            str(sha) if sha else None,
            next_at if isinstance(next_at, datetime.datetime) else None,
            fetched=last_at is not None,
            http_status=int(str(status)) if status is not None else None,
        )

    def _record(
        self, url: str, status: int | None, state: _PageState, next_at: datetime.datetime | None
    ) -> None:
        self.conn.execute(
            """insert into crawl.page
                 (url, source_slug, last_fetched_at, http_status, etag, last_modified,
                  content_sha256, next_fetch_at)
               values (%s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (url) do update
                 set last_fetched_at = excluded.last_fetched_at,
                     http_status = excluded.http_status,
                     etag = excluded.etag,
                     last_modified = excluded.last_modified,
                     content_sha256 = excluded.content_sha256,
                     next_fetch_at = excluded.next_fetch_at""",
            (
                url,
                self.source.slug,
                self.now(),
                status,
                state.etag,
                state.last_modified,
                state.sha256,
                next_at,
            ),
        )


def _http_status(message: str) -> int | None:
    match = re.search(r"HTTP (\d{3})|: (\d{3}) após", message)
    if not match:
        return None
    return int(match.group(1) or match.group(2))


# --- slugs ----------------------------------------------------------------------------------------


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def assign_slugs(contests: list[ContestFound]) -> None:
    """`<órgão>-<ano>`; quando dois concursos colidem, acrescenta o `slug_hint` de cada um."""
    in_scope = [c for c in contests if c.scope == "in_scope" and c.agency and c.year]
    base = {id(c): f"{c.agency}-{c.year}" for c in in_scope}
    counts: dict[str, int] = {}
    for value in base.values():
        counts[value] = counts.get(value, 0) + 1
    seen: set[str] = set()
    for index, contest in enumerate(in_scope):
        slug = base[id(contest)]
        if counts[slug] > 1 and contest.slug_hint:
            slug = f"{slug}-{slugify(contest.slug_hint)}"
        if slug in seen:
            slug = f"{slug}-{index}"
        seen.add(slug)
        contest.slug = slug


# --- execução de uma fonte ------------------------------------------------------------------------


@dataclass
class Report:
    source: str
    requests: int = 0
    from_cache: int = 0
    contests_seen: int = 0
    out_of_scope: int = 0
    candidate_agencies: dict[str, list[str]] = field(default_factory=dict)  # prefixo → eventos
    approved: dict[str, tuple[int, int, list[str]]] = field(default_factory=dict)
    # slug → (documentos do manifesto encontrados, total no manifesto, documentos novos)
    rejected: list[str] = field(default_factory=list)
    proposed: dict[str, str] = field(default_factory=dict)  # slug → nova | atualizada | sem mudança
    without_proposal: dict[str, str] = field(default_factory=dict)  # slug → motivo
    removed: dict[str, str] = field(default_factory=dict)  # proposta apagada de _pending → motivo
    errors: list[str] = field(default_factory=list)
    blocked: dict[str, str] = field(default_factory=dict)

    def lines(self) -> list[str]:
        out = [
            f"crawl {self.source}: {self.requests} requisição(ões), {self.from_cache} do cache,"
            f" {self.contests_seen} concursos vistos, {self.out_of_scope} fora do escopo"
        ]
        for slug, (found, total, new) in sorted(self.approved.items()):
            extra = f"; {len(new)} documento(s) novo(s) fora do manifesto" if new else ""
            out.append(
                f"  aprovado {slug}: {found}/{total} documentos do manifesto encontrados{extra}"
            )
            out.extend(f"    novo: {url}" for url in new)
        out.extend(f"  rejeitado {slug}: ignorado" for slug in self.rejected)
        for slug, what in sorted(self.proposed.items()):
            out.append(f"  proposta {slug}: {what}")
        for slug, why in sorted(self.without_proposal.items()):
            out.append(f"  sem proposta {slug}: {why}")
        for slug, why in sorted(self.removed.items()):
            out.append(f"  proposta removida {slug}: {why}")
        for prefix, events in sorted(self.candidate_agencies.items()):
            out.append(f"  órgão candidato ao catálogo {prefix}: {', '.join(events)}")
        out.extend(f"  host bloqueado {host}: {why}" for host, why in self.blocked.items())
        out.extend(f"  erro: {error}" for error in self.errors)
        return out


def run_source(
    source: Source,
    crawler: Crawler,
    catalog: Catalog,
    conn: Conn,
    *,
    data_dir: Path,
    manifests_dir: Path,
    client_factory: Callable[[], PoliteClient],
    now: Callable[[], datetime.datetime] | None = None,
    force: bool = False,
    log: Callable[[str], None] = print,
) -> Report:
    """Roda o crawler de uma fonte e sincroniza propostas e estado. Não faz commit."""
    fetcher = Fetcher(
        source,
        conn,
        data_dir / "crawl" / source.slug,
        client_factory,
        now=now,
        force=force,
        log=log,
    )
    try:
        contests = crawler.crawl(fetcher, catalog)
    finally:
        fetcher.close()
    assign_slugs(contests)
    report = Report(
        source.slug,
        requests=fetcher.requests,
        from_cache=fetcher.from_cache,
        contests_seen=len(contests),
        errors=list(fetcher.errors),
        blocked=dict(fetcher.blocked),
    )
    approved_urls = proposals.approved_documents(manifests_dir)
    ingested = _ingested_urls(conn)
    for contest in contests:
        _sync_contest(
            contest, catalog, conn, source, manifests_dir, approved_urls, ingested, report
        )
    _remove_stale_proposals(contests, source, manifests_dir, report)
    return report


def _remove_stale_proposals(
    contests: list[ContestFound], source: Source, manifests_dir: Path, report: Report
) -> None:
    """Apaga de `_pending/` a proposta que esta execução não refez (decisão 0012).

    Só vale para concurso **visto e lido** nesta execução: a regra mudou e ele deixou de render
    proposta, saiu do escopo ou mudou de slug. Concurso que sumiu da listagem, ou cujo detalhe
    falhou, mantém a proposta — falha de rede não apaga nada. O git guarda o arquivo apagado.
    """
    by_url = {c.url: c for c in contests}
    for path in proposals.list_pending(manifests_dir):
        try:
            pending = manifest_module.load(path)
        except (ValueError, OSError, yaml.YAMLError):
            continue  # proposta inválida: fica para quem aprova ver o erro
        if pending.evidence.get("source") != source.slug:
            continue
        contest = by_url.get(pending.source_url or "")
        if contest is None or contest.note:
            continue
        if contest.slug == path.stem and path.stem in report.proposed:
            continue
        if contest.scope != "in_scope":
            why = f"concurso fora do escopo: {contest.reason}"
        elif contest.slug != path.stem:
            why = f"concurso agora proposto como {contest.slug}"
        else:
            why = report.without_proposal.get(path.stem, "sem proposta nesta execução")
        path.unlink()
        report.removed[path.stem] = why


def _sync_contest(
    contest: ContestFound,
    catalog: Catalog,
    conn: Conn,
    source: Source,
    manifests_dir: Path,
    approved_urls: dict[str, tuple[str, str, str]],
    ingested: set[str],
    report: Report,
) -> None:
    if contest.scope == "out_of_scope":
        report.out_of_scope += 1
        _upsert(conn, source, contest, status="out_of_scope", reason=contest.reason)
        return
    if contest.scope == "candidate_agency":
        prefix = contest.slug_hint or "?"
        report.candidate_agencies.setdefault(prefix, []).append(contest.link_text)
        _upsert(conn, source, contest, status="pending", reason=contest.reason)
        return
    slug = contest.slug
    assert slug is not None
    if contest.note:
        report.errors.append(f"{slug}: {contest.note}")
    rejected = proposals.rejection(slug, manifests_dir)
    if rejected is not None:
        report.rejected.append(slug)
        reason = f"proposta rejeitada: {rejected}"
        _upsert(conn, source, contest, status="rejected", reason=reason)
        for doc in contest.documents:
            _upsert(conn, source, doc, status="rejected", reason=reason, contest_slug=slug)
        return
    if proposals.is_approved(slug, manifests_dir):
        _sync_approved(contest, slug, conn, source, approved_urls, ingested, report)
        return
    _upsert(conn, source, contest, status="pending", reason=None)
    proposable = [e for e in contest.exams if any(k in e.documents for k in KEY_KINDS)]
    if not proposable:
        why = contest.note or (
            "nenhuma prova objetiva com gabarito identificada"
            if not contest.exams
            else "provas sem gabarito"
        )
        report.without_proposal[slug] = why
        for doc in contest.documents:
            _upsert_document(conn, source, doc, slug, approved_urls, ingested, proposed=False)
        return
    manifest = proposals.build(contest, proposable, source.slug)
    problems = catalog_module.manifest_problems(catalog, manifest)
    if problems:
        report.without_proposal[slug] = "; ".join(problems)
        return
    report.proposed[slug] = proposals.write_pending(manifest, manifests_dir)
    _upsert(conn, source, contest, status="proposed", reason=None)
    proposed_urls = {doc.url for exam in proposable for doc in exam.all_documents()}
    for doc in contest.documents:
        _upsert_document(
            conn, source, doc, slug, approved_urls, ingested, proposed=doc.url in proposed_urls
        )


def _sync_approved(
    contest: ContestFound,
    slug: str,
    conn: Conn,
    source: Source,
    approved_urls: dict[str, tuple[str, str, str]],
    ingested: set[str],
    report: Report,
) -> None:
    in_manifest = {url for url, (c, _, _) in approved_urls.items() if c == slug}
    found = {doc.url for doc in contest.documents}
    # Só o que entraria numa proposta: prova com gabarito e cargo do catálogo. O resto (peritos,
    # editais, discursivas) fica em discovered_document com o motivo.
    new = sorted(
        {
            doc.url
            for exam in contest.exams
            for doc in exam.all_documents()
            if doc.url not in approved_urls
        }
    )
    report.approved[slug] = (len(in_manifest & found), len(in_manifest), new)
    _upsert(conn, source, contest, status="approved", reason=None)
    for doc in contest.documents:
        _upsert_document(conn, source, doc, slug, approved_urls, ingested, proposed=False)


def _upsert_document(
    conn: Conn,
    source: Source,
    doc: FoundDocument,
    contest_slug: str,
    approved_urls: dict[str, tuple[str, str, str]],
    ingested: set[str],
    *,
    proposed: bool,
) -> None:
    if doc.url in ingested:
        status, reason = "ingested", None
    elif doc.url in approved_urls:
        status, reason = "approved", None
    elif doc.kind is None:
        status, reason = "out_of_scope", doc.reason or "tipo não reconhecido"
    elif proposed:
        status, reason = "proposed", None
    else:
        status, reason = "pending", doc.reason
    _upsert(conn, source, doc, status=status, reason=reason, contest_slug=contest_slug)


def _upsert(
    conn: Conn,
    source: Source,
    item: ContestFound | FoundDocument,
    *,
    status: str,
    reason: str | None,
    contest_slug: str | None = None,
) -> None:
    kind = item.kind if isinstance(item, FoundDocument) else None
    slug = contest_slug if isinstance(item, FoundDocument) else item.slug
    conn.execute(
        """insert into crawl.discovered_document
             (url, source_slug, found_on_url, link_text, guessed_kind, guessed_contest_slug,
              guessed, status, status_reason)
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           on conflict (url) do update
             set found_on_url = excluded.found_on_url,
                 link_text = excluded.link_text,
                 guessed_kind = excluded.guessed_kind,
                 guessed_contest_slug = excluded.guessed_contest_slug,
                 guessed = excluded.guessed,
                 status = excluded.status,
                 status_reason = excluded.status_reason,
                 last_seen_at = now()""",
        (
            item.url,
            source.slug,
            item.found_on_url,
            item.link_text[:500],
            kind,
            slug,
            Jsonb(item.guessed),
            status,
            reason,
        ),
    )


def _ingested_urls(conn: Conn) -> set[str]:
    return {str(row[0]) for row in conn.execute("select url from source_document")}
