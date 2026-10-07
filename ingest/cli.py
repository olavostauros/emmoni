"""Comando `emmoni`."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from ingest import catalog, checks, db, fetch, manifest, pipeline, review, taxonomy


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="emmoni")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="roda os checks de qualidade dos dados")
    check.add_argument("--checks-dir", type=Path, default=checks.CHECKS_DIR)

    tax = commands.add_parser("taxonomy", help="taxonomia de disciplinas e assuntos")
    tax_commands = tax.add_subparsers(dest="taxonomy_command", required=True)
    tax_load = tax_commands.add_parser("load", help="carrega db/taxonomy/*.yaml no banco")
    tax_load.add_argument("--dir", type=Path, default=taxonomy.TAXONOMY_DIR)

    cat = commands.add_parser("catalog", help="catálogo de bancas, órgãos e cargos")
    cat_commands = cat.add_subparsers(dest="catalog_command", required=True)
    cat_load = cat_commands.add_parser("load", help="carrega db/catalog.yaml no banco")
    cat_load.add_argument("--file", type=Path, default=catalog.CATALOG_FILE)

    ingest = commands.add_parser("ingest", help="ingere as provas de um manifesto")
    ingest.add_argument("manifest", help="slug do concurso (pf-2021) ou caminho do YAML")
    ingest.add_argument("--exam", help="só esta prova (slug)")
    ingest.add_argument("--step", choices=pipeline.STEPS, help="só esta etapa")

    rev = commands.add_parser("review", help="fila de revisão e amostragem")
    rev_commands = rev.add_subparsers(dest="review_command", required=True)
    rev_list = rev_commands.add_parser("list", help="questões em revisão e seus motivos")
    rev_list.add_argument("exam", nargs="?", help="<concurso>/<prova>")
    rev_show = rev_commands.add_parser("show", help="mostra questões de uma prova")
    rev_show.add_argument("exam", help="<concurso>/<prova>")
    rev_show.add_argument("numbers", nargs="+", type=int)
    rev_sample = rev_commands.add_parser("sample", help="gera a amostra para conferência")
    rev_sample.add_argument("exam", help="<concurso>/<prova>")
    rev_sample.add_argument("--n", type=int, default=10)
    rev_approve = rev_commands.add_parser("approve", help="publica a prova após a amostragem")
    rev_approve.add_argument("exam", help="<concurso>/<prova>")

    args = parser.parse_args(argv)
    if args.command == "review":
        return _review(args)
    if args.command == "check":
        return _check(args.checks_dir)
    if args.command == "taxonomy":
        return _taxonomy_load(args.dir)
    if args.command == "catalog":
        return _catalog_load(args.file)
    if args.command == "ingest":
        return _ingest(args.manifest, args.exam, args.step)
    parser.error(f"comando desconhecido: {args.command}")


def _check(checks_dir: Path) -> int:
    with db.connect() as conn:
        results = checks.run_checks(conn, checks_dir)
    for result in results:
        print(f"{'ok   ' if result.ok else 'FALHA'} {result.name} ({len(result.violations)})")
        for row in result.violations[:10]:
            print("      ", dict(zip(result.columns, row, strict=True)))
    failed = sum(not result.ok for result in results)
    print(f"check: {len(results)} rodado(s), {failed} com violações")
    return 1 if failed else 0


def _taxonomy_load(directory: Path) -> int:
    try:
        subjects = taxonomy.load_dir(directory)
    except taxonomy.TaxonomyError as error:
        print(f"taxonomy: {error}")
        return 1
    with db.connect() as conn:
        report = taxonomy.sync(conn, subjects)
    print(f"taxonomy: {report.subjects} disciplina(s), {report.topics} assunto(s)")
    for path in report.orphans:
        print(f"  aviso: {path} está no banco mas não nos arquivos")
    return 0


def _catalog_load(path: Path) -> int:
    loaded = catalog.load(path)
    with db.connect() as conn:
        boards, agencies, positions = catalog.sync(conn, loaded)
    print(f"catalog: {boards} banca(s), {agencies} órgão(s), {positions} cargo(s)")
    return 0


def _ingest(name: str, exam_slug: str | None, step: str | None) -> int:
    loaded = manifest.load(manifest.resolve(name))
    exams = [loaded.exam(exam_slug)] if exam_slug else loaded.exams
    for exam in exams:
        print(f"{loaded.contest}/{exam.slug}")
        pipeline.ExamRun(loaded, exam).run(step)
    return 0


def _review(args: argparse.Namespace) -> int:
    try:
        ref = review.ExamRef.parse(args.exam) if args.exam else None
        with db.connect() as conn:
            if args.review_command == "list":
                rows = review.list_review(conn, ref)
                for exam, number, reasons in rows:
                    print(f"{exam} {number:>4}  {'; '.join(reasons)}")
                print(f"review: {len(rows)} questão(ões)")
            elif args.review_command == "show":
                assert ref is not None
                for q in review.show(conn, ref, args.numbers):
                    print(
                        f"--- {ref} questão {q.number} (página {q.source_page}, {q.publish_status})"
                    )
                    if q.passage_md:
                        print(f"[texto-base]\n{q.passage_md}\n")
                    print(q.statement_md)
                    print(f"gabarito: {q.answer_final} ({q.answer_status}) · {q.subject}")
                    for reason in q.review_reasons:
                        print(f"  motivo: {reason}")
            elif args.review_command == "sample":
                assert ref is not None
                page = review.write_sample(conn, ref, args.n, fetch.data_dir())
                print(f"amostra: {page}")
            elif args.review_command == "approve":
                assert ref is not None
                published, left = review.approve(conn, ref, fetch.data_dir())
                conn.commit()
                print(f"{ref} publicada: {published} questão(ões) visíveis, {left} fora")
    except review.ReviewError as error:
        print(f"review: {error}")
        return 1
    return 0
