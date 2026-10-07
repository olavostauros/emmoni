"""Etapa `classify`: questões → assuntos da taxonomia, pelo LLM (SPECIFICATIONS.md §7.3, §7.4).

- A disciplina vem do manifesto; o LLM só escolhe assuntos **dessa** disciplina, entre os que existem
  em `db/taxonomy/` (o JSON schema restringe os identificadores a um `enum`).
- Saída por JSON schema (`output_config.format`), nunca texto livre.
- Cada resposta é cacheada em `data/staging/llm-cache/<sha256>.json` pelo hash de prompt + entrada +
  modelo: reprocessar não gasta tokens. Testes usam respostas gravadas e nunca chamam a API.
- Confiança < 0,6 → a questão vai para `review` com o motivo registrado.
"""

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ingest.taxonomy import Subject
from ingest.validate import StagedQuestion, Validated

PROMPT_NAME = "classify@1"
PROMPT_FILE = Path(__file__).with_name("prompts") / f"{PROMPT_NAME}.md"
DEFAULT_MODEL = "claude-sonnet-5-5"
MIN_CONFIDENCE = 0.6
MAX_PASSAGE_CHARS = 6000

# Recebe os parâmetros da requisição, devolve o JSON da resposta (já parseado).
Caller = Callable[[dict[str, Any]], dict[str, Any]]


class Assigned(BaseModel):
    path: str
    origin: str = "llm"
    confidence: float


class Classified(BaseModel):
    """`topics.json`: assuntos aceitos e pendências por número de questão."""

    model: str
    prompt: str
    topics: dict[int, list[Assigned]]
    review: dict[int, str]  # número → motivo
    suggestions: dict[int, str]  # número → assunto sugerido (para curadoria da taxonomia)


def model_name() -> str:
    return os.environ.get("EMMONI_LLM_MODEL") or DEFAULT_MODEL


def request_for(
    question: StagedQuestion, passage: str | None, subject: Subject, model: str
) -> dict[str, Any]:
    topics = "\n".join(f"- {t.path} — {t.name}" for t in subject.topics)
    passage_block = f"Texto-base:\n{passage[:MAX_PASSAGE_CHARS]}\n\n" if passage else ""
    prompt = PROMPT_FILE.read_text(encoding="utf-8").format(
        subject_name=subject.name,
        topics=topics,
        passage=passage_block,
        statement=question.statement_md,
    )
    schema = {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "enum": [t.path for t in subject.topics]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["path", "confidence"],
                    "additionalProperties": False,
                },
            },
            "suggested_topic": {"type": "string"},
        },
        "required": ["topics", "suggested_topic"],
        "additionalProperties": False,
    }
    return {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": schema}},
    }


def anthropic_caller() -> Caller:
    """Chamada real à Claude API. Importa o SDK só aqui: testes não precisam dele."""
    import anthropic

    client = anthropic.Anthropic()

    def call(params: dict[str, Any]) -> dict[str, Any]:
        # Fallback no servidor: se o modelo recusar por política, outro modelo continua a mesma
        # requisição (quem respondeu fica em response.model).
        response = client.beta.messages.create(
            **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"classificação recusada pelo modelo ({response.stop_details})")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("resposta da classificação cortada (max_tokens)")
        text = next(block.text for block in response.content if block.type == "text")
        data: dict[str, Any] = json.loads(text)
        return data

    return call


def classify(
    validated: Validated,
    subjects: dict[str, Subject],
    cache_dir: Path,
    caller: Caller | None,
    model: str | None = None,
) -> Classified:
    """Classifica as questões com disciplina. Sem `caller`, usa só o cache (falha no que faltar)."""
    model = model or model_name()
    passages = {p.key: p.body_md for p in validated.passages}
    result = Classified(model=model, prompt=PROMPT_NAME, topics={}, review={}, suggestions={})
    for question in validated.questions:
        if question.subject is None or question.subject not in subjects:
            continue
        subject = subjects[question.subject]
        if not subject.topics:
            result.review[question.number] = "disciplina sem assuntos na taxonomia"
            continue
        params = request_for(
            question,
            passages.get(question.passage_key) if question.passage_key else None,
            subject,
            model,
        )
        answer = _cached(params, cache_dir, caller)
        allowed = {t.path for t in subject.topics}
        accepted = [
            Assigned(path=t["path"], confidence=float(t["confidence"]))
            for t in answer.get("topics", [])
            if t.get("path") in allowed and float(t.get("confidence", 0)) >= MIN_CONFIDENCE
        ]
        if accepted:
            result.topics[question.number] = accepted[:3]
        else:
            result.review[question.number] = (
                f"classificação com confiança abaixo de {MIN_CONFIDENCE} (assunto)"
            )
        if answer.get("suggested_topic"):
            result.suggestions[question.number] = str(answer["suggested_topic"])
    return result


def _cached(params: dict[str, Any], cache_dir: Path, caller: Caller | None) -> dict[str, Any]:
    key = hashlib.sha256(
        json.dumps({"prompt": PROMPT_NAME, **params}, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    path = cache_dir / f"{key}.json"
    if path.exists():
        cached: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return cached
    if caller is None:
        raise RuntimeError(f"resposta não está no cache ({path.name}) e não há acesso à API")
    answer = caller(params)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(answer, ensure_ascii=False, indent=1), encoding="utf-8")
    return answer
