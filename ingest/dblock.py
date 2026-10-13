"""Trava do banco: um comando que escreve no Postgres por vez na máquina (decisão 0025).

O Postgres do docker compose é um só para todos os worktrees (decisão 0019). Quem chega com o
banco ocupado espera a trava, até `EMMONI_DB_LOCK_WAIT` segundos, em vez de perguntar a alguém.
A mesma trava é tomada pelo Makefile (`scripts/db-lock.sh`, com `flock(1)`) e por aqui (com
`fcntl.flock`); as duas usam `flock(2)` sobre o mesmo arquivo e se enxergam.

- arquivo: `EMMONI_DB_LOCK`, ou `${XDG_RUNTIME_DIR:-/tmp}/emmoni-db.lock`;
- espera máxima: `EMMONI_DB_LOCK_WAIT` segundos (padrão 1800);
- `EMMONI_DB_LOCKED` definido: um processo pai já segura a trava; não trava de novo.

O arquivo nunca é apagado: o conteúdo (PID e comando de quem segura) é só informativo, e a
trava é do kernel, que a solta quando o processo termina.
"""

import fcntl
import os
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

DEFAULT_WAIT = 1800.0
POLL_SECONDS = 1.0
LOCKED_ENV = "EMMONI_DB_LOCKED"
TIMEOUT_EXIT = 75  # EX_TEMPFAIL: tente de novo mais tarde (o mesmo de scripts/db-lock.sh)


class DbLockError(Exception):
    """A trava não foi obtida (tempo de espera esgotado ou configuração inválida)."""


class DbLockTimeout(DbLockError):
    """A trava não foi obtida dentro do tempo de espera."""


def lock_path() -> Path:
    explicit = os.environ.get("EMMONI_DB_LOCK")
    if explicit:
        return Path(explicit)
    return Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp") / "emmoni-db.lock"


def wait_seconds() -> float:
    raw = os.environ.get("EMMONI_DB_LOCK_WAIT")
    if not raw:
        return DEFAULT_WAIT
    try:
        value = float(raw)
    except ValueError as error:
        raise DbLockError(f"EMMONI_DB_LOCK_WAIT deve ser um número de segundos: {raw!r}") from error
    return max(value, 0.0)


def holder(path: Path) -> str:
    """Quem segura a trava, como gravado no arquivo (pode estar velho se ninguém segura)."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return text.splitlines()[0] if text else ""


def _try_lock(fd: int) -> bool:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


@contextmanager
def hold(
    label: str,
    *,
    path: Path | None = None,
    wait: float | None = None,
    out: TextIO | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Iterator[None]:
    """Segura a trava do banco durante o bloco; espera se outro processo a tem."""
    if os.environ.get(LOCKED_ENV):
        yield
        return
    path = path or lock_path()
    wait = wait_seconds() if wait is None else wait
    out = out or sys.stderr
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if not _try_lock(fd):
            who = holder(path) or "quem segura não se identificou"
            print(
                f"banco ocupado ({who}); esperando a trava {path} por até {wait:.0f} s",
                file=out,
                flush=True,
            )
            deadline = clock() + wait
            while not _try_lock(fd):
                if clock() >= deadline:
                    raise DbLockTimeout(
                        f"banco ocupado há mais de {wait:.0f} s ({holder(path) or 'sem dono'});"
                        f" desisti de esperar a trava {path}"
                    )
                sleep(min(POLL_SECONDS, max(deadline - clock(), 0.0)))
        since = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        os.ftruncate(fd, 0)
        os.pwrite(fd, f"pid {os.getpid()} desde {since}: {label}\n".encode(), 0)
        os.environ[LOCKED_ENV] = "1"  # subprocessos herdam: não travam de novo
        try:
            yield
        finally:
            os.environ.pop(LOCKED_ENV, None)
            os.ftruncate(fd, 0)
    finally:
        os.close(fd)  # solta a trava
