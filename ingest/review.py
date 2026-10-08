"""Fila de revisão e amostragem manual (SPECIFICATIONS.md §8).

- `list`/`show`: questões em `review`, com os motivos gravados pela etapa `validate`.
- `sample`: sorteia N questões publicáveis de uma prova e gera um HTML com cada questão ao lado da
  página do PDF original, para a conferência do agente revisor (decisão 0011). O sorteio é
  determinístico por prova. Para o agente, gera também `amostra.md` (enunciado, texto-base,
  alternativas, gabarito e disciplina) e as páginas em PNG em `paginas/`: a da prova onde está
  cada questão (e a anterior, quando há texto-base) e a do gabarito definitivo.
- `approve`: publica a **prova** (`exam.publish_status = 'published'`) depois da amostragem. O
  comando exige que a amostra tenha sido gerada e registra quem aprovou (`--by`, o modelo).
- `topics`: amostra determinística de N questões classificadas, de todas as provas reais, para
  conferir a qualidade da classificação por assunto (critério do M4: 50 amostras, ≥ 90% de
  acerto). Gera `data/review/assuntos/amostra.json` (onde o revisor grava `verdict`) e
  `amostra.md`; `--report` conta os vereditos.
"""

import base64
import datetime
import getpass
import html
import json
import random
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pymupdf

Conn = psycopg.Connection[tuple[object, ...]]
PAGE_ZOOM = 1.6


class ReviewError(Exception):
    pass


@dataclass(frozen=True)
class ExamRef:
    contest: str
    exam: str

    @classmethod
    def parse(cls, text: str) -> "ExamRef":
        contest, sep, exam = text.partition("/")
        if not sep or not contest or not exam:
            raise ReviewError(f"use <concurso>/<prova>, ex.: pf-2021/agente (recebido {text!r})")
        return cls(contest, exam)

    def __str__(self) -> str:
        return f"{self.contest}/{self.exam}"


def _exam_id(conn: Conn, ref: ExamRef) -> int:
    row = conn.execute(
        """select e.id from exam e join contest c on c.id = e.contest_id
            where c.slug = %s and e.slug = %s""",
        (ref.contest, ref.exam),
    ).fetchone()
    if row is None:
        raise ReviewError(f"prova {ref} não está no banco")
    return int(str(row[0]))


def list_review(conn: Conn, ref: ExamRef | None = None) -> list[tuple[str, int, list[str]]]:
    rows = conn.execute(
        """select c.slug || '/' || e.slug, q.number, q.review_reasons
             from question q join exam e on e.id = q.exam_id join contest c on c.id = e.contest_id
            where q.publish_status = 'review'
              and (%s::text is null or (c.slug = %s and e.slug = %s))
            order by 1, 2""",
        (str(ref) if ref else None, ref.contest if ref else None, ref.exam if ref else None),
    ).fetchall()
    return [(str(r[0]), int(str(r[1])), list(r[2])) for r in rows]  # type: ignore[call-overload]


@dataclass(frozen=True)
class QuestionView:
    number: int
    statement_md: str
    passage_md: str | None
    answer_preliminary: str | None
    answer_final: str | None
    answer_status: str
    subject: str | None
    topics: list[str]
    publish_status: str
    review_reasons: list[str]
    source_page: int
    pdf_path: str | None
    options: list[tuple[str, str]]


def show(conn: Conn, ref: ExamRef, numbers: list[int]) -> list[QuestionView]:
    exam_id = _exam_id(conn, ref)
    rows = conn.execute(
        """select q.number, q.statement_md, p.body_md, q.answer_preliminary, q.answer_final,
                  q.answer_status::text, s.name,
                  coalesce((select array_agg(t.path::text order by t.path)
                              from question_topic qt join topic t on t.id = qt.topic_id
                             where qt.question_id = q.id), '{}'),
                  q.publish_status::text, q.review_reasons, q.source_page, d.local_path,
                  coalesce((select array_agg(array[o.letter, o.body_md] order by o.letter)
                              from question_option o where o.question_id = q.id), '{}')
             from question q
             join exam e on e.id = q.exam_id
             left join passage p on p.id = q.passage_id
             left join subject s on s.id = q.subject_id
             left join source_document d on d.id = e.exam_document_id
            where q.exam_id = %s and q.number = any(%s)
            order by q.number""",
        (exam_id, numbers),
    ).fetchall()
    return [
        QuestionView(
            number=int(str(r[0])),
            statement_md=str(r[1]),
            passage_md=None if r[2] is None else str(r[2]),
            answer_preliminary=None if r[3] is None else str(r[3]),
            answer_final=None if r[4] is None else str(r[4]),
            answer_status=str(r[5]),
            subject=None if r[6] is None else str(r[6]),
            topics=list(r[7]),  # type: ignore[call-overload]
            publish_status=str(r[8]),
            review_reasons=list(r[9]),  # type: ignore[call-overload]
            source_page=int(str(r[10])),
            pdf_path=None if r[11] is None else str(r[11]),
            options=[(str(o[0]), str(o[1])) for o in r[12]],  # type: ignore[attr-defined]
        )
        for r in rows
    ]


