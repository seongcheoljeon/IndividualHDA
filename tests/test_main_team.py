from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_sqlite_repository import payload
from test_team_library import TestTransport, create_asset
from test_team_library import server as server  # noqa: F401


def wait_panel(app: Any, panel: Any) -> None:
    from PySide6 import QtTest

    for _ in range(1200):
        app.processEvents()
        team = panel._team_library

        if (
            not team._tasks.busy
            and not team._refresh_pending
            and not panel._sync_tasks.busy
        ):
            app.processEvents()
            return
        QtTest.QTest.qWait(10)
    pytest.fail("Panel jobs did not finish")


def test_team_uses_main_widgets_and_keeps_personal_database_and_drafts(
    app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, server: Any
) -> None:
    from threading import current_thread, main_thread

    from test_qt import wait_search

    import public
    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
    from libs.team.client import BlobCache, HttpCatalog
    from libs.team.contracts import Command, Unavailable
    from main import IndividualHDA
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    preference = Preference()
    preference.data_dirpath = str(tmp_path)
    preference._Preference__pref_settings.save_cfg_dict_to_file()
    preference.close()
    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    local = SqliteLibraryRepository(database)
    local.ensure_user("tester")
    local_asset = local.register_asset(payload(tmp_path, "LocalWater")).asset
    client, _, _, _, token, project, _ = server
    writes: list[Any] = []

    class RecordingCatalog(HttpCatalog):
        def execute(self, command: Command) -> Any:
            writes.append(current_thread())
            return super().execute(command)

    backend = RecordingCatalog(
        TestTransport(client, token),
        project,
        BlobCache(tmp_path / "remote-cache", project),
    )
    _, remote_asset = create_asset(backend, tmp_path, "TeamWater")
    panel = IndividualHDA()
    try:
        wait_panel(app, panel)
        panel._ihda_list_view.setCurrentIndex(panel._ihda_list_proxy_model.index(0, 0))
        panel._slot_on_hda_item_clicked(panel._ihda_list_proxy_model.index(0, 0))
        panel.textEdit__note.setPlainText("unsaved personal draft")
        original_view = panel._ihda_list_view
        panel._ai_target_id = local_asset["hda_id"]
        team = panel._team_library

        class BrokenCatalog(HttpCatalog):
            def list_assets(
                self, query: str = "", offset: int = 0, limit: int = 100
            ) -> Any:
                raise Unavailable("Connection failed")

        broken = BrokenCatalog(backend.transport, project, backend.cache)
        team.open_backend(
            broken, {"id": project, "name": "Unavailable", "role": "owner"}
        )
        wait_panel(app, panel)
        assert not team.active
        assert panel._assets.rows[0]["hda_name"] == "LocalWater"
        assert panel.textEdit__note.toPlainText() == "unsaved personal draft"

        team.open_backend(backend, {"id": project, "name": "Studio", "role": "owner"})
        wait_panel(app, panel)
        assert team.active, panel.label__metadata_status.text()
        assert panel._ihda_list_view is original_view
        assert panel._assets.rows[0]["hda_name"] == "TeamWater"
        assert panel._repository is None and panel._db_filepath is None
        assert panel._browser.view.comboBox__library_source.currentText() == "Studio"
        panel._ihda_list_view.setCurrentIndex(panel._ihda_list_proxy_model.index(0, 0))
        panel._slot_on_hda_item_clicked(panel._ihda_list_proxy_model.index(0, 0))
        from libs.ai_features import Description

        panel._ai_describe_done(Description("stale personal AI suggestion", []))
        assert panel.textEdit__note.toPlainText() != "stale personal AI suggestion"
        panel.textEdit__note.setPlainText("saved in team")
        panel.pushButton__note_save.click()
        wait_panel(app, panel)
        assert backend.get_asset(remote_asset["id"])["note"] == "saved in team"
        assert not local.list_assets()[0]["hda_note"]
        assert writes and writes[-1] is not main_thread()
        from PySide6 import QtCore

        index = panel._ihda_list_proxy_model.index(0, 0)
        assert index.flags() & QtCore.Qt.ItemFlag.ItemIsDragEnabled
        assert not index.data(QtCore.Qt.ItemDataRole.FontRole).strikeOut()
        panel.actionHistory.trigger()
        wait_panel(app, panel)
        assert panel._ihda_history_model.rowCount() == 1
        history_index = panel._ihda_history_model.index(0, 0)
        assert not history_index.data(QtCore.Qt.ItemDataRole.FontRole).strikeOut()
        # A failed history request must not poison the loaded-owner cache.
        original_histories = team.catalog.histories

        def unavailable_history(asset_id: int) -> Any:
            raise Unavailable("History temporarily unavailable")

        team._history_owner = None
        monkeypatch.setattr(team.catalog, "histories", unavailable_history)
        team.request_history()
        wait_panel(app, panel)
        assert team._history_owner is None
        monkeypatch.setattr(team.catalog, "histories", original_histories)
        team.request_history()
        wait_panel(app, panel)
        assert team._history_owner == remote_asset["id"]
        # Refresh replaces histories; reload the selected asset's history after idle.
        team.refresh()
        panel.actionHistory.trigger()
        wait_panel(app, panel)
        assert panel._ihda_history_model.rowCount() == 1
        assert panel._selection.asset.name == "TeamWater"
        panel._slot_select_view(index=panel._ihda_view_idx)

        panel.comboBox__search_type.setCurrentText("Note")
        panel.lineEdit__search_hda.setText("saved in team")
        wait_search(app, panel)
        assert panel._ihda_list_proxy_model.rowCount() == 1
        panel.lineEdit__search_hda.setText("missing note")
        wait_search(app, panel)
        assert panel._ihda_list_proxy_model.rowCount() == 0
        panel.lineEdit__search_hda.clear()
        panel.comboBox__search_type.setCurrentText("Name")
        wait_search(app, panel)
        panel._ihda_list_view.setCurrentIndex(panel._ihda_list_proxy_model.index(0, 0))
        panel._slot_on_hda_item_clicked(panel._ihda_list_proxy_model.index(0, 0))
        latest = backend.get_asset(remote_asset["id"])
        backend.execute(
            Command(
                "metadata",
                asset_id=latest["id"],
                expected_revision=latest["revision"],
                values={"note": "another artist's edit"},
            )
        )
        panel.textEdit__note.setPlainText("my conflicting draft")
        panel.pushButton__note_save.click()
        wait_panel(app, panel)
        assert "Review changes" in panel.label__metadata_status.text()
        assert panel.textEdit__note.toPlainText() == "my conflicting draft"
        team._recover("compare")
        wait_panel(app, panel)
        dialogs = [
            widget
            for widget in app.topLevelWidgets()
            if widget.windowTitle().startswith("Review changes")
        ]
        assert len(dialogs) == 1
        dialogs[0].reject()
        panel.pushButton__note_save.click()
        wait_panel(app, panel)
        assert backend.get_asset(remote_asset["id"])["note"] == "my conflicting draft"
        team.open_backend(backend, {"id": project, "name": "Studio", "role": "viewer"})
        wait_panel(app, panel)
        assert not panel.pushButton__note_save.isEnabled()
        assert not panel.actionProject_Members.isVisible()
        team.open_backend(
            broken, {"id": project, "name": "Unavailable", "role": "owner"}
        )
        wait_panel(app, panel)
        assert team.active and team.project["name"] == "Studio"
        import os

        if os.environ.get("IHDA_UI_CAPTURE"):
            panel.resize(1200, 820)
            panel.show()
            app.processEvents()
            panel.grab().save(os.environ["IHDA_UI_CAPTURE"])

        assert "revision" not in panel.label__metadata_status.text().lower()
        team.use_personal()
        wait_panel(app, panel)
        assert not team.active
        assert panel._assets.rows[0]["hda_name"] == "LocalWater"
        panel._ihda_list_view.setCurrentIndex(panel._ihda_list_proxy_model.index(0, 0))
        panel._slot_on_hda_item_clicked(panel._ihda_list_proxy_model.index(0, 0))
        assert panel._selection.asset.id == local_asset["hda_id"]
        assert panel.textEdit__note.toPlainText() == "unsaved personal draft"
        assert panel.actionExport_Data.isEnabled()
    finally:
        panel.close()
        app.processEvents()


