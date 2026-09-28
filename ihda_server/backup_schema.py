"""The tables a backup bundle of the current schema carries."""

from sqlalchemy import Table

from ihda_server import lifecycle_schema, tracking_schema  # noqa: F401
from ihda_server.database import SCHEMA_VERSION
from ihda_server.schema import metadata


def backup_tables(version: int) -> list[Table]:
    if version != SCHEMA_VERSION:
        raise ValueError("Unsupported backup schema")
    return list(metadata.sorted_tables)
