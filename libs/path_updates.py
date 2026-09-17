"""Replay the same ordered file moves against stored paths without filesystem IO."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
