"""Copy a live SQLite database to another file with the online backup API."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


def backup_database(connection: sqlite3.Connection, destination: str | Path) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(destination))) as backup:
        connection.backup(backup)
