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
from ingest.crawlers.http import CrawlError, PoliteClient
from ingest.sources import Source
from tests.factories import scalar

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures/crawl/cebraspe"
# Manifestos aprovados cujo evento tem fixture: o crawler deve redescobri-los a partir dela.
MANUAL = sorted(
    path
    for path in manifest.MANIFESTS_DIR.glob("*.yaml")
    if (FIXTURES / f"{(manifest.load(path).source_url or '').rsplit('/', 1)[-1]}.json").exists()
)
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
        ("Caderno de provas - Conhecimentos Básicos - cargo 2: escrivão de polícia", "exam"),
        ("PROVA OBJETIVA (P1) - CARGO 2 - SEM EFEITO", None),
        ("PROVA OBJETIVA - CURSO DE INSTRUÇÃO", None),
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
        (
            "Caderno de provas - Conhecimentos Básicos - soldado combatente",
            "CONHECIMENTOS BASICOS - SOLDADO COMBATENTE",
        ),
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


def _agency(slug: str) -> catalog.Agency:
    found = catalog.agency_by_slug(catalog.load(), slug)
    assert found is not None
    return found


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Cargo 2: Soldado da Polícia Militar", ("soldado", 1.0)),
        ("Cargo 1: Aluno-Praça", ("soldado", 0.9)),  # apelido (decisão 0008)
        ("CARGO DE PRAÇA DA POLÍCIA MILITAR DO ESTADO DO PARÁ", ("soldado", 0.9)),
        ("Cargo 1: Cadete", ("oficial", 0.9)),
        ("Curso de Formação de Oficiais", ("oficial", 0.9)),
        ("Soldado Combatente", ("soldado", 0.8)),  # primeira palavra do nome
        ("Técnico de Enfermagem", None),
    ],
)
def test_match_position_uses_aliases(text: str, expected: tuple[str, float] | None) -> None:
    found = cebraspe.match_position(text, _agency("pmpa").positions)
    assert (found and (found[0].slug, found[1])) == expected


def test_shared_exam_goes_to_every_catalog_position() -> None:
    cargos = {
        1: "Cargo 1: Agente de Polícia",
        2: "Cargo 2: Escrivão de Polícia",
        3: "Cargo 3: Necrotomista",
    }
    shared = cebraspe.resolve_positions("CONHECIMENTOS GERAIS", cargos, _agency("pcse"))
    assert (shared.slugs, shared.unmatched) == (["agente", "escrivao"], ["NECROTOMISTA"])
    assert shared.evidence["confidence"] == pytest.approx(0.7)
    everyone = cebraspe.resolve_positions(
        "CONHECIMENTOS GERAIS PARA TODOS OS CARGOS", cargos, _agency("pcse")
    )
    assert everyone.slugs == ["agente", "escrivao"]
    # Rótulo que nomeia um grupo de cargos fora do catálogo não é "para todos".
    peritos = cebraspe.resolve_positions(
        "CONHECIMENTOS BASICOS PARA TODOS OS CARGOS DE PERITO CRIMINAL FEDERAL",
        {1: "Cargo 1: Delegado de Polícia Federal", 2: "Cargo 2: Perito Criminal Federal"},
        _agency("pf"),
    )
    assert peritos.slugs == []
    assert cebraspe.resolve_positions("TECNICO DE ENFERMAGEM", cargos, _agency("pcse")).slugs == []


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
        ("PC_PE_23", "PC PE 23", 2023, "in_scope", "pcpe"),  # decisão 0008
        ("PM_TO_20_QPE", "PMTO QPE 2020", 2020, "in_scope", "pmto"),
        ("CBMTO_21", "CBMTO 2021", 2021, "in_scope", "cbmto"),
        ("DEPEN_20", "DEPEN 20", 2020, "in_scope", "depen"),
        ("SDS_PE_16_CIVIL", "SDS/PE POLÍCIA CIVIL 2016", 2016, "in_scope", "pcpe"),  # 0012
        ("SDS_PE_16_CIENTIFICA", "SDS/PE Polícia Científica 2016", 2016, "candidate_agency", None),
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


