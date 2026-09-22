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

    # History filters: the date filter starts on the last month, so entries
    # registered today stay visible; Clear filters undoes everything at once.
    from PySide6.QtCore import QDate

    history = panel.models.history_proxy_model
    assert panel.dateEdit__hist_search_end.date() == QDate.currentDate()
    assert panel.dateEdit__hist_search_start.date() < QDate.currentDate()
    panel.checkBox__hist_search_date.setChecked(True)
    assert history.rowCount() == 2 and panel.label__hist_cnt.text() == "2"
    # An inverted range is sorted, not refused.
    panel.dateEdit__hist_search_start.setDate(QDate.currentDate().addDays(3))
    assert history.rowCount() == 2
    panel.comboBox__hist_ihda_node.setCurrentIndex(
        panel.comboBox__hist_ihda_node.findData(1)
    )
    panel.lineEdit__search_hda_hist.setText("zzz")
    panel.models.search_filter_regexp_hist_hda_item("zzz")
    assert history.rowCount() == 0
    panel.pushButton__hist_reset_filters.click()
    assert panel.comboBox__hist_ihda_node.currentData() == -1
    assert panel.lineEdit__search_hda_hist.text() == ""
    assert not panel.checkBox__hist_search_date.isChecked()
    assert not panel.dateEdit__hist_search_start.isEnabled()
    assert history.rowCount() == 2 and panel.label__hist_cnt.text() == "2"

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
        last_timings: dict[str, float] = {}

        def complete(self, prompt: Prompt, *, progress: Any = None) -> str:
            prompts.append(prompt)
            if progress is not None:
                progress(1)
                progress(2)
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
    # Tags arrive as suggestion chips; the stored tag stays until one is accepted.
    assert panel.textEdit__tag.tags() == ["물"]
    assert sorted(panel.textEdit__tag.suggestions()) == ["sim", "water"]
    assert repo.list_assets()[0].hda_note is None  # nothing saved without a click
    # The progress line and its cancel button only exist while a request runs.
    assert not panel.label__ai_status.isVisible()
    assert not panel.pushButton__ai_cancel.isVisible()
    assert panel.label__ai_status.text() == ""
    # The GUI slot formats what the worker emitted; no thread needed to check it.
    panel._ai_actions.progress.emit(95)
    app.processEvents()
    assert "95 tokens" in panel.label__ai_status.text()
    assert panel.pushButton__ai_suggest.isEnabled()
    panel.close()
    app.processEvents()


def test_ai_cancel_discards_the_answer_and_is_not_an_error(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cancel is an exception raised from the progress callback.

    BackgroundJob routes it to the result channel, so the editors must stay
    untouched and the log must not call it a failure.
    """
    from libs.ai_features import Description
    from libs.ai_provider import AISettings, Prompt
    from main import IndividualHDA
    from widgets.panel.ai_actions import _Cancelled
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

    captured: list[Any] = []

    class Fake:
        last_timings: dict[str, float] = {}

        def complete(self, prompt: Prompt, *, progress: Any = None) -> str:
            captured.append(progress)
            return '{"summary": "should never arrive", "tags": []}'

    panel = IndividualHDA(services=PanelServices(ai=lambda settings: Fake()))
    try:
        panel.selection.state.asset.id = 1
        panel.selection.state.asset.data = panel.models.assets.rows[0]
        panel._slot_ai_suggest()
        for _ in range(300):
            app.processEvents()
            if not panel._ai_tasks.busy:
                break
            QtTest.QTest.qWait(10)
        app.processEvents()

        # The fake answered immediately, so start from a known editor state and
        # then cancel: what matters is that nothing lands afterwards.
        panel.textEdit__note.setPlainText("hand written")
        panel.pushButton__ai_cancel.click()

        # The callback the worker was handed now refuses to continue -- this is
        # the cancel, no token crosses into libs/.
        with pytest.raises(_Cancelled):
            captured[0](5)
        # A result that beat the cancel is dropped rather than applied.
        panel._ai_actions.describe_done(Description("should never arrive", ()))
        assert panel.textEdit__note.toPlainText() == "hand written"
        # And the cancel is reported as such, never through the failure branch.
        panel._ai_actions.result(None, _Cancelled())
    finally:
        panel.close()
