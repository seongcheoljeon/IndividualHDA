"""Appearance and fonts (note, tag, debug console).

Part of the preference dialog layout; see widgets/preference/layout.py build_ui().
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
    QDialog,
    QFontComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from libs.ui_icons import Icon
from widgets.layout_helpers import preference_text
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

if TYPE_CHECKING:
    from widgets.preference.layout import PreferenceLayout


def build_appearance_settings(layout: PreferenceLayout, window: QDialog) -> None:
    layout.groupBox__app_properties = QGroupBox(window)
    layout.groupBox__app_properties.setObjectName("groupBox__app_properties")
    layout.groupBox__app_properties.setTitle(
        preference_text("APP Properties (Default)")
    )
    layout.horizontalLayout__appearance = QHBoxLayout(layout.groupBox__app_properties)
    layout.horizontalLayout__appearance.setObjectName("horizontalLayout__appearance")
    layout.horizontalLayout__appearance.setContentsMargins(5, 5, 5, 5)
    layout.pushButton__reset_default_app_properties = QPushButton(
        layout.groupBox__app_properties
    )
    layout.pushButton__reset_default_app_properties.setObjectName(
        "pushButton__reset_default_app_properties"
    )
    layout.pushButton__reset_default_app_properties.setMaximumSize(QSize(55, 55))
    layout.pushButton__reset_default_app_properties.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.pushButton__reset_default_app_properties.setIcon(
        QIcon(Icon.IC_REFRESH_WHITE)
    )
    layout.pushButton__reset_default_app_properties.setIconSize(QSize(50, 50))
    layout.pushButton__reset_default_app_properties.setFlat(True)
    layout.pushButton__reset_default_app_properties.setToolTip(
        preference_text("Initialize app properties to default values")
    )
    layout.pushButton__reset_default_app_properties.setText("")
    layout.horizontalLayout__appearance.addWidget(
        layout.pushButton__reset_default_app_properties
    )
    layout.verticalLayout__appearance_groups = QVBoxLayout()
    layout.verticalLayout__appearance_groups.setObjectName(
        "verticalLayout__appearance_groups"
    )
    layout.groupBox__main_icons = QGroupBox(layout.groupBox__app_properties)
    layout.groupBox__main_icons.setObjectName("groupBox__main_icons")
    layout.groupBox__main_icons.setTitle(preference_text("Main View"))
    layout.verticalLayout__main_icons = QVBoxLayout(layout.groupBox__main_icons)
    layout.verticalLayout__main_icons.setObjectName("verticalLayout__main_icons")
    layout.horizontalLayout__default_main_icon_size = QHBoxLayout()
    layout.horizontalLayout__default_main_icon_size.setObjectName(
        "horizontalLayout__default_main_icon_size"
    )
    layout.label__default_main_icon_size = QLabel(layout.groupBox__main_icons)
    layout.label__default_main_icon_size.setObjectName("label__default_main_icon_size")
    layout.label__default_main_icon_size.setText(preference_text("Icon"))
    layout.horizontalLayout__default_main_icon_size.addWidget(
        layout.label__default_main_icon_size
    )
    layout.spinBox__default_main_icon_size = QSpinBox(layout.groupBox__main_icons)
    layout.spinBox__default_main_icon_size.setObjectName(
        "spinBox__default_main_icon_size"
    )
    layout.spinBox__default_main_icon_size.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.spinBox__default_main_icon_size.setFrame(False)
    layout.spinBox__default_main_icon_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.spinBox__default_main_icon_size.setMinimum(1)
    layout.spinBox__default_main_icon_size.setMaximum(30)
    layout.spinBox__default_main_icon_size.setValue(20)
    layout.spinBox__default_main_icon_size.setSuffix(preference_text("px"))
    layout.horizontalLayout__default_main_icon_size.addWidget(
        layout.spinBox__default_main_icon_size
    )
    layout.verticalLayout__main_icons.addLayout(
        layout.horizontalLayout__default_main_icon_size
    )
    layout.verticalLayout__appearance_groups.addWidget(layout.groupBox__main_icons)
    layout.groupBox__default_icon = QGroupBox(layout.groupBox__app_properties)
    layout.groupBox__default_icon.setObjectName("groupBox__default_icon")
    layout.groupBox__default_icon.setTitle(preference_text("Item View"))
    layout.verticalLayout__view_settings = QVBoxLayout(layout.groupBox__default_icon)
    layout.verticalLayout__view_settings.setObjectName("verticalLayout__view_settings")
    layout.horizontalLayout__view_font_size = QHBoxLayout()
    layout.horizontalLayout__view_font_size.setObjectName(
        "horizontalLayout__view_font_size"
    )
    layout.horizontalLayout__view_font_size_row = QHBoxLayout()
    layout.horizontalLayout__view_font_size_row.setObjectName(
        "horizontalLayout__view_font_size_row"
    )
    layout.label__view_font_size = QLabel(layout.groupBox__default_icon)
    layout.label__view_font_size.setObjectName("label__view_font_size")
    layout.label__view_font_size.setText(preference_text("Font Size"))
    layout.horizontalLayout__view_font_size_row.addWidget(layout.label__view_font_size)
    layout.spinBox__view_font_size = QSpinBox(layout.groupBox__default_icon)
    layout.spinBox__view_font_size.setObjectName("spinBox__view_font_size")
    layout.spinBox__view_font_size.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    layout.spinBox__view_font_size.setFrame(False)
    layout.spinBox__view_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.spinBox__view_font_size.setMinimum(2)
    layout.spinBox__view_font_size.setMaximum(50)
    layout.spinBox__view_font_size.setValue(11)
    layout.horizontalLayout__view_font_size_row.addWidget(
        layout.spinBox__view_font_size
    )
    layout.horizontalLayout__view_font_size.addLayout(
        layout.horizontalLayout__view_font_size_row
    )
    layout.spacer__view_font_size = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__view_font_size.addItem(layout.spacer__view_font_size)
    layout.horizontalLayout__view_font_style = QHBoxLayout()
    layout.horizontalLayout__view_font_style.setObjectName(
        "horizontalLayout__view_font_style"
    )
    layout.label__view_font_style = QLabel(layout.groupBox__default_icon)
    layout.label__view_font_style.setObjectName("label__view_font_style")
    layout.label__view_font_style.setText(preference_text("Font Style"))
    layout.horizontalLayout__view_font_style.addWidget(layout.label__view_font_style)
    layout.fontComboBox__view_font_style = QFontComboBox(layout.groupBox__default_icon)
    layout.fontComboBox__view_font_style.setObjectName("fontComboBox__view_font_style")
    layout.fontComboBox__view_font_style.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.fontComboBox__view_font_style.setFrame(False)
    layout.horizontalLayout__view_font_style.addWidget(
        layout.fontComboBox__view_font_style
    )
    layout.horizontalLayout__view_font_size.addLayout(
        layout.horizontalLayout__view_font_style
    )
    layout.verticalLayout__view_settings.addLayout(
        layout.horizontalLayout__view_font_size
    )
    layout.line__view_settings = QFrame(layout.groupBox__default_icon)
    layout.line__view_settings.setObjectName("line__view_settings")
    layout.line__view_settings.setFrameShape(QFrame.Shape.HLine)
    layout.line__view_settings.setFrameShadow(QFrame.Shadow.Sunken)
    layout.verticalLayout__view_settings.addWidget(layout.line__view_settings)
    layout.tabWidget__view_settings = QTabWidget(layout.groupBox__default_icon)
    layout.tabWidget__view_settings.setObjectName("tabWidget__view_settings")
    layout.tabWidget__view_settings.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )


def build_note_font(layout: PreferenceLayout, window: QDialog) -> None:
    layout.tab__text = QWidget()
    layout.tab__text.setObjectName("tab__text")
    layout.verticalLayout__text_settings = QVBoxLayout(layout.tab__text)
    layout.verticalLayout__text_settings.setSpacing(5)
    layout.verticalLayout__text_settings.setObjectName("verticalLayout__text_settings")
    layout.verticalLayout__text_settings.setContentsMargins(5, 5, 5, 5)
    layout.groupBox__note = QGroupBox(layout.tab__text)
    layout.groupBox__note.setObjectName("groupBox__note")
    layout.groupBox__note.setTitle(preference_text("Note"))
    layout.verticalLayout__note_font_size = QVBoxLayout(layout.groupBox__note)
    layout.verticalLayout__note_font_size.setObjectName(
        "verticalLayout__note_font_size"
    )
    layout.horizontalLayout__note_font_size = QHBoxLayout()
    layout.horizontalLayout__note_font_size.setSpacing(15)
    layout.horizontalLayout__note_font_size.setObjectName(
        "horizontalLayout__note_font_size"
    )
    layout.horizontalLayout__note_font_size_row = QHBoxLayout()
    layout.horizontalLayout__note_font_size_row.setObjectName(
        "horizontalLayout__note_font_size_row"
    )
    layout.label__note_font_size = QLabel(layout.groupBox__note)
    layout.label__note_font_size.setObjectName("label__note_font_size")
    layout.label__note_font_size.setText(preference_text("Font Size"))
    layout.horizontalLayout__note_font_size_row.addWidget(layout.label__note_font_size)
    layout.spinBox__note_font_size = QSpinBox(layout.groupBox__note)
    layout.spinBox__note_font_size.setObjectName("spinBox__note_font_size")
    layout.spinBox__note_font_size.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    layout.spinBox__note_font_size.setFrame(False)
    layout.spinBox__note_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.spinBox__note_font_size.setMinimum(2)
    layout.spinBox__note_font_size.setMaximum(50)
    layout.spinBox__note_font_size.setValue(11)
    layout.horizontalLayout__note_font_size_row.addWidget(
        layout.spinBox__note_font_size
    )
    layout.horizontalLayout__note_font_size.addLayout(
        layout.horizontalLayout__note_font_size_row
    )
    layout.spacer__note_font_size = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__note_font_size.addItem(layout.spacer__note_font_size)
    layout.horizontalLayout__note_font_style = QHBoxLayout()
    layout.horizontalLayout__note_font_style.setObjectName(
        "horizontalLayout__note_font_style"
    )
    layout.label__note_font_style = QLabel(layout.groupBox__note)
    layout.label__note_font_style.setObjectName("label__note_font_style")
    layout.label__note_font_style.setText(preference_text("Font Style"))
    layout.horizontalLayout__note_font_style.addWidget(layout.label__note_font_style)
    layout.fontComboBox__note_font_style = QFontComboBox(layout.groupBox__note)
    layout.fontComboBox__note_font_style.setObjectName("fontComboBox__note_font_style")
    layout.fontComboBox__note_font_style.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.fontComboBox__note_font_style.setFrame(False)
    layout.horizontalLayout__note_font_style.addWidget(
        layout.fontComboBox__note_font_style
    )
    layout.horizontalLayout__note_font_size.addLayout(
        layout.horizontalLayout__note_font_style
    )
    layout.verticalLayout__note_font_size.addLayout(
        layout.horizontalLayout__note_font_size
    )
    layout.verticalLayout__text_settings.addWidget(layout.groupBox__note)


def build_tag_font(layout: PreferenceLayout, window: QDialog) -> None:
    layout.groupBox__tags = QGroupBox(layout.tab__text)
    layout.groupBox__tags.setObjectName("groupBox__tags")
    layout.groupBox__tags.setTitle(preference_text("Tags"))
    layout.verticalLayout__tags_font_size = QVBoxLayout(layout.groupBox__tags)
    layout.verticalLayout__tags_font_size.setObjectName(
        "verticalLayout__tags_font_size"
    )
    layout.horizontalLayout__tags_font_size = QHBoxLayout()
    layout.horizontalLayout__tags_font_size.setSpacing(15)
    layout.horizontalLayout__tags_font_size.setObjectName(
        "horizontalLayout__tags_font_size"
    )
    layout.horizontalLayout__tags_font_size_row = QHBoxLayout()
    layout.horizontalLayout__tags_font_size_row.setObjectName(
        "horizontalLayout__tags_font_size_row"
    )
    layout.label__tags_font_size = QLabel(layout.groupBox__tags)
    layout.label__tags_font_size.setObjectName("label__tags_font_size")
    layout.label__tags_font_size.setText(preference_text("Font Size"))
    layout.horizontalLayout__tags_font_size_row.addWidget(layout.label__tags_font_size)
    layout.spinBox__tags_font_size = QSpinBox(layout.groupBox__tags)
    layout.spinBox__tags_font_size.setObjectName("spinBox__tags_font_size")
    layout.spinBox__tags_font_size.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    layout.spinBox__tags_font_size.setFrame(False)
    layout.spinBox__tags_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.spinBox__tags_font_size.setMinimum(2)
    layout.spinBox__tags_font_size.setMaximum(50)
    layout.spinBox__tags_font_size.setValue(11)
    layout.horizontalLayout__tags_font_size_row.addWidget(
        layout.spinBox__tags_font_size
    )
    layout.horizontalLayout__tags_font_size.addLayout(
        layout.horizontalLayout__tags_font_size_row
    )
    layout.spacer__tags_font_size = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__tags_font_size.addItem(layout.spacer__tags_font_size)
    layout.horizontalLayout__tags_font_style = QHBoxLayout()
    layout.horizontalLayout__tags_font_style.setObjectName(
        "horizontalLayout__tags_font_style"
    )
    layout.label__tags_font_style = QLabel(layout.groupBox__tags)
    layout.label__tags_font_style.setObjectName("label__tags_font_style")
    layout.label__tags_font_style.setText(preference_text("Font Style"))
    layout.horizontalLayout__tags_font_style.addWidget(layout.label__tags_font_style)
    layout.fontComboBox__tags_font_style = QFontComboBox(layout.groupBox__tags)
    layout.fontComboBox__tags_font_style.setObjectName("fontComboBox__tags_font_style")
    layout.fontComboBox__tags_font_style.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.fontComboBox__tags_font_style.setFrame(False)
    layout.horizontalLayout__tags_font_style.addWidget(
        layout.fontComboBox__tags_font_style
    )
    layout.horizontalLayout__tags_font_size.addLayout(
        layout.horizontalLayout__tags_font_style
    )
    layout.verticalLayout__tags_font_size.addLayout(
        layout.horizontalLayout__tags_font_size
    )
    layout.verticalLayout__text_settings.addWidget(layout.groupBox__tags)


def build_debug_font(layout: PreferenceLayout, window: QDialog) -> None:
    layout.groupBox__debug = QGroupBox(layout.tab__text)
    layout.groupBox__debug.setObjectName("groupBox__debug")
    layout.groupBox__debug.setTitle(preference_text("Debug"))
    layout.verticalLayout__debug_font_size = QVBoxLayout(layout.groupBox__debug)
    layout.verticalLayout__debug_font_size.setObjectName(
        "verticalLayout__debug_font_size"
    )
    layout.horizontalLayout__debug_font_size = QHBoxLayout()
    layout.horizontalLayout__debug_font_size.setSpacing(15)
    layout.horizontalLayout__debug_font_size.setObjectName(
        "horizontalLayout__debug_font_size"
    )
    layout.horizontalLayout__debug_font_size_row = QHBoxLayout()
    layout.horizontalLayout__debug_font_size_row.setObjectName(
        "horizontalLayout__debug_font_size_row"
    )
    layout.label__debug_font_size = QLabel(layout.groupBox__debug)
    layout.label__debug_font_size.setObjectName("label__debug_font_size")
    layout.label__debug_font_size.setText(preference_text("Font Size"))
    layout.horizontalLayout__debug_font_size_row.addWidget(
        layout.label__debug_font_size
    )
    layout.spinBox__debug_font_size = QSpinBox(layout.groupBox__debug)
    layout.spinBox__debug_font_size.setObjectName("spinBox__debug_font_size")
    layout.spinBox__debug_font_size.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.spinBox__debug_font_size.setFrame(False)
    layout.spinBox__debug_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.spinBox__debug_font_size.setMinimum(2)
    layout.spinBox__debug_font_size.setMaximum(50)
    layout.spinBox__debug_font_size.setValue(11)
    layout.horizontalLayout__debug_font_size_row.addWidget(
        layout.spinBox__debug_font_size
    )
    layout.horizontalLayout__debug_font_size.addLayout(
        layout.horizontalLayout__debug_font_size_row
    )
    layout.spacer__debug_font_size = QSpacerItem(
        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout.horizontalLayout__debug_font_size.addItem(layout.spacer__debug_font_size)
    layout.horizontalLayout__debug_font_style = QHBoxLayout()
    layout.horizontalLayout__debug_font_style.setObjectName(
        "horizontalLayout__debug_font_style"
    )
    layout.label__debug_font_style = QLabel(layout.groupBox__debug)
    layout.label__debug_font_style.setObjectName("label__debug_font_style")
    layout.label__debug_font_style.setText(preference_text("Font Style"))
    layout.horizontalLayout__debug_font_style.addWidget(layout.label__debug_font_style)
    layout.fontComboBox__debug_font_style = QFontComboBox(layout.groupBox__debug)
    layout.fontComboBox__debug_font_style.setObjectName(
        "fontComboBox__debug_font_style"
    )
    layout.fontComboBox__debug_font_style.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.fontComboBox__debug_font_style.setFrame(False)
    layout.horizontalLayout__debug_font_style.addWidget(
        layout.fontComboBox__debug_font_style
    )
    layout.horizontalLayout__debug_font_size.addLayout(
        layout.horizontalLayout__debug_font_style
    )
    layout.verticalLayout__debug_font_size.addLayout(
        layout.horizontalLayout__debug_font_size
    )
    layout.verticalLayout__text_settings.addWidget(layout.groupBox__debug)
    layout.tabWidget__view_settings.addTab(
        layout.tab__text, QIcon(Icon.CASE_SENSITIVE), preference_text("Text")
    )
    layout.verticalLayout__view_settings.addWidget(layout.tabWidget__view_settings)
    layout.verticalLayout__appearance_groups.addWidget(layout.groupBox__default_icon)
    layout.horizontalLayout__appearance.addLayout(
        layout.verticalLayout__appearance_groups
    )
    layout.verticalLayout__preferences.addWidget(layout.groupBox__app_properties)
