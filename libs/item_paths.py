"""Resolve optional paths from local or remote library metadata."""

from pathlib import Path


def item_path(directory: Path | None, filename: str | None) -> Path | None:
    return directory / filename if directory is not None and filename else None


def path_exists(directory: Path | None, filename: str | None) -> bool:
    """One stat() when a row is built; views never touch the filesystem per repaint."""
    path = item_path(directory, filename)
    return path is not None and path.exists()
