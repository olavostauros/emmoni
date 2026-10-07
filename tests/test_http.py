"""Regras de cortesia do cliente HTTP (SPECIFICATIONS.md §7.1, §9). Nenhum teste usa a rede."""

from collections.abc import Callable

import httpx
import pytest

from ingest import sources
from ingest.crawlers.http import MIN_INTERVAL, CrawlError, HostBlocked, NotAllowed, PoliteClient

BASE = "https://www.cebraspe.org.br"
PDF = {"content-type": "application/pdf"}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


Handler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: Handler, robots: str = "") -> tuple[PoliteClient, list[str], FakeClock]:
    requested: list[str] = []
    clock = FakeClock()

    def transport(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        return handler(request)

    client = PoliteClient(
        sources.load(),
        "teste@emmoni.dev",
        transport=httpx.MockTransport(transport),
        clock=clock,
        sleep=clock.sleep,
    )
    return client, requested, clock


def ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=b"%PDF-1.7", headers=PDF)


def test_sources_file_is_valid() -> None:
    listed = sources.load()
    assert [s.slug for s in listed.sources] == ["cebraspe"]
    assert listed.is_denied("https://www.qconcursos.com/questoes")
    assert listed.is_denied("https://qconcursos.com/")
    assert not listed.is_denied("https://notqconcursos.com/")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.qconcursos.com/questoes-de-concursos",  # denylist
        "https://www.google.com/",  # fora da lista
        "https://www.cebraspe.org.br/outra-area/",  # host certo, prefixo errado
        "http://www.cebraspe.org.br/concursos/",  # sem https
    ],
)
def test_url_outside_allowlist_makes_no_request(url: str) -> None:
    client, requested, _ = make_client(ok)
    with pytest.raises(NotAllowed):
        client.get(url)
    assert requested == []


def test_robots_disallow_makes_no_request_to_the_url() -> None:
    client, requested, _ = make_client(ok, robots="User-agent: *\nDisallow: /concursos/privado/")
    with pytest.raises(NotAllowed, match="robots"):
        client.get(f"{BASE}/concursos/privado/x.pdf")
    assert requested == [f"{BASE}/robots.txt"]


def test_robots_is_cached_and_user_agent_has_contact() -> None:
    agents: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        agents.append(request.headers["user-agent"])
        return ok(request)

    client, requested, _ = make_client(handler)
    client.get(f"{BASE}/concursos/a.pdf")
    client.get(f"{BASE}/concursos/b.pdf")
    assert requested.count(f"{BASE}/robots.txt") == 1
    assert agents and all(a.startswith("emmoni-bot/") and "teste@emmoni.dev" in a for a in agents)


def test_rate_limit_one_request_per_second_per_host() -> None:
    client, requested, clock = make_client(ok)
    client.get(f"{BASE}/concursos/a.pdf")
    client.get(f"{BASE}/concursos/b.pdf")
    # robots, a, b: duas esperas de 1 s entre três requisições ao mesmo host.
    assert len(requested) == 3
    assert clock.slept == [MIN_INTERVAL, MIN_INTERVAL]


def test_crawl_delay_is_respected() -> None:
    client, _, clock = make_client(ok, robots="User-agent: *\nCrawl-delay: 5")
    client.get(f"{BASE}/concursos/a.pdf")
    client.get(f"{BASE}/concursos/b.pdf")
    assert clock.slept[-1] == 5


def test_403_blocks_host_for_the_run() -> None:
    client, requested, _ = make_client(lambda r: httpx.Response(403))
    with pytest.raises(HostBlocked):
        client.get(f"{BASE}/concursos/a.pdf")
    before = len(requested)
    with pytest.raises(HostBlocked):
        client.get(f"{BASE}/concursos/b.pdf")
    assert len(requested) == before
    assert client.blocked == {"www.cebraspe.org.br": "403"}


def test_captcha_blocks_host() -> None:
    page = b'<html><div class="g-recaptcha"></div></html>'
    client, _, _ = make_client(
        lambda r: httpx.Response(200, content=page, headers={"content-type": "text/html"})
    )
    with pytest.raises(HostBlocked, match="captcha"):
        client.get(f"{BASE}/concursos/")


def test_429_backs_off_with_retry_after_then_gives_up() -> None:
    client, requested, clock = make_client(
        lambda r: httpx.Response(429, headers={"retry-after": "7"})
    )
    with pytest.raises(CrawlError, match="3 tentativas"):
        client.get(f"{BASE}/concursos/a.pdf")
    assert requested.count(f"{BASE}/concursos/a.pdf") == 3
    assert clock.slept.count(7) == 2


def test_redirect_target_is_checked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://www.qconcursos.com/x.pdf"})

    client, requested, _ = make_client(handler)
    with pytest.raises(NotAllowed, match="denylist"):
        client.get(f"{BASE}/concursos/a.pdf")
    assert not any("qconcursos" in url for url in requested)


def test_redirect_inside_allowlist_is_followed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.cebraspe.org.br":
            return httpx.Response(301, headers={"location": "https://cdn.cebraspe.org.br/a.pdf"})
        return ok(request)

    client, _, _ = make_client(handler)
    response = client.get(f"{BASE}/concursos/a.pdf")
    assert response.url == "https://cdn.cebraspe.org.br/a.pdf"
    assert response.content == b"%PDF-1.7"


def test_conditional_request_and_not_modified() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["if-none-match"] == '"abc"'
        return httpx.Response(304, headers={"etag": '"abc"'})

    client, _, _ = make_client(handler)
    assert client.get(f"{BASE}/concursos/a.pdf", etag='"abc"').not_modified


def test_rejects_other_content_types_and_large_bodies() -> None:
    client, _, _ = make_client(
        lambda r: httpx.Response(200, content=b"x", headers={"content-type": "text/plain"})
    )
    with pytest.raises(CrawlError, match="não aceito"):
        client.get(f"{BASE}/concursos/a.txt")

    big = {"content-type": "application/pdf", "content-length": str(60 * 1024 * 1024)}
    client, _, _ = make_client(lambda r: httpx.Response(200, content=b"x", headers=big))
    with pytest.raises(CrawlError, match="limite"):
        client.get(f"{BASE}/concursos/a.pdf")


def test_placeholder_contact_is_refused() -> None:
    with pytest.raises(CrawlError, match="EMMONI_CRAWL_CONTACT"):
        PoliteClient(sources.load(), "contato@exemplo.com")


def test_extra_content_types_are_per_source() -> None:
    client, _, _ = make_client(
        lambda r: httpx.Response(200, content=b"[]", headers={"content-type": "application/json"})
    )
    response = client.get("https://apis.cebraspe.org.br/cebraspe/eventos/PF_21")
    assert response.content_type == "application/json"
