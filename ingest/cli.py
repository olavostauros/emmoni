"""Comando `emmoni`."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ingest import (
    catalog,
    checks,
    coverage,
    crawl,
    db,
    dblock,
    fetch,
    manifest,
    pipeline,
    proposals,
    review,
    taxonomy,
)
from ingest import sources as sources_module
from ingest.crawlers.http import CrawlError, PoliteClient
from ingest.crawlers.registry import CRAWLERS
from ingest.load import LoadError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="emmoni")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("coverage", help="gera docs/coverage.md")
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
    rev_sample.add_argument(
        "--also", type=int, nargs="+", default=[], help="questões além do sorteio (que mudaram)"
    )
    rev_sample.add_argument(
        "--seed",
        help="semente do sorteio (padrão: <concurso>/<prova>); outra semente reamostra a prova",
    )
    rev_approve = rev_commands.add_parser("approve", help="publica a prova após a amostragem")
    rev_approve.add_argument("exam", help="<concurso>/<prova>")
    rev_approve.add_argument("--by", help="quem conferiu a amostra (modelo e versão do agente)")
    rev_commands.add_parser(
        "restore", help="publica as provas cujo conteúdo confere com a aprovação registrada"
    )
    rev_topics = rev_commands.add_parser(
        "topics", help="amostra de classificações por assunto para conferência"
    )
    rev_topics.add_argument("--n", type=int, default=50)
    rev_topics.add_argument("--seed", default=review.TOPIC_SAMPLE_SEED)
    rev_topics.add_argument("--report", action="store_true", help="conta os vereditos gravados")

    crawl_cmd = commands.add_parser("crawl", help="descobre provas nas fontes e propõe manifestos")
    crawl_cmd.add_argument("source", nargs="?", help="slug da fonte (ingest/sources.yaml)")
    crawl_cmd.add_argument("--all", action="store_true", help="todas as fontes")
    crawl_cmd.add_argument(
        "--force", action="store_true", help="ignora next_fetch_at e busca tudo de novo"
    )

    man = commands.add_parser(
        "manifests", help="propostas do crawler: pendentes, aprovar, rejeitar"
    )
    man_commands = man.add_subparsers(dest="manifests_command", required=True)
    man_commands.add_parser("pending", help="lista as propostas pendentes")
    man_show = man_commands.add_parser("show", help="mostra uma proposta")
    man_show.add_argument("slug")
    man_approve = man_commands.add_parser("approve", help="move a proposta para os aprovados")
    man_approve.add_argument("slug")
    man_reject = man_commands.add_parser("reject", help="rejeita a proposta (com motivo)")
    man_reject.add_argument("slug")
    man_reject.add_argument("--reason", required=True)

    args = parser.parse_args(argv)
    if not _writes_db(args):
        return _run(parser, args)
    label = "emmoni " + " ".join(sys.argv[1:] if argv is None else argv)
    try:
        with dblock.hold(label):
            return _run(parser, args)
    except dblock.DbLockError as error:
        print(f"emmoni: {error}", file=sys.stderr)
        return dblock.TIMEOUT_EXIT


# Subcomandos que escrevem no banco: tomam a trava (decisão 0025).
_DB_WRITERS = {
    ("ingest", None),
    ("crawl", None),
    ("catalog", "load"),
    ("taxonomy", "load"),
    ("review", "approve"),
    ("review", "restore"),
}


def _writes_db(args: argparse.Namespace) -> bool:
    sub = getattr(args, f"{args.command}_command", None)
    return (args.command, sub) in _DB_WRITERS


def _run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if args.command == "crawl":
        return _crawl(args.source, args.all, args.force)
    if args.command == "manifests":
        return _manifests(args)
    if args.command == "review":
        return _review(args)
    if args.command == "coverage":
        with db.connect() as conn:
            cov = coverage.write(conn)
        print(
            f"coverage: {cov.total} questões publicadas; {len(cov.not_loaded)} prova(s) fora do"
            f" banco, {len(cov.not_published)} não publicada(s), {len(cov.pending)} proposta(s)"
            f" pendente(s) → {coverage.COVERAGE_FILE}"
        )
        return 0
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
    failed: list[str] = []
    for exam in exams:
        print(f"{loaded.contest}/{exam.slug}")
        try:
            pipeline.ExamRun(loaded, exam).run(step)
        except LoadError as error:  # uma prova que não carrega não impede as seguintes
            print(f"  erro na carga: {error}")
            failed.append(exam.slug)
    if failed:
        print(f"ingest: {len(failed)} prova(s) não carregada(s): {', '.join(failed)}")
        return 1
    return 0


def _review(args: argparse.Namespace) -> int:
    try:
        exam_arg = getattr(args, "exam", None)
        ref = review.ExamRef.parse(exam_arg) if exam_arg else None
        with db.connect() as conn:
            if args.review_command == "topics":
                if args.report:
                    report = review.topic_sample_report(fetch.data_dir())
                    accuracy = f"{report.accuracy:.0%}" if report.accuracy is not None else "—"
                    print(
                        f"assuntos: {report.judged}/{report.total} conferidas,"
                        f" {report.ok} corretas ({accuracy})"
                    )
                else:
                    print(
                        f"amostra: {review.write_topic_sample(conn, args.n, fetch.data_dir(), args.seed)}"
                    )
            elif args.review_command == "list":
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
                page = review.write_sample(
                    conn, ref, args.n, fetch.data_dir(), args.also, args.seed
                )
                print(f"amostra: {page}")
            elif args.review_command == "approve":
                assert ref is not None
                published, left = review.approve(conn, ref, fetch.data_dir(), args.by)
                conn.commit()
                print(f"{ref} publicada: {published} questão(ões) visíveis, {left} fora")
            elif args.review_command == "restore":
                results = review.restore(conn)
                conn.commit()
                for exam, outcome in results:
                    print(f"{exam:<60} {outcome}")
                published = sum(outcome.startswith("publicada") for _, outcome in results)
                print(f"restore: {published} de {len(results)} prova(s) publicada(s)")
    except review.ReviewError as error:
        print(f"review: {error}")
        return 1
    return 0


def _crawl(source_slug: str | None, all_sources: bool, force: bool) -> int:
    listed = sources_module.load()
    if all_sources == bool(source_slug):
        print("crawl: informe uma fonte ou --all")
        return 2
    chosen = listed.sources if all_sources else [s for s in listed.sources if s.slug == source_slug]
    if not chosen:
        print(f"crawl: fonte {source_slug!r} não está em ingest/sources.yaml")
        return 2
    if not all_sources and chosen[0].crawler is None:
        print(f"crawl: a fonte {source_slug!r} não tem crawler (só a etapa fetch)")
        return 2
    known = catalog.load()
    failed = 0
    with db.connect() as conn:
        for source in chosen:
            if source.crawler is None:  # fonte só da etapa fetch
                continue
            try:
                report = crawl.run_source(
                    source,
                    CRAWLERS[source.crawler],
                    known,
                    conn,
                    data_dir=fetch.data_dir(),
                    manifests_dir=manifest.MANIFESTS_DIR,
                    client_factory=lambda: PoliteClient.from_env(listed),
                    force=force,
                )
            except CrawlError as error:  # configuração: nada foi gravado para esta fonte
                conn.rollback()
                print(f"crawl {source.slug}: {error}")
                return 2
            conn.commit()
            print("\n".join(report.lines()))
            failed += bool(report.blocked)  # erros pontuais ficam no relatório
    return 1 if failed else 0


def _manifests(args: argparse.Namespace) -> int:
    try:
        if args.manifests_command == "pending":
            paths = proposals.list_pending()
            for path in paths:
                loaded = manifest.load(path)
                print(f"{loaded.contest:<24} {len(loaded.exams)} prova(s)  {loaded.name}")
            print(f"manifests: {len(paths)} proposta(s) pendente(s)")
        elif args.manifests_command == "show":
            print(proposals.pending_path(args.slug).read_text(encoding="utf-8"), end="")
        elif args.manifests_command == "approve":
            print(f"aprovado: {proposals.approve(args.slug)}")
        elif args.manifests_command == "reject":
            print(f"rejeitado: {proposals.reject(args.slug, args.reason)}")
    except (proposals.ProposalError, FileNotFoundError) as error:
        print(f"manifests: {error}")
        return 1
    return 0
