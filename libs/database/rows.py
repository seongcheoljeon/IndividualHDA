"""Named SQLite reads and typed application record decoding."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from libs.asset_contracts import AssetData, HistoryData
from libs.item_paths import path_exists
from libs.record_codec import decode_record
from libs.tags import normalize_tags

# Soft deletes live in asset_identity / version_identity, not in the rows they
# hide. Every read of hda_key or hda_history must apply one of these, e.g.
# ``WHERE k.id {LIVE_ASSET_IDS}``; writing the subquery by hand is how trashed
# assets kept leaking into tags, icons and the category tree.
LIVE_ASSET_IDS = "IN (SELECT asset_id FROM asset_identity WHERE deleted_at IS NULL)"
LIVE_HISTORY_IDS = (
    "IN (SELECT history_id FROM version_identity WHERE deleted_at IS NULL)"
)


def named_query(
    connection: sqlite3.Connection,
    sql: str,
    parameters: Mapping[str, Any] | None = None,
) -> sqlite3.Cursor:
    """Use a private cursor; never change the caller's connection row factory."""
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row
    try:
        cursor.execute(sql, parameters if parameters is not None else {})
        names = [column[0].casefold() for column in cursor.description or ()]
        if not names or len(names) != len(set(names)):
            raise ValueError("Named queries require unique result column names")
        return cursor
    except BaseException:
        cursor.close()
        raise


def require_fields(row: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    """Select fields by name, raising KeyError for an incomplete projection."""
    return {field: row[field] for field in fields}


def _paths(data: dict[str, Any], fields: Sequence[str]) -> None:
    for field in fields:
        value = data[field]
        data[field] = Path(value) if value is not None else None


def asset_data(row: Mapping[str, Any]) -> AssetData:
    data = dict(row)
    _paths(data, ("hda_dirpath", "hip_dirpath", "thumbnail_dirpath", "video_dirpath"))
    for field in ("is_favorite_hda", "is_network", "is_sub_network"):
        data[field] = bool(data[field])
    data["hda_icon"] = data["hda_icon"].split(",") if data["hda_icon"] else []
    data["hda_tags"] = normalize_tags(data["hda_tags"]) if data["hda_tags"] else []
    data["available"] = path_exists(data["hda_dirpath"], data.get("hda_filename"))
    return decode_record(AssetData, data)


def history_record(row: Mapping[str, Any]) -> HistoryData:
    data = dict(row)
    _paths(data, ("ihda_dirpath", "hip_dirpath", "thumb_dirpath", "video_dirpath"))
    data["icon"] = data["icon"].split(",") if data["icon"] else []
    data["tags"] = normalize_tags(data["tags"]) if data["tags"] else []
    data["available"] = path_exists(data["ihda_dirpath"], data.get("ihda_filename"))
    return decode_record(HistoryData, data)
