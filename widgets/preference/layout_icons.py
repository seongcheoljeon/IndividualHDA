"""Icon sizes for the list, table and tree views.

Part of the preference dialog layout; see widgets/preference/layout.py build_ui().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QCursor,
    QIcon,
)
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from widgets.layout_helpers import preference_text

if TYPE_CHECKING:
    from widgets.preference.layout import PreferenceLayout


def build_icon_sizes(layout: PreferenceLayout, window: QDialog) -> None:
    layout.tab__icon = QWidget()
    layout.tab__icon.setObjectName("tab__icon")
    layout.verticalLayout__icon_sizes = QVBoxLayout(layout.tab__icon)
    layout.verticalLayout__icon_sizes.setSpacing(5)
    layout.verticalLayout__icon_sizes.setObjectName("verticalLayout__icon_sizes")
    layout.verticalLayout__icon_sizes.setContentsMargins(5, 5, 5, 5)
    build_list_icon_settings(layout, window)
    build_table_icon_settings(layout, window)
    build_tree_icon_settings(layout, window)


def build_list_icon_settings(layout: PreferenceLayout, window: QDialog) -> None:
    layout.horizontalLayout__default_listview_icon_size = QHBoxLayout()
    layout.horizontalLayout__default_listview_icon_size.setSpacing(15)
    layout.horizontalLayout__default_listview_icon_size.setObjectName(
        "horizontalLayout__default_listview_icon_size"
    )
    layout.horizontalLayout__default_listview_icon_size_row = QHBoxLayout()
    layout.horizontalLayout__default_listview_icon_size_row.setObjectName(
        "horizontalLayout__default_listview_icon_size_row"
    )
    layout.label__default_listview_icon_size = QLabel(layout.tab__icon)
    layout.label__default_listview_icon_size.setObjectName(
        "label__default_listview_icon_size"
    )
    layout.label__default_listview_icon_size.setText(preference_text("ListView"))
    layout.horizontalLayout__default_listview_icon_size_row.addWidget(
        layout.label__default_listview_icon_size
    )
    layout.spinBox__default_listview_icon_size = QSpinBox(layout.tab__icon)
    layout.spinBox__default_listview_icon_size.setObjectName(
        "spinBox__default_listview_icon_size"
    )
    layout.spinBox__default_listview_icon_size.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.spinBox__default_listview_icon_size.setFrame(False)
    layout.spinBox__default_listview_icon_size.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.spinBox__default_listview_icon_size.setMinimum(1)
    layout.spinBox__default_listview_icon_size.setValue(38)
    layout.spinBox__default_listview_icon_size.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_listview_icon_size_row.addWidget(
        layout.spinBox__default_listview_icon_size
    )
    layout.horizontalLayout__default_listview_icon_size.addLayout(
        layout.horizontalLayout__default_listview_icon_size_row
    )
    layout.spacer__default_listview_icon_size = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_listview_icon_size.addItem(
        layout.spacer__default_listview_icon_size
    )
    layout.horizontalLayout__default_listview_thumb_scale = QHBoxLayout()
    layout.horizontalLayout__default_listview_thumb_scale.setObjectName(
        "horizontalLayout__default_listview_thumb_scale"
    )
    layout.label__default_listview_thumb_scale = QLabel(layout.tab__icon)
    layout.label__default_listview_thumb_scale.setObjectName(
        "label__default_listview_thumb_scale"
    )
    layout.label__default_listview_thumb_scale.setText(
        preference_text("Thumbnail Scale")
    )
    layout.horizontalLayout__default_listview_thumb_scale.addWidget(
        layout.label__default_listview_thumb_scale
    )
    layout.doubleSpinBox__default_listview_thumb_scale = QDoubleSpinBox(
        layout.tab__icon
    )
    layout.doubleSpinBox__default_listview_thumb_scale.setObjectName(
        "doubleSpinBox__default_listview_thumb_scale"
    )
    layout.doubleSpinBox__default_listview_thumb_scale.setFrame(False)
    layout.doubleSpinBox__default_listview_thumb_scale.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_listview_thumb_scale.setDecimals(1)
    layout.doubleSpinBox__default_listview_thumb_scale.setMinimum(0.1)
    layout.doubleSpinBox__default_listview_thumb_scale.setMaximum(50.0)
    layout.doubleSpinBox__default_listview_thumb_scale.setSingleStep(0.1)
    layout.doubleSpinBox__default_listview_thumb_scale.setValue(2.0)
    layout.doubleSpinBox__default_listview_thumb_scale.setPrefix(preference_text("x"))
    layout.horizontalLayout__default_listview_thumb_scale.addWidget(
        layout.doubleSpinBox__default_listview_thumb_scale
    )
    layout.spacer__default_listview_thumb_scale = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_listview_thumb_scale.addItem(
        layout.spacer__default_listview_thumb_scale
    )
    layout.horizontalLayout__default_listview_icon_size.addLayout(
        layout.horizontalLayout__default_listview_thumb_scale
    )
    layout.verticalLayout__icon_sizes.addLayout(
        layout.horizontalLayout__default_listview_icon_size
    )


def build_table_icon_settings(layout: PreferenceLayout, window: QDialog) -> None:
    layout.horizontalLayout__default_tableview_icon_size = QHBoxLayout()
    layout.horizontalLayout__default_tableview_icon_size.setSpacing(15)
    layout.horizontalLayout__default_tableview_icon_size.setObjectName(
        "horizontalLayout__default_tableview_icon_size"
    )
    layout.horizontalLayout__default_tableview_icon_size_row = QHBoxLayout()
    layout.horizontalLayout__default_tableview_icon_size_row.setObjectName(
        "horizontalLayout__default_tableview_icon_size_row"
    )
    layout.label__default_tableview_icon_size = QLabel(layout.tab__icon)
    layout.label__default_tableview_icon_size.setObjectName(
        "label__default_tableview_icon_size"
    )
    layout.label__default_tableview_icon_size.setText(preference_text("TableView"))
    layout.horizontalLayout__default_tableview_icon_size_row.addWidget(
        layout.label__default_tableview_icon_size
    )
    layout.spinBox__default_tableview_icon_size = QSpinBox(layout.tab__icon)
    layout.spinBox__default_tableview_icon_size.setObjectName(
        "spinBox__default_tableview_icon_size"
    )
    layout.spinBox__default_tableview_icon_size.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.spinBox__default_tableview_icon_size.setFrame(False)
    layout.spinBox__default_tableview_icon_size.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.spinBox__default_tableview_icon_size.setMinimum(1)
    layout.spinBox__default_tableview_icon_size.setValue(38)
    layout.spinBox__default_tableview_icon_size.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_tableview_icon_size_row.addWidget(
        layout.spinBox__default_tableview_icon_size
    )
    layout.horizontalLayout__default_tableview_icon_size.addLayout(
        layout.horizontalLayout__default_tableview_icon_size_row
    )
    layout.spacer__default_tableview_icon_size = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_tableview_icon_size.addItem(
        layout.spacer__default_tableview_icon_size
    )
    layout.horizontalLayout__default_tableview_thumb_scale = QHBoxLayout()
    layout.horizontalLayout__default_tableview_thumb_scale.setObjectName(
        "horizontalLayout__default_tableview_thumb_scale"
    )
    layout.label__default_tableview_thumb_scale = QLabel(layout.tab__icon)
    layout.label__default_tableview_thumb_scale.setObjectName(
        "label__default_tableview_thumb_scale"
    )
    layout.label__default_tableview_thumb_scale.setText(
        preference_text("Thumbnail Scale")
    )
    layout.horizontalLayout__default_tableview_thumb_scale.addWidget(
        layout.label__default_tableview_thumb_scale
    )
    layout.doubleSpinBox__default_tableview_thumb_scale = QDoubleSpinBox(
        layout.tab__icon
    )
    layout.doubleSpinBox__default_tableview_thumb_scale.setObjectName(
        "doubleSpinBox__default_tableview_thumb_scale"
    )
    layout.doubleSpinBox__default_tableview_thumb_scale.setFrame(False)
    layout.doubleSpinBox__default_tableview_thumb_scale.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_tableview_thumb_scale.setDecimals(1)
    layout.doubleSpinBox__default_tableview_thumb_scale.setMinimum(0.1)
    layout.doubleSpinBox__default_tableview_thumb_scale.setMaximum(50.0)
    layout.doubleSpinBox__default_tableview_thumb_scale.setSingleStep(0.1)
    layout.doubleSpinBox__default_tableview_thumb_scale.setValue(1.3)
    layout.doubleSpinBox__default_tableview_thumb_scale.setPrefix(preference_text("x"))
    layout.horizontalLayout__default_tableview_thumb_scale.addWidget(
        layout.doubleSpinBox__default_tableview_thumb_scale
    )
    layout.spacer__default_tableview_thumb_scale = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_tableview_thumb_scale.addItem(
        layout.spacer__default_tableview_thumb_scale
    )
    layout.horizontalLayout__default_tableview_icon_size.addLayout(
        layout.horizontalLayout__default_tableview_thumb_scale
    )
    layout.verticalLayout__icon_sizes.addLayout(
        layout.horizontalLayout__default_tableview_icon_size
    )


def build_tree_icon_settings(layout: PreferenceLayout, window: QDialog) -> None:
    layout.horizontalLayout__default_treeview_icon_size = QHBoxLayout()
    layout.horizontalLayout__default_treeview_icon_size.setObjectName(
        "horizontalLayout__default_treeview_icon_size"
    )
    layout.label__default_treeview_icon_size = QLabel(layout.tab__icon)
    layout.label__default_treeview_icon_size.setObjectName(
        "label__default_treeview_icon_size"
    )
    layout.label__default_treeview_icon_size.setText(preference_text("TreeView"))
    layout.horizontalLayout__default_treeview_icon_size.addWidget(
        layout.label__default_treeview_icon_size
    )
    layout.spinBox__default_treeview_icon_size = QSpinBox(layout.tab__icon)
    layout.spinBox__default_treeview_icon_size.setObjectName(
        "spinBox__default_treeview_icon_size"
    )
    layout.spinBox__default_treeview_icon_size.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.spinBox__default_treeview_icon_size.setFrame(False)
    layout.spinBox__default_treeview_icon_size.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.spinBox__default_treeview_icon_size.setMinimum(1)
    layout.spinBox__default_treeview_icon_size.setValue(24)
    layout.spinBox__default_treeview_icon_size.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_treeview_icon_size.addWidget(
        layout.spinBox__default_treeview_icon_size
    )
    layout.spacer__default_treeview_icon_size = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_treeview_icon_size.addItem(
        layout.spacer__default_treeview_icon_size
    )
    layout.verticalLayout__icon_sizes.addLayout(
        layout.horizontalLayout__default_treeview_icon_size
    )
    layout.tabWidget__view_settings.addTab(
        layout.tab__icon,
        QIcon(":/main/icons/ic_photo_white.png"),
        preference_text("Icon / Thumbnail"),
    )
