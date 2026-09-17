"""Named application contracts and historical receipt compatibility."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError, asdict, fields, replace
from pathlib import Path

import pytest
from support.personal import payload

from libs.asset_contracts import AssetData, HistoryData, NodeConnection
from libs.drag_payload import decode_drag_record, encode_payload
from libs.model_columns import AssetColumn, HistoryColumn
from libs.record_codec import decode_record, record_document
from libs.registration_recovery import (
    decode_payload,
    decode_result,
    encode_result,
    fingerprint,
    payload_document,
)
from libs.repository import RegistrationResult


def test_named_records_reject_missing_unknown_and_positional_fields() -> None:
    with pytest.raises(ValueError, match="Invalid AssetData"):
        decode_record(AssetData, {"hda_name": "Water"})
    with pytest.raises(ValueError, match="named fields"):
        decode_record(AssetData, [1, "Water"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Unknown"):
        decode_record(AssetData, {"hda_id": 1, "hda_name": "Water", "typo": 0})
    with pytest.raises(ValueError, match="Invalid type"):
        decode_record(AssetData, {"hda_id": True, "hda_name": "Water"})
    asset = AssetData(hda_id=1, hda_name="Water", hda_tags=("fluid",))
    with pytest.raises(FrozenInstanceError):
        asset.hda_name = "Fire"
    assert decode_drag_record(encode_payload(asset)) == asset
    with pytest.raises(TypeError):
        AssetData(1, "Water")  # type: ignore[misc]


def test_v2_receipt_is_named_and_independent_of_document_field_order(
    tmp_path: Path,
) -> None:
    asset = AssetData(
        hda_id=7, hda_name="물", hda_dirpath=tmp_path, hda_tags=("fluid",)
    )
    history = HistoryData(
        hda_id=7, org_hda_name="물", version="1.0", icon=("SOP", "box")
    )
    result = RegistrationResult(
        asset=asset, history=history, history_id=9, thumb_filepath=tmp_path / "t.jpg"
    )
    document = json.loads(encode_result(result))
    assert document["format_version"] == 2 and isinstance(document["history"], dict)
    for key in ("asset", "history"):
        document[key] = dict(reversed(list(document[key].items())))
    assert decode_result(json.dumps(document)) == result
    with pytest.raises(ValueError, match="Unsupported"):
        decode_result(json.dumps({**document, "format_version": 999}))


def test_v1_receipt_reader_preserves_paths_flags_and_history(tmp_path: Path) -> None:
    # Frozen pre-v2 disk layout, intentionally independent of the live dataclass order.
    history = [
        7,
        "created",
        "Water",
        "1.0",
        "Water.hda",
        str(tmp_path),
        "2026-01-01",
        "21",
        "scene.hip",
        str(tmp_path),
        "commercial",
        "Linux",
        "/obj/Water",
        "Box",
        "box",
        "sop",
        "tester",
        ["SOP", "box"],
        "t.jpg",
        str(tmp_path),
        None,
        None,
    ]
    document = {
        "asset": {"hda_id": 7, "hda_name": "Water", "is_favorite_hda": 1},
        "history": history,
        "history_id": 9,
        "thumb_filepath": str(tmp_path / "t.jpg"),
    }
    result = decode_result(json.dumps(document))
    assert result.asset.is_favorite_hda is True
    assert result.history.ihda_dirpath == tmp_path and result.history.version == "1.0"
    assert result.history.icon == ("SOP", "box")
    document["history"] = history[:-1]
    with pytest.raises(ValueError, match="v1"):
        decode_result(json.dumps(document))


def test_capture_job_fingerprint_survives_v1_and_v2_decoding(tmp_path: Path) -> None:
    request = replace(
        payload(tmp_path, "Water"),
        input_conn=(
            NodeConnection(port=2, node_name="input", node_type="box", peer_port=0),
        ),
    )
    old_payload = json.loads(json.dumps(asdict(request), default=str))
    old_payload["input_conn"] = [[2, "input", "box", 0]]
    old_document = {"payload": old_payload, "asset_id": None}
    canonical = json.loads(json.dumps(old_document))
    canonical["payload"].pop("operation_id")
    expected = hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode()
    ).hexdigest()
    assert fingerprint(request, None) == expected
    for document in (old_document, payload_document(request, None)):
        decoded = decode_payload(document)
        assert decoded == request and fingerprint(decoded, None) == expected
    assert record_document(request)["input_conn"][0]["port"] == 2


def test_column_definitions_reference_named_fields() -> None:
    for columns, record in ((AssetColumn, AssetData), (HistoryColumn, HistoryData)):
        names = {field.name for field in fields(record)}
        assert all(column.field in names and column.label for column in columns)
        assert len({column.field for column in columns}) == len(columns)


def test_domain_imports_without_storage_ui_or_host() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import builtins
original = builtins.__import__
def checked(name, *args, **kwargs):
    if name.split('.')[0] in {'sqlite3', 'sqlalchemy', 'PySide6', 'hou', 'httpx'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = checked
import libs.asset_contracts
import libs.scene_contracts
import libs.asset_rename
import libs.asset_commands
import libs.asset_registration
import libs.asset_lifecycle
""",
        ],
        check=True,
    )
