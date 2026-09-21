"""Code-built Preference layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
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
    QListWidget,
    QScrollArea,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
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
        self.add_page(preference_text("Storage"))
        build_storage_settings(self, window)
        build_ffmpeg_settings(self, window)
        self.add_page(preference_text("Appearance"))
        build_appearance_settings(self, window)
        build_icon_sizes(self, window)
        build_item_padding(self, window)
        build_note_font(self, window)
        build_tag_font(self, window)
        build_debug_font(self, window)
        self._build_dialog_buttons(window)
        self.listWidget__pages.setCurrentRow(0)

    def _configure_window(self, window: QDialog) -> None:
        if not window.objectName():
            window.setObjectName("Dialog__preference")
        window.resize(760, 600)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(Icon.VIEWPORT_LOGO_TRANS))
        window.setWindowTitle(preference_text("iHDA Preference"))
        self.pages: dict[str, tuple[QScrollArea, QWidget]] = {}
        self.verticalLayout__preference_shell = QVBoxLayout(window)
        self.verticalLayout__preference_shell.setObjectName(
            "verticalLayout__preference_shell"
        )
        self.horizontalLayout__pages = QHBoxLayout()
        self.horizontalLayout__pages.setObjectName("horizontalLayout__pages")
        self.horizontalLayout__pages.setSpacing(8)
        self.listWidget__pages = QListWidget(window)
        self.listWidget__pages.setObjectName("listWidget__pages")
        self.listWidget__pages.setFixedWidth(150)
        self.listWidget__pages.setFrameShape(QFrame.Shape.NoFrame)
        self.horizontalLayout__pages.addWidget(self.listWidget__pages)
        self.verticalLayout__page_column = QVBoxLayout()
        self.verticalLayout__page_column.setObjectName("verticalLayout__page_column")
        self.verticalLayout__page_column.setSpacing(4)
        self.lineEdit__filter = QLineEdit(window)
        self.lineEdit__filter.setObjectName("lineEdit__filter")
        self.lineEdit__filter.setClearButtonEnabled(True)
        self.lineEdit__filter.setPlaceholderText(preference_text("Filter settings"))
        self.verticalLayout__page_column.addWidget(self.lineEdit__filter)
        self.stackedWidget__pages = QStackedWidget(window)
        self.stackedWidget__pages.setObjectName("stackedWidget__pages")
        self.verticalLayout__page_column.addWidget(self.stackedWidget__pages, 1)
        self.horizontalLayout__pages.addLayout(self.verticalLayout__page_column, 1)
        self.verticalLayout__preference_shell.addLayout(self.horizontalLayout__pages, 1)
        self.listWidget__pages.currentRowChanged.connect(
            self.stackedWidget__pages.setCurrentIndex
        )
        self.lineEdit__filter.textChanged.connect(self.filter_pages)

    def add_page(self, title: str) -> QVBoxLayout:
        """A sidebar entry with its own scrolling column; builders add groups to it.

        The returned layout is also ``verticalLayout__preferences`` until the next
        page is added, which is what the section modules append to.
        """
        area = QScrollArea(self.stackedWidget__pages)
        area.setObjectName(f"scrollArea__page_{len(self.pages)}")
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(area)
        content.setObjectName(f"widget__page_{len(self.pages)}")
        area.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(5)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addStretch(1)  # groups pack at the top; inserted before this
        self.stackedWidget__pages.addWidget(area)
        self.listWidget__pages.addItem(title)
        self.pages[title] = (area, content)
        self.verticalLayout__preferences = _PageLayout(layout)
        return self.verticalLayout__preferences

    @property
    def scrollArea__preferences(self) -> QScrollArea:
        """The scroll area of the page on screen."""
        area = self.stackedWidget__pages.currentWidget()
        assert isinstance(area, QScrollArea)
        return area

    def show_page(self, title: str) -> None:
        self.listWidget__pages.setCurrentRow(list(self.pages).index(title))

    def filter_pages(self, text: str) -> None:
        """Hide the groups whose title and labels do not mention ``text``."""
        needle = text.strip().casefold()
        for row, (_area, content) in enumerate(self.pages.values()):
            visible_any = False
            for group in content.findChildren(
                QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
            ):
                match = not needle or needle in _searchable_text(group)
                group.setVisible(match)
                visible_any = visible_any or match
            item = self.listWidget__pages.item(row)
            item.setFlags(
                item.flags() | Qt.ItemFlag.ItemIsEnabled
                if visible_any
                else item.flags() & ~Qt.ItemFlag.ItemIsEnabled
            )

    def _build_dialog_buttons(self, window: QDialog) -> None:
        self.buttonBox__confirm = QDialogButtonBox(window)
        self.buttonBox__confirm.setObjectName("buttonBox__confirm")
        self.buttonBox__confirm.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox__confirm.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        self.verticalLayout__preference_shell.addWidget(self.buttonBox__confirm)
        self.buttonBox__confirm.accepted.connect(window.accept)
        self.buttonBox__confirm.rejected.connect(window.reject)
        self.tabWidget__view_settings.setCurrentIndex(0)


class _PageLayout(QVBoxLayout):
    """Proxy that inserts widgets above the page's trailing stretch."""

    def __init__(self, target: QVBoxLayout) -> None:
        super().__init__()
        self._target = target

    def addWidget(self, widget: QWidget, *args: object, **kwargs: object) -> None:  # type: ignore[override]
        self._target.insertWidget(self._target.count() - 1, widget)

    def insertWidget(
        self, index: int, widget: QWidget, *args: object, **kwargs: object
    ) -> None:  # type: ignore[override]
        self._target.insertWidget(min(index, self._target.count() - 1), widget)


def _searchable_text(widget: QWidget) -> str:
    parts = [widget.objectName().replace("groupBox__", "").replace("_", " ")]
    title = getattr(widget, "title", None)
    if callable(title):
        parts.append(str(title()))
    parts.extend(label.text() for label in widget.findChildren(QLabel))
    parts.extend(box.title() for box in widget.findChildren(QGroupBox))
    tabs = widget.findChildren(QTabWidget)
    for tab in tabs:
        parts.extend(tab.tabText(i) for i in range(tab.count()))
    return " ".join(parts).casefold()
