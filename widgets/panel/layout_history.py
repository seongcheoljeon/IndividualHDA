"""History page: search, date filter and results.

Part of the main window layout; see widgets/panel/layout.py build_ui().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QDate,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QCursor,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from libs.ui_icons import Icon
from widgets.layout_helpers import main_window_text, size_policy
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

# The date filter starts on the last month; the old 2020 range hid everything.
DEFAULT_DATE_SPAN_DAYS = 30

if TYPE_CHECKING:
    from widgets.panel.layout import MainWindowLayout


def build_history_page(layout: MainWindowLayout, window: QMainWindow) -> None:
    layout.page__history = QWidget()
    layout.page__history.setObjectName("page__history")
    layout.verticalLayout__history_page = QVBoxLayout(layout.page__history)
    layout.verticalLayout__history_page.setSpacing(1)
    layout.verticalLayout__history_page.setObjectName("verticalLayout__history_page")
    layout.verticalLayout__history_page.setContentsMargins(1, 1, 1, 1)
    layout.verticalLayout__history_content = QVBoxLayout()
    layout.verticalLayout__history_content.setSpacing(1)
    layout.verticalLayout__history_content.setObjectName(
        "verticalLayout__history_content"
    )
    layout.splitter__ihda_hist_whole_vertical = QSplitter(layout.page__history)
    layout.splitter__ihda_hist_whole_vertical.setObjectName(
        "splitter__ihda_hist_whole_vertical"
    )
    layout.splitter__ihda_hist_whole_vertical.setOrientation(Qt.Orientation.Vertical)
    layout.splitter__ihda_hist_whole_vertical.setHandleWidth(3)
    build_history_search(layout, window)
    build_history_date_filter(layout, window)
    build_history_results(layout, window)


def build_history_search(layout: MainWindowLayout, window: QMainWindow) -> None:
    layout.widget__history_search = QWidget(layout.splitter__ihda_hist_whole_vertical)
    layout.widget__history_search.setObjectName("widget__history_search")
    layout.horizontalLayout__history_search = QHBoxLayout(layout.widget__history_search)
    layout.horizontalLayout__history_search.setSpacing(5)
    layout.horizontalLayout__history_search.setObjectName(
        "horizontalLayout__history_search"
    )
    layout.horizontalLayout__history_search.setContentsMargins(0, 0, 0, 0)
    layout.comboBox__hist_ihda_node = QComboBox(layout.widget__history_search)
    layout.comboBox__hist_ihda_node.setObjectName("comboBox__hist_ihda_node")
    layout.comboBox__hist_ihda_node.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.comboBox__hist_ihda_node.setFrame(False)
    layout.comboBox__hist_ihda_node.setToolTip(main_window_text("Select iHDA node"))
    layout.comboBox__hist_ihda_node.setStatusTip(
        main_window_text("It shows the history of the selected iHDA node.")
    )
    layout.horizontalLayout__history_search.addWidget(layout.comboBox__hist_ihda_node)
    layout.spacer__history_search = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__history_search.addItem(layout.spacer__history_search)
    layout.horizontalLayout__history_query = QHBoxLayout()
    layout.horizontalLayout__history_query.setSpacing(5)
    layout.horizontalLayout__history_query.setObjectName(
        "horizontalLayout__history_query"
    )
    layout.horizontalLayout__history_query.setContentsMargins(3, -1, 3, -1)
    layout.comboBox__search_field_hist = QComboBox(layout.widget__history_search)
    layout.comboBox__search_field_hist.setObjectName("comboBox__search_field_hist")
    layout.comboBox__search_field_hist.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.comboBox__search_field_hist.setFrame(False)
    layout.comboBox__search_field_hist.setToolTip(main_window_text("Search Type"))
    layout.comboBox__search_field_hist.setStatusTip(
        main_window_text("Decide what type to search for")
    )
    layout.horizontalLayout__history_query.addWidget(layout.comboBox__search_field_hist)
    layout.checkBox__casesensitive_hda_hist = QCheckBox(layout.widget__history_search)
    layout.checkBox__casesensitive_hda_hist.setObjectName(
        "checkBox__casesensitive_hda_hist"
    )
    layout.checkBox__casesensitive_hda_hist.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.checkBox__casesensitive_hda_hist.setIcon(QIcon(Icon.CASE_SENSITIVE))
    layout.checkBox__casesensitive_hda_hist.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.checkBox__casesensitive_hda_hist.setToolTip(
        main_window_text("Word Case Sensitive")
    )
    layout.checkBox__casesensitive_hda_hist.setStatusTip(
        main_window_text("It is case sensitive")
    )
    layout.checkBox__casesensitive_hda_hist.setText("")
    layout.horizontalLayout__history_query.addWidget(
        layout.checkBox__casesensitive_hda_hist
    )
    layout.lineEdit__search_hda_hist = QLineEdit(layout.widget__history_search)
    layout.lineEdit__search_hda_hist.setObjectName("lineEdit__search_hda_hist")
    layout.lineEdit__search_hda_hist.setFrame(False)
    layout.lineEdit__search_hda_hist.setClearButtonEnabled(True)
    layout.lineEdit__search_hda_hist.setStatusTip(
        main_window_text("Please enter your search term")
    )
    layout.lineEdit__search_hda_hist.setPlaceholderText(main_window_text("ex) wrangle"))
    layout.horizontalLayout__history_query.addWidget(layout.lineEdit__search_hda_hist)
    layout.horizontalLayout__history_search.addLayout(
        layout.horizontalLayout__history_query
    )
    layout.line__history_filters = QFrame(layout.widget__history_search)
    layout.line__history_filters.setObjectName("line__history_filters")
    layout.line__history_filters.setFrameShape(QFrame.Shape.VLine)
    layout.line__history_filters.setFrameShadow(QFrame.Shadow.Sunken)
    layout.horizontalLayout__history_search.addWidget(layout.line__history_filters)


def build_history_date_filter(layout: MainWindowLayout, window: QMainWindow) -> None:
    layout.horizontalLayout__history_date_filter = QHBoxLayout()
    layout.horizontalLayout__history_date_filter.setObjectName(
        "horizontalLayout__history_date_filter"
    )
    layout.checkBox__hist_search_date = QCheckBox(layout.widget__history_search)
    layout.checkBox__hist_search_date.setObjectName("checkBox__hist_search_date")
    layout.checkBox__hist_search_date.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.checkBox__hist_search_date.setToolTip(
        main_window_text("Search History By Date")
    )
    layout.checkBox__hist_search_date.setStatusTip(
        main_window_text("Search iHDA history by date")
    )
    layout.checkBox__hist_search_date.setText(main_window_text("Date Search"))
    layout.horizontalLayout__history_date_filter.addWidget(
        layout.checkBox__hist_search_date
    )
    layout.horizontalLayout__history_date_range = QHBoxLayout()
    layout.horizontalLayout__history_date_range.setObjectName(
        "horizontalLayout__history_date_range"
    )
    layout.dateEdit__hist_search_start = QDateEdit(layout.widget__history_search)
    layout.dateEdit__hist_search_start.setObjectName("dateEdit__hist_search_start")
    layout.dateEdit__hist_search_start.setFrame(False)
    layout.dateEdit__hist_search_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.dateEdit__hist_search_start.setCalendarPopup(True)
    layout.dateEdit__hist_search_start.setDisplayFormat("yyyy-MM-dd")
    layout.dateEdit__hist_search_start.setDate(
        QDate.currentDate().addDays(-DEFAULT_DATE_SPAN_DAYS)
    )
    layout.dateEdit__hist_search_start.setToolTip(main_window_text("Start Date"))
    layout.dateEdit__hist_search_start.setStatusTip(
        main_window_text("Start date to search")
    )
    layout.horizontalLayout__history_date_range.addWidget(
        layout.dateEdit__hist_search_start
    )
    layout.label__join_str = QLabel(layout.widget__history_search)
    layout.label__join_str.setObjectName("label__join_str")
    layout.label__join_str.setSizePolicy(
        size_policy(
            layout.label__join_str,
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
    )
    layout.label__join_str.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.label__join_str.setText(main_window_text("~"))
    layout.horizontalLayout__history_date_range.addWidget(layout.label__join_str)
    layout.dateEdit__hist_search_end = QDateEdit(layout.widget__history_search)
    layout.dateEdit__hist_search_end.setObjectName("dateEdit__hist_search_end")
    layout.dateEdit__hist_search_end.setFrame(False)
    layout.dateEdit__hist_search_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.dateEdit__hist_search_end.setCalendarPopup(True)
    layout.dateEdit__hist_search_end.setDisplayFormat("yyyy-MM-dd")
    layout.dateEdit__hist_search_end.setDate(QDate.currentDate())
    layout.dateEdit__hist_search_end.setToolTip(main_window_text("End Date"))
    layout.dateEdit__hist_search_end.setStatusTip(
        main_window_text("End date to search")
    )
    layout.horizontalLayout__history_date_range.addWidget(
        layout.dateEdit__hist_search_end
    )
    layout.horizontalLayout__history_date_filter.addLayout(
        layout.horizontalLayout__history_date_range
    )
    layout.horizontalLayout__history_search.addLayout(
        layout.horizontalLayout__history_date_filter
    )
    layout.spacer__history_search_middle = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__history_search.addItem(
        layout.spacer__history_search_middle
    )
    layout.pushButton__hist_reset_filters = QPushButton(layout.widget__history_search)
    layout.pushButton__hist_reset_filters.setObjectName(
        "pushButton__hist_reset_filters"
    )
    layout.pushButton__hist_reset_filters.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.pushButton__hist_reset_filters.setIcon(QIcon(Icon.CLEAR))
    layout.pushButton__hist_reset_filters.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.pushButton__hist_reset_filters.setFlat(True)
    layout.pushButton__hist_reset_filters.setToolTip(main_window_text("Clear filters"))
    layout.pushButton__hist_reset_filters.setStatusTip(
        main_window_text("Show every history entry again")
    )
    layout.horizontalLayout__history_search.addWidget(
        layout.pushButton__hist_reset_filters
    )
    layout.splitter__ihda_hist_whole_vertical.addWidget(layout.widget__history_search)


def build_history_results(layout: MainWindowLayout, window: QMainWindow) -> None:
    layout.widget__history_view = QWidget(layout.splitter__ihda_hist_whole_vertical)
    layout.widget__history_view.setObjectName("widget__history_view")
    layout.verticalLayout__history = QVBoxLayout(layout.widget__history_view)
    layout.verticalLayout__history.setSpacing(1)
    layout.verticalLayout__history.setObjectName("verticalLayout__history")
    layout.verticalLayout__history.setContentsMargins(0, 0, 0, 0)
    layout.splitter__ihda_hist_whole_vertical.addWidget(layout.widget__history_view)
    layout.verticalLayout__history_content.addWidget(
        layout.splitter__ihda_hist_whole_vertical
    )
    layout.horizontalLayout__history_footer = QHBoxLayout()
    layout.horizontalLayout__history_footer.setSpacing(5)
    layout.horizontalLayout__history_footer.setObjectName(
        "horizontalLayout__history_footer"
    )
    layout.label__hist_tag_pixmap = QLabel(layout.page__history)
    layout.label__hist_tag_pixmap.setObjectName("label__hist_tag_pixmap")
    layout.label__hist_tag_pixmap.setMaximumSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.label__hist_tag_pixmap.setPixmap(QPixmap(Icon.IC_BOOKMARK_WHITE))
    layout.label__hist_tag_pixmap.setScaledContents(True)
    layout.label__hist_tag_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.label__hist_tag_pixmap.setText("")
    layout.horizontalLayout__history_footer.addWidget(layout.label__hist_tag_pixmap)
    layout.label__hist_tags = QLabel(layout.page__history)
    layout.label__hist_tags.setObjectName("label__hist_tags")
    layout.label__hist_tags.setStyleSheet("color: palette(link);")
    layout.label__hist_tags.setText("")
    layout.horizontalLayout__history_footer.addWidget(layout.label__hist_tags)
    layout.spacer__history_footer = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__history_footer.addItem(layout.spacer__history_footer)
    layout.horizontalLayout__history_count = QHBoxLayout()
    layout.horizontalLayout__history_count.setSpacing(5)
    layout.horizontalLayout__history_count.setObjectName(
        "horizontalLayout__history_count"
    )
    layout.label__hist_cnt = QLabel(layout.page__history)
    layout.label__hist_cnt.setObjectName("label__hist_cnt")
    layout.label__hist_cnt.setAlignment(
        Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignVCenter
    )
    layout.label__hist_cnt.setText(main_window_text("0"))
    layout.horizontalLayout__history_count.addWidget(layout.label__hist_cnt)
    layout.label__hist_cnt_suffix = QLabel(layout.page__history)
    layout.label__hist_cnt_suffix.setObjectName("label__hist_cnt_suffix")
    layout.label__hist_cnt_suffix.setText(main_window_text("shown"))
    layout.label__hist_cnt.setToolTip(
        main_window_text("History entries that pass the filters above")
    )
    layout.horizontalLayout__history_count.addWidget(layout.label__hist_cnt_suffix)
    layout.horizontalLayout__history_footer.addLayout(
        layout.horizontalLayout__history_count
    )
    layout.verticalLayout__history_content.addLayout(
        layout.horizontalLayout__history_footer
    )
    layout.verticalLayout__history_page.addLayout(
        layout.verticalLayout__history_content
    )
    layout.stackedWidget__whole.addWidget(layout.page__history)
    layout.splitter__whole_vertical.addWidget(layout.stackedWidget__whole)
