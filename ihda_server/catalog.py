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

from sqlalchemy import (
    Connection,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from ihda_server.operations import HANDLERS, Mutation
from ihda_server.queries import CatalogQueries
from ihda_server.tracking import team_tracking
from libs.library_metadata import new_identity, version_details
from libs.tags import normalize_tags
from libs.team.contracts import (
    Blob,
    Command,
    Conflict,
    NotFound,
    Role,
    TeamError,
    parse_blob,
)


class SqlCatalog(CatalogQueries):
    """Writes to a project; reads are inherited from CatalogQueries."""

    def require_access(
        self, project_id: str, user_id: str, write: bool = False
    ) -> None:
        with self.reading(project_id, user_id, write=write):
            pass

    def create_project(self, user_id: str, name: str) -> dict[str, Any]:
        if not name.strip() or len(name) > 120:
            raise TeamError("Project name must contain 1–120 characters")
        project = {"id": str(uuid4()), "name": name.strip(), "revision": 0}
        with self.creating() as connection:
            connection.execute(insert(tables.projects).values(**project))
            connection.execute(
                insert(tables.members).values(
                    project_id=project["id"], user_id=user_id, role="owner"
                )
            )
        return project

    def set_member(
        self, project_id: str, actor: str, user_id: str, role: Role | None
    ) -> None:
        if role not in {"viewer", "editor", "owner", None}:
            raise TeamError("Invalid project role")
        with self.writing(project_id, actor, owner=True) as connection:
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
        with self.writing(project_id, user_id) as connection:
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

    def execute(
        self, project_id: str, user_id: str, command: Command
    ) -> dict[str, Any]:
        command.validate()
        try:
            with self.writing(
                project_id,
                user_id,
                write=command.operation not in {"preference", "usage"},
                owner=command.operation in {"purge", "purge_history"},
            ) as connection:
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
            asset_id, document = self._create(
                connection, project_id, user_id, values, now
            )
        else:
            assert command.asset_id is not None  # validate() guarantees it
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
            mutation = Mutation(
                connection=connection,
                project_id=project_id,
                user_id=user_id,
                command=command,
                values=values,
                asset_id=asset_id,
                info=info,
                document=document,
                lifecycle=self.lifecycle,
            )
            document = HANDLERS[operation](mutation)
            audit_snapshot = mutation.audit_snapshot
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

    def _create(
        self,
        connection: Connection,
        project_id: str,
        user_id: str,
        values: dict[str, Any],
        now: str,
    ) -> tuple[int, dict[str, Any]]:
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
        return asset_id, document

    def tracking_execute(
        self, project_id: str, user_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            if set(body) != {"request_id", "operation", "values"} or not isinstance(
                body["values"], dict
            ):
                raise ValueError("Invalid tracking request")
            with self.writing(
                project_id, user_id, write=body["operation"] != "scene"
            ) as connection:
                result = team_tracking(connection, project_id).execute(
                    user_id, body["request_id"], body["operation"], body["values"]
                )
                return result
        except (ValueError, TypeError, KeyError) as error:
            raise TeamError(str(error)) from error
