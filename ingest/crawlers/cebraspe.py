"""Crawler do Cebraspe (decisões 0004 e 0007).

O site de concursos é uma aplicação React; lemos a mesma API JSON que a página lê:

- listagem: `eventos/tipo/concursos/` → fases (`Novos`, `Inscrições Abertas`, `Em Andamento`,
  `Encerrados`) com os eventos (`eventoURL`, `eventoNomeAbreviado`, `eventoAno`);
- detalhe: `eventos/<eventoURL>` → `eventoCargos`, `arquivosEdital` e `arquivosGabarito`
  (a aba "Provas e gabaritos": provas objetivas, gabaritos, discursivas, orais...).

Só por regras, sem LLM: o órgão vem dos `aliases` do catálogo casados com o prefixo da URL do
evento; o tipo de cada arquivo vem da descrição; prova e gabarito se casam pelo rótulo, pelo nome
do arquivo ou pelo número do cargo; os cargos vêm de `eventoCargos` casados com o catálogo.
"""

import datetime
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from ingest.catalog import Agency, Catalog, Position
from ingest.crawl import (
    KEY_KINDS,
    ContestFound,
    ExamFound,
    Fetcher,
    FoundDocument,
    Policy,
    slugify,
)

LISTING_URL = "https://apis.cebraspe.org.br/cebraspe/eventos/tipo/concursos/"
EVENT_URL = "https://apis.cebraspe.org.br/cebraspe/eventos/{event}"
PAGE_URL = "https://www.cebraspe.org.br/concursos/{event}"
CDN_URL = "https://cdn.cebraspe.org.br/concursos/{event}/arquivos/{name}"
CDN_GUID_URL = "https://cdn.cebraspe.org.br/{name}"
CLOSED_PHASE = "Encerrados"

# Prefixos e palavras que sugerem órgão policial fora do catálogo (só para o relatório).
POLICE_PREFIXES = frozenset(
    [
        "PC",
        "PM",
        "CBM",
        "BM",
        "PP",
        "PPE",
        "PCDF",
        "PMDF",
        "CBMDF",
        "DEPEN",
        "SEAP",
        "SEJUS",
        "SEJUSP",
        "SAP",
        "SUSIPE",
        "SDS",
        "SESP",
        "SSP",
        "GM",
        "GCM",
        "PL",
    ]
)
POLICE_WORDS = frozenset(
    ["POLICIA", "POLICIAL", "BOMBEIRO", "BOMBEIROS", "PENAL", "PENITENCIARIO", "PENITENCIARIA"]
)


# --- modelos da API (campos extras são ignorados) --------------------------------------------------


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _Event(_Lenient):
    eventoURL: str
    eventoNomeAbreviado: str
    eventoNomeCompleto: str | None = None
    eventoAno: int | None = None


class _Phase(_Lenient):
    faseEvento: str
    eventos: list[_Event] = []


class _File(_Lenient):
    nomeArquivo: str
    descricaoArquivo: str = ""
    dataArquivoObj: datetime.datetime | None = None
    isGuid: bool = False


class _Cargo(_Lenient):
    idArea: str
    area: str


class _Detail(_Event):
    eventoCargos: list[_Cargo] | None = None
    arquivosEdital: list[_File] | None = None
    arquivosGabarito: list[_File] | None = None


_phases = TypeAdapter(list[_Phase])


# --- normalização ---------------------------------------------------------------------------------


