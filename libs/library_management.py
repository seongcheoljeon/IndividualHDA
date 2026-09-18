"""Focused local/HTTP adapters for library management views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, cast

from libs.database.lifecycle import PersonalLifecycle, inspect_files
from libs.database.rows import named_query
from libs.library_files import cleanup
from libs.paths import hda_base_dirpath
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.team.contracts import (
    DEFAULT_AUDIT_EVENT_LIMIT,
    Command,
    ManagementCatalog,
    Operation,
    TeamError,
)
from libs.team.pending import PendingCommand


class ManagementGateway(Protocol):
    def record_check(self, asset_id: int, body: dict[str, Any]) -> None: ...
    def tracking_read(
        self, kind: str, asset_uuid: str, offset: int = 0
    ) -> list[dict[str, Any]]: ...
    def dependents(self, item: dict[str, Any]) -> list[dict[str, Any]]: ...
    def trash(self) -> list[dict[str, Any]]: ...
    def change(self, item: dict[str, Any], operation: str) -> None: ...
    def details(self, asset_id: int) -> dict[str, Any]: ...
    def save_details(
        self, asset_id: int, version: dict[str, Any], values: dict[str, Any]
    ) -> None: ...
    def reclaim(self, apply: bool) -> list[dict[str, Any]]: ...
    @property
    def inspects_files(self) -> bool: ...
    def inspect(self) -> None: ...


class LocalManagement:
    def __init__(self, database: Path) -> None:
        self.database = database

    def trash(self) -> list[dict[str, Any]]:
        with SQLite3DatabaseAPI(self.database) as db:
            return PersonalLifecycle(db._connect).trash()

    def change(self, item: dict[str, Any], operation: str) -> None:
        with SQLite3DatabaseAPI(self.database) as db, db.transaction():
            PersonalLifecycle(db._connect).change(
                item["asset_id"], operation, item.get("history_id")
            )

    def details(self, asset_id: int) -> dict[str, Any]:
        with SQLite3DatabaseAPI(self.database) as db:
            identity = named_query(
                db._connect,
                "SELECT uuid FROM asset_identity WHERE asset_id=:asset_id AND deleted_at IS NULL",
                {"asset_id": asset_id},
            ).fetchone()
            if identity is None:
                raise ValueError("Asset no longer exists")
            from libs.database.tracking import local_tracking

            tracking = local_tracking(db._connect)
            versions = []
            for row in named_query(
                db._connect,
                """SELECT h.id,h.version,h.comment,v.details,v.uuid AS version_uuid
                FROM hda_history h JOIN version_identity v ON v.history_id=h.id
                WHERE h.hda_key_id=:asset_id AND v.deleted_at IS NULL ORDER BY h.id DESC""",
                {"asset_id": asset_id},
            ):
                versions.append(
                    {
                        "id": row["id"],
                        "version_uuid": row["version_uuid"],
                        "version": row["version"],
                        "snapshot": {
                            "description": row["comment"],
                            **json.loads(row["details"]),
                        },
                        "document": {
                            "description": row["comment"],
                            **json.loads(row["details"]),
                            "dependencies": tracking.dependencies(row["version_uuid"]),
                        },
                    }
                )
            events = [
                {
                    "operation": row["operation"],
                    "actor": row["actor"],
                    "occurred_at": row["occurred_at"],
                    "changes": json.loads(row["changes"]),
                }
                for row in named_query(
                    db._connect,
                    "SELECT operation,actor,occurred_at,changes FROM audit_events WHERE asset_uuid=:uuid ORDER BY occurred_at DESC LIMIT :DEFAULT_AUDIT_EVENT_LIMIT",
                    {
                        "uuid": identity["uuid"],
                        "DEFAULT_AUDIT_EVENT_LIMIT": DEFAULT_AUDIT_EVENT_LIMIT,
                    },
                )
            ]
            files = [
                {
                    "version": row["version"],
                    "kind": row["kind"],
                    "filename": row["filename"],
                    "status": row["status"],
                }
                for row in named_query(
                    db._connect,
                    "SELECT h.version,f.kind,f.filename,f.status FROM version_files f JOIN hda_history h ON h.id=f.history_id WHERE h.hda_key_id=:asset_id",
                    {"asset_id": asset_id},
                )
            ]
            from libs.database.tracking import local_tracking

            tracking = local_tracking(db._connect)
            return {
                "versions": versions,
                "events": events,
                "files": files,
                "asset_uuid": identity["uuid"],
                "tracking": {
                    kind: tracking.read(kind, identity["uuid"])
                    for kind in ("checks", "dependents", "scenes")
                },
            }

    def save_details(
        self, asset_id: int, version: dict[str, Any], values: dict[str, Any]
    ) -> None:
        with SQLite3DatabaseAPI(self.database) as db, db.transaction():
            row = named_query(
                db._connect,
                "SELECT h.hda_key_id,h.comment,v.details FROM hda_history h JOIN version_identity v ON v.history_id=h.id WHERE h.id=:id",
                {"id": version["id"]},
            ).fetchone()
            if (
                row is None
                or row["hda_key_id"] != asset_id
                or {"description": row["comment"], **json.loads(row["details"])}
                != version.get("snapshot", version["document"])
            ):
                raise ValueError("Version changed; reload before saving")
            PersonalLifecycle(db._connect).details(version["id"], values)

    def tracking_read(
        self, kind: str, asset_uuid: str, offset: int = 0
    ) -> list[dict[str, Any]]:
        from libs.database.tracking import local_tracking

        with SQLite3DatabaseAPI(self.database) as db:
            return local_tracking(db._connect).read(kind, asset_uuid, offset=offset)

    def record_check(self, asset_id: int, body: dict[str, Any]) -> None:
        from libs.database.tracking import local_tracking

        with SQLite3DatabaseAPI(self.database) as db, db.transaction():
            tracking = local_tracking(db._connect)
            version = tracking.version(body["values"]["version_uuid"])
            identity = named_query(
                db._connect,
                "SELECT uuid FROM asset_identity WHERE asset_id=:asset_id",
                {"asset_id": asset_id},
            ).fetchone()
            if identity is None or identity["uuid"] != version["asset_uuid"]:
                raise ValueError("Version belongs to a different asset")
            actor = db._connect.execute(
                "SELECT user_id FROM hda_key WHERE id=:asset_id", {"asset_id": asset_id}
            ).fetchone()[0]
            local_tracking(db._connect).execute(
                actor, body["request_id"], "check", body["values"]
            )

    def dependents(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        from libs.database.tracking import local_tracking

        with SQLite3DatabaseAPI(self.database) as db:
            asset = db._connect.execute(
                "SELECT uuid FROM asset_identity WHERE asset_id=:asset_id",
                {"asset_id": item["asset_id"]},
            ).fetchone()
            if not asset:
                return []
            uuid = None
            if item.get("history_id"):
                version = db._connect.execute(
                    "SELECT uuid FROM version_identity WHERE history_id=:history_id",
                    {"history_id": item["history_id"]},
                ).fetchone()
                uuid = version[0] if version else None
            return local_tracking(db._connect).read("dependents", asset[0], uuid)

    inspects_files = True

    def inspect(self) -> None:
        with SQLite3DatabaseAPI(self.database) as db:
            inspect_files(db._connect)

    def reclaim(self, apply: bool) -> list[dict[str, Any]]:
        """Files a purge queued for deletion: preview them, or delete the safe ones.

        Purging only removes rows; the files wait in file_cleanup so a failed
        delete never leaves the database pointing at nothing. cleanup() skips
        paths another version still references or that lie outside the library.
        """
        return cleanup(
            self.database,
            hda_base_dirpath(base_dirpath=self.database.parent),
            apply=apply,
        )


class RemoteManagement:
    def __init__(
        self, catalog: ManagementCatalog, pending: PendingCommand | None = None
    ) -> None:
        self.catalog = catalog
        self.pending = pending

    def _execute(self, command: Command) -> None:
        if self.pending is not None:
            if self.pending.load() is not None:
                raise TeamError(
                    "Close this dialog and resolve the pending request from the main panel first"
                )
            self.pending.save(command)
        try:
            self.catalog.execute(command)
        except TeamError as error:
            if self.pending is not None and error.status in {400, 403, 404, 409, 422}:
                self.pending.clear(command.request_id)
            raise
        else:
            if self.pending is not None:
                self.pending.clear(command.request_id)

    def reclaim(self, apply: bool) -> list[dict[str, Any]]:
        return []  # the server keeps its own blobs; nothing to free here

    inspects_files = False

    def inspect(self) -> None:
        return None  # file integrity is the server's job

    def trash(self) -> list[dict[str, Any]]:
        return list(self.catalog.trash())

    def change(self, item: dict[str, Any], operation: str) -> None:
        history_id = item.get("history_id")
        command = Command(
            cast(Operation, operation + ("_history" if history_id else "")),
            asset_id=item["asset_id"],
            expected_revision=item["revision"],
            values={"history_id": history_id} if history_id else {},
        )
        self._execute(command)

    def details(self, asset_id: int) -> dict[str, Any]:
        asset = self.catalog.get_asset(asset_id)
        versions = self.catalog.histories(asset_id)
        for version in versions:
            version["asset_revision"] = asset["revision"]
        tracking = (
            {
                kind: self.catalog.tracking_read(kind, asset["asset_uuid"])
                for kind in ("checks", "dependents", "scenes")
            }
            if self.catalog.tracking_supported()
            else None
        )
        return {
            "asset_uuid": asset["asset_uuid"],
            "tracking": tracking,
            "versions": versions,
            "events": self.catalog.events(asset["asset_uuid"]),
            "files": self.catalog.file_status(asset_id),
        }

    def save_details(
        self, asset_id: int, version: dict[str, Any], values: dict[str, Any]
    ) -> None:
        self._execute(
            Command(
                "version_details",
                asset_id=asset_id,
                expected_revision=version["asset_revision"],
                values={"history_id": version["id"], **values},
            )
        )

    def tracking_read(
        self, kind: str, asset_uuid: str, offset: int = 0
    ) -> list[dict[str, Any]]:
        return list(self.catalog.tracking_read(kind, asset_uuid, offset=offset))

    def record_check(self, asset_id: int, body: dict[str, Any]) -> None:
        self.catalog.tracking_execute(body)

    def dependents(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.catalog.tracking_supported():
            return []
        if item.get("asset_uuid"):
            return list(
                self.catalog.tracking_read(
                    "dependents", item["asset_uuid"], item.get("version_uuid")
                )
            )
        asset = self.catalog.get_asset(item["asset_id"])
        uuid = None
        if item.get("history_id"):
            uuid = next(
                (
                    h["document"]["version_uuid"]
                    for h in self.catalog.histories(item["asset_id"])
                    if h["id"] == item["history_id"]
                ),
                None,
            )
        return list(self.catalog.tracking_read("dependents", asset["asset_uuid"], uuid))
