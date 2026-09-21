"""Code-built Preference layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QLocale,
    Qt,
)
from PySide6.QtGui import (
    QIcon,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpacerItem,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from libs.ui_icons import Icon
from widgets.layout_helpers import make_font, preference_text
from widgets.preference.layout_appearance import (
    build_appearance_settings,
    build_debug_font,
    build_note_font,
    build_tag_font,
)
from widgets.preference.layout_icons import (
    build_icon_sizes,
)
from widgets.preference.layout_padding import (
    build_item_padding,
)
from widgets.preference.layout_storage import (
    build_ffmpeg_settings,
    build_storage_settings,
)

from . import preference_icons_rc  # noqa: F401 (register bundled icons)


class PreferenceLayout:
    # Widgets built by the section modules (layout_*.py); declared here so they
    # are members of the layout like the ones built in this file.
    doubleSpinBox__default_cate_item_padding: QDoubleSpinBox
    doubleSpinBox__default_history_item_padding: QDoubleSpinBox
    doubleSpinBox__default_inside_item_padding: QDoubleSpinBox
    doubleSpinBox__default_list_item_padding: QDoubleSpinBox
    doubleSpinBox__default_listview_thumb_scale: QDoubleSpinBox
    doubleSpinBox__default_record_item_padding: QDoubleSpinBox
    doubleSpinBox__default_table_item_padding: QDoubleSpinBox
    doubleSpinBox__default_tableview_thumb_scale: QDoubleSpinBox
    fontComboBox__debug_font_style: QFontComboBox
    fontComboBox__note_font_style: QFontComboBox
    fontComboBox__tags_font_style: QFontComboBox
    fontComboBox__view_font_style: QFontComboBox
    groupBox__app_properties: QGroupBox
    groupBox__data: QGroupBox
    groupBox__debug: QGroupBox
    groupBox__default_icon: QGroupBox
    groupBox__ffmpeg: QGroupBox
    groupBox__main_icons: QGroupBox
    groupBox__note: QGroupBox
    groupBox__tags: QGroupBox
    horizontalLayout__appearance: QHBoxLayout
    horizontalLayout__data_dirpath: QHBoxLayout
    horizontalLayout__debug_font_size: QHBoxLayout
    horizontalLayout__debug_font_size_row: QHBoxLayout
    horizontalLayout__debug_font_style: QHBoxLayout
    horizontalLayout__default_cate_item_padding: QHBoxLayout
    horizontalLayout__default_history_item_padding: QHBoxLayout
    horizontalLayout__default_inside_item_padding: QHBoxLayout
    horizontalLayout__default_list_item_padding: QHBoxLayout
    horizontalLayout__default_listview_icon_size: QHBoxLayout
    horizontalLayout__default_listview_icon_size_row: QHBoxLayout
    horizontalLayout__default_listview_thumb_scale: QHBoxLayout
    horizontalLayout__default_main_icon_size: QHBoxLayout
    horizontalLayout__default_record_item_padding: QHBoxLayout
    horizontalLayout__default_table_item_padding: QHBoxLayout
    horizontalLayout__default_tableview_icon_size: QHBoxLayout
    horizontalLayout__default_tableview_icon_size_row: QHBoxLayout
    horizontalLayout__default_tableview_thumb_scale: QHBoxLayout
    horizontalLayout__default_treeview_icon_size: QHBoxLayout
    horizontalLayout__ffmpeg_dirpath: QHBoxLayout
    horizontalLayout__ffmpeg_pixmap: QHBoxLayout
    horizontalLayout__ffmpeg_result_show: QHBoxLayout
    horizontalLayout__note_font_size: QHBoxLayout
    horizontalLayout__note_font_size_row: QHBoxLayout
    horizontalLayout__note_font_style: QHBoxLayout
    horizontalLayout__padding_columns: QHBoxLayout
    horizontalLayout__pixmap: QHBoxLayout
    horizontalLayout__result_show: QHBoxLayout
    horizontalLayout__tags_font_size: QHBoxLayout
    horizontalLayout__tags_font_size_row: QHBoxLayout
    horizontalLayout__tags_font_style: QHBoxLayout
    horizontalLayout__view_font_size: QHBoxLayout
    horizontalLayout__view_font_size_row: QHBoxLayout
    horizontalLayout__view_font_style: QHBoxLayout
    label__data_dirpath: QLabel
    label__debug_font_size: QLabel
    label__debug_font_style: QLabel
    label__default_cate_item_padding: QLabel
    label__default_history_item_padding: QLabel
    label__default_inside_item_padding: QLabel
    label__default_list_item_padding: QLabel
    label__default_listview_icon_size: QLabel
    label__default_listview_thumb_scale: QLabel
    label__default_main_icon_size: QLabel
    label__default_record_item_padding: QLabel
    label__default_table_item_padding: QLabel
    label__default_tableview_icon_size: QLabel
    label__default_tableview_thumb_scale: QLabel
    label__default_treeview_icon_size: QLabel
    label__ffmpeg_dirpath: QLabel
    label__ffmpeg_pixmap: QLabel
    label__ffmpeg_result_show: QLabel
    label__ffmpeg_valid_chk_pixmap: QLabel
    label__note_font_size: QLabel
    label__note_font_style: QLabel
    label__pixmap: QLabel
    label__result_show: QLabel
    label__tags_font_size: QLabel
    label__tags_font_style: QLabel
    label__valid_chk_pixmap: QLabel
    label__view_font_size: QLabel
    label__view_font_style: QLabel
    lineEdit__data_dirpath: QLineEdit
    lineEdit__ffmpeg_dirpath: QLineEdit
    lineEdit__ffmpeg_result: QLineEdit
    lineEdit__result: QLineEdit
    line__view_settings: QFrame
    pushButton__reset_default_app_properties: QPushButton
    spacer__debug_font_size: QSpacerItem
    spacer__default_cate_item_padding: QSpacerItem
    spacer__default_history_item_padding: QSpacerItem
    spacer__default_inside_item_padding: QSpacerItem
    spacer__default_list_item_padding: QSpacerItem
    spacer__default_listview_icon_size: QSpacerItem
    spacer__default_listview_thumb_scale: QSpacerItem
    spacer__default_record_item_padding: QSpacerItem
    spacer__default_table_item_padding: QSpacerItem
    spacer__default_tableview_icon_size: QSpacerItem
    spacer__default_tableview_thumb_scale: QSpacerItem
    spacer__default_treeview_icon_size: QSpacerItem
    spacer__note_font_size: QSpacerItem
    spacer__padding_columns: QSpacerItem
    spacer__tags_font_size: QSpacerItem
    spacer__view_font_size: QSpacerItem
    spinBox__debug_font_size: QSpinBox
    spinBox__default_listview_icon_size: QSpinBox
    spinBox__default_main_icon_size: QSpinBox
    spinBox__default_tableview_icon_size: QSpinBox
    spinBox__default_treeview_icon_size: QSpinBox
    spinBox__note_font_size: QSpinBox
    spinBox__tags_font_size: QSpinBox
    spinBox__view_font_size: QSpinBox
    tabWidget__view_settings: QTabWidget
    tab__icon: QWidget
    tab__padding: QWidget
    tab__text: QWidget
    toolButton__select_data_dirpath: QToolButton
    toolButton__select_ffmpeg_dirpath: QToolButton
    verticalLayout__appearance_groups: QVBoxLayout
    verticalLayout__asset_padding: QVBoxLayout
    verticalLayout__data_dirpath: QVBoxLayout
    verticalLayout__debug_font_size: QVBoxLayout
    verticalLayout__ffmpeg_dirpath: QVBoxLayout
    verticalLayout__icon_sizes: QVBoxLayout
    verticalLayout__main_icons: QVBoxLayout
    verticalLayout__note_font_size: QVBoxLayout
    verticalLayout__tags_font_size: QVBoxLayout
    verticalLayout__text_settings: QVBoxLayout
    verticalLayout__tree_padding: QVBoxLayout
    verticalLayout__view_settings: QVBoxLayout

    def build_ui(self, window: QDialog) -> None:
        self._configure_window(window)
        build_storage_settings(self, window)
        build_ffmpeg_settings(self, window)
        build_appearance_settings(self, window)
        build_icon_sizes(self, window)
        build_item_padding(self, window)
        build_note_font(self, window)
        build_tag_font(self, window)
        build_debug_font(self, window)
        self._build_dialog_buttons(window)

    def _configure_window(self, window: QDialog) -> None:
        if not window.objectName():
            window.setObjectName("Dialog__preference")
        window.resize(817, 889)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(Icon.VIEWPORT_LOGO_TRANS))
        window.setLocale(
            QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        )
        window.setWindowTitle(preference_text("iHDA Preference"))
        self.verticalLayout__preference_shell = QVBoxLayout(window)
        self.verticalLayout__preference_shell.setObjectName(
            "verticalLayout__preference_shell"
        )
        self.scrollArea__preferences = QScrollArea(window)
        self.scrollArea__preferences.setObjectName("scrollArea__preferences")
        self.scrollArea__preferences.setWidgetResizable(True)
        self.scrollArea__preferences.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(self.scrollArea__preferences)
        content.setObjectName("widget__preference_content")
        self.scrollArea__preferences.setWidget(content)
        self.verticalLayout__preference_shell.addWidget(self.scrollArea__preferences)
        self.verticalLayout__preferences = QVBoxLayout(content)
        self.verticalLayout__preferences.setSpacing(5)
        self.verticalLayout__preferences.setObjectName("verticalLayout__preferences")
        self.verticalLayout__preferences.setContentsMargins(6, 6, 6, 6)

    def _build_dialog_buttons(self, window: QDialog) -> None:
        self.buttonBox__confirm = QDialogButtonBox(window)
        self.buttonBox__confirm.setObjectName("buttonBox__confirm")
        self.buttonBox__confirm.setLocale(
            QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        )
        self.buttonBox__confirm.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox__confirm.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.verticalLayout__preference_shell.addWidget(self.buttonBox__confirm)
        self.buttonBox__confirm.accepted.connect(window.accept)
        self.buttonBox__confirm.rejected.connect(window.reject)
        self.tabWidget__view_settings.setCurrentIndex(0)
