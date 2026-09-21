"""Item padding for assets and the category tree.

Part of the preference dialog layout; see widgets/preference/layout.py build_ui().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QIcon,
)
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from widgets.layout_helpers import preference_text

if TYPE_CHECKING:
    from widgets.preference.layout import PreferenceLayout


def build_item_padding(layout: PreferenceLayout, window: QDialog) -> None:
    layout.tab__padding = QWidget()
    layout.tab__padding.setObjectName("tab__padding")
    layout.horizontalLayout__padding_columns = QHBoxLayout(layout.tab__padding)
    layout.horizontalLayout__padding_columns.setSpacing(5)
    layout.horizontalLayout__padding_columns.setObjectName(
        "horizontalLayout__padding_columns"
    )
    layout.horizontalLayout__padding_columns.setContentsMargins(5, 5, 5, 5)
    build_asset_padding(layout, window)
    build_tree_padding(layout, window)


def build_asset_padding(layout: PreferenceLayout, window: QDialog) -> None:
    layout.verticalLayout__asset_padding = QVBoxLayout()
    layout.verticalLayout__asset_padding.setObjectName("verticalLayout__asset_padding")
    layout.horizontalLayout__default_list_item_padding = QHBoxLayout()
    layout.horizontalLayout__default_list_item_padding.setObjectName(
        "horizontalLayout__default_list_item_padding"
    )
    layout.label__default_list_item_padding = QLabel(layout.tab__padding)
    layout.label__default_list_item_padding.setObjectName(
        "label__default_list_item_padding"
    )
    layout.label__default_list_item_padding.setText(preference_text("List View"))
    layout.horizontalLayout__default_list_item_padding.addWidget(
        layout.label__default_list_item_padding
    )
    layout.spacer__default_list_item_padding = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_list_item_padding.addItem(
        layout.spacer__default_list_item_padding
    )
    layout.doubleSpinBox__default_list_item_padding = QDoubleSpinBox(
        layout.tab__padding
    )
    layout.doubleSpinBox__default_list_item_padding.setObjectName(
        "doubleSpinBox__default_list_item_padding"
    )
    layout.doubleSpinBox__default_list_item_padding.setFrame(False)
    layout.doubleSpinBox__default_list_item_padding.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_list_item_padding.setDecimals(1)
    layout.doubleSpinBox__default_list_item_padding.setMinimum(0.0)
    layout.doubleSpinBox__default_list_item_padding.setMaximum(100.0)
    layout.doubleSpinBox__default_list_item_padding.setSingleStep(0.1)
    layout.doubleSpinBox__default_list_item_padding.setValue(20.0)
    layout.doubleSpinBox__default_list_item_padding.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_list_item_padding.addWidget(
        layout.doubleSpinBox__default_list_item_padding
    )
    layout.verticalLayout__asset_padding.addLayout(
        layout.horizontalLayout__default_list_item_padding
    )
    layout.horizontalLayout__default_table_item_padding = QHBoxLayout()
    layout.horizontalLayout__default_table_item_padding.setObjectName(
        "horizontalLayout__default_table_item_padding"
    )
    layout.label__default_table_item_padding = QLabel(layout.tab__padding)
    layout.label__default_table_item_padding.setObjectName(
        "label__default_table_item_padding"
    )
    layout.label__default_table_item_padding.setText(preference_text("Table View"))
    layout.horizontalLayout__default_table_item_padding.addWidget(
        layout.label__default_table_item_padding
    )
    layout.spacer__default_table_item_padding = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_table_item_padding.addItem(
        layout.spacer__default_table_item_padding
    )
    layout.doubleSpinBox__default_table_item_padding = QDoubleSpinBox(
        layout.tab__padding
    )
    layout.doubleSpinBox__default_table_item_padding.setObjectName(
        "doubleSpinBox__default_table_item_padding"
    )
    layout.doubleSpinBox__default_table_item_padding.setFrame(False)
    layout.doubleSpinBox__default_table_item_padding.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_table_item_padding.setDecimals(1)
    layout.doubleSpinBox__default_table_item_padding.setMinimum(0.0)
    layout.doubleSpinBox__default_table_item_padding.setMaximum(100.0)
    layout.doubleSpinBox__default_table_item_padding.setSingleStep(0.1)
    layout.doubleSpinBox__default_table_item_padding.setValue(0.0)
    layout.doubleSpinBox__default_table_item_padding.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_table_item_padding.addWidget(
        layout.doubleSpinBox__default_table_item_padding
    )
    layout.verticalLayout__asset_padding.addLayout(
        layout.horizontalLayout__default_table_item_padding
    )
    layout.horizontalLayout__default_history_item_padding = QHBoxLayout()
    layout.horizontalLayout__default_history_item_padding.setObjectName(
        "horizontalLayout__default_history_item_padding"
    )
    layout.label__default_history_item_padding = QLabel(layout.tab__padding)
    layout.label__default_history_item_padding.setObjectName(
        "label__default_history_item_padding"
    )
    layout.label__default_history_item_padding.setText(preference_text("History View"))
    layout.horizontalLayout__default_history_item_padding.addWidget(
        layout.label__default_history_item_padding
    )
    layout.spacer__default_history_item_padding = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_history_item_padding.addItem(
        layout.spacer__default_history_item_padding
    )
    layout.doubleSpinBox__default_history_item_padding = QDoubleSpinBox(
        layout.tab__padding
    )
    layout.doubleSpinBox__default_history_item_padding.setObjectName(
        "doubleSpinBox__default_history_item_padding"
    )
    layout.doubleSpinBox__default_history_item_padding.setFrame(False)
    layout.doubleSpinBox__default_history_item_padding.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_history_item_padding.setDecimals(1)
    layout.doubleSpinBox__default_history_item_padding.setMinimum(0.0)
    layout.doubleSpinBox__default_history_item_padding.setMaximum(100.0)
    layout.doubleSpinBox__default_history_item_padding.setSingleStep(0.1)
    layout.doubleSpinBox__default_history_item_padding.setValue(0.0)
    layout.doubleSpinBox__default_history_item_padding.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_history_item_padding.addWidget(
        layout.doubleSpinBox__default_history_item_padding
    )
    layout.verticalLayout__asset_padding.addLayout(
        layout.horizontalLayout__default_history_item_padding
    )
    layout.horizontalLayout__padding_columns.addLayout(
        layout.verticalLayout__asset_padding
    )
    layout.spacer__padding_columns = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__padding_columns.addItem(layout.spacer__padding_columns)


def build_tree_padding(layout: PreferenceLayout, window: QDialog) -> None:
    layout.verticalLayout__tree_padding = QVBoxLayout()
    layout.verticalLayout__tree_padding.setObjectName("verticalLayout__tree_padding")
    layout.horizontalLayout__default_cate_item_padding = QHBoxLayout()
    layout.horizontalLayout__default_cate_item_padding.setObjectName(
        "horizontalLayout__default_cate_item_padding"
    )
    layout.label__default_cate_item_padding = QLabel(layout.tab__padding)
    layout.label__default_cate_item_padding.setObjectName(
        "label__default_cate_item_padding"
    )
    layout.label__default_cate_item_padding.setText(preference_text("Category View"))
    layout.horizontalLayout__default_cate_item_padding.addWidget(
        layout.label__default_cate_item_padding
    )
    layout.spacer__default_cate_item_padding = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_cate_item_padding.addItem(
        layout.spacer__default_cate_item_padding
    )
    layout.doubleSpinBox__default_cate_item_padding = QDoubleSpinBox(
        layout.tab__padding
    )
    layout.doubleSpinBox__default_cate_item_padding.setObjectName(
        "doubleSpinBox__default_cate_item_padding"
    )
    layout.doubleSpinBox__default_cate_item_padding.setFrame(False)
    layout.doubleSpinBox__default_cate_item_padding.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_cate_item_padding.setDecimals(1)
    layout.doubleSpinBox__default_cate_item_padding.setMinimum(0.0)
    layout.doubleSpinBox__default_cate_item_padding.setMaximum(100.0)
    layout.doubleSpinBox__default_cate_item_padding.setSingleStep(0.1)
    layout.doubleSpinBox__default_cate_item_padding.setValue(15.0)
    layout.doubleSpinBox__default_cate_item_padding.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_cate_item_padding.addWidget(
        layout.doubleSpinBox__default_cate_item_padding
    )
    layout.verticalLayout__tree_padding.addLayout(
        layout.horizontalLayout__default_cate_item_padding
    )
    layout.horizontalLayout__default_record_item_padding = QHBoxLayout()
    layout.horizontalLayout__default_record_item_padding.setObjectName(
        "horizontalLayout__default_record_item_padding"
    )
    layout.label__default_record_item_padding = QLabel(layout.tab__padding)
    layout.label__default_record_item_padding.setObjectName(
        "label__default_record_item_padding"
    )
    layout.label__default_record_item_padding.setText(preference_text("Record View"))
    layout.horizontalLayout__default_record_item_padding.addWidget(
        layout.label__default_record_item_padding
    )
    layout.spacer__default_record_item_padding = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_record_item_padding.addItem(
        layout.spacer__default_record_item_padding
    )
    layout.doubleSpinBox__default_record_item_padding = QDoubleSpinBox(
        layout.tab__padding
    )
    layout.doubleSpinBox__default_record_item_padding.setObjectName(
        "doubleSpinBox__default_record_item_padding"
    )
    layout.doubleSpinBox__default_record_item_padding.setFrame(False)
    layout.doubleSpinBox__default_record_item_padding.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_record_item_padding.setDecimals(1)
    layout.doubleSpinBox__default_record_item_padding.setMinimum(0.0)
    layout.doubleSpinBox__default_record_item_padding.setMaximum(100.0)
    layout.doubleSpinBox__default_record_item_padding.setSingleStep(0.1)
    layout.doubleSpinBox__default_record_item_padding.setValue(5.0)
    layout.doubleSpinBox__default_record_item_padding.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_record_item_padding.addWidget(
        layout.doubleSpinBox__default_record_item_padding
    )
    layout.verticalLayout__tree_padding.addLayout(
        layout.horizontalLayout__default_record_item_padding
    )
    layout.horizontalLayout__default_inside_item_padding = QHBoxLayout()
    layout.horizontalLayout__default_inside_item_padding.setObjectName(
        "horizontalLayout__default_inside_item_padding"
    )
    layout.label__default_inside_item_padding = QLabel(layout.tab__padding)
    layout.label__default_inside_item_padding.setObjectName(
        "label__default_inside_item_padding"
    )
    layout.label__default_inside_item_padding.setText(preference_text("Inside View"))
    layout.horizontalLayout__default_inside_item_padding.addWidget(
        layout.label__default_inside_item_padding
    )
    layout.spacer__default_inside_item_padding = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__default_inside_item_padding.addItem(
        layout.spacer__default_inside_item_padding
    )
    layout.doubleSpinBox__default_inside_item_padding = QDoubleSpinBox(
        layout.tab__padding
    )
    layout.doubleSpinBox__default_inside_item_padding.setObjectName(
        "doubleSpinBox__default_inside_item_padding"
    )
    layout.doubleSpinBox__default_inside_item_padding.setFrame(False)
    layout.doubleSpinBox__default_inside_item_padding.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    layout.doubleSpinBox__default_inside_item_padding.setDecimals(1)
    layout.doubleSpinBox__default_inside_item_padding.setMinimum(0.0)
    layout.doubleSpinBox__default_inside_item_padding.setMaximum(100.0)
    layout.doubleSpinBox__default_inside_item_padding.setSingleStep(0.1)
    layout.doubleSpinBox__default_inside_item_padding.setValue(5.0)
    layout.doubleSpinBox__default_inside_item_padding.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_inside_item_padding.addWidget(
        layout.doubleSpinBox__default_inside_item_padding
    )
    layout.verticalLayout__tree_padding.addLayout(
        layout.horizontalLayout__default_inside_item_padding
    )
    layout.horizontalLayout__padding_columns.addLayout(
        layout.verticalLayout__tree_padding
    )
    layout.tabWidget__view_settings.addTab(
        layout.tab__padding,
        QIcon(":/main/icons/ic_settings_overscan_white.png"),
        preference_text("Padding"),
    )
