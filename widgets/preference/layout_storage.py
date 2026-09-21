"""Storage and FFmpeg settings.

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
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from libs.ui_icons import Icon
from widgets.layout_helpers import make_font, preference_text, size_policy
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

if TYPE_CHECKING:
    from widgets.preference.layout import PreferenceLayout


def build_storage_settings(layout: PreferenceLayout, window: QDialog) -> None:
    layout.groupBox__data = QGroupBox(window)
    layout.groupBox__data.setObjectName("groupBox__data")
    layout.groupBox__data.setTitle(preference_text("Data (Required)"))
    layout.horizontalLayout__pixmap = QHBoxLayout(layout.groupBox__data)
    layout.horizontalLayout__pixmap.setObjectName("horizontalLayout__pixmap")
    layout.horizontalLayout__pixmap.setContentsMargins(5, 5, 5, 5)
    layout.label__pixmap = QLabel(layout.groupBox__data)
    layout.label__pixmap.setObjectName("label__pixmap")
    layout.label__pixmap.setMaximumSize(QSize(55, 55))
    layout.label__pixmap.setPixmap(QPixmap(":/main/icons/ic_settings_white.png"))
    layout.label__pixmap.setScaledContents(True)
    layout.label__pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.label__pixmap.setText("")
    layout.horizontalLayout__pixmap.addWidget(layout.label__pixmap)
    layout.verticalLayout__data_dirpath = QVBoxLayout()
    layout.verticalLayout__data_dirpath.setObjectName("verticalLayout__data_dirpath")
    layout.horizontalLayout__data_dirpath = QHBoxLayout()
    layout.horizontalLayout__data_dirpath.setObjectName(
        "horizontalLayout__data_dirpath"
    )
    layout.label__data_dirpath = QLabel(layout.groupBox__data)
    layout.label__data_dirpath.setObjectName("label__data_dirpath")
    layout.label__data_dirpath.setText(preference_text("Directory"))
    layout.horizontalLayout__data_dirpath.addWidget(layout.label__data_dirpath)
    layout.lineEdit__data_dirpath = QLineEdit(layout.groupBox__data)
    layout.lineEdit__data_dirpath.setObjectName("lineEdit__data_dirpath")
    layout.lineEdit__data_dirpath.setToolTip(preference_text("Data storage directory"))
    layout.lineEdit__data_dirpath.setPlaceholderText(
        preference_text("Choose a library directory")
    )
    layout.horizontalLayout__data_dirpath.addWidget(layout.lineEdit__data_dirpath)
    layout.toolButton__select_data_dirpath = QToolButton(layout.groupBox__data)
    layout.toolButton__select_data_dirpath.setObjectName(
        "toolButton__select_data_dirpath"
    )
    layout.toolButton__select_data_dirpath.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.toolButton__select_data_dirpath.setIcon(QIcon(Icon.IC_FOLDER_WHITE))
    layout.toolButton__select_data_dirpath.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.toolButton__select_data_dirpath.setToolTip(
        preference_text("Select the directory where data will be saved")
    )
    layout.toolButton__select_data_dirpath.setStatusTip(
        preference_text("Select the directory where data will be saved")
    )
    layout.toolButton__select_data_dirpath.setText("")
    layout.horizontalLayout__data_dirpath.addWidget(
        layout.toolButton__select_data_dirpath
    )
    layout.verticalLayout__data_dirpath.addLayout(layout.horizontalLayout__data_dirpath)
    layout.horizontalLayout__result_show = QHBoxLayout()
    layout.horizontalLayout__result_show.setObjectName("horizontalLayout__result_show")
    layout.label__result_show = QLabel(layout.groupBox__data)
    layout.label__result_show.setObjectName("label__result_show")
    layout.label__result_show.setSizePolicy(
        size_policy(
            layout.label__result_show,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Preferred,
        )
    )
    layout.label__result_show.setFont(make_font(point_size=11))
    layout.label__result_show.setText(preference_text("Final Path"))
    layout.horizontalLayout__result_show.addWidget(layout.label__result_show)
    layout.lineEdit__result = QLineEdit(layout.groupBox__data)
    layout.lineEdit__result.setObjectName("lineEdit__result")
    layout.lineEdit__result.setReadOnly(True)
    layout.lineEdit__result.setToolTip(preference_text("Final data storage directory"))
    layout.horizontalLayout__result_show.addWidget(layout.lineEdit__result)
    layout.label__valid_chk_pixmap = QLabel(layout.groupBox__data)
    layout.label__valid_chk_pixmap.setObjectName("label__valid_chk_pixmap")
    layout.label__valid_chk_pixmap.setSizePolicy(
        size_policy(
            layout.label__valid_chk_pixmap,
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
    )
    layout.label__valid_chk_pixmap.setMaximumSize(QSize(24, 24))
    layout.label__valid_chk_pixmap.setPixmap(QPixmap(Icon.IC_CLEAR_WHITE))
    layout.label__valid_chk_pixmap.setScaledContents(True)
    layout.label__valid_chk_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.label__valid_chk_pixmap.setToolTip(
        preference_text("It determines whether it is a valid directory")
    )
    layout.label__valid_chk_pixmap.setText("")
    layout.horizontalLayout__result_show.addWidget(layout.label__valid_chk_pixmap)
    layout.verticalLayout__data_dirpath.addLayout(layout.horizontalLayout__result_show)
    layout.horizontalLayout__pixmap.addLayout(layout.verticalLayout__data_dirpath)
    layout.verticalLayout__preferences.addWidget(layout.groupBox__data)


def build_ffmpeg_settings(layout: PreferenceLayout, window: QDialog) -> None:
    layout.groupBox__ffmpeg = QGroupBox(window)
    layout.groupBox__ffmpeg.setObjectName("groupBox__ffmpeg")
    layout.groupBox__ffmpeg.setTitle(preference_text("FFmpeg (Optional)"))
    layout.horizontalLayout__ffmpeg_pixmap = QHBoxLayout(layout.groupBox__ffmpeg)
    layout.horizontalLayout__ffmpeg_pixmap.setObjectName(
        "horizontalLayout__ffmpeg_pixmap"
    )
    layout.horizontalLayout__ffmpeg_pixmap.setContentsMargins(5, 5, 5, 5)
    layout.label__ffmpeg_pixmap = QLabel(layout.groupBox__ffmpeg)
    layout.label__ffmpeg_pixmap.setObjectName("label__ffmpeg_pixmap")
    layout.label__ffmpeg_pixmap.setSizePolicy(
        size_policy(
            layout.label__ffmpeg_pixmap,
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
    )
    layout.label__ffmpeg_pixmap.setMaximumSize(QSize(55, 55))
    layout.label__ffmpeg_pixmap.setPixmap(QPixmap(":/main/icons/ffmpeg.png"))
    layout.label__ffmpeg_pixmap.setScaledContents(True)
    layout.label__ffmpeg_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.label__ffmpeg_pixmap.setText("")
    layout.horizontalLayout__ffmpeg_pixmap.addWidget(layout.label__ffmpeg_pixmap)
    layout.verticalLayout__ffmpeg_dirpath = QVBoxLayout()
    layout.verticalLayout__ffmpeg_dirpath.setObjectName(
        "verticalLayout__ffmpeg_dirpath"
    )
    layout.horizontalLayout__ffmpeg_dirpath = QHBoxLayout()
    layout.horizontalLayout__ffmpeg_dirpath.setObjectName(
        "horizontalLayout__ffmpeg_dirpath"
    )
    layout.label__ffmpeg_dirpath = QLabel(layout.groupBox__ffmpeg)
    layout.label__ffmpeg_dirpath.setObjectName("label__ffmpeg_dirpath")
    layout.label__ffmpeg_dirpath.setText(preference_text("Directory"))
    layout.horizontalLayout__ffmpeg_dirpath.addWidget(layout.label__ffmpeg_dirpath)
    layout.lineEdit__ffmpeg_dirpath = QLineEdit(layout.groupBox__ffmpeg)
    layout.lineEdit__ffmpeg_dirpath.setObjectName("lineEdit__ffmpeg_dirpath")
    layout.lineEdit__ffmpeg_dirpath.setToolTip(
        preference_text("Installed FFmpeg directory")
    )
    layout.lineEdit__ffmpeg_dirpath.setPlaceholderText(
        preference_text("Optional FFmpeg directory")
    )
    layout.horizontalLayout__ffmpeg_dirpath.addWidget(layout.lineEdit__ffmpeg_dirpath)
    layout.toolButton__select_ffmpeg_dirpath = QToolButton(layout.groupBox__ffmpeg)
    layout.toolButton__select_ffmpeg_dirpath.setObjectName(
        "toolButton__select_ffmpeg_dirpath"
    )
    layout.toolButton__select_ffmpeg_dirpath.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    layout.toolButton__select_ffmpeg_dirpath.setIcon(QIcon(Icon.IC_FOLDER_WHITE))
    layout.toolButton__select_ffmpeg_dirpath.setIconSize(
        QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
    )
    layout.toolButton__select_ffmpeg_dirpath.setToolTip(
        preference_text("Select the directory where FFmpeg is installed")
    )
    layout.toolButton__select_ffmpeg_dirpath.setStatusTip(
        preference_text("Select the directory where FFmpeg is installed")
    )
    layout.toolButton__select_ffmpeg_dirpath.setText("")
    layout.horizontalLayout__ffmpeg_dirpath.addWidget(
        layout.toolButton__select_ffmpeg_dirpath
    )
    layout.verticalLayout__ffmpeg_dirpath.addLayout(
        layout.horizontalLayout__ffmpeg_dirpath
    )
    layout.horizontalLayout__ffmpeg_result_show = QHBoxLayout()
    layout.horizontalLayout__ffmpeg_result_show.setObjectName(
        "horizontalLayout__ffmpeg_result_show"
    )
    layout.label__ffmpeg_result_show = QLabel(layout.groupBox__ffmpeg)
    layout.label__ffmpeg_result_show.setObjectName("label__ffmpeg_result_show")
    layout.label__ffmpeg_result_show.setSizePolicy(
        size_policy(
            layout.label__ffmpeg_result_show,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Preferred,
        )
    )
    layout.label__ffmpeg_result_show.setFont(make_font(point_size=11))
    layout.label__ffmpeg_result_show.setText(preference_text("Final Path"))
    layout.horizontalLayout__ffmpeg_result_show.addWidget(
        layout.label__ffmpeg_result_show
    )
    layout.lineEdit__ffmpeg_result = QLineEdit(layout.groupBox__ffmpeg)
    layout.lineEdit__ffmpeg_result.setObjectName("lineEdit__ffmpeg_result")
    layout.lineEdit__ffmpeg_result.setReadOnly(True)
    layout.lineEdit__ffmpeg_result.setToolTip(
        preference_text("Final installed FFmpeg directory")
    )
    layout.horizontalLayout__ffmpeg_result_show.addWidget(
        layout.lineEdit__ffmpeg_result
    )
    layout.label__ffmpeg_valid_chk_pixmap = QLabel(layout.groupBox__ffmpeg)
    layout.label__ffmpeg_valid_chk_pixmap.setObjectName(
        "label__ffmpeg_valid_chk_pixmap"
    )
    layout.label__ffmpeg_valid_chk_pixmap.setSizePolicy(
        size_policy(
            layout.label__ffmpeg_valid_chk_pixmap,
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
    )
    layout.label__ffmpeg_valid_chk_pixmap.setMaximumSize(QSize(24, 24))
    layout.label__ffmpeg_valid_chk_pixmap.setPixmap(QPixmap(Icon.IC_CLEAR_WHITE))
    layout.label__ffmpeg_valid_chk_pixmap.setScaledContents(True)
    layout.label__ffmpeg_valid_chk_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.label__ffmpeg_valid_chk_pixmap.setToolTip(
        preference_text("It determines whether it is a valid directory")
    )
    layout.label__ffmpeg_valid_chk_pixmap.setText("")
    layout.horizontalLayout__ffmpeg_result_show.addWidget(
        layout.label__ffmpeg_valid_chk_pixmap
    )
    layout.verticalLayout__ffmpeg_dirpath.addLayout(
        layout.horizontalLayout__ffmpeg_result_show
    )
    layout.horizontalLayout__ffmpeg_pixmap.addLayout(
        layout.verticalLayout__ffmpeg_dirpath
    )
    layout.verticalLayout__preferences.addWidget(layout.groupBox__ffmpeg)
