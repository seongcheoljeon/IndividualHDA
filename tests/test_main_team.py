from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from support.personal import payload
from support.team import TestTransport, create_asset
from support.team import server as server  # noqa: F401


def wait_panel(app: Any, panel: Any) -> None:
    from PySide6 import QtTest

    for _ in range(1200):
        app.processEvents()
        team = panel._team_library

        if (
            not team._tasks.busy
            and not team._refresh_pending
            and not panel._library_sync.tasks.busy
        ):
            app.processEvents()
            return
        QtTest.QTest.qWait(10)
    pytest.fail("Panel jobs did not finish")


def test_team_uses_main_widgets_and_keeps_personal_database_and_drafts(
    app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, server: Any
) -> None:
    from threading import current_thread, main_thread

    from test_qt import wait_search, wait_until

    import public
    from libs.database.sqlite_repository import SqliteLibraryRepository
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
    from libs.team.client import BlobCache, HttpCatalog
    from libs.team.contracts import Command, NotFound, Unavailable
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
        panel.views.assets_list.setCurrentIndex(
            panel.models.list_proxy_model.index(0, 0)
        )
        panel.selection._slot_on_hda_item_clicked(
            panel.models.list_proxy_model.index(0, 0)
        )
        panel.textEdit__note.setPlainText("unsaved personal draft")
        original_view = panel.views.assets_list
        panel._ai_target_id = local_asset.hda_id
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
        assert panel.models.assets.rows[0].hda_name == "LocalWater"
        assert panel.textEdit__note.toPlainText() == "unsaved personal draft"

        team.open_backend(backend, {"id": project, "name": "Studio", "role": "owner"})
        wait_panel(app, panel)
        assert team.active, panel.label__metadata_status.text()
        assert panel.views.assets_list is original_view
        assert panel.models.assets.rows[0].hda_name == "TeamWater"
        assert panel.session.repository is None and panel.queries.db_filepath is None
        assert panel._browser.view.comboBox__library_source.currentText() == "Studio"
        panel.views.assets_list.setCurrentIndex(
            panel.models.list_proxy_model.index(0, 0)
        )
        panel.selection._slot_on_hda_item_clicked(
            panel.models.list_proxy_model.index(0, 0)
        )
        from libs.ai_features import Description

        panel._ai_describe_done(Description("stale personal AI suggestion", []))
        assert panel.textEdit__note.toPlainText() != "stale personal AI suggestion"
        panel.textEdit__note.setPlainText("saved in team")
        panel.pushButton__metadata_save.click()
        wait_panel(app, panel)
        assert backend.get_asset(remote_asset["id"])["note"] == "saved in team"
        # Leaving the personal library autosaved its draft; the team write above
        # must not have touched it.
        assert local.list_assets()[0].hda_note == "unsaved personal draft"
        assert writes and writes[-1] is not main_thread()
        from PySide6 import QtCore

        from model.ihda_history_model import HistoryModel

        index = panel.models.list_proxy_model.index(0, 0)
        assert index.flags() & QtCore.Qt.ItemFlag.ItemIsDragEnabled
        assert not index.data(QtCore.Qt.ItemDataRole.FontRole).strikeOut()
        panel.actionHistory.trigger()
        wait_panel(app, panel)
        assert panel.models.history_model.rowCount() == 1
        history_index = panel.models.history_model.index(0, 0)
        assert not history_index.data(QtCore.Qt.ItemDataRole.FontRole).strikeOut()
        # A rename on the server shows up as an activity row, not a version.
        backend.execute(
            Command(
                "rename",
                asset_id=remote_asset["id"],
                expected_revision=backend.get_asset(remote_asset["id"])["revision"],
                values={"name": "TeamWater2"},
            )
        )
        team._history_owner = None
        team.request_history()
        wait_panel(app, panel)
        rows = [
            panel.models.history_model.index(row, 0).data(HistoryModel.data_role)
            for row in range(panel.models.history_model.rowCount())
        ]
        assert [row.kind for row in rows] == ["version", "rename"]
        assert rows[1].comment == "NAME (CHANGE) TeamWater → TeamWater2"
        assert rows[1].remote and rows[1].hist_id == 0 and rows[1].userid
        assert not (
            panel.models.history_model.index(1, 0).flags()
            & QtCore.Qt.ItemFlag.ItemIsDragEnabled
        )
        # Activity is decoration: when the events call fails the versions still load.
        original_events = team.catalog.events
        monkeypatch.setattr(
            team.catalog,
            "events",
            lambda asset_uuid: (_ for _ in ()).throw(Unavailable("events down")),
        )
        team._history_owner = None
        team.request_history()
        wait_panel(app, panel)
        assert team._history_owner == remote_asset["id"]
        assert panel.models.history_model.rowCount() == 1
        monkeypatch.setattr(team.catalog, "events", original_events)
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
        assert panel.models.history_model.rowCount() == 2  # version + rename row
        assert panel.selection.state.asset.name == "TeamWater2"
        panel.selection.slot_select_view(index=panel._ihda_view_idx)

        panel.comboBox__search_type.setCurrentText("Note")
        panel.lineEdit__search_hda.setText("saved in team")
        wait_search(app, panel)
        assert panel.models.list_proxy_model.rowCount() == 1
        panel.lineEdit__search_hda.setText("missing note")
        wait_search(app, panel)
        assert panel.models.list_proxy_model.rowCount() == 0
        panel.lineEdit__search_hda.clear()
        panel.comboBox__search_type.setCurrentText("Name")
        wait_search(app, panel)
        panel.views.assets_list.setCurrentIndex(
            panel.models.list_proxy_model.index(0, 0)
        )
        panel.selection._slot_on_hda_item_clicked(
            panel.models.list_proxy_model.index(0, 0)
        )
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
        panel.pushButton__metadata_save.click()
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
        # Both sides render as a line diff; the changed line is highlighted.
        assert "my conflicting draft" in dialogs[0].textEdit__left.toPlainText()
        assert "another artist's edit" in dialogs[0].textEdit__right.toPlainText()
        assert "background-color:" in dialogs[0].textEdit__left.toHtml()
        dialogs[0].pushButton__keep_mine.click()  # saves the draft over theirs
        wait_panel(app, panel)
        assert backend.get_asset(remote_asset["id"])["note"] == "my conflicting draft"

        # Trash needs no prompt when nothing depends on the asset; Undo restores it.
        def trashed() -> bool:
            try:
                backend.get_asset(remote_asset["id"])  # the server hides trashed assets
            except NotFound:
                return True
            return False

        team.actions.remove()
        # The confirm step runs on a deferred timer and re-arms while a task is
        # busy, so poll for the outcome instead of counting event-loop turns.
        wait_until(app, trashed)
        wait_panel(app, panel)
        toasts = panel._toasts.toasts()
        assert toasts and toasts[-1].action is not None
        toasts[-1].action.click()
        wait_until(app, lambda: not trashed())
        wait_panel(app, panel)
        assert not backend.get_asset(remote_asset["id"]).get("deleted")
        team.refresh()
        wait_panel(app, panel)
        assert panel.models.assets.rows[0].hda_name == "TeamWater2"
        team.open_backend(backend, {"id": project, "name": "Studio", "role": "viewer"})
        wait_panel(app, panel)
        assert not panel.pushButton__metadata_save.isEnabled()
        assert not panel.tools.actionProject_Members.isVisible()
        assert panel.label__metadata_status.text() == "Read-only (viewer role)"
        team.open_backend(
            broken, {"id": project, "name": "Unavailable", "role": "owner"}
        )
        wait_panel(app, panel)
        assert team.active and team.project["name"] == "Studio"
        # Another user's change shows up on the next revision poll, no Reload.
        create_asset(backend, tmp_path, "TeamZeta")
        assert len(panel.models.assets.rows) == 1
        panel._library_sync.timer.timeout.emit()
        wait_panel(app, panel)
        assert [row.hda_name for row in panel.models.assets.rows] == [
            "TeamWater2",
            "TeamZeta",
        ]
        assert panel._library_sync.tasks.busy is False
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
        assert panel.models.assets.rows[0].hda_name == "LocalWater"
        panel.views.assets_list.setCurrentIndex(
            panel.models.list_proxy_model.index(0, 0)
        )
        panel.selection._slot_on_hda_item_clicked(
            panel.models.list_proxy_model.index(0, 0)
        )
        assert panel.selection.state.asset.id == local_asset.hda_id
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
        def __init__(self, url: str, credential: Any, *, timeout: float) -> None:
            super().__init__(client, credential())
            self.url = url
            assert timeout == 47

    monkeypatch.setattr(connection_module, "HttpTransport", Transport)
    from libs.runtime_settings import RuntimeSettings

    dialog = connection_module.ConnectionDialog(
        tmp_path, runtime=RuntimeSettings(team_timeout_seconds=47)
    )
    connected = []
    dialog.connected.connect(
        lambda backend, project: connected.append((backend, project))
    )
    try:
        assert (
            dialog.lineEdit__access_token.echoMode()
            == QtWidgets.QLineEdit.EchoMode.Password
        )
        dialog.checkBox__show_token.setChecked(True)
        assert (
            dialog.lineEdit__access_token.echoMode()
            == QtWidgets.QLineEdit.EchoMode.Normal
        )
        dialog.checkBox__show_token.setChecked(False)
        dialog.lineEdit__access_token.setText(token)
        # A bare host is refused before any request goes out.
        dialog.lineEdit__server_url.setText("127.0.0.1:8000")
        dialog.pushButton__connect.click()
        assert not dialog._tasks.busy
        assert "http://" in dialog.label__connection_status.text()
        dialog.lineEdit__server_url.setText("http://127.0.0.1:8000")
        assert not dialog.pushButton__open_library.isEnabled()
        assert dialog.pushButton__connect.isDefault()
        dialog.pushButton__connect.click()
        for _ in range(500):
            app.processEvents()
            if not dialog._tasks.busy:
                break
            QtTest.QTest.qWait(10)
        assert not dialog._tasks.busy
        assert dialog.comboBox__project.currentText() == "Studio"
        assert dialog.pushButton__open_library.isEnabled()
        assert dialog.pushButton__open_library.isDefault()
        dialog.pushButton__open_library.click()
        assert len(connected) == 1
        saved = (tmp_path / "workspace.json").read_text(encoding="utf-8")
        assert token not in saved
        dialog.lineEdit__server_url.setText("http://127.0.0.1:8001")
        assert not dialog.pushButton__open_library.isEnabled()
        assert dialog._transport is None
    finally:
        dialog.shutdown()
        dialog.deleteLater()
    # The next dialog starts on the last server and suggests the recent ones.
    assert connection_module.recent_servers(tmp_path) == ["http://127.0.0.1:8000"]
    again = connection_module.ConnectionDialog(tmp_path)
    try:
        assert again.lineEdit__server_url.text() == "http://127.0.0.1:8000"
        assert again.lineEdit__server_url.completer().model().stringList() == [
            "http://127.0.0.1:8000"
        ]
    finally:
        again.shutdown()
        again.deleteLater()
