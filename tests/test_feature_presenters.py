from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from libs.asset_contracts import HistoryData, LibrarySnapshot, SyncContext
from libs.scene_contracts import SceneRecord
from widgets.asset_details.presenter import AssetDetailsPresenter
from widgets.asset_lifecycle.presenter import AssetCommandPresenter
from widgets.asset_media.presenter import AssetMediaPresenter, MediaRequest
from widgets.detail_view.presenter import DetailPresenter
from widgets.history.presenter import HistoryPresenter
from widgets.library_manager.presenter import LibraryManagerPresenter
from widgets.rename_ihda.presenter import validate_name
from widgets.web_view.presenter import WebPresenter


class View:
    def __init__(self) -> None:
        self.draft = ("", "")
        self.state = (False, False, False)
        self.errors: list[str] = []
        self.saves: list[Any] = []
        self.content: Any = None
        self.zoom = 0.0

    def show_draft(self, note: str, tags: str) -> None:
        self.draft = note, tags

    def show_state(self, note_dirty: bool, tag_dirty: bool, saving: bool) -> None:
        self.state = note_dirty, tag_dirty, saving

    def show_error(self, message: str) -> None:
        self.errors.append(message)

    show_command_error = show_error
    show_media_error = show_error
    show_history_error = show_error
    show_preference_error = show_error
    show_video_settings_error = show_error

    def saved(self, *args: Any) -> None:
        self.saves.append(args)

    def show_content(self, content: Any) -> None:
        self.content = content

    def show_history_dates(self, dates: list[str]) -> None:
        self.content = dates

    def show_zoom(self, factor: float) -> None:
        self.zoom = factor


class DelayedExecutor:
    def __init__(self) -> None:
        self.operation: Callable[[], None] | None = None
        self.finished: Callable[[Exception | None], None] | None = None
        self.accept = True

    def submit(
        self,
        operation: Callable[[], None],
        finished: Callable[[Exception | None], None],
    ) -> bool:
        if not self.accept:
            return False
        self.operation, self.finished = operation, finished
        return True

    def complete(self, error: Exception | None = None) -> None:
        assert self.finished and self.operation
        if error is None:
            self.operation()
        self.finished(error)


class Metadata:
    def __init__(self) -> None:
        self.writes: list[Any] = []

    def set_note(self, asset_id: int, note: str) -> None:
        self.writes.append((asset_id, note))

    def set_tags(self, asset_id: int, tags: Sequence[str]) -> None:
        self.writes.append((asset_id, list(tags)))


def test_note_and_tag_dirty_are_reported_separately() -> None:
    """Each editor has its own save button, so each needs its own indicator.

    One shared flag lit the note indicator whenever tags were edited -- and an
    AI suggestion fills both at once, which is where it showed.
    """
    view, executor, repository = View(), DelayedExecutor(), Metadata()
    presenter = AssetDetailsPresenter(view, executor)
    presenter.change_gateway(repository)
    presenter.select(1, "note", ["tag"])
    assert view.state == (False, False, False)

    presenter.edit("edited note", "#tag")
    assert view.state == (True, False, False)
    presenter.save("note")
    executor.complete()
    assert view.state == (False, False, False)

    presenter.edit("edited note", "#tag #extra")
    assert view.state == (False, True, False)
    presenter.save("tag")
    executor.complete()
    assert view.state == (False, False, False)

    # Both at once -- the AI suggestion path.
    presenter.edit("again", "#tag #extra #more")
    assert view.state == (True, True, False)


@pytest.mark.parametrize("field", ["note", "tag"])
def test_save_keeps_target_and_newer_edits(field: Any) -> None:
    view, executor, repository = View(), DelayedExecutor(), Metadata()
    presenter = AssetDetailsPresenter(view, executor)
    presenter.change_gateway(repository)
    presenter.select(1, "original", ["old"])
    presenter.edit("first edit", "#Water #water #한글")
    presenter.save(field)
    presenter.edit("second edit", "#newer")
    presenter.select(2, "other", [])
    executor.complete()
    assert repository.writes == [
        (1, "first edit" if field == "note" else ["Water", "한글"])
    ]
    assert view.draft == ("other", "")
    assert view.saves[0][0] == 1
    presenter.select(1, "first edit", ["Water", "한글"])
    assert view.draft == ("second edit", "#newer")
    assert view.state == (True, True, False)


