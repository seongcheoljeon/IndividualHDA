"""One handler per team operation that mutates a loaded asset.

``SqlCatalog._apply`` loads the asset, calls ``HANDLERS[operation]`` and then
persists the document, the history row and the audit event. Adding an
operation means: extend ``Operation`` in libs.team.contracts, write one handler
here, register it, and give it a label in the metadata dialog.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, select, update

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from ihda_server.lifecycle import LifecycleStore
from ihda_server.tracking import team_tracking
from libs.library_metadata import new_identity, version_details
from libs.tags import normalize_tags
from libs.team.contracts import Command, NotFound, Operation

LIFECYCLE_OPERATIONS: frozenset[str] = frozenset(
    {
        "delete",
        "restore",
        "purge",
        "delete_history",
        "restore_history",
        "purge_history",
    }
)
# Operations _apply handles itself because they do not mutate a loaded asset.
EXPLICIT_OPERATIONS: frozenset[str] = frozenset(
    {"create", "copy_asset", "preference", "usage"}
)


@dataclass(slots=True)
class Mutation:
    """Everything a handler may read; ``document`` is the copy it edits."""

    connection: Connection
    project_id: str
    user_id: str
    command: Command
    values: dict[str, Any]
    asset_id: int
    info: dict[str, Any]
    document: dict[str, Any]
    lifecycle: LifecycleStore
    # (before, after) for the audit event when the change is about a version
    # rather than the asset document itself.
    audit_snapshot: tuple[dict[str, Any], dict[str, Any]] | None = None


Handler = Callable[[Mutation], dict[str, Any]]


def rename(mutation: Mutation) -> dict[str, Any]:
    mutation.document["name"] = mutation.values["name"]
    return mutation.document


def metadata(mutation: Mutation) -> dict[str, Any]:
    document = mutation.document
    document.update(mutation.values)
    document["tags"] = normalize_tags(document["tags"])
    return document


def version(mutation: Mutation) -> dict[str, Any]:
    document, values = mutation.document, mutation.values
    document.update(
        version=values["version"],
        metadata=values.get("metadata", {}),
        files=values["files"],
        version_uuid=new_identity(),
        **version_details(values),
    )
    mutation.connection.execute(
        update(state.asset_state)
        .where(state.asset_state.c.asset_id == mutation.asset_id)
        .values(current_version_uuid=document["version_uuid"])
    )
    return document


def _live_history(mutation: Mutation, *criteria: Any) -> Any:
    row = (
        mutation.connection.execute(
            select(tables.history)
            .join(state.version_state)
            .where(
                tables.history.c.asset_id == mutation.asset_id,
                *criteria,
                state.version_state.c.deleted_at.is_(None),
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise NotFound("Version does not exist")
    return row


def _save_history_document(mutation: Mutation, historical: Any, snapshot: Any) -> None:
    mutation.connection.execute(
        update(tables.history)
        .where(tables.history.c.id == historical["id"])
        .values(document=snapshot)
    )
    mutation.audit_snapshot = (dict(historical["document"]), snapshot)


def media(mutation: Mutation) -> dict[str, Any]:
    """Attach or replace a thumbnail/video on the current version."""
    values = mutation.values
    historical = _live_history(
        mutation, state.version_state.c.uuid == mutation.info["current_version_uuid"]
    )
    snapshot = deepcopy(historical["document"])
    snapshot["files"][values["kind"]] = values["file"]
    mutation.document["files"][values["kind"]] = values["file"]
    mutation.lifecycle.sync_files(mutation.connection, historical["id"], snapshot)
    _save_history_document(mutation, historical, snapshot)
    return mutation.document


def version_details_change(mutation: Mutation) -> dict[str, Any]:
    """Description and dependencies of one version, current or not."""
    values = mutation.values
    historical = _live_history(mutation, tables.history.c.id == values["history_id"])
    snapshot = deepcopy(historical["document"])
    details = {
        **version_details(snapshot),
        **{key: value for key, value in values.items() if key != "history_id"},
    }
    tracking = team_tracking(mutation.connection, mutation.project_id)
    tracking.replace_dependencies(
        snapshot["version_uuid"], details.get("dependencies", [])
    )
    details["dependencies"] = tracking.dependencies(snapshot["version_uuid"])
    snapshot.update(details)
    mutation.connection.execute(
        update(state.version_state)
        .where(state.version_state.c.history_id == historical["id"])
        .values(details=details)
    )
    if snapshot["version_uuid"] == mutation.document["version_uuid"]:
        mutation.document.update(details)
    _save_history_document(mutation, historical, snapshot)
    return mutation.document


def lifecycle_change(mutation: Mutation) -> dict[str, Any]:
    """Trash, restore or purge an asset or one of its versions."""
    values, document = mutation.values, mutation.document
    operation = mutation.command.operation
    if "history_id" in values:
        target = mutation.connection.execute(
            select(state.version_state.c.uuid, tables.history.c.version)
            .join(tables.history)
            .where(
                tables.history.c.id == values["history_id"],
                tables.history.c.asset_id == mutation.asset_id,
            )
        ).first()
        if target is not None:
            identity = {
                "asset_uuid": document["asset_uuid"],
                "version_uuid": target[0],
                "version": target[1],
            }
            mutation.audit_snapshot = (
                {**identity, "deleted": operation != "delete_history"},
                {
                    **identity,
                    "deleted": operation == "delete_history",
                    "purged": operation == "purge_history",
                },
            )
    return mutation.lifecycle.change_lifecycle(
        mutation.connection,
        mutation.project_id,
        mutation.user_id,
        mutation.command,
        document,
    )


HANDLERS: dict[Operation, Handler] = {
    "rename": rename,
    "metadata": metadata,
    "version": version,
    "media": media,
    "version_details": version_details_change,
    "delete": lifecycle_change,
    "restore": lifecycle_change,
    "purge": lifecycle_change,
    "delete_history": lifecycle_change,
    "restore_history": lifecycle_change,
    "purge_history": lifecycle_change,
}
