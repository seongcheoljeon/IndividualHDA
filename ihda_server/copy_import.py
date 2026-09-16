"""Copy a source snapshot under the catalog's project lock and transaction."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from sqlalchemy import Connection, and_, or_, select, update

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from libs.team.contracts import Command, Conflict


def copy_matches(
    connection: Connection,
    project_id: str,
    name: str,
    category: str,
    origin: dict[str, str],
) -> dict[str, Any]:
    matches: dict[str, Any] = {"source_match": None, "name_conflict": None}
    rows = connection.execute(
        select(
            tables.assets.c.id,
            tables.assets.c.name,
            tables.assets.c.category,
            state.asset_state.c.provenance,
            state.asset_state.c.deleted_at,
        )
        .join(state.asset_state)
        .where(
            tables.assets.c.project_id == project_id,
            or_(
                and_(
                    tables.assets.c.category == category,
                    tables.assets.c.name_key == name.casefold(),
                ),
                and_(
                    state.asset_state.c.provenance["copy_source"][
                        "library_uuid"
                    ].as_string()
                    == origin["library_uuid"],
                    state.asset_state.c.provenance["copy_source"][
                        "asset_uuid"
                    ].as_string()
                    == origin["asset_uuid"],
                ),
            ),
        )
    ).mappings()
    for row in rows:
        summary = {key: row[key] for key in ("id", "name", "deleted_at")}
        if row["provenance"].get("copy_source") == origin:
            matches["source_match"] = summary
        if row["category"] == category and row["name"].casefold() == name.casefold():
            matches["name_conflict"] = summary
    return matches


def apply_copy(
    connection: Connection,
    project_id: str,
    command: Command,
    apply: Callable[[Command], dict[str, Any]],
) -> dict[str, Any]:
    values = command.values
    matches = copy_matches(
        connection, project_id, values["name"], values["category"], values["origin"]
    )
    if matches["source_match"]:
        raise Conflict(
            "This personal asset has already been copied to this project (including Trash)"
        )
    if matches["name_conflict"]:
        raise Conflict(
            "An asset with this name and category already exists (including Trash)"
        )
    document: dict[str, Any] = {}
    for index, version in enumerate(values["versions"]):
        data = deepcopy(version["values"])
        note = data.pop("note", "")
        if index == 0:
            data.update(
                name=values["name"],
                category=values["category"],
                note=note,
                tags=values["tags"],
            )
            inner = Command("create", request_id=command.request_id, values=data)
        else:
            inner = Command(
                "version",
                request_id=command.request_id,
                asset_id=document["id"],
                expected_revision=document["revision"],
                values=data,
            )
        document = apply(inner)
        # decorate() adds personal preferences only to its returned copy.
        snapshot = connection.execute(
            select(tables.assets.c.document).where(tables.assets.c.id == document["id"])
        ).scalar_one()
        snapshot = {
            **snapshot,
            "note": note,
            "provenance": {
                "copy_source": values["origin"],
                "source_version": version["origin"],
            },
        }
        history_id = connection.execute(
            select(tables.history.c.id).where(
                tables.history.c.asset_id == document["id"],
                tables.history.c.version == data["version"],
            )
        ).scalar_one()
        connection.execute(
            update(tables.history)
            .where(tables.history.c.id == history_id)
            .values(document=snapshot)
        )
        details = connection.execute(
            select(state.version_state.c.details).where(
                state.version_state.c.history_id == history_id
            )
        ).scalar_one()
        connection.execute(
            update(state.version_state)
            .where(state.version_state.c.history_id == history_id)
            .values(details={**details, "provenance": snapshot["provenance"]})
        )
    snapshot.update(note=values["note"], provenance={"copy_source": values["origin"]})
    connection.execute(
        update(tables.assets)
        .where(tables.assets.c.id == document["id"])
        .values(document=snapshot)
    )
    connection.execute(
        update(state.asset_state)
        .where(state.asset_state.c.asset_id == document["id"])
        .values(provenance=snapshot["provenance"])
    )
    return {**document, **snapshot}
