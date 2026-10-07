"""Crawler do Cebraspe e orquestração do crawling (SPECIFICATIONS.md §7.1, §9; decisão 0007).

Nenhum teste acessa a rede: as respostas da API estão gravadas em `fixtures/crawl/cebraspe/`.
"""

import datetime
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import psycopg
import pytest

from ingest import catalog, crawl, manifest, sources
from ingest.crawlers import cebraspe
from ingest.crawlers.http import PoliteClient
from ingest.sources import Source
from tests.factories import scalar

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures/crawl/cebraspe"
MANUAL = sorted(manifest.MANIFESTS_DIR.glob("*.yaml"))
Conn = psycopg.Connection[tuple[object, ...]]
T0 = datetime.datetime(2026, 10, 7, 12, tzinfo=datetime.UTC)


# --- regras puras ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("description", "kind"),
    [
        ("PROVA OBJETIVA - CARGO 2: AGENTE DE POLÍCIA FEDERAL", "exam"),
        ("PROVA OBJETIVA – CONHECIMENTOS ESPECÍFICOS – CARGO 17", "exam"),
        ("PROVA OBJETIVA (P1) E GABARITO PRELIMINAR COM JUSTIFICATIVAS ", "exam"),
        ("GABARITO DEFINITIVO - CARGO 2: AGENTE DE POLÍCIA FEDERAL", "answer_key_final"),
        ("GABARITO DEFINITIVO – PROVA OBJETIVA (P1)", "answer_key_final"),
        ("GABARITO PRELIMINAR - PROVA OBJETIVA", "answer_key_preliminary"),
        ("GABARITOS OFICIAIS PRELIMINARES", "answer_key_preliminary"),
        ("1.ª PROVA OBJETIVA - CURSO DE FORMAÇÃO", None),
        ("GABARITO DEFINITIVO - CFP - 2ª TURMA - 1ª PROVA - CARGO 8", None),
        ("PROVA DE VERIFICAÇÃO DE APRENDIZAGEM - CURSO DE FORMAÇÃO PROFISSIONAL", None),
        ("PROVA ORAL – 04/02/2024 – MALOTE 1 – SUB JUDICE", None),
        ("PADRÃO DE RESPOSTA DEFINITIVO - PROVA DISCURSIVA - CARGO 14", None),
        ("PROVA DISCURSIVA - Delegado de Polícia Federal", None),
        ("PROVA DE DIGITAÇÃO - CARGO DE ESCRIVÃO", None),
        ("Edital nº 23 - Resultado provisório na prova de capacidade física", None),
    ],
)
def test_classify_file(description: str, kind: str | None) -> None:
    found, rule = cebraspe.classify_file(description, "x.pdf")
    assert found == kind
    assert rule


@pytest.mark.parametrize(
    ("description", "label"),
    [
        (
            "PROVA OBJETIVA - CARGO 2: AGENTE DE POLÍCIA FEDERAL",
            "CARGO 2 - AGENTE DE POLICIA FEDERAL",
        ),
        ("GABARITO DEFINITIVO - PROVA OBJETIVA - CARGO 12", "CARGO 12"),
        ("GABARITO DEFINITIVO – PROVA OBJETIVA (P1)", "(P1)"),
        ("PROVA OBJETIVA (P1) E GABARITO PRELIMINAR COM JUSTIFICATIVAS ", "(P1)"),
        ("PROVA OBJETIVA", ""),
        ("GABARITO DEFINITIVO - ITENS DE 9 A 120", "ITENS DE 9 A 120"),
    ],
)
def test_exam_label(description: str, label: str) -> None:
    assert cebraspe.exam_label(description) == label


