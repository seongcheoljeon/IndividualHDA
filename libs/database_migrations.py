"""Versioned, atomic upgrades of existing iHDA libraries (no ID rewriting)."""

from __future__ import annotations
from pathlib import Path

from typing import Iterator
import pathlib
from datetime import datetime, timezone
import sqlite3
from contextlib import closing
import uuid

from libs.database_rebuild import rebuild_base_tables
from model.sqlite3_db_schema import db_schema, category_cleanup_trigger

SCHEMA_VERSION = 4


def backup_database(connection: sqlite3.Connection, destination: str | Path) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(destination))) as backup:
        connection.backup(backup)


def _statements(script: str) -> Iterator[str]:
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            yield statement
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete migration SQL")


def migrate(connection: sqlite3.Connection, filepath: pathlib.Path) -> None:
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
    existing = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    if existing:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError(
                "Library integrity check failed; original database retained"
            )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_database(
            connection,
            Path(filepath).with_name(
                f"{Path(filepath).name}.pre-v{SCHEMA_VERSION}-{stamp}-{uuid.uuid4().hex[:8]}.bak"
            ),
        )
    foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        if existing:
            rebuild_base_tables(connection, _statements(db_schema()))
        for statement in _statements(db_schema()):
            connection.execute(statement)
        for table, columns in {
            "hda_key": "user_id, category",
            "hda_history": "hda_key_id, version, id",
            "hda_note_history": "hda_key_id, hda_version, id",
            "hda_node_location_record": "hda_key_id, hip_dirpath, hip_filename",
            "houdini_node_category_path_info": "info_id",
            "houdini_node_type_path_info": "info_id",
            "houdini_node_input_connect_info": "info_id",
            "houdini_node_output_connect_info": "info_id",
        }.items():
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_lookup ON {table} ({columns})"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_user_date ON hda_history(userid, registration_datetime)"
        )
        connection.execute("DROP TRIGGER IF EXISTS delete_trg_unused_hda_category")
        connection.execute(category_cleanup_trigger())
        # Keep the legacy delimiter field readable by the old API, with normalized,
        # indexed tags maintained transactionally for every writer.
        connection.execute("""CREATE TABLE IF NOT EXISTS asset_tags (
            hda_key_id INTEGER NOT NULL REFERENCES hda_key(id) ON UPDATE CASCADE ON DELETE CASCADE,
            tag TEXT NOT NULL CHECK(length(tag) > 0), PRIMARY KEY(hda_key_id, tag))""")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_asset_tags_text ON asset_tags(tag COLLATE NOCASE, hda_key_id)"
        )
        split = """INSERT OR IGNORE INTO asset_tags(hda_key_id, tag)
            WITH RECURSIVE split(id, tag, rest) AS (
                SELECT hda_key_id, '', tag || '#' FROM tag_info {where}
                UNION ALL SELECT id, substr(rest, 1, instr(rest, '#') - 1),
                    substr(rest, instr(rest, '#') + 1) FROM split WHERE rest <> ''
            ) SELECT id, trim(tag) FROM split WHERE trim(tag) <> '';"""
        # tag_info is authoritative; rebuild to remove stale derived rows from v2.
        connection.execute("DELETE FROM asset_tags")
        connection.execute(split.format(where=""))
        for action in ("INSERT", "UPDATE"):
            connection.execute(f"DROP TRIGGER IF EXISTS sync_tags_{action.lower()}")
            previous = "old.hda_key_id, " if action == "UPDATE" else ""
            connection.execute(f"""CREATE TRIGGER IF NOT EXISTS sync_tags_{action.lower()}
                AFTER {action} ON tag_info BEGIN
                DELETE FROM asset_tags WHERE hda_key_id IN ({previous}new.hda_key_id);
                {split.format(where="WHERE hda_key_id = new.hda_key_id")}
                END""")
        connection.execute("""CREATE TRIGGER IF NOT EXISTS sync_tags_delete AFTER DELETE ON tag_info
            BEGIN DELETE FROM asset_tags WHERE hda_key_id = old.hda_key_id; END""")
        # Table CHECK constraints now validate every writer, including INSERT and UPDATE.
        for action in ("insert", "update"):
            connection.execute(f"DROP TRIGGER IF EXISTS validate_hda_info_{action}")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_asset_latest ON hda_history(hda_key_id, id)"
        )
        for table, reference_columns in {
            "hda_info": ("filename",),
            "thumbnail_info": ("filename",),
            "video_info": ("filename",),
            "hda_history": ("hda_filename", "thumb_filename", "video_filename"),
        }.items():
            for column in reference_columns:
                connection.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_{column}_reference "
                    f"ON {table}({column} COLLATE NOCASE)"
                )
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            raise sqlite3.IntegrityError(
                "Library contains orphaned records; original database retained"
            )
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.execute(f"PRAGMA foreign_keys={foreign_keys}")