def test_failed_save_keeps_draft_and_can_retry() -> None:
    view, executor, repository = View(), DelayedExecutor(), Metadata()
    presenter = AssetDetailsPresenter(view, executor)
    presenter.change_gateway(repository)
    presenter.select(3, "old")
    presenter.edit("unsaved", "")
    presenter.save("note")
    executor.complete(RuntimeError("offline"))
    assert view.errors == ["offline"] and not view.saves
    presenter.select(4)
    presenter.select(3, "old")
    assert view.draft[0] == "unsaved" and view.state == (True, False, False)
    presenter.save("note")
    executor.complete()
    assert view.state == (False, False, False)
    assert repository.writes == [(3, "unsaved")]


def test_library_switch_ignores_old_result_and_executor_busy_is_recoverable() -> None:
    view, executor, old, new = View(), DelayedExecutor(), Metadata(), Metadata()
    presenter = AssetDetailsPresenter(view, executor)
    presenter.change_gateway(old)
    presenter.select(1)
    presenter.edit("old library", "")
    presenter.save("note")
    presenter.change_gateway(new)
    presenter.select(1, "new library")
    executor.complete()
    assert old.writes == [(1, "old library")] and not new.writes
    assert view.draft == ("new library", "") and not view.saves
    presenter.edit("new edit", "")
    executor.accept = False
    presenter.save("note")
    assert view.state == (True, False, False) and view.errors
    executor.accept = True
    presenter.save("note")
    executor.complete()
    assert new.writes == [(1, "new edit")]


def test_deleted_asset_does_not_receive_late_save() -> None:
    view, executor = View(), DelayedExecutor()
    presenter = AssetDetailsPresenter(view, executor)
    presenter.change_gateway(Metadata())
    presenter.select(1)
    presenter.edit("value", "")
    presenter.save("note")
    presenter.forget(1)
    executor.complete()
    assert not view.saves and view.draft == ("", "")


@pytest.mark.parametrize("command", ["register", "rename", "delete", "delete_history"])
def test_commands_publish_only_after_commit(command: str) -> None:
    view = View()
    events: list[str] = []

    class Gateway:
        fail = True

        def operation(self, *args: Any) -> Any:
            events.append("storage")
            if self.fail:
                raise RuntimeError("conflict")
            return "committed"

        register = rename = delete = delete_history = operation

    gateway = Gateway()
    presenter = AssetCommandPresenter(view, gateway)
    arguments = {
        "register": (None, None),
        "rename": ({}, "Water"),
        "delete": (1, Path("Water")),
        "delete_history": (1, 2, []),
    }[command]
    commit = lambda result: events.append(result)  # noqa: E731
    assert not getattr(presenter, command)(*arguments, commit)
    assert events == ["storage"] and view.errors == ["conflict"]
    gateway.fail = False
    assert getattr(presenter, command)(*arguments, commit)
    assert events == ["storage", "storage", "committed"]


@pytest.mark.parametrize("kind", ["video", "thumbnail"])
def test_media_does_not_update_view_on_storage_failure(kind: str) -> None:
    view = View()

    class Gateway:
        def save(self, *args: Any) -> Any:
            raise RuntimeError("unavailable")

        set_video = set_thumbnail = save

    presenter = AssetMediaPresenter(view, Gateway())
    assert not getattr(presenter, kind)(
        MediaRequest(1, "1.0", Path("video"), "v.mp4"), view.saves.append
    )
    assert not view.saves and view.errors == ["unavailable"]


def test_detail_does_not_mutate_record_and_handles_missing_thumbnail() -> None:
    view = View()
    data = SceneRecord(
        sf=1,
        ef=10,
        fps=24,
        node_name="<b>literal</b>",
        record_id=0,
        hda_id=0,
        node_ver="",
    )
    original = data
    presenter = DetailPresenter(view)
    presenter.show(data, record=True)
    assert data == original
    assert view.content.thumbnail is None
    assert "<b>literal</b>" in view.content.text
    presenter.show(HistoryData(hda_id=0, org_hda_name="", version=""), history=True)
    assert view.content.thumbnail is None
    assert "None" in view.content.text


