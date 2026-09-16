"""Validation of an atomic copy, reusing normal asset/version rules."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from libs.team.contracts import Command, TeamError
from libs.team.limits import MAX_COPY_VERSIONS


def validate_copy(values: dict[str, Any]) -> None:
    if set(values) != {"name", "category", "note", "tags", "origin", "versions"}:
        raise TeamError("Invalid copy fields")
    origin = values["origin"]
    if not isinstance(origin, dict) or set(origin) != {"library_uuid", "asset_uuid"}:
        raise TeamError("Source library and asset identities are required")
    versions = values["versions"]
    if not isinstance(versions, list) or not 1 <= len(versions) <= MAX_COPY_VERSIONS:
        raise TeamError(f"Copy requires 1–{MAX_COPY_VERSIONS} versions")
    labels, identities = set(), set()
    try:
        for identity in origin.values():
            UUID(identity)
        for version in versions:
            if not isinstance(version, dict) or set(version) != {"origin", "values"}:
                raise TeamError("Invalid copied version")
            source = version["origin"]
            if not isinstance(source, dict) or set(source) != {
                "version_uuid",
                "version",
                "created_at",
                "created_by",
            }:
                raise TeamError("Invalid version origin")
            UUID(source["version_uuid"])
            if not all(isinstance(value, str) for value in source.values()):
                raise TeamError("Version origin must contain text")
            data = version["values"]
            if not isinstance(data, dict) or set(data) - {
                "version",
                "files",
                "metadata",
                "note",
                "description",
                "dependencies",
                "dependency_status",
            }:
                raise TeamError("Invalid copied version fields")
            Command(
                "create",
                values={
                    **data,
                    "name": values["name"],
                    "category": values["category"],
                    "tags": values["tags"],
                },
            ).validate()
            if data["version"] in labels or source["version_uuid"] in identities:
                raise TeamError("Copied version labels and identities must be unique")
            labels.add(data["version"])
            identities.add(source["version_uuid"])
    except (ValueError, TypeError, AttributeError) as error:
        raise TeamError("Invalid source identity") from error
    if not isinstance(values["note"], str):
        raise TeamError("note must be text")
