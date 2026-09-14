"""Atomic UTF-8 settings writes retain the last complete configuration on failure."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def save_json(path: str | Path, values: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(values, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load_json(path: str | Path) -> dict[str, Any]:
    """Settings as a dict; a missing file is empty, a corrupt one is set aside.

    The corrupt file is renamed ``<name>.corrupt`` and the failure logged, so the
    application starts with defaults instead of failing in __init__.
    """
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, dict):
            raise ValueError("settings must contain a JSON object")
        return data
    except (ValueError, OSError) as error:
        corrupt = path.with_suffix(".corrupt")
        log.warning(
            "Settings file %s is unreadable (%s); moved to %s", path, error, corrupt
        )
        try:
            path.replace(corrupt)
        except OSError as move_error:
            log.warning("Could not set aside %s: %s", path, move_error)
        return {}


def apply_settings(
    values: dict[str, Any], table: Sequence[tuple[str, Callable[[Any], None]]]
) -> list[str]:
    """Apply each (key, setter) independently; a bad key never blocks the others.

    Missing keys keep their widget defaults silently (older files). A value of the
    wrong type is logged and skipped. Returns the keys that were not applied.
    """
    skipped: list[str] = []
    for key, setter in table:
        if key not in values:
            skipped.append(key)
            continue
        try:
            setter(values[key])
        except (TypeError, ValueError, OverflowError, AttributeError) as error:
            log.warning("Ignoring setting %s=%r: %s", key, values[key], error)
            skipped.append(key)
    return skipped


def initialize_config() -> None:
    """Carry existing settings into the writable per-user location on first use."""
    from shutil import copy2

    import public

    target = public.Paths.config_dirpath
    target.mkdir(parents=True, exist_ok=True)
    if os.getenv("IHDA_CONFIG_DIR"):
        return
    for source in (
        public.Paths._legacy_config,
        public.Paths.curt_script_dirpath / ".config",
    ):
        if source.resolve() == target.resolve() or not source.is_dir():
            continue
        for pattern in ("*.json", "*.ini"):
            for old in source.glob(pattern):
                destination = target / old.name
                if not destination.exists():
                    copy2(old, destination)
