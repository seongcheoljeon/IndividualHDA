"""Committed-only rename/Trash updates and existing journal rollback."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support.personal import payload
from test_registration_workflow import Capture, setup

from libs.repository import LibraryError
from widgets.asset_lifecycle.presenter import AssetCommandPresenter


@pytest.fixture
def mutation_panel(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Any]:
    from dataclasses import replace

    from test_library_sync import wait_sync

    import public
    from main import IndividualHDA
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    preference = Preference()
    preference.data_dirpath = str(tmp_path)
    preference._Preference__pref_settings.save_cfg_dict_to_file()
    preference.close()
    repository, request, service = setup(tmp_path)
    first = service.register(request, Capture())
    service.register(
        replace(
            request,
            version="1.1",
            hda_filename="Water_1.1.hda",
            thumb_filename="Water_1.1.jpg",
        ),
        Capture(),
        first.asset.hda_id,
    )
    repository.register_asset(payload(tmp_path, "Fire"))
    panel = IndividualHDA()
    wait_sync(app, panel)
    try:
        yield panel
    finally:
        panel.close()
        app.processEvents()


def test_mixed_asset_trash_keeps_failed_asset_history_and_selection(
    mutation_panel: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from model.ihda_list_model import ListModel

    panel = mutation_panel
    original = panel.session.repository.delete_asset
    assets = {row.hda_name: row for row in panel.models.assets.rows}
    water_id = assets["Water"].hda_id
    panel.selection._select_model_item_by_hda_id(water_id)
    errors: list[str] = []
    monkeypatch.setattr(panel.management, "show_command_error", errors.append)

    def fail_water(asset_id: int, directory: Path) -> None:
        if asset_id == water_id:
            raise LibraryError("injected delete failure")
        original(asset_id, directory)

    monkeypatch.setattr(panel.session.repository, "delete_asset", fail_water)
    indexes = [panel.models.list_proxy_model.index(row, 0) for row in range(2)]
    assert {index.data(ListModel.data_role).hda_name for index in indexes} == {
        "Water",
        "Fire",
    }
    panel.management._remove_hda_item(indexes)
    assert [row.hda_name for row in panel.models.assets.rows] == ["Water"]
    assert panel.models.history_model.rowCount() == 2
    assert panel.selection.state.asset.id == water_id
    assert panel.comboBox__hist_ihda_node.findData(water_id) >= 0
    assert errors == ["injected delete failure"]
    assert assets["Fire"].hda_dirpath.exists()  # Trash retains files


def test_history_failure_and_current_version_protection_preserve_view(
    mutation_panel: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = mutation_panel
    water = next(row for row in panel.models.assets.rows if row.hda_name == "Water")
    history = panel.session.repository.histories(water.hda_id, owner="tester")
    old = next(row for row in history if row.version == "1.0")
    current = next(row for row in history if row.version == "1.1")
    panel.selection.state.select_history(old, 0)
    count = panel.models.history_model.rowCount()
    errors: list[str] = []
    monkeypatch.setattr(panel.management, "show_command_error", errors.append)
    original = panel.session.repository.delete_history

    def fail(*args: Any) -> None:
        raise LibraryError("injected history failure")

    monkeypatch.setattr(panel.session.repository, "delete_history", fail)
    assert not panel.management._delete_each_hist_ihda_item(old)
    assert panel.selection.state.history.hist_id == old.hist_id
    assert panel.models.history_model.rowCount() == count
    monkeypatch.setattr(panel.session.repository, "delete_history", original)
    assert not panel.management._delete_each_hist_ihda_item(current)
    assert panel.models.history_model.rowCount() == count
    assert panel.management._delete_each_hist_ihda_item(old)
    assert panel.models.history_model.rowCount() == count - 1
    assert panel.selection.state.history.hist_id is None
    assert (old.ihda_dirpath / old.ihda_filename).is_file()
    assert panel.comboBox__hist_ihda_node.findData(water.hda_id) >= 0


def test_rename_failure_rolls_back_journal_and_does_not_change_view(
    mutation_panel: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs.sqlite3_db_api import SQLite3DatabaseAPI

    panel = mutation_panel
    water = next(row for row in panel.models.assets.rows if row.hda_name == "Water")
    old_directory = water.hda_dirpath
    panel.selection._select_model_item_by_hda_id(water.hda_id)
    monkeypatch.setattr(panel.management, "show_command_error", lambda message: None)
    with monkeypatch.context() as patch:
        patch.setattr(
            SQLite3DatabaseAPI,
            "update_hda_name_to_history",
            lambda *args, **kwargs: None,
        )
        assert not panel.management._change_ihda_name("Stream")
    assert water.hda_dirpath.exists()
    assert not water.hda_dirpath.with_name("Stream").exists()
    assert panel.selection.state.asset.name == "Water"
    assert panel.management._change_ihda_name("Stream")
    assert panel.selection.state.asset.name == "Stream"
    assert panel.selection.state.asset.filepath.is_file()
    assert not old_directory.exists()


@pytest.mark.parametrize("name", ["../invalid", "box", "box1"])
def test_service_rejects_invalid_rename_before_files_move(
    mutation_panel: Any, name: str
) -> None:
    panel = mutation_panel
    asset = next(row for row in panel.models.assets.rows if row.hda_name == "Water")
    gateway = panel._services.lifecycle(panel.session.repository, panel._services.names)
    with pytest.raises(ValueError):
        gateway.rename(asset, name)
    assert (asset.hda_dirpath / asset.hda_filename).is_file()


@pytest.mark.parametrize(
    "operation,args",
    [
        ("rename", ({}, "Stream")),
        ("delete", (1, Path("asset"))),
        ("delete_history", (1, 2, [])),
    ],
)
def test_display_failure_reports_commit_without_retry(
    operation: str, args: tuple[Any, ...]
) -> None:
    stored: list[bool] = []
    failures: list[Exception] = []

    def commit(*args: Any) -> None:
        stored.append(True)

    def broken_display(result: Any) -> None:
        raise RuntimeError("view failure")

    presenter = AssetCommandPresenter(
        SimpleNamespace(show_command_error=lambda message: pytest.fail(message)),
        SimpleNamespace(rename=commit, delete=commit, delete_history=commit),
        failures.append,
    )
    assert getattr(presenter, operation)(*args, broken_display)
    assert stored == [True] and str(failures[0]) == "view failure"


def test_bulk_history_trash_retains_notes_current_version_and_files(
    mutation_panel: Any,
) -> None:
    panel = mutation_panel
    water = next(row for row in panel.models.assets.rows if row.hda_name == "Water")
    asset_id = water.hda_id
    panel.session.repository.set_note(asset_id, "retain this note")
    notes = panel.session.repository.note_history(asset_id)
    histories = panel.models.history_model.get_hist_data_by_hkey_id_from_model(
        hkey_id=asset_id
    )
    paths = [row.ihda_dirpath / row.ihda_filename for row in histories]
    panel.management._trash_history_rows(
        histories + histories
    )  # duplicate selections are harmless
    remaining = panel.session.repository.histories(asset_id, owner="tester")
    assert [row.version for row in remaining] == ["1.1"]
    assert panel.session.repository.note_history(asset_id) == notes
    assert all(path.is_file() for path in paths)


@pytest.mark.parametrize("history", [False, True])
def test_trash_audit_failure_rolls_back_database_and_preserves_ui(
    mutation_panel: Any, monkeypatch: pytest.MonkeyPatch, history: bool
) -> None:
    from libs.database.lifecycle import PersonalLifecycle

    panel = mutation_panel
    water = next(row for row in panel.models.assets.rows if row.hda_name == "Water")
    old = next(
        row
        for row in panel.session.repository.histories(water.hda_id, owner="tester")
        if row.version == "1.0"
    )
    count = panel.models.history_model.rowCount()

    def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(PersonalLifecycle, "event", fail)
    monkeypatch.setattr(panel.management, "show_command_error", lambda message: None)
    if history:
        assert not panel.management._delete_each_hist_ihda_item(old)
    else:
        assert not panel.management._delete_ihda_item(
            water.hda_id, water.hda_cate, water.hda_name, water.hda_dirpath
        )
    assert panel.models.history_model.rowCount() == count
    assert len(panel.session.repository.list_assets()) == 2
    assert len(panel.session.repository.histories(water.hda_id, owner="tester")) == 2
    assert (old.ihda_dirpath / old.ihda_filename).is_file()


def test_rename_overlay_closes_on_exception() -> None:
    from widgets.panel.asset_management import PanelAssetManagement

    events: list[str] = []

    def fail(**kwargs: Any) -> bool:
        raise RuntimeError("unexpected error")

    owner = SimpleNamespace(
        bindings=SimpleNamespace(
            rename_dialog=SimpleNamespace(
                is_valid_ihda_name=True, final_ihda_name="Stream"
            ),
            presentation=SimpleNamespace(
                dragdrop_overlay_show=lambda **kwargs: events.append("show"),
                dragdrop_overlay_close=lambda: events.append("close"),
            ),
        ),
        _change_ihda_name=fail,
    )
    with pytest.raises(RuntimeError):
        PanelAssetManagement._slot_hda_name_changed(owner)
    assert events == ["show", "close"]


def test_history_trash_skips_activity_rows(
    mutation_panel: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs.asset_contracts import HistoryData

    panel = mutation_panel
    water = next(row for row in panel.models.assets.rows if row.hda_name == "Water")
    deleted: list[int] = []
    original = panel.session.repository.delete_history

    def record(asset_id: int, history_id: int, *args: Any, **kwargs: Any) -> Any:
        deleted.append(history_id)
        return original(asset_id, history_id, *args, **kwargs)

    monkeypatch.setattr(panel.session.repository, "delete_history", record)
    histories = panel.models.history_model.get_hist_data_by_hkey_id_from_model(
        hkey_id=water.hda_id
    )
    activity = HistoryData(
        kind="video",
        hda_id=water.hda_id,
        org_hda_name="Water",
        version="",
        comment="VIDEO (INSERT)",
        reg_time="2026-09-17 10:00:00",
    )
    panel.management._trash_history_rows([activity, *histories])
    assert 0 not in deleted and deleted
    remaining = panel.session.repository.histories(water.hda_id, owner="tester")
    assert [row.version for row in remaining] == ["1.1"]
