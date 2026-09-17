"""Portable version tracking rules and transactional storage; no Qt or HTTP."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from libs.library_metadata import utc_now, validate_version_details
from libs.search_limits import TEAM_PAGE_DEFAULT, TEAM_PAGE_MAX

CAPABILITY = "version_tracking"


def schema_statements() -> tuple[str, ...]:
    return (
        """CREATE TABLE version_dependencies (scope_id TEXT NOT NULL, source_uuid TEXT NOT NULL,
        ordinal INTEGER NOT NULL, target_scope TEXT, target_asset TEXT, target_version TEXT,
        kind TEXT NOT NULL, target TEXT NOT NULL, version TEXT NOT NULL, required INTEGER NOT NULL CHECK(required IN (0,1)),
        source TEXT NOT NULL, PRIMARY KEY(scope_id,source_uuid,ordinal))""",
        "CREATE INDEX idx_dependency_target ON version_dependencies(target_scope,target_asset,target_version)",
        """CREATE TABLE version_checks (scope_id TEXT NOT NULL, id TEXT NOT NULL, version_uuid TEXT NOT NULL,
        asset_uuid TEXT NOT NULL, actor TEXT NOT NULL, checked_at TEXT NOT NULL, created_at TEXT NOT NULL,
        document TEXT NOT NULL, PRIMARY KEY(scope_id,id))""",
        "CREATE INDEX idx_checks_version ON version_checks(scope_id,version_uuid,created_at,id)",
        """CREATE TABLE scene_usages (scope_id TEXT NOT NULL,id TEXT NOT NULL,actor TEXT NOT NULL,
        client_id TEXT NOT NULL,scene_key TEXT NOT NULL,node_path TEXT NOT NULL,asset_uuid TEXT NOT NULL,
        version_uuid TEXT NOT NULL,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,document TEXT NOT NULL,
        PRIMARY KEY(scope_id,id),UNIQUE(scope_id,actor,client_id,scene_key,node_path,version_uuid))""",
        "CREATE INDEX idx_scene_version ON scene_usages(scope_id,asset_uuid,version_uuid,last_seen,id)",
        """CREATE TABLE tracking_requests (scope_id TEXT NOT NULL,actor TEXT NOT NULL,id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(scope_id,actor,id))""",
        """CREATE TABLE registration_jobs (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
        phase TEXT NOT NULL, document TEXT NOT NULL, result TEXT, error TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    )


class TrackingConnection(Protocol):
    def rows(self, sql: str, values: dict[str, Any]) -> list[dict[str, Any]]: ...
    def write(self, sql: str, values: dict[str, Any]) -> None: ...


def _text(
    values: dict[str, Any], name: str, maximum: int = 1000, *, optional: bool = False
) -> str:
    value = values.get(name, "")
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (not optional and not value.strip())
    ):
        raise ValueError(f"Invalid {name}")
    return value


def validate_tracking(operation: str, values: dict[str, Any]) -> None:
    if len(json.dumps(values).encode()) > 64 * 1024:
        raise ValueError("Tracking record is too large")
    UUID(_text(values, "version_uuid", 36))
    if operation == "check":
        allowed = {
            "version_uuid",
            "houdini_version",
            "os",
            "scope",
            "result",
            "notes",
            "checked_at",
            "supersedes",
            "provenance",
        }
        for field in ("houdini_version", "os", "scope"):
            _text(values, field, 240)
        if values.get("result") not in {"passed", "failed"}:
            raise ValueError("A manual check must pass or fail")
        _text(values, "notes", 16000, optional=True)
        moment = datetime.fromisoformat(_text(values, "checked_at", 60))
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("Check time requires a timezone")
        if values.get("supersedes"):
            UUID(_text(values, "supersedes", 36))
    elif operation == "scene":
        allowed = {
            "version_uuid",
            "client_id",
            "scene_key",
            "previous_scene_key",
            "scene_path",
            "node_path",
            "houdini_version",
            "os",
        }
        UUID(_text(values, "client_id", 36))
        for field in ("scene_key", "node_path", "houdini_version", "os"):
            _text(values, field, 4096)
        _text(values, "scene_path", 4096, optional=True)
        _text(values, "previous_scene_key", 4096, optional=True)
    else:
        raise ValueError("Unsupported tracking operation")
    if set(values) - allowed:
        raise ValueError("Unknown tracking fields")


