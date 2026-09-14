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


# Search syntax shared by the panel, the manager and the AI rewrite hook:
# whitespace-separated tokens are ANDed; ``*``/``?`` are wildcards; an optional
# ``name:``/``tag:``/``type:``/``note:`` prefix restricts one token to a field.
_FIELD_ALIASES = {
    "name": "Name",
    "tag": "Tags",
    "tags": "Tags",
    "type": "Type",
    "note": "Note",
}
_TAG_MATCH = (
    "EXISTS (SELECT 1 FROM asset_tags t WHERE t.hda_key_id=k.id AND t.tag {op} ?{esc})"
)
_FIELD_COLUMNS: dict[str, tuple[str, ...]] = {
    "Name": ("k.name",),
    "Tags": (_TAG_MATCH,),
    "Type": ("COALESCE(n.node_type_name,'')",),
    "Note": ("COALESCE(o.note,'')",),
}
_FIELD_COLUMNS["All"] = (
    *_FIELD_COLUMNS["Name"],
    *_FIELD_COLUMNS["Tags"],
    *_FIELD_COLUMNS["Type"],
    "COALESCE(n.node_def_desc,'')",
    *_FIELD_COLUMNS["Note"],
)


def _pattern(text: str, case_sensitive: bool) -> tuple[str, str, str]:
    """Return (operator, escape clause, pattern) for one token."""
    if case_sensitive:
        # GLOB keeps * and ? as wildcards; only character classes need escaping.
        return "GLOB", "", "*" + text.replace("[", "[[]") + "*"
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    escaped = escaped.replace("*", "%").replace("?", "_")
    return "LIKE", " ESCAPE '\\'", "%" + escaped + "%"


def _token_clause(
    token: str, field: str, case_sensitive: bool
) -> tuple[str, list[str]]:
    prefix, sep, rest = token.partition(":")
    if sep and rest and prefix.lower() in _FIELD_ALIASES:
        field, token = _FIELD_ALIASES[prefix.lower()], rest
    op, esc, pattern = _pattern(token, case_sensitive)
    columns = _FIELD_COLUMNS.get(field, _FIELD_COLUMNS["All"])
    parts = []
    for column in columns:
        if column is _TAG_MATCH:
            parts.append(column.format(op=op, esc=esc))
        else:
            parts.append(f"{column} {op} ?{esc}")
    return "(" + " OR ".join(parts) + ")", [pattern] * len(parts)


def search_asset_ids(
    database: Path,
    query: str,
    *,
    user: str | None = None,
    field: str = "All",
    case_sensitive: bool = False,
    limit: int = 5000,
    cancel: threading.Event | None = None,
) -> list[int]:
    """Asset ids whose fields match every token of ``query`` (see syntax above).

    An empty query matches every asset; callers keep that case local instead.
    """
    # ponytail: LIKE/GLOB full scan; swap the body for FTS5 (trigram) if the
    # library grows past ~50k rows or ranking is needed. Callers stay unchanged.
    tokens = query.split()
    clauses: list[str] = ["(? IS NULL OR k.user_id = ?)"]
    params: list[object] = [user, user]
    for token in tokens:
        clause, token_params = _token_clause(token, field, case_sensitive)
        clauses.append(clause)
        params.extend(token_params)
    sql = f"""SELECT k.id FROM hda_key k
        LEFT JOIN houdini_node_info n ON n.hda_key_id=k.id
        LEFT JOIN note_info o ON o.hda_key_id=k.id
        WHERE {" AND ".join(clauses)} ORDER BY k.id LIMIT ?"""
    params.append(limit)
    with read_database(database, cancel) as connection:
        rows = connection.execute(sql, params).fetchall()
        check_cancel(cancel)
        return [row[0] for row in rows]


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
