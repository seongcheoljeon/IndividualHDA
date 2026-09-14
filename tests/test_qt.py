from __future__ import annotations
import pathlib

from typing import Any
from pathlib import Path
import sys
import pytest
from PySide6 import QtCore, QtWidgets
from libs.drag_payload import encode_payload, decode_payload
from libs.qt_helpers import wildcard_expression
from libs.process_job import ProcessJob


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
        ([sys.executable, "-c", 'print("한글")'], 0),
        (["/nonexistent/ihda-executable"], -1),
    ]:
        loop = QtCore.QEventLoop()
        result = []
        job = ProcessJob(command)
        job.finished.connect(
            lambda code, output: (result.append((code, output)), loop.quit())
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
            assert "한글" in result[0][1]


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
    assert panel.comboBox__search_type.count() == 3
    panel.close()


def test_panel_with_saved_library(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    import public
    from widgets.preference.preference import Preference
    from widgets.web_view.web_view import WebView
    from libs.sqlite3_db_api import SQLite3DatabaseAPI
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
    panel = IndividualHDA()
    model = panel._ihda_list_proxy_model
    assert model.rowCount() == 1
    panel.lineEdit__search_hda.setText("missing")
    app.processEvents()
    assert model.rowCount() == 0
    panel.lineEdit__search_hda.setText("Water")
    app.processEvents()
    assert model.rowCount() == 1
    panel._open_library_tools(4)
    dialog = panel._library_manager
    assert dialog.tabs.count() == 6 and dialog.tabs.currentIndex() == 4
    dialog.close()
    app.processEvents()
    assert panel._library_manager is None
    panel._open_library_tools(0)
    panel._library_manager._search()
    panel.close()
    app.processEvents()


@pytest.mark.parametrize("outcome", ["success", "failure", "close", "host_destroy"])
def test_panel_background_job_lifecycle(
    app: Any, monkeypatch: pytest.MonkeyPatch, outcome: Any
) -> None:
    """Inherited Qt slots must return to the GUI thread and defer close safely."""
    from threading import Event
    from PySide6 import QtTest
    from widgets.web_view.web_view import WebView
    from main import IndividualHDA

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
            assert not panel.close()
            assert panel._close_requested and not panel._closing
        release.set()
        if outcome == "host_destroy":
            panel.shutdown_for_host()
            assert panel._host_destroying and panel._closing
        for _ in range(500):
            app.processEvents()
            if panel._tasks.file_job is None and (outcome != "close" or panel._closing):
                break
            QtTest.QTest.qWait(10)
        assert panel._tasks.file_job is None
        assert worker_threads and worker_threads[0] != app.thread()
        assert results == ([] if outcome == "failure" else [("finished", app.thread())])
        assert panel.centralwidget.isEnabled()
        if outcome == "close":
            assert panel._closing
    finally:
        release.set()
        if panel._tasks.file_job is not None:
            panel._tasks.file_job.wait(6000)
            app.processEvents()
        panel.close()


def test_help_server_is_resolved_only_when_web_view_is_shown(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from widgets.web_view.web_view import WebView
    import public

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
