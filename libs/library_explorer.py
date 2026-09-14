"""Bounded, cancellable read-only library pages and history snapshots."""

from __future__ import annotations
from pathlib import Path
import threading
from typing import Any
from libs.library_maintenance import read_database, check_cancel


def search_assets(
    database: Path,
    user: str,
    text: str,
    field: str = "Name",
    offset: int = 0,
    limit: int = 200,
    cancel: threading.Event | None = None,
) -> list[dict[str, Any]]:
    if limit < 1 or limit > 1000 or offset < 0:
        raise ValueError("Invalid page bounds")
    columns = {
        "Name": "k.name",
        "Tags": "COALESCE(t.tag,'')",
        "Type": "COALESCE(n.node_type_name,'')",
    }
    column = columns[field]
    # Literal substring matching; SQL metacharacters are escaped, not executed.
    pattern = (
        "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    )
    with read_database(database, cancel) as connection:
        rows = connection.execute(
            f"""SELECT k.id,k.name,k.category,i.version,i.dirpath,i.filename
            FROM hda_key k JOIN hda_info i ON i.hda_key_id=k.id
            LEFT JOIN tag_info t ON t.hda_key_id=k.id
            LEFT JOIN houdini_node_info n ON n.hda_key_id=k.id
            WHERE k.user_id=? AND {column} LIKE ? ESCAPE '\\'
            ORDER BY k.name,k.id LIMIT ? OFFSET ?""",
            (user, pattern, limit, offset),
        ).fetchall()
        check_cancel(cancel)
        return [dict(row) for row in rows]


def history_versions(
    database: Path, asset_id: int, cancel: threading.Event | None = None
) -> list[dict[str, Any]]:
    with read_database(database, cancel) as connection:
        return [
            dict(row)
            for row in connection.execute(
                """SELECT h.*,
            (SELECT note FROM hda_note_history n WHERE n.hda_key_id=h.hda_key_id
             AND n.hda_version=h.version AND n.registration_datetime<=h.registration_datetime
             ORDER BY n.registration_datetime DESC,n.id DESC LIMIT 1) AS note
            FROM hda_history h WHERE h.hda_key_id=? ORDER BY h.id DESC""",
                (asset_id,),
            )
        ]
