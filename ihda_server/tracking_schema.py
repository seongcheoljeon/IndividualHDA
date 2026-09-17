"""Schema v3 tables included in migration, backup inventory and restore."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Index,
    Integer,
    Table,
    Text,
    UniqueConstraint,
)

from ihda_server.schema import metadata


def text_column(
    name: str, *, primary_key: bool = False, nullable: bool = False
) -> Column:
    return Column(name, Text, primary_key=primary_key, nullable=nullable)


dependencies = Table(
    "version_dependencies",
    metadata,
    text_column("scope_id", primary_key=True),
    text_column("source_uuid", primary_key=True),
    Column("ordinal", Integer, primary_key=True),
    *(
        text_column(name, nullable=True)
        for name in ("target_scope", "target_asset", "target_version")
    ),
    *(text_column(name) for name in ("kind", "target", "version")),
    Column("required", Integer, nullable=False),
    text_column("source"),
    CheckConstraint("required IN (0,1)"),
    Index("idx_dependency_target", "target_scope", "target_asset", "target_version"),
)
checks = Table(
    "version_checks",
    metadata,
    text_column("scope_id", primary_key=True),
    text_column("id", primary_key=True),
    *(
        text_column(name)
        for name in (
            "version_uuid",
            "asset_uuid",
            "actor",
            "checked_at",
            "created_at",
            "document",
        )
    ),
    Index("idx_checks_version", "scope_id", "version_uuid", "created_at", "id"),
)
scenes = Table(
    "scene_usages",
    metadata,
    text_column("scope_id", primary_key=True),
    text_column("id", primary_key=True),
    *(
        text_column(name)
        for name in (
            "actor",
            "client_id",
            "scene_key",
            "node_path",
            "asset_uuid",
            "version_uuid",
            "first_seen",
            "last_seen",
            "document",
        )
    ),
    UniqueConstraint(
        "scope_id", "actor", "client_id", "scene_key", "node_path", "version_uuid"
    ),
    Index(
        "idx_scene_version", "scope_id", "asset_uuid", "version_uuid", "last_seen", "id"
    ),
)
requests = Table(
    "tracking_requests",
    metadata,
    *(text_column(name, primary_key=True) for name in ("scope_id", "actor", "id")),
    text_column("fingerprint"),
    text_column("result"),
)
TABLES = (dependencies, checks, scenes, requests)
