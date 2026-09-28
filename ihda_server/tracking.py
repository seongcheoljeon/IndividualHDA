"""Authorized server adapter for portable tracking storage."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection, text

from ihda_server.audit import record_event
from libs.version_tracking import VersionTracking


class ServerTrackingConnection:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        schema = (
            connection.get_execution_options().get("schema_translate_map", {}).get(None)
        )
        if schema and connection.dialect.name == "postgresql":
            quoted = connection.dialect.identifier_preparer.quote_schema(schema)
            connection.exec_driver_sql(f"SET LOCAL search_path TO {quoted}")

    def rows(self, sql: str, values: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            dict(row) for row in self.connection.execute(text(sql), values).mappings()
        ]

    def write(self, sql: str, values: dict[str, Any]) -> None:
        self.connection.execute(text(sql), values)


def team_tracking(connection: Connection, scope: str) -> VersionTracking:
    adapter = ServerTrackingConnection(connection)

    def versions(identities: list[str] | None) -> list[dict[str, Any]]:
        if identities == []:
            return []
        query = """SELECT v.uuid AS version_uuid,a.uuid AS asset_uuid,k.name,h.version,
            (a.deleted_at IS NULL AND v.deleted_at IS NULL) AS active FROM team_version_state v
            JOIN team_history h ON h.id=v.history_id JOIN team_asset_state a ON a.asset_id=h.asset_id
            JOIN team_assets k ON k.id=a.asset_id WHERE k.project_id=:scope"""
        values = {"scope": scope}
        if identities is not None:
            keys = ["identity_" + str(index) for index in range(len(identities))]
            query += " AND v.uuid IN (" + ",".join(":" + key for key in keys) + ")"
            values.update(zip(keys, identities, strict=True))
        return adapter.rows(query, values)

    def audit(
        actor: str, request_id: str, version: dict[str, Any], document: dict[str, Any]
    ) -> None:
        record_event(
            connection,
            scope,
            actor,
            "manual_check",
            {},
            {
                "asset_uuid": version["asset_uuid"],
                "version_uuid": version["version_uuid"],
                "check_id": request_id,
                "report": document,
            },
            request_id,
        )

    return VersionTracking(adapter, scope, versions, audit)


def verify_current(connection: Connection, scope: str) -> None:
    ServerTrackingConnection(connection)
    invalid = connection.execute(
        text("""SELECT a.asset_id FROM team_asset_state a JOIN team_assets k ON k.id=a.asset_id
        WHERE k.project_id=:scope AND a.current_version_uuid IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM team_version_state v JOIN team_history h ON h.id=v.history_id
        WHERE v.uuid=a.current_version_uuid AND h.asset_id=a.asset_id AND v.deleted_at IS NULL)"""),
        {"scope": scope},
    ).first()
    if invalid:
        raise ValueError("Current version must belong to this asset and be active")
