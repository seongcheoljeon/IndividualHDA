"""Scene records page.

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
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from widgets.layout_helpers import main_window_text
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

if TYPE_CHECKING:
    from widgets.panel.layout import MainWindowLayout


def build_scene_records(layout: MainWindowLayout, window: QMainWindow) -> None:
    layout.page__hda_loc_record = QWidget()
    layout.page__hda_loc_record.setObjectName("page__hda_loc_record")
    layout.verticalLayout__scene_record_page = QVBoxLayout(layout.page__hda_loc_record)
    layout.verticalLayout__scene_record_page.setSpacing(1)
    layout.verticalLayout__scene_record_page.setObjectName(
        "verticalLayout__scene_record_page"
    )
    layout.verticalLayout__scene_record_page.setContentsMargins(1, 1, 1, 1)
    layout.verticalLayout__scene_record_content = QVBoxLayout()
    layout.verticalLayout__scene_record_content.setSpacing(1)
    layout.verticalLayout__scene_record_content.setObjectName(
        "verticalLayout__scene_record_content"
    )
    layout.horizontalLayout__scene_record_search = QHBoxLayout()
    layout.horizontalLayout__scene_record_search.setSpacing(5)
    layout.horizontalLayout__scene_record_search.setObjectName(
        "horizontalLayout__scene_record_search"
    )
    layout.lineEdit__search_record = QLineEdit(layout.page__hda_loc_record)
    layout.lineEdit__search_record.setObjectName("lineEdit__search_record")
    layout.lineEdit__search_record.setFrame(False)
    layout.lineEdit__search_record.setClearButtonEnabled(True)
    layout.lineEdit__search_record.setStatusTip(
        main_window_text("Please enter your search term")
    )
    layout.lineEdit__search_record.setPlaceholderText(
        main_window_text("ex) untitled.hip")
    )
    layout.horizontalLayout__scene_record_search.addWidget(
        layout.lineEdit__search_record
    )
    layout.checkBox__record_only_current_ihda = QCheckBox(layout.page__hda_loc_record)
    layout.checkBox__record_only_current_ihda.setObjectName(
        "checkBox__record_only_current_ihda"
    )
    layout.checkBox__record_only_current_ihda.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.checkBox__record_only_current_ihda.setIcon(
        QIcon(":/main/icons/show_all.png")
    )
    layout.checkBox__record_only_current_ihda.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.checkBox__record_only_current_ihda.setToolTip(
        main_window_text("Show Only Current iHDA")
    )
    layout.checkBox__record_only_current_ihda.setStatusTip(
        main_window_text(
            "When selected, displays information only from the current iHDA node."
        )
    )
    layout.checkBox__record_only_current_ihda.setText("")
    layout.horizontalLayout__scene_record_search.addWidget(
        layout.checkBox__record_only_current_ihda
    )
    layout.checkBox__record_only_current_hipfile = QCheckBox(
        layout.page__hda_loc_record
    )
    layout.checkBox__record_only_current_hipfile.setObjectName(
        "checkBox__record_only_current_hipfile"
    )
    layout.checkBox__record_only_current_hipfile.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.checkBox__record_only_current_hipfile.setIcon(
        QIcon(":/main/icons/hipfile.png")
    )
    layout.checkBox__record_only_current_hipfile.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.checkBox__record_only_current_hipfile.setToolTip(
        main_window_text("Show Only Current HIP File")
    )
    layout.checkBox__record_only_current_hipfile.setStatusTip(
        main_window_text(
            "When checked, only information from the current HIP file is displayed."
        )
    )
    layout.checkBox__record_only_current_hipfile.setText("")
    layout.horizontalLayout__scene_record_search.addWidget(
        layout.checkBox__record_only_current_hipfile
    )
    layout.spacer__scene_record_search = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__scene_record_search.addItem(
        layout.spacer__scene_record_search
    )
    layout.pushButton__cleanup_hda_record = QPushButton(layout.page__hda_loc_record)
    layout.pushButton__cleanup_hda_record.setObjectName(
        "pushButton__cleanup_hda_record"
    )
    layout.pushButton__cleanup_hda_record.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.pushButton__cleanup_hda_record.setIcon(QIcon(":/main/icons/clear.png"))
    layout.pushButton__cleanup_hda_record.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.pushButton__cleanup_hda_record.setFlat(True)
    layout.pushButton__cleanup_hda_record.setToolTip(
        main_window_text("Remove any unnecessary iHDA Record data that does not exist.")
    )
    layout.pushButton__cleanup_hda_record.setStatusTip(
        main_window_text("Remove any unnecessary iHDA Record data that does not exist.")
    )
    layout.pushButton__cleanup_hda_record.setText("")
    layout.horizontalLayout__scene_record_search.addWidget(
        layout.pushButton__cleanup_hda_record
    )
    layout.verticalLayout__scene_record_content.addLayout(
        layout.horizontalLayout__scene_record_search
    )
    layout.verticalLayout__hda_loc_record = QVBoxLayout()
    layout.verticalLayout__hda_loc_record.setSpacing(1)
    layout.verticalLayout__hda_loc_record.setObjectName(
        "verticalLayout__hda_loc_record"
    )
    layout.verticalLayout__scene_record_content.addLayout(
        layout.verticalLayout__hda_loc_record
    )
    layout.horizontalLayout__scene_record_count = QHBoxLayout()
    layout.horizontalLayout__scene_record_count.setSpacing(5)
    layout.horizontalLayout__scene_record_count.setObjectName(
        "horizontalLayout__scene_record_count"
    )
    layout.spacer__scene_record_count = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__scene_record_count.addItem(
        layout.spacer__scene_record_count
    )
    layout.label__loc_record_count = QLabel(layout.page__hda_loc_record)
    layout.label__loc_record_count.setObjectName("label__loc_record_count")
    layout.label__loc_record_count.setAlignment(
        Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignVCenter
    )
    layout.label__loc_record_count.setText(main_window_text("0"))
    layout.horizontalLayout__scene_record_count.addWidget(
        layout.label__loc_record_count
    )
    layout.label__loc_record_count_suffix = QLabel(layout.page__hda_loc_record)
    layout.label__loc_record_count_suffix.setObjectName(
        "label__loc_record_count_suffix"
    )
    layout.label__loc_record_count_suffix.setText(main_window_text("records"))
    layout.horizontalLayout__scene_record_count.addWidget(
        layout.label__loc_record_count_suffix
    )
    layout.verticalLayout__scene_record_content.addLayout(
        layout.horizontalLayout__scene_record_count
    )
    layout.verticalLayout__scene_record_page.addLayout(
        layout.verticalLayout__scene_record_content
    )
    layout.stackedWidget__hda_infos.addWidget(layout.page__hda_loc_record)