class VersionTracking:
    def __init__(
        self,
        connection: TrackingConnection,
        scope: str,
        versions: Callable[[list[str] | None], list[dict[str, Any]]],
        audit: Callable[[str, str, dict[str, Any], dict[str, Any]], None] | None = None,
    ) -> None:
        self.connection, self.scope, self.versions = connection, scope, versions
        self.audit = audit

    def version(self, uuid: str) -> dict[str, Any]:
        for item in self.versions([uuid]):
            if item["version_uuid"] == uuid and item["active"]:
                return item
        raise ValueError("Version is unavailable in this library")

    def replace_dependencies(
        self, uuid: str, dependencies: list[dict[str, Any]]
    ) -> None:
        validate_version_details({"dependencies": dependencies})
        versions = self.versions(None)
        existing = self.dependencies(uuid)
        self.connection.write(
            "DELETE FROM version_dependencies WHERE scope_id=:scope AND source_uuid=:uuid",
            {"scope": self.scope, "uuid": uuid},
        )
        for ordinal, dependency in enumerate(dependencies):
            dependency = dict(dependency)
            # Preserve a previously resolved identity when an older client resaves
            # the unchanged text projection after a target rename or removal.
            if not dependency.get("asset_uuid") and not dependency.get("version_uuid"):
                matches = [
                    old
                    for old in existing
                    if all(
                        old.get(key, "") == dependency.get(key, "")
                        for key in ("kind", "target", "version", "source")
                    )
                ]
                if len(matches) == 1:
                    for key in ("library_uuid", "asset_uuid", "version_uuid"):
                        dependency[key] = matches[0].get(key)
            target_scope = dependency.get("library_uuid") or self.scope
            asset, version = (
                dependency.get("asset_uuid"),
                dependency.get("version_uuid"),
            )
            candidates = (
                [
                    v
                    for v in versions
                    if v["active"]
                    and target_scope == self.scope
                    and (
                        v["asset_uuid"] == asset
                        if asset
                        else v["name"] == dependency["target"]
                    )
                    and (
                        v["version_uuid"] == version
                        if version
                        else not dependency.get("version")
                        or v["version"] == dependency["version"]
                    )
                ]
                if dependency["kind"] == "asset"
                else []
            )
            if version and target_scope == self.scope:
                identified = next(
                    (item for item in versions if item["version_uuid"] == version), None
                )
                if identified and asset and identified["asset_uuid"] != asset:
                    raise ValueError("Dependency version belongs to another asset")
                if identified:
                    asset = identified["asset_uuid"]
            if len(candidates) == 1:
                asset, version = (
                    candidates[0]["asset_uuid"],
                    candidates[0]["version_uuid"],
                )
            values = {
                "scope": self.scope,
                "uuid": uuid,
                "ordinal": ordinal,
                "target_scope": target_scope,
                "target_asset": asset,
                "target_version": version,
                "kind": dependency["kind"],
                "target": dependency["target"],
                "version": dependency.get("version", ""),
                "required": int(dependency.get("required", True)),
                "source": dependency.get("source", ""),
            }
            self.connection.write(
                """INSERT INTO version_dependencies (scope_id,source_uuid,ordinal,target_scope,target_asset,target_version,kind,target,version,required,source) VALUES(:scope,:uuid,:ordinal,:target_scope,:target_asset,
                :target_version,:kind,:target,:version,:required,:source)""",
                values,
            )

    def dependencies(self, uuid: str) -> list[dict[str, Any]]:
        result = []
        rows = self.connection.rows(
            "SELECT * FROM version_dependencies WHERE scope_id=:scope AND source_uuid=:uuid ORDER BY ordinal",
            {"scope": self.scope, "uuid": uuid},
        )
        live = {
            v["version_uuid"]: v
            for v in self.versions(
                [
                    row["target_version"]
                    for row in rows
                    if row["target_scope"] == self.scope and row["target_version"]
                ]
            )
            if v["active"]
        }
        for row in rows:
            result.append(
                {
                    "kind": row["kind"],
                    "target": row["target"],
                    "version": row["version"],
                    "required": bool(row["required"]),
                    "source": row["source"],
                    "library_uuid": row["target_scope"],
                    "asset_uuid": row["target_asset"],
                    "version_uuid": row["target_version"],
                    "resolution": "resolved"
                    if row["target_scope"] == self.scope
                    and row["target_version"] in live
                    else "missing"
                    if row["target_scope"] == self.scope and row["target_version"]
                    else "unresolved",
                }
            )
        return result

    def read(
        self,
        kind: str,
        asset_uuid: str,
        version_uuid: str | None = None,
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> list[dict[str, Any]]:
        if offset < 0 or not 1 <= limit <= TEAM_PAGE_MAX:
            raise ValueError("Invalid tracking page")
        values = {
            "scope": self.scope,
            "asset": asset_uuid,
            "uuid": version_uuid,
            "offset": offset,
            "limit": limit,
        }
        if kind == "dependents":
            rows = self.connection.rows(
                """SELECT * FROM version_dependencies WHERE scope_id=:scope AND target_scope=:scope AND target_asset=:asset
                AND (CAST(:uuid AS TEXT) IS NULL OR target_version=:uuid OR target_version IS NULL) ORDER BY source_uuid,ordinal LIMIT :limit OFFSET :offset""",
                values,
            )
            versions = {
                v["version_uuid"]: v
                for v in self.versions([row["source_uuid"] for row in rows])
            }
            return [
                {**row, "source_version": versions[row["source_uuid"]]}
                for row in rows
                if row["source_uuid"] in versions
            ]
        table = {"checks": "version_checks", "scenes": "scene_usages"}.get(kind)
        if table is None:
            raise ValueError("Invalid tracking query")
        order = "created_at" if kind == "checks" else "last_seen"
        rows = self.connection.rows(
            f"SELECT * FROM {table} WHERE scope_id=:scope AND asset_uuid=:asset AND (CAST(:uuid AS TEXT) IS NULL OR version_uuid=:uuid) ORDER BY {order} DESC,id LIMIT :limit OFFSET :offset",
            values,
        )
        return [{**row, "document": json.loads(row["document"])} for row in rows]

    def execute(
        self, actor: str, request_id: str, operation: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(request_id, str):
            raise ValueError("Invalid request ID")
        UUID(request_id)
        validate_tracking(operation, values)
        fingerprint = hashlib.sha256(
            json.dumps(
                [operation, values], sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        key = {"scope": self.scope, "actor": actor, "id": request_id}
        receipts = self.connection.rows(
            "SELECT * FROM tracking_requests WHERE scope_id=:scope AND actor=:actor AND id=:id",
            key,
        )
        if receipts:
            if receipts[0]["fingerprint"] != fingerprint:
                raise ValueError("Request ID belongs to different content")
            return dict(json.loads(receipts[0]["result"]))
        if self.connection.rows(
            "SELECT id FROM version_checks WHERE scope_id=:scope AND id=:id UNION ALL SELECT id FROM scene_usages WHERE scope_id=:scope AND id=:id",
            key,
        ):
            raise ValueError("Request ID belongs to another actor or operation")
        version = self.version(values["version_uuid"])
        now = utc_now()
        document = {
            **values,
            "asset_name": version["name"],
            "version": version["version"],
        }
        if operation == "check":
            if values.get("supersedes") and not self.connection.rows(
                "SELECT id FROM version_checks WHERE scope_id=:scope AND id=:id AND version_uuid=:uuid",
                {
                    "scope": self.scope,
                    "id": values["supersedes"],
                    "uuid": values["version_uuid"],
                },
            ):
                raise ValueError("Correction must refer to a check of this version")
            document["method"] = "manual"
            self.connection.write(
                "INSERT INTO version_checks (scope_id,id,version_uuid,asset_uuid,actor,checked_at,created_at,document) VALUES(:scope,:id,:uuid,:asset,:actor,:checked,:now,:document)",
                dict(
                    **key,
                    uuid=values["version_uuid"],
                    asset=version["asset_uuid"],
                    checked=values["checked_at"],
                    now=now,
                    document=json.dumps(document),
                ),
            )
            if self.audit is not None:
                self.audit(actor, request_id, version, document)
        else:
            record = dict(
                **key,
                client=values["client_id"],
                scene=values["scene_key"],
                node=values["node_path"],
                asset=version["asset_uuid"],
                uuid=values["version_uuid"],
                now=now,
                first=now,
                document=json.dumps(document),
            )
            if values.get("previous_scene_key", "").startswith("unsaved:"):
                previous = self.connection.rows(
                    "SELECT first_seen FROM scene_usages WHERE scope_id=:scope AND actor=:actor AND client_id=:client AND scene_key=:previous AND node_path=:node AND version_uuid=:uuid",
                    {**record, "previous": values["previous_scene_key"]},
                )
                if previous:
                    record["first"] = previous[0]["first_seen"]
                self.connection.write(
                    "DELETE FROM scene_usages WHERE scope_id=:scope AND actor=:actor AND client_id=:client AND scene_key=:previous AND node_path=:node AND version_uuid=:uuid",
                    {**record, "previous": values["previous_scene_key"]},
                )
            self.connection.write(
                """INSERT INTO scene_usages (scope_id,id,actor,client_id,scene_key,node_path,asset_uuid,version_uuid,first_seen,last_seen,document) VALUES(:scope,:id,:actor,:client,:scene,:node,:asset,:uuid,:first,:now,:document)
                ON CONFLICT(scope_id,actor,client_id,scene_key,node_path,version_uuid) DO UPDATE SET first_seen=CASE WHEN scene_usages.first_seen<excluded.first_seen THEN scene_usages.first_seen ELSE excluded.first_seen END,last_seen=excluded.last_seen,document=excluded.document""",
                record,
            )
        result = {
            "id": request_id,
            "version_uuid": values["version_uuid"],
            "recorded_at": now,
        }
        self.connection.write(
            "INSERT INTO tracking_requests (scope_id,actor,id,fingerprint,result) VALUES(:scope,:actor,:id,:fingerprint,:result)",
            {**key, "fingerprint": fingerprint, "result": json.dumps(result)},
        )
        return result
