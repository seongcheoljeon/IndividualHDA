"""Purging drops rows; the files wait in a queue until reclaim() frees them."""

from __future__ import annotations

from pathlib import Path

from support.personal import payload

from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.library_management import LocalManagement
from libs.paths import hda_base_dirpath
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def test_reclaim_previews_then_deletes_only_unreferenced_library_files(
    tmp_path: Path,
) -> None:
    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repo = SqliteLibraryRepository(database)
    repo.ensure_user("tester")
    root = hda_base_dirpath(base_dirpath=tmp_path) / "tester"
    asset = repo.register_asset(payload(root, "Water")).asset
    hda = asset.hda_dirpath / asset.hda_filename
    thumbnail = asset.thumbnail_dirpath / asset.thumbnail_filename
    assert hda.is_file() and thumbnail.is_file()
    # A file outside the managed root must never be touched, even if queued.
    stray = tmp_path / "elsewhere.hda"
    stray.write_text("keep me", encoding="utf-8")
    with SQLite3DatabaseAPI(database) as db:
        db._connect.execute("INSERT INTO file_cleanup(path) VALUES(?)", (str(stray),))
        db._connect.commit()

    gateway = LocalManagement(database)
    assert gateway.reclaim(False) == [
        {
            "path": str(stray),
            "bytes": len("keep me"),
            "status": "Outside the managed asset root or symbolic link",
        }
    ]
    repo.delete_asset(asset.hda_id, asset.hda_dirpath)
    gateway.change({"asset_id": asset.hda_id, "history_id": None}, "purge")

    preview = gateway.reclaim(False)
    candidates = {row["path"] for row in preview if row["status"] == "candidate"}
    assert candidates == {str(hda), str(thumbnail)}
    assert all(row["bytes"] > 0 for row in preview if row["status"] == "candidate")
    assert hda.is_file()  # a preview deletes nothing

    applied = gateway.reclaim(True)
    assert {row["path"] for row in applied if row["status"] == "removed"} == candidates
    assert not hda.exists() and not thumbnail.exists() and stray.exists()
    # Empty directories go with the files, up to (not including) the asset root.
    assert not hda.parent.exists() and not thumbnail.parent.exists()
    assert not root.exists() and root.parent.exists()
    assert {row["path"] for row in applied if row["status"] == "removed directory"} >= {
        str(hda.parent),
        str(thumbnail.parent),
    }
    assert gateway.reclaim(False) == [
        {
            "path": str(stray),
            "bytes": len("keep me"),
            "status": "Outside the managed asset root or symbolic link",
        }
    ]
