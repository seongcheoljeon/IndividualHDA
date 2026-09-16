"""Relational schema shared by PostgreSQL production and SQLite contract tests."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

metadata = MetaData()
users = Table(
    "team_users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(120), nullable=False, unique=True),
)
tokens = Table(
    "team_tokens",
    metadata,
    Column("digest", String(64), primary_key=True),
    Column("user_id", ForeignKey("team_users.id"), nullable=False),
    Column("expires_at", String(40), nullable=False),
)
projects = Table(
    "team_projects",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(120), nullable=False),
    Column("revision", Integer, nullable=False, default=0),
)
members = Table(
    "team_members",
    metadata,
    Column("project_id", ForeignKey("team_projects.id"), primary_key=True),
    Column("user_id", ForeignKey("team_users.id"), primary_key=True),
    Column("role", String(12), nullable=False),
)
assets = Table(
    "team_assets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", ForeignKey("team_projects.id"), nullable=False, index=True),
    Column("name", String(254), nullable=False),
    Column("name_key", String(254), nullable=False),
    Column("category", String(80), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("document", JSON, nullable=False),
    UniqueConstraint("project_id", "category", "name_key"),
)
history = Table(
    "team_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", ForeignKey("team_projects.id"), nullable=False, index=True),
    Column(
        "asset_id",
        ForeignKey("team_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("version", String(80), nullable=False),
    Column("document", JSON, nullable=False),
    UniqueConstraint("asset_id", "version"),
)
requests = Table(
    "team_requests",
    metadata,
    Column("project_id", ForeignKey("team_projects.id"), primary_key=True),
    Column("user_id", ForeignKey("team_users.id"), primary_key=True),
    Column("request_id", String(36), primary_key=True),
    Column("fingerprint", String(64), nullable=False),
    Column("result", JSON, nullable=False),
)
blobs = Table(
    "team_blobs",
    metadata,
    Column("project_id", ForeignKey("team_projects.id"), primary_key=True),
    Column("digest", String(64), primary_key=True),
    Column("size", Integer, nullable=False),
)
versions = Table("team_schema", metadata, Column("version", Integer, primary_key=True))
