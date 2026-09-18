"""Lifecycle persistence within the catalog's authorized transaction."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from sqlalchemy import Connection, delete, insert, select, update

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from ihda_server.audit import record_event
from ihda_server.tracking import team_tracking
from ihda_server.tracking_schema import dependencies
from libs.library_metadata import utc_now, version_details
from libs.team.contracts import Command, Conflict, NotFound


class LifecycleStore:
    @staticmethod
    def preference(
        connection: Connection, asset_id: int, user_id: str
    ) -> dict[str, Any]:
        row = (
            connection.execute(
                select(state.preferences).where(
                    state.preferences.c.asset_id == asset_id,
                    state.preferences.c.user_id == user_id,
                )
            )
            .mappings()
            .first()
        )
        return (
            dict(row)
            if row
            else {
                "asset_id": asset_id,
                "user_id": user_id,
                "favorite": False,
                "revision": 0,
                "use_count": 0,
                "last_used_at": None,
            }
        )

    def decorate(
        self, connection: Connection, document: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        return self.apply_preference(
            document, self.preference(connection, document["id"], user_id)
        )

    @staticmethod
    def preference_row(row: Mapping[Any, Any], user_id: str) -> dict[str, Any]:
        """A joined preferences row (all None when the user never set one)."""
        return {
            "asset_id": row["document"]["id"],
            "user_id": user_id,
            "favorite": bool(row["favorite"]),
            "revision": row["revision"] or 0,
            "use_count": row["use_count"] or 0,
            "last_used_at": row["last_used_at"],
        }

    @staticmethod
    def apply_preference(
        document: dict[str, Any], preference: Mapping[str, Any]
    ) -> dict[str, Any]:
        result = deepcopy(document)
        result.update(
            favorite=bool(preference["favorite"]),
            preference_revision=preference["revision"],
            use_count=preference["use_count"],
            last_used_at=preference["last_used_at"],
        )
        return result

    def set_preference(
        self, connection: Connection, user_id: str, command: Command
    ) -> dict[str, Any]:
        assert command.asset_id is not None
        asset_id = command.asset_id
        current = self.preference(connection, asset_id, user_id)
        if (
            command.operation == "preference"
            and current["revision"] != command.expected_revision
        ):
            raise Conflict("Personal settings changed; reload before saving")
        values = dict(current)
        values["revision"] += 1
        if command.operation == "preference":
            values["favorite"] = int(command.values["favorite"])
        else:
            values["use_count"] += 1
            values["last_used_at"] = utc_now()
        if current["revision"]:
            connection.execute(
                update(state.preferences)
                .where(
                    state.preferences.c.asset_id == asset_id,
                    state.preferences.c.user_id == user_id,
                )
                .values(**values)
            )
        else:
            connection.execute(insert(state.preferences).values(**values))
        return values

    @staticmethod
    def event(
        connection: Connection,
        project_id: str,
        actor: str,
        operation: str,
        before: dict[str, Any],
        after: dict[str, Any],
        request_id: str | None = None,
    ) -> None:
        record_event(
            connection, project_id, actor, operation, before, after, request_id
        )

    @staticmethod
    def asset_state(connection: Connection, asset_id: int) -> dict[str, Any]:
        row = (
            connection.execute(
                select(state.asset_state).where(
                    state.asset_state.c.asset_id == asset_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise NotFound("Asset does not exist")
        return dict(row)

    @staticmethod
    def save_version(
        connection: Connection, history_id: int, document: dict[str, Any]
    ) -> None:
        connection.execute(
            insert(state.version_state).values(
                history_id=history_id,
                uuid=document["version_uuid"],
                details=version_details(document),
            )
        )
        LifecycleStore.sync_files(connection, history_id, document)
        project_id = connection.execute(
            select(tables.history.c.project_id).where(tables.history.c.id == history_id)
        ).scalar_one()
        team_tracking(connection, project_id).replace_dependencies(
            document["version_uuid"], document.get("dependencies", [])
        )

    @staticmethod
    def sync_files(
        connection: Connection, history_id: int, document: dict[str, Any]
    ) -> None:
        current = {
            row["kind"]: dict(row)
            for row in connection.execute(
                select(state.file_refs).where(
                    state.file_refs.c.history_id == history_id
                )
            ).mappings()
        }
        for kind in set(current) - set(document["files"]):
            connection.execute(
                delete(state.file_refs).where(
                    state.file_refs.c.history_id == history_id,
                    state.file_refs.c.kind == kind,
                )
            )
        for kind, blob in document["files"].items():
            old = current.get(kind)
            if old and all(old[key] == value for key, value in blob.items()):
                continue
            values = {
                **blob,
                "registered_at": utc_now(),
                "status": "unverified",
                "checked_at": None,
            }
            if old:
                connection.execute(
                    update(state.file_refs)
                    .where(
                        state.file_refs.c.history_id == history_id,
                        state.file_refs.c.kind == kind,
                    )
                    .values(**values)
                )
            else:
                connection.execute(
                    insert(state.file_refs).values(
                        history_id=history_id, kind=kind, **values
                    )
                )

    def change_lifecycle(
        self,
        connection: Connection,
        project_id: str,
        user_id: str,
        command: Command,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        asset_id = document["id"]
        info = self.asset_state(connection, asset_id)
        operation = command.operation
        if operation in {"delete", "restore", "purge"}:
            deleted = info["deleted_at"] is not None
            if deleted != (operation != "delete"):
                raise Conflict("The asset's trash state changed; reload")
            if operation == "purge":
                connection.execute(
                    delete(dependencies).where(
                        dependencies.c.scope_id == project_id,
                        dependencies.c.source_uuid.in_(
                            select(state.version_state.c.uuid)
                            .join(tables.history)
                            .where(tables.history.c.asset_id == asset_id)
                        ),
                    )
                )
                connection.execute(
                    delete(tables.assets).where(tables.assets.c.id == asset_id)
                )
                return {**document, "purged": True}
            values = {
                "deleted_at": utc_now() if operation == "delete" else None,
                "deleted_by": user_id if operation == "delete" else None,
            }
            connection.execute(
                update(state.asset_state)
                .where(state.asset_state.c.asset_id == asset_id)
                .values(**values)
            )
            return {**document, **values, "deleted": operation == "delete"}
        row = (
            connection.execute(
                select(
                    tables.history,
                    state.version_state.c.uuid,
                    state.version_state.c.deleted_at,
                )
                .join(state.version_state)
                .where(
                    tables.history.c.asset_id == asset_id,
                    tables.history.c.id == command.values["history_id"],
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise NotFound("Version does not exist")
        if (
            operation == "delete_history"
            and row["uuid"] == info["current_version_uuid"]
        ):
            raise Conflict("The current asset version cannot be deleted")
        deleted = row["deleted_at"] is not None
        if deleted != (operation != "delete_history"):
            raise Conflict("The version's trash state changed; reload")
        if operation == "purge_history":
            connection.execute(
                delete(dependencies).where(
                    dependencies.c.scope_id == project_id,
                    dependencies.c.source_uuid == row["uuid"],
                )
            )
            connection.execute(
                delete(tables.history).where(tables.history.c.id == row["id"])
            )
        else:
            connection.execute(
                update(state.version_state)
                .where(state.version_state.c.history_id == row["id"])
                .values(
                    deleted_at=utc_now() if operation == "delete_history" else None,
                    deleted_by=user_id if operation == "delete_history" else None,
                )
            )
        return document
