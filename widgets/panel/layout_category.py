"""Category tree panel.

Part of the main window layout; see widgets/panel/layout.py build_ui().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QCursor,
    QIcon,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from widgets.layout_helpers import main_window_text
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

if TYPE_CHECKING:
    from widgets.panel.layout import MainWindowLayout


def build_category_panel(layout: MainWindowLayout, window: QMainWindow) -> None:
    layout.widget__category_panel = QWidget(layout.splitter__whole_horizontal)
    layout.widget__category_panel.setObjectName("widget__category_panel")
    layout.verticalLayout__category_panel = QVBoxLayout(layout.widget__category_panel)
    layout.verticalLayout__category_panel.setSpacing(1)
    layout.verticalLayout__category_panel.setObjectName(
        "verticalLayout__category_panel"
    )
    layout.verticalLayout__category_panel.setContentsMargins(0, 0, 0, 0)
    layout.splitter__cate_whole_vertical = QSplitter(layout.widget__category_panel)
    layout.splitter__cate_whole_vertical.setObjectName("splitter__cate_whole_vertical")
    layout.splitter__cate_whole_vertical.setOrientation(Qt.Orientation.Vertical)
    layout.splitter__cate_whole_vertical.setHandleWidth(3)
    layout.widget__category_search = QWidget(layout.splitter__cate_whole_vertical)
    layout.widget__category_search.setObjectName("widget__category_search")
    layout.horizontalLayout__category_search = QHBoxLayout(
        layout.widget__category_search
    )
    layout.horizontalLayout__category_search.setSpacing(5)
    layout.horizontalLayout__category_search.setObjectName(
        "horizontalLayout__category_search"
    )
    layout.horizontalLayout__category_search.setContentsMargins(3, 0, 3, 0)
    layout.checkBox__casesensitive_cate = QCheckBox(layout.widget__category_search)
    layout.checkBox__casesensitive_cate.setObjectName("checkBox__casesensitive_cate")
    layout.checkBox__casesensitive_cate.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.checkBox__casesensitive_cate.setIcon(
        QIcon(":/main/icons/case_sensitive.png")
    )
    layout.checkBox__casesensitive_cate.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.checkBox__casesensitive_cate.setToolTip(
        main_window_text("Word Case Sensitive")
    )
    layout.checkBox__casesensitive_cate.setStatusTip(
        main_window_text("It is case sensitive")
    )
    layout.checkBox__casesensitive_cate.setText("")
    layout.horizontalLayout__category_search.addWidget(
        layout.checkBox__casesensitive_cate
    )
    layout.lineEdit__search_cate = QLineEdit(layout.widget__category_search)
    layout.lineEdit__search_cate.setObjectName("lineEdit__search_cate")
    layout.lineEdit__search_cate.setFrame(False)
    layout.lineEdit__search_cate.setClearButtonEnabled(True)
    layout.lineEdit__search_cate.setStatusTip(
        main_window_text("Please enter your search term")
    )
    layout.lineEdit__search_cate.setPlaceholderText(main_window_text("ex) sop"))
    layout.horizontalLayout__category_search.addWidget(layout.lineEdit__search_cate)
    layout.splitter__cate_whole_vertical.addWidget(layout.widget__category_search)
    layout.stackedWidget__category = QStackedWidget(
        layout.splitter__cate_whole_vertical
    )
    layout.stackedWidget__category.setObjectName("stackedWidget__category")
    layout.stackedWidget__category.setStatusTip(
        main_window_text("Show the category of the iHDA")
    )
    layout.page__category = QWidget()
    layout.page__category.setObjectName("page__category")
    layout.verticalLayout__category_page = QVBoxLayout(layout.page__category)
    layout.verticalLayout__category_page.setSpacing(1)
    layout.verticalLayout__category_page.setObjectName("verticalLayout__category_page")
    layout.verticalLayout__category_page.setContentsMargins(0, 0, 0, 0)
    layout.verticalLayout__category = QVBoxLayout()
    layout.verticalLayout__category.setSpacing(1)
    layout.verticalLayout__category.setObjectName("verticalLayout__category")
    layout.verticalLayout__category_page.addLayout(layout.verticalLayout__category)
    layout.stackedWidget__category.addWidget(layout.page__category)
    layout.splitter__cate_whole_vertical.addWidget(layout.stackedWidget__category)
    layout.verticalLayout__category_panel.addWidget(
        layout.splitter__cate_whole_vertical
    )
    layout.horizontalLayout__category_count = QHBoxLayout()
    layout.horizontalLayout__category_count.setSpacing(3)
    layout.horizontalLayout__category_count.setObjectName(
        "horizontalLayout__category_count"
    )
    layout.horizontalLayout__category_count.setContentsMargins(3, -1, 3, -1)
    layout.spacer__category_count = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__category_count.addItem(layout.spacer__category_count)
    layout.label__cate_count = QLabel(layout.widget__category_panel)
    layout.label__cate_count.setObjectName("label__cate_count")
    layout.label__cate_count.setAlignment(
        Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignVCenter
    )
    layout.label__cate_count.setText(main_window_text("0"))
    layout.horizontalLayout__category_count.addWidget(layout.label__cate_count)
    layout.label__cate_count_suffix = QLabel(layout.widget__category_panel)
    layout.label__cate_count_suffix.setObjectName("label__cate_count_suffix")
    layout.label__cate_count_suffix.setText(main_window_text("categories"))
    layout.horizontalLayout__category_count.addWidget(layout.label__cate_count_suffix)
    layout.verticalLayout__category_panel.addLayout(
        layout.horizontalLayout__category_count
    )
    layout.splitter__whole_horizontal.addWidget(layout.widget__category_panel)
