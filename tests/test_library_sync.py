from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtTest
from support.personal import payload

import public
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def wait_sync(app: Any, panel: Any) -> None:
    for _ in range(300):
        app.processEvents()
        if not panel._library_sync.tasks.busy and not panel._reload_pending:
            break
        QtTest.QTest.qWait(10)
    app.processEvents()


def test_reload_and_revision_poll_follow_external_changes(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from main import IndividualHDA
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView

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
    assert len(panel.models.assets.rows) == 1 and panel.session.user == "tester"
    panel.selection.state.asset.id = 1
    panel.selection.state.asset.data = panel.models.assets.rows[0]

    # Another panel/user adds an asset: an explicit Reload picks it up.
    external.register_asset(payload(root, "Fire"))
    panel.reload_library()
    wait_sync(app, panel)
    assert [row.hda_name for row in panel.models.assets.rows] == ["Fire", "Water"]
    assert panel.selection.state.asset.id == 1 and panel.selection.state.asset.row == 1
    from model.ihda_list_model import ListModel
    from model.ihda_table_model import TableModel

    assert panel.selection.state.asset.name == "Water"
    assert panel.selection.state.asset.version == "1.0"
    assert panel.views.assets_list.currentIndex().data(ListModel.id_role) == 1
    assert panel.views.assets_table.currentIndex().data(TableModel.id_role) == 1
    assert panel.comboBox__hist_ihda_node.currentData() == -1
    assert panel.comboBox__hist_ihda_node.count() == 3
    assert panel.models.history_model.rowCount() == 2

    # The poller notices a revision change and drops a selection that vanished.
    external.delete_asset(1, root / "sop" / "Water")
    panel._known_revision = -1
    panel._poll_library_revision()
    wait_sync(app, panel)
    assert [row.hda_name for row in panel.models.assets.rows] == ["Fire"]
    assert panel.selection.state.asset.id is None
    assert panel.label__hda_count.text() == "1"

    # Unchanged revision: no reload is scheduled.
    panel._poll_library_revision()
    wait_sync(app, panel)
    assert not panel._reload_pending
    panel.close()
    app.processEvents()


def test_ai_suggest_fills_editors_without_saving(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from libs.ai_provider import AISettings, Prompt
    from main import IndividualHDA
    from widgets.panel.services import PanelServices
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(
        WebView,
        "_WebView__set_init_load",
        lambda self: self.lineEdit__address.setText("about:blank"),
    )
    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    preference = Preference()
    preference.data_dirpath = str(tmp_path)
    preference.ai_settings = AISettings(kind="local", endpoint="http://x", model="m")
    preference._Preference__pref_settings.save_cfg_dict_to_file()
    preference.close()
    root = public.hda_base_dirpath(tmp_path) / "tester"
    with SQLite3DatabaseAPI(tmp_path / "ihda.db"):
        pass
    repo = SqliteLibraryRepository(tmp_path / "ihda.db")
    repo.ensure_user("tester")
    repo.register_asset(payload(root, "Water"))
    repo.set_tags(1, ["물"])

    prompts: list[Prompt] = []

    class Fake:
        def complete(self, prompt: Prompt) -> str:
            prompts.append(prompt)
            return '{"summary": "Water sim.", "tags": ["water", "sim"]}'

    panel = IndividualHDA(services=PanelServices(ai=lambda settings: Fake()))
    panel.selection.state.asset.id = 1
    panel.selection.state.asset.data = panel.models.assets.rows[0]
    panel._slot_ai_suggest()
    for _ in range(300):
        app.processEvents()
        if not panel._ai_tasks.busy:
            break
        QtTest.QTest.qWait(10)
    app.processEvents()
    assert "물" in prompts[0].text  # vocabulary from the library
    assert panel.textEdit__note.toPlainText() == "Water sim."
    assert panel.notes._split_tag_string(panel.notes._hda_tags) == [
        "sim",
        "water",
        "물",
    ]
    assert repo.list_assets()[0].hda_note is None  # nothing saved without a click
    assert panel.pushButton__ai_suggest.isEnabled()
    panel.close()
    app.processEvents()
