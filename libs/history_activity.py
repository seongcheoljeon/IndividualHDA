"""Audit events as non-version history rows; personal and team share this.

Renames and preview videos are recorded in ``audit_events`` (personal, SQL
triggers) and ``team_audit_events`` (server) but never in ``hda_history``: the
v6 trigger turns every history row into a version. So activity reaches the
History panel as rows built here, marked ``kind != "version"``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from libs import keys
from libs.asset_contracts import HistoryData

ACTIVITY_OPERATIONS = (
    "hda_key.update",
    "video_info.insert",
    "video_info.update",
)


def changes(event: Mapping[str, Any]) -> dict[str, Any]:
    """The ``changes`` payload as a dict; personal rows keep the JSON text."""
    value = event.get("changes") or {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def rename_names(event: Mapping[str, Any]) -> tuple[str, str] | None:
    """(old, new) when the event renamed the asset, else None.

    The server writes a per-key diff (``{"name": {"before", "after"}}``); the
    personal trigger writes whole rows and also fires for a category-only edit,
    which is not a rename.
    """
    diff = changes(event)
    operation = event.get("operation")
    if operation == "rename":
        entry = diff.get("name")
        if isinstance(entry, dict) and entry.get("before") is not None:
            return str(entry["before"]), str(entry.get("after") or "")
        return None
    if operation == "hda_key.update":
        old = (diff.get("before") or {}).get("name")
        new = (diff.get("after") or {}).get("name")
        if old is not None and new is not None and old != new:
            return str(old), str(new)
    return None


def video_action(event: Mapping[str, Any]) -> str | None:
    """'insert' | 'update' when the event attached or replaced the video."""
    operation = event.get("operation")
    if operation == "video_info.insert":
        return "insert"
    if operation == "video_info.update":
        return "update"
    if operation == "media":
        files = changes(event).get("files") or {}
        before, after = files.get("before") or {}, files.get("after") or {}
        if "video" in after and after.get("video") != before.get("video"):
            return "update" if "video" in before else "insert"
    return None


def local_time(value: Any) -> str:
    """ISO UTC ('Z' or offset) to the panel's local ``hda_history`` format."""
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return ""
    return moment.astimezone().strftime(keys.Value.datetime_fmt_str)


def activity_comment(event: Mapping[str, Any]) -> tuple[str, str] | None:
    """(kind, comment) for a row the panel shows; None for everything else."""
    names = rename_names(event)
    if names is not None:
        return "rename", f"NAME (CHANGE) {names[0]} → {names[1]}"
    action = video_action(event)
    if action is not None:
        return "video", f"VIDEO ({action.upper()})"
    return None


def activity_rows(
    events: Iterable[Mapping[str, Any]], **shared: Any
) -> list[HistoryData]:
    """Build history rows from event dicts.

    Each event carries ``operation, actor, occurred_at, changes`` plus the asset
    it belongs to (``hda_id``, ``org_hda_name``, optional ``node_category``).
    ``shared`` (``remote=``, ``library_id=``) is applied to every row. A rename
    moves the video folder in the same request, so that ``video_info.update``
    is dropped as noise.
    """
    items = list(events)
    rename_requests = {
        item.get("request_id")
        for item in items
        if item.get("operation") == "hda_key.update"
    } - {None}
    rows = []
    for item in items:
        if (
            item.get("operation") == "video_info.update"
            and item.get("request_id") in rename_requests
        ):
            continue
        shown = activity_comment(item)
        if shown is None:
            continue
        kind, comment = shown
        rows.append(
            HistoryData(
                kind=kind,
                hda_id=int(item["hda_id"]),
                org_hda_name=item.get("org_hda_name") or "",
                version="",
                comment=comment,
                reg_time=local_time(item.get("occurred_at")),
                userid=item.get("actor") or "",
                node_category=item.get("node_category") or "",
                **shared,
            )
        )
    return rows


def merge_history_rows(
    versions: Iterable[HistoryData], activity: Iterable[HistoryData]
) -> list[HistoryData]:
    """Chronological interleave; the sort is stable, so versions win ties."""
    return sorted([*versions, *activity], key=lambda row: row.reg_time)