def _by_exam(loaded: manifest.Manifest) -> dict[str, manifest.Exam]:
    return {e.documents.exam: e for e in loaded.exams}


def test_proposals_reproduce_the_manual_manifests(run: tuple[Runner, FakeSite, Path]) -> None:
    """Critério do M3: o crawler redescobre sozinho PF e PRF ingeridos no M2."""
    runner, _, manifests_dir = run
    report = runner()
    assert set(report.proposed) >= {path.stem for path in MANUAL}
    for path in MANUAL:
        proposed = manifest.load(manifests_dir / "_pending" / path.name)
        manual = manifest.load(path)
        proposed_exams, manual_exams = _by_exam(proposed), _by_exam(manual)
        # O manifesto curado pode excluir provas (PM/MA 2017: oficiais de saúde, decisão 0009),
        # nunca ter prova que o crawler não achou.
        assert set(manual_exams) <= set(proposed_exams), path.stem
        for url, exam in manual_exams.items():
            # O manifesto curado pode ter gabaritos a mais (DEPEN 2020: complementares de nível
            # superior, decisão 0009); o crawler acha ao menos um, e nunca um fora do manifesto.
            found = {
                kind: set(proposed_exams[url].documents.urls(kind))
                for kind in ("answer_key_preliminary", "answer_key_final")
            }
            assert any(found.values()), (path.stem, url)
            for kind, urls in found.items():
                assert urls <= set(exam.documents.urls(kind)), (path.stem, url, kind)
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
    # SDS/PE: só o concurso da PC-PE entra, pelo alias do evento (decisão 0012).
    assert report.candidate_agencies == {"SDS": ["SDS/PE Polícia Científica 2016"]}
    assert not any("SDS_PE_16_CIENTIFICA" in url for url in site.requested)
    pcpe2016 = manifest.load(manifests_dir / "_pending" / "pcpe-2016.yaml")
    assert {e.slug: e.positions for e in pcpe2016.exams}["delegado"] == ["delegado"]
    # Órgãos estaduais e polícia penal (decisão 0008): propostos a partir das fixtures.
    # Slugs com sufixo: PM_PA_23_CFO/CFP, CBM_PA_23_CFO/CFP e PM_SC_23_OFICIAL/SOLDADO colidem.
    assert {
        "pcgo-2016",
        "pmal-2017",
        "pmma-2017",
        "cbmto-2022",
        "pmpa-2023-cfp",
        "cbmpa-2023-cfp",
        "pcpe-2023",
        "pcse-2021",
        "pcal-2021",
        "depen-2020",
        "pmsc-2023-soldado",
        "pcce-2025",
    } <= set(report.proposed)
    assert "nenhuma prova" in report.without_proposal["pcal-2026"]  # só o edital até agora
    pcgo = manifest.load(manifests_dir / "_pending" / "pcgo-2016.yaml")  # 'Caderno de provas'
    assert len(pcgo.exams) == 6 and all(e.documents.answer_key_final for e in pcgo.exams)
    cbmto = manifest.load(manifests_dir / "_pending" / "cbmto-2022.yaml")  # cadete, aluno-praça
    assert {e.positions[0] for e in cbmto.exams} == {"oficial", "soldado"}
    pcse = manifest.load(manifests_dir / "_pending" / "pcse-2021.yaml")
    assert pcse.exam("conhecimentos-gerais").positions == ["agente", "escrivao"]
    pcpe = manifest.load(manifests_dir / "_pending" / "pcpe-2023.yaml")
    assert not any("sem-efeito" in e.slug for e in pcpe.exams)
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