@pytest.mark.parametrize(
    "name,valid",
    [
        ("", False),
        ("12", False),
        ("_abc", False),
        ("1abc", False),
        (".abc", False),
        ("ab", False),
        ("x" * 255, False),
        ("-abc", False),
        ("a/b", False),
        ("한글", False),
        ("old", False),
        ("Water Sim", True),
    ],
)
def test_name_validation(name: str, valid: bool) -> None:
    result = validate_name(name, "old")
    assert result.valid == valid
    if valid:
        assert result.name == "Water_Sim"


def test_history_invalid_range_keeps_previous_filter() -> None:
    view = View()
    presenter = HistoryPresenter(view)
    presenter.filter_dates(True, date(2026, 1, 1), date(2026, 2, 1))
    assert view.content == ["2026-01-01", "2026-02-01"]
    presenter.filter_dates(True, date(2026, 2, 1), date(2026, 1, 1))
    assert view.errors and view.content == ["2026-01-01", "2026-02-01"]
    presenter.filter_dates(False, date(2026, 2, 1), date(2026, 1, 1))
    assert view.content == []


def test_paging_ignores_old_search_result() -> None:
    presenter = LibraryManagerPresenter()
    old = presenter.request(False)
    presenter.invalidate()
    assert presenter.receive(old, 200) is None
    request = presenter.request(False)
    assert "200 assets" in presenter.receive(request, 200)
    more = presenter.request(True)
    assert more.offset == 200
    assert "end of results" in presenter.receive(more, 2)
    presenter.invalidate()
    assert presenter.request(True).offset == 0


def test_web_zoom_applies_host_scale_once() -> None:
    view = View()
    presenter = WebPresenter(view, scale=2.0)
    presenter.reset_zoom()
    assert view.zoom == 2.0
    presenter.zoom(view.zoom, 1.1)
    assert view.zoom == pytest.approx(2.2)
    presenter.zoom(view.zoom, 1.1)
    assert view.zoom == pytest.approx(2.42)
    presenter.zoom(10, 1.1)
    assert view.zoom == 10
    presenter.zoom(0.5, 0.5)
    assert view.zoom == 0.5


def test_presenters_import_no_host_or_storage_implementation() -> None:
    import ast

    for path in Path("widgets").glob("*/presenter.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            assert not any(
                module.split(".")[0] in {"PySide6", "hou", "public", "main", "sqlite3"}
                or module.startswith("libs.database")
                for module in modules
            ), path
        importlib.import_module(".".join(path.with_suffix("").parts))


def test_video_and_preference_validation() -> None:
    from widgets.make_video_info.presenter import VideoInfoPresenter
    from widgets.preference.presenter import PreferencePresenter

    view = View()
    video = VideoInfoPresenter(view)
    assert video.validate(1001, 1001, 23.976)
    assert not video.validate(1010, 1001, 24)
    assert not video.validate(1, 2, float("nan"))
    assert not video.validate(1, 2, 0)
    preference = PreferencePresenter(view, lambda path: path == Path("valid"))
    assert preference.validate("valid")
    assert not preference.validate("")
    assert not preference.validate("missing")


def test_model_actions_follow_installed_state_and_worker_busy() -> None:
    from widgets.ai_models.presenter import LocalModelsPresenter

    presenter = LocalModelsPresenter()
    installed = {"model:latest"}
    state = presenter.actions("model", installed, True, False, True)
    assert state.installed and state.download and state.use and state.remove
    assert not state.download_default
    state = presenter.actions("model", installed, True, True, True)
    assert not any((state.download, state.use, state.remove, state.download_default))
    state = presenter.actions("other", installed, False, False, False)
    assert not state.installed and not state.download and not state.use


def test_same_library_preference_change_preserves_draft() -> None:
    view, executor = View(), DelayedExecutor()
    presenter = AssetDetailsPresenter(view, executor)
    presenter.change_gateway(Metadata())
    presenter.select(1, "saved")
    presenter.edit("draft", "#tag")
    presenter.change_gateway(Metadata(), preserve_drafts=True)
    presenter.select(1, "saved")
    assert view.draft == ("draft", "#tag") and view.state == (True, True, False)