def sample_numbers(conn: Conn, ref: ExamRef, n: int) -> list[int]:
    """Sorteio determinístico entre as questões sem motivo de revisão."""
    exam_id = _exam_id(conn, ref)
    rows = conn.execute(
        """select number from question
            where exam_id = %s and publish_status <> 'review' order by number""",
        (exam_id,),
    ).fetchall()
    candidates = [int(str(r[0])) for r in rows]
    if not candidates:
        raise ReviewError(f"{ref}: nenhuma questão publicável para amostrar")
    return sorted(random.Random(str(ref)).sample(candidates, min(n, len(candidates))))


def sample_dir(data: Path, ref: ExamRef) -> Path:
    return data / "review" / ref.contest / ref.exam


def write_sample(conn: Conn, ref: ExamRef, n: int, data: Path) -> Path:
    numbers = sample_numbers(conn, ref, n)
    questions = show(conn, ref, numbers)
    directory = sample_dir(data, ref)
    directory.mkdir(parents=True, exist_ok=True)
    page = directory / "amostra.html"
    page.write_text(_html(ref, questions), encoding="utf-8")
    keys = _answer_key_paths(conn, ref)
    (directory / "amostra.md").write_text(
        _markdown(ref, questions, _write_pages(directory / "paginas", questions, keys)),
        encoding="utf-8",
    )
    record = {
        "exam": str(ref),
        "numbers": numbers,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "approved_at": None,
        "approved_by": None,
    }
    (directory / "sample.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return page


def approve(conn: Conn, ref: ExamRef, data: Path, by: str | None = None) -> tuple[int, int]:
    """Publica a prova. Devolve (questões publicadas, questões que ficam de fora)."""
    record_path = sample_dir(data, ref) / "sample.json"
    if not record_path.exists():
        raise ReviewError(f"{ref}: gere e confira a amostra antes (emmoni review sample {ref})")
    exam_id = _exam_id(conn, ref)
    with conn.transaction():
        conn.execute("update exam set publish_status = 'published' where id = %s", (exam_id,))
        row = conn.execute(
            """select count(*) filter (where publish_status = 'published'),
                      count(*) filter (where publish_status <> 'published')
                 from question where exam_id = %s""",
            (exam_id,),
        ).fetchone()
    assert row is not None
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["approved_at"] = datetime.datetime.now(datetime.UTC).isoformat()
    record["approved_by"] = by or getpass.getuser()
    record_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return int(str(row[0])), int(str(row[1]))


TOPIC_SAMPLE_SEED = "assuntos"
VERDICTS = ("ok", "wrong")


@dataclass(frozen=True)
class TopicSampleItem:
    id: str
    exam: str
    number: int
    subject: str
    passage_md: str | None
    statement_md: str
    topics: list[str]  # "path — nome"


def sample_topics(conn: Conn, n: int, seed: str = TOPIC_SAMPLE_SEED) -> list[TopicSampleItem]:
    """Sorteio determinístico entre as questões reais classificadas e sem pendência de revisão."""
    rows = conn.execute(
        """select q.id::text, c.slug || '/' || e.slug, q.number, s.name, p.body_md, q.statement_md,
                  array_agg(t.path::text || ' — ' || t.name order by t.path)
             from question q
             join exam e on e.id = q.exam_id
             join contest c on c.id = e.contest_id
             join subject s on s.id = q.subject_id
             join question_topic qt on qt.question_id = q.id
             join topic t on t.id = qt.topic_id
             left join passage p on p.id = q.passage_id
            where c.slug not like 'seed-%%' and q.publish_status <> 'review'
            group by q.id, c.slug, e.slug, q.number, s.name, p.body_md, q.statement_md
            order by c.slug, e.slug, q.number"""
    ).fetchall()
    if not rows:
        raise ReviewError("nenhuma questão classificada para amostrar")
    chosen = random.Random(seed).sample(rows, min(n, len(rows)))
    items = [
        TopicSampleItem(
            id=str(r[0]),
            exam=str(r[1]),
            number=int(str(r[2])),
            subject=str(r[3]),
            passage_md=None if r[4] is None else str(r[4]),
            statement_md=str(r[5]),
            topics=list(r[6]),  # type: ignore[call-overload]
        )
        for r in chosen
    ]
    return sorted(items, key=lambda i: (i.exam, i.number))


def topic_sample_dir(data: Path) -> Path:
    return data / "review" / "assuntos"


def write_topic_sample(conn: Conn, n: int, data: Path, seed: str = TOPIC_SAMPLE_SEED) -> Path:
    items = sample_topics(conn, n, seed)
    directory = topic_sample_dir(data)
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "seed": seed,
        "items": [
            {
                "id": i.id,
                "exam": i.exam,
                "number": i.number,
                "subject": i.subject,
                "topics": i.topics,
                "verdict": None,  # "ok" | "wrong", preenchido pelo agente revisor
                "note": "",
                "reviewed_by": None,
            }
            for i in items
        ],
    }
    (directory / "amostra.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    lines = [
        "# Amostra de classificação por assunto",
        "",
        f"{len(items)} questões sorteadas (semente `{seed}`). Para cada uma, confira se os assuntos",
        "atribuídos descrevem o conteúdo cobrado e grave `verdict` (`ok` ou `wrong`) e, se quiser,",
        "`note` em `amostra.json`. Depois: `emmoni review topics --report`.",
        "",
    ]
    for i in items:
        lines += [f"## {i.exam} — questão {i.number} ({i.subject})", ""]
        if i.passage_md:
            lines += ["**Texto-base**", "", i.passage_md, ""]
        lines += [i.statement_md, "", "**Assuntos atribuídos:**", ""]
        lines += [f"- `{t}`" for t in i.topics]
        lines.append("")
    page = directory / "amostra.md"
    page.write_text("\n".join(lines), encoding="utf-8")
    return page