def test_single_booklet_gets_one_answer_key_per_block(run: tuple[Runner, FakeSite, Path]) -> None:
    """PCDF 2019: caderno único, gabaritos de básicos e de específicos (decisão 0012)."""
    runner, _, manifests_dir = run
    runner()
    proposed = manifest.load(manifests_dir / "_pending" / "pcdf-2019.yaml")
    manual = manifest.load(manifest.MANIFESTS_DIR / "pcdf-2019.yaml")
    [exam] = proposed.exams
    assert exam.documents.urls("answer_key_final") == manual.exams[0].documents.urls(
        "answer_key_final"
    )  # básicos (CB1) antes de específicos
    assert (
        "um gabarito por bloco"
        in proposed.evidence["exams"]["objetiva"]["pairing"]["answer_key_final"]
    )
    assert not any("CB1" in item["url"] for item in proposed.evidence["skipped"])
    # Provas separadas por bloco (PCDF 2020) continuam com um gabarito cada.
    pcdf2020 = manifest.load(manifests_dir / "_pending" / "pcdf-2020.yaml")
    assert all(isinstance(e.documents.answer_key_final, str) for e in pcdf2020.exams)


def _write_pending(manifests_dir: Path, slug: str, event: str, source: str = "cebraspe") -> Path:
    path = manifests_dir / "_pending" / f"{slug}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://www.cebraspe.org.br/concursos/{event}"
    path.write_text(
        f"""contest: {slug}
name: proposta antiga
agency: pcal
exam_board: cebraspe
year: 2026
source_url: {url}
exams:
- slug: objetiva
  name: prova
  positions: [agente]
  documents: {{exam: {url}/p.pdf, answer_key_final: {url}/g.pdf}}
evidence: {{source: {source}}}
""",
        encoding="utf-8",
    )
    return path


def test_stale_proposals_are_removed(run: tuple[Runner, FakeSite, Path]) -> None:
    """Proposta que a regra atual não refaz sai de `_pending/` (decisão 0012)."""
    runner, _, manifests_dir = run
    no_exam = _write_pending(manifests_dir, "pcal-2026", "PC_AL_26")  # só edital na fonte
    renamed = _write_pending(manifests_dir, "pmpa-2023", "PM_PA_23_CFP")  # agora pmpa-2023-cfp
    unseen = _write_pending(manifests_dir, "pcxx-2020", "PC_XX_20")  # fora da listagem
    failed = _write_pending(manifests_dir, "pf-2014", "DPF_14_AGENTE")  # detalhe com erro 500
    other = _write_pending(manifests_dir, "pcal-2026-x", "PC_AL_26", source="outra")
    report = runner()
    assert not no_exam.exists() and not renamed.exists()
    assert "nenhuma prova" in report.removed["pcal-2026"]
    assert report.removed["pmpa-2023"] == "concurso agora proposto como pmpa-2023-cfp"
    assert unseen.exists() and failed.exists() and other.exists()  # outra fonte: não é dele
    assert set(report.removed) == {"pcal-2026", "pmpa-2023"}


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
        if slug != "pmma-2017":  # provas excluídas na curadoria aparecem como documentos novos
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


def test_placeholder_contact_aborts_before_touching_state(tx: Conn, tmp_path: Path) -> None:
    """Erro de configuração não é erro da página: nada é gravado em crawl.page."""
    site = FakeSite()

    def bad_client() -> PoliteClient:
        return PoliteClient(site.listed, "contato@exemplo.com", transport=httpx.MockTransport(site))

    with pytest.raises(CrawlError, match="EMMONI_CRAWL_CONTACT"):
        crawl.run_source(
            site.source,
            cebraspe.crawler,
            catalog.load(),
            tx,
            data_dir=tmp_path / "data",
            manifests_dir=tmp_path / "manifests",
            client_factory=bad_client,
            now=lambda: T0,
            log=lambda _: None,
        )
    assert scalar(tx, "select count(*) from crawl.page") == 0
    assert site.requested == []


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
    assert report.removed == {}
    assert report.proposed == {} and report.contests_seen == 0
    assert len([u for u in site.requested if "robots" not in u]) == 1