def test_connection_dialog_only_opens_verified_project_and_never_saves_token(
    app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, server: Any
) -> None:
    from PySide6 import QtTest, QtWidgets

    from widgets.library_connection import dialog as connection_module

    client, _, _, _, token, _, _ = server

    class Transport(TestTransport):
        def __init__(self, url: str, credential: Any) -> None:
            super().__init__(client, credential())
            self.url = url

    monkeypatch.setattr(connection_module, "HttpTransport", Transport)
    dialog = connection_module.ConnectionDialog(tmp_path)
    connected = []
    dialog.connected.connect(
        lambda backend, project: connected.append((backend, project))
    )
    try:
        assert (
            dialog.lineEdit__access_token.echoMode()
            == QtWidgets.QLineEdit.EchoMode.Password
        )
        dialog.lineEdit__server_url.setText("http://127.0.0.1:8000")
        dialog.lineEdit__access_token.setText(token)
        assert not dialog.pushButton__open_library.isEnabled()
        dialog.pushButton__connect.click()
        for _ in range(500):
            app.processEvents()
            if not dialog._tasks.busy:
                break
            QtTest.QTest.qWait(10)
        assert not dialog._tasks.busy
        assert dialog.comboBox__project.currentText() == "Studio"
        assert dialog.pushButton__open_library.isEnabled()
        dialog.pushButton__open_library.click()
        assert len(connected) == 1
        assert token not in (tmp_path / "workspace.json").read_text()
        dialog.lineEdit__server_url.setText("http://127.0.0.1:8001")
        assert not dialog.pushButton__open_library.isEnabled()
        assert dialog._transport is None
    finally:
        dialog.shutdown()
        dialog.deleteLater()