@dataclass(frozen=True)
class TopicSampleReport:
    total: int
    judged: int
    ok: int

    @property
    def accuracy(self) -> float | None:
        return self.ok / self.judged if self.judged else None


def topic_sample_report(data: Path) -> TopicSampleReport:
    path = topic_sample_dir(data) / "amostra.json"
    if not path.exists():
        raise ReviewError("gere a amostra antes (emmoni review topics)")
    record = json.loads(path.read_text(encoding="utf-8"))
    items = record["items"]
    for item in items:
        if item["verdict"] not in (None, *VERDICTS):
            raise ReviewError(
                f"{item['exam']} questão {item['number']}: veredito inválido {item['verdict']!r}"
                f" (use {' ou '.join(VERDICTS)})"
            )
    judged = [i for i in items if i["verdict"] is not None]
    return TopicSampleReport(
        total=len(items), judged=len(judged), ok=sum(i["verdict"] == "ok" for i in judged)
    )


def _page_png(pdf_path: str | None, page: int) -> str | None:
    if not pdf_path or not Path(pdf_path).exists():
        return None
    with pymupdf.open(pdf_path) as document:  # type: ignore[no-untyped-call]
        zoom = pymupdf.Matrix(PAGE_ZOOM, PAGE_ZOOM)  # type: ignore[no-untyped-call]
        pixmap = document[page - 1].get_pixmap(matrix=zoom)
        return base64.b64encode(pixmap.tobytes("png")).decode()


def _answer_key_paths(conn: Conn, ref: ExamRef) -> list[str]:
    rows = conn.execute(
        """select d.local_path from exam_document ed join source_document d
                on d.id = ed.source_document_id
            where ed.exam_id = %s and ed.kind = 'answer_key_final' and d.local_path is not null
            order by ed.position""",
        (_exam_id(conn, ref),),
    ).fetchall()
    return [str(r[0]) for r in rows]


