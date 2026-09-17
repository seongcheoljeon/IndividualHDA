"""Atomic relational operations. Each write locks its project and records its result.

The project lock also serializes membership changes and duplicate requests across
processes. Authorization, expected revisions and the idempotency receipt share
one transaction with the asset/history changes.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from ihda_server.lifecycle import LifecycleStore
from libs.library_metadata import new_identity, version_details
from libs.search_limits import QUERY_TEXT_MAX, TEAM_PAGE_DEFAULT, TEAM_PAGE_MAX
from libs.tags import normalize_tags
from libs.team.contracts import (
    Blob,
    Command,
    Conflict,
    Forbidden,
    NotFound,
    Page,
    Role,
    TeamError,
    parse_blob,
)
from libs.team.limits import DEFAULT_AUDIT_EVENT_LIMIT


class SqlCatalog:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self.lifecycle = LifecycleStore()

    @staticmethod
    def authorize(
        connection: Connection,
        project_id: str,
        user_id: str,
        write: bool = False,
        owner: bool = False,
    ) -> str:
        role = connection.execute(
            select(tables.members.c.role).where(
                tables.members.c.project_id == project_id,
                tables.members.c.user_id == user_id,
            )
        ).scalar_one_or_none()
        if role is None or (write and role == "viewer") or (owner and role != "owner"):
            raise Forbidden("Project permission denied")
        return str(role)

    @staticmethod
    def lock(connection: Connection, project_id: str) -> None:
        result = connection.execute(
            update(tables.projects)
            .where(tables.projects.c.id == project_id)
            .values(revision=tables.projects.c.revision)
        )
        if result.rowcount != 1:
            raise Forbidden("Project permission denied")

    def require_access(
        self, project_id: str, user_id: str, write: bool = False
    ) -> None:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id, write)

    def projects(self, user_id: str) -> list[dict[str, Any]]:
        with self._engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(tables.projects, tables.members.c.role)
                    .join(tables.members)
                    .where(tables.members.c.user_id == user_id)
                    .order_by(tables.projects.c.name)
                ).mappings()
            ]

    def create_project(self, user_id: str, name: str) -> dict[str, Any]:
        if not name.strip() or len(name) > 120:
            raise TeamError("Project name must contain 1–120 characters")
        project = {"id": str(uuid4()), "name": name.strip(), "revision": 0}
        with self._engine.begin() as connection:
            connection.execute(insert(tables.projects).values(**project))
            connection.execute(
                insert(tables.members).values(
                    project_id=project["id"], user_id=user_id, role="owner"
                )
            )
        return project

    def members(self, project_id: str, user_id: str) -> list[dict[str, Any]]:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id, owner=True)
            return [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.members.c.user_id,
                        tables.members.c.role,
                        tables.users.c.name,
                    )
                    .join(tables.users)
                    .where(tables.members.c.project_id == project_id)
                ).mappings()
            ]

    def set_member(
        self, project_id: str, actor: str, user_id: str, role: Role | None
    ) -> None:
        if role not in {"viewer", "editor", "owner", None}:
            raise TeamError("Invalid project role")
        with self._engine.begin() as connection:
            self.lock(connection, project_id)
            self.authorize(connection, project_id, actor, owner=True)
            if (
                connection.execute(
                    select(tables.users.c.id).where(tables.users.c.id == user_id)
                ).scalar_one_or_none()
                is None
            ):
                raise NotFound("User does not exist")
            existing = connection.execute(
                select(tables.members.c.role).where(
                    tables.members.c.project_id == project_id,
                    tables.members.c.user_id == user_id,
                )
            ).scalar_one_or_none()
            owners = connection.execute(
                select(func.count())
                .select_from(tables.members)
                .where(
                    tables.members.c.project_id == project_id,
                    tables.members.c.role == "owner",
                )
            ).scalar_one()
            if existing == "owner" and role != "owner" and owners <= 1:
                raise Conflict("A project must retain at least one owner")
            connection.execute(
                delete(tables.members).where(
                    tables.members.c.project_id == project_id,
                    tables.members.c.user_id == user_id,
                )
            )
            if role is not None:
                connection.execute(
                    insert(tables.members).values(
                        project_id=project_id, user_id=user_id, role=role
                    )
                )
            self.lifecycle.event(
                connection,
                project_id,
                actor,
                "membership",
                {"user_id": user_id, "role": existing},
                {"user_id": user_id, "role": role},
            )

    def register_blob(
        self, project_id: str, user_id: str, digest: str, size: int
    ) -> None:
        with self._engine.begin() as connection:
            self.lock(connection, project_id)
            self.authorize(connection, project_id, user_id, write=True)
            if (
                connection.execute(
                    select(tables.blobs.c.digest).where(
                        tables.blobs.c.project_id == project_id,
                        tables.blobs.c.digest == digest,
                    )
                ).first()
                is None
            ):
                connection.execute(
                    insert(tables.blobs).values(
                        project_id=project_id, digest=digest, size=size
                    )
                )

    def blob_size(self, project_id: str, user_id: str, digest: str) -> int:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            size = connection.execute(
                select(tables.blobs.c.size).where(
                    tables.blobs.c.project_id == project_id,
                    tables.blobs.c.digest == digest,
                )
            ).scalar_one_or_none()
            if size is None:
                raise NotFound("File does not belong to this project")
            return int(size)

    @staticmethod
    def _verify_blob(connection: Connection, project_id: str, blob: Blob) -> None:
        size = connection.execute(
            select(tables.blobs.c.size).where(
                tables.blobs.c.project_id == project_id,
                tables.blobs.c.digest == blob.digest,
            )
        ).scalar_one_or_none()
        if size != blob.size:
            raise TeamError("File must be uploaded to this project before registration")

    def list_assets(
        self,
        project_id: str,
        user_id: str,
        query: str = "",
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> Page:
        if offset < 0 or not 1 <= limit <= TEAM_PAGE_MAX or len(query) > QUERY_TEXT_MAX:
            raise TeamError("Invalid pagination or query")
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            criteria = [
                tables.assets.c.project_id == project_id,
                tables.assets.c.id.in_(
                    select(state.asset_state.c.asset_id).where(
                        state.asset_state.c.deleted_at.is_(None)
                    )
                ),
            ]
            if query.strip():
                pattern = (
                    "%"
                    + query.strip()
                    .replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                    + "%"
                )
                criteria.append(
                    or_(
                        tables.assets.c.name.ilike(pattern, escape="\\"),
                        tables.assets.c.category.ilike(pattern, escape="\\"),
                    )
                )
            total = connection.execute(
                select(func.count()).select_from(tables.assets).where(*criteria)
            ).scalar_one()
            rows = (
                connection.execute(
                    select(tables.assets.c.document)
                    .where(*criteria)
                    .order_by(tables.assets.c.name_key, tables.assets.c.id)
                    .offset(offset)
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            revision = connection.execute(
                select(tables.projects.c.revision).where(
                    tables.projects.c.id == project_id
                )
            ).scalar_one()
            return Page(
                [self.lifecycle.decorate(connection, row, user_id) for row in rows],
                total,
                offset,
                limit,
                revision,
            )

    def get_asset(self, project_id: str, user_id: str, asset_id: int) -> dict[str, Any]:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            document = connection.execute(
                select(tables.assets.c.document).where(
                    tables.assets.c.project_id == project_id,
                    tables.assets.c.id == asset_id,
                )
            ).scalar_one_or_none()
            if document is None:
                raise NotFound("Asset does not exist")
            info = self.lifecycle.asset_state(connection, asset_id)
            if info["deleted_at"]:
                raise NotFound("Asset is in the trash")
            from ihda_server.tracking import team_tracking

            document = {
                **document,
                "dependencies": team_tracking(connection, project_id).dependencies(
                    document["version_uuid"]
                ),
            }
            return self.lifecycle.decorate(connection, document, user_id)

    def histories(
        self, project_id: str, user_id: str, asset_id: int
    ) -> list[dict[str, Any]]:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            rows = [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.history.c.id,
                        tables.history.c.version,
                        tables.history.c.document,
                    )
                    .where(
                        tables.history.c.project_id == project_id,
                        tables.history.c.asset_id == asset_id,
                        tables.history.c.id.in_(
                            select(state.version_state.c.history_id).where(
                                state.version_state.c.deleted_at.is_(None)
                            )
                        ),
                        tables.history.c.asset_id.in_(
                            select(state.asset_state.c.asset_id).where(
                                state.asset_state.c.deleted_at.is_(None)
                            )
                        ),
                    )
                    .order_by(tables.history.c.id.desc())
                ).mappings()
            ]

            from ihda_server.tracking import team_tracking

            tracking = team_tracking(connection, project_id)
            for row in rows:
                row["document"] = {
                    **row["document"],
                    "dependencies": tracking.dependencies(
                        row["document"]["version_uuid"]
                    ),
                }
            return rows

    def execute(
        self, project_id: str, user_id: str, command: Command
    ) -> dict[str, Any]:
        command.validate()
        try:
            with self._engine.begin() as connection:
                self.lock(connection, project_id)
                self.authorize(
                    connection,
                    project_id,
                    user_id,
                    write=command.operation not in {"preference", "usage"},
                    owner=command.operation in {"purge", "purge_history"},
                )
                receipt = (
                    connection.execute(
                        select(tables.requests).where(
                            tables.requests.c.project_id == project_id,
                            tables.requests.c.user_id == user_id,
                            tables.requests.c.request_id == command.request_id,
                        )
                    )
                    .mappings()
                    .first()
                )
                if receipt is not None:
                    if receipt["fingerprint"] != command.fingerprint():
                        raise Conflict(
                            "Request ID was already used with different content"
                        )
                    return dict(receipt["result"])
                result = self._apply(connection, project_id, user_id, command)
                from ihda_server.tracking import verify_current

                try:
                    verify_current(connection, project_id)
                except ValueError as error:
                    raise Conflict(str(error)) from error
                if command.operation not in {"preference", "usage"}:
                    connection.execute(
                        update(tables.projects)
                        .where(tables.projects.c.id == project_id)
                        .values(revision=tables.projects.c.revision + 1)
                    )
                connection.execute(
                    insert(tables.requests).values(
                        project_id=project_id,
                        user_id=user_id,
                        request_id=command.request_id,
                        fingerprint=command.fingerprint(),
                        result=result,
                    )
                )
                return result
        except IntegrityError as error:
            raise Conflict("An asset name or version already exists") from error

    def _apply(
        self, connection: Connection, project_id: str, user_id: str, command: Command
    ) -> dict[str, Any]:
        if command.operation == "copy_asset":
            from ihda_server.copy_import import apply_copy

            copied = apply_copy(
                connection,
                project_id,
                command,
                lambda inner: self._apply(connection, project_id, user_id, inner),
            )
            self.lifecycle.event(
                connection,
                project_id,
                user_id,
                "copy_asset",
                {},
                copied,
                command.request_id,
            )
            return copied
        values = deepcopy(command.values)
        now = datetime.now(UTC).isoformat()
        operation = command.operation
        for file in values.get("files", {}).values():
            self._verify_blob(connection, project_id, parse_blob(file))
        if operation == "media":
            self._verify_blob(connection, project_id, parse_blob(values["file"]))
        before: dict[str, Any] = {}
        audit_snapshot: tuple[dict[str, Any], dict[str, Any]] | None = None
        if operation == "create":
            document = {
                "project_id": project_id,
                "name": values["name"],
                "category": values["category"],
                "version": values["version"],
                "revision": 1,
                "note": values.get("note", ""),
                "tags": normalize_tags(values.get("tags", [])),
                "metadata": values.get("metadata", {}),
                "files": values["files"],
                "created_at": now,
                "updated_at": now,
                "created_by": user_id,
                "updated_by": user_id,
                "asset_uuid": new_identity(),
                "version_uuid": new_identity(),
                "deleted_at": None,
                **version_details(values),
            }
            result = connection.execute(
                insert(tables.assets).values(
                    project_id=project_id,
                    name=document["name"],
                    name_key=document["name"].casefold(),
                    category=document["category"],
                    revision=1,
                    document=document,
                )
            )
            assert result.inserted_primary_key is not None
            asset_id = result.inserted_primary_key[0]
            document["id"] = asset_id
            connection.execute(
                insert(state.asset_state).values(
                    asset_id=asset_id,
                    uuid=document["asset_uuid"],
                    current_version_uuid=document["version_uuid"],
                    provenance={},
                )
            )
        else:
            asset_id = command.asset_id
            row = (
                connection.execute(
                    select(tables.assets).where(
                        tables.assets.c.project_id == project_id,
                        tables.assets.c.id == asset_id,
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise NotFound("Asset does not exist")
            info = self.lifecycle.asset_state(connection, row["id"])
            if info["deleted_at"] and operation not in {"restore", "purge"}:
                raise NotFound("Asset is in the trash")
            if operation in {"preference", "usage"}:
                self.lifecycle.set_preference(connection, user_id, command)
                return self.lifecycle.decorate(connection, row["document"], user_id)
            if row["revision"] != command.expected_revision:
                raise Conflict(
                    "Asset changed since it was loaded; reload before saving"
                )
            before = deepcopy(row["document"])
            document = deepcopy(before)
            document.update(
                revision=document["revision"] + 1, updated_at=now, updated_by=user_id
            )
            if operation in {
                "delete",
                "restore",
                "purge",
                "delete_history",
                "restore_history",
                "purge_history",
            }:
                if "history_id" in values:
                    target = connection.execute(
                        select(state.version_state.c.uuid, tables.history.c.version)
                        .join(tables.history)
                        .where(
                            tables.history.c.id == values["history_id"],
                            tables.history.c.asset_id == asset_id,
                        )
                    ).first()
                    if target is not None:
                        identity = {
                            "asset_uuid": document["asset_uuid"],
                            "version_uuid": target[0],
                            "version": target[1],
                        }
                        audit_snapshot = (
                            {**identity, "deleted": operation != "delete_history"},
                            {
                                **identity,
                                "deleted": operation == "delete_history",
                                "purged": operation == "purge_history",
                            },
                        )
                document = self.lifecycle.change_lifecycle(
                    connection, project_id, user_id, command, document
                )
            elif operation == "rename":
                document["name"] = values["name"]
            elif operation == "metadata":
                document.update(values)
                document["tags"] = normalize_tags(document["tags"])
            elif operation == "version":
                document.update(
                    version=values["version"],
                    metadata=values.get("metadata", {}),
                    files=values["files"],
                    version_uuid=new_identity(),
                    **version_details(values),
                )
                connection.execute(
                    update(state.asset_state)
                    .where(state.asset_state.c.asset_id == asset_id)
                    .values(current_version_uuid=document["version_uuid"])
                )
            elif operation in {"media", "version_details"}:
                criteria = [tables.history.c.asset_id == asset_id]
                if operation == "media":
                    criteria.append(
                        state.version_state.c.uuid == info["current_version_uuid"]
                    )
                else:
                    criteria.append(tables.history.c.id == values["history_id"])
                historical = (
                    connection.execute(
                        select(tables.history)
                        .join(state.version_state)
                        .where(*criteria, state.version_state.c.deleted_at.is_(None))
                    )
                    .mappings()
                    .first()
                )
                if historical is None:
                    raise NotFound("Version does not exist")
                snapshot = deepcopy(historical["document"])
                if operation == "media":
                    snapshot["files"][values["kind"]] = values["file"]
                    document["files"][values["kind"]] = values["file"]
                    self.lifecycle.sync_files(connection, historical["id"], snapshot)
                else:
                    details = {
                        **version_details(snapshot),
                        **{k: v for k, v in values.items() if k != "history_id"},
                    }
                    from ihda_server.tracking import team_tracking

                    tracking = team_tracking(connection, project_id)
                    tracking.replace_dependencies(
                        snapshot["version_uuid"], details.get("dependencies", [])
                    )
                    details["dependencies"] = tracking.dependencies(
                        snapshot["version_uuid"]
                    )
                    snapshot.update(details)
                    connection.execute(
                        update(state.version_state)
                        .where(state.version_state.c.history_id == historical["id"])
                        .values(details=details)
                    )
                    if snapshot["version_uuid"] == document["version_uuid"]:
                        document.update(details)
                connection.execute(
                    update(tables.history)
                    .where(tables.history.c.id == historical["id"])
                    .values(document=snapshot)
                )
                audit_snapshot = (dict(historical["document"]), snapshot)
        if operation != "purge":
            connection.execute(
                update(tables.assets)
                .where(tables.assets.c.id == asset_id)
                .values(
                    name=document["name"],
                    name_key=document["name"].casefold(),
                    revision=document["revision"],
                    document=document,
                )
            )
        if operation in {"create", "version"}:
            result = connection.execute(
                insert(tables.history).values(
                    project_id=project_id,
                    asset_id=asset_id,
                    version=document["version"],
                    document=document,
                )
            )
            assert result.inserted_primary_key is not None
            self.lifecycle.save_version(
                connection, result.inserted_primary_key[0], document
            )
        audit_after = (
            {**document, "history_id": values["history_id"]}
            if "history_id" in values
            else document
        )
        self.lifecycle.event(
            connection,
            project_id,
            user_id,
            operation,
            audit_snapshot[0] if audit_snapshot else before,
            audit_snapshot[1] if audit_snapshot else audit_after,
            command.request_id,
        )
        return self.lifecycle.decorate(connection, document, user_id)

    def trash(self, project_id: str, user_id: str) -> list[dict[str, Any]]:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            rows = [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.assets.c.id,
                        tables.assets.c.name,
                        tables.assets.c.revision,
                        state.asset_state.c.deleted_at,
                        state.asset_state.c.uuid.label("asset_uuid"),
                    )
                    .join(state.asset_state)
                    .where(
                        tables.assets.c.project_id == project_id,
                        state.asset_state.c.deleted_at.is_not(None),
                    )
                ).mappings()
            ]
            for item in rows:
                item["asset_id"] = item.pop("id")
                item["history_id"] = None
            for row in connection.execute(
                select(
                    tables.assets.c.id,
                    tables.assets.c.name,
                    tables.assets.c.revision,
                    tables.history.c.id.label("history_id"),
                    tables.history.c.version,
                    state.version_state.c.deleted_at,
                    state.asset_state.c.uuid.label("asset_uuid"),
                    state.version_state.c.uuid.label("version_uuid"),
                )
                .select_from(tables.assets)
                .join(tables.history)
                .join(state.version_state)
                .join(
                    state.asset_state,
                    state.asset_state.c.asset_id == tables.assets.c.id,
                )
                .where(
                    tables.assets.c.project_id == project_id,
                    state.asset_state.c.deleted_at.is_(None),
                    state.version_state.c.deleted_at.is_not(None),
                )
            ).mappings():
                item = dict(row)
                item["asset_id"] = item.pop("id")
                rows.append(item)
            return rows

    def events(
        self, project_id: str, user_id: str, asset_uuid: str
    ) -> list[dict[str, Any]]:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            return [
                dict(row)
                for row in connection.execute(
                    select(state.audit, tables.users.c.name.label("actor_name"))
                    .outerjoin(tables.users, tables.users.c.id == state.audit.c.actor)
                    .where(
                        state.audit.c.project_id == project_id,
                        state.audit.c.asset_uuid == asset_uuid,
                    )
                    .order_by(state.audit.c.occurred_at.desc())
                    .limit(DEFAULT_AUDIT_EVENT_LIMIT)
                ).mappings()
            ]

    def file_status(
        self, project_id: str, user_id: str, asset_id: int
    ) -> list[dict[str, Any]]:
        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            return [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.history.c.version,
                        state.file_refs.c.kind,
                        state.file_refs.c.filename,
                        state.file_refs.c.status,
                    )
                    .join(tables.history)
                    .where(
                        tables.history.c.asset_id == asset_id,
                        tables.history.c.project_id == project_id,
                    )
                ).mappings()
            ]

    def copy_check(
        self,
        project_id: str,
        user_id: str,
        name: str,
        category: str,
        library_uuid: str,
        asset_uuid: str,
    ) -> dict[str, Any]:
        from ihda_server.copy_import import copy_matches

        with self._engine.connect() as connection:
            self.authorize(connection, project_id, user_id)
            return copy_matches(
                connection,
                project_id,
                name,
                category,
                {"library_uuid": library_uuid, "asset_uuid": asset_uuid},
            )

    def tracking_read(
        self,
        project_id: str,
        user_id: str,
        kind: str,
        asset_uuid: str,
        version_uuid: str | None = None,
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> list[dict[str, Any]]:
        from ihda_server.tracking import team_tracking

        try:
            with self._engine.connect() as connection:
                self.authorize(connection, project_id, user_id)
                return team_tracking(connection, project_id).read(
                    kind, asset_uuid, version_uuid, offset, limit
                )
        except ValueError as error:
            raise TeamError(str(error)) from error

    def tracking_execute(
        self, project_id: str, user_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        from ihda_server.tracking import team_tracking

        try:
            if set(body) != {"request_id", "operation", "values"} or not isinstance(
                body["values"], dict
            ):
                raise ValueError("Invalid tracking request")
            with self._engine.begin() as connection:
                self.lock(connection, project_id)
                self.authorize(
                    connection, project_id, user_id, write=body["operation"] != "scene"
                )
                result = team_tracking(connection, project_id).execute(
                    user_id, body["request_id"], body["operation"], body["values"]
                )
                return result
        except (ValueError, TypeError, KeyError) as error:
            raise TeamError(str(error)) from error