@pytest.mark.parametrize(
    ("label", "numbers"),
    [
        ("CARGO 12", {12}),
        ("CONHECIMENTOS BASICOS - BLOCO I - PARA OS CARGOS 15, 16 E 17", {15, 16, 17}),
        ("CONHECIMENTOS BASICOS PARA OS CARGOS DE 2 A 11", set(range(2, 12))),
        ("CONHECIMENTOS ESPECIFICOS - CARGO 11/AREA 14", {11}),
        ("CONHECIMENTOS ESPECIFICOS - CARGO 4 - AREA 3", {4}),
        ("ITENS DE 9 A 120", set()),
    ],
)
def test_cargo_numbers(label: str, numbers: set[int]) -> None:
    assert cebraspe.cargo_numbers(label) == frozenset(numbers)


def _event(url: str, name: str, year: int | None = None) -> cebraspe._Event:
    return cebraspe._Event(eventoURL=url, eventoNomeAbreviado=name, eventoAno=year)


@pytest.mark.parametrize(
    ("url", "name", "year", "scope", "agency"),
    [
        ("PF_21", "PF 2021", 2021, "in_scope", "pf"),
        ("DPF_14_AGENTE", "DPF 2014 AGENTE", 2014, "in_scope", "pf"),
        ("PRF_18", "PRF 2018", 2018, "in_scope", "prf"),
        ("PC_DF_20_AGENTE", "PC_DF_20_AGENTE", 2020, "in_scope", "pcdf"),
        ("PF_25_ADM", "PF 25 ADM", 2025, "out_of_scope", None),  # cargos administrativos
        ("PC_PE_26", "PC PE 26", 2026, "candidate_agency", None),
        ("SDS_PE_16_CIVIL", "SDS/PE POLÍCIA CIVIL 2016", 2016, "candidate_agency", None),
        ("TJ_CE_25_NOTARIOS", "TJ CE 25 NOTÁRIOS", 2025, "out_of_scope", None),
        ("PRF_XX", "PRF sem ano", None, "out_of_scope", None),
    ],
)
def test_scope_rules(url: str, name: str, year: int | None, scope: str, agency: str | None) -> None:
    contest = cebraspe.scope(_event(url, name, year), catalog.load())
    assert contest.scope == scope
    assert contest.agency == agency
    assert contest.scope == "in_scope" or contest.reason


def test_year_falls_back_to_url_token() -> None:
    contest = cebraspe.scope(_event("PF_21", "PF", None), catalog.load())
    assert (contest.scope, contest.year) == ("in_scope", 2021)


def test_assign_slugs_resolves_collisions() -> None:
    known = catalog.load()
    contests = [
        cebraspe.scope(_event(url, url, year), known)
        for url, year in (
            ("PF_20_QPE", 2020),
            ("PF_20_QPPM", 2020),
            ("PF_21", 2021),
            ("PRF_20", 2020),
        )
    ]
    crawl.assign_slugs(contests)
    assert [c.slug for c in contests] == ["pf-2020-qpe", "pf-2020-qppm", "pf-2021", "prf-2020"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("1d", datetime.timedelta(days=1)), ("12h", datetime.timedelta(hours=12)), ("never", None)],
)
def test_parse_interval(text: str, expected: datetime.timedelta | None) -> None:
    assert crawl.parse_interval(text) == expected
    with pytest.raises(ValueError):
        crawl.parse_interval("sempre")


# --- execução sobre as fixtures (banco de testes) -------------------------------------------------


@pytest.fixture
def tx(ingest: Conn) -> Iterator[Conn]:
    yield ingest
    ingest.rollback()


class FakeSite:
    """Serve as fixtures como se fosse a API do Cebraspe; concurso sem fixture responde 500."""

    def __init__(self, listing_status: int = 200) -> None:
        self.requested: list[str] = []
        self.listing_status = listing_status
        self.listed = sources.load()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requested.append(str(request.url))
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="")
        if path == "/cebraspe/eventos/tipo/concursos/":
            return self._json(FIXTURES / "listing.json", self.listing_status)
        if path.startswith("/cebraspe/eventos/"):
            return self._json(FIXTURES / f"{path.rsplit('/', 1)[-1]}.json")
        return httpx.Response(404)

    @staticmethod
    def _json(path: Path, status: int = 200) -> httpx.Response:
        if status != 200 or not path.exists():
            return httpx.Response(status if status != 200 else 500)
        return httpx.Response(
            200, content=path.read_bytes(), headers={"content-type": "application/json"}
        )

    def client(self) -> PoliteClient:
        return PoliteClient(
            self.listed,
            "teste@emmoni.dev",
            transport=httpx.MockTransport(self),
            sleep=lambda _: None,
        )

    @property
    def source(self) -> Source:
        return self.listed.sources[0]


