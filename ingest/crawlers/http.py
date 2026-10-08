"""Cliente HTTP único com as regras de cortesia (SPECIFICATION.md §7.1).

Todo acesso à rede — crawler e etapa `fetch` — passa por aqui. Antes de cada requisição:
denylist, lista de fontes permitidas e `robots.txt`. Entre requisições ao mesmo host: no mínimo
1 s (ou o `Crawl-delay`, se maior). 403 ou captcha param o host até o fim da execução; não há
nenhuma tentativa de contornar bloqueio.
"""

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import version
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ingest.sources import SourceList

log = logging.getLogger(__name__)

MIN_INTERVAL = 1.0  # segundos entre requisições ao mesmo host
ROBOTS_TTL = 24 * 3600
MAX_BYTES = 50 * 1024 * 1024
MAX_ATTEMPTS = 3
MAX_REDIRECTS = 5
ALLOWED_TYPES = ("application/pdf", "text/html")
PLACEHOLDER_CONTACTS = {"", "contato@exemplo.com"}
CAPTCHA_MARKERS = (b"g-recaptcha", b"h-captcha", b"hcaptcha", b"cf-challenge", b"captcha-delivery")


class CrawlError(Exception):
    """Falha ao buscar uma URL."""


class NotAllowed(CrawlError):
    """URL fora das fontes permitidas, na denylist ou proibida pelo robots.txt. Nada foi pedido."""


class HostBlocked(CrawlError):
    """O host recusou (403, captcha). Paramos de acessá-lo nesta execução."""


@dataclass(frozen=True)
class Response:
    url: str
    status: int  # 200 ou 304
    content: bytes
    content_type: str
    etag: str | None
    last_modified: str | None

    @property
    def not_modified(self) -> bool:
        return self.status == 304


@dataclass
class _Robots:
    parser: RobotFileParser
    fetched_at: float


