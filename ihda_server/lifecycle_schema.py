"""Additive v2 tables. Legacy v1 table definitions remain migration inputs."""

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, Table

from ihda_server.schema import metadata

asset_state = Table(
    "team_asset_state",
    metadata,
    Column(
        "asset_id", ForeignKey("team_assets.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("uuid", String(36), nullable=False, unique=True),
    Column("current_version_uuid", String(36)),
    Column("deleted_at", String(40)),
    Column("deleted_by", String(36)),
    Column("provenance", JSON, nullable=False),
)
version_state = Table(
    "team_version_state",
    metadata,
    Column(
        "history_id",
        ForeignKey("team_history.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("uuid", String(36), nullable=False, unique=True),
    Column("deleted_at", String(40)),
    Column("deleted_by", String(36)),
    Column("details", JSON, nullable=False),
)
preferences = Table(
    "team_asset_user_preferences",
    metadata,
    Column(
        "asset_id", ForeignKey("team_assets.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("user_id", ForeignKey("team_users.id"), primary_key=True),
    Column("favorite", Integer, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("use_count", Integer, nullable=False),
    Column("last_used_at", String(40)),
)
audit = Table(
    "team_audit_events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("project_id", ForeignKey("team_projects.id"), nullable=False, index=True),
    Column("asset_uuid", String(36), index=True),
    Column("version_uuid", String(36)),
    Column("actor", String(36), nullable=False),
    Column("occurred_at", String(40), nullable=False),
    Column("request_id", String(36)),
    Column("operation", String(40), nullable=False),
    Column("changes", JSON, nullable=False),
)
# events(): WHERE project_id AND asset_uuid ORDER BY occurred_at DESC LIMIT n.
audit_lookup_index = Index(
    "ix_team_audit_lookup", audit.c.project_id, audit.c.asset_uuid, audit.c.occurred_at
)
file_refs = Table(
    "team_version_files",
    metadata,
    Column(
        "history_id",
        ForeignKey("team_history.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("kind", String(20), primary_key=True),
    Column("digest", String(64), nullable=False, index=True),
    Column("size", Integer, nullable=False),
    Column("filename", String(240), nullable=False),
    Column("registered_at", String(40)),
    Column("checked_at", String(40)),
    Column("status", String(20), nullable=False),
)
