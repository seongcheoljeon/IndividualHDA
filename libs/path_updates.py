"""Replay the same ordered file moves against stored paths without filesystem IO."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from libs.asset_contracts import HistoryData
from libs.item_paths import path_exists


@dataclass(frozen=True, slots=True, kw_only=True)
class PathMove:
    source: Path
    target: Path


PathMoves = tuple[PathMove, ...]


def relocated_path(path: Path, moves: PathMoves) -> Path:
    for move in moves:
        try:
            relative = path.relative_to(move.source)
        except ValueError:
            continue
        path = move.target / relative
    return path


HISTORY_FILE_FIELDS = (
    ("ihda_dirpath", "ihda_filename"),
    ("thumb_dirpath", "thumb_filename"),
    ("video_dirpath", "video_filename"),
)


def relocate_history(item: HistoryData, moves: PathMoves) -> HistoryData:
    """The history row after its files followed ``moves``; availability rechecked."""
    changes: dict[str, Any] = {}
    for directory_key, filename_key in HISTORY_FILE_FIELDS:
        directory, filename = getattr(item, directory_key), getattr(item, filename_key)
        if isinstance(directory, Path) and isinstance(filename, str):
            path = relocated_path(directory / filename, moves)
            changes[directory_key], changes[filename_key] = path.parent, path.name
    moved = replace(item, **changes)
    return replace(
        moved, available=path_exists(moved.ihda_dirpath, moved.ihda_filename)
    )
