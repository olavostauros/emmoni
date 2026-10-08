"""Propostas de manifesto do crawler e sua aprovação (SPECIFICATIONS.md §7.1, decisão 0007).

Três diretórios, três estados, tudo versionado no git:

- `ingest/manifests/_pending/<concurso>.yaml` — proposto pelo crawler; **o crawler é dono** do
  arquivo, o reescreve quando a fonte muda e o apaga quando o concurso deixa de render proposta
  (decisão 0012). Não edite: aprove e ajuste o aprovado.
- `ingest/manifests/<concurso>.yaml` — aprovado (`emmoni manifests approve`); curado à mão
  depois disso. O crawler nunca reescreve; documentos novos só aparecem no relatório.
- `ingest/manifests/_rejected/<concurso>.yaml` — rejeitado (`emmoni manifests reject`), com o
  motivo no bloco `rejected`; o crawler não volta a propor.
"""

import datetime
import getpass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from ingest import manifest as manifest_module
from ingest.manifest import MANIFESTS_DIR, Manifest

if TYPE_CHECKING:
    from ingest.crawl import ContestFound, ExamFound

PENDING = "_pending"
REJECTED = "_rejected"


class ProposalError(Exception):
    pass


# --- leitura do estado ----------------------------------------------------------------------------


def pending_path(slug: str, manifests_dir: Path = MANIFESTS_DIR) -> Path:
    return manifests_dir / PENDING / f"{slug}.yaml"


def is_approved(slug: str, manifests_dir: Path = MANIFESTS_DIR) -> bool:
    return (manifests_dir / f"{slug}.yaml").exists()


def rejection(slug: str, manifests_dir: Path = MANIFESTS_DIR) -> str | None:
    """Motivo da rejeição, ou None se o concurso não foi rejeitado."""
    path = manifests_dir / REJECTED / f"{slug}.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    block = data.get("rejected") or {}
    return str(block.get("reason") or "sem motivo registrado")


def list_pending(manifests_dir: Path = MANIFESTS_DIR) -> list[Path]:
    return sorted((manifests_dir / PENDING).glob("*.yaml"))


def approved_documents(manifests_dir: Path = MANIFESTS_DIR) -> dict[str, tuple[str, str, str]]:
    """URL → (concurso, prova, tipo) para todos os manifestos aprovados."""
    found: dict[str, tuple[str, str, str]] = {}
    for path in sorted(manifests_dir.glob("*.yaml")):
        loaded = manifest_module.load(path)
        for exam in loaded.exams:
            for kind in ("exam", "answer_key_preliminary", "answer_key_final"):
                for url in exam.documents.urls(kind):
                    found[url] = (loaded.contest, exam.slug, kind)
    return found


# --- construção e escrita -------------------------------------------------------------------------


def build(contest: "ContestFound", exams: list["ExamFound"], source_slug: str) -> Manifest:
    assert contest.slug and contest.agency and contest.year
    evidence_exams: dict[str, Any] = {}
    exam_entries = []
    for exam in exams:
        documents: dict[str, str | list[str]] = {
            kind: doc.url for kind, doc in exam.documents.items()
        }
        for kind, more in exam.more_keys.items():
            documents[kind] = [exam.documents[kind].url, *(doc.url for doc in more)]
        exam_entries.append(
            {
                "slug": exam.slug,
                "name": exam.name,
                "positions": list(exam.positions),
                "documents": documents,
            }
        )
        evidence_exams[exam.slug] = {
            **exam.evidence,
            "documents": {
                kind: {
                    "url": doc.url,
                    "link_text": doc.link_text,
                    **doc.guessed.get("kind", {}),
                }
                for kind, doc in exam.documents.items()
            },
        }
        for kind, more in exam.more_keys.items():
            for position, doc in enumerate(more, start=2):
                evidence_exams[exam.slug]["documents"][f"{kind}#{position}"] = {
                    "url": doc.url,
                    "link_text": doc.link_text,
                    **doc.guessed.get("kind", {}),
                }
    data: dict[str, Any] = {
        "contest": contest.slug,
        "name": contest.name,
        "agency": contest.agency,
        "exam_board": source_slug,
        "year": contest.year,
        "source_url": contest.url,
        "exams": exam_entries,
        "evidence": {
            "source": source_slug,
            "contest": {"url": contest.url, "link_text": contest.link_text, **contest.guessed},
            "exams": evidence_exams,
            "skipped": list(contest.skipped),
        },
    }
    return Manifest.model_validate(data)


