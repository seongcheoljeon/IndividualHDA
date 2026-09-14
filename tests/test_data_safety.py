from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from test_sqlite_repository import payload

from libs.archive_transfer import ArchiveTransfer
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.library_backups import AUTO_BACKUP_PREFIX, auto_backup
from libs.repository import LibraryConflict, LibraryError
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def make_library(tmp_path: Path) -> SqliteLibraryRepository:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db"):
        pass
    repo = SqliteLibraryRepository(tmp_path / "ihda.db")
    repo.ensure_user("tester")
    return repo


def test_failed_registration_removes_the_files_it_created(tmp_path: Path) -> None:
    repo = make_library(tmp_path)
    repo.register_asset(payload(tmp_path, "Water"))
    duplicate = payload(tmp_path / "second", "Water")  # same name -> conflict
    with pytest.raises(LibraryConflict):
        repo.register_asset(duplicate)
    assert not (duplicate.hda_dirpath / duplicate.hda_filename).exists()
    assert not (duplicate.thumb_dirpath / duplicate.thumb_filename).exists()
    assert not duplicate.hda_dirpath.exists()  # emptied directories are removed

    class BrokenHistory(SQLite3DatabaseAPI):
        def insert_hda_history(self, data: Any = None) -> int | None:
            return None

    broken = SqliteLibraryRepository(tmp_path / "ihda.db", open_database=BrokenHistory)
    fire = payload(tmp_path, "Fire")
    with pytest.raises(LibraryError):
        broken.register_asset(fire)
    assert not (fire.hda_dirpath / fire.hda_filename).exists()
    assert repo.list_assets() and repo.list_assets()[0]["hda_name"] == "Water"


def test_wal_mode_lets_a_reader_see_writes_and_revision_moves(tmp_path: Path) -> None:
    repo = make_library(tmp_path)
    with closing(sqlite3.connect(tmp_path / "ihda.db")) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    before = repo.revision()
    time.sleep(0.02)
    reader = sqlite3.connect(f"file:{tmp_path / 'ihda.db'}?mode=ro", uri=True)
    try:
        reader.execute("SELECT COUNT(*) FROM hda_key").fetchone()  # open read txn
        repo.register_asset(payload(tmp_path, "Water"))  # writer is not blocked
        assert reader.execute("SELECT COUNT(*) FROM hda_key").fetchone()[0] == 1
    finally:
        reader.close()
    assert repo.revision() > before


def test_import_commit_moves_wal_sidecars_with_the_database(tmp_path: Path) -> None:
    directory = tmp_path
    assets = directory / "houdini" / "IndividualHDA"
    assets.mkdir(parents=True)
    (directory / "ihda.db").write_bytes(b"old")
    (directory / "ihda.db-wal").write_bytes(b"old-wal")
    (directory / "ihda.db-shm").write_bytes(b"old-shm")
    stage = directory / "stage"
    stage.mkdir()
    (stage / "ihda.db").write_bytes(b"new")
    transfer = ArchiveTransfer(assets, directory)
    transfer.stage = stage
    transfer.commit_import()
    assert (directory / "ihda.db").read_bytes() == b"new"
    assert (
        not (directory / "ihda.db-wal").exists()
        and not (directory / "ihda.db-shm").exists()
    )
    previous = sorted(directory.glob("ihda.db.previous-*"))
    assert [
        p.name.rsplit("-", 1)[-1] for p in previous if p.name.endswith(("-wal", "-shm"))
    ] == ["shm", "wal"]


def test_auto_backup_is_daily_and_bounded(tmp_path: Path) -> None:
    make_library(tmp_path)
    database = tmp_path / "ihda.db"
    first = auto_backup(database)
    assert first is not None and first.name.startswith(AUTO_BACKUP_PREFIX)
    with closing(sqlite3.connect(first)) as copy:
        assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert auto_backup(database) is None  # younger than a day
    old = time.time() - 2 * 86400
    os.utime(first, (old, old))
    for index in range(9):  # simulate a history of stale copies
        stale = database.with_name(f"{AUTO_BACKUP_PREFIX}2020010{index}T000000Z.bak")
        stale.write_bytes(b"x")
        os.utime(stale, (old, old))
    second = auto_backup(database, keep=3)
    assert second is not None
    remaining = sorted(database.parent.glob(AUTO_BACKUP_PREFIX + "*.bak"))
    assert len(remaining) == 3 and remaining[-1] == second
    assert auto_backup(tmp_path / "missing.db") is None
