from __future__ import annotations

import pathlib
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from libs.drag_payload import decode_payload, encode_payload
from libs.process_job import ProcessJob
from libs.qt_helpers import wildcard_expression


def test_drag_unicode_path() -> None:
    value = {"hda_id": 7, "hda_dirpath": Path("asset's 한글"), "tags": ["물"]}
    assert decode_payload(encode_payload(value)) == value
    with pytest.raises(ValueError):
        decode_payload('__import__("os").system("echo bad")')


def test_wildcard_search() -> None:
    regex = wildcard_expression("foo*", QtCore.Qt.CaseInsensitive)
    assert regex.match("prefix Foo_한글").hasMatch()
    assert not regex.match("bar").hasMatch()


def test_note_highlighter(app: Any) -> None:
    from libs.note_syntax import NoteHighLighter

    edit = QtWidgets.QTextEdit()
    highlighter = NoteHighLighter(edit.document())
    edit.setPlainText("Important #한글\n!!!critical 'text' 1.5")
    highlighter.rehighlight()


def test_process_success_and_failure(app: Any) -> None:
    for command, expected in [
        # -X utf8: the child must not depend on the runner's console code page.
        ([sys.executable, "-X", "utf8", "-c", 'print("한글")'], 0),
        (["/nonexistent/ihda-executable"], -1),
    ]:
        loop = QtCore.QEventLoop()
        result = []
        job = ProcessJob(command)
        job.finished.connect(
            lambda code, output, result=result, loop=loop: (
                result.append((code, output)),
                loop.quit(),
            )
        )
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(5000)
        job.start()
        loop.exec()
        job.shutdown()
        assert result and result[0][0] == expected
        if expected == 0:
            # macOS may hand back decomposed Hangul; compare in one normal form.
            assert "한글" in unicodedata.normalize("NFC", result[0][1])


def test_video_widget(app: Any) -> None:
    from widgets.video_player.video_player import VideoPlayer

    widget = VideoPlayer()
    widget.add_playlist(["one.mp4", "two.mp4", "one.mp4"])
    assert widget.listWidget__playlist.count() == 2
    widget.close()


