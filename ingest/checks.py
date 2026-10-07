"""Checks de qualidade dos dados (SPECIFICATIONS.md §8)."""

from dataclasses import dataclass
from pathlib import Path

import psycopg

CHECKS_DIR = Path(__file__).resolve().parent.parent / "db" / "checks"


@dataclass(frozen=True)
class CheckResult:
    name: str
    columns: list[str]
    violations: list[tuple[object, ...]]

    @property
    def ok(self) -> bool:
        return not self.violations


def run_checks(
    conn: psycopg.Connection[tuple[object, ...]], checks_dir: Path = CHECKS_DIR
) -> list[CheckResult]:
    """Roda cada `*.sql` de `checks_dir`, em ordem, numa transação somente leitura."""
    conn.read_only = True
    results = []
    with conn.transaction(force_rollback=True), conn.cursor() as cur:
        for path in sorted(checks_dir.glob("*.sql")):
            cur.execute(path.read_bytes())
            columns = [col.name for col in cur.description or []]
            results.append(CheckResult(path.stem, columns, cur.fetchall()))
    return results
