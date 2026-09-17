"""Data-only serialization for internal asset drag/drop."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, SupportsBytes

from libs.asset_contracts import AssetData, HistoryData
from libs.record_codec import decode_record
from libs.scene_contracts import SceneRecord

DragRecord = AssetData | HistoryData | SceneRecord


def encode_payload(data: Any) -> bytes:
    if is_dataclass(data) and not isinstance(data, type):
        data = asdict(data)

    def encode(value: Any) -> dict[str, str]:
        if isinstance(value, Path):
            return {"__ihda_path__": str(value)}
        raise TypeError(f"Unsupported drag data: {type(value).__name__}")

    return json.dumps(data, default=encode, ensure_ascii=False).encode("utf-8")


def decode_payload(data: str | bytes | bytearray | SupportsBytes) -> dict[str, Any]:
    def decode(value: dict[str, Any]) -> dict[str, Any] | Path:
        if set(value) == {"__ihda_path__"}:
            return Path(value["__ihda_path__"])
        return value

    raw = data if isinstance(data, str) else bytes(data)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Asset drag payload exceeds limit")
    result = json.loads(raw, object_hook=decode)
    if not isinstance(result, dict):
        raise ValueError("Asset drag payload must be an object")
    return result


def decode_drag_record(data: str | bytes | bytearray | SupportsBytes) -> DragRecord:
    document = decode_payload(data)
    if "record_id" in document:
        return decode_record(SceneRecord, document)
    if "hist_id" in document:
        return decode_record(HistoryData, document)
    return decode_record(AssetData, document)
