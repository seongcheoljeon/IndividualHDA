"""Append-only audit trail shared by the catalog, lifecycle and tracking stores.

Kept apart so tracking can record events without importing the lifecycle
store, which imports tracking; that cycle used to be hidden behind
function-level imports.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection, insert

from ihda_server import lifecycle_schema as state
from libs.library_metadata import new_identity, utc_now


def record_event(
    connection: Connection,
    project_id: str,
    actor: str,
    operation: str,
    before: dict[str, Any],
    after: dict[str, Any],
    request_id: str | None = None,
) -> None:
    keys = set(before) | set(after)
    changes = {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(keys)
        if before.get(key) != after.get(key)
    }
    connection.execute(
        insert(state.audit).values(
            id=new_identity(),
            project_id=project_id,
            actor=actor,
            occurred_at=utc_now(),
            request_id=request_id,
            operation=operation,
            asset_uuid=after.get("asset_uuid", before.get("asset_uuid")),
            version_uuid=after.get("version_uuid", before.get("version_uuid")),
            changes=changes,
        )
    )
