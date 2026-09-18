"""Portable library metadata rules, independent of Qt and database drivers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def file_stamp() -> str:
    """UTC timestamp for file names: sortable, no separators, microseconds."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def new_identity() -> str:
    return str(uuid4())


def validate_version_details(values: dict[str, Any]) -> None:
    description = values.get("description", "")
    if not isinstance(description, str) or len(description) > 16000:
        raise ValueError("Version description must contain at most 16000 characters")
    dependencies = values.get("dependencies", [])
    if not isinstance(dependencies, list) or len(dependencies) > 256:
        raise ValueError("At most 256 dependencies can be recorded")
    for item in dependencies:
        if not isinstance(item, dict) or set(item) - {
            "kind",
            "target",
            "version",
            "required",
            "source",
            "library_uuid",
            "asset_uuid",
            "version_uuid",
            "resolution",
        }:
            raise ValueError("Invalid dependency fields")
        if item.get("kind") not in {"asset", "plugin", "file", "package"}:
            raise ValueError("Invalid dependency kind")
        if not isinstance(item.get("target"), str) or not item["target"].strip():
            raise ValueError("Dependency target is required")
        if any(not isinstance(item.get(key, ""), str) for key in ("version", "source")):
            raise ValueError("Dependency version and source must be text")
        for key in ("library_uuid", "asset_uuid", "version_uuid"):
            if item.get(key) is not None:
                if not isinstance(item[key], str):
                    raise ValueError("Dependency identity must be text")
                UUID(item[key])
        if not isinstance(item.get("required", True), bool):
            raise ValueError("Dependency required must be boolean")
    if values.get("dependency_status", "unknown") not in {"unknown", "recorded"}:
        raise ValueError("Invalid dependency status")


def version_details(values: dict[str, Any]) -> dict[str, Any]:
    validate_version_details(values)
    return {
        "description": values.get("description", ""),
        "dependencies": values.get("dependencies", []),
        "dependency_status": values.get("dependency_status", "unknown"),
        "compatibility_status": "unverified",
        "metadata_schema": 1,
    }
