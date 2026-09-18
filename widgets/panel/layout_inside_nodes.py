"""Inside-nodes page.

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
    QComboBox,
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


def build_inside_nodes(layout: MainWindowLayout, window: QMainWindow) -> None:
    layout.page__hda_inside_hipfile = QWidget()
    layout.page__hda_inside_hipfile.setObjectName("page__hda_inside_hipfile")
    layout.verticalLayout__inside_page = QVBoxLayout(layout.page__hda_inside_hipfile)
    layout.verticalLayout__inside_page.setSpacing(1)
    layout.verticalLayout__inside_page.setObjectName("verticalLayout__inside_page")
    layout.verticalLayout__inside_page.setContentsMargins(1, 1, 1, 1)
    layout.verticalLayout__inside_content = QVBoxLayout()
    layout.verticalLayout__inside_content.setSpacing(1)
    layout.verticalLayout__inside_content.setObjectName(
        "verticalLayout__inside_content"
    )
    layout.horizontalLayout__inside_search = QHBoxLayout()
    layout.horizontalLayout__inside_search.setSpacing(3)
    layout.horizontalLayout__inside_search.setObjectName(
        "horizontalLayout__inside_search"
    )
    layout.checkBox__hda_inside_connect_to_view = QCheckBox(
        layout.page__hda_inside_hipfile
    )
    layout.checkBox__hda_inside_connect_to_view.setObjectName(
        "checkBox__hda_inside_connect_to_view"
    )
    layout.checkBox__hda_inside_connect_to_view.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.checkBox__hda_inside_connect_to_view.setIcon(
        QIcon(":/main/icons/show_all.png")
    )
    layout.checkBox__hda_inside_connect_to_view.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.checkBox__hda_inside_connect_to_view.setToolTip(
        main_window_text("Connect to List/Table View")
    )
    layout.checkBox__hda_inside_connect_to_view.setStatusTip(
        main_window_text(
            "When you enable this option, when you select an iHDA node in the List/Table view, only the information for that node is automatically displayed."
        )
    )
    layout.checkBox__hda_inside_connect_to_view.setText("")
    layout.horizontalLayout__inside_search.addWidget(
        layout.checkBox__hda_inside_connect_to_view
    )
    layout.comboBox__hda_inside_node = QComboBox(layout.page__hda_inside_hipfile)
    layout.comboBox__hda_inside_node.setObjectName("comboBox__hda_inside_node")
    layout.comboBox__hda_inside_node.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.comboBox__hda_inside_node.setFrame(False)
    layout.comboBox__hda_inside_node.setToolTip(
        main_window_text("Select which iHDA node to search.")
    )
    layout.comboBox__hda_inside_node.setStatusTip(
        main_window_text(
            "The selected iHDA node is retrieved from the current HIP file."
        )
    )
    layout.horizontalLayout__inside_search.addWidget(layout.comboBox__hda_inside_node)
    layout.lineEdit__search_found_hda_inside_node = QLineEdit(
        layout.page__hda_inside_hipfile
    )
    layout.lineEdit__search_found_hda_inside_node.setObjectName(
        "lineEdit__search_found_hda_inside_node"
    )
    layout.lineEdit__search_found_hda_inside_node.setFrame(False)
    layout.lineEdit__search_found_hda_inside_node.setClearButtonEnabled(True)
    layout.lineEdit__search_found_hda_inside_node.setStatusTip(
        main_window_text("Please enter your search term")
    )
    layout.lineEdit__search_found_hda_inside_node.setPlaceholderText(
        main_window_text("ex) setup_fire")
    )
    layout.horizontalLayout__inside_search.addWidget(
        layout.lineEdit__search_found_hda_inside_node
    )
    layout.spacer__inside_search = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__inside_search.addItem(layout.spacer__inside_search)
    layout.pushButton__hda_inside_node_refresh = QPushButton(
        layout.page__hda_inside_hipfile
    )
    layout.pushButton__hda_inside_node_refresh.setObjectName(
        "pushButton__hda_inside_node_refresh"
    )
    layout.pushButton__hda_inside_node_refresh.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.pushButton__hda_inside_node_refresh.setIcon(
        QIcon(":/main/icons/ic_refresh_white.png")
    )
    layout.pushButton__hda_inside_node_refresh.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.pushButton__hda_inside_node_refresh.setFlat(True)
    layout.pushButton__hda_inside_node_refresh.setToolTip(
        main_window_text(
            "Refresh the iHDA node search results in the current HIP file."
        )
    )
    layout.pushButton__hda_inside_node_refresh.setStatusTip(
        main_window_text(
            "If the search results do not match the iHDA node in the current HIP file, click this button to refresh."
        )
    )
    layout.pushButton__hda_inside_node_refresh.setText("")
    layout.horizontalLayout__inside_search.addWidget(
        layout.pushButton__hda_inside_node_refresh
    )
    layout.verticalLayout__inside_content.addLayout(
        layout.horizontalLayout__inside_search
    )
    layout.verticalLayout__hda_inside_node = QVBoxLayout()
    layout.verticalLayout__hda_inside_node.setSpacing(1)
    layout.verticalLayout__hda_inside_node.setObjectName(
        "verticalLayout__hda_inside_node"
    )
    layout.verticalLayout__inside_content.addLayout(
        layout.verticalLayout__hda_inside_node
    )
    layout.horizontalLayout__inside_count = QHBoxLayout()
    layout.horizontalLayout__inside_count.setSpacing(3)
    layout.horizontalLayout__inside_count.setObjectName(
        "horizontalLayout__inside_count"
    )
    layout.horizontalLayout__inside_count.setContentsMargins(3, -1, 3, -1)
    layout.spacer__inside_count = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__inside_count.addItem(layout.spacer__inside_count)
    layout.label__found_hda_inside_hipfile = QLabel(layout.page__hda_inside_hipfile)
    layout.label__found_hda_inside_hipfile.setObjectName(
        "label__found_hda_inside_hipfile"
    )
    layout.label__found_hda_inside_hipfile.setText(main_window_text("found iHDA of "))
    layout.horizontalLayout__inside_count.addWidget(
        layout.label__found_hda_inside_hipfile
    )
    layout.label__found_hda_inside_hipfile_count = QLabel(
        layout.page__hda_inside_hipfile
    )
    layout.label__found_hda_inside_hipfile_count.setObjectName(
        "label__found_hda_inside_hipfile_count"
    )
    layout.label__found_hda_inside_hipfile_count.setAlignment(
        Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignVCenter
    )
    layout.label__found_hda_inside_hipfile_count.setText(main_window_text("0"))
    layout.horizontalLayout__inside_count.addWidget(
        layout.label__found_hda_inside_hipfile_count
    )
    layout.verticalLayout__inside_content.addLayout(
        layout.horizontalLayout__inside_count
    )
    layout.verticalLayout__inside_page.addLayout(layout.verticalLayout__inside_content)
    layout.stackedWidget__hda_infos.addWidget(layout.page__hda_inside_hipfile)
    layout.splitter__hda_info_whole_vertical.addWidget(layout.stackedWidget__hda_infos)
    layout.splitter__whole_horizontal.addWidget(
        layout.splitter__hda_info_whole_vertical
    )
    layout.verticalLayout__library_page.addWidget(layout.splitter__whole_horizontal)
    layout.stackedWidget__whole.addWidget(layout.page__ihda)