@dataclass
class PoliteClient:
    sources: SourceList
    contact: str
    transport: httpx.BaseTransport | None = None
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    blocked: dict[str, str] = field(default_factory=dict)  # host → motivo
    _last_request: dict[str, float] = field(default_factory=dict)
    _robots: dict[str, _Robots] = field(default_factory=dict)
    _http: httpx.Client = field(init=False)

    def __post_init__(self) -> None:
        if self.contact.strip() in PLACEHOLDER_CONTACTS:
            raise CrawlError("defina EMMONI_CRAWL_CONTACT com um contato real (vai no User-Agent)")
        self._http = httpx.Client(
            transport=self.transport,
            headers={"User-Agent": self.user_agent},
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,  # cada redirecionamento passa pelas mesmas checagens
            # Uma conexão por host: as requisições são sequenciais neste cliente.
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        )

    @classmethod
    def from_env(cls, sources: SourceList) -> "PoliteClient":
        return cls(sources, os.environ.get("EMMONI_CRAWL_CONTACT", ""))

    @property
    def user_agent(self) -> str:
        return f"emmoni-bot/{version('emmoni')} (+{self.contact})"

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "PoliteClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def check(self, url: str) -> None:
        """Levanta NotAllowed/HostBlocked se `url` não pode ser pedida. Pode buscar o robots.txt."""
        parts = urlsplit(url)
        if parts.scheme not in ("https", "http"):
            raise NotAllowed(f"só https: {url}")
        if self.sources.is_denied(url):
            raise NotAllowed(f"domínio na denylist: {url}")
        source = self.sources.source_for(url)
        if source is None:
            raise NotAllowed(f"fora das fontes permitidas (ingest/sources.yaml): {url}")
        if parts.scheme == "http" and not source.allow_http:
            raise NotAllowed(f"só https: {url}")
        host = parts.netloc.lower()
        if host in self.blocked:
            raise HostBlocked(f"{host} bloqueado nesta execução: {self.blocked[host]}")
        if not self._robots_for(parts.scheme, host).parser.can_fetch(self.user_agent, url):
            raise NotAllowed(f"proibida pelo robots.txt: {url}")

    def get(
        self, url: str, *, etag: str | None = None, last_modified: str | None = None
    ) -> Response:
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        for _ in range(MAX_REDIRECTS + 1):
            self.check(url)
            response = self._request(url, headers)
            if response.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, response.headers["location"])
                continue
            return self._accept(url, response)
        raise CrawlError(f"redirecionamentos demais: {url}")

    def _robots_for(self, scheme: str, host: str) -> _Robots:
        cached = self._robots.get(host)
        if cached and self.clock() - cached.fetched_at < ROBOTS_TTL:
            return cached
        parser = RobotFileParser()
        robots_url = f"{scheme}://{host}/robots.txt"
        response = self._request(robots_url, {})
        # RFC 9309: 4xx → sem restrições; 5xx ou falha → tudo proibido.
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        elif 400 <= response.status_code < 500:
            parser.parse([])
        else:
            parser.parse(["User-agent: *", "Disallow: /"])
        robots = _Robots(parser, self.clock())
        self._robots[host] = robots
        return robots

    def _interval(self, host: str) -> float:
        robots = self._robots.get(host)
        delay = robots.parser.crawl_delay(self.user_agent) if robots else None
        return max(MIN_INTERVAL, float(delay or 0))

    def _request(self, url: str, headers: dict[str, str]) -> httpx.Response:
        host = urlsplit(url).netloc.lower()
        for attempt in range(MAX_ATTEMPTS):
            last = self._last_request.get(host)
            if last is not None:
                wait = last + self._interval(host) - self.clock()
                if wait > 0:
                    self.sleep(wait)
            self._last_request[host] = self.clock()
            try:
                response = self._read(url, headers)
            except httpx.HTTPError as error:
                raise CrawlError(f"{url}: {error}") from error
            log.info("GET %s → %s", url, response.status_code)
            if response.status_code == 403 or _is_captcha(response):
                reason = "403" if response.status_code == 403 else "captcha"
                self.blocked[host] = reason
                log.warning("host %s bloqueado (%s); parando nesta execução", host, reason)
                raise HostBlocked(f"{host}: {reason} em {url}")
            if response.status_code not in (429, 503):
                return response
            if attempt + 1 < MAX_ATTEMPTS:
                self.sleep(_retry_after(response, attempt))
        raise CrawlError(f"{url}: {response.status_code} após {MAX_ATTEMPTS} tentativas")

    def _read(self, url: str, headers: dict[str, str]) -> httpx.Response:
        with self._http.stream("GET", url, headers=headers) as response:
            declared = int(response.headers.get("content-length") or 0)
            if declared > MAX_BYTES:
                raise CrawlError(f"{url}: {declared} bytes, acima do limite de {MAX_BYTES}")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise CrawlError(f"{url}: acima do limite de {MAX_BYTES} bytes")
            # O corpo já vem descomprimido: sem content-encoding para não decodificar de novo.
            kept = [
                (name, value)
                for name, value in response.headers.multi_items()
                if name.lower() not in ("content-encoding", "content-length", "transfer-encoding")
            ]
            return httpx.Response(
                response.status_code,
                headers=kept,
                content=bytes(body),
                request=response.request,
            )

    def _accept(self, url: str, response: httpx.Response) -> Response:
        etag = response.headers.get("etag")
        last_modified = response.headers.get("last-modified")
        if response.status_code == 304:
            return Response(url, 304, b"", "", etag, last_modified)
        if response.status_code != 200:
            raise CrawlError(f"{url}: HTTP {response.status_code}")
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        source = self.sources.source_for(url)
        extra = source.extra_content_types if source else []
        if content_type not in ALLOWED_TYPES and content_type not in extra:
            raise CrawlError(f"{url}: tipo {content_type!r} não aceito")
        return Response(url, 200, response.content, content_type, etag, last_modified)


def _is_captcha(response: httpx.Response) -> bool:
    if "text/html" not in response.headers.get("content-type", ""):
        return False
    head = response.content[:200_000].lower()
    return any(marker in head for marker in CAPTCHA_MARKERS)


def _retry_after(response: httpx.Response, attempt: int) -> float:
    value = response.headers.get("retry-after", "")
    if value.isdigit():
        return max(float(value), MIN_INTERVAL)
    return float(2 ** (attempt + 1))
