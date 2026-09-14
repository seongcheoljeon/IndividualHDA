from __future__ import annotations

from contextlib import closing
from dataclasses import replace
from pathlib import Path
import shutil
import sqlite3
import threading
from typing import Any
import zipfile

import pytest
from PySide6 import QtCore, QtTest, QtWidgets

from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.library_maintenance import inspect_library, plan_paths, apply_paths, Cancelled
from libs.library_backups import (
    create_backup,
    list_backups,
    validate_backup,
    recovery_files,
    cleanup_recovery,
)
from libs.library_explorer import search_assets, history_versions
from libs.version_compare import compare_expanded
from test_integrity_followup import seed


@pytest.fixture
def library(tmp_path: Path) -> tuple[Path, Path]:
    database, assets = tmp_path / "ihda.db", tmp_path / "assets"
    with SQLite3DatabaseAPI(database) as db:
        seed(db, assets / "Old")
        db.insert_hipfile_info(
            1, "scene.hip", assets / "Old", "21", "commercial", "Linux", 1, 100, 24
        )
        db.insert_houdini_node_info(1, "box", "Box", False, False, "/obj/Old")
    return database, assets


def test_health_reports_missing_files_and_incomplete_metadata(
    library: tuple[Path, Path],
) -> None:
    database, assets = library
    assert all(issue.severity == "source" for issue in inspect_library(database))
    (assets / "Old/v1.hda").unlink()
    issues = inspect_library(database)
    assert sum(i.severity == "missing" for i in issues) == 2
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM houdini_node_info")
    assert any(
        i.message == "Incomplete asset metadata" for i in inspect_library(database)
    )


def test_path_repair_preview_backup_and_stale_rejection(
    library: tuple[Path, Path], tmp_path: Path
) -> None:
    database, assets = library
    new = tmp_path / "moved"
    shutil.copytree(assets, new)
    changes = [c for c in plan_paths(database, str(assets), new) if c.exists]
    assert len(changes) >= 9
    backup = apply_paths(database, changes)
    assert backup.is_file()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT dirpath FROM hda_info").fetchone()[0] == str(
            new / "Old"
        )
    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT dirpath FROM hda_info").fetchone()[0] == str(
            assets / "Old"
        )
    with pytest.raises(RuntimeError, match="preview"):
        apply_paths(database, changes)


def test_cross_platform_root_matching_and_missing_destination(
    library: tuple[Path, Path], tmp_path: Path
) -> None:
    database, assets = library
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE hda_info SET dirpath='C:\\OLD\\Old'")
    plan = plan_paths(database, "c:/old", assets)
    current = next(c for c in plan if c.table == "hda_info")
    assert current.target_file == assets / "Old/v2.hda"
    assert current.exists
    with pytest.raises(ValueError):
        apply_paths(database, [replace(current, target_file=tmp_path / "missing")])
    with pytest.raises(ValueError):
        plan_paths(database, "relative", assets)


def test_backup_validation_and_reason(library: tuple[Path, Path]) -> None:
    database, assets = library
    backup = create_backup(database, assets, "Before review")
    entries = list_backups(database.parent)
    assert entries[0].path == backup and entries[0].reason == "Before review"
    assert entries[0].restorable
    assert "verified" in validate_backup(backup)
    with zipfile.ZipFile(backup) as archive:
        assert archive.testzip() is None


def test_incomplete_backup_rejected(library: tuple[Path, Path]) -> None:
    database, assets = library
    (assets / "Old/v1.hda").unlink()
    backup = create_backup(database, assets, "incomplete")
    with pytest.raises(ValueError, match="missing library files"):
        validate_backup(backup)


def test_restore_stages_only_after_validation_and_preserves_original(
    library: tuple[Path, Path],
) -> None:
    from libs.archive_transfer import ArchiveTransfer

    database, assets = library
    backup = create_backup(database, assets, "original")
    original = (assets / "Old/v2.hda").read_text()
    (assets / "Old/v2.hda").write_text("changed")
    stream = ArchiveTransfer(assets, database.parent)
    validate_backup(backup)
    safety = stream.import_ihda_data(backup)
    assert safety.is_file() and stream.stage is not None
    assert (assets / "Old/v2.hda").read_text() == "changed"
    stream.commit_import()
    assert (assets / "Old/v2.hda").read_text() == original


def test_recovery_cleanup_references_and_safety_archive(
    library: tuple[Path, Path],
) -> None:
    database, assets = library
    recovery = assets / "Old" / (".ihda-deleted-" + "a" * 32 + "-old.hda")
    recovery.write_text("saved data")
    entries = recovery_files(database, assets)
    assert len(entries) == 1 and not entries[0].referenced
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE hda_info SET filename=?", (recovery.name,))
    with pytest.raises(RuntimeError, match="referenced"):
        cleanup_recovery(database, assets, entries)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE hda_info SET filename='v2.hda'")
    safety = cleanup_recovery(database, assets, entries)
    assert not recovery.exists()
    with zipfile.ZipFile(safety) as archive:
        assert archive.read("0/" + recovery.name) == b"saved data"
    assert not next(
        e for e in list_backups(database.parent) if e.path == safety
    ).restorable


