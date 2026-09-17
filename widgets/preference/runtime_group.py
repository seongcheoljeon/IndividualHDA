"""Collapsible runtime preferences; values are applied on the next panel start."""

from dataclasses import asdict

from PySide6 import QtCore, QtWidgets

from libs.runtime_settings import RUNTIME_FIELDS, RuntimeSettings


class RuntimeGroup(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("widget__runtime_settings")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        toggle = QtWidgets.QToolButton(self)
        toggle.setObjectName("toolButton__runtime_settings")
        toggle.setText("Performance and connections")
        toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        toggle.setCheckable(True)
        layout.addWidget(toggle)
        body = QtWidgets.QWidget(self)
        form = QtWidgets.QFormLayout(body)
        note = QtWidgets.QLabel(
            "Save and reopen the panel to apply these settings.", body
        )
        note.setWordWrap(True)
        form.addRow(note)
        self.inputs: dict[str, QtWidgets.QSpinBox] = {}
        for name, spec in RUNTIME_FIELDS.items():
            spin = QtWidgets.QSpinBox(body)
            spin.setObjectName(f"spinBox__runtime_{name}")
            spin.setRange(spec.minimum, spec.maximum)
            spin.setSuffix(spec.suffix)
            spin.setToolTip(spec.description)
            form.addRow(spec.label, spin)
            self.inputs[name] = spin
        reset = QtWidgets.QPushButton("Restore performance defaults", body)
        reset.setObjectName("pushButton__reset_runtime")
        reset.clicked.connect(lambda: self.set_settings(RuntimeSettings()))
        form.addRow(reset)
        layout.addWidget(body)
        body.hide()

        def expanded(checked: bool) -> None:
            body.setVisible(checked)
            toggle.setArrowType(
                QtCore.Qt.ArrowType.DownArrow
                if checked
                else QtCore.Qt.ArrowType.RightArrow
            )

        toggle.toggled.connect(expanded)
        self.set_settings(RuntimeSettings())

    def settings(self) -> RuntimeSettings:
        return RuntimeSettings(
            **{name: spin.value() for name, spin in self.inputs.items()}
        )

    def set_settings(self, settings: RuntimeSettings) -> None:
        for name, value in asdict(settings).items():
            self.inputs[name].setValue(value)
