"""Code-built Preference layout.

Edit the named _build_* methods below; widget attributes follow widgetType__purpose.
This module owns presentation only. Event handling stays in the owning widget.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QCoreApplication,
    QLocale,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QCursor,
    QIcon,
    QPixmap,
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
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from widgets.layout_helpers import make_font, size_policy
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

from . import preference_icons_rc  # noqa: F401 (register bundled icons)


def _translate(text: str) -> str:
    return QCoreApplication.translate("Dialog__preference", text)


class PreferenceLayout:
    def build_ui(self, window: QDialog) -> None:
        self._configure_window(window)
        self._build_storage_settings(window)
        self._build_ffmpeg_settings(window)
        self._build_appearance_settings(window)
        self._build_icon_sizes(window)
        self._build_item_padding(window)
        self._build_note_font(window)
        self._build_tag_font(window)
        self._build_debug_font(window)
        self._build_dialog_buttons(window)

    def _configure_window(self, window: QDialog) -> None:
        if not window.objectName():
            window.setObjectName("Dialog__preference")
        window.resize(817, 889)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(":/main/icons/viewport_logo_trans.png"))
        window.setLocale(
            QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        )
        window.setWindowTitle(_translate("iHDA Preference"))
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

    def _build_storage_settings(self, window: QDialog) -> None:
        self.groupBox__data = QGroupBox(window)
        self.groupBox__data.setObjectName("groupBox__data")
        self.groupBox__data.setTitle(_translate("Data (Required)"))
        self.horizontalLayout__pixmap = QHBoxLayout(self.groupBox__data)
        self.horizontalLayout__pixmap.setObjectName("horizontalLayout__pixmap")
        self.horizontalLayout__pixmap.setContentsMargins(5, 5, 5, 5)
        self.label__pixmap = QLabel(self.groupBox__data)
        self.label__pixmap.setObjectName("label__pixmap")
        self.label__pixmap.setMaximumSize(QSize(55, 55))
        self.label__pixmap.setPixmap(QPixmap(":/main/icons/ic_settings_white.png"))
        self.label__pixmap.setScaledContents(True)
        self.label__pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__pixmap.setText("")
        self.horizontalLayout__pixmap.addWidget(self.label__pixmap)
        self.verticalLayout__data_dirpath = QVBoxLayout()
        self.verticalLayout__data_dirpath.setObjectName("verticalLayout__data_dirpath")
        self.horizontalLayout__data_dirpath = QHBoxLayout()
        self.horizontalLayout__data_dirpath.setObjectName(
            "horizontalLayout__data_dirpath"
        )
        self.label__data_dirpath = QLabel(self.groupBox__data)
        self.label__data_dirpath.setObjectName("label__data_dirpath")
        self.label__data_dirpath.setText(_translate("Directory"))
        self.horizontalLayout__data_dirpath.addWidget(self.label__data_dirpath)
        self.lineEdit__data_dirpath = QLineEdit(self.groupBox__data)
        self.lineEdit__data_dirpath.setObjectName("lineEdit__data_dirpath")
        self.lineEdit__data_dirpath.setToolTip(_translate("Data storage directory"))
        self.lineEdit__data_dirpath.setPlaceholderText(
            _translate("Choose a library directory")
        )
        self.horizontalLayout__data_dirpath.addWidget(self.lineEdit__data_dirpath)
        self.toolButton__select_data_dirpath = QToolButton(self.groupBox__data)
        self.toolButton__select_data_dirpath.setObjectName(
            "toolButton__select_data_dirpath"
        )
        self.toolButton__select_data_dirpath.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.toolButton__select_data_dirpath.setIcon(
            QIcon(":/main/icons/ic_folder_white.png")
        )
        self.toolButton__select_data_dirpath.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.toolButton__select_data_dirpath.setToolTip(
            _translate("Select the directory where data will be saved")
        )
        self.toolButton__select_data_dirpath.setStatusTip(
            _translate("Select the directory where data will be saved")
        )
        self.toolButton__select_data_dirpath.setText("")
        self.horizontalLayout__data_dirpath.addWidget(
            self.toolButton__select_data_dirpath
        )
        self.verticalLayout__data_dirpath.addLayout(self.horizontalLayout__data_dirpath)
        self.horizontalLayout__result_show = QHBoxLayout()
        self.horizontalLayout__result_show.setObjectName(
            "horizontalLayout__result_show"
        )
        self.label__result_show = QLabel(self.groupBox__data)
        self.label__result_show.setObjectName("label__result_show")
        self.label__result_show.setSizePolicy(
            size_policy(
                self.label__result_show,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Preferred,
            )
        )
        self.label__result_show.setFont(make_font(point_size=11))
        self.label__result_show.setText(_translate("Final Path"))
        self.horizontalLayout__result_show.addWidget(self.label__result_show)
        self.lineEdit__result = QLineEdit(self.groupBox__data)
        self.lineEdit__result.setObjectName("lineEdit__result")
        self.lineEdit__result.setReadOnly(True)
        self.lineEdit__result.setToolTip(_translate("Final data storage directory"))
        self.horizontalLayout__result_show.addWidget(self.lineEdit__result)
        self.label__valid_chk_pixmap = QLabel(self.groupBox__data)
        self.label__valid_chk_pixmap.setObjectName("label__valid_chk_pixmap")
        self.label__valid_chk_pixmap.setSizePolicy(
            size_policy(
                self.label__valid_chk_pixmap,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.label__valid_chk_pixmap.setMaximumSize(QSize(24, 24))
        self.label__valid_chk_pixmap.setPixmap(
            QPixmap(":/main/icons/ic_clear_white.png")
        )
        self.label__valid_chk_pixmap.setScaledContents(True)
        self.label__valid_chk_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__valid_chk_pixmap.setToolTip(
            _translate("It determines whether it is a valid directory")
        )
        self.label__valid_chk_pixmap.setText("")
        self.horizontalLayout__result_show.addWidget(self.label__valid_chk_pixmap)
        self.verticalLayout__data_dirpath.addLayout(self.horizontalLayout__result_show)
        self.horizontalLayout__pixmap.addLayout(self.verticalLayout__data_dirpath)
        self.verticalLayout__preferences.addWidget(self.groupBox__data)

    def _build_ffmpeg_settings(self, window: QDialog) -> None:
        self.groupBox__ffmpeg = QGroupBox(window)
        self.groupBox__ffmpeg.setObjectName("groupBox__ffmpeg")
        self.groupBox__ffmpeg.setTitle(_translate("FFmpeg (Optional)"))
        self.horizontalLayout__ffmpeg_pixmap = QHBoxLayout(self.groupBox__ffmpeg)
        self.horizontalLayout__ffmpeg_pixmap.setObjectName(
            "horizontalLayout__ffmpeg_pixmap"
        )
        self.horizontalLayout__ffmpeg_pixmap.setContentsMargins(5, 5, 5, 5)
        self.label__ffmpeg_pixmap = QLabel(self.groupBox__ffmpeg)
        self.label__ffmpeg_pixmap.setObjectName("label__ffmpeg_pixmap")
        self.label__ffmpeg_pixmap.setSizePolicy(
            size_policy(
                self.label__ffmpeg_pixmap,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.label__ffmpeg_pixmap.setMaximumSize(QSize(55, 55))
        self.label__ffmpeg_pixmap.setPixmap(QPixmap(":/main/icons/ffmpeg.png"))
        self.label__ffmpeg_pixmap.setScaledContents(True)
        self.label__ffmpeg_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__ffmpeg_pixmap.setText("")
        self.horizontalLayout__ffmpeg_pixmap.addWidget(self.label__ffmpeg_pixmap)
        self.verticalLayout__ffmpeg_dirpath = QVBoxLayout()
        self.verticalLayout__ffmpeg_dirpath.setObjectName(
            "verticalLayout__ffmpeg_dirpath"
        )
        self.horizontalLayout__ffmpeg_dirpath = QHBoxLayout()
        self.horizontalLayout__ffmpeg_dirpath.setObjectName(
            "horizontalLayout__ffmpeg_dirpath"
        )
        self.label__ffmpeg_dirpath = QLabel(self.groupBox__ffmpeg)
        self.label__ffmpeg_dirpath.setObjectName("label__ffmpeg_dirpath")
        self.label__ffmpeg_dirpath.setText(_translate("Directory"))
        self.horizontalLayout__ffmpeg_dirpath.addWidget(self.label__ffmpeg_dirpath)
        self.lineEdit__ffmpeg_dirpath = QLineEdit(self.groupBox__ffmpeg)
        self.lineEdit__ffmpeg_dirpath.setObjectName("lineEdit__ffmpeg_dirpath")
        self.lineEdit__ffmpeg_dirpath.setToolTip(
            _translate("Installed FFmpeg directory")
        )
        self.lineEdit__ffmpeg_dirpath.setPlaceholderText(
            _translate("Optional FFmpeg directory")
        )
        self.horizontalLayout__ffmpeg_dirpath.addWidget(self.lineEdit__ffmpeg_dirpath)
        self.toolButton__select_ffmpeg_dirpath = QToolButton(self.groupBox__ffmpeg)
        self.toolButton__select_ffmpeg_dirpath.setObjectName(
            "toolButton__select_ffmpeg_dirpath"
        )
        self.toolButton__select_ffmpeg_dirpath.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.toolButton__select_ffmpeg_dirpath.setIcon(
            QIcon(":/main/icons/ic_folder_white.png")
        )
        self.toolButton__select_ffmpeg_dirpath.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.toolButton__select_ffmpeg_dirpath.setToolTip(
            _translate("Select the directory where FFmpeg is installed")
        )
        self.toolButton__select_ffmpeg_dirpath.setStatusTip(
            _translate("Select the directory where FFmpeg is installed")
        )
        self.toolButton__select_ffmpeg_dirpath.setText("")
        self.horizontalLayout__ffmpeg_dirpath.addWidget(
            self.toolButton__select_ffmpeg_dirpath
        )
        self.verticalLayout__ffmpeg_dirpath.addLayout(
            self.horizontalLayout__ffmpeg_dirpath
        )
        self.horizontalLayout__ffmpeg_result_show = QHBoxLayout()
        self.horizontalLayout__ffmpeg_result_show.setObjectName(
            "horizontalLayout__ffmpeg_result_show"
        )
        self.label__ffmpeg_result_show = QLabel(self.groupBox__ffmpeg)
        self.label__ffmpeg_result_show.setObjectName("label__ffmpeg_result_show")
        self.label__ffmpeg_result_show.setSizePolicy(
            size_policy(
                self.label__ffmpeg_result_show,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Preferred,
            )
        )
        self.label__ffmpeg_result_show.setFont(make_font(point_size=11))
        self.label__ffmpeg_result_show.setText(_translate("Final Path"))
        self.horizontalLayout__ffmpeg_result_show.addWidget(
            self.label__ffmpeg_result_show
        )
        self.lineEdit__ffmpeg_result = QLineEdit(self.groupBox__ffmpeg)
        self.lineEdit__ffmpeg_result.setObjectName("lineEdit__ffmpeg_result")
        self.lineEdit__ffmpeg_result.setReadOnly(True)
        self.lineEdit__ffmpeg_result.setToolTip(
            _translate("Final installed FFmpeg directory")
        )
        self.horizontalLayout__ffmpeg_result_show.addWidget(
            self.lineEdit__ffmpeg_result
        )
        self.label__ffmpeg_valid_chk_pixmap = QLabel(self.groupBox__ffmpeg)
        self.label__ffmpeg_valid_chk_pixmap.setObjectName(
            "label__ffmpeg_valid_chk_pixmap"
        )
        self.label__ffmpeg_valid_chk_pixmap.setSizePolicy(
            size_policy(
                self.label__ffmpeg_valid_chk_pixmap,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.label__ffmpeg_valid_chk_pixmap.setMaximumSize(QSize(24, 24))
        self.label__ffmpeg_valid_chk_pixmap.setPixmap(
            QPixmap(":/main/icons/ic_clear_white.png")
        )
        self.label__ffmpeg_valid_chk_pixmap.setScaledContents(True)
        self.label__ffmpeg_valid_chk_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__ffmpeg_valid_chk_pixmap.setToolTip(
            _translate("It determines whether it is a valid directory")
        )
        self.label__ffmpeg_valid_chk_pixmap.setText("")
        self.horizontalLayout__ffmpeg_result_show.addWidget(
            self.label__ffmpeg_valid_chk_pixmap
        )
        self.verticalLayout__ffmpeg_dirpath.addLayout(
            self.horizontalLayout__ffmpeg_result_show
        )
        self.horizontalLayout__ffmpeg_pixmap.addLayout(
            self.verticalLayout__ffmpeg_dirpath
        )
        self.verticalLayout__preferences.addWidget(self.groupBox__ffmpeg)

    def _build_appearance_settings(self, window: QDialog) -> None:
        self.groupBox__app_properties = QGroupBox(window)
        self.groupBox__app_properties.setObjectName("groupBox__app_properties")
        self.groupBox__app_properties.setTitle(_translate("APP Properties (Default)"))
        self.horizontalLayout__appearance = QHBoxLayout(self.groupBox__app_properties)
        self.horizontalLayout__appearance.setObjectName("horizontalLayout__appearance")
        self.horizontalLayout__appearance.setContentsMargins(5, 5, 5, 5)
        self.pushButton__reset_default_app_properties = QPushButton(
            self.groupBox__app_properties
        )
        self.pushButton__reset_default_app_properties.setObjectName(
            "pushButton__reset_default_app_properties"
        )
        self.pushButton__reset_default_app_properties.setMaximumSize(QSize(55, 55))
        self.pushButton__reset_default_app_properties.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.pushButton__reset_default_app_properties.setIcon(
            QIcon(":/main/icons/ic_refresh_white.png")
        )
        self.pushButton__reset_default_app_properties.setIconSize(QSize(50, 50))
        self.pushButton__reset_default_app_properties.setFlat(True)
        self.pushButton__reset_default_app_properties.setToolTip(
            _translate("Initialize app properties to default values")
        )
        self.pushButton__reset_default_app_properties.setText("")
        self.horizontalLayout__appearance.addWidget(
            self.pushButton__reset_default_app_properties
        )
        self.verticalLayout__appearance_groups = QVBoxLayout()
        self.verticalLayout__appearance_groups.setObjectName(
            "verticalLayout__appearance_groups"
        )
        self.groupBox__main_icons = QGroupBox(self.groupBox__app_properties)
        self.groupBox__main_icons.setObjectName("groupBox__main_icons")
        self.groupBox__main_icons.setTitle(_translate("Main View"))
        self.verticalLayout__main_icons = QVBoxLayout(self.groupBox__main_icons)
        self.verticalLayout__main_icons.setObjectName("verticalLayout__main_icons")
        self.horizontalLayout__default_main_icon_size = QHBoxLayout()
        self.horizontalLayout__default_main_icon_size.setObjectName(
            "horizontalLayout__default_main_icon_size"
        )
        self.label__default_main_icon_size = QLabel(self.groupBox__main_icons)
        self.label__default_main_icon_size.setObjectName(
            "label__default_main_icon_size"
        )
        self.label__default_main_icon_size.setText(_translate("Icon"))
        self.horizontalLayout__default_main_icon_size.addWidget(
            self.label__default_main_icon_size
        )
        self.spinBox__default_main_icon_size = QSpinBox(self.groupBox__main_icons)
        self.spinBox__default_main_icon_size.setObjectName(
            "spinBox__default_main_icon_size"
        )
        self.spinBox__default_main_icon_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__default_main_icon_size.setFrame(False)
        self.spinBox__default_main_icon_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinBox__default_main_icon_size.setMinimum(1)
        self.spinBox__default_main_icon_size.setMaximum(30)
        self.spinBox__default_main_icon_size.setValue(20)
        self.spinBox__default_main_icon_size.setSuffix(_translate("px"))
        self.horizontalLayout__default_main_icon_size.addWidget(
            self.spinBox__default_main_icon_size
        )
        self.verticalLayout__main_icons.addLayout(
            self.horizontalLayout__default_main_icon_size
        )
        self.verticalLayout__appearance_groups.addWidget(self.groupBox__main_icons)
        self.groupBox__default_icon = QGroupBox(self.groupBox__app_properties)
        self.groupBox__default_icon.setObjectName("groupBox__default_icon")
        self.groupBox__default_icon.setTitle(_translate("Item View"))
        self.verticalLayout__view_settings = QVBoxLayout(self.groupBox__default_icon)
        self.verticalLayout__view_settings.setObjectName(
            "verticalLayout__view_settings"
        )
        self.horizontalLayout__view_font_size = QHBoxLayout()
        self.horizontalLayout__view_font_size.setObjectName(
            "horizontalLayout__view_font_size"
        )
        self.horizontalLayout__view_font_size_row = QHBoxLayout()
        self.horizontalLayout__view_font_size_row.setObjectName(
            "horizontalLayout__view_font_size_row"
        )
        self.label__view_font_size = QLabel(self.groupBox__default_icon)
        self.label__view_font_size.setObjectName("label__view_font_size")
        self.label__view_font_size.setText(_translate("Font Size"))
        self.horizontalLayout__view_font_size_row.addWidget(self.label__view_font_size)
        self.spinBox__view_font_size = QSpinBox(self.groupBox__default_icon)
        self.spinBox__view_font_size.setObjectName("spinBox__view_font_size")
        self.spinBox__view_font_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__view_font_size.setFrame(False)
        self.spinBox__view_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinBox__view_font_size.setMinimum(2)
        self.spinBox__view_font_size.setMaximum(50)
        self.spinBox__view_font_size.setValue(11)
        self.horizontalLayout__view_font_size_row.addWidget(
            self.spinBox__view_font_size
        )
        self.horizontalLayout__view_font_size.addLayout(
            self.horizontalLayout__view_font_size_row
        )
        self.spacer__view_font_size = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__view_font_size.addItem(self.spacer__view_font_size)
        self.horizontalLayout__view_font_style = QHBoxLayout()
        self.horizontalLayout__view_font_style.setObjectName(
            "horizontalLayout__view_font_style"
        )
        self.label__view_font_style = QLabel(self.groupBox__default_icon)
        self.label__view_font_style.setObjectName("label__view_font_style")
        self.label__view_font_style.setText(_translate("Font Style"))
        self.horizontalLayout__view_font_style.addWidget(self.label__view_font_style)
        self.fontComboBox__view_font_style = QFontComboBox(self.groupBox__default_icon)
        self.fontComboBox__view_font_style.setObjectName(
            "fontComboBox__view_font_style"
        )
        self.fontComboBox__view_font_style.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.fontComboBox__view_font_style.setFrame(False)
        self.horizontalLayout__view_font_style.addWidget(
            self.fontComboBox__view_font_style
        )
        self.horizontalLayout__view_font_size.addLayout(
            self.horizontalLayout__view_font_style
        )
        self.verticalLayout__view_settings.addLayout(
            self.horizontalLayout__view_font_size
        )
        self.line__view_settings = QFrame(self.groupBox__default_icon)
        self.line__view_settings.setObjectName("line__view_settings")
        self.line__view_settings.setFrameShape(QFrame.Shape.HLine)
        self.line__view_settings.setFrameShadow(QFrame.Shadow.Sunken)
        self.verticalLayout__view_settings.addWidget(self.line__view_settings)
        self.tabWidget__view_settings = QTabWidget(self.groupBox__default_icon)
        self.tabWidget__view_settings.setObjectName("tabWidget__view_settings")
        self.tabWidget__view_settings.setIconSize(
            QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )

    def _build_icon_sizes(self, window: QDialog) -> None:
        self.tab__icon = QWidget()
        self.tab__icon.setObjectName("tab__icon")
        self.verticalLayout__icon_sizes = QVBoxLayout(self.tab__icon)
        self.verticalLayout__icon_sizes.setSpacing(5)
        self.verticalLayout__icon_sizes.setObjectName("verticalLayout__icon_sizes")
        self.verticalLayout__icon_sizes.setContentsMargins(5, 5, 5, 5)
        self._build_list_icon_settings(window)
        self._build_table_icon_settings(window)
        self._build_tree_icon_settings(window)

    def _build_list_icon_settings(self, window: QDialog) -> None:
        self.horizontalLayout__default_listview_icon_size = QHBoxLayout()
        self.horizontalLayout__default_listview_icon_size.setSpacing(15)
        self.horizontalLayout__default_listview_icon_size.setObjectName(
            "horizontalLayout__default_listview_icon_size"
        )
        self.horizontalLayout__default_listview_icon_size_row = QHBoxLayout()
        self.horizontalLayout__default_listview_icon_size_row.setObjectName(
            "horizontalLayout__default_listview_icon_size_row"
        )
        self.label__default_listview_icon_size = QLabel(self.tab__icon)
        self.label__default_listview_icon_size.setObjectName(
            "label__default_listview_icon_size"
        )
        self.label__default_listview_icon_size.setText(_translate("ListView"))
        self.horizontalLayout__default_listview_icon_size_row.addWidget(
            self.label__default_listview_icon_size
        )
        self.spinBox__default_listview_icon_size = QSpinBox(self.tab__icon)
        self.spinBox__default_listview_icon_size.setObjectName(
            "spinBox__default_listview_icon_size"
        )
        self.spinBox__default_listview_icon_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__default_listview_icon_size.setFrame(False)
        self.spinBox__default_listview_icon_size.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.spinBox__default_listview_icon_size.setMinimum(1)
        self.spinBox__default_listview_icon_size.setValue(38)
        self.spinBox__default_listview_icon_size.setSuffix(_translate("px"))
        self.horizontalLayout__default_listview_icon_size_row.addWidget(
            self.spinBox__default_listview_icon_size
        )
        self.horizontalLayout__default_listview_icon_size.addLayout(
            self.horizontalLayout__default_listview_icon_size_row
        )
        self.spacer__default_listview_icon_size = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_listview_icon_size.addItem(
            self.spacer__default_listview_icon_size
        )
        self.horizontalLayout__default_listview_thumb_scale = QHBoxLayout()
        self.horizontalLayout__default_listview_thumb_scale.setObjectName(
            "horizontalLayout__default_listview_thumb_scale"
        )
        self.label__default_listview_thumb_scale = QLabel(self.tab__icon)
        self.label__default_listview_thumb_scale.setObjectName(
            "label__default_listview_thumb_scale"
        )
        self.label__default_listview_thumb_scale.setText(_translate("Thumbnail Scale"))
        self.horizontalLayout__default_listview_thumb_scale.addWidget(
            self.label__default_listview_thumb_scale
        )
        self.doubleSpinBox__default_listview_thumb_scale = QDoubleSpinBox(
            self.tab__icon
        )
        self.doubleSpinBox__default_listview_thumb_scale.setObjectName(
            "doubleSpinBox__default_listview_thumb_scale"
        )
        self.doubleSpinBox__default_listview_thumb_scale.setFrame(False)
        self.doubleSpinBox__default_listview_thumb_scale.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_listview_thumb_scale.setDecimals(1)
        self.doubleSpinBox__default_listview_thumb_scale.setMinimum(0.1)
        self.doubleSpinBox__default_listview_thumb_scale.setMaximum(50.0)
        self.doubleSpinBox__default_listview_thumb_scale.setSingleStep(0.1)
        self.doubleSpinBox__default_listview_thumb_scale.setValue(2.0)
        self.doubleSpinBox__default_listview_thumb_scale.setPrefix(_translate("x"))
        self.horizontalLayout__default_listview_thumb_scale.addWidget(
            self.doubleSpinBox__default_listview_thumb_scale
        )
        self.spacer__default_listview_thumb_scale = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_listview_thumb_scale.addItem(
            self.spacer__default_listview_thumb_scale
        )
        self.horizontalLayout__default_listview_icon_size.addLayout(
            self.horizontalLayout__default_listview_thumb_scale
        )
        self.verticalLayout__icon_sizes.addLayout(
            self.horizontalLayout__default_listview_icon_size
        )

    def _build_table_icon_settings(self, window: QDialog) -> None:
        self.horizontalLayout__default_tableview_icon_size = QHBoxLayout()
        self.horizontalLayout__default_tableview_icon_size.setSpacing(15)
        self.horizontalLayout__default_tableview_icon_size.setObjectName(
            "horizontalLayout__default_tableview_icon_size"
        )
        self.horizontalLayout__default_tableview_icon_size_row = QHBoxLayout()
        self.horizontalLayout__default_tableview_icon_size_row.setObjectName(
            "horizontalLayout__default_tableview_icon_size_row"
        )
        self.label__default_tableview_icon_size = QLabel(self.tab__icon)
        self.label__default_tableview_icon_size.setObjectName(
            "label__default_tableview_icon_size"
        )
        self.label__default_tableview_icon_size.setText(_translate("TableView"))
        self.horizontalLayout__default_tableview_icon_size_row.addWidget(
            self.label__default_tableview_icon_size
        )
        self.spinBox__default_tableview_icon_size = QSpinBox(self.tab__icon)
        self.spinBox__default_tableview_icon_size.setObjectName(
            "spinBox__default_tableview_icon_size"
        )
        self.spinBox__default_tableview_icon_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__default_tableview_icon_size.setFrame(False)
        self.spinBox__default_tableview_icon_size.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.spinBox__default_tableview_icon_size.setMinimum(1)
        self.spinBox__default_tableview_icon_size.setValue(38)
        self.spinBox__default_tableview_icon_size.setSuffix(_translate("px"))
        self.horizontalLayout__default_tableview_icon_size_row.addWidget(
            self.spinBox__default_tableview_icon_size
        )
        self.horizontalLayout__default_tableview_icon_size.addLayout(
            self.horizontalLayout__default_tableview_icon_size_row
        )
        self.spacer__default_tableview_icon_size = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_tableview_icon_size.addItem(
            self.spacer__default_tableview_icon_size
        )
        self.horizontalLayout__default_tableview_thumb_scale = QHBoxLayout()
        self.horizontalLayout__default_tableview_thumb_scale.setObjectName(
            "horizontalLayout__default_tableview_thumb_scale"
        )
        self.label__default_tableview_thumb_scale = QLabel(self.tab__icon)
        self.label__default_tableview_thumb_scale.setObjectName(
            "label__default_tableview_thumb_scale"
        )
        self.label__default_tableview_thumb_scale.setText(_translate("Thumbnail Scale"))
        self.horizontalLayout__default_tableview_thumb_scale.addWidget(
            self.label__default_tableview_thumb_scale
        )
        self.doubleSpinBox__default_tableview_thumb_scale = QDoubleSpinBox(
            self.tab__icon
        )
        self.doubleSpinBox__default_tableview_thumb_scale.setObjectName(
            "doubleSpinBox__default_tableview_thumb_scale"
        )
        self.doubleSpinBox__default_tableview_thumb_scale.setFrame(False)
        self.doubleSpinBox__default_tableview_thumb_scale.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_tableview_thumb_scale.setDecimals(1)
        self.doubleSpinBox__default_tableview_thumb_scale.setMinimum(0.1)
        self.doubleSpinBox__default_tableview_thumb_scale.setMaximum(50.0)
        self.doubleSpinBox__default_tableview_thumb_scale.setSingleStep(0.1)
        self.doubleSpinBox__default_tableview_thumb_scale.setValue(1.3)
        self.doubleSpinBox__default_tableview_thumb_scale.setPrefix(_translate("x"))
        self.horizontalLayout__default_tableview_thumb_scale.addWidget(
            self.doubleSpinBox__default_tableview_thumb_scale
        )
        self.spacer__default_tableview_thumb_scale = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_tableview_thumb_scale.addItem(
            self.spacer__default_tableview_thumb_scale
        )
        self.horizontalLayout__default_tableview_icon_size.addLayout(
            self.horizontalLayout__default_tableview_thumb_scale
        )
        self.verticalLayout__icon_sizes.addLayout(
            self.horizontalLayout__default_tableview_icon_size
        )

    def _build_tree_icon_settings(self, window: QDialog) -> None:
        self.horizontalLayout__default_treeview_icon_size = QHBoxLayout()
        self.horizontalLayout__default_treeview_icon_size.setObjectName(
            "horizontalLayout__default_treeview_icon_size"
        )
        self.label__default_treeview_icon_size = QLabel(self.tab__icon)
        self.label__default_treeview_icon_size.setObjectName(
            "label__default_treeview_icon_size"
        )
        self.label__default_treeview_icon_size.setText(_translate("TreeView"))
        self.horizontalLayout__default_treeview_icon_size.addWidget(
            self.label__default_treeview_icon_size
        )
        self.spinBox__default_treeview_icon_size = QSpinBox(self.tab__icon)
        self.spinBox__default_treeview_icon_size.setObjectName(
            "spinBox__default_treeview_icon_size"
        )
        self.spinBox__default_treeview_icon_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__default_treeview_icon_size.setFrame(False)
        self.spinBox__default_treeview_icon_size.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.spinBox__default_treeview_icon_size.setMinimum(1)
        self.spinBox__default_treeview_icon_size.setValue(24)
        self.spinBox__default_treeview_icon_size.setSuffix(_translate("px"))
        self.horizontalLayout__default_treeview_icon_size.addWidget(
            self.spinBox__default_treeview_icon_size
        )
        self.spacer__default_treeview_icon_size = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_treeview_icon_size.addItem(
            self.spacer__default_treeview_icon_size
        )
        self.verticalLayout__icon_sizes.addLayout(
            self.horizontalLayout__default_treeview_icon_size
        )
        self.tabWidget__view_settings.addTab(
            self.tab__icon,
            QIcon(":/main/icons/ic_photo_white.png"),
            _translate("Icon / Thumbnail"),
        )

    def _build_item_padding(self, window: QDialog) -> None:
        self.tab__padding = QWidget()
        self.tab__padding.setObjectName("tab__padding")
        self.horizontalLayout__padding_columns = QHBoxLayout(self.tab__padding)
        self.horizontalLayout__padding_columns.setSpacing(5)
        self.horizontalLayout__padding_columns.setObjectName(
            "horizontalLayout__padding_columns"
        )
        self.horizontalLayout__padding_columns.setContentsMargins(5, 5, 5, 5)
        self._build_asset_padding(window)
        self._build_tree_padding(window)

    def _build_asset_padding(self, window: QDialog) -> None:
        self.verticalLayout__asset_padding = QVBoxLayout()
        self.verticalLayout__asset_padding.setObjectName(
            "verticalLayout__asset_padding"
        )
        self.horizontalLayout__default_list_item_padding = QHBoxLayout()
        self.horizontalLayout__default_list_item_padding.setObjectName(
            "horizontalLayout__default_list_item_padding"
        )
        self.label__default_list_item_padding = QLabel(self.tab__padding)
        self.label__default_list_item_padding.setObjectName(
            "label__default_list_item_padding"
        )
        self.label__default_list_item_padding.setText(_translate("List View"))
        self.horizontalLayout__default_list_item_padding.addWidget(
            self.label__default_list_item_padding
        )
        self.spacer__default_list_item_padding = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_list_item_padding.addItem(
            self.spacer__default_list_item_padding
        )
        self.doubleSpinBox__default_list_item_padding = QDoubleSpinBox(
            self.tab__padding
        )
        self.doubleSpinBox__default_list_item_padding.setObjectName(
            "doubleSpinBox__default_list_item_padding"
        )
        self.doubleSpinBox__default_list_item_padding.setFrame(False)
        self.doubleSpinBox__default_list_item_padding.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_list_item_padding.setDecimals(1)
        self.doubleSpinBox__default_list_item_padding.setMinimum(0.0)
        self.doubleSpinBox__default_list_item_padding.setMaximum(100.0)
        self.doubleSpinBox__default_list_item_padding.setSingleStep(0.1)
        self.doubleSpinBox__default_list_item_padding.setValue(20.0)
        self.doubleSpinBox__default_list_item_padding.setSuffix(_translate("px"))
        self.horizontalLayout__default_list_item_padding.addWidget(
            self.doubleSpinBox__default_list_item_padding
        )
        self.verticalLayout__asset_padding.addLayout(
            self.horizontalLayout__default_list_item_padding
        )
        self.horizontalLayout__default_table_item_padding = QHBoxLayout()
        self.horizontalLayout__default_table_item_padding.setObjectName(
            "horizontalLayout__default_table_item_padding"
        )
        self.label__default_table_item_padding = QLabel(self.tab__padding)
        self.label__default_table_item_padding.setObjectName(
            "label__default_table_item_padding"
        )
        self.label__default_table_item_padding.setText(_translate("Table View"))
        self.horizontalLayout__default_table_item_padding.addWidget(
            self.label__default_table_item_padding
        )
        self.spacer__default_table_item_padding = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_table_item_padding.addItem(
            self.spacer__default_table_item_padding
        )
        self.doubleSpinBox__default_table_item_padding = QDoubleSpinBox(
            self.tab__padding
        )
        self.doubleSpinBox__default_table_item_padding.setObjectName(
            "doubleSpinBox__default_table_item_padding"
        )
        self.doubleSpinBox__default_table_item_padding.setFrame(False)
        self.doubleSpinBox__default_table_item_padding.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_table_item_padding.setDecimals(1)
        self.doubleSpinBox__default_table_item_padding.setMinimum(0.0)
        self.doubleSpinBox__default_table_item_padding.setMaximum(100.0)
        self.doubleSpinBox__default_table_item_padding.setSingleStep(0.1)
        self.doubleSpinBox__default_table_item_padding.setValue(0.0)
        self.doubleSpinBox__default_table_item_padding.setSuffix(_translate("px"))
        self.horizontalLayout__default_table_item_padding.addWidget(
            self.doubleSpinBox__default_table_item_padding
        )
        self.verticalLayout__asset_padding.addLayout(
            self.horizontalLayout__default_table_item_padding
        )
        self.horizontalLayout__default_history_item_padding = QHBoxLayout()
        self.horizontalLayout__default_history_item_padding.setObjectName(
            "horizontalLayout__default_history_item_padding"
        )
        self.label__default_history_item_padding = QLabel(self.tab__padding)
        self.label__default_history_item_padding.setObjectName(
            "label__default_history_item_padding"
        )
        self.label__default_history_item_padding.setText(_translate("History View"))
        self.horizontalLayout__default_history_item_padding.addWidget(
            self.label__default_history_item_padding
        )
        self.spacer__default_history_item_padding = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_history_item_padding.addItem(
            self.spacer__default_history_item_padding
        )
        self.doubleSpinBox__default_history_item_padding = QDoubleSpinBox(
            self.tab__padding
        )
        self.doubleSpinBox__default_history_item_padding.setObjectName(
            "doubleSpinBox__default_history_item_padding"
        )
        self.doubleSpinBox__default_history_item_padding.setFrame(False)
        self.doubleSpinBox__default_history_item_padding.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_history_item_padding.setDecimals(1)
        self.doubleSpinBox__default_history_item_padding.setMinimum(0.0)
        self.doubleSpinBox__default_history_item_padding.setMaximum(100.0)
        self.doubleSpinBox__default_history_item_padding.setSingleStep(0.1)
        self.doubleSpinBox__default_history_item_padding.setValue(0.0)
        self.doubleSpinBox__default_history_item_padding.setSuffix(_translate("px"))
        self.horizontalLayout__default_history_item_padding.addWidget(
            self.doubleSpinBox__default_history_item_padding
        )
        self.verticalLayout__asset_padding.addLayout(
            self.horizontalLayout__default_history_item_padding
        )
        self.horizontalLayout__padding_columns.addLayout(
            self.verticalLayout__asset_padding
        )
        self.spacer__padding_columns = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__padding_columns.addItem(self.spacer__padding_columns)

    def _build_tree_padding(self, window: QDialog) -> None:
        self.verticalLayout__tree_padding = QVBoxLayout()
        self.verticalLayout__tree_padding.setObjectName("verticalLayout__tree_padding")
        self.horizontalLayout__default_cate_item_padding = QHBoxLayout()
        self.horizontalLayout__default_cate_item_padding.setObjectName(
            "horizontalLayout__default_cate_item_padding"
        )
        self.label__default_cate_item_padding = QLabel(self.tab__padding)
        self.label__default_cate_item_padding.setObjectName(
            "label__default_cate_item_padding"
        )
        self.label__default_cate_item_padding.setText(_translate("Category View"))
        self.horizontalLayout__default_cate_item_padding.addWidget(
            self.label__default_cate_item_padding
        )
        self.spacer__default_cate_item_padding = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_cate_item_padding.addItem(
            self.spacer__default_cate_item_padding
        )
        self.doubleSpinBox__default_cate_item_padding = QDoubleSpinBox(
            self.tab__padding
        )
        self.doubleSpinBox__default_cate_item_padding.setObjectName(
            "doubleSpinBox__default_cate_item_padding"
        )
        self.doubleSpinBox__default_cate_item_padding.setFrame(False)
        self.doubleSpinBox__default_cate_item_padding.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_cate_item_padding.setDecimals(1)
        self.doubleSpinBox__default_cate_item_padding.setMinimum(0.0)
        self.doubleSpinBox__default_cate_item_padding.setMaximum(100.0)
        self.doubleSpinBox__default_cate_item_padding.setSingleStep(0.1)
        self.doubleSpinBox__default_cate_item_padding.setValue(15.0)
        self.doubleSpinBox__default_cate_item_padding.setSuffix(_translate("px"))
        self.horizontalLayout__default_cate_item_padding.addWidget(
            self.doubleSpinBox__default_cate_item_padding
        )
        self.verticalLayout__tree_padding.addLayout(
            self.horizontalLayout__default_cate_item_padding
        )
        self.horizontalLayout__default_record_item_padding = QHBoxLayout()
        self.horizontalLayout__default_record_item_padding.setObjectName(
            "horizontalLayout__default_record_item_padding"
        )
        self.label__default_record_item_padding = QLabel(self.tab__padding)
        self.label__default_record_item_padding.setObjectName(
            "label__default_record_item_padding"
        )
        self.label__default_record_item_padding.setText(_translate("Record View"))
        self.horizontalLayout__default_record_item_padding.addWidget(
            self.label__default_record_item_padding
        )
        self.spacer__default_record_item_padding = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_record_item_padding.addItem(
            self.spacer__default_record_item_padding
        )
        self.doubleSpinBox__default_record_item_padding = QDoubleSpinBox(
            self.tab__padding
        )
        self.doubleSpinBox__default_record_item_padding.setObjectName(
            "doubleSpinBox__default_record_item_padding"
        )
        self.doubleSpinBox__default_record_item_padding.setFrame(False)
        self.doubleSpinBox__default_record_item_padding.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_record_item_padding.setDecimals(1)
        self.doubleSpinBox__default_record_item_padding.setMinimum(0.0)
        self.doubleSpinBox__default_record_item_padding.setMaximum(100.0)
        self.doubleSpinBox__default_record_item_padding.setSingleStep(0.1)
        self.doubleSpinBox__default_record_item_padding.setValue(5.0)
        self.doubleSpinBox__default_record_item_padding.setSuffix(_translate("px"))
        self.horizontalLayout__default_record_item_padding.addWidget(
            self.doubleSpinBox__default_record_item_padding
        )
        self.verticalLayout__tree_padding.addLayout(
            self.horizontalLayout__default_record_item_padding
        )
        self.horizontalLayout__default_inside_item_padding = QHBoxLayout()
        self.horizontalLayout__default_inside_item_padding.setObjectName(
            "horizontalLayout__default_inside_item_padding"
        )
        self.label__default_inside_item_padding = QLabel(self.tab__padding)
        self.label__default_inside_item_padding.setObjectName(
            "label__default_inside_item_padding"
        )
        self.label__default_inside_item_padding.setText(_translate("Inside View"))
        self.horizontalLayout__default_inside_item_padding.addWidget(
            self.label__default_inside_item_padding
        )
        self.spacer__default_inside_item_padding = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__default_inside_item_padding.addItem(
            self.spacer__default_inside_item_padding
        )
        self.doubleSpinBox__default_inside_item_padding = QDoubleSpinBox(
            self.tab__padding
        )
        self.doubleSpinBox__default_inside_item_padding.setObjectName(
            "doubleSpinBox__default_inside_item_padding"
        )
        self.doubleSpinBox__default_inside_item_padding.setFrame(False)
        self.doubleSpinBox__default_inside_item_padding.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.doubleSpinBox__default_inside_item_padding.setDecimals(1)
        self.doubleSpinBox__default_inside_item_padding.setMinimum(0.0)
        self.doubleSpinBox__default_inside_item_padding.setMaximum(100.0)
        self.doubleSpinBox__default_inside_item_padding.setSingleStep(0.1)
        self.doubleSpinBox__default_inside_item_padding.setValue(5.0)
        self.doubleSpinBox__default_inside_item_padding.setSuffix(_translate("px"))
        self.horizontalLayout__default_inside_item_padding.addWidget(
            self.doubleSpinBox__default_inside_item_padding
        )
        self.verticalLayout__tree_padding.addLayout(
            self.horizontalLayout__default_inside_item_padding
        )
        self.horizontalLayout__padding_columns.addLayout(
            self.verticalLayout__tree_padding
        )
        self.tabWidget__view_settings.addTab(
            self.tab__padding,
            QIcon(":/main/icons/ic_settings_overscan_white.png"),
            _translate("Padding"),
        )

    def _build_note_font(self, window: QDialog) -> None:
        self.tab__text = QWidget()
        self.tab__text.setObjectName("tab__text")
        self.verticalLayout__text_settings = QVBoxLayout(self.tab__text)
        self.verticalLayout__text_settings.setSpacing(5)
        self.verticalLayout__text_settings.setObjectName(
            "verticalLayout__text_settings"
        )
        self.verticalLayout__text_settings.setContentsMargins(5, 5, 5, 5)
        self.groupBox__note = QGroupBox(self.tab__text)
        self.groupBox__note.setObjectName("groupBox__note")
        self.groupBox__note.setTitle(_translate("Note"))
        self.verticalLayout__note_font_size = QVBoxLayout(self.groupBox__note)
        self.verticalLayout__note_font_size.setObjectName(
            "verticalLayout__note_font_size"
        )
        self.horizontalLayout__note_font_size = QHBoxLayout()
        self.horizontalLayout__note_font_size.setSpacing(15)
        self.horizontalLayout__note_font_size.setObjectName(
            "horizontalLayout__note_font_size"
        )
        self.horizontalLayout__note_font_size_row = QHBoxLayout()
        self.horizontalLayout__note_font_size_row.setObjectName(
            "horizontalLayout__note_font_size_row"
        )
        self.label__note_font_size = QLabel(self.groupBox__note)
        self.label__note_font_size.setObjectName("label__note_font_size")
        self.label__note_font_size.setText(_translate("Font Size"))
        self.horizontalLayout__note_font_size_row.addWidget(self.label__note_font_size)
        self.spinBox__note_font_size = QSpinBox(self.groupBox__note)
        self.spinBox__note_font_size.setObjectName("spinBox__note_font_size")
        self.spinBox__note_font_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__note_font_size.setFrame(False)
        self.spinBox__note_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinBox__note_font_size.setMinimum(2)
        self.spinBox__note_font_size.setMaximum(50)
        self.spinBox__note_font_size.setValue(11)
        self.horizontalLayout__note_font_size_row.addWidget(
            self.spinBox__note_font_size
        )
        self.horizontalLayout__note_font_size.addLayout(
            self.horizontalLayout__note_font_size_row
        )
        self.spacer__note_font_size = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__note_font_size.addItem(self.spacer__note_font_size)
        self.horizontalLayout__note_font_style = QHBoxLayout()
        self.horizontalLayout__note_font_style.setObjectName(
            "horizontalLayout__note_font_style"
        )
        self.label__note_font_style = QLabel(self.groupBox__note)
        self.label__note_font_style.setObjectName("label__note_font_style")
        self.label__note_font_style.setText(_translate("Font Style"))
        self.horizontalLayout__note_font_style.addWidget(self.label__note_font_style)
        self.fontComboBox__note_font_style = QFontComboBox(self.groupBox__note)
        self.fontComboBox__note_font_style.setObjectName(
            "fontComboBox__note_font_style"
        )
        self.fontComboBox__note_font_style.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.fontComboBox__note_font_style.setFrame(False)
        self.horizontalLayout__note_font_style.addWidget(
            self.fontComboBox__note_font_style
        )
        self.horizontalLayout__note_font_size.addLayout(
            self.horizontalLayout__note_font_style
        )
        self.verticalLayout__note_font_size.addLayout(
            self.horizontalLayout__note_font_size
        )
        self.verticalLayout__text_settings.addWidget(self.groupBox__note)

    def _build_tag_font(self, window: QDialog) -> None:
        self.groupBox__tags = QGroupBox(self.tab__text)
        self.groupBox__tags.setObjectName("groupBox__tags")
        self.groupBox__tags.setTitle(_translate("Tags"))
        self.verticalLayout__tags_font_size = QVBoxLayout(self.groupBox__tags)
        self.verticalLayout__tags_font_size.setObjectName(
            "verticalLayout__tags_font_size"
        )
        self.horizontalLayout__tags_font_size = QHBoxLayout()
        self.horizontalLayout__tags_font_size.setSpacing(15)
        self.horizontalLayout__tags_font_size.setObjectName(
            "horizontalLayout__tags_font_size"
        )
        self.horizontalLayout__tags_font_size_row = QHBoxLayout()
        self.horizontalLayout__tags_font_size_row.setObjectName(
            "horizontalLayout__tags_font_size_row"
        )
        self.label__tags_font_size = QLabel(self.groupBox__tags)
        self.label__tags_font_size.setObjectName("label__tags_font_size")
        self.label__tags_font_size.setText(_translate("Font Size"))
        self.horizontalLayout__tags_font_size_row.addWidget(self.label__tags_font_size)
        self.spinBox__tags_font_size = QSpinBox(self.groupBox__tags)
        self.spinBox__tags_font_size.setObjectName("spinBox__tags_font_size")
        self.spinBox__tags_font_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__tags_font_size.setFrame(False)
        self.spinBox__tags_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinBox__tags_font_size.setMinimum(2)
        self.spinBox__tags_font_size.setMaximum(50)
        self.spinBox__tags_font_size.setValue(11)
        self.horizontalLayout__tags_font_size_row.addWidget(
            self.spinBox__tags_font_size
        )
        self.horizontalLayout__tags_font_size.addLayout(
            self.horizontalLayout__tags_font_size_row
        )
        self.spacer__tags_font_size = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__tags_font_size.addItem(self.spacer__tags_font_size)
        self.horizontalLayout__tags_font_style = QHBoxLayout()
        self.horizontalLayout__tags_font_style.setObjectName(
            "horizontalLayout__tags_font_style"
        )
        self.label__tags_font_style = QLabel(self.groupBox__tags)
        self.label__tags_font_style.setObjectName("label__tags_font_style")
        self.label__tags_font_style.setText(_translate("Font Style"))
        self.horizontalLayout__tags_font_style.addWidget(self.label__tags_font_style)
        self.fontComboBox__tags_font_style = QFontComboBox(self.groupBox__tags)
        self.fontComboBox__tags_font_style.setObjectName(
            "fontComboBox__tags_font_style"
        )
        self.fontComboBox__tags_font_style.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.fontComboBox__tags_font_style.setFrame(False)
        self.horizontalLayout__tags_font_style.addWidget(
            self.fontComboBox__tags_font_style
        )
        self.horizontalLayout__tags_font_size.addLayout(
            self.horizontalLayout__tags_font_style
        )
        self.verticalLayout__tags_font_size.addLayout(
            self.horizontalLayout__tags_font_size
        )
        self.verticalLayout__text_settings.addWidget(self.groupBox__tags)

    def _build_debug_font(self, window: QDialog) -> None:
        self.groupBox__debug = QGroupBox(self.tab__text)
        self.groupBox__debug.setObjectName("groupBox__debug")
        self.groupBox__debug.setTitle(_translate("Debug"))
        self.verticalLayout__debug_font_size = QVBoxLayout(self.groupBox__debug)
        self.verticalLayout__debug_font_size.setObjectName(
            "verticalLayout__debug_font_size"
        )
        self.horizontalLayout__debug_font_size = QHBoxLayout()
        self.horizontalLayout__debug_font_size.setSpacing(15)
        self.horizontalLayout__debug_font_size.setObjectName(
            "horizontalLayout__debug_font_size"
        )
        self.horizontalLayout__debug_font_size_row = QHBoxLayout()
        self.horizontalLayout__debug_font_size_row.setObjectName(
            "horizontalLayout__debug_font_size_row"
        )
        self.label__debug_font_size = QLabel(self.groupBox__debug)
        self.label__debug_font_size.setObjectName("label__debug_font_size")
        self.label__debug_font_size.setText(_translate("Font Size"))
        self.horizontalLayout__debug_font_size_row.addWidget(
            self.label__debug_font_size
        )
        self.spinBox__debug_font_size = QSpinBox(self.groupBox__debug)
        self.spinBox__debug_font_size.setObjectName("spinBox__debug_font_size")
        self.spinBox__debug_font_size.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.spinBox__debug_font_size.setFrame(False)
        self.spinBox__debug_font_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinBox__debug_font_size.setMinimum(2)
        self.spinBox__debug_font_size.setMaximum(50)
        self.spinBox__debug_font_size.setValue(11)
        self.horizontalLayout__debug_font_size_row.addWidget(
            self.spinBox__debug_font_size
        )
        self.horizontalLayout__debug_font_size.addLayout(
            self.horizontalLayout__debug_font_size_row
        )
        self.spacer__debug_font_size = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__debug_font_size.addItem(self.spacer__debug_font_size)
        self.horizontalLayout__debug_font_style = QHBoxLayout()
        self.horizontalLayout__debug_font_style.setObjectName(
            "horizontalLayout__debug_font_style"
        )
        self.label__debug_font_style = QLabel(self.groupBox__debug)
        self.label__debug_font_style.setObjectName("label__debug_font_style")
        self.label__debug_font_style.setText(_translate("Font Style"))
        self.horizontalLayout__debug_font_style.addWidget(self.label__debug_font_style)
        self.fontComboBox__debug_font_style = QFontComboBox(self.groupBox__debug)
        self.fontComboBox__debug_font_style.setObjectName(
            "fontComboBox__debug_font_style"
        )
        self.fontComboBox__debug_font_style.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.fontComboBox__debug_font_style.setFrame(False)
        self.horizontalLayout__debug_font_style.addWidget(
            self.fontComboBox__debug_font_style
        )
        self.horizontalLayout__debug_font_size.addLayout(
            self.horizontalLayout__debug_font_style
        )
        self.verticalLayout__debug_font_size.addLayout(
            self.horizontalLayout__debug_font_size
        )
        self.verticalLayout__text_settings.addWidget(self.groupBox__debug)
        self.tabWidget__view_settings.addTab(
            self.tab__text, QIcon(":/main/icons/case_sensitive.png"), _translate("Text")
        )
        self.verticalLayout__view_settings.addWidget(self.tabWidget__view_settings)
        self.verticalLayout__appearance_groups.addWidget(self.groupBox__default_icon)
        self.horizontalLayout__appearance.addLayout(
            self.verticalLayout__appearance_groups
        )
        self.verticalLayout__preferences.addWidget(self.groupBox__app_properties)

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
