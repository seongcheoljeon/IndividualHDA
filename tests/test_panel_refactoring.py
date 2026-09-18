"""Selection identities and asynchronous panel lifecycle regressions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_team_workspace import Executor, workspace

from libs.asset_contracts import AssetData, HistoryData, LibrarySnapshot, SyncContext
from libs.domain import SelectionState
from libs.record_codec import decode_record
from widgets.panel.library_session import PersonalPanelSession, TeamPanelSession
from widgets.panel.selection_presenter import PanelSelectionPresenter
from widgets.panel.sync_presenter import LibrarySyncPresenter


def test_reload_rebuilds_all_selection_fields_and_preserves_historical_version() -> (
    None
):
    state = SelectionState()
    state.select_asset(
        decode_record(AssetData, {"hda_id": 7, "hda_name": "Old", "hda_version": "1"}),
        4,
    )
    state.select_history(
        decode_record(
            HistoryData,
            {"org_hda_name": "", "hda_id": 7, "hist_id": 42, "version": "1"},
        ),
        8,
    )
    displayed: list[str] = []
    view = SimpleNamespace(
        show_asset_selection=lambda: displayed.append("asset"),
        show_history_selection=lambda: displayed.append("history"),
        refresh_selection_dependents=lambda: displayed.append("dependents"),
    )
    presenter = PanelSelectionPresenter(state, view)
    presenter.select_asset(state.asset.data, state.asset.row, None)
    presenter.select_history(state.history.data, state.history.row, None)
    assert displayed == ["asset", "dependents", "history", "dependents"]
    presenter.restore(
        [
            decode_record(AssetData, {"hda_name": "", "hda_id": 9}),
            decode_record(
                AssetData,
                {
                    "hda_id": 7,
                    "hda_name": "Renamed",
                    "hda_cate": "sop",
                    "hda_version": "2",
                    "hda_dirpath": Path("/assets"),
                    "hda_filename": "renamed.hda",
                },
            ),
        ],
        [
            decode_record(
                HistoryData,
                {
                    "hda_id": 7,
                    "hist_id": 42,
                    "version": "1",
                    "org_hda_name": "Original",
                    "node_category": "sop",
                    "ihda_dirpath": Path("/history"),
                    "ihda_filename": "original.hda",
                },
            )
        ],
    )
    assert (state.asset.id, state.asset.row, state.asset.name, state.asset.version) == (
        7,
        1,
        "Renamed",
        "2",
    )
    assert state.asset.filepath == Path("/assets/renamed.hda")
    assert (state.history.hist_id, state.history.row, state.history.version) == (
        42,
        0,
        "1",
    )
    assert state.history.filepath == Path("/history/original.hda")
    presenter.restore([], [])
    assert state.asset.data is state.asset.filepath is state.asset.id is None
    assert state.history.data is state.history.hist_id is None


@pytest.mark.parametrize("change", ["selection", "roundtrip", "clear", "close"])
def test_team_history_discards_stale_response(tmp_path: Path, change: str) -> None:
    presenter, view, backend, executor, _ = workspace(tmp_path)
    shown: list[Any] = []
    view.show_history = lambda items, events=(): shown.append(items)
    backend.histories = lambda identifier: [{"document": {"id": identifier}}]
    assert presenter.history()
    if change == "close":
        presenter.close()
    else:
        presenter.select(None if change == "clear" else 2)
        if change == "roundtrip":
            presenter.select(1)
    executor.complete()
    assert shown == []
    if change != "close":
        presenter.select(1)
        assert presenter.history()
        executor.complete()
        assert shown == [[{"document": {"id": 1}}]]


def test_team_history_busy_and_failure_can_retry(tmp_path: Path) -> None:
    presenter, view, backend, executor, _ = workspace(tmp_path)
    shown: list[Any] = []
    view.show_history = lambda items, events=(): shown.append(items)

    def fail(identifier: int) -> Any:
        raise RuntimeError("offline")

    backend.histories = fail
    assert presenter.history()
    assert not presenter.history()
    executor.complete()
    assert "offline" in view.messages
    backend.histories = lambda identifier: []
    assert presenter.history()
    executor.complete()
    assert shown == [[]]


def test_sync_waits_for_idle_and_retries_snapshot_invalidated_by_save() -> None:
    executor = Executor()
    applied: list[Any] = []
    context = SimpleNamespace(repository=object(), generation=0, allowed=True)
    view = SimpleNamespace(
        sync_allowed=lambda: context.allowed,
        sync_context=lambda: SyncContext(
            repository=context.repository, write_generation=context.generation
        ),
        read_snapshot=lambda: lambda: LibrarySnapshot(revision=2),
        show_snapshot=applied.append,
        show_sync_error=lambda message: pytest.fail(message),
    )
    presenter = LibrarySyncPresenter(view, executor)
    context.allowed = False
    presenter.refresh()
    assert presenter.pending and executor.queued is None
    context.allowed = True
    presenter.idle()
    context.generation += 1
    context.allowed = False
    executor.complete()
    assert presenter.pending and not applied
    presenter.idle()
    assert executor.queued is None
    context.allowed = True
    presenter.idle()
    executor.complete()
    assert applied == [LibrarySnapshot(revision=2)] and not presenter.pending
    presenter.refresh()
    presenter.close()
    executor.complete()
    assert applied == [LibrarySnapshot(revision=2)]


def test_sync_rejected_submission_is_retried_after_idle() -> None:
    executor = SimpleNamespace(accept=False, callback=None)

    def submit(operation: Any, finished: Any) -> bool:
        if not executor.accept:
            return False
        executor.callback = finished
        return True

    shown: list[Any] = []
    identity = object()
    view = SimpleNamespace(
        sync_allowed=lambda: True,
        sync_context=lambda: SyncContext(repository=identity, write_generation=0),
        read_snapshot=lambda: lambda: LibrarySnapshot(revision=3),
        show_snapshot=shown.append,
        show_sync_error=lambda message: pytest.fail(message),
    )
    presenter = LibrarySyncPresenter(view, SimpleNamespace(submit=submit))
    presenter.refresh()
    assert presenter.pending
    executor.accept = True
    presenter.idle()
    executor.callback(LibrarySnapshot(revision=3), None)
    assert shown == [LibrarySnapshot(revision=3)] and presenter.known_revision == 3


def test_library_capabilities_and_dispatch_are_explicit() -> None:
    calls: list[Any] = []
    local = SimpleNamespace(
        _repository=object(),
        _details=SimpleNamespace(
            presenter=SimpleNamespace(
                select=lambda *args: calls.append(args), save=calls.append
            )
        ),
        _library_sync_presenter=SimpleNamespace(
            refresh=lambda: calls.append("local refresh")
        ),
    )
    from widgets.panel.state import PanelSessionState

    personal = PersonalPanelSession(
        PanelSessionState(repository=local._repository),
        local._details.presenter,
        local._library_sync_presenter.refresh,
    )
    personal.select(
        3, AssetData(hda_note="draft", hda_tags=("water",), hda_id=0, hda_name="")
    )
    personal.save("note")
    personal.refresh()
    assert calls == [(3, "draft", ("water",)), "note", "local refresh"]
    assert (
        personal.capabilities.local_files
        and personal.capabilities.confirm_metadata_save
    )
    remote = SimpleNamespace(
        writable=False,
        project={"role": "viewer"},
        select=calls.append,
        refresh=lambda: calls.append("team refresh"),
        request_history=lambda: calls.append("history"),
    )
    team = TeamPanelSession(remote)
    team.select(3, None)
    team.refresh()
    team.history()
    assert calls[-3:] == [3, "team refresh", "history"]
    assert not team.capabilities.edit_metadata and not team.capabilities.manage_members
    remote.project["role"] = "owner"
    remote.writable = True
    assert team.capabilities.edit_metadata and team.capabilities.manage_members


def test_ai_result_cannot_cross_a_library_session(app: Any) -> None:
    from PySide6 import QtWidgets

    from libs.ai_features import Description
    from widgets.panel.ai_actions import PanelAIActions
    from widgets.panel.state import PanelSessionState

    state = SelectionState()
    state.select_asset(decode_record(AssetData, {"hda_id": 7, "hda_name": "Current"}))
    session = PanelSessionState(user="tester")
    note, tags = QtWidgets.QTextEdit(), QtWidgets.QTextEdit()
    note.setPlainText("Current draft")
    feature = PanelAIActions()
    feature.target_id = 7
    feature._target_repository = session.repository
    feature._target_generation = session.generation
    feature.bindings = SimpleNamespace(
        selection=SimpleNamespace(state=state),
        session=session,
        ui=SimpleNamespace(textEdit__note=note, textEdit__tag=tags),
    )
    # IDs can be identical across two libraries, even when both are disconnected.
    session.replace(None, None)
    feature.describe_done(Description(summary="Stale answer", tags=["stale"]))
    assert note.toPlainText() == "Current draft"
    assert tags.toPlainText() == ""


def test_registration_capture_accepts_a_host_adapter(tmp_path: Path) -> None:
    from libs.repository import LibraryError
    from widgets.asset_lifecycle.capture import HoudiniRegistrationCapture

    calls: list[dict[str, Any]] = []

    class Host:
        def create_hda_file(self, **values: Any) -> bool:
            calls.append(values)
            return False

        def create_thumbnail(self, output_filepath: Path) -> bool:
            output_filepath.write_bytes(b"partial")
            return False

    capture = HoudiniRegistrationCapture(object(), "1.2", Host())
    with pytest.raises(LibraryError, match="capture failed"):
        capture.asset(tmp_path / "Asset.hda")
    assert calls[0]["hda_version"] == "1.2"
    thumbnail = tmp_path / "preview.jpg"
    capture.thumbnail(thumbnail)
    assert not thumbnail.exists()
