"""Code-built WebView layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import (
    QCoreApplication,
    QSize,
    Qt,
    QUrl,
)
from PySide6.QtGui import (
    QCursor,
    QIcon,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import icons_rc  # noqa: F401 (register bundled icons)
from libs.ui_icons import Icon
from widgets.layout_helpers import make_font
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

from . import web_view_icons_rc  # noqa: F401 (register bundled icons)


def _translate(text: str) -> str:
    return QCoreApplication.translate("Form__web", text)


class Bookmark(NamedTuple):
    key: str  # widget attribute is pushButton__<key>
    icon: str
    tooltip: str
    url: str | None  # None: resolved by the widget (Houdini help server)


BOOKMARKS: tuple[Bookmark, ...] = (
    Bookmark("help", "houdini_logo.png", "Houdini Help", None),
    Bookmark("sidefx", "news.png", "SideFX Learn", "https://www.sidefx.com/learn/"),
    Bookmark("odforce", "odforce.png", "odforce forums", "https://forums.odforce.net/"),
    Bookmark("google", "google.png", "Google", "https://www.google.com/"),
    Bookmark(
        "translation",
        "ic_g_translate_white.png",
        "Google Translate",
        "https://translate.google.com/?hl=ko&tab=wT1&authuser=0",
    ),
    Bookmark("youtube", "youtube.png", "YouTube", "https://www.youtube.com/"),
    Bookmark("vimeo", "vimeo.png", "Vimeo", "https://vimeo.com/"),
)


class WebViewLayout:
    def build_ui(self, window: QWidget) -> None:
        self._configure_window(window)
        self._build_shell(window)
        self._build_navigation(window)
        self._build_bookmarks_and_address(window)
        self._build_web_content(window)

    def _configure_window(self, window: QWidget) -> None:
        if not window.objectName():
            window.setObjectName("Form__web")
        window.resize(646, 423)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(":/web_view_main/icons/viewport_logo_trans.png"))
        window.setWindowTitle(_translate("iHDA Web View"))

    def _build_shell(self, window: QWidget) -> None:
        self.verticalLayout__web_view = QVBoxLayout(window)
        self.verticalLayout__web_view.setSpacing(1)
        self.verticalLayout__web_view.setObjectName("verticalLayout__web_view")
        self.verticalLayout__web_view.setContentsMargins(0, 0, 0, 0)
        self.splitter__webview_whole_vertical = QSplitter(window)
        self.splitter__webview_whole_vertical.setObjectName(
            "splitter__webview_whole_vertical"
        )
        self.splitter__webview_whole_vertical.setOrientation(Qt.Orientation.Vertical)
        self.splitter__webview_whole_vertical.setHandleWidth(3)
        self.widget__web_controls = QWidget(self.splitter__webview_whole_vertical)
        self.widget__web_controls.setObjectName("widget__web_controls")
        self.verticalLayout__web_controls = QVBoxLayout(self.widget__web_controls)
        self.verticalLayout__web_controls.setSpacing(1)
        self.verticalLayout__web_controls.setObjectName("verticalLayout__web_controls")
        self.verticalLayout__web_controls.setContentsMargins(0, 0, 0, 0)

    def _build_navigation(self, window: QWidget) -> None:
        self.horizontalLayout__web_navigation = QHBoxLayout()
        self.horizontalLayout__web_navigation.setObjectName(
            "horizontalLayout__web_navigation"
        )
        self.horizontalLayout__web_navigation.setContentsMargins(3, -1, 3, -1)
        self.pushButton__back_page = QPushButton(self.widget__web_controls)
        self.pushButton__back_page.setObjectName("pushButton__back_page")
        self.pushButton__back_page.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__back_page.setIcon(
            QIcon(":/web_view_main/icons/ic_arrow_back_white.png")
        )
        self.pushButton__back_page.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__back_page.setFlat(True)
        self.pushButton__back_page.setToolTip(_translate("Back (Alt+Left)"))
        self.pushButton__back_page.setStatusTip(_translate("back page"))
        self.pushButton__back_page.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__back_page)
        self.pushButton__forward_page = QPushButton(self.widget__web_controls)
        self.pushButton__forward_page.setObjectName("pushButton__forward_page")
        self.pushButton__forward_page.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__forward_page.setIcon(
            QIcon(":/web_view_main/icons/ic_arrow_forward_white.png")
        )
        self.pushButton__forward_page.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__forward_page.setFlat(True)
        self.pushButton__forward_page.setToolTip(_translate("Forward (Alt+Right)"))
        self.pushButton__forward_page.setStatusTip(_translate("forward page"))
        self.pushButton__forward_page.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__forward_page)
        self.pushButton__refresh_page = QPushButton(self.widget__web_controls)
        self.pushButton__refresh_page.setObjectName("pushButton__refresh_page")
        self.pushButton__refresh_page.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__refresh_page.setIcon(
            QIcon(":/web_view_main/icons/ic_refresh_white.png")
        )
        self.pushButton__refresh_page.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__refresh_page.setFlat(True)
        self.pushButton__refresh_page.setToolTip(_translate("Reload (F5)"))
        self.pushButton__refresh_page.setStatusTip(_translate("refresh page"))
        self.pushButton__refresh_page.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__refresh_page)
        self.pushButton__close_page = QPushButton(self.widget__web_controls)
        self.pushButton__close_page.setObjectName("pushButton__close_page")
        self.pushButton__close_page.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__close_page.setIcon(QIcon(Icon.IC_CLEAR_WHITE))
        self.pushButton__close_page.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__close_page.setFlat(True)
        self.pushButton__close_page.setToolTip(_translate("Stop loading"))
        self.pushButton__close_page.setStatusTip(_translate("stop loading"))
        self.pushButton__close_page.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__close_page)
        self.pushButton__home_page = QPushButton(self.widget__web_controls)
        self.pushButton__home_page.setObjectName("pushButton__home_page")
        self.pushButton__home_page.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__home_page.setIcon(
            QIcon(":/web_view_main/icons/ic_home_white.png")
        )
        self.pushButton__home_page.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__home_page.setFlat(True)
        self.pushButton__home_page.setToolTip(_translate("Home"))
        self.pushButton__home_page.setStatusTip(_translate("home page"))
        self.pushButton__home_page.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__home_page)
        self.spacer__web_navigation = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__web_navigation.addItem(self.spacer__web_navigation)
        self.pushButton__zoomin = QPushButton(self.widget__web_controls)
        self.pushButton__zoomin.setObjectName("pushButton__zoomin")
        self.pushButton__zoomin.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__zoomin.setIcon(
            QIcon(":/web_view_main/icons/ic_zoom_in_white.png")
        )
        self.pushButton__zoomin.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        self.pushButton__zoomin.setFlat(True)
        self.pushButton__zoomin.setToolTip(_translate("Zoom in (Ctrl+=)"))
        self.pushButton__zoomin.setStatusTip(_translate("zoom in"))
        self.pushButton__zoomin.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__zoomin)
        self.pushButton__zoomout = QPushButton(self.widget__web_controls)
        self.pushButton__zoomout.setObjectName("pushButton__zoomout")
        self.pushButton__zoomout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__zoomout.setIcon(
            QIcon(":/web_view_main/icons/ic_zoom_out_white.png")
        )
        self.pushButton__zoomout.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__zoomout.setFlat(True)
        self.pushButton__zoomout.setToolTip(_translate("Zoom out (Ctrl+-)"))
        self.pushButton__zoomout.setStatusTip(_translate("zoom out"))
        self.pushButton__zoomout.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__zoomout)
        self.pushButton__reset_zoom = QPushButton(self.widget__web_controls)
        self.pushButton__reset_zoom.setObjectName("pushButton__reset_zoom")
        self.pushButton__reset_zoom.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__reset_zoom.setIcon(QIcon(Icon.IC_RESTORE_PAGE_WHITE))
        self.pushButton__reset_zoom.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.pushButton__reset_zoom.setFlat(True)
        self.pushButton__reset_zoom.setToolTip(_translate("Reset zoom (Ctrl+0)"))
        self.pushButton__reset_zoom.setStatusTip(_translate("reset zoom"))
        self.pushButton__reset_zoom.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__reset_zoom)
        self.verticalLayout__web_controls.addLayout(
            self.horizontalLayout__web_navigation
        )

    def _build_bookmarks_and_address(self, window: QWidget) -> None:
        self.horizontalLayout__web_address = QHBoxLayout()
        self.horizontalLayout__web_address.setObjectName(
            "horizontalLayout__web_address"
        )
        self.horizontalLayout__web_address.setContentsMargins(3, -1, 3, 2)
        self.horizontalLayout__web_bookmarks = QHBoxLayout()
        self.horizontalLayout__web_bookmarks.setObjectName(
            "horizontalLayout__web_bookmarks"
        )
        for bookmark in BOOKMARKS:
            button = QPushButton(self.widget__web_controls)
            button.setObjectName(f"pushButton__{bookmark.key}")
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            button.setIcon(QIcon(f":/web_view_main/icons/{bookmark.icon}"))
            button.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
            button.setFlat(True)
            button.setToolTip(_translate(bookmark.tooltip))
            button.setStatusTip(_translate(bookmark.tooltip))
            setattr(self, f"pushButton__{bookmark.key}", button)
            self.horizontalLayout__web_bookmarks.addWidget(button)
        self.horizontalLayout__web_address.addLayout(
            self.horizontalLayout__web_bookmarks
        )
        self.lineEdit__address = QLineEdit(self.widget__web_controls)
        self.lineEdit__address.setObjectName("lineEdit__address")
        self.lineEdit__address.setClearButtonEnabled(True)
        self.lineEdit__address.setPlaceholderText(_translate("Search or enter address"))
        self.lineEdit__address.setToolTip(_translate("Address (Ctrl+L)"))
        self.lineEdit__address.setText(
            _translate("https://www.google.co.kr/?gws_rd=ssl")
        )
        self.horizontalLayout__web_address.addWidget(self.lineEdit__address)
        self.verticalLayout__web_controls.addLayout(self.horizontalLayout__web_address)
        # A thin bar under the address: the only progress feedback the page gives.
        self.progressBar__load = QProgressBar(self.widget__web_controls)
        self.progressBar__load.setObjectName("progressBar__load")
        self.progressBar__load.setRange(0, 100)
        self.progressBar__load.setTextVisible(False)
        self.progressBar__load.setFixedHeight(3)
        self.progressBar__load.hide()
        self.verticalLayout__web_controls.addWidget(self.progressBar__load)
        self.splitter__webview_whole_vertical.addWidget(self.widget__web_controls)

    def _build_web_content(self, window: QWidget) -> None:
        self.widget__web_content = QWidget(self.splitter__webview_whole_vertical)
        self.widget__web_content.setObjectName("widget__web_content")
        self.verticalLayout__web_content = QVBoxLayout(self.widget__web_content)
        self.verticalLayout__web_content.setSpacing(1)
        self.verticalLayout__web_content.setObjectName("verticalLayout__web_content")
        self.verticalLayout__web_content.setContentsMargins(0, 0, 0, 0)
        # Shown instead of Chromium's blank page when a load fails.
        self.widget__page_status = QWidget(self.widget__web_content)
        self.widget__page_status.setObjectName("widget__page_status")
        self.horizontalLayout__page_status = QHBoxLayout(self.widget__page_status)
        self.horizontalLayout__page_status.setContentsMargins(6, 2, 6, 2)
        self.label__page_status = QLabel(self.widget__page_status)
        self.label__page_status.setObjectName("label__page_status")
        self.label__page_status.setWordWrap(True)
        self.horizontalLayout__page_status.addWidget(self.label__page_status, 1)
        self.pushButton__retry_page = QPushButton(
            _translate("Reload"), self.widget__page_status
        )
        self.pushButton__retry_page.setObjectName("pushButton__retry_page")
        self.pushButton__retry_page.setIcon(
            QIcon(":/web_view_main/icons/ic_refresh_white.png")
        )
        self.horizontalLayout__page_status.addWidget(self.pushButton__retry_page)
        self.widget__page_status.hide()
        self.verticalLayout__web_content.addWidget(self.widget__page_status)
        self.webEngineView__webview = QWebEngineView(self.widget__web_content)
        self.webEngineView__webview.setObjectName("webEngineView__webview")
        self.webEngineView__webview.setUrl(QUrl("about:blank"))
        self.verticalLayout__web_content.addWidget(self.webEngineView__webview)
        self.splitter__webview_whole_vertical.addWidget(self.widget__web_content)
        self.verticalLayout__web_view.addWidget(self.splitter__webview_whole_vertical)
