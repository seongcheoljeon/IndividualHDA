"""Operational settings reach real consumers without mutating live sessions."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from libs.resource_policy import MediaPolicy, ThumbnailPolicy
from libs.runtime_settings import RuntimeSettings
from libs.settings_store import load_json, save_json


def test_runtime_invalid_fields_are_isolated_and_batch_pair_recovers(
    caplog: Any,
) -> None:
    settings = RuntimeSettings.from_mapping(
        {
            "search_delay_ms": True,
            "team_timeout_seconds": float("inf"),
            "explorer_page_size": 1001,
            "sync_interval_seconds": 19,
            "maximum_node_batch": 3,
            "warn_node_batch": 7,
            "future_setting": 99,
        }
    )
    assert settings == replace(RuntimeSettings(), sync_interval_seconds=19)
    assert "inconsistent node batch" in caplog.text
    for bad in [[], "bad", 7]:
        assert RuntimeSettings.from_mapping(bad) == RuntimeSettings()
    with pytest.raises(ValueError, match="must not exceed"):
        RuntimeSettings(maximum_node_batch=2)


def test_preference_save_cancel_reset_and_failure(
    app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs.paths import Paths
    from widgets.preference import preference_ui_settings
    from widgets.preference.preference import Preference

    config = tmp_path / "preference.json"
    monkeypatch.setattr(Paths, "json_pref_filepath", config)
    save_json(config, {"unrelated": "keep", "runtime": {"future_setting": 99}})
    dialog = Preference()
    dialog.data_dirpath = str(tmp_path)
    errors: list[str] = []
    monkeypatch.setattr(dialog, "show_preference_error", errors.append)
    desired = RuntimeSettings(search_delay_ms=333, team_page_size=17)
    dialog.runtime_settings = desired
    dialog.accept()
    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    raw = load_json(config)
    assert raw["runtime"]["future_setting"] == 99
    assert raw["unrelated"] == "keep"
    assert RuntimeSettings.from_mapping(raw["runtime"]) == desired
    dialog.runtime_settings = replace(desired, search_delay_ms=555)
    dialog.reject()
    assert dialog.runtime_settings == desired
    assert load_json(config) == raw
    dialog.findChild(QtWidgets.QPushButton, "pushButton__reset_runtime").click()
    assert dialog.runtime_settings == RuntimeSettings()
    assert dialog.data_dirpath == tmp_path
    # Invalid relationship is caught before any save or acceptance.
    dialog.runtime_group.inputs["maximum_node_batch"].setValue(1)
    dialog.accept()
    assert "must not exceed" in errors[-1]
    assert load_json(config) == raw
    dialog.runtime_settings = desired
    before = config.read_bytes()
    monkeypatch.setattr(
        preference_ui_settings, "save_json", Mock(side_effect=OSError("disk full"))
    )
    dialog.accept()
    assert "disk full" in errors[-1]
    assert config.read_bytes() == before
    dialog.reject()


def test_saved_policies_are_snapshots_and_explicit_services_win(
    app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs.browser_search import SearchPolicy
    from libs.paths import Paths
    from main import IndividualHDA
    from widgets.panel.policy import PanelPolicy
    from widgets.panel.services import PanelServices
    from widgets.web_view.web_view import WebView

    config = tmp_path / "preference.json"
    monkeypatch.setattr(Paths, "json_pref_filepath", config)
    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    desired = RuntimeSettings(
        search_delay_ms=321,
        sync_interval_seconds=23,
        maximum_node_batch=8,
        warn_node_batch=4,
    )
    save_json(config, {"runtime": asdict(desired)})
    panel = IndividualHDA()
    assert panel._services.runtime == desired
    assert panel._services.policy.search.delay_ms == 321
    assert panel._browser.debounce.timer.interval() == 321
    assert panel._history_search_debounce.timer.interval() == 321
    assert panel._library_sync.timer.interval() == 23000
    assert panel._MAX_NUM_OF_NODE_REGIST == 8
    save_json(config, {"runtime": asdict(RuntimeSettings())})
    assert panel._library_sync.timer.interval() == 23000
    panel.close()
    explicit = PanelServices(
        policy=PanelPolicy(sync_interval_ms=700, search=SearchPolicy(delay_ms=41))
    )
    panel = IndividualHDA(services=explicit)
    assert panel._services is explicit
    assert panel._library_sync.timer.interval() == 700
    panel.close()
    reopened = IndividualHDA()
    assert reopened._library_sync.timer.interval() == 10000
    reopened.close()


def test_explorer_custom_page_updates_queries_offsets_status_and_label(
    app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from threading import Event

    from widgets.library_manager import dialog as module

    calls: list[tuple[int, int]] = []

    def search(*args: Any, limit: int, cancel: Any) -> list[dict[str, Any]]:
        offset = args[4]
        calls.append((offset, limit))
        return [
            {"id": i, "name": str(i), "category": "sop", "version": "1"}
            for i in range(offset, min(offset + limit, 5))
        ]

    monkeypatch.setattr(module, "search_assets", search)
    dialog = module.LibraryManager(
        tmp_path / "unused.db",
        tmp_path,
        "tester",
        runtime=RuntimeSettings(explorer_page_size=3, explorer_delay_ms=477),
    )
    monkeypatch.setattr(
        dialog, "_run", lambda operation, ready: ready(operation(Event()))
    )
    assert dialog.search_timer.interval() == 477
    assert any(
        button.text() == "Load next 3"
        for button in dialog.findChildren(QtWidgets.QPushButton)
    )
    dialog._search()
    assert "load next page" in dialog.status.text()
    dialog._search(more=True)
    assert calls == [(0, 3), (3, 3)]
    assert dialog.explorer.rowCount() == 5
    assert "end of results" in dialog.status.text()
    dialog.close()


def test_team_page_size_limits_each_request_without_truncating_browser() -> None:
    from libs.team.contracts import Page
    from libs.team.panel_catalog import PanelCatalog

    calls: list[tuple[int, int]] = []

    def page(query: str, offset: int, limit: int) -> Page:
        calls.append((offset, limit))
        return Page(
            [{"id": i} for i in range(offset, min(offset + limit, 7))],
            7,
            offset,
            limit,
            1,
        )

    catalog = PanelCatalog(SimpleNamespace(list_assets=page), page_size=3)
    assert [row["id"] for row in catalog.list_assets().items] == list(range(7))
    assert calls == [(0, 3), (3, 3), (6, 3)]
    with pytest.raises(ValueError):
        PanelCatalog(SimpleNamespace(), page_size=201)


def test_custom_media_timeout_and_thumbnail_decode_reach_workers(
    app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs import ffmpeg_api
    from libs.thumbnail_cache import ThumbnailCache

    run = Mock(return_value=SimpleNamespace(stdout='{"streams": []}'))
    monkeypatch.setattr(ffmpeg_api.subprocess, "run", run)
    monkeypatch.setattr(ffmpeg_api.FFmpegAPI, "executable", lambda *args: "ffprobe")
    assert ffmpeg_api.FFmpegAPI.video_info(
        video_filepath=tmp_path / "video.mp4", policy=MediaPolicy(7)
    ) == {"streams": []}
    assert run.call_args.kwargs["timeout"] == 7
    path = tmp_path / "large.png"
    image = QtGui.QImage(120, 80, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtCore.Qt.GlobalColor.red)
    assert image.save(str(path))
    cache = ThumbnailCache(
        QtGui.QPixmap(2, 2),
        policy=ThumbnailPolicy(capacity=1, decode_edge=24, workers=1, pending=1),
    )
    cache.set_path(1, path)
    cache.get(1)
    for _ in range(200):
        app.processEvents()
        if cache.decoded_count:
            break
        QtTest.QTest.qWait(5)
    pixmap = cache.get(1)
    assert pixmap.width() == 24
    assert pixmap.height() == 16
    cache.shutdown()


def test_team_node_batch_uses_policy_and_cancellation(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from widgets.panel.policy import PanelPolicy
    from widgets.panel.services import PanelServices
    from widgets.team_library.actions import MainAssetActions

    window = QtWidgets.QWidget()
    window._services = PanelServices(
        policy=PanelPolicy(maximum_node_batch=3, warn_node_batch=1)
    )
    errors: list[str] = []
    library = SimpleNamespace(
        bindings=SimpleNamespace(parent=window, policy=window._services.policy),
        show_error=errors.append,
    )
    actions = MainAssetActions(library)
    assert actions._allow_batch(1, "Register")
    assert not actions._allow_batch(4, "Register")
    assert "3 nodes" in errors[-1]
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *args: QtWidgets.QMessageBox.StandardButton.No,
    )
    assert not actions._allow_batch(2, "Import")


def test_expanded_preferences_keep_confirmation_buttons_visible(app: Any) -> None:
    from widgets.preference.preference import Preference

    dialog = Preference()
    dialog.runtime_group.findChild(QtWidgets.QToolButton).setChecked(True)
    dialog.show()
    app.processEvents()
    available = dialog.screen().availableGeometry()
    assert dialog.height() <= available.height()
    assert dialog.rect().contains(dialog.buttonBox__confirm.geometry())
    assert dialog.scrollArea__preferences.verticalScrollBar().maximum() > 0
    dialog.reject()
