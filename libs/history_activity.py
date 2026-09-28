"""Audit events as non-version history rows; personal and team share this.

Renames and preview videos are recorded in ``audit_events`` (personal, SQL
triggers) and ``team_audit_events`` (server) but never in ``hda_history``: the
v6 trigger turns every history row into a version. So activity reaches the
History panel as rows built here, marked ``kind != "version"``. In the table
such a row borrows the version it happened to (``merge_history_rows``), so it
reads like the "NODE (INSERT)" row above it, with "VIDEO (INSERT)" as comment.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import datetime
from typing import Any

from libs import keys
from libs.asset_contracts import HistoryData

# Personal audit operations the History panel shows as rows.
ACTIVITY_OPERATIONS = (
    "hda_key.update",
    "video_info.insert",
    "video_info.update",
    "thumbnail_info.update",
)
# Operations whose request also rewrites the media rows: a rename moves the
# files, a new version captures a thumbnail. Those media events are noise.
REQUEST_MARKERS = ("hda_key.update", "hda_history.insert")
NOISE_OPERATIONS = ("video_info.update", "thumbnail_info.update")


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


def _media_action(event: Mapping[str, Any], table: str, kind: str) -> str | None:
    """'insert' | 'update' when the event attached or replaced that media.

    Personal rows come from the ``<table>.insert/update`` triggers; the server
    writes one ``media`` event with the files diff.
    """
    operation = event.get("operation")
    if operation == f"{table}.insert":
        return "insert"
    if operation == f"{table}.update":
        return "update"
    if operation == "media":
        files = changes(event).get("files") or {}
        before, after = files.get("before") or {}, files.get("after") or {}
        if kind in after and after.get(kind) != before.get(kind):
            return "update" if kind in before else "insert"
    return None


def video_action(event: Mapping[str, Any]) -> str | None:
    return _media_action(event, "video_info", "video")


def thumbnail_action(event: Mapping[str, Any]) -> str | None:
    return _media_action(event, "thumbnail_info", "thumbnail")


def media_version(event: Mapping[str, Any]) -> str:
    """The version a personal media event was made for ('' before schema v7)."""
    after = changes(event).get("after") or {}
    return str(after.get("version") or "")


def local_time(value: Any) -> str:
    """ISO UTC ('Z' or offset) to the panel's local ``hda_history`` format."""
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return ""
    return moment.astimezone().strftime(keys.Value.datetime_fmt_str)


def activity_title(event: Mapping[str, Any]) -> str | None:
    """What happened, in words, or None when the panel does not show the event.

    The History table and the Version details dialog both label these events, so
    they say it the same way: "VIDEO (INSERT)" read like a database row.
    """
    names = rename_names(event)
    if names is not None:
        return f'Renamed "{names[0]}" → "{names[1]}"'
    action = video_action(event)
    if action is not None:
        return "Video attached" if action == "insert" else "Video replaced"
    action = thumbnail_action(event)
    if action is not None:
        return "Thumbnail attached" if action == "insert" else "Thumbnail replaced"
    return None


def activity_comment(event: Mapping[str, Any]) -> str | None:
    """The History table's Comment for the event, in the style of "NODE (INSERT)"."""
    names = rename_names(event)
    if names is not None:
        return f"NAME (CHANGE) {names[0]} → {names[1]}"
    for label, action in (
        ("VIDEO", video_action(event)),
        ("THUMBNAIL", thumbnail_action(event)),
    ):
        if action is not None:
            return f"{label} ({action.upper()})"
    return None


def activity_kind(event: Mapping[str, Any]) -> str | None:
    """ "rename" | "video" | "thumbnail" for a row the panel shows; else None."""
    if rename_names(event) is not None:
        return "rename"
    if video_action(event) is not None:
        return "video"
    if thumbnail_action(event) is not None:
        return "thumbnail"
    return None


def activity_rows(
    events: Iterable[Mapping[str, Any]], **shared: Any
) -> list[HistoryData]:
    """Build history rows from event dicts.

    Each event carries ``operation, actor, occurred_at, changes`` plus the asset
    it belongs to (``hda_id``, ``org_hda_name``, optional ``node_category``).
    ``shared`` (``remote=``, ``library_id=``) is applied to every row. A rename
    moves the media folders and a new version captures its thumbnail in the
    same request, so those media updates are dropped as noise.
    """
    items = list(events)
    busy_requests = {
        item.get("request_id")
        for item in items
        if item.get("operation") in REQUEST_MARKERS
    } - {None}
    rows = []
    for item in items:
        if (
            item.get("operation") in NOISE_OPERATIONS
            and item.get("request_id") in busy_requests
        ):
            continue
        kind = activity_kind(item)
        if kind is None:
            continue
        rows.append(
            HistoryData(
                kind=kind,
                comment=activity_comment(item),
                hda_id=int(item["hda_id"]),
                org_hda_name=item.get("org_hda_name") or "",
                version=media_version(item) if kind != "rename" else "",
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
    """Chronological interleave; the sort is stable, so versions win ties.

    An event row borrows the version it happened to: the one it names, else the
    newest row of its asset at that moment (the newest at all when the clocks
    disagree), keeping only its own kind, comment, time and actor. So a video
    or a rename shows the same thumbnail, id, version, definition and Houdini
    version as the version row it belongs to, the way the original app copied
    the current row. With no version left (trashed), the event stays as it is.
    """
    ordered = sorted(versions, key=lambda row: row.reg_time)
    by_asset: dict[int, list[HistoryData]] = {}
    for row in ordered:
        by_asset.setdefault(row.hda_id, []).append(row)
    rows = list(ordered)
    for event in activity:
        candidates = by_asset.get(event.hda_id) or []
        named = [
            row for row in candidates if event.version and row.version == event.version
        ]
        current = named or [row for row in candidates if row.reg_time <= event.reg_time]
        source = (current or candidates)[-1] if candidates else None
        if source is not None:
            event = replace(
                source,
                kind=event.kind,
                comment=event.comment,
                reg_time=event.reg_time,
                userid=event.userid,
            )
        rows.append(event)
    return sorted(rows, key=lambda row: row.reg_time)