def normalize(text: str) -> str:
    """Maiúsculas, sem acentos, travessões viram hífens, espaços colapsados."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    ascii_text = ascii_text.upper().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", ascii_text).strip()


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^A-Z0-9]+", normalize(text)) if t]


# --- escopo do evento -----------------------------------------------------------------------------


def _match_agency(
    url_tokens: list[str], name_tokens: list[str], catalog: Catalog
) -> tuple[Agency, str, int] | None:
    """(órgão, regra, quantos tokens da URL o alias consumiu)."""
    for agency in catalog.agencies:
        for alias in agency.aliases:
            parts = alias.upper().split("_")
            if url_tokens[: len(parts)] == parts:
                return agency, f"prefixo {alias} da URL do evento", len(parts)
            if name_tokens[: len(parts)] == parts:
                return agency, f"prefixo {alias} do nome do evento", 0
    return None


def _year(event: _Event, url_tokens: list[str]) -> int | None:
    if event.eventoAno and 1980 <= event.eventoAno <= 2100:
        return event.eventoAno
    for token in url_tokens:
        if re.fullmatch(r"\d{2}", token):
            return 2000 + int(token)
        if re.fullmatch(r"(19|20)\d{2}", token):
            return int(token)
    return None


def scope(event: _Event, catalog: Catalog) -> ContestFound:
    url_tokens = _tokens(event.eventoURL)
    name_tokens = _tokens(event.eventoNomeAbreviado)
    name = (event.eventoNomeCompleto or event.eventoNomeAbreviado).strip()
    contest = ContestFound(
        url=PAGE_URL.format(event=event.eventoURL),
        found_on_url=LISTING_URL,
        link_text=event.eventoNomeAbreviado.strip(),
        name=name,
        scope="out_of_scope",
        guessed={"event": event.eventoURL},
    )
    matched = _match_agency(url_tokens, name_tokens, catalog)
    year = _year(event, url_tokens)
    if "ADM" in url_tokens or "ADM" in name_tokens:
        contest.reason = "cargos administrativos (ADM no nome do evento)"
        return contest
    if matched is not None:
        agency, rule, consumed = matched
        if year is None:
            contest.reason = "sem ano identificável"
            return contest
        contest.scope = "in_scope"
        contest.agency = agency.slug
        contest.year = year
        contest.guessed["agency"] = {"value": agency.slug, "confidence": 1.0, "rule": rule}
        contest.guessed["year"] = {"value": year, "confidence": 1.0, "rule": "eventoAno"}
        rest = [t for t in url_tokens[consumed:] if not re.fullmatch(r"\d{2}|\d{4}", t)]
        contest.slug_hint = "-".join(rest)
        return contest
    prefix = url_tokens[0] if url_tokens else ""
    if prefix in POLICE_PREFIXES or POLICE_WORDS & set(name_tokens):
        contest.scope = "candidate_agency"
        contest.slug_hint = prefix
        contest.reason = (
            f"órgão policial fora do catálogo (prefixo {prefix}); inclua em db/catalog.yaml"
        )
        return contest
    contest.reason = "órgão não policial"
    return contest


# --- tipo de cada arquivo -------------------------------------------------------------------------

_NOT_CORE = (
    (
        ("CURSO DE FORMACAO", "CURSO DE INSTRUCAO", "CFP", "VERIFICACAO DE APRENDIZAGEM", "TURMA"),
        "curso de formação",
    ),
    (("SEM EFEITO",), "documento sem efeito"),
    (("PROVA ORAL", "ORAL "), "prova oral"),
    (("DISCURSIV", "PADRAO DE RESPOSTA", "REDACAO"), "prova discursiva"),
    (
        ("DIGITACAO", "CAPACIDADE FISICA", "TAF", "PRATICA", "TITULOS", "PSICOLOG", "TOXICOLOG"),
        "etapa não objetiva",
    ),
)
_FINAL = ("GABARITO DEFINITIVO", "GABARITOS DEFINITIVOS", "GABARITO OFICIAL DEFINITIVO")
_PRELIMINARY = (
    "GABARITO PRELIMINAR",
    "GABARITOS PRELIMINARES",
    "GABARITO OFICIAL PRELIMINAR",
    "GABARITOS OFICIAIS PRELIMINARES",
)


def classify_file(description: str, name: str) -> tuple[str | None, str]:
    """(tipo de documento ou None, regra/motivo)."""
    d = normalize(description)
    if d.startswith("EDITAL") or d.startswith("COMUNICADO"):
        return None, "edital ou comunicado na aba de provas"
    for markers, reason in _NOT_CORE:
        if any(m in f" {d} " for m in markers):
            return None, reason
    if any(m in d for m in _FINAL):
        return "answer_key_final", "descrição contém 'GABARITO DEFINITIVO'"
    preliminary = any(m in d for m in _PRELIMINARY)
    n = normalize(name)
    if n.startswith("GAB_PRELIMINAR") and not preliminary:
        # PCES 2022: descrição "PROVA OBJETIVA - ..." num arquivo GAB_PRELIMINAR_*.PDF.
        return "answer_key_preliminary", "nome do arquivo começa com GAB_PRELIMINAR"
    if n.startswith("GAB_DEFINITIVO"):
        return "answer_key_final", "nome do arquivo começa com GAB_DEFINITIVO"
    if preliminary and "PROVA OBJETIVA" in d and not d.startswith("GABARITO"):
        return "exam", "caderno de prova publicado junto com o gabarito preliminar"
    if preliminary:
        return "answer_key_preliminary", "descrição contém 'GABARITO PRELIMINAR'"
    if "PROVA OBJETIVA" in d or (d.startswith("PROVA") and "OBJETIVA" in d):
        return "exam", "descrição contém 'PROVA OBJETIVA'"
    if "CADERNO DE PROVA" in d:  # concursos de 2016–2017: 'Caderno de provas - Conhecimentos...'
        return "exam", "descrição contém 'CADERNO DE PROVAS'"
    if "GABARITO" in d:
        return None, "gabarito de tipo não reconhecido"
    if "PROVA" in d:
        return None, "prova de tipo não reconhecido"
    return None, "tipo não reconhecido"


_LABEL_NOISE = (
    *_FINAL,
    *_PRELIMINARY,
    "PROVA OBJETIVA",
    "CADERNO DE PROVAS",
    "CADERNO DE PROVA",
    "COM JUSTIFICATIVAS",
    "COM JUSTIFICATIVA",
)


def exam_label(description: str) -> str:
    """O que sobra da descrição sem o tipo: identifica a prova ('CARGO 2: AGENTE...')."""
    label = normalize(description)
    for noise in _LABEL_NOISE:
        label = label.replace(noise, " ")
    label = re.sub(r"\bE\s+(?=-|$)", " ", label)  # 'PROVA OBJETIVA (P1) E GABARITO...' → '(P1)'
    label = re.sub(r"\s*[-:]\s*", " - ", label)
    label = re.sub(r"\s+", " ", label).strip(" -")
    return label


def cargo_numbers(label: str) -> frozenset[int]:
    """'CARGO 12' → {12}; 'CARGOS 15, 16 E 17' → {15,16,17}; 'CARGOS DE 2 A 11' → 2..11."""
    numbers: set[int] = set()
    for match in re.finditer(r"\bCARGOS?\b(.*?)(?= - |/|\bAREA\b|$)", label):
        segment = match.group(1)
        span = re.search(r"DE (\d+) A (\d+)", segment)
        if span:
            numbers.update(range(int(span.group(1)), int(span.group(2)) + 1))
        else:
            numbers.update(int(n) for n in re.findall(r"\d+", segment))
    return frozenset(numbers)


def _scope_marker(label: str) -> str | None:
    if "BASICO" in label:
        return "basicos"
    if "ESPECIFICO" in label:
        return "especificos"
    return None


def _file_core(name: str) -> str:
    core = normalize(name).rsplit(".", 1)[0]
    for prefix in ("GAB_DEFINITIVO_", "GAB_PRELIMINAR_", "GABARITO_", "MATRIZ_", "P_"):
        core = core.removeprefix(prefix)
    return core if not re.fullmatch(r"[0-9A-F]{64}", core) else ""


def _file_match(exam_name: str, key_name: str) -> bool:
    exam_core, key_core = _file_core(exam_name), _file_core(key_name)
    if len(exam_core) < 6 or len(key_core) < 6:
        return False
    return key_core in exam_core or exam_core in key_core


# --- cargos ---------------------------------------------------------------------------------------


def _cargo_name(area: str) -> str:
    return re.sub(r"^\s*CARGO\s*\d*\s*:\s*", "", normalize(area)).strip()


def match_position(text: str, positions: list[Position]) -> tuple[Position, float, str] | None:
    """Cargo do catálogo citado em `text`: nome completo, apelido ou primeira palavra do nome."""
    haystack = normalize(text)
    for position in positions:
        if normalize(position.name) in haystack:
            return position, 1.0, f"nome do cargo '{position.name}' aparece em '{text.strip()}'"
    words = set(_tokens(haystack))
    for position in positions:
        for alias in position.aliases:
            alias_tokens = _tokens(alias)
            if alias_tokens and set(alias_tokens) <= words:
                return (
                    position,
                    0.9,
                    f"'{alias}' (apelido de '{position.name}') em '{text.strip()}'",
                )
    for position in positions:
        first = _tokens(position.name)[0]
        if len(first) >= 5 and first in words:
            return position, 0.8, f"'{first}' (de '{position.name}') aparece em '{text.strip()}'"
    return None


# Rótulo genérico de prova comum a todos os cargos: só o tipo de conhecimento, sem citar cargo
# ('CONHECIMENTOS GERAIS', 'CONHECIMENTOS BASICOS - BLOCO I - PARA TODOS OS CARGOS'). Rótulo que
# nomeia um grupo ('...PARA TODOS OS CARGOS DE PERITO') não é genérico.
_SHARED_LABEL = re.compile(
    r"^(CONHECIMENTOS (GERAIS|BASICOS|COMPLEMENTARES)( - BLOCO [IVX0-9]+)?( \(P\d\))?"
    r"( - )?( PARA TODOS OS CARGOS)?)?$"
)


def _is_shared_label(label: str) -> bool:
    return _SHARED_LABEL.fullmatch(label) is not None


@dataclass
class _Positions:
    slugs: list[str]
    unmatched: list[str]
    evidence: dict[str, Any]


def resolve_positions(label: str, cargos: dict[int, str], agency: Agency) -> _Positions:
    numbers = cargo_numbers(label)
    names = [_cargo_name(cargos[n]) for n in sorted(numbers) if n in cargos]
    rule = "cargos citados na descrição"
    if not names and label:
        found = match_position(label, agency.positions)
        if found:
            position, confidence, why = found
            return _Positions([position.slug], [], {"confidence": confidence, "rule": why})
    shared = False
    if not names and not numbers and len(cargos) == 1:
        names = [_cargo_name(next(iter(cargos.values())))]
        rule = "único cargo do concurso"
    elif not names and not numbers and len(cargos) > 1 and _is_shared_label(label):
        # 'CONHECIMENTOS GERAIS' sem cargo: prova comum a todos os cargos do concurso.
        names = [_cargo_name(area) for _, area in sorted(cargos.items())]
        rule = "prova sem cargo citado: todos os cargos do concurso que estão no catálogo"
        shared = True
    matched: list[tuple[Position, float, str]] = []
    unmatched: list[str] = []
    for name in names:
        found = match_position(name, agency.positions)
        if found and found[0].slug not in {m[0].slug for m in matched}:
            matched.append(found)
        elif not found:
            unmatched.append(name)
    if not matched and not unmatched and len(agency.positions) == 1:
        position = agency.positions[0]
        matched.append((position, 0.6, "único cargo do órgão no catálogo"))
        rule = "cargo não citado"
    evidence = {
        "confidence": min((m[1] for m in matched), default=0.0) * (0.7 if shared else 1.0),
        "rule": rule + "; " + "; ".join(m[2] for m in matched) if matched else rule,
    }
    return _Positions([m[0].slug for m in matched], unmatched, evidence)


# --- provas ---------------------------------------------------------------------------------------


def _exam_slug(label: str, positions: list[str]) -> str:
    if not label:
        return "objetiva"
    if len(positions) == 1 and re.fullmatch(r"CARGO \d+( - [^-]*)?", label):
        return positions[0]
    return slugify(label) or "objetiva"


def _latest(docs: list[FoundDocument]) -> FoundDocument:
    return max(
        docs,
        key=lambda d: (d.published_at or datetime.datetime.min.replace(tzinfo=datetime.UTC), d.url),
    )


def _pair(
    exam: FoundDocument, keys: list[FoundDocument], kind: str
) -> tuple[FoundDocument, str] | None:
    same_kind = [k for k in keys if k.kind == kind]
    exam_label_ = exam_label(exam.link_text)
    by_label = [k for k in same_kind if exam_label(k.link_text) == exam_label_]
    if by_label:
        return _latest(by_label), "mesmo rótulo na descrição"
    by_name = [k for k in same_kind if _file_match(_name(exam), _name(k))]
    if by_name:
        return _latest(by_name), "nome do arquivo"
    numbers = cargo_numbers(exam_label_)
    if numbers:
        by_cargo = [
            k
            for k in same_kind
            if cargo_numbers(exam_label(k.link_text)) == numbers
            and _scope_marker(exam_label(k.link_text)) == _scope_marker(exam_label_)
        ]
        if by_cargo:
            return _latest(by_cargo), "mesmo número de cargo"
    return None


def _name(doc: FoundDocument) -> str:
    return doc.url.rsplit("/", 1)[-1]


def pair_exams(contest: ContestFound, cargos: dict[int, str], agency: Agency) -> None:
    exams = [d for d in contest.documents if d.kind == "exam"]
    keys = [d for d in contest.documents if d.kind in KEY_KINDS]
    used_keys: set[str] = set()
    by_slug: dict[str, ExamFound] = {}
    for exam_doc in sorted(exams, key=lambda d: _name(d)):
        label = exam_label(exam_doc.link_text)
        positions = resolve_positions(label, cargos, agency)
        if not positions.slugs:
            why = (
                "cargo fora do catálogo: " + "; ".join(positions.unmatched)
                if positions.unmatched
                else "cargo não identificado"
            )
            exam_doc.reason = why
            contest.skipped.append(
                {"label": label or exam_doc.link_text, "url": exam_doc.url, "reason": why}
            )
            continue
        documents = {"exam": exam_doc}
        pairing: dict[str, str] = {}
        for kind in KEY_KINDS:
            paired = _pair(exam_doc, keys, kind)
            if paired:
                documents[kind], pairing[kind] = paired
                used_keys.add(paired[0].url)
        if not any(k in documents for k in KEY_KINDS):
            exam_doc.reason = "prova sem gabarito correspondente"
            contest.skipped.append({"label": label, "url": exam_doc.url, "reason": exam_doc.reason})
        slug = _exam_slug(label, positions.slugs)
        found = ExamFound(
            slug=slug,
            name=exam_doc.link_text,
            positions=positions.slugs,
            documents=documents,
            evidence={
                "positions": {"value": positions.slugs, **positions.evidence},
                "pairing": pairing,
            },
        )
        previous = by_slug.get(slug)
        if previous is not None:
            older, newer = sorted((previous, found), key=lambda e: _sort_key(e.documents["exam"]))
            older.documents[
                "exam"
            ].reason = f"substituída por documento mais recente ({_name(newer.documents['exam'])})"
            contest.skipped.append(
                {
                    "label": label,
                    "url": older.documents["exam"].url,
                    "reason": older.documents["exam"].reason,
                }
            )
            found = newer
        by_slug[slug] = found
    for key in keys:
        if key.url not in used_keys:
            key.reason = "gabarito sem prova correspondente"
            contest.skipped.append(
                {"label": exam_label(key.link_text), "url": key.url, "reason": key.reason}
            )
    contest.exams = [e for e in by_slug.values() if any(k in e.documents for k in KEY_KINDS)]


def _sort_key(doc: FoundDocument) -> tuple[datetime.datetime, str]:
    return (doc.published_at or datetime.datetime.min.replace(tzinfo=datetime.UTC), doc.url)


# --- detalhe de um concurso -----------------------------------------------------------------------


def _file_url(event: str, file: _File) -> str:
    if file.isGuid:
        return CDN_GUID_URL.format(name=file.nomeArquivo)
    return CDN_URL.format(event=event, name=file.nomeArquivo)


def _cargos(detail: _Detail) -> dict[int, str]:
    """Número do cargo → descrição ('Cargo 2: Agente de Polícia Federal')."""
    cargos: dict[int, str] = {}
    for index, cargo in enumerate(detail.eventoCargos or [], start=1):
        digits = re.search(r"\d+", cargo.idArea)
        cargos[int(digits.group()) if digits else index] = cargo.area
    return cargos


def collect(contest: ContestFound, detail: _Detail, agency: Agency) -> None:
    event = detail.eventoURL
    page = contest.url
    for file in detail.arquivosGabarito or []:
        kind, rule = classify_file(file.descricaoArquivo, file.nomeArquivo)
        contest.documents.append(
            FoundDocument(
                url=_file_url(event, file),
                found_on_url=page,
                link_text=file.descricaoArquivo.strip(),
                kind=kind,
                guessed={"kind": {"value": kind, "confidence": 1.0 if kind else 0.0, "rule": rule}},
                reason=None if kind else rule,
                published_at=_aware(file.dataArquivoObj),
            )
        )
    for file in detail.arquivosEdital or []:
        d = normalize(file.descricaoArquivo)
        is_pdf = file.nomeArquivo.lower().endswith(".pdf")
        if re.search(r"\bABERTURA\b", d) and d.startswith("EDITAL") and is_pdf:
            contest.documents.append(
                FoundDocument(
                    url=_file_url(event, file),
                    found_on_url=page,
                    link_text=file.descricaoArquivo.strip(),
                    kind="notice",
                    guessed={
                        "kind": {"value": "notice", "confidence": 1.0, "rule": "edital de abertura"}
                    },
                    reason="edital: não entra no manifesto",
                    published_at=_aware(file.dataArquivoObj),
                )
            )
    if detail.eventoNomeCompleto:
        contest.name = detail.eventoNomeCompleto.strip() or contest.name
    pair_exams(contest, _cargos(detail), agency)


def _aware(value: datetime.datetime | None) -> datetime.datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=datetime.UTC)


# --- ponto de entrada -----------------------------------------------------------------------------


class CebraspeCrawler:
    def crawl(self, fetcher: Fetcher, catalog: Catalog) -> list[ContestFound]:
        body = fetcher.get(LISTING_URL, "listing", depth=0)
        if body is None:
            return []
        try:
            phases = _phases.validate_json(body)
        except ValidationError as error:
            fetcher.errors.append(f"listagem do Cebraspe em formato inesperado: {error}")
            return []
        agencies = {a.slug: a for a in catalog.agencies}
        contests: list[ContestFound] = []
        for phase in phases:
            policy: Policy = "closed" if phase.faseEvento == CLOSED_PHASE else "open"
            for event in phase.eventos:
                contest = scope(event, catalog)
                contest.guessed["phase"] = phase.faseEvento
                contests.append(contest)
                if contest.scope != "in_scope":
                    continue
                detail_body = fetcher.get(EVENT_URL.format(event=event.eventoURL), policy, depth=1)
                if detail_body is None:
                    contest.note = "detalhe do concurso indisponível nesta execução"
                    continue
                try:
                    detail = _Detail.model_validate_json(detail_body)
                except ValidationError as error:
                    contest.note = f"detalhe em formato inesperado: {error}"
                    continue
                assert contest.agency is not None
                collect(contest, detail, agencies[contest.agency])
        return contests


crawler = CebraspeCrawler()
