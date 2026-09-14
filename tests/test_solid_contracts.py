from __future__ import annotations
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterator
import pytest
from PySide6 import QtCore
from libs.asset_store import AssetStore
from libs.asset_rename import build_rename_plan, rename_asset
from libs.contracts import SilentRows
from libs.library_reader import LibraryReader
from libs.database.rename_repository import SQLiteRenameRepository
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.task_controller import TaskController
from libs.process_job import ProcessJob
from libs.background_job import BackgroundJob


class Names:
    @staticmethod
    def make_hda_filename(name: str, version: str, with_suffix: bool = True) -> str:
        return f"{name}-{version}.hda"

    @staticmethod
    def make_thumbnail_filename(name: str, version: str) -> str:
        return f"{name}.png"

    @staticmethod
    def make_thumbnail_dirpath(directory: Path) -> Path:
        return directory / "thumbnail"

    @staticmethod
    def make_video_filename(name: str, version: str) -> str:
        return f"{name}.mp4"

    @staticmethod
    def make_video_dirpath(directory: Path) -> Path:
        return directory / "video"


def test_domain_imports_without_qt_or_houdini() -> None:
    code = """
import builtins
original = builtins.__import__
def restricted(name, *args, **kwargs):
    if name.split('.')[0] in ('hou', 'PySide6'):
        raise AssertionError('Domain imported host: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = restricted
from libs.asset_store import AssetStore
from libs.asset_rename import build_rename_plan
from libs.asset_commands import delete_asset
from libs.library_reader import LibraryReader
store = AssetStore()
store.insert({'hda_id': 1, 'hda_name': 'A'})
assert store.id_rows[1] == 0
"""
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )


def test_store_observer_sees_valid_before_and_after_states() -> None:
    events = []

    class Observer(SilentRows):
        def begin_insert(self, row: int) -> None:
            events.append(("before", row, len(store.rows)))

        def end_insert(self) -> None:
            events.append(("after", len(store.rows), dict(store.id_rows)))

    store = AssetStore(Observer())
    store.insert({"hda_id": 7, "hda_name": "Water"})
    assert events == [("before", 0, 0), ("after", 1, {7: 0})]
    with pytest.raises(IndexError):
        store.update(-1, {"hda_name": "wrong"})
    assert store.rows[0]["hda_name"] == "Water"


def test_reader_closes_substitute_repository_after_failure(tmp_path: Path) -> None:
    path = tmp_path / "db"
    path.touch()

    class ReadOnlyRepository:
        closed = False

        def get_hda_data(self, **kwargs: Any) -> list[Any]:
            raise ValueError("read failed")

        def close(self) -> None:
            self.closed = True

    repository = ReadOnlyRepository()
    reader = LibraryReader(lambda path: repository)
    with pytest.raises(ValueError, match="read failed"):
        reader.assets(path, "user")
    assert repository.closed


@pytest.mark.parametrize("fail_history", [False, True])
def test_rename_sqlite_adapter_preserves_atomicity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_history: bool
) -> None:
    old = tmp_path / "Old"
    old.mkdir()
    (old / "old.hda").write_text("asset")
    (old / "thumbnail").mkdir()
    (old / "thumbnail" / "old.png").write_text("thumbnail")
    data = {
        "hda_id": 1,
        "hda_name": "Old",
        "hda_version": "1.0",
        "hda_dirpath": old,
        "hda_filename": "old.hda",
        "node_old_path": "/obj/Old",
        "thumbnail_dirpath": old / "thumbnail",
        "thumbnail_filename": "old.png",
    }
    plan = build_rename_plan(data, "New", Names(), rename_video=False)
    assert old.exists() and not plan.directory.exists()  # planning has no mutations
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        db.insert_users("user", "user@example.com")
        db.insert_hda_category("sop", "user")
        db.insert_hda_key("Old", "sop", "user")
        db.insert_hda_info(1, "1.0", filename="old.hda", dirpath=old)
        db.insert_thumbnail_info(1, old / "thumbnail", "old.png", "1.0")
        adapter = SQLiteRenameRepository(db)
        if fail_history:
            monkeypatch.setattr(db, "update_hda_name_to_history", lambda **kwargs: None)
            with pytest.raises(RuntimeError):
                rename_asset(adapter, plan)
            assert db.get_count_hda_key(name="Old") == 1
            assert (old / "old.hda").is_file()
            assert (old / "thumbnail" / "old.png").is_file()
            assert not plan.directory.exists()
        else:
            renamed, _ = rename_asset(adapter, plan)
            assert renamed > 0
            assert db.get_count_hda_key(name="New") == 1
            assert (plan.directory / plan.filename).is_file()
            assert (plan.thumbnail_directory / plan.thumbnail_filename).is_file()
            assert not old.exists()


def test_process_owner_handles_substitute_completion_once(app: Any) -> None:
    class ImmediateProcess(ProcessJob):
        def start(self) -> None:
            self.finished.emit(0, "done")
            self.finished.emit(0, "duplicate")

    controller = TaskController(process_factory=ImmediateProcess)
    results = []
    assert controller.start_process(["unused"], lambda code, text: results.append(text))
    assert results == ["done"]
    assert not controller.busy
    controller.deleteLater()


def test_file_start_failure_releases_owner(app: Any) -> None:
    class FailingJob(BackgroundJob):
        def start(self) -> None:
            raise RuntimeError("cannot start")

    controller = TaskController(file_factory=FailingJob)
    with pytest.raises(RuntimeError, match="cannot start"):
        controller.start(lambda: None, lambda value: None)
    assert not controller.busy
    controller.deleteLater()


@pytest.mark.parametrize("name", ["list", "table", "history"])
def test_qt_model_empty_population_and_unsupported_drop(app: Any, name: str) -> None:
    from importlib import import_module

    model_type = getattr(
        import_module(f"model.ihda_{name}_model"),
        {"list": "ListModel", "table": "TableModel", "history": "HistoryModel"}[name],
    )
    model = model_type()
    model.add_items()
    model.append_item({"hda_id": 1, "hda_name": "Asset"})
    assert model.rowCount() == 1
    assert not model.dropMimeData(
        QtCore.QMimeData(), QtCore.Qt.DropAction.CopyAction, 0, 0, QtCore.QModelIndex()
    )
    assert model.rowCount() == 1
