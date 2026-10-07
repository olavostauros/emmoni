"""Comando `emmoni`."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from ingest import checks, db


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="emmoni")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="roda os checks de qualidade dos dados")
    check.add_argument("--checks-dir", type=Path, default=checks.CHECKS_DIR)

    args = parser.parse_args(argv)
    if args.command == "check":
        return _check(args.checks_dir)
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
