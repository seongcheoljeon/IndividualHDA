"""Authorized server adapter for portable tracking storage."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Connection, text

from ihda_server import tracking_schema
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
        from ihda_server.lifecycle import LifecycleStore

        LifecycleStore.event(
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


def install(connection: Connection) -> None:
    ServerTrackingConnection(connection)
    for table in tracking_schema.TABLES:
        table.create(connection, checkfirst=True)
    for scope in connection.execute(text("SELECT id FROM team_projects")).scalars():
        tracking = team_tracking(connection, scope)
        for row in connection.execute(
            text(
                "SELECT v.uuid,v.details FROM team_version_state v JOIN team_history h ON h.id=v.history_id WHERE h.project_id=:scope"
            ),
            {"scope": scope},
        ).mappings():
            details = (
                json.loads(row["details"])
                if isinstance(row["details"], str)
                else row["details"]
            )
            tracking.replace_dependencies(row["uuid"], details.get("dependencies", []))

    # Preserve evidence of damaged legacy pointers before clearing them.
    invalid = (
        connection.execute(
            text("""SELECT a.asset_id,a.uuid,a.current_version_uuid,k.project_id FROM team_asset_state a JOIN team_assets k ON k.id=a.asset_id
        WHERE a.current_version_uuid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM team_version_state v JOIN team_history h ON h.id=v.history_id
        WHERE v.uuid=a.current_version_uuid AND h.asset_id=a.asset_id AND v.deleted_at IS NULL)""")
        )
        .mappings()
        .all()
    )
    from ihda_server.lifecycle import LifecycleStore

    for row in invalid:
        LifecycleStore.event(
            connection,
            row["project_id"],
            "migration",
            "repair_current_version",
            {"asset_uuid": row["uuid"], "version_uuid": row["current_version_uuid"]},
            {"asset_uuid": row["uuid"], "version_uuid": None},
        )
        connection.execute(
            text(
                "UPDATE team_asset_state SET current_version_uuid=NULL WHERE asset_id=:id"
            ),
            {"id": row["asset_id"]},
        )
    if connection.dialect.name == "postgresql":
        from sqlalchemy import inspect

        schema = (
            connection.get_execution_options().get("schema_translate_map", {}).get(None)
        )
        constraints = inspect(connection).get_foreign_keys(
            "team_asset_state", schema=schema
        )
        if not any(item["name"] == "fk_current_version" for item in constraints):
            connection.exec_driver_sql(
                "ALTER TABLE team_asset_state ADD CONSTRAINT fk_current_version FOREIGN KEY(current_version_uuid) REFERENCES team_version_state(uuid) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED"
            )


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
