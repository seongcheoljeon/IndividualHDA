"""Transactional table reconstruction for schema v4 (called with foreign keys off)."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable

from libs.database.rows import named_query


def _quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def rebuild_base_tables(
    connection: sqlite3.Connection, statements: Iterable[str]
) -> None:
    """Copy into constrained tables, retaining IDs, sequence watermarks and SQL objects.

    The caller owns backup, transaction, foreign-key checking and PRAGMA restoration.
    Unknown columns are rejected rather than silently discarded. Copy failures leave
    the original database available for rollback with the offending table named.
    """
    if (
        not connection.in_transaction
        or connection.execute("PRAGMA foreign_keys").fetchone()[0]
    ):
        raise sqlite3.ProgrammingError(
            "Rebuild requires a transaction with foreign keys disabled"
        )
    objects = named_query(
        connection,
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ('trigger', 'view', 'index') AND sql IS NOT NULL "
        "ORDER BY CASE type WHEN 'view' THEN 0 WHEN 'index' THEN 1 ELSE 2 END",
    ).fetchall()
    # Triggers on other tables and chained views can also reference rebuilt tables.
    for obj in objects:
        if obj["type"] in ("trigger", "view"):
            connection.execute(f"DROP {obj['type'].upper()} {_quoted(obj['name'])}")
    has_sequence = (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'"
        ).fetchone()
        is not None
    )
    for statement in statements:
        match = re.match(r"\s*CREATE TABLE IF NOT EXISTS (\w+)", statement)
        if match is None:
            continue
        table = match.group(1)
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=:table",
            {"table": table},
        ).fetchone():
            continue
        temporary = f"__ihda_v4_{table}"
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name=:temporary",
            {"temporary": temporary},
        ).fetchone():
            raise sqlite3.DatabaseError(
                f"Migration temporary name already exists: {temporary}"
            )
        sequence = (
            connection.execute(
                "SELECT seq FROM sqlite_sequence WHERE name=:table", {"table": table}
            ).fetchone()
            if has_sequence
            else None
        )
        ddl = statement[: match.start(1)] + temporary + statement[match.end(1) :]
        connection.execute(ddl)
        old_columns = [
            row["name"]
            for row in named_query(connection, f"PRAGMA table_xinfo({_quoted(table)})")
        ]
        new_columns = [
            row["name"]
            for row in named_query(
                connection, f"PRAGMA table_xinfo({_quoted(temporary)})"
            )
        ]
        if set(old_columns) != set(new_columns):
            raise sqlite3.DatabaseError(
                f"Unexpected columns in {table}; migration aborted without discarding data"
            )
        columns = ", ".join(map(_quoted, old_columns))
        try:
            connection.execute(
                f"INSERT INTO {_quoted(temporary)} ({columns}) SELECT {columns} FROM {_quoted(table)}"
            )
        except sqlite3.IntegrityError as error:
            raise sqlite3.IntegrityError(
                f"Cannot upgrade {table}: {error}; original data retained"
            ) from error
        connection.execute(f"DROP TABLE {_quoted(table)}")
        connection.execute(
            f"ALTER TABLE {_quoted(temporary)} RENAME TO {_quoted(table)}"
        )
        if sequence is not None:
            # MAX(id) alone would reuse IDs of previously deleted rows.
            connection.execute(
                "DELETE FROM sqlite_sequence WHERE name=:table", {"table": table}
            )
            connection.execute(
                "INSERT INTO sqlite_sequence(name, seq) VALUES (:table, :value)",
                {"table": table, "value": sequence[0]},
            )
    for obj in objects:
        name, sql = obj["name"], obj["sql"]
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name=:name", {"name": name}
        ).fetchone():
            connection.execute(sql)
