from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtTest

import public
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from test_sqlite_repository import payload


def wait_sync(app: Any, panel: Any) -> None:
    for _ in range(300):
        app.processEvents()
        if not panel._sync_tasks.busy and not panel._reload_pending:
            break
        QtTest.QTest.qWait(10)
    app.processEvents()


def test_reload_and_revision_poll_follow_external_changes(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView
    from main import IndividualHDA

    monkeypatch.setattr(
        WebView,
        "_WebView__set_init_load",
        lambda self: self.lineEdit__address.setText("about:blank"),
    )
    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    preference = Preference()
    preference.data_dirpath = str(tmp_path)
    preference._Preference__pref_settings.save_cfg_dict_to_file()
    preference.close()
    root = public.hda_base_dirpath(tmp_path) / "tester"
    with SQLite3DatabaseAPI(tmp_path / "ihda.db"):
        pass
    external = SqliteLibraryRepository(tmp_path / "ihda.db")
    external.ensure_user("tester")
    external.register_asset(payload(root, "Water"))

    panel = IndividualHDA()
    assert len(panel._assets.rows) == 1 and panel._user == "tester"
    panel._selection.asset.id = 1
    panel._selection.asset.data = panel._assets.rows[0]

    # Another panel/user adds an asset: an explicit Reload picks it up.
    external.register_asset(payload(root, "Fire"))
    panel.reload_library()
    wait_sync(app, panel)
    assert [row["hda_name"] for row in panel._assets.rows] == ["Fire", "Water"]
    assert panel._selection.asset.id == 1 and panel._selection.asset.row == 1
    assert panel.comboBox__hist_ihda_node.count() == 2
    assert panel._ihda_history_model.rowCount() == 2

    # The poller notices a revision change and drops a selection that vanished.
    external.delete_asset(1, root / "sop" / "Water")
    panel._known_revision = -1
    panel._poll_library_revision()
    wait_sync(app, panel)
    assert [row["hda_name"] for row in panel._assets.rows] == ["Fire"]
    assert panel._selection.asset.id is None
    assert panel.label__hda_count.text() == "1"

    # Unchanged revision: no reload is scheduled.
    panel._poll_library_revision()
    wait_sync(app, panel)
    assert not panel._reload_pending
    panel.close()
    app.processEvents()
