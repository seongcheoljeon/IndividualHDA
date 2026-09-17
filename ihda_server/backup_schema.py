"""Version-specific backup inventory; older bundles restore before migration."""

from sqlalchemy import Table

from ihda_server import lifecycle_schema, tracking_schema  # noqa: F401
from ihda_server.schema import metadata


def backup_tables(version: int) -> list[Table]:
    if version not in {2, 3}:
        raise ValueError("Unsupported backup schema")
    tracking = {table.name for table in tracking_schema.TABLES}
    return [
        table
        for table in metadata.sorted_tables
        if version == 3 or table.name not in tracking
    ]