def test_panel_constructs(app: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(
        WebView,
        "_WebView__set_init_load",
        lambda self: self.lineEdit__address.setText("about:blank"),
    )
    from main import IndividualHDA

    panel = IndividualHDA()
    assert panel.comboBox__search_type.count() == 5
    source = panel._browser.view.comboBox__library_source
    assert source.currentText() == "Personal"
    panel._team_library.open_connection()
    connection = panel._team_library._connection
    assert connection is not None and connection.isVisible()
    assert not hasattr(connection, "tableWidget__assets")
    connection.reject()
    app.processEvents()
    assert panel._team_library._connection is None
    panel.close()


def wait_until(app: Any, condition: Callable[[], bool], tries: int = 500) -> None:
    """Poll the GUI loop until ``condition`` holds; never a fixed wait (CI timing)."""
    from PySide6 import QtTest

    for _ in range(tries):
        app.processEvents()
        if condition():
            return
        QtTest.QTest.qWait(10)
    pytest.fail("Condition not met in time")


def wait_search(app: Any, panel: Any) -> None:
    """Repository searches run off the GUI thread; wait for the current one."""
    from PySide6 import QtTest

    for _ in range(200):
        app.processEvents()
        if not panel._asset_search.busy:
            break
        QtTest.QTest.qWait(10)
    app.processEvents()


def test_panel_with_saved_library(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    import public
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
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
    assets = public.hda_base_dirpath(tmp_path) / "anonymous" / "sop" / "Water"
    assets.mkdir(parents=True)
    (assets / "water.ihda").touch()
    with SQLite3DatabaseAPI(tmp_path / "ihda.db") as db:
        assert db.insert_users("anonymous", "a@example.com") == 1
        assert db.insert_hda_category("sop", "anonymous") == 1
        assert db.insert_hda_key("Water", "sop", "anonymous") == 1
        key = db.get_hda_key_id(name="Water")[0]
        assert (
            db.insert_hda_info(key, "1.0", filename="water.ihda", dirpath=assets) == 1
        )
        assert db.insert_icon_info(key, ["SOP", "box"]) == 1
        assert (
            db.insert_hipfile_info(
                key, "test.hip", tmp_path, "21.0", "commercial", "Linux", 1, 24, 23.976
            )
            == 1
        )
        assert (
            db.insert_houdini_node_info(key, "box", "Box", False, False, "/obj/geo/box")
            == 1
        )
        assert db.insert_thumbnail_info(key, assets, "thumb.jpg", "1.0") == 1
        assert db.insert_tag_info(key, ["water"]) == 1
    from widgets.panel.policy import PanelPolicy
    from widgets.panel.services import PanelServices

    panel = IndividualHDA(
        services=PanelServices(policy=PanelPolicy(autosave_delay_ms=20))
    )
    model = panel.models.list_proxy_model
    assert model.rowCount() == 1
    panel.lineEdit__search_hda.setText("missing")
    wait_search(app, panel)
    assert model.rowCount() == 0
    panel.lineEdit__search_hda.setText("Water")
    wait_search(app, panel)
    assert model.rowCount() == 1
    panel.comboBox__search_type.setCurrentText("Note")
    wait_search(app, panel)
    assert model.rowCount() == 0
    panel.comboBox__search_type.setCurrentText("All")
    panel.lineEdit__search_hda.setText("tag:water")
    wait_search(app, panel)
    assert model.rowCount() == 1
    panel.lineEdit__search_hda.setText("")
    app.processEvents()
    assert model.rowCount() == 1
    # The code-built browser still drives the legacy selection/detail path.
    browser = panel._browser.view
    browser.listView__hda.clicked.emit(model.index(0, 0))
    assert panel.selection.state.asset.id == key
    browser.pushButton__table_mode.click()
    browser.tableView__hda.setCurrentIndex(panel.models.table_proxy_model.index(0, 0))
    browser.tableView__hda.clicked.emit(panel.models.table_proxy_model.index(0, 0))
    assert (
        panel.selection.state.asset.id == key
        and browser.stackedWidget__hda.currentIndex() == 1
    )
    # Personal edits autosave: editor -> debounce -> presenter -> worker -> SQLite.
    assert not panel.pushButton__metadata_save.isVisible()
    panel.textEdit__note.setPlainText("saved from the metadata presenter")
    assert panel.label__metadata_status.text() == "Unsaved"
    # The label follows the GUI callback that also updates the shared models.
    wait_until(app, lambda: panel.label__metadata_status.text() == "Saved · just now")
    assert (
        panel.session.repository.list_assets()[0].hda_note
        == "saved from the metadata presenter"
    )
    assert panel.models.assets.rows[0].hda_note == "saved from the metadata presenter"
    panel.textEdit__tag.setPlainText("#Water #water #한글")
    # Editing tags must light the tag indicator, not the note one.
    assert panel.label__tag_status.text() == "Unsaved"
    assert not panel.label__metadata_status.text()
    wait_until(app, lambda: panel.label__metadata_status.text() == "Saved · just now")
    assert panel.session.repository.list_assets()[0].hda_tags == ("Water", "한글")
    assert not panel.label__tag_status.text()
    # The category tree knows how many assets each category holds.
    from model.ihda_category_model import CategoryModel

    tree = panel.models.category_model
    network = tree.index(0, 0)
    sop = next(
        tree.index(row, 0, network)
        for row in range(tree.rowCount(network))
        if tree.index(row, 0, network).data(CategoryModel.category_role) == "sop"
    )
    assert sop.data(CategoryModel.count_role) == 1
    # The grid draws cards; the star on a card toggles the favorite of that row.
    from widgets.item_delegates import CardDelegate

    assert isinstance(panel.views.assets_list.itemDelegate(), CardDelegate)
    assert not panel.session.repository.list_assets()[0].is_favorite_hda
    panel.management.toggle_favorite_at(panel.models.list_proxy_model.index(0, 0))
    assert panel.session.repository.list_assets()[0].is_favorite_hda
    assert panel.models.list_proxy_model.index(0, 0).data(
        panel.models.list_proxy_model.favorite_role
    )
    panel.management.toggle_favorite_at(panel.models.list_proxy_model.index(0, 0))
    assert not panel.session.repository.list_assets()[0].is_favorite_hda
    # Double-click plays the video (none here: a toast, no import); Enter imports
    # the selected rows through the Houdini port.
    imported: list[list[bytes]] = []
    monkeypatch.setattr(panel.houdini, "import_models", imported.append)
    panel.selection._slot_hda_double_clicked(panel.models.table_proxy_model.index(0, 0))
    assert not imported and "no video" in panel._toasts.toasts()[-1].message.text()
    for toast in panel._toasts.toasts():
        toast.dismiss()
    # Keyboard: Enter imports, Escape clears the search, F5 reloads; all scoped to
    # the panel so Houdini keeps its own keys.
    panel._shortcuts["import_table"].activated.emit()
    assert len(imported) == 1 and len(imported[0]) == 1
    assert decode_payload(imported[0][0])["hda_name"] == "Water"
    panel.lineEdit__search_hda.setText("pending")
    panel._shortcuts["clear_search"].activated.emit()
    assert panel.lineEdit__search_hda.text() == ""
    assert panel.actionReload.shortcut() == QtGui.QKeySequence(
        QtGui.QKeySequence.StandardKey.Refresh
    )
    assert all(
        s.context() != QtCore.Qt.ShortcutContext.WindowShortcut
        for s in panel._shortcuts.values()
    )
    # Markdown preview renders the plain-text note; the stored value is untouched.
    panel.textEdit__note.setPlainText("# Title\n\nSome **bold** text")
    panel.toolButton__note_preview.setChecked(True)
    assert (
        panel.textEdit__note.isHidden()
        and not panel.textBrowser__note_preview.isHidden()
    )
    assert panel.textBrowser__note_preview.toPlainText() == "Title\nSome bold text"
    panel.textEdit__note.setPlainText("# Title\n\nSome **bold** text, more")
    assert (
        panel.textBrowser__note_preview.toPlainText() == "Title\nSome bold text, more"
    )
    panel.toolButton__note_preview.setChecked(False)
    assert (
        not panel.textEdit__note.isHidden()
        and panel.textBrowser__note_preview.isHidden()
    )
    wait_until(app, lambda: panel.label__metadata_status.text() == "Saved · just now")
    assert (
        panel.session.repository.list_assets()[0].hda_note
        == "# Title\n\nSome **bold** text, more"
    )
    # Delete moves to the Trash without a prompt; the toast offers Undo.
    panel._shortcuts["remove_table"].activated.emit()
    wait_until(app, lambda: panel.models.list_proxy_model.rowCount() == 0)
    toasts = panel._toasts.toasts()
    assert toasts and toasts[-1].action is not None
    assert toasts[-1].action.text() == "Undo" and "Trash" in toasts[-1].message.text()
    toasts[-1].action.click()
    wait_until(app, lambda: panel.models.list_proxy_model.rowCount() == 1)
    assert not panel._toasts.toasts()
    panel.doubleSpinBox__zoom.setValue(150)
    panel._ui_settings.save_cfg_dict_to_file()
    panel.doubleSpinBox__zoom.setValue(100)
    panel._ui_settings.load_cfg_dict_from_file()
    assert panel.doubleSpinBox__zoom.value() == 150
    panel.tools.open_library_tools(4)
    dialog = panel.tools.library_manager
    assert dialog.tabs.count() == 6 and dialog.tabs.currentIndex() == 4
    dialog.close()
    app.processEvents()
    assert panel.tools.library_manager is None
    panel.tools.open_library_tools(0)
    panel.tools.library_manager._search()
    panel.close()
    app.processEvents()


@pytest.mark.parametrize("outcome", ["success", "failure", "close", "host_destroy"])
def test_panel_background_job_lifecycle(
    app: Any, monkeypatch: pytest.MonkeyPatch, outcome: Any
) -> None:
    """Inherited Qt slots must return to the GUI thread and defer close safely."""
    from threading import Event

    from PySide6 import QtTest

    from main import IndividualHDA
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(
        WebView,
        "_WebView__set_init_load",
        lambda self: self.lineEdit__address.setText("about:blank"),
    )
    panel = IndividualHDA()
    release = Event()
    results = []
    worker_threads = []

    def operation() -> str:
        worker_threads.append(QtCore.QThread.currentThread())
        if not release.wait(5):
            raise TimeoutError("test worker was not released")
        if outcome == "failure":
            raise ValueError("expected test failure")
        return "finished"

    try:
        panel._start_file_job(
            operation,
            lambda value: results.append((value, QtCore.QThread.currentThread())),
        )
        job = panel._tasks.file_job
        assert not panel.centralwidget.isEnabled()
        # Duplicate requests must not replace an active operation.
        panel._start_file_job(lambda: "duplicate", results.append)
        assert panel._tasks.file_job is job
        if outcome == "close":
            shutdowns: list[int] = []
            monkeypatch.setattr(
                panel._preference, "shutdown", lambda: shutdowns.append(1)
            )
            assert not panel.close()
            assert panel.status.close_requested and not panel.status.closing
            # A refused close tears nothing down yet.
            assert not shutdowns and panel._library_sync.timer.isActive()
        release.set()
        if outcome == "host_destroy":
            panel.shutdown_for_host()
            assert panel.status.host_destroying and panel.status.closing
        for _ in range(500):
            app.processEvents()
            if panel._tasks.file_job is None and (
                outcome != "close" or panel.status.closing
            ):
                break
            QtTest.QTest.qWait(10)
        assert panel._tasks.file_job is None
        assert worker_threads and worker_threads[0] != app.thread()
        assert results == ([] if outcome == "failure" else [("finished", app.thread())])
        assert panel.centralwidget.isEnabled()
        if outcome == "close":
            assert panel.status.closing
            assert shutdowns == [1]
            assert not panel._library_sync.timer.isActive()
            assert not panel._asset_search_debounce.timer.isActive()
    finally:
        release.set()
        if panel._tasks.file_job is not None:
            panel._tasks.file_job.wait(6000)
            app.processEvents()
        panel.close()


def test_help_server_is_resolved_only_when_web_view_is_shown(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    import public
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(public.Paths, "json_web_filepath", tmp_path / "web.json")

    calls = []
    loads = []

    def help_url() -> str:
        calls.append(True)
        return "http://localhost:48626/"

    monkeypatch.setattr(
        WebView,
        "_WebView__load",
        lambda self, url=None: loads.append(url or self.lineEdit__address.text()),
    )
    view = WebView(help_site=help_url)
    try:
        assert calls == loads == []
        view.show()
        app.processEvents()
        assert calls == [True]
        assert loads == ["http://localhost:48626/"]
        view.hide()
        view.show()
        view.pushButton__help.click()
        assert calls == [True]
        assert loads[-1] == "http://localhost:48626/"
    finally:
        view.close()


@pytest.mark.parametrize(
    ("saved", "expected", "kept"),
    [
        # A dead help server from a previous Houdini session must not come back.
        ("http://127.0.0.1:9547/", "http://localhost:48626/", False),
        # A page the user navigated to is still restored.
        ("https://forums.odforce.net/", "https://forums.odforce.net/", True),
    ],
)
def test_saved_address_never_revives_a_dead_help_server(
    app: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    saved: str,
    expected: str,
    kept: bool,
) -> None:
    import json

    import public
    from libs import keys
    from widgets.web_view.web_view import WebView

    config = tmp_path / "web.json"
    config.write_text(json.dumps({keys.Name.WebUI.url_addr: saved}), encoding="utf-8")
    monkeypatch.setattr(public.Paths, "json_web_filepath", config)
    monkeypatch.setattr(public.Paths, "ini_web_filepath", tmp_path / "web.ini")

    loads: list[str] = []
    monkeypatch.setattr(
        WebView,
        "_WebView__load",
        lambda self, url=None: loads.append(url or self.lineEdit__address.text()),
    )
    view = WebView(help_site=lambda: "http://localhost:48626/")
    try:
        view.show()
        app.processEvents()
        assert loads == [expected]
    finally:
        view.close()
    # Closing rewrites the file: the stale key is dropped, a real one is retained.
    stored = json.loads(config.read_text(encoding="utf-8"))
    assert (keys.Name.WebUI.url_addr in stored) is kept


@pytest.mark.parametrize(
    ("url", "loopback"),
    [
        ("http://127.0.0.1:9547/", True),
        ("http://127.0.1.1:8000/", True),
        ("http://localhost:48626/", True),
        ("http://[::1]:9547/", True),
        ("https://forums.odforce.net/", False),
        ("", False),
        (None, False),
    ],
)
def test_is_loopback(url: Any, loopback: bool) -> None:
    from widgets.web_view.web_ui_settings import _is_loopback

    assert _is_loopback(url) is loopback


def test_playback_does_not_require_ffmpeg(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Double-click plays through QMediaPlayer, which never shells out to FFmpeg.

    The gate used to sit on this path, so an unset FFmpeg directory blocked
    playback of videos that already existed.
    """
    from types import SimpleNamespace

    from main import IndividualHDA
    from model import ihda_record_model
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    monkeypatch.setattr(Preference, "is_valid_ffmpeg_dirpath", lambda self: False)

    video = tmp_path / "asset_v1.0.mp4"
    video.write_bytes(b"not really a movie")

    panel = IndividualHDA()
    try:
        assert not panel._preference.is_ffmpeg_valid
        played: list[list[pathlib.Path]] = []
        monkeypatch.setattr(
            panel._video_player,
            "play_after_add_playlist",
            lambda filepath_lst: played.append(filepath_lst),
        )
        # The test environment has no library selected; only latest_video is used.
        panel.session.repository = SimpleNamespace(
            latest_video=lambda asset_id, version: video
        )
        roles = {
            ihda_record_model.RecordModel.record_data_role: SimpleNamespace(
                node_ver="1.0"
            ),
            ihda_record_model.RecordModel.hda_id_role: 1,
            ihda_record_model.RecordModel.name_role: "asset",
        }
        index = SimpleNamespace(isValid=lambda: True, data=roles.get)

        panel.selection._slot_hda_record_double_clicked(index)

        assert played == [[video]]
        assert panel.stackedWidget__whole.currentWidget() is panel.page__video_player
    finally:
        panel.close()


def test_path_with_qt_libraries() -> None:
    """Chromium's helper resolves Houdini's Qt DLLs through PATH, or dies.

    QtWebEngineProcess.exe sits in $HFS/qt/bin with no DLLs beside it, so without
    $HFS/bin on PATH it exits with STATUS_DLL_NOT_FOUND and every navigation
    fails. Appending keeps Houdini's bundled codecs from shadowing the libraries
    of other child processes.
    """
    import os

    from widgets.web_view import path_with_qt_libraries

    # No drive letters: os.pathsep is ":" on this platform and would split them.
    houdini = os.path.join("Houdini", "bin")
    other = os.path.join("other", "tools")

    added = path_with_qt_libraries(houdini, other)
    assert added == other + os.pathsep + houdini
    # Appended, never prepended.
    assert added.split(os.pathsep)[-1] == houdini
    # Idempotent: a second panel must not keep growing PATH.
    assert path_with_qt_libraries(houdini, added) is None
    assert path_with_qt_libraries(houdini, "") == houdini
    # Windows case-insensitivity comes from os.path.normcase and cannot be
    # exercised here: normcase is the identity on POSIX.


def test_playback_state_is_quiet_but_failures_are_logged(
    app: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Buffering and track changes fire several times a second.

    They used to be logged verbatim -- the same string the window title already
    shows -- which flooded the panel on every play. A real failure still has to
    surface, and now does so as an error instead of hiding inside a title.
    """
    import logging

    from widgets.video_player.video_player import VideoPlayer

    widget = VideoPlayer()
    try:
        with caplog.at_level(logging.DEBUG):
            widget._VideoPlayer__set_status_info("Buffering 40%")
            widget._VideoPlayer__set_track_info("clip.mp4")
        assert "Buffering 40%" in widget.windowTitle()
        assert caplog.records == []

        caplog.clear()
        widget._VideoPlayer__player.errorString = lambda: "codec not supported"
        with caplog.at_level(logging.DEBUG):
            widget._VideoPlayer__display_error_msg(None)
        assert [r.levelno for r in caplog.records] == [logging.ERROR]
        assert "codec not supported" in caplog.records[0].getMessage()
    finally:
        widget.close()
