"""Data-only serialization for internal asset drag/drop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6 import QtCore


def encode_payload(data: dict[str, Any]) -> bytes:
    def encode(value: Any) -> dict[str, str]:
        if isinstance(value, Path):
            return {"__ihda_path__": str(value)}
        raise TypeError(f"Unsupported drag data: {type(value).__name__}")

    return json.dumps(data, default=encode, ensure_ascii=False).encode("utf-8")


def decode_payload(data: str | bytes | bytearray | QtCore.QByteArray) -> dict[str, Any]:
    def decode(value: dict[str, Any]) -> dict[str, Any] | Path:
        if set(value) == {"__ihda_path__"}:
            return Path(value["__ihda_path__"])
        return value

    raw = bytes(data.data()) if isinstance(data, QtCore.QByteArray) else data
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Asset drag payload exceeds limit")
    result = json.loads(raw, object_hook=decode)
    if not isinstance(result, dict):
        raise ValueError("Asset drag payload must be an object")
    return result
