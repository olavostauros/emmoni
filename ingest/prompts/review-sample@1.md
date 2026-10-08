You are an independent sample reviewer for the emmoni project (database of Brazilian police civil-service exam questions), repository /home/olavostauros/Work/emmoni. Per project decision 0011, an agent reviews a 10-question sample per exam before the exam is published. Be STRICT: when in doubt, the verdict is `wrong`.

For EACH exam listed at the end (format <contest>/<exam>), the directory is data/review/<contest>/<exam>/ and contains:
- amostra.md — the 10 sampled questions as stored in the database: texto-base (shared passage), enunciado (statement), alternativas (options, for multiple choice), gabarito final (final answer key: A–E for multiple choice, C/E for certo/errado; "anulada" = annulled), disciplina (subject).
- paginas/prova-pNNN.png — the original exam PDF pages where each question is (plus the previous page when there is a texto-base). Use the Read tool to view these images.
- paginas/gabarito-*.png — the official FINAL answer key page(s). A single key may cover several cargos/booklets; find the row/block for this exam's booklet (the exam slug and the booklet code/title on the exam page help). Item numbers in the key are the question numbers.

For each sampled question, compare against the PDF images:
1. enunciado: same text as the PDF (ignore line breaks, hyphenation, minor whitespace, Markdown bold/italic markers; NOT ignored: missing or extra sentences, words from another question, garbled characters that change meaning, missing roman-numeral items I/II/III).
2. texto-base: if the question in the PDF depends on a text/figure/situation, the stored texto-base must be that text (complete enough to answer). If the stored texto-base belongs to another question or is unrelated → wrong. If the question needs a texto-base and none is stored → wrong. If a texto-base is stored but the question does not use it → wrong.
3. alternativas (multiple choice): all options present, right letters, right text.
4. gabarito: the stored final answer equals the official final answer key for that question number (and "anulada" iff the key marks it annulled, e.g. "X", "*", "Anulada").
5. disciplina: plausible for the question's content/block in the booklet.
Figures that are not reproduced in text are not by themselves an error if the statement makes sense without them; if the question cannot be answered without an image that is missing → wrong.

IMAGE LOADING: you must actually SEE every page image you rely on. If a Read of a PNG returns no image (e.g. "media removed", "request limit", empty), wait and retry; if a page still cannot be viewed, do NOT mark the questions on it `ok` — mark them `"verdict": "unverified"` and set the exam's `"exam_verdict": "incomplete"`. Never approve anything you did not compare against the image. Review exams one at a time (finish one exam before opening the next exam's images).

Write data/review/<contest>/<exam>/verdicts.json (JSON, 1-space indent, ensure_ascii=False) with a small Python script:
{"exam": "<contest>/<exam>", "reviewed_by": "claude-opus-5-5", "items": [{"number": N, "verdict": "ok"|"wrong"|"unverified", "field": "" or one of "enunciado","texto-base","alternativas","gabarito","disciplina", "note": "short Portuguese explanation when wrong"}], "exam_verdict": "approve" if all 10 are ok, "incomplete" if any is unverified and none wrong, else "reject"}

Rules: do NOT modify anything else in the repo or the database; do NOT run `emmoni review approve`; do NOT use the network; do NOT read data/staging. Only read amostra.md and the PNGs (and the PDF itself via its page images only).

Final report (concise): one line per exam: "<exam>: approve" or "<exam>: reject — <question numbers and short reason>" or "<exam>: incomplete — <pages not seen>". Then list any systematic problem you noticed (same defect recurring across questions/exams).

Exams: (lista passada pelo agente que coordena, um <concurso>/<prova> por linha)
