"""Contracts for the first code-UI feature and its eventual remote boundary."""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore, QtTest, QtWidgets
from test_models import asset

from libs.asset_search import AssetSearch
from libs.browser_search import RepositoryAssetSearch, SearchRequest
from libs.repository import LibraryUnavailable
from model.ihda_list_model import ListModel
from model.ihda_list_proxy_model import ListProxyModel
from model.ihda_table_model import TableModel
from model.ihda_table_proxy_model import TableProxyModel
from widgets.asset_browser.presenter import AssetBrowserPresenter
from widgets.asset_browser.view import AssetBrowserView


class RecordingView:
    def __init__(self) -> None:
        self.busy = False
        self.error = ""
        self.ids = frozenset({99})
        self.local: SearchRequest | None = None

    def show_busy(self, busy: bool) -> None:
        self.busy = busy

    def show_error(self, message: str) -> None:
        self.error = message

    def show_results(self, ids: frozenset[int]) -> None:
        self.ids = ids

    def filter_text(self, request: SearchRequest) -> None:
        self.local = request


class Gateway:
    def __init__(self) -> None:
        self.requests: list[SearchRequest] = []
        self.ids = [1, 2]

    def search(self, request: SearchRequest, cancel: threading.Event) -> list[int]:
        self.requests.append(request)
        if request.text == "fail":
            raise LibraryUnavailable("server unavailable")
        return self.ids


class ImmediateExecutor:
    """Exercise presentation without a QApplication or a real backend."""

    presenter: AssetBrowserPresenter

    def submit(self, text: str, search: Any) -> None:
        try:
            self.presenter.results(frozenset(search(text, threading.Event())))
        except Exception as error:
            self.presenter.failed(error)

    def cancel(self) -> None:
        pass

    def drain(self) -> None:
        pass


def test_presenter_search_refresh_failure_and_empty_query() -> None:
    view, gateway, executor = RecordingView(), Gateway(), ImmediateExecutor()
    presenter = AssetBrowserPresenter(view, executor, gateway)
    executor.presenter = presenter
    presenter.search(SearchRequest("  water  ", "Tags", True))
    assert gateway.requests == [SearchRequest("water", "Tags", True)]
    assert view.ids == {1, 2} and not view.busy
    gateway.ids = [2]
    presenter.search(SearchRequest("water", "Tags", True))
    assert view.ids == {2}
    presenter.search(SearchRequest("fail"))
    assert view.ids == {2} and "server unavailable" in view.error
    assert not view.busy
    calls = len(gateway.requests)
    presenter.search(SearchRequest("  ", "All"))
    assert view.local == SearchRequest("", "All") and not view.error
    assert len(gateway.requests) == calls
    presenter.close()
    presenter.search(SearchRequest("after close"))
    assert len(gateway.requests) == calls


def test_search_gateway_preserves_repository_arguments_and_cancellation() -> None:
    class Repository:
        def search_asset_ids(self, query: str, **kwargs: Any) -> list[int]:
            assert query == "tag:water"
            assert kwargs == {"field": "All", "case_sensitive": True, "cancel": cancel}
            return [7]

    cancel = threading.Event()
    gateway = RepositoryAssetSearch(Repository())
    assert gateway.search(SearchRequest("tag:water", "All", True), cancel) == [7]


@pytest.mark.parametrize(
    "transition", ["new_query", "invalidate", "empty", "library", "close"]
)
def test_delayed_response_cannot_overwrite_new_state(app: Any, transition: str) -> None:
    entered, release = threading.Event(), threading.Event()
    view = RecordingView()
    runner = AssetSearch(app)

    class SlowGateway:
        def search(self, request: SearchRequest, cancel: threading.Event) -> list[int]:
            entered.set()
            release.wait(3)
            return [8]  # simulate an HTTP response that ignored cancellation

    presenter = AssetBrowserPresenter(view, runner, SlowGateway())
    runner.results.connect(presenter.results)
    runner.failed.connect(presenter.failed)
    try:
        presenter.search(SearchRequest("old"))
        assert entered.wait(2)
        if transition == "new_query":
            presenter.change_gateway(Gateway())
            presenter.search(SearchRequest("new"))
        elif transition == "invalidate":
            presenter.invalidate()  # user typed, debounce has not fired yet
        elif transition == "empty":
            presenter.search(SearchRequest())
        elif transition == "library":
            presenter.change_gateway(Gateway())
        else:
            release.set()
            presenter.close()
        release.set()
        for _ in range(200):
            app.processEvents()
            if not runner.busy:
                break
            QtTest.QTest.qWait(5)
        app.processEvents()
        assert view.ids == (
            frozenset({1, 2}) if transition == "new_query" else frozenset({99})
        )
        assert not view.busy
    finally:
        release.set()
        presenter.close()
        runner.deleteLater()


