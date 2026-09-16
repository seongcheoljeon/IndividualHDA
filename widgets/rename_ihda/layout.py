"""Code-built Rename layout.

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
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)

from widgets.layout_helpers import make_font, size_policy

from . import rename_ihda_icons_rc  # noqa: F401 (register bundled icons)


def _translate(text: str) -> str:
    return QCoreApplication.translate("Dialog__rename_ihda", text)


class RenameLayout:
    def build_ui(self, window: QDialog) -> None:
        self._configure_window(window)
        self._build_name_preview(window)
        self._build_name_input(window)
        self._build_validation_feedback(window)
        self._build_dialog_buttons(window)

    def _configure_window(self, window: QDialog) -> None:
        if not window.objectName():
            window.setObjectName("Dialog__rename_ihda")
        window.resize(577, 202)
        window.setFont(make_font(point_size=11))
        window.setWindowIcon(QIcon(":/main/icons/viewport_logo_trans.png"))
        window.setWindowTitle(_translate("iHDA Rename"))
        self.verticalLayout__rename_dialog = QVBoxLayout(window)
        self.verticalLayout__rename_dialog.setObjectName(
            "verticalLayout__rename_dialog"
        )

    def _build_name_preview(self, window: QDialog) -> None:
        self.horizontalLayout__name_preview = QHBoxLayout()
        self.horizontalLayout__name_preview.setObjectName(
            "horizontalLayout__name_preview"
        )
        self.label__pixmap = QLabel(window)
        self.label__pixmap.setObjectName("label__pixmap")
        self.label__pixmap.setMaximumSize(QSize(50, 50))
        self.label__pixmap.setPixmap(QPixmap(":/main/icons/ic_translate_white.png"))
        self.label__pixmap.setScaledContents(True)
        self.label__pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__pixmap.setText("")
        self.horizontalLayout__name_preview.addWidget(self.label__pixmap)
        self.verticalLayout__rename_content = QVBoxLayout()
        self.verticalLayout__rename_content.setObjectName(
            "verticalLayout__rename_content"
        )
        self.horizontalLayout__name_summary = QHBoxLayout()
        self.horizontalLayout__name_summary.setObjectName(
            "horizontalLayout__name_summary"
        )
        self.horizontalLayout__old_name = QHBoxLayout()
        self.horizontalLayout__old_name.setObjectName("horizontalLayout__old_name")
        self.horizontalLayout__old_name_parts = QHBoxLayout()
        self.horizontalLayout__old_name_parts.setObjectName(
            "horizontalLayout__old_name_parts"
        )
        self.label__old_ihda_name_prefix = QLabel(window)
        self.label__old_ihda_name_prefix.setObjectName("label__old_ihda_name_prefix")
        self.label__old_ihda_name_prefix.setText(_translate("OLD Name: "))
        self.horizontalLayout__old_name_parts.addWidget(
            self.label__old_ihda_name_prefix
        )
        self.label__old_ihda_name = QLabel(window)
        self.label__old_ihda_name.setObjectName("label__old_ihda_name")
        self.label__old_ihda_name.setText("")
        self.horizontalLayout__old_name_parts.addWidget(self.label__old_ihda_name)
        self.horizontalLayout__old_name.addLayout(self.horizontalLayout__old_name_parts)
        self.spacer__old_name = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__old_name.addItem(self.spacer__old_name)
        self.label__bridge = QLabel(window)
        self.label__bridge.setObjectName("label__bridge")
        self.label__bridge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__bridge.setText(_translate("----->"))
        self.horizontalLayout__old_name.addWidget(self.label__bridge)
        self.horizontalLayout__new_name = QHBoxLayout()
        self.horizontalLayout__new_name.setObjectName("horizontalLayout__new_name")
        self.spacer__new_name = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__new_name.addItem(self.spacer__new_name)
        self.label__new_ihda_name_prefix = QLabel(window)
        self.label__new_ihda_name_prefix.setObjectName("label__new_ihda_name_prefix")
        self.label__new_ihda_name_prefix.setText(_translate("NEW Name: "))
        self.horizontalLayout__new_name.addWidget(self.label__new_ihda_name_prefix)
        self.label__new_ihda_name = QLabel(window)
        self.label__new_ihda_name.setObjectName("label__new_ihda_name")
        self.label__new_ihda_name.setText("")
        self.horizontalLayout__new_name.addWidget(self.label__new_ihda_name)
        self.horizontalLayout__old_name.addLayout(self.horizontalLayout__new_name)
        self.horizontalLayout__name_summary.addLayout(self.horizontalLayout__old_name)
        self.spacer__name_summary = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__name_summary.addItem(self.spacer__name_summary)
        self.verticalLayout__rename_content.addLayout(
            self.horizontalLayout__name_summary
        )

    def _build_name_input(self, window: QDialog) -> None:
        self.line__name_separator = QFrame(window)
        self.line__name_separator.setObjectName("line__name_separator")
        self.line__name_separator.setFrameShape(QFrame.Shape.HLine)
        self.line__name_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.verticalLayout__rename_content.addWidget(self.line__name_separator)
        self.horizontalLayout__name_input = QHBoxLayout()
        self.horizontalLayout__name_input.setObjectName("horizontalLayout__name_input")
        self.label__input_ihda_name_prefix = QLabel(window)
        self.label__input_ihda_name_prefix.setObjectName(
            "label__input_ihda_name_prefix"
        )
        self.label__input_ihda_name_prefix.setText(_translate("Input Name: "))
        self.horizontalLayout__name_input.addWidget(self.label__input_ihda_name_prefix)
        self.lineEdit__input_ihda_name = QLineEdit(window)
        self.lineEdit__input_ihda_name.setObjectName("lineEdit__input_ihda_name")
        self.lineEdit__input_ihda_name.setPlaceholderText(
            _translate("Caution: Do not overlap with Houdini node type.")
        )
        self.horizontalLayout__name_input.addWidget(self.lineEdit__input_ihda_name)
        self.verticalLayout__rename_content.addLayout(self.horizontalLayout__name_input)

    def _build_validation_feedback(self, window: QDialog) -> None:
        self.horizontalLayout__validation_feedback = QHBoxLayout()
        self.horizontalLayout__validation_feedback.setObjectName(
            "horizontalLayout__validation_feedback"
        )
        self.label__confirm_ihda_name_pixmap = QLabel(window)
        self.label__confirm_ihda_name_pixmap.setObjectName(
            "label__confirm_ihda_name_pixmap"
        )
        self.label__confirm_ihda_name_pixmap.setSizePolicy(
            size_policy(
                self.label__confirm_ihda_name_pixmap,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        )
        self.label__confirm_ihda_name_pixmap.setMinimumSize(QSize(22, 22))
        self.label__confirm_ihda_name_pixmap.setMaximumSize(QSize(24, 24))
        self.label__confirm_ihda_name_pixmap.setPixmap(
            QPixmap(":/main/icons/ic_clear_white.png")
        )
        self.label__confirm_ihda_name_pixmap.setScaledContents(True)
        self.label__confirm_ihda_name_pixmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label__confirm_ihda_name_pixmap.setText("")
        self.horizontalLayout__validation_feedback.addWidget(
            self.label__confirm_ihda_name_pixmap
        )
        self.label__confirm_ihda_name = QLabel(window)
        self.label__confirm_ihda_name.setObjectName("label__confirm_ihda_name")
        self.label__confirm_ihda_name.setFont(make_font(point_size=12))
        self.label__confirm_ihda_name.setText("")
        self.horizontalLayout__validation_feedback.addWidget(
            self.label__confirm_ihda_name
        )
        self.spacer__validation_feedback = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.horizontalLayout__validation_feedback.addItem(
            self.spacer__validation_feedback
        )
        self.verticalLayout__rename_content.addLayout(
            self.horizontalLayout__validation_feedback
        )
        self.horizontalLayout__name_preview.addLayout(
            self.verticalLayout__rename_content
        )
        self.verticalLayout__rename_dialog.addLayout(
            self.horizontalLayout__name_preview
        )

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
        self.verticalLayout__rename_dialog.addWidget(self.buttonBox__confirm)
        self.buttonBox__confirm.accepted.connect(window.accept)
        self.buttonBox__confirm.rejected.connect(window.reject)
