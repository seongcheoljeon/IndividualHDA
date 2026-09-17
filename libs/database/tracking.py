"""SQLite adapter for shared tracking operations. Caller owns the transaction."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from libs.database.rows import named_query
from libs.scene_outbox import SceneOutbox
from libs.version_tracking import VersionTracking


class SQLiteTrackingConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def rows(self, sql: str, values: dict[str, Any]) -> list[dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in cursor.execute(sql, values).fetchall()]
        finally:
            cursor.close()

    def write(self, sql: str, values: dict[str, Any]) -> None:
        self.connection.execute(sql, values)


def local_tracking(connection: sqlite3.Connection) -> VersionTracking:
    scope = connection.execute("SELECT uuid FROM library_identity").fetchone()[0]

    def versions(identities: list[str] | None) -> list[dict[str, Any]]:
        if identities == []:
            return []
        query = """SELECT a.asset_id,v.uuid AS version_uuid,a.uuid AS asset_uuid,k.name,h.version,
            (a.deleted_at IS NULL AND v.deleted_at IS NULL) AS active FROM version_identity v
            JOIN hda_history h ON h.id=v.history_id JOIN asset_identity a ON a.asset_id=h.hda_key_id JOIN hda_key k ON k.id=a.asset_id"""
        parameters = {
            f"version_{index}": value for index, value in enumerate(identities or [])
        }
        if identities is not None:
            query += (
                " WHERE v.uuid IN (" + ",".join(":" + key for key in parameters) + ")"
            )
        return [dict(row) for row in named_query(connection, query, parameters)]

    def audit(
        actor: str, request_id: str, version: dict[str, Any], document: dict[str, Any]
    ) -> None:
        from libs.database.lifecycle import PersonalLifecycle

        PersonalLifecycle(connection).event(
            version["asset_id"],
            "manual_check",
            {"check_id": request_id, "report": document},
            request_id,
            version["version_uuid"],
        )

    return VersionTracking(SQLiteTrackingConnection(connection), scope, versions, audit)


def deliver_local_scene_usage(database: Path, actor: str, outbox: SceneOutbox) -> int:
    """Deliver a captured outbox batch inside adapter-owned transactions."""
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    def execute(body: dict[str, Any]) -> None:
        with SQLite3DatabaseAPI(database) as db, db.transaction():
            local_tracking(db._connect).execute(
                actor, body["request_id"], "scene", body["values"]
            )

    return outbox.flush("local:" + str(database.resolve()), execute)