Runner = Callable[..., crawl.Report]


@pytest.fixture
def run(tx: Conn, tmp_path: Path) -> tuple[Runner, FakeSite, Path]:
    site = FakeSite()
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    clock = {"now": T0}

    def runner(*, with_manual: bool = False, at: datetime.datetime | None = None) -> crawl.Report:
        if with_manual:
            for path in MANUAL:
                shutil.copy(path, manifests_dir / path.name)
        clock["now"] = at or clock["now"]
        return crawl.run_source(
            site.source,
            cebraspe.crawler,
            catalog.load(),
            tx,
            data_dir=tmp_path / "data",
            manifests_dir=manifests_dir,
            client_factory=site.client,
            now=lambda: clock["now"],
            log=lambda _: None,
        )

    return runner, site, manifests_dir


def _pairs(loaded: manifest.Manifest) -> set[tuple[str, str | None, str | None]]:
    return {
        (e.documents.exam, e.documents.answer_key_final, e.documents.answer_key_preliminary)
        for e in loaded.exams
    }


def test_proposals_reproduce_the_manual_manifests(run: tuple[Runner, FakeSite, Path]) -> None:
    """Critério do M3: o crawler redescobre sozinho PF e PRF ingeridos no M2."""
    runner, _, manifests_dir = run
    report = runner()
    assert set(report.proposed) >= {path.stem for path in MANUAL}
    for path in MANUAL:
        proposed = manifest.load(manifests_dir / "_pending" / path.name)
        manual = manifest.load(path)
        assert _pairs(proposed) == _pairs(manual), path.stem
        assert (proposed.agency, proposed.year) == (manual.agency, manual.year)
        assert {e.slug for e in proposed.exams if not e.positions} == set()


def test_proposes_new_police_contests_and_reports_candidates(
    run: tuple[Runner, FakeSite, Path], tx: Conn
) -> None:
    runner, site, manifests_dir = run
    report = runner()
    # PCDF entrou no catálogo (decisão 0007): três concursos novos propostos.
    assert {"pcdf-2019", "pcdf-2020", "pcdf-2026"} <= set(report.proposed)
    pcdf = manifest.load(manifests_dir / "_pending" / "pcdf-2020.yaml")
    assert [e.positions for e in pcdf.exams] == [["agente"], ["agente"]]
    assert pcdf.evidence["contest"]["agency"]["rule"] == "prefixo PC_DF da URL do evento"
    # Órgãos policiais fora do catálogo só vão para o relatório; o detalhe não é buscado.
    assert {"PC", "PM", "CBM", "DEPEN"} <= set(report.candidate_agencies)
    assert not any("PC_PE_26" in url for url in site.requested)
    # Fora do escopo: cargos administrativos e órgãos não policiais, com motivo gravado.
    reason = scalar(
        tx,
        "select status_reason from crawl.discovered_document where url = %s",
        ("https://www.cebraspe.org.br/concursos/PF_25_ADM",),
    )
    assert "administrativos" in str(reason)
    assert report.out_of_scope >= 5
    # DPF 2014: a API responde 500 → sem proposta, erro visível, nova tentativa agendada.
    assert "pf-2014" in report.without_proposal
    assert any("DPF_14_AGENTE" in error and "500" in error for error in report.errors)
    next_at = scalar(
        tx,
        "select next_fetch_at from crawl.page where url like '%%DPF_14_AGENTE'",
    )
    assert next_at == T0 + crawl.RETRY_AFTER_ERROR


