from __future__ import annotations

import json
from pathlib import Path

import pytest
from support.team import server as server  # noqa: F401


def test_legacy_pending_requires_review_and_keeps_file(tmp_path: Path) -> None:
    from libs.team.contracts import TeamError
    from libs.team.pending import PendingCommand

    path = tmp_path / "pending.json"
    payload = {"operation": "metadata", "asset_id": 1, "values": {"note": "old draft"}}
    path.write_text(json.dumps(payload), encoding="utf-8")
    pending = PendingCommand(path)
    with pytest.raises(TeamError, match="pre-upgrade"):
        pending.load()
    assert pending.legacy() == payload and path.exists()
    pending.archive_legacy()
    assert pending.load() is None
    assert (
        json.loads(next(tmp_path.glob("*.pre-v2-*.json")).read_text(encoding="utf-8"))
        == payload
    )


def test_trash_is_retained_and_relocatable_in_backup(tmp_path: Path) -> None:
    from support.personal import payload

    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.library_backups import create_backup, validate_backup
    from libs.library_management import LocalManagement
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    first = repository.register_asset(payload(tmp_path, "Water"))
    repository.add_version(first.asset.hda_id, payload(tmp_path, "Water", "1.1"))
    management = LocalManagement(database)
    management.change(
        {"asset_id": first.asset.hda_id, "history_id": first.history_id}, "delete"
    )
    management.change({"asset_id": first.asset.hda_id, "history_id": None}, "delete")
    backup = create_backup(database, tmp_path / "sop", "Trash retained")
    assert "verified" in validate_backup(backup)
    assert first.thumb_filepath.exists()
    assert len(management.trash()) == 1


def test_file_integrity_survives_description_changes(tmp_path: Path) -> None:
    from support.personal import payload

    from libs.database.lifecycle import PersonalLifecycle, inspect_files
    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    first = repository.register_asset(payload(tmp_path, "Water"))
    with SQLite3DatabaseAPI(database) as db:
        inspect_files(db._connect)
        digest = db._connect.execute(
            "SELECT digest FROM version_files WHERE kind='asset'"
        ).fetchone()[0]
        with db.transaction():
            PersonalLifecycle(db._connect).details(
                first.history_id, {"description": "Only documentation changed"}
            )
        assert (
            db._connect.execute(
                "SELECT digest FROM version_files WHERE kind='asset'"
            ).fetchone()[0]
            == digest
        )
        (first.asset.hda_dirpath / first.asset.hda_filename).write_bytes(b"corruption")
        inspect_files(db._connect)
        assert (
            db._connect.execute(
                "SELECT status FROM version_files WHERE kind='asset'"
            ).fetchone()[0]
            == "mismatch"
        )