def _header(manifest: Manifest) -> str:
    return (
        f"# Proposta do crawler `{manifest.evidence.get('source', '?')}` a partir de"
        f" {manifest.source_url}.\n"
        "# Não edite: a próxima execução do crawler reescreve este arquivo. Aprove com\n"
        f"# `emmoni manifests approve {manifest.contest}` e ajuste o manifesto aprovado"
        " (disciplinas por faixa,\n# nomes, `first_number`) antes de ingerir.\n"
    )


def render(manifest: Manifest) -> str:
    data = manifest.model_dump(mode="json", by_alias=True, exclude_defaults=True)
    for exam in data.get("exams", []):
        exam.pop("subjects_by_range", None)
    return _header(manifest) + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110)


def write_pending(manifest: Manifest, manifests_dir: Path = MANIFESTS_DIR) -> str:
    """Escreve a proposta se mudou. Devolve 'nova', 'atualizada' ou 'sem mudança'."""
    path = pending_path(manifest.contest, manifests_dir)
    text = render(manifest)
    if path.exists():
        if path.read_text(encoding="utf-8") == text:
            return "sem mudança"
        path.write_text(text, encoding="utf-8")
        return "atualizada"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return "nova"


# --- aprovação e rejeição -------------------------------------------------------------------------


def load_pending(slug: str, manifests_dir: Path = MANIFESTS_DIR) -> Manifest:
    path = pending_path(slug, manifests_dir)
    if not path.exists():
        raise ProposalError(f"não há proposta pendente {slug} em {path.parent}")
    try:
        return manifest_module.load(path)
    except ValidationError as error:
        raise ProposalError(f"proposta {slug} inválida: {error}") from error


def approve(slug: str, manifests_dir: Path = MANIFESTS_DIR) -> Path:
    """Valida a proposta (manifesto + catálogo) e a move para os aprovados."""
    from ingest import catalog as catalog_module  # evita ciclo de importação

    if is_approved(slug, manifests_dir):
        raise ProposalError(f"{slug} já está aprovado")
    loaded = load_pending(slug, manifests_dir)
    problems = catalog_module.manifest_problems(catalog_module.load(), loaded)
    if problems:
        raise ProposalError(f"proposta {slug} cita slugs fora do catálogo: {'; '.join(problems)}")
    source = pending_path(slug, manifests_dir)
    target = manifests_dir / f"{slug}.yaml"
    source.rename(target)
    return target


def reject(
    slug: str,
    reason: str,
    manifests_dir: Path = MANIFESTS_DIR,
    *,
    by: str | None = None,
    now: datetime.datetime | None = None,
) -> Path:
    """Move a proposta para `_rejected/` com o motivo. O crawler não volta a propor o concurso."""
    if not reason.strip():
        raise ProposalError("informe o motivo da rejeição (--reason)")
    source = pending_path(slug, manifests_dir)
    if not source.exists():
        raise ProposalError(f"não há proposta pendente {slug}")
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    data["rejected"] = {
        "reason": reason.strip(),
        "by": by or getpass.getuser(),
        "at": (now or datetime.datetime.now(datetime.UTC)).isoformat(timespec="seconds"),
    }
    target = manifests_dir / REJECTED / f"{slug}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "# Proposta rejeitada; o crawler não volta a propor este concurso.\n"
        + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110),
        encoding="utf-8",
    )
    source.unlink()
    return target
