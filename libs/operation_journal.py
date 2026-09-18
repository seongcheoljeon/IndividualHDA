"""Write-ahead rename journal with idempotent rollback and SQLite commit markers.

All paths are local absolute paths. Recovery never overwrites an existing path.
The operation lock prevents recovery from racing another active operation.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any

from libs.contracts import TransactionalRepository
from libs.legacy_documents import journal_moves_v1
from libs.settings_store import save_json


def sync_directory(directory: Path) -> None:
    # Windows does not expose directory fsync via Python's os.open. Written as a
    # sys.platform test, not os.name, because that is the form mypy narrows: it
    # then skips this branch on Windows, where os.O_DIRECTORY does not exist.
    if sys.platform != "win32":
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def sync_file(path: Path) -> None:
    """Flush a file this process did not open for writing.

    Windows implements os.fsync with _commit(), which calls FlushFileBuffers();
    that API requires GENERIC_WRITE, so fsync on a descriptor opened "rb" fails
    with OSError [Errno 9] Bad file descriptor. Open for update instead.
    """
    with path.open("rb+") as stream:
        os.fsync(stream.fileno())


def sync_tree(root: Path) -> None:
    """Flush staged archive content on its worker before activation."""
    for directory, _, filenames in os.walk(root, topdown=False):
        parent = Path(directory)
        for filename in filenames:
            sync_file(parent / filename)
        sync_directory(parent)


@contextmanager
def operation_lock(directory: Path) -> Iterator[None]:
    from PySide6.QtCore import QLockFile

    directory.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(directory / ".ihda-operation.lock"))
    lock.setStaleLockTime(0)  # only dead processes, never a slow live operation
    if not lock.tryLock(0):
        raise RuntimeError("Another library operation is active")
    try:
        yield
    finally:
        lock.unlock()


class MoveJournal:
    def __init__(self, directory: Path, database: Path | None = None) -> None:
        self.path = directory / f".ihda-operation-{uuid.uuid4().hex}.json"
        self.state: dict[str, Any] = {
            "version": 2,
            "id": self.path.stem,
            "committed": False,
            "database": str(database.resolve()) if database else None,
            "moves": [],
        }
        self._save()

    def _save(self) -> None:
        save_json(self.path, self.state)
        sync_directory(self.path.parent)

    def move(self, source: Path, destination: Path) -> None:
        source, destination = source.absolute(), destination.absolute()
        if source == destination:
            return
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        if not source.exists():
            raise FileNotFoundError(source)
        self.state["moves"].append(
            {"source": str(source), "destination": str(destination)}
        )
        self._save()  # Persist intent before mutation, including the crash window.
        source.rename(destination)
        sync_directory(source.parent)
        sync_directory(destination.parent)

    def _database_committed(self) -> bool:
        database = self.state["database"]
        if not database:
            return False
        # mode=rw prevents recovery from creating a missing/empty database.
        with closing(
            sqlite3.connect(Path(database).as_uri() + "?mode=rw", uri=True)
        ) as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM operation_commits WHERE operation_id = :id",
                    {"id": self.state["id"]},
                ).fetchone()
                is not None
            )

    def finish(self) -> None:
        self.state["committed"] = True
        self._save()
        self.path.unlink()
        sync_directory(self.path.parent)

    def rollback(self) -> None:
        while self.state["moves"]:
            move = self.state["moves"][-1]
            source, destination = Path(move["source"]), Path(move["destination"])
            if destination.exists() or destination.is_symlink():
                if source.exists() or source.is_symlink():
                    raise RuntimeError(
                        f"Recovery conflict: {source} and {destination}; both retained"
                    )
                destination.rename(source)
                sync_directory(destination.parent)
                sync_directory(source.parent)
            elif not source.exists():
                raise RuntimeError(
                    f"Recovery cannot find either {source} or {destination}"
                )
            self.state["moves"].pop()
            self._save()
        self.path.unlink()
        sync_directory(self.path.parent)


def recover_operations(directory: Path) -> list[Path]:
    recovered: list[Path] = []
    with operation_lock(directory):
        for path in sorted(directory.glob(".ihda-operation-*.json")):
            state = json.loads(path.read_text(encoding="utf-8"))
            if (
                type(state.get("version")) is not int
                or state["version"] not in (1, 2)
                or not isinstance(state.get("moves"), list)
            ):
                raise ValueError(f"Unsupported operation journal: {path}")
            if state["version"] == 1:
                state["moves"] = journal_moves_v1(state["moves"])
                state["version"] = 2
            for move in state["moves"]:
                if (
                    not isinstance(move, dict)
                    or set(move) != {"source", "destination"}
                    or not all(isinstance(value, str) for value in move.values())
                ):
                    raise ValueError(f"Invalid operation journal move: {path}")
            journal = object.__new__(MoveJournal)
            journal.path, journal.state = path, state
            if state["committed"] or journal._database_committed():
                journal.finish()
            else:
                journal.rollback()
            recovered.append(path)
    return recovered


@contextmanager
def durable_operation(
    directory: Path, db: TransactionalRepository | None = None
) -> Iterator[MoveJournal]:
    if db is not None and db.in_transaction:
        raise RuntimeError(
            "Durable file operations must own the outer database transaction"
        )
    with operation_lock(directory):
        journal = MoveJournal(directory, db.db_filepath if db else None)
        try:
            if db is None:
                yield journal
            else:
                with db.transaction():
                    yield journal
                    db.record_operation_commit(journal.state["id"])
        except BaseException:
            # Database transaction has rolled back before reversing file moves.
            journal.rollback()
            raise
        else:
            # If this write fails after SQLite committed, startup reads its marker.
            journal.finish()
