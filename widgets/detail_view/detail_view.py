from __future__ import annotations

from typing import Any

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.05.15 03:43:41
# modified date:
# description:
from PySide6 import QtCore, QtGui, QtWidgets

from libs.ui_icons import Icon
from widgets.detail_view.layout import DetailViewLayout
from widgets.detail_view.presenter import DetailContent, DetailPresenter
from widgets.layout_helpers import copy_to_clipboard


class DetailView(QtWidgets.QDialog, DetailViewLayout):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.build_ui(self)
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.resize(1200, 620)
        self.textBrowser__detail.setFontPointSize(12)
        self.__pixmap_size = 600
        self._presenter = DetailPresenter(self)
        self._copyable: dict[str, str] = {}
        self._copy_buttons = {
            "Name": self.pushButton__copy_name,
            "Path": self.pushButton__copy_path,
            "Version": self.pushButton__copy_version,
        }
        for key, button in self._copy_buttons.items():
            button.clicked.connect(lambda _=False, k=key: self._copy(k))

    def _copy(self, key: str) -> None:
        value = self._copyable.get(key)
        if value:
            copy_to_clipboard(value)

    def show_detail_ihda_data(
        self, data: Any = None, is_histview: bool | None = None
    ) -> None:
        if data is not None:
            self._presenter.show(data, history=bool(is_histview))

    def show_detail_record_data(self, data: Any = None) -> None:
        if data is not None:
            self._presenter.show(data, record=True)

    def show_content(self, content: DetailContent) -> None:
        from html import escape

        key_style = "color: palette(mid); padding-right: 12px; white-space: nowrap;"
        cells = "".join(
            f'<tr><td style="{key_style}">{escape(key)}</td><td>{escape(value)}</td></tr>'
            for key, value in content.rows
        )
        self.textBrowser__detail.setHtml(
            f'<table cellspacing="0" cellpadding="3">{cells}</table>'
        )
        self._copyable = dict(content.copyable)
        for key, button in self._copy_buttons.items():
            button.setEnabled(key in self._copyable)
            button.setToolTip(self._copyable.get(key, ""))
        thumbnail_filepath = content.thumbnail
        if thumbnail_filepath is not None and thumbnail_filepath.is_file():
            pixmap = QtGui.QPixmap(thumbnail_filepath.as_posix())
        else:
            pixmap = QtGui.QPixmap(Icon.NO_IMG_AVAILABLE)
        self.label__pixmap.resize(self.__pixmap_size, self.__pixmap_size)
        self.label__pixmap.setPixmap(
            pixmap.scaled(
                self.label__pixmap.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.show()
