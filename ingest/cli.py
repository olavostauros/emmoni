"""Comando `emmoni`."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from ingest import checks, db, taxonomy


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="emmoni")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="roda os checks de qualidade dos dados")
    check.add_argument("--checks-dir", type=Path, default=checks.CHECKS_DIR)

    tax = commands.add_parser("taxonomy", help="taxonomia de disciplinas e assuntos")
    tax_commands = tax.add_subparsers(dest="taxonomy_command", required=True)
    tax_load = tax_commands.add_parser("load", help="carrega db/taxonomy/*.yaml no banco")
    tax_load.add_argument("--dir", type=Path, default=taxonomy.TAXONOMY_DIR)

    args = parser.parse_args(argv)
    if args.command == "check":
        return _check(args.checks_dir)
    if args.command == "taxonomy":
        return _taxonomy_load(args.dir)
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
