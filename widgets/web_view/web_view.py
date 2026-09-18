from __future__ import annotations

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.23 02:03:49
# modified date:
# description:
import logging
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEngineFullScreenRequest, QWebEngineProfile

from libs import host, log_handler, paths
from libs.houdini_api import HoudiniAPI
from widgets.web_view import web_ui_settings
from widgets.web_view.layout import WebViewLayout
from widgets.web_view.presenter import WebPresenter


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
        self.__blank_site = "about:blank"
        self.__help_site = help_site
        self.__initial_load_pending = True

        self.__load_config()
        self.__connections()

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
        # self.webEngineView__webview.page().fullScreenRequested.connect(self.__full_screen)
        #
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
        self.pushButton__sidefx.clicked.connect(
            lambda: self.__load(url=self.__urls()["sidefx"])
        )
        self.pushButton__odforce.clicked.connect(
            lambda: self.__load(url=self.__urls()["odforce"])
        )
        self.pushButton__google.clicked.connect(
            lambda: self.__load(url=self.__urls()["google"])
        )
        self.pushButton__translation.clicked.connect(
            lambda: self.__load(url=self.__urls()["translation"])
        )
        self.pushButton__youtube.clicked.connect(
            lambda: self.__load(url=self.__urls()["youtube"])
        )
        self.pushButton__vimeo.clicked.connect(
            lambda: self.__load(url=self.__urls()["vimeo"])
        )
        self.pushButton__help.clicked.connect(
            lambda: self.__load(url=self.__urls()["help"])
        )

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

    def __full_screen(self, request: Any) -> None:
        req = QWebEngineFullScreenRequest(request)
        req.accept()

    @QtCore.Slot()
    def __load_started(self) -> None:
        log_handler.LogHandler.log_msg(
            method=logging.info, msg="start loading iHDA webview"
        )

    @QtCore.Slot(int)
    def __load_progress(self, prog: int) -> None:
        log_handler.LogHandler.log_msg(
            method=logging.info, msg=f"loading progress: {prog}"
        )

    @QtCore.Slot(bool)
    def __load_finished(self, status: bool) -> None:
        if status:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="iHDA webview loading ends"
            )
        else:
            # requestedUrl(), not url(): a navigation that fails never commits,
            # so url() still reports the page already on screen (about:blank on
            # the first attempt) rather than the address that could not load.
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg=f"iHDA webview loading ends failed: "
                f"{self.webEngineView__webview.page().requestedUrl().toString()}",
            )

    @QtCore.Slot(object, int)
    def __render_process_terminated(self, status: Any, exit_code: int) -> None:
        """A dead render process fails every navigation, not just one address.

        Chromium runs the page in a helper process (QtWebEngineProcess). When the
        helper cannot start, loadFinished(False) is all that surfaces, which looks
        identical to an unreachable site. Naming the termination separates the two.
        """
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
        self.lineEdit__address.setText(url.toString())

    def __set_view_by_zoom_factor(self, zoom_factor: Any) -> None:
        if host.IS_HOUDINI:
            self.webEngineView__webview.setZoomFactor(
                zoom_factor * HoudiniAPI.global_scale_factor()
            )
        else:
            self.webEngineView__webview.setZoomFactor(zoom_factor)
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg=f"current zoom factor of the webview: {self.curt_zoom_value}",
        )

    def show_zoom(self, factor: float) -> None:
        self.webEngineView__webview.setZoomFactor(factor)

    def __zoom_in(self) -> None:
        self._presenter.zoom(self.webEngineView__webview.zoomFactor(), 1.1)

    def __zoom_out(self) -> None:
        self._presenter.zoom(self.webEngineView__webview.zoomFactor(), 0.5)

    def __reset_zoom(self) -> None:
        self._presenter.reset_zoom()

    @property
    def curt_zoom_value(self) -> int:
        percent = int(self.webEngineView__webview.zoomFactor() * 100)
        return percent

    @staticmethod
    def __maximum_zoom_factor() -> float:
        if host.IS_HOUDINI:
            return 5 * HoudiniAPI.global_scale_factor()
        else:
            return 5

    @staticmethod
    def __minimum_zoom_factor() -> float:
        if host.IS_HOUDINI:
            return 0.25 * HoudiniAPI.global_scale_factor()
        else:
            return 0.25

    def __urls(self) -> dict[str, Any]:
        url_dat = {
            "sidefx": "https://www.sidefx.com/learn/",
            "odforce": "https://forums.odforce.net/",
            "google": "https://www.google.com/",
            "translation": "https://translate.google.com/?hl=ko&tab=wT1&authuser=0",
            "youtube": "https://www.youtube.com/",
            "vimeo": "https://vimeo.com/",
            "help": self.__help_url() or self.__blank_site,
        }
        return url_dat
