"""Code-built WebView layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

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
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from widgets.layout_helpers import make_font

from . import web_view_icons_rc  # noqa: F401 (register bundled icons)


def _translate(text: str) -> str:
    return QCoreApplication.translate("Form__web", text)


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
        self.pushButton__back_page.setIconSize(QSize(20, 20))
        self.pushButton__back_page.setFlat(True)
        self.pushButton__back_page.setToolTip(_translate("Back Page"))
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
        self.pushButton__forward_page.setIconSize(QSize(20, 20))
        self.pushButton__forward_page.setFlat(True)
        self.pushButton__forward_page.setToolTip(_translate("Forward Page"))
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
        self.pushButton__refresh_page.setIconSize(QSize(20, 20))
        self.pushButton__refresh_page.setFlat(True)
        self.pushButton__refresh_page.setToolTip(_translate("Refresh Page"))
        self.pushButton__refresh_page.setStatusTip(_translate("refresh page"))
        self.pushButton__refresh_page.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__refresh_page)
        self.pushButton__close_page = QPushButton(self.widget__web_controls)
        self.pushButton__close_page.setObjectName("pushButton__close_page")
        self.pushButton__close_page.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__close_page.setIcon(
            QIcon(":/web_view_main/icons/ic_close_white.png")
        )
        self.pushButton__close_page.setIconSize(QSize(20, 20))
        self.pushButton__close_page.setFlat(True)
        self.pushButton__close_page.setToolTip(_translate("Close Page"))
        self.pushButton__close_page.setStatusTip(_translate("close page"))
        self.pushButton__close_page.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__close_page)
        self.pushButton__home_page = QPushButton(self.widget__web_controls)
        self.pushButton__home_page.setObjectName("pushButton__home_page")
        self.pushButton__home_page.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__home_page.setIcon(
            QIcon(":/web_view_main/icons/ic_home_white.png")
        )
        self.pushButton__home_page.setIconSize(QSize(20, 20))
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
        self.pushButton__zoomin.setIconSize(QSize(20, 20))
        self.pushButton__zoomin.setFlat(True)
        self.pushButton__zoomin.setToolTip(_translate("zoom in"))
        self.pushButton__zoomin.setStatusTip(_translate("zoom in"))
        self.pushButton__zoomin.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__zoomin)
        self.pushButton__zoomout = QPushButton(self.widget__web_controls)
        self.pushButton__zoomout.setObjectName("pushButton__zoomout")
        self.pushButton__zoomout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__zoomout.setIcon(
            QIcon(":/web_view_main/icons/ic_zoom_out_white.png")
        )
        self.pushButton__zoomout.setIconSize(QSize(20, 20))
        self.pushButton__zoomout.setFlat(True)
        self.pushButton__zoomout.setToolTip(_translate("zoom out"))
        self.pushButton__zoomout.setStatusTip(_translate("zoom out"))
        self.pushButton__zoomout.setText("")
        self.horizontalLayout__web_navigation.addWidget(self.pushButton__zoomout)
        self.pushButton__reset_zoom = QPushButton(self.widget__web_controls)
        self.pushButton__reset_zoom.setObjectName("pushButton__reset_zoom")
        self.pushButton__reset_zoom.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__reset_zoom.setIcon(
            QIcon(":/web_view_main/icons/ic_search_white.png")
        )
        self.pushButton__reset_zoom.setIconSize(QSize(20, 20))
        self.pushButton__reset_zoom.setFlat(True)
        self.pushButton__reset_zoom.setToolTip(_translate("reset zoom"))
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
        self.pushButton__help = QPushButton(self.widget__web_controls)
        self.pushButton__help.setObjectName("pushButton__help")
        self.pushButton__help.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__help.setIcon(QIcon(":/web_view_main/icons/houdini_logo.png"))
        self.pushButton__help.setIconSize(QSize(20, 20))
        self.pushButton__help.setFlat(True)
        self.pushButton__help.setToolTip(_translate("Help"))
        self.pushButton__help.setStatusTip(_translate("Houdini Help"))
        self.pushButton__help.setText("")
        self.horizontalLayout__web_bookmarks.addWidget(self.pushButton__help)
        self.pushButton__sidefx = QPushButton(self.widget__web_controls)
        self.pushButton__sidefx.setObjectName("pushButton__sidefx")
        self.pushButton__sidefx.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__sidefx.setIcon(QIcon(":/web_view_main/icons/news.png"))
        self.pushButton__sidefx.setIconSize(QSize(20, 20))
        self.pushButton__sidefx.setFlat(True)
        self.pushButton__sidefx.setToolTip(_translate("SideFX"))
        self.pushButton__sidefx.setStatusTip(_translate("go to sidefx"))
        self.pushButton__sidefx.setText("")
        self.horizontalLayout__web_bookmarks.addWidget(self.pushButton__sidefx)
        self.pushButton__odforce = QPushButton(self.widget__web_controls)
        self.pushButton__odforce.setObjectName("pushButton__odforce")
        self.pushButton__odforce.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__odforce.setIcon(QIcon(":/web_view_main/icons/odforce.png"))
        self.pushButton__odforce.setIconSize(QSize(20, 20))
        self.pushButton__odforce.setFlat(True)
        self.pushButton__odforce.setToolTip(_translate("ODFORCE"))
        self.pushButton__odforce.setStatusTip(_translate("home page"))
        self.pushButton__odforce.setText("")
        self.horizontalLayout__web_bookmarks.addWidget(self.pushButton__odforce)
        self.pushButton__google = QPushButton(self.widget__web_controls)
        self.pushButton__google.setObjectName("pushButton__google")
        self.pushButton__google.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__google.setIcon(QIcon(":/web_view_main/icons/google.png"))
        self.pushButton__google.setIconSize(QSize(20, 20))
        self.pushButton__google.setFlat(True)
        self.pushButton__google.setToolTip(_translate("Google"))
        self.pushButton__google.setStatusTip(_translate("go to google"))
        self.pushButton__google.setText("")
        self.horizontalLayout__web_bookmarks.addWidget(self.pushButton__google)
        self.pushButton__translation = QPushButton(self.widget__web_controls)
        self.pushButton__translation.setObjectName("pushButton__translation")
        self.pushButton__translation.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__translation.setIcon(
            QIcon(":/web_view_main/icons/ic_g_translate_white.png")
        )
        self.pushButton__translation.setIconSize(QSize(20, 20))
        self.pushButton__translation.setFlat(True)
        self.pushButton__translation.setToolTip(_translate("Translation"))
        self.pushButton__translation.setStatusTip(_translate("translation"))
        self.pushButton__translation.setText("")
        self.horizontalLayout__web_bookmarks.addWidget(self.pushButton__translation)
        self.pushButton__youtube = QPushButton(self.widget__web_controls)
        self.pushButton__youtube.setObjectName("pushButton__youtube")
        self.pushButton__youtube.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__youtube.setIcon(QIcon(":/web_view_main/icons/youtube.png"))
        self.pushButton__youtube.setIconSize(QSize(20, 20))
        self.pushButton__youtube.setFlat(True)
        self.pushButton__youtube.setToolTip(_translate("Youtube"))
        self.pushButton__youtube.setStatusTip(_translate("go to youtube"))
        self.pushButton__youtube.setText("")
        self.horizontalLayout__web_bookmarks.addWidget(self.pushButton__youtube)
        self.pushButton__vimeo = QPushButton(self.widget__web_controls)
        self.pushButton__vimeo.setObjectName("pushButton__vimeo")
        self.pushButton__vimeo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton__vimeo.setIcon(QIcon(":/web_view_main/icons/vimeo.png"))
        self.pushButton__vimeo.setIconSize(QSize(20, 20))
        self.pushButton__vimeo.setFlat(True)
        self.pushButton__vimeo.setToolTip(_translate("Vimeo"))
        self.pushButton__vimeo.setStatusTip(_translate("go to vimeo"))
        self.pushButton__vimeo.setText("")
        self.horizontalLayout__web_bookmarks.addWidget(self.pushButton__vimeo)
        self.horizontalLayout__web_address.addLayout(
            self.horizontalLayout__web_bookmarks
        )
        self.lineEdit__address = QLineEdit(self.widget__web_controls)
        self.lineEdit__address.setObjectName("lineEdit__address")
        self.lineEdit__address.setClearButtonEnabled(True)
        self.lineEdit__address.setText(
            _translate("https://www.google.co.kr/?gws_rd=ssl")
        )
        self.horizontalLayout__web_address.addWidget(self.lineEdit__address)
        self.verticalLayout__web_controls.addLayout(self.horizontalLayout__web_address)
        self.splitter__webview_whole_vertical.addWidget(self.widget__web_controls)

    def _build_web_content(self, window: QWidget) -> None:
        self.widget__web_content = QWidget(self.splitter__webview_whole_vertical)
        self.widget__web_content.setObjectName("widget__web_content")
        self.verticalLayout__web_content = QVBoxLayout(self.widget__web_content)
        self.verticalLayout__web_content.setSpacing(1)
        self.verticalLayout__web_content.setObjectName("verticalLayout__web_content")
        self.verticalLayout__web_content.setContentsMargins(0, 0, 0, 0)
        self.webEngineView__webview = QWebEngineView(self.widget__web_content)
        self.webEngineView__webview.setObjectName("webEngineView__webview")
        self.webEngineView__webview.setUrl(QUrl("about:blank"))
        self.verticalLayout__web_content.addWidget(self.webEngineView__webview)
        self.splitter__webview_whole_vertical.addWidget(self.widget__web_content)
        self.verticalLayout__web_view.addWidget(self.splitter__webview_whole_vertical)