def test_browser_models_filters_selection_and_mode(app: Any, tmp_path: Path) -> None:
    base = asset(tmp_path)
    rows = [
        {**base, "hda_id": 1, "hda_name": "Water", "is_favorite_hda": True},
        {**base, "hda_id": 2, "hda_name": "Fire", "is_favorite_hda": False},
    ]
    view = AssetBrowserView()
    first, second = ListModel(items=rows), TableModel(items=rows)
    lp, tp = ListProxyModel(), TableProxyModel()
    lp.setSourceModel(first)
    tp.setSourceModel(second)
    view.bind_models(lp, tp)
    selected = []
    view.asset_selected.connect(selected.append)
    view.show_results(frozenset({2}))
    assert lp.rowCount() == tp.rowCount() == 1 and view.label__hda_count.text() == "1"
    view.listView__hda.setCurrentIndex(lp.index(0, 0))
    assert selected[-1] == 2
    view.pushButton__table_mode.click()
    assert (
        view.stackedWidget__hda.currentIndex() == 1
        and not view.pushButton__icon_mode.isChecked()
    )
    view.tableView__hda.setCurrentIndex(tp.index(0, 0))
    assert selected[-1] == 2
    view.filter_text(SearchRequest("w*", "Name", False))
    assert lp.index(0, 0).data(lp.id_role) == 1
    assert lp.rowCount() == tp.rowCount() == 1
    view.filter_text(SearchRequest())
    selection = view.listView__hda.selectionModel()
    selection.select(lp.index(0, 0), QtCore.QItemSelectionModel.SelectionFlag.Select)
    selection.select(lp.index(1, 0), QtCore.QItemSelectionModel.SelectionFlag.Select)
    assert selected[-1] == 2
    view.listView__hda.clicked.emit(lp.index(1, 0))
    assert selected[-1] == 2  # clicked ID, not the first item in a multi-selection
    for proxy in (lp, tp):
        proxy.is_favorite_nodes = True
    assert lp.rowCount() == tp.rowCount() == 1 and view.label__hda_count.text() == "1"
    view.show_results(frozenset({2}))
    assert lp.rowCount() == tp.rowCount() == 0
    view.close()
    view.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_ui_shell_and_compatibility_preserve_names(app: Any) -> None:
    from widgets.asset_browser.integration import AssetBrowserIntegration
    from widgets.panel.layout import MainWindowLayout

    class Shell(QtWidgets.QMainWindow, MainWindowLayout):
        _ihda_list_model = None

        def _asset_search_failed_message(self, message: str) -> None:
            pass

    shell = Shell()
    shell.build_ui(shell)
    runner = AssetSearch(shell)
    bridge = AssetBrowserIntegration(shell, runner, RepositoryAssetSearch)
    assert shell.lineEdit__search_hda is bridge.view.lineEdit__search_hda
    assert shell.stackedWidget__hda is bridge.view.stackedWidget__hda
    assert shell.label__hda_count is bridge.view.label__hda_count
    assert (
        shell.findChild(QtWidgets.QSplitter, "splitter__ihda_whole_vertical")
        is bridge.view.splitter__ihda_whole_vertical
    )
    # Remaining editors use descriptive names and keep their parent relationships.
    assert shell.widget__note_editor is shell.textEdit__note.parentWidget()
    assert shell.widget__tag_editor is shell.textEdit__tag.parentWidget()
    # Saved splitter bytes remain compatible with the former two-pane splitter.
    old_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
    old_splitter.addWidget(QtWidgets.QWidget())
    old_splitter.addWidget(QtWidgets.QWidget())
    old_splitter.setSizes([70, 350])
    old_splitter.setHandleWidth(7)
    old_splitter.setChildrenCollapsible(False)
    assert bridge.view.splitter__ihda_whole_vertical.restoreState(
        old_splitter.saveState()
    )
    assert bridge.view.splitter__ihda_whole_vertical.handleWidth() == 7
    assert not bridge.view.splitter__ihda_whole_vertical.childrenCollapsible()
    old_splitter.close()
    bridge.close()
    shell.close()
    shell.deleteLater()
    old_splitter.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_presenter_and_search_contract_import_without_qt_or_host() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import builtins
original = builtins.__import__
def restricted(name, *args, **kwargs):
    if name.split('.')[0] in ('PySide6', 'hou', 'main', 'sqlite3'):
        raise AssertionError('Unexpected dependency: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = restricted
from libs.browser_search import SearchRequest, RepositoryAssetSearch
from widgets.asset_browser.presenter import AssetBrowserPresenter
""",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )
