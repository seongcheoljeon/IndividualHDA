from __future__ import annotations

from typing import Any

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.05.15 03:43:41
# modified date:
# description:
from PySide6 import QtCore, QtGui, QtWidgets

from widgets.detail_view.layout import DetailViewLayout
from widgets.detail_view.presenter import DetailContent, DetailPresenter


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

    def show_detail_ihda_data(
        self, data: Any = None, is_histview: bool | None = None
    ) -> None:
        if data is not None:
            self._presenter.show(data, history=bool(is_histview))

    def show_detail_record_data(self, data: Any = None) -> None:
        if data is not None:
            self._presenter.show(data, record=True)

    def show_content(self, content: DetailContent) -> None:
        self.textBrowser__detail.setPlainText(content.text)
        thumbnail_filepath = content.thumbnail
        if thumbnail_filepath is not None and thumbnail_filepath.is_file():
            pixmap = QtGui.QPixmap(thumbnail_filepath.as_posix())
        else:
            pixmap = QtGui.QPixmap(":/main/icons/no_img_available.png")
        self.label__pixmap.resize(self.__pixmap_size, self.__pixmap_size)
        self.label__pixmap.setPixmap(
            pixmap.scaled(
                self.label__pixmap.size(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio
            )
        )
        self.show()
