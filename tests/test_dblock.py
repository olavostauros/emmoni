"""Trava do banco (decisão 0025): Python, scripts/db-lock.sh e o comando emmoni, sem banco."""

import fcntl
import io
import os
import shutil
import signal
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from ingest import cli, dblock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "db-lock.sh"
needs_flock = pytest.mark.skipif(shutil.which("flock") is None, reason="sem flock(1)")


@pytest.fixture(autouse=True)
def _lock_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    # `make test` roda sob a trava, com EMMONI_DB_LOCKED=1: aqui cada teste usa a sua.
    monkeypatch.delenv(dblock.LOCKED_ENV, raising=False)
    monkeypatch.delenv("EMMONI_DB_LOCK_WAIT", raising=False)
    path = tmp_path / "emmoni-db.lock"
    monkeypatch.setenv("EMMONI_DB_LOCK", str(path))
    return path


@contextmanager
def held_elsewhere(path: Path, who: str = "pid 4242 desde agora: make gates") -> Iterator[int]:
    """Outra descrição de arquivo segurando a trava (flock(2) é por descrição, não por processo)."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.ftruncate(fd, 0)
    os.write(fd, f"{who}\n".encode())
    try:
        yield fd
    finally:
        os.close(fd)


def test_lock_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMMONI_DB_LOCK")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1234")
    assert dblock.lock_path() == Path("/run/user/1234/emmoni-db.lock")
    monkeypatch.delenv("XDG_RUNTIME_DIR")
    assert dblock.lock_path() == Path("/tmp/emmoni-db.lock")
    monkeypatch.setenv("EMMONI_DB_LOCK", "/x/trava")
    assert dblock.lock_path() == Path("/x/trava")


def test_wait_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    assert dblock.wait_seconds() == 1800
    monkeypatch.setenv("EMMONI_DB_LOCK_WAIT", "5")
    assert dblock.wait_seconds() == 5
    monkeypatch.setenv("EMMONI_DB_LOCK_WAIT", "meia hora")
    with pytest.raises(dblock.DbLockError, match="EMMONI_DB_LOCK_WAIT"):
        dblock.wait_seconds()


def test_hold_records_holder_and_marks_children(_lock_env: Path) -> None:
    with dblock.hold("emmoni ingest pf-2021"):
        assert os.environ[dblock.LOCKED_ENV] == "1"
        text = _lock_env.read_text()
        assert f"pid {os.getpid()} " in text and "emmoni ingest pf-2021" in text
        with pytest.raises(BlockingIOError), held_elsewhere(_lock_env):
            pass
    assert dblock.LOCKED_ENV not in os.environ
    assert _lock_env.exists() and _lock_env.read_text() == ""
    with held_elsewhere(_lock_env):  # solta ao sair
        pass


def test_nested_hold_does_not_lock_again(_lock_env: Path) -> None:
    with dblock.hold("fora"), dblock.hold("dentro"):
        assert "fora" in _lock_env.read_text()


def test_parent_already_holds(monkeypatch: pytest.MonkeyPatch, _lock_env: Path) -> None:
    monkeypatch.setenv(dblock.LOCKED_ENV, "1")
    with held_elsewhere(_lock_env), dblock.hold("x", wait=0):
        pass


def test_waits_then_gets_the_lock(_lock_env: Path) -> None:
    out = io.StringIO()
    holder = os.open(_lock_env, os.O_RDWR | os.O_CREAT)
    fcntl.flock(holder, fcntl.LOCK_EX)
    os.write(holder, b"pid 4242 desde agora: make test\n")
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 2:
            os.close(holder)  # o outro termina

    with dblock.hold("emmoni crawl --all", wait=60, out=out, sleep=sleep):
        assert "emmoni crawl --all" in _lock_env.read_text()
    assert len(sleeps) == 2
    assert "banco ocupado (pid 4242 desde agora: make test)" in out.getvalue()


def test_times_out_without_removing_the_lock(_lock_env: Path) -> None:
    out = io.StringIO()
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    with (
        held_elsewhere(_lock_env),
        pytest.raises(dblock.DbLockTimeout, match="mais de 3 s"),
        dblock.hold("x", wait=3, out=out, sleep=sleep, clock=lambda: now[0]),
    ):
        pytest.fail("não devia obter a trava")
    assert now[0] == pytest.approx(3)
    assert _lock_env.read_text() == "pid 4242 desde agora: make gates\n"
    assert dblock.LOCKED_ENV not in os.environ


def test_cli_writer_waits_for_the_lock(
    monkeypatch: pytest.MonkeyPatch, _lock_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EMMONI_DB_LOCK_WAIT", "0")
    with held_elsewhere(_lock_env):
        assert cli.main(["catalog", "load"]) == dblock.TIMEOUT_EXIT
        assert cli.main(["review", "approve", "pf-2021/agente"]) == dblock.TIMEOUT_EXIT
    err = capsys.readouterr().err
    assert "banco ocupado (pid 4242" in err and "desisti de esperar" in err


def test_cli_readers_do_not_take_the_lock(monkeypatch: pytest.MonkeyPatch, _lock_env: Path) -> None:
    monkeypatch.setenv("EMMONI_DB_LOCK_WAIT", "0")
    with held_elsewhere(_lock_env):
        assert cli.main(["manifests", "pending"]) == 0


def _script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        timeout=30,
        check=False,
    )


@needs_flock
def test_script_holds_the_lock_for_the_command(_lock_env: Path) -> None:
    result = _script(
        "make gates",
        "sh",
        "-c",
        'echo "$EMMONI_DB_LOCKED"; cat "$EMMONI_DB_LOCK"; [ -e /dev/fd/9 ] && echo herdou || echo limpo',
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "1"
    assert lines[1].startswith("pid ") and lines[1].endswith(": make gates")
    assert lines[2] == "limpo"  # o comando não herda o descritor da trava
    assert _lock_env.read_text() == ""


@needs_flock
def test_script_passes_the_exit_status(_lock_env: Path) -> None:
    assert _script("x", "sh", "-c", "exit 3").returncode == 3


@needs_flock
def test_script_times_out_on_python_holder(_lock_env: Path) -> None:
    with dblock.hold("emmoni ingest pf-2021"):
        del os.environ[dblock.LOCKED_ENV]  # o script é outro "processo de fora"
        result = _script("make test", "true", env={"EMMONI_DB_LOCK_WAIT": "0"})
        os.environ[dblock.LOCKED_ENV] = "1"
    assert result.returncode == dblock.TIMEOUT_EXIT
    assert "banco ocupado (pid" in result.stderr and "emmoni ingest pf-2021" in result.stderr
    assert "desisti de esperar" in result.stderr


@needs_flock
def test_script_skips_when_parent_holds(_lock_env: Path) -> None:
    with held_elsewhere(_lock_env):
        result = _script("x", "true", env={"EMMONI_DB_LOCKED": "1", "EMMONI_DB_LOCK_WAIT": "0"})
    assert result.returncode == 0, result.stderr


@needs_flock
def test_python_waits_on_script_holder(_lock_env: Path) -> None:
    proc = subprocess.Popen(
        [str(SCRIPT), "make migrate", "sh", "-c", "echo pronto; sleep 30"],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        assert proc.stdout is not None and proc.stdout.readline() == "pronto\n"
        with (
            pytest.raises(dblock.DbLockTimeout, match="make migrate"),
            dblock.hold("x", wait=0, out=io.StringIO()),
        ):
            pass
    finally:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