def _write_pages(
    directory: Path, questions: list[QuestionView], keys: list[str]
) -> dict[str, list[str]]:
    """Grava as páginas em PNG; devolve, por questão (e por "gabarito"), os arquivos relativos."""
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob("*.png"):
        old.unlink()
    files: dict[str, list[str]] = {}

    def render(pdf_path: str, page: int, name: str) -> str | None:
        target = directory / name
        if not target.exists():
            png = _page_png(pdf_path, page)
            if png is None:
                return None
            target.write_bytes(base64.b64decode(png))
        return f"paginas/{name}"

    for q in questions:
        pages = [q.source_page - 1, q.source_page] if q.passage_md else [q.source_page]
        names = [
            render(q.pdf_path, page, f"prova-p{page:03d}.png")
            for page in pages
            if q.pdf_path and page >= 1
        ]
        files[str(q.number)] = [n for n in names if n]
    keys_rendered = [render(path, 1, f"gabarito-{i}.png") for i, path in enumerate(keys, 1)]
    files["gabarito"] = [n for n in keys_rendered if n]
    return files


def _markdown(ref: ExamRef, questions: list[QuestionView], pages: dict[str, list[str]]) -> str:
    lines = [
        f"# Amostra — {ref}",
        "",
        "Confira cada questão contra as páginas do PDF: enunciado, texto-base, alternativas,",
        "gabarito definitivo e disciplina. Gabarito definitivo: "
        + (", ".join(f"`{p}`" for p in pages["gabarito"]) or "(PDF não encontrado em disco)"),
        "",
    ]
    for q in questions:
        answer = q.answer_final or ("anulada" if q.answer_status == "annulled" else "—")
        lines += [
            f"## Questão {q.number}",
            "",
            f"- Páginas: {', '.join(f'`{p}`' for p in pages[str(q.number)]) or '(PDF não encontrado)'}"
            f" (questão na página {q.source_page})",
            f"- Gabarito final: **{answer}** ({q.answer_status}; preliminar:"
            f" {q.answer_preliminary or '—'})",
            f"- Disciplina: {q.subject or '—'} · Assuntos: {', '.join(q.topics) or '—'}",
            "",
        ]
        if q.passage_md:
            lines += ["**Texto-base**", "", q.passage_md, ""]
        lines += ["**Enunciado**", "", q.statement_md, ""]
        if q.options:
            lines += ["**Alternativas**", ""] + [
                f"- {letter}) {body}" for letter, body in q.options
            ]
            lines.append("")
    return "\n".join(lines)


def _html(ref: ExamRef, questions: list[QuestionView]) -> str:
    pages: dict[int, str | None] = {}
    blocks = []
    for q in questions:
        if q.source_page not in pages:
            pages[q.source_page] = _page_png(q.pdf_path, q.source_page)
        png = pages[q.source_page]
        image = (
            f'<img alt="página {q.source_page}" src="data:image/png;base64,{png}">'
            if png
            else "<p>(PDF não encontrado em disco)</p>"
        )
        passage = (
            f"<h4>Texto-base</h4><div class='md'>{html.escape(q.passage_md)}</div>"
            if q.passage_md
            else ""
        )
        answer = q.answer_final or ("anulada" if q.answer_status == "annulled" else "—")
        blocks.append(
            f"""<section>
  <div class="q">
    <h3>Questão {q.number} <small>página {q.source_page} · {html.escape(q.publish_status)}</small></h3>
    <p class="meta">Gabarito: <b>{answer}</b> ({q.answer_status}) · Disciplina:
      {html.escape(q.subject or "—")} · Assuntos: {html.escape(", ".join(q.topics) or "—")}</p>
    <div class="md">{html.escape(q.statement_md)}</div>
    {passage}
    <label><input type="checkbox"> confere com o PDF</label>
  </div>
  <div class="pdf">{image}</div>
</section>"""
        )
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Amostra {html.escape(str(ref))}</title>
<style>
:root {{ --bg: #fff; --fg: #1b1b1b; --muted: #666; --line: #ddd; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #161616; --fg: #eee; --muted: #aaa; --line: #333; }} }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, sans-serif; margin: 0 16px; }}
section {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; border-bottom: 1px solid var(--line); padding: 24px 0; }}
@media (max-width: 900px) {{ section {{ grid-template-columns: 1fr; }} }}
.md {{ white-space: pre-wrap; }}
.meta, small {{ color: var(--muted); }}
img {{ width: 100%; border: 1px solid var(--line); }}
</style></head><body>
<h1>Amostra — {html.escape(str(ref))}</h1>
<p>Confira cada questão contra a página do PDF (enunciado, texto-base, gabarito e disciplina).
Se tudo conferir: <code>emmoni review approve {html.escape(str(ref))}</code>.</p>
{"".join(blocks)}
</body></html>
"""
