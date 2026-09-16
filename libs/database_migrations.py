"""Ordered personal-library upgrades with backup and transactional rollback."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from libs.database_migrations_v4 import backup_database
from libs.database_migrations_v4 import migrate as migrate_v4
from libs.database_v5 import install

SCHEMA_VERSION = 5


def migrate(connection: sqlite3.Connection, filepath: Path) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema {version} is newer than supported {SCHEMA_VERSION}"
        )
    if version == SCHEMA_VERSION:
        return
    if connection.in_transaction:
        raise sqlite3.ProgrammingError(
            "Migration requires a connection without an active transaction"
        )
    if version < 4:
        migrate_v4(connection, filepath)
    if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise sqlite3.DatabaseError("Library integrity check failed")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    if version >= 4:
        backup_database(
            connection, filepath.with_name(f"{filepath.name}.pre-v5-{stamp}.bak")
        )
    try:
        connection.execute("BEGIN IMMEDIATE")
        install(connection)
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            raise sqlite3.IntegrityError("Library contains orphaned records")
        connection.execute("PRAGMA user_version=5")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
