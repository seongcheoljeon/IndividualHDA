"""Focused local/HTTP adapters for library management views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, cast

from libs.database.lifecycle import PersonalLifecycle, inspect_files
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.team.contracts import Command, Operation, TeamError
from libs.team.limits import DEFAULT_AUDIT_EVENT_LIMIT
from libs.team.pending import PendingCommand


class ManagementGateway(Protocol):
    def trash(self) -> list[dict[str, Any]]: ...
    def change(self, item: dict[str, Any], operation: str) -> None: ...
    def details(self, asset_id: int) -> dict[str, Any]: ...
    def save_details(
        self, asset_id: int, version: dict[str, Any], values: dict[str, Any]
    ) -> None: ...


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
            identity = db._connect.execute(
                "SELECT uuid FROM asset_identity WHERE asset_id=? AND deleted_at IS NULL",
                (asset_id,),
            ).fetchone()
            if identity is None:
                raise ValueError("Asset no longer exists")
            versions = []
            for history_id, version, description, details in db._connect.execute(
                """SELECT h.id,h.version,h.comment,v.details
                FROM hda_history h JOIN version_identity v ON v.history_id=h.id
                WHERE h.hda_key_id=? AND v.deleted_at IS NULL ORDER BY h.id DESC""",
                (asset_id,),
            ):
                versions.append(
                    {
                        "id": history_id,
                        "version": version,
                        "document": {"description": description, **json.loads(details)},
                    }
                )
            events = [
                {
                    "operation": operation,
                    "actor": actor,
                    "occurred_at": occurred,
                    "changes": json.loads(changes),
                }
                for operation, actor, occurred, changes in db._connect.execute(
                    "SELECT operation,actor,occurred_at,changes FROM audit_events WHERE asset_uuid=? ORDER BY occurred_at DESC LIMIT ?",
                    (identity[0], DEFAULT_AUDIT_EVENT_LIMIT),
                )
            ]
            files = [
                {
                    "version": version,
                    "kind": kind,
                    "filename": filename,
                    "status": status,
                }
                for version, kind, filename, status in db._connect.execute(
                    """SELECT h.version,f.kind,f.filename,f.status FROM version_files f JOIN hda_history h ON h.id=f.history_id WHERE h.hda_key_id=?""",
                    (asset_id,),
                )
            ]
            return {"versions": versions, "events": events, "files": files}

    def save_details(
        self, asset_id: int, version: dict[str, Any], values: dict[str, Any]
    ) -> None:
        with SQLite3DatabaseAPI(self.database) as db, db.transaction():
            row = db._connect.execute(
                "SELECT h.hda_key_id,h.comment,v.details FROM hda_history h JOIN version_identity v ON v.history_id=h.id WHERE h.id=?",
                (version["id"],),
            ).fetchone()
            if (
                row is None
                or row[0] != asset_id
                or {"description": row[1], **json.loads(row[2])} != version["document"]
            ):
                raise ValueError("Version changed; reload before saving")
            PersonalLifecycle(db._connect).details(version["id"], values)

    def inspect(self) -> None:
        with SQLite3DatabaseAPI(self.database) as db:
            inspect_files(db._connect)


class RemoteManagement:
    def __init__(self, catalog: Any, pending: PendingCommand | None = None) -> None:
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
        return {
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
