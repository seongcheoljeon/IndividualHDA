"""Atomic UTF-8 settings writes retain the last complete configuration on failure."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


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
