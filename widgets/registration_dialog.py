"""One form for everything a registration needs, validated as you type.

Replaces the chains of QInputDialog / QMessageBox prompts: name, category,
version and change description sit together, the reasons a request cannot go
are listed under the fields, and Register is enabled only when there are none.
"""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from libs.registration_request import RegistrationRequest, Taken, validate


class RegistrationDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        *,
        title: str,
        request: RegistrationRequest,
        categories: list[str] = [],  # noqa: B006 (read only)
        taken: Taken | None = None,
        lock_identity: bool = False,
        file: Path | None = None,
        thumbnail: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("Dialog__registration")
        self._taken = taken
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        if file is not None:
            self.label__file = QtWidgets.QLabel(file.name, self)
            self.label__file.setToolTip(str(file))
            form.addRow("File", self.label__file)
        self.lineEdit__name = QtWidgets.QLineEdit(request.name, self)
        self.lineEdit__name.setObjectName("lineEdit__name")
        form.addRow("Name", self.lineEdit__name)
        self.comboBox__category = QtWidgets.QComboBox(self)
        self.comboBox__category.setObjectName("comboBox__category")
        self.comboBox__category.setEditable(True)
        self.comboBox__category.addItems(sorted(set(categories) | {request.category}))
        self.comboBox__category.setCurrentText(request.category)
        form.addRow("Category", self.comboBox__category)
        self.lineEdit__version = QtWidgets.QLineEdit(request.version, self)
        self.lineEdit__version.setObjectName("lineEdit__version")
        form.addRow("Version", self.lineEdit__version)
        self.plainTextEdit__description = QtWidgets.QPlainTextEdit(
            request.description, self
        )
        self.plainTextEdit__description.setObjectName("plainTextEdit__description")
        self.plainTextEdit__description.setPlaceholderText("What changed? (optional)")
        self.plainTextEdit__description.setMaximumHeight(90)
        form.addRow("Change description", self.plainTextEdit__description)
        layout.addLayout(form)
        if thumbnail is not None and thumbnail.is_file():
            pixmap = QtGui.QPixmap(str(thumbnail))
            if not pixmap.isNull():
                self.label__thumbnail = QtWidgets.QLabel(self)
                self.label__thumbnail.setPixmap(
                    pixmap.scaled(
                        160,
                        160,
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                        QtCore.Qt.TransformationMode.SmoothTransformation,
                    )
                )
                layout.addWidget(
                    self.label__thumbnail, 0, QtCore.Qt.AlignmentFlag.AlignHCenter
                )
        self.label__errors = QtWidgets.QLabel(self)
        self.label__errors.setObjectName("label__errors")
        self.label__errors.setWordWrap(True)
        self.label__errors.setStyleSheet("color: #d9534f;")
        layout.addWidget(self.label__errors)
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.pushButton__register = self.buttonBox.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        self.pushButton__register.setText("Update" if lock_identity else "Register")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
        if lock_identity:
            # A new version keeps the asset's identity; only what is new is editable.
            self.lineEdit__name.setReadOnly(True)
            self.comboBox__category.setEnabled(False)
            self.lineEdit__version.setFocus()
        for signal in (
            self.lineEdit__name.textChanged,
            self.comboBox__category.currentTextChanged,
            self.lineEdit__version.textChanged,
        ):
            signal.connect(self._validate)
        self._validate()

    def request(self) -> RegistrationRequest:
        return RegistrationRequest(
            self.lineEdit__name.text(),
            self.comboBox__category.currentText(),
            self.lineEdit__version.text(),
            self.plainTextEdit__description.toPlainText(),
        ).normalized()

    def errors(self) -> list[str]:
        return validate(self.request(), taken=self._taken)

    def _validate(self) -> None:
        errors = self.errors()
        self.label__errors.setText("\n".join(errors))
        self.label__errors.setVisible(bool(errors))
        self.pushButton__register.setEnabled(not errors)

    def accept(self) -> None:
        if not self.errors():
            super().accept()