def test_dialog_validation_controls_accepted_signal(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from PySide6 import QtCore, QtWidgets

    import public
    from widgets.make_video_info.make_video_info import MakeVideoInfo
    from widgets.preference.preference import Preference
    from widgets.rename_ihda.rename_ihda import RenameIHDA

    monkeypatch.setattr(
        public.Paths, "json_pref_filepath", tmp_path / "dialog-prefs.json"
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", lambda _: 0)
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *args: 0)
    rename = RenameIHDA()
    video = MakeVideoInfo()
    preference = Preference()
    accepted: list[str] = []
    rename.accepted.connect(lambda: accepted.append("rename"))
    video.accepted.connect(lambda: accepted.append("video"))
    preference.accepted.connect(lambda: accepted.append("preference"))
    rename.lineEdit__input_ihda_name.setText("a/")
    video.sf, video.ef = 100, 1
    preference.lineEdit__data_dirpath.setText("")
    for dialog in (rename, video, preference):
        dialog.buttonBox__confirm.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).click()
    assert not accepted
    rename.lineEdit__input_ihda_name.setText("Water Sim")
    rename.set_old_ihda_name("Water_Sim")
    assert not rename.is_valid_ihda_name
    rename.lineEdit__input_ihda_name.setText("Fire")
    video.ef = 200
    preference.data_dirpath = str(tmp_path)
    for dialog in (rename, video, preference):
        dialog.buttonBox__confirm.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).click()
    assert accepted == ["rename", "video", "preference"]
    for dialog in (rename, video, preference):
        dialog.close()
        dialog.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_local_lifecycle_uses_transactional_repository(tmp_path: Path) -> None:
    from support.names import Names
    from support.personal import payload

    from libs.asset_lifecycle import LocalAssetLifecycle
    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.repository import LibraryConflict
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    database = tmp_path / "library.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    gateway = LocalAssetLifecycle(repository, Names)
    first = gateway.register(payload(tmp_path, "Water"))
    asset_id = first.asset.hda_id
    second = gateway.register(payload(tmp_path, "Water", "1.1"), asset_id)
    with pytest.raises(LibraryConflict, match="recent"):
        gateway.delete_history(asset_id, second.history_id, [])
    gateway.delete_history(asset_id, first.history_id, [])
    assert len(repository.histories(asset_id, owner="tester")) == 1
    renamed = gateway.rename(second.asset, "Fire")
    assert renamed.asset_rows > 0
    assert (renamed.plan.directory / renamed.plan.filename).is_file()
    assert repository.list_assets()[0].hda_name == "Fire"
    gateway.delete(asset_id, renamed.plan.directory)
    assert not repository.list_assets() and renamed.plan.directory.exists()


def test_metadata_empty_tags_and_deleted_asset(tmp_path: Path) -> None:
    from support.personal import payload

    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.repository import LibraryError
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    database = tmp_path / "metadata.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    asset = repository.register_asset(payload(tmp_path, "Water")).asset
    asset_id = asset.hda_id
    repository.set_tags(asset_id, [])
    repository.set_tags(asset_id, ["water"])
    repository.set_tags(asset_id, [])
    assert repository.list_assets()[0].hda_tags == ()
    repository.delete_asset(asset_id, asset.hda_dirpath)
    with pytest.raises(LibraryError):
        repository.set_note(asset_id, "late write")
    with pytest.raises(LibraryError):
        repository.set_tags(asset_id, ["late"])


@pytest.mark.parametrize("change", ["metadata_save", "library_switch", "none"])
def test_reload_discards_snapshot_from_before_write_or_library_switch(
    change: str,
) -> None:
    from types import SimpleNamespace

    from widgets.panel.sync_presenter import LibrarySyncPresenter

    callbacks: list[Any] = []
    applied: list[Any] = []
    context = SimpleNamespace(repository=object(), write_generation=0)

    class Executor:
        def submit(self, operation: Any, completed: Any) -> bool:
            callbacks.append(completed)
            return True

    view = SimpleNamespace(
        sync_allowed=lambda: True,
        sync_context=lambda: SyncContext(
            repository=context.repository, write_generation=context.write_generation
        ),
        read_snapshot=lambda: lambda: LibrarySnapshot(revision=1),
        show_snapshot=applied.append,
        show_sync_error=lambda message: pytest.fail(message),
    )
    presenter = LibrarySyncPresenter(view, Executor())
    presenter.refresh()
    if change == "metadata_save":
        context.write_generation += 1
    elif change == "library_switch":
        context.repository = object()
    callbacks[0](LibrarySnapshot(revision=1), None)
    assert applied == ([LibrarySnapshot(revision=1)] if change == "none" else [])
    assert presenter.pending == (change == "metadata_save")