def test_skipped_exams_keep_their_reason(run: tuple[Runner, FakeSite, Path], tx: Conn) -> None:
    runner, _, _ = run
    runner()
    rows = tx.execute(
        """select url, status, status_reason from crawl.discovered_document
            where guessed_contest_slug = 'pf-2018' and guessed_kind = 'exam' order by url"""
    ).fetchall()
    by_name = {str(url).rsplit("/", 1)[-1]: (status, reason) for url, status, reason in rows}
    assert by_name["MATRIZ_408_DGPPF012__PAG_9.PDF"] == ("proposed", None)  # agente
    status, reason = by_name["MATRIZ_408_DGPPF002__PAG_4.PDF"]  # perito, fora do catálogo
    assert status == "pending" and "fora do catálogo" in str(reason)
    oral = scalar(
        tx,
        "select status from crawl.discovered_document where url like '%%P_MALOTE01_DGPPF_ORAL.PDF'",
    )
    assert oral == "out_of_scope"


def test_approved_manifests_are_recognized_not_rewritten(
    run: tuple[Runner, FakeSite, Path], tx: Conn
) -> None:
    runner, _, manifests_dir = run
    before = {path.name: path.read_text() for path in MANUAL}
    report = runner(with_manual=True)
    assert set(report.approved) == {path.stem for path in MANUAL}
    for slug, (found, total, new) in report.approved.items():
        assert found == total, slug
        assert new == [], slug
    assert not (manifests_dir / "_pending" / "pf-2021.yaml").exists()
    assert {p.name: p.read_text() for p in manifests_dir.glob("*.yaml")} == before
    status = scalar(
        tx,
        "select status from crawl.discovered_document where url = %s",
        (manifest.load(MANUAL[0]).exams[0].documents.exam,),
    )
    assert status == "approved"


def test_second_run_is_idempotent_and_offline(run: tuple[Runner, FakeSite, Path], tx: Conn) -> None:
    runner, site, manifests_dir = run
    runner()
    pending = {p.name: p.read_text() for p in (manifests_dir / "_pending").glob("*.yaml")}
    rows = scalar(tx, "select count(*) from crawl.discovered_document")
    requests_before = len(site.requested)
    report = runner()
    assert len(site.requested) == requests_before  # nada venceu: nem a listagem nem o erro
    assert set(report.proposed.values()) == {"sem mudança"}
    assert {p.name: p.read_text() for p in (manifests_dir / "_pending").glob("*.yaml")} == pending
    assert scalar(tx, "select count(*) from crawl.discovered_document") == rows


def test_recrawl_follows_the_source_policy(run: tuple[Runner, FakeSite, Path]) -> None:
    runner, site, _ = run
    runner()
    site.requested.clear()
    runner(at=T0 + datetime.timedelta(days=2))  # listagem (1d) e o erro (1d) venceram; 3d/never não
    fetched = {u.rsplit("/", 1)[-1] for u in site.requested if "robots" not in u}
    assert fetched == {"", "DPF_14_AGENTE"}  # "" = a listagem (termina em /)
    site.requested.clear()
    runner(at=T0 + datetime.timedelta(days=4))  # PF_25 está "Em Andamento": 3d
    fetched = {u.rsplit("/", 1)[-1] for u in site.requested if "eventos/" in u}
    assert "PF_25" in fetched
    assert "PF_21" not in fetched  # encerrado: never


def test_blocked_host_stops_without_proposals(tx: Conn, tmp_path: Path) -> None:
    site = FakeSite(listing_status=403)
    report = crawl.run_source(
        site.source,
        cebraspe.crawler,
        catalog.load(),
        tx,
        data_dir=tmp_path / "data",
        manifests_dir=tmp_path,
        client_factory=site.client,
        now=lambda: T0,
        log=lambda _: None,
    )
    assert "apis.cebraspe.org.br" in report.blocked
    assert report.proposed == {} and report.contests_seen == 0
    assert len([u for u in site.requested if "robots" not in u]) == 1
