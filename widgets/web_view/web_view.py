from __future__ import annotations

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.23 02:03:49
# modified date:
# description:
import logging
from collections.abc import Callable
from functools import partial
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEngineProfile

from libs import host, log_handler, paths
from libs.houdini_api import HoudiniAPI
from widgets.panel.shortcuts import PANEL, shortcut
from widgets.web_view import web_ui_settings
from widgets.web_view.layout import BOOKMARKS, WebViewLayout
from widgets.web_view.presenter import WebPresenter

BLANK_SITE = "about:blank"


class WebView(QtWidgets.QWidget, WebViewLayout):
    def __init__(
        self,
        help_site: str | Callable[[], str] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.build_ui(self)
        self._presenter = WebPresenter(
            self, HoudiniAPI.global_scale_factor() if host.IS_HOUDINI else 1.0
        )
        self.__ui_settings = web_ui_settings.WebUISettings(window=self)
        self.__help_site = help_site
        self.__initial_load_pending = True
        # Addresses visited this session, offered by the address bar.
        self.__visited = QtCore.QStringListModel(self)
        completer = QtWidgets.QCompleter(self.__visited, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.lineEdit__address.setCompleter(completer)

        self.__load_config()
        self.__connections()
        self._shortcuts = self.__install_shortcuts()
        self.__sync_history_buttons()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if self.__initial_load_pending:
            self.__initial_load_pending = False
            self.__init_set()

    def __help_url(self) -> str | None:
        if callable(self.__help_site):
            self.__help_site = self.__help_site()
        return self.__help_site

    def __init_set(self) -> None:
        self.webEngineView__webview.page().profile().setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        self.__set_init_load()
        self.__load_config()
        self.__load()

    def __connections(self) -> None:
        self.webEngineView__webview.page().titleChanged.connect(self.setWindowTitle)
        self.webEngineView__webview.page().urlChanged.connect(self.__url_changed)
        self.webEngineView__webview.loadStarted.connect(self.__load_started)
        self.webEngineView__webview.loadProgress.connect(self.__load_progress)
        self.webEngineView__webview.loadFinished.connect(self.__load_finished)
        self.webEngineView__webview.page().renderProcessTerminated.connect(
            self.__render_process_terminated
        )
        # No fullScreenRequested handling: the view is embedded in a Houdini pane
        # and has no window of its own to enlarge.
        self.pushButton__back_page.clicked.connect(self.__back)
        self.pushButton__forward_page.clicked.connect(self.__forward)
        self.pushButton__refresh_page.clicked.connect(self.__reload)
        self.pushButton__close_page.clicked.connect(self.__stop)
        self.pushButton__home_page.clicked.connect(self.__init_set)
        self.pushButton__zoomin.clicked.connect(self.__zoom_in)
        self.pushButton__zoomout.clicked.connect(self.__zoom_out)
        self.pushButton__reset_zoom.clicked.connect(self.__reset_zoom)
        self.lineEdit__address.returnPressed.connect(self.__load)
        #
        self.pushButton__retry_page.clicked.connect(self.__reload)
        for bookmark in BOOKMARKS:
            button: QtWidgets.QPushButton = getattr(self, f"pushButton__{bookmark.key}")
            button.clicked.connect(partial(self.__open_bookmark, bookmark.key))

    def __install_shortcuts(self) -> dict[str, QtGui.QShortcut]:
        """Browser keys, scoped to this widget so Houdini keeps its own F5/Ctrl+L."""
        keys = QtGui.QKeySequence
        std = QtGui.QKeySequence.StandardKey
        return {
            "address": shortcut(keys("Ctrl+L"), self, self.focus_address, PANEL),
            "reload": shortcut(std.Refresh, self, self.__reload, PANEL),
            "reload_ctrl": shortcut(keys("Ctrl+R"), self, self.__reload, PANEL),
            "back": shortcut(std.Back, self, self.__back, PANEL),
            "forward": shortcut(std.Forward, self, self.__forward, PANEL),
            "zoom_in": shortcut(std.ZoomIn, self, self.__zoom_in, PANEL),
            "zoom_out": shortcut(std.ZoomOut, self, self.__zoom_out, PANEL),
            "zoom_reset": shortcut(keys("Ctrl+0"), self, self.__reset_zoom, PANEL),
        }

    def focus_address(self) -> None:
        self.lineEdit__address.setFocus()
        self.lineEdit__address.selectAll()

    def visited_urls(self) -> list[str]:
        return list(self.__visited.stringList())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.__ui_settings.save_main_window_geometry()
        self.__ui_settings.save_splitter_status()
        if not self.__initial_load_pending:
            self.__ui_settings.save_cfg_dict_to_file()
        self.webEngineView__webview.page().profile().clearHttpCache()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        event.accept()

    def __load_config(self) -> None:
        if paths.Paths.json_web_filepath.exists():
            self.__ui_settings.load_main_window_geometry()
            self.__ui_settings.load_splitter_status()
            self.__ui_settings.load_cfg_dict_from_file()

    def __set_init_load(self) -> None:
        self.lineEdit__address.setText(
            self.__help_url()
            or "https://www.youtube.com/channel/UCy4fuTNjIPeKPB4hacaP_6A?view_as=subscriber"
        )

    def __load(self, url: str | None = None) -> None:
        address = QtCore.QUrl.fromUserInput(
            self.lineEdit__address.text() if url is None else url
        )
        if address.isValid():
            self.webEngineView__webview.load(address)

    @QtCore.Slot()
    def __load_started(self) -> None:
        self.widget__page_status.hide()
        self.progressBar__load.setValue(0)
        self.progressBar__load.show()
        self.pushButton__close_page.setEnabled(True)

    @QtCore.Slot(int)
    def __load_progress(self, prog: int) -> None:
        self.progressBar__load.setValue(prog)

    @QtCore.Slot(bool)
    def __load_finished(self, status: bool) -> None:
        self.progressBar__load.hide()
        self.pushButton__close_page.setEnabled(False)
        self.__sync_history_buttons()
        if status:
            return
        # requestedUrl(), not url(): a navigation that fails never commits,
        # so url() still reports the page already on screen (about:blank on
        # the first attempt) rather than the address that could not load.
        requested = self.webEngineView__webview.page().requestedUrl().toString()
        self.__show_page_status(f"Could not load {requested}")
        log_handler.LogHandler.log_msg(
            method=logging.error, msg=f"iHDA webview loading ends failed: {requested}"
        )

    def __show_page_status(self, message: str) -> None:
        self.label__page_status.setText(message)
        self.widget__page_status.show()

    @QtCore.Slot(object, int)
    def __render_process_terminated(self, status: Any, exit_code: int) -> None:
        """A dead render process fails every navigation, not just one address.

        Chromium runs the page in a helper process (QtWebEngineProcess). When the
        helper cannot start, loadFinished(False) is all that surfaces, which looks
        identical to an unreachable site. Naming the termination separates the two.
        """
        self.progressBar__load.hide()
        self.__show_page_status(f"The page stopped responding (exit {exit_code})")
        log_handler.LogHandler.log_msg(
            method=logging.error,
            msg=f"iHDA webview render process terminated: {status} (exit {exit_code})",
        )

    def __back(self) -> None:
        self.webEngineView__webview.back()

    def __forward(self) -> None:
        self.webEngineView__webview.forward()

    def __reload(self) -> None:
        self.webEngineView__webview.reload()

    def __stop(self) -> None:
        self.webEngineView__webview.stop()

    def __url_changed(self, url: QtCore.QUrl) -> None:
        address = url.toString()
        self.lineEdit__address.setText(address)
        self.__sync_history_buttons()
        if address != BLANK_SITE and address not in self.__visited.stringList():
            self.__visited.insertRows(0, 1)
            self.__visited.setData(self.__visited.index(0), address)

    def __sync_history_buttons(self) -> None:
        history = self.webEngineView__webview.history()
        self.pushButton__back_page.setEnabled(history.canGoBack())
        self.pushButton__forward_page.setEnabled(history.canGoForward())

    def show_zoom(self, factor: float) -> None:
        self.webEngineView__webview.setZoomFactor(factor)

    def __zoom_in(self) -> None:
        self._presenter.zoom(self.webEngineView__webview.zoomFactor(), 1.1)

    def __zoom_out(self) -> None:
        self._presenter.zoom(self.webEngineView__webview.zoomFactor(), 0.5)

    def __reset_zoom(self) -> None:
        self._presenter.reset_zoom()

    def __open_bookmark(self, key: str) -> None:
        url = next(b.url for b in BOOKMARKS if b.key == key)
        if url is None:  # the help bookmark: Houdini's per-session help server
            url = self.__help_url() or BLANK_SITE
        self.__load(url=url)