def test_recovery_changed_preview_and_pending_journal_rejected(
    library: tuple[Path, Path],
) -> None:
    database, assets = library
    recovery = assets / (".ihda-deleted-" + "b" * 32 + "-old")
    recovery.mkdir()
    item = recovery / "a.hda"
    item.write_text("old")
    entries = recovery_files(database, assets)
    item.write_text("changed")
    with pytest.raises(RuntimeError):
        cleanup_recovery(database, assets, entries)
    journal = database.parent / ".ihda-operation-test.json"
    journal.write_text("{}")
    with pytest.raises(RuntimeError, match="journals"):
        cleanup_recovery(database, assets, recovery_files(database, assets))
    assert item.read_text() == "changed"


def test_paged_search_literal_matching_and_cancellation(
    library: tuple[Path, Path],
) -> None:
    database, _ = library
    with SQLite3DatabaseAPI(database) as db:
        for i in range(7):
            db.insert_hda_key(f"Name%_{i}", "sop", "user")
            db.insert_hda_info(i + 2, "1", filename="a.hda", dirpath=Path("/assets"))
    pages = [
        search_assets(database, "user", "Name%_", offset=offset, limit=3)
        for offset in (0, 3, 6)
    ]
    assert [len(page) for page in pages] == [3, 3, 1]
    assert len({row["id"] for page in pages for row in page}) == 7
    assert not search_assets(database, "user", "' OR 1=1 --")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Cancelled):
        search_assets(database, "user", "", cancel=cancel)
    assert len(history_versions(database, 1)) == 3


def test_diff_reports_metadata_parameters_and_node_sections(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "node.parm").write_text("size = 1\n")
    (right / "node.parm").write_text("size = 2\n")
    result = compare_expanded(
        left, right, {"note": "old"}, {"note": "new"}, {"box": "one"}, {"box": "two"}
    )
    assert "note:" in result and "-size = 1" in result and "+size = 2" in result
    assert "PARAMETER INTERFACE" in result


def wait_tasks(app: Any, dialog: Any) -> None:
    for _ in range(500):
        app.processEvents()
        if not dialog.tasks.busy:
            return
        QtTest.QTest.qWait(10)
    raise AssertionError("Worker did not finish")


def test_manager_scan_pages_and_shutdown(app: Any, library: tuple[Path, Path]) -> None:
    from widgets.library_manager.dialog import LibraryManager

    database, assets = library
    dialog = LibraryManager(database, assets, "user", 1)
    assert dialog.tabs.count() == 6
    dialog._run(lambda token: inspect_library(database, token), dialog._health_ready)
    wait_tasks(app, dialog)
    assert dialog.health.rowCount() > 0
    dialog._search()
    wait_tasks(app, dialog)
    assert dialog.explorer.rowCount() == 1
    dialog._versions()
    wait_tasks(app, dialog)
    assert dialog.left.count() == 3
    dialog.shutdown()


def test_debounce_delivers_only_latest_query(app: Any) -> None:
    from libs.debounce import DebouncedText

    owner = QtCore.QObject()
    received = []
    debounce = DebouncedText(received.append, owner, 20)
    for text in ("a", "ab", "abc"):
        debounce.submit(text)
    QtTest.QTest.qWait(60)
    assert received == ["abc"]


def test_manager_close_waits_for_worker_and_emits_finished_once(
    app: Any, library: tuple[Path, Path]
) -> None:
    from widgets.library_manager.dialog import LibraryManager

    database, assets = library
    dialog = LibraryManager(database, assets, "user")
    dialog.show()
    gate = threading.Event()
    completed = []
    finished = []
    dialog.finished.connect(finished.append)
    dialog._run(lambda token: gate.wait(2), completed.append, False)
    dialog.close()
    app.processEvents()
    assert dialog.tasks.busy and not finished
    gate.set()
    wait_tasks(app, dialog)
    assert len(completed) == 1 and len(finished) == 1
    assert not dialog.isVisible()


def test_manager_superseded_search_cannot_publish_stale_rows(
    app: Any, library: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from widgets.library_manager.dialog import LibraryManager
    import widgets.library_manager.dialog as module

    database, assets = library
    dialog = LibraryManager(database, assets, "user")
    gate = threading.Event()
    entered = threading.Event()
    original = module.search_assets

    def slow(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        entered.set()
        gate.wait(2)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "search_assets", slow)
    dialog._search()
    assert entered.wait(2)
    dialog.search.setText("absent")
    gate.set()
    wait_tasks(app, dialog)
    QtTest.QTest.qWait(300)
    wait_tasks(app, dialog)
    assert dialog.explorer.rowCount() == 0
    dialog.shutdown()


def test_malformed_backup_is_not_offered_as_restorable(
    library: tuple[Path, Path],
) -> None:
    database, _ = library
    backup = database.parent / "backup" / "malformed.zip"
    backup.parent.mkdir()
    with zipfile.ZipFile(backup, "w") as archive:
        archive.write(database, "ihda.db")
        archive.writestr("ihda-manifest.json", "invalid JSON")
    entry = list_backups(database.parent)[0]
    assert not entry.restorable and entry.reason == "Unreadable archive"
