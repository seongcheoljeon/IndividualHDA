"""Kill a separate process between persistent writes; recover in a fresh owner."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from libs.operation_journal import durable_operation, recover_operations
from libs.sqlite3_db_api import SQLite3DatabaseAPI


@pytest.mark.parametrize("step", [1, 2, 3, 4])
def test_import_crash_after_each_rename(tmp_path: Path, step: int) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "old").write_text("old")
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage" / "new").write_text("new")
    (tmp_path / "stage" / "ihda.db").write_text("new db")
    (tmp_path / "ihda.db").write_text("old db")
    code = """
import os, sys
from pathlib import Path
from libs.operation_journal import durable_operation
root = Path(sys.argv[1])
original = Path.rename
count = 0
def crash(source, destination):
    global count
    result = original(source, destination)
    count += 1
    if count == int(sys.argv[2]): os._exit(71)
    return result
Path.rename = crash
with durable_operation(root) as journal:
    for source, destination in [('assets','old-assets'), ('ihda.db','old.db'), ('stage/ihda.db','ihda.db'), ('stage','assets')]:
        journal.move(root/source, root/destination)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), str(step)],
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 71
    assert len(recover_operations(tmp_path)) == 1
    assert (tmp_path / "ihda.db").read_text() == "old db"
    assert (tmp_path / "assets" / "old").read_text() == "old"
    assert (tmp_path / "stage" / "new").read_text() == "new"
    assert (tmp_path / "stage" / "ihda.db").read_text() == "new db"
    assert recover_operations(tmp_path) == []


@pytest.mark.parametrize("committed", [False, True])
def test_database_commit_decides_recovery(tmp_path: Path, committed: bool) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        db.insert_users("user", "old")
    (tmp_path / "old.hda").write_text("asset")
    code = """
import os, sys
from pathlib import Path
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.operation_journal import durable_operation, MoveJournal
root = Path(sys.argv[1])
MoveJournal.finish = lambda self: os._exit(72)
with SQLite3DatabaseAPI(root/'ihda.db') as db:
    with durable_operation(root, db) as journal:
        journal.move(root/'old.hda', root/'new.hda')
        db._connect.execute("UPDATE users SET email='new'")
        if sys.argv[2] == 'False': os._exit(72)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), str(committed)],
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 72
    recover_operations(tmp_path)
    with sqlite3.connect(tmp_path / "ihda.db") as db:
        assert db.execute("SELECT email FROM users").fetchone()[0] == (
            "new" if committed else "old"
        )
    assert (tmp_path / ("new.hda" if committed else "old.hda")).is_file()


def test_recovery_conflict_retains_both_files(tmp_path: Path) -> None:
    from libs.operation_journal import MoveJournal

    (tmp_path / "old").write_text("original")
    journal = MoveJournal(tmp_path)
    journal.move(tmp_path / "old", tmp_path / "new")
    (tmp_path / "old").write_text("external")
    with pytest.raises(RuntimeError, match="conflict"):
        recover_operations(tmp_path)
    assert (tmp_path / "new").read_text() == "original"
    assert (tmp_path / "old").read_text() == "external"
    assert journal.path.exists()


def test_nested_database_transaction_savepoint(tmp_path: Path) -> None:
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        with db.transaction():
            db.insert_users("outer", "keep")
            with pytest.raises(ValueError), db.transaction():
                db.insert_users("inner", "discard")
                raise ValueError("fail inner")
            db.insert_users("after", "keep-after")
        assert set(db.get_user_id()) == {"outer", "after"}


def test_delete_asset_rolls_back_files_when_database_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs.asset_commands import delete_asset

    assets = tmp_path / "Water"
    assets.mkdir()
    (assets / "water.hda").write_text("asset")
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        db.insert_users("user", "user@example.com")
        db.insert_hda_category("sop", "user")
        db.insert_hda_key("Water", "sop", "user")
        db._connect.execute("""CREATE TRIGGER reject_trash BEFORE UPDATE OF deleted_at ON asset_identity
            BEGIN SELECT RAISE(ABORT,'simulated write failure'); END""")
        with pytest.raises(sqlite3.DatabaseError):
            delete_asset(db, 1)
        assert (assets / "water.hda").read_text() == "asset"
        assert (
            db._connect.execute("SELECT deleted_at FROM asset_identity").fetchone()[0]
            is None
        )
        db._connect.execute("DROP TRIGGER reject_trash")
        delete_asset(db, 1)
        assert assets.exists()
        assert db._connect.execute("SELECT deleted_at FROM asset_identity").fetchone()[
            0
        ]
        assert not list(tmp_path.glob(".ihda-deleted-*"))


def test_version_one_migration_adds_operation_markers(tmp_path: Path) -> None:
    path = tmp_path / "ihda.db"
    from libs.database_migrations_v4 import migrate as migrate_v4

    with sqlite3.connect(path) as db:
        migrate_v4(db, path)
        db.execute("INSERT INTO users VALUES('keep','keep@example.com','2020-01-01')")
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE operation_commits")
        connection.execute("PRAGMA user_version=1")
    with SQLite3DatabaseAPI(path) as db:
        assert db.get_user_id() == ["keep"]
        with db.transaction():
            db.record_operation_commit("test")
    assert list(tmp_path.glob("ihda.db.pre-v*-*.bak"))


def test_durable_operation_requires_outermost_database_transaction(
    tmp_path: Path,
) -> None:
    with (
        SQLite3DatabaseAPI(tmp_path / "ihda.db") as db,
        db.transaction(),
        pytest.raises(RuntimeError, match="outer database transaction"),
        durable_operation(tmp_path, db),
    ):
        pytest.fail("must reject before any file work")
    assert not list(tmp_path.glob(".ihda-operation-*.json"))


def test_v1_journal_recovers_and_new_journals_write_named_moves(tmp_path: Path) -> None:
    import json

    from libs.operation_journal import MoveJournal

    source, destination = tmp_path / "old", tmp_path / "new"
    destination.write_text("original")
    journal_path = tmp_path / ".ihda-operation-historical.json"
    journal_path.write_text(
        json.dumps(
            {
                "version": 1,
                "id": "historical",
                "database": None,
                "committed": False,
                "moves": [[str(source), str(destination)]],
            }
        )
    )
    assert recover_operations(tmp_path) == [journal_path]
    assert source.read_text() == "original" and not destination.exists()
    journal = MoveJournal(tmp_path)
    journal.move(source, destination)
    document = json.loads(journal.path.read_text())
    assert document["version"] == 2
    assert document["moves"] == [
        {"source": str(source), "destination": str(destination)}
    ]
    journal.rollback()
    assert source.read_text() == "original"
