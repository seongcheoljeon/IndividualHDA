"""Replay the same ordered file moves against stored paths without filesystem IO."""

from __future__ import annotations
from pathlib import Path

PathMoves = tuple[tuple[Path, Path], ...]


def relocated_path(path: Path, moves: PathMoves) -> Path:
    for source, target in moves:
        try:
            relative = path.relative_to(source)
        except ValueError:
            continue
        path = target / relative
    return path
