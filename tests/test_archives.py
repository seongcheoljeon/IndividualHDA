from __future__ import annotations

import pathlib
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import pytest

from libs.archive_service import create_archive, extract_archive, prepare_database
from libs.data_stream import DataStream
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def library(root: Any) -> Any:
    assets = root / "houdini" / "individualHDA" / "anonymous"
    asset = assets / "sop" / "asset's 한글"
    asset.mkdir(parents=True)
    (asset / "asset.hda").write_bytes(b"asset data")
    with SQLite3DatabaseAPI(root / "ihda.db") as db:
        db.insert_users("anonymous", "a@example.com")
        db.insert_hda_category("sop", "anonymous")
        db.insert_hda_key("asset's 한글", "sop", "anonymous")
        key = db.get_hda_key_id(user_id="anonymous")[0]
        db.insert_hda_info(key, "1.0", filename="asset.hda", dirpath=asset)
    return assets


@pytest.mark.parametrize(
    "entry",
    ["../escape", "/absolute", "C:/windows", "a\\..\\escape", "file:stream", "a./x"],
)
def test_unsafe_archive_rejected(tmp_path: pathlib.Path, entry: Any) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("ihda.db", b"")
        out.writestr(entry, b"bad")
    stage = tmp_path / "stage"
    stage.mkdir()
    with pytest.raises(ValueError):
        extract_archive(archive, stage)
    assert list(stage.iterdir()) == []


def test_archive_roundtrip_relocates_assets(tmp_path: pathlib.Path) -> None:
    original = tmp_path / "original"
    assets = library(original)
    archive = create_archive(original / "ihda.db", assets, tmp_path / "library.zip")
    destination = tmp_path / "different 한글"
    stage = tmp_path / "stage"
    stage.mkdir()
    extract_archive(archive, stage)
    prepare_database(stage, destination)
    with sqlite3.connect(stage / "ihda.db") as db:
        path = db.execute("SELECT dirpath FROM hda_info").fetchone()[0]
        assert Path(path) == destination / "sop" / "asset's 한글"
    assert (stage / "sop" / "asset's 한글" / "asset.hda").read_bytes() == b"asset data"


def test_wal_snapshot_includes_uncheckpointed_commits(tmp_path: pathlib.Path) -> None:
    assets = library(tmp_path)
    with sqlite3.connect(tmp_path / "ihda.db") as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE users SET email = 'new@example.com'")
        writer.commit()
        archive = create_archive(tmp_path / "ihda.db", assets, tmp_path / "library.zip")
    stage = tmp_path / "stage"
    stage.mkdir()
    extract_archive(archive, stage)
    with sqlite3.connect(stage / "ihda.db") as db:
        assert db.execute("SELECT email FROM users").fetchone()[0] == "new@example.com"


def test_import_commit_and_rollback(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    assets = library(source)
    archive = create_archive(source / "ihda.db", assets, tmp_path / "export.zip")
    destination = tmp_path / "destination"
    target_assets = library(destination)
    stream = DataStream("anonymous", target_assets, destination)
    assert stream.import_ihda_data(archive).is_file()
    original_rename = Path.rename

    def fail_stage(path: Any, target: Any) -> Any:
        if path == stream.stage:
            raise OSError("Injected rename failure")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_stage)
    with pytest.raises(OSError):
        stream.commit_import()
    assert (destination / "ihda.db").is_file()
    assert (target_assets / "sop" / "asset's 한글" / "asset.hda").is_file()
    monkeypatch.setattr(Path, "rename", original_rename)
    stream.commit_import()
    assert stream.stage is None
    assert list(destination.glob("ihda.db.previous-*"))
