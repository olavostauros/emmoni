"""Orquestração das etapas de ingestão de uma prova (SPECIFICATIONS.md §7.3).

Cada etapa lê e grava em `data/staging/<concurso>/<prova>/` e pode ser rerodada sozinha:

    fetch → extract → segment → answer-key → validate → classify → load

`classify` precisa de credencial da Claude API (ou das respostas já no cache); sem ela a etapa é
pulada com aviso e o `load` carrega as questões sem assunto (`draft`).
"""

import json
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from pydantic import TypeAdapter

from ingest import classify as classify_step
from ingest import db, fetch, taxonomy
from ingest.crawlers.http import PoliteClient
from ingest.extract import Page, extract
from ingest.load import DocumentIds, LoadReport, TopicAssignment, load_exam
from ingest.manifest import Exam, Manifest
from ingest.parsers import cebraspe
from ingest.sources import load as load_sources
from ingest.staging import AnswerKey, Segmented, write
from ingest.validate import Validated, validate

STEPS = ("fetch", "extract", "segment", "answer-key", "validate", "classify", "load")
PARSERS: dict[str, ModuleType] = {"cebraspe": cebraspe}
KEY_KINDS = ("answer_key_preliminary", "answer_key_final")

_pages = TypeAdapter(list[Page])


class ExamRun:
    def __init__(self, manifest: Manifest, exam: Exam, data: Path | None = None) -> None:
        self.manifest = manifest
        self.exam = exam
        self.data = data or fetch.data_dir()
        self.dir = self.data / "staging" / manifest.contest / exam.slug
        self.parser = PARSERS[manifest.exam_board]
        self.log: Callable[[str], None] = print

    # --- caminhos -------------------------------------------------------------------------------

    def path(self, name: str) -> Path:
        return self.dir / name

    def documents(self) -> dict[str, str]:
        docs = self.exam.documents
        found = {
            "exam": docs.exam,
            "answer_key_preliminary": docs.answer_key_preliminary,
            "answer_key_final": docs.answer_key_final,
        }
        return {kind: url for kind, url in found.items() if url}

    # --- etapas ---------------------------------------------------------------------------------

    def fetch(self) -> None:
        store = fetch.RawStore(self.data / "raw")
        client: PoliteClient | None = None
        recorded: dict[str, dict[str, object]] = {}
        try:
            with db.connect() as conn:
                for kind, url in self.documents().items():
                    if url not in store.index and client is None:
                        client = PoliteClient.from_env(load_sources())
                    doc = store.get(url, client)
                    doc_id = fetch.record(conn, kind, doc)
                    conn.commit()
                    recorded[kind] = {"url": url, "sha256": doc.sha256, "id": doc_id}
                    self.log(f"  fetch {kind}: {'baixado' if doc.downloaded else 'em disco'} {url}")
        finally:
            if client is not None:
                client.close()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path("documents.json").write_text(json.dumps(recorded, indent=1))

    def _documents_json(self) -> dict[str, dict[str, object]]:
        data: dict[str, dict[str, object]] = json.loads(self.path("documents.json").read_text())
        return data

    def _raw(self, kind: str) -> Path:
        return self.data / "raw" / f"{self._documents_json()[kind]['sha256']}.pdf"

    def extract(self) -> None:
        for kind in self._documents_json():
            pages = extract(self._raw(kind))
            self.path(f"pages.{kind}.json").write_bytes(_pages.dump_json(pages, indent=1))
            empty = [p.number for p in pages if not p.has_text]
            note = f" (sem texto: páginas {empty}; OCR ainda não implementado)" if empty else ""
            self.log(f"  extract {kind}: {len(pages)} páginas{note}")

    def _read_pages(self, kind: str) -> list[Page]:
        return _pages.validate_json(self.path(f"pages.{kind}.json").read_bytes())

    def segment(self) -> None:
        segmented: Segmented = self.parser.segment(
            self._read_pages("exam"), first=self.exam.first_number
        )
        write(self.path("segmented.json"), segmented)
        flagged = sum(1 for q in segmented.questions if q.flags)
        self.log(
            f"  segment: {len(segmented.questions)} questões, {len(segmented.passages)} textos-base,"
            f" {flagged} com pendências"
        )

    def answer_key(self) -> None:
        for kind in KEY_KINDS:
            if kind not in self._documents_json():
                continue
            key: AnswerKey = self.parser.parse_answer_key(self._read_pages(kind))
            write(self.path(f"{kind}.json"), key)
            annulled = [n for n, mark in key.answers.items() if mark == "X"]
            self.log(f"  answer-key {kind}: {len(key.answers)} itens, anulados {annulled}")

    def _key(self, kind: str) -> AnswerKey | None:
        path = self.path(f"{kind}.json")
        return AnswerKey.model_validate_json(path.read_bytes()) if path.exists() else None

    def validate(self) -> None:
        segmented = Segmented.model_validate_json(self.path("segmented.json").read_bytes())
        validated = validate(
            self.exam, segmented, self._key("answer_key_preliminary"), self._key("answer_key_final")
        )
        write(self.path("questions.json"), validated)
        review = sum(1 for q in validated.questions if q.review_reasons)
        self.log(f"  validate: {len(validated.questions)} questões, {review} para revisão")
        for reason in validated.exam_reasons:
            self.log(f"  ERRO na prova: {reason}")

    def classify(self) -> None:
        validated = Validated.model_validate_json(self.path("questions.json").read_bytes())
        subjects = {s.slug: s for s in taxonomy.load_dir(taxonomy.TAXONOMY_DIR)}
        cache = self.data / "staging" / "llm-cache"
        try:
            caller = classify_step.anthropic_caller() if _has_credentials() else None
            result = classify_step.classify(validated, subjects, cache, caller)
        except RuntimeError as error:
            self.log(f"  classify: pulado — {error}")
            return
        write(self.path("topics.json"), result)
        self.log(
            f"  classify: {len(result.topics)} classificadas, {len(result.review)} para revisão,"
            f" {len(result.suggestions)} sugestões de assunto ({result.model})"
        )

    def load(self) -> LoadReport:
        validated = Validated.model_validate_json(self.path("questions.json").read_bytes())
        docs = self._documents_json()

        def doc_id(kind: str) -> int | None:
            return int(str(docs[kind]["id"])) if kind in docs else None

        exam_doc = doc_id("exam")
        assert exam_doc is not None
        topics: dict[int, list[TopicAssignment]] = {}
        extra: dict[int, str] = {}
        topics_path = self.path("topics.json")
        if topics_path.exists():
            classified = classify_step.Classified.model_validate_json(topics_path.read_bytes())
            topics = {
                n: [TopicAssignment(t.path, t.origin, t.confidence) for t in assigned]
                for n, assigned in classified.topics.items()
            }
            extra = classified.review
        with db.connect() as conn:
            report = load_exam(
                conn,
                self.manifest,
                self.exam,
                DocumentIds(exam_doc, doc_id("answer_key_preliminary"), doc_id("answer_key_final")),
                validated,
                topics,
                extra,
            )
        self.log(
            f"  load: {report.questions} questões — {report.published} publicáveis,"
            f" {report.review} em revisão, {report.draft} sem assunto;"
            f" {report.duplicates} duplicatas, {report.removed} removidas"
        )
        return report

    def run(self, step: str | None = None) -> None:
        steps = {
            "fetch": self.fetch,
            "extract": self.extract,
            "segment": self.segment,
            "answer-key": self.answer_key,
            "validate": self.validate,
            "classify": self.classify,
            "load": self.load,
        }
        for name in [step] if step else STEPS:
            steps[name]()


def _has_credentials() -> bool:
    """Chave ou token da Claude API no ambiente (o SDK também aceita perfil do `ant auth login`)."""
    import os

    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
