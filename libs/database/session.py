"""Connection lifecycle, backup and transaction boundaries."""

from __future__ import annotations

import pathlib
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Self

from libs.database.policy import SQLitePolicy
from libs.database_migrations import backup_database, migrate


class DatabaseSession:
    def __init__(
        self,
        db_filepath: str | pathlib.Path | None = None,
        *,
        policy: SQLitePolicy = SQLitePolicy(),
    ) -> None:
        if db_filepath is None:
            raise ValueError("Database path is required")
        self._db_filepath = pathlib.Path(db_filepath)
        self._connection: sqlite3.Connection | None = None
        self._db_cursor: sqlite3.Cursor | None = None
        self._transaction_depth = 0
        try:
            self._connection = sqlite3.connect(
                str(self._db_filepath), timeout=policy.connect_timeout_seconds
            )
            self._connect.execute("PRAGMA foreign_keys = ON")
            self._connect.execute(f"PRAGMA busy_timeout = {policy.busy_timeout_ms}")
            # WAL: readers (search worker, revision poller, a second panel) no longer
            # block writers. Persistent; requires a local filesystem (see README).
            self._connect.execute("PRAGMA journal_mode = WAL")
            migrate(self._connect, self._db_filepath)
            self._db_cursor = self._connect.cursor()
        except BaseException:
            self.close()
            raise

    @property
    def _connect(self) -> sqlite3.Connection:
        if self._connection is None:
            raise sqlite3.ProgrammingError("Database is closed")
        return self._connection

    @property
    def _cursor(self) -> sqlite3.Cursor:
        if self._db_cursor is None:
            raise sqlite3.ProgrammingError("Database is closed")
        return self._db_cursor

    def close(self) -> None:
        if self._db_cursor is not None:
            self._db_cursor.close()
            self._db_cursor = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __del__(self) -> None:
        if getattr(self, "_connection", None) is not None:
            self.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @property
    def db_filepath(self) -> pathlib.Path:
        return self._db_filepath

    def create_tables(self) -> bool:
        migrate(self._connect, self._db_filepath)
        return True

    def backup(self, destination: str | pathlib.Path) -> None:
        backup_database(self._connect, destination)

    @contextmanager
    def transaction(self) -> Iterator[Self]:
        """Group existing API mutations atomically; failed writes abort the group."""
        outer = self._transaction_depth == 0
        if outer:
            self._connect.execute("BEGIN IMMEDIATE")
            from libs.library_metadata import new_identity

            self._connect.execute(
                "UPDATE write_context SET request_id=:new_identity",
                {"new_identity": new_identity()},
            )
        savepoint = f"ihda_nested_{self._transaction_depth}"
        if not outer:
            self._connect.execute(f"SAVEPOINT {savepoint}")
        self._transaction_depth += 1
        try:
            yield self
            if outer:
                self._connect.execute("UPDATE write_context SET request_id=NULL")
                self._connect.commit()
            else:
                self._connect.execute(f"RELEASE SAVEPOINT {savepoint}")
        except BaseException:
            if outer:
                self._connect.rollback()
            else:
                self._connect.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self._connect.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        finally:
            self._transaction_depth -= 1

    def _commit(self) -> None:
        if not self._transaction_depth:
            self._connect.commit()

    def _rollback(self) -> None:
        if self._transaction_depth:
            raise sqlite3.DatabaseError(
                "Transaction aborted by a failed database operation"
            )
        self._connect.rollback()

    @property
    def in_transaction(self) -> bool:
        return self._connect.in_transaction

    def record_operation_commit(self, operation_id: str) -> None:
        if not self._transaction_depth:
            raise sqlite3.ProgrammingError(
                "Operation markers require an active transaction"
            )
        self._connect.execute(
            "INSERT INTO operation_commits(operation_id) VALUES (:operation_id)",
            {"operation_id": operation_id},
        )

    @property
    def get_last_insert_id(self) -> int | None:
        return self._cursor.lastrowid
