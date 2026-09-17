"""Resolve optional paths from local or remote library metadata."""

from pathlib import Path


def item_path(directory: Path | None, filename: str | None) -> Path | None:
    return directory / filename if directory is not None and filename else None
