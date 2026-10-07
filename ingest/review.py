"""Fila de revisão e amostragem manual (SPECIFICATIONS.md §8).

- `list`/`show`: questões em `review`, com os motivos gravados pela etapa `validate`.
- `sample`: sorteia N questões publicáveis de uma prova e gera um HTML com cada questão ao lado da
  página do PDF original, para conferência humana. O sorteio é determinístico por prova.
- `approve`: publica a **prova** (`exam.publish_status = 'published'`) depois da amostragem. É um
  ato humano: o comando exige que a amostra tenha sido gerada e registra quem aprovou.
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


def show(conn: Conn, ref: ExamRef, numbers: list[int]) -> list[QuestionView]:
    exam_id = _exam_id(conn, ref)
    rows = conn.execute(
        """select q.number, q.statement_md, p.body_md, q.answer_preliminary, q.answer_final,
                  q.answer_status::text, s.name,
                  coalesce((select array_agg(t.path::text order by t.path)
                              from question_topic qt join topic t on t.id = qt.topic_id
                             where qt.question_id = q.id), '{}'),
                  q.publish_status::text, q.review_reasons, q.source_page, d.local_path
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
    record = {
        "exam": str(ref),
        "numbers": numbers,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "approved_at": None,
        "approved_by": None,
    }
    (directory / "sample.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return page


def approve(conn: Conn, ref: ExamRef, data: Path) -> tuple[int, int]:
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
    record["approved_by"] = getpass.getuser()
    record_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return int(str(row[0])), int(str(row[1]))


def _page_png(pdf_path: str | None, page: int) -> str | None:
    if not pdf_path or not Path(pdf_path).exists():
        return None
    with pymupdf.open(pdf_path) as document:  # type: ignore[no-untyped-call]
        zoom = pymupdf.Matrix(PAGE_ZOOM, PAGE_ZOOM)  # type: ignore[no-untyped-call]
        pixmap = document[page - 1].get_pixmap(matrix=zoom)
        return base64.b64encode(pixmap.tobytes("png")).decode()


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
