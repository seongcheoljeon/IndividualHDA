"""Pending registrations in Library Tools; retries reuse the stored request."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs.task_controller import TaskController


class RegistrationRecoveryDialog(QtWidgets.QDialog):
    changed = QtCore.Signal()

    def __init__(
        self,
        jobs: Callable[[], list[dict[str, Any]]],
        retry: Callable[[str], Any],
        discard: Callable[[str], None],
        parent: QtWidgets.QWidget,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pending registrations")
        self.resize(700, 350)
        self._jobs, self._retry, self._discard = jobs, retry, discard
        self._tasks = TaskController(self)
        self._tasks.result.connect(self._result)
        self._tasks.idle.connect(self._idle)
        self._reload = False
        self._closing = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                "Retry resumes captured files. An interrupted capture must be captured again in Houdini."
            )
        )
        self.listWidget__jobs = QtWidgets.QListWidget()
        layout.addWidget(self.listWidget__jobs)
        self.label__status = QtWidgets.QLabel()
        self.label__status.setWordWrap(True)
        layout.addWidget(self.label__status)
        buttons = QtWidgets.QHBoxLayout()
        for title, action in (
            ("Refresh", self.reload),
            ("Retry selected", self.retry),
            ("Discard selected…", self.discard),
        ):
            button = QtWidgets.QPushButton(title)
            button.clicked.connect(action)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.reload()

    def reload(self) -> None:
        self._tasks.start(self._jobs, self._loaded)

    def _loaded(self, rows: list[dict[str, Any]]) -> None:
        self.listWidget__jobs.clear()
        for row in rows:
            if row["phase"] in {"committed", "discarded"}:
                continue
            item = QtWidgets.QListWidgetItem(
                f"{row.get('name', 'Registration')} {row.get('version', '')} · {row['phase']}\n{row.get('error') or 'Ready for review'}"
            )
            item.setToolTip("Request: " + row["id"])
            item.setData(QtCore.Qt.ItemDataRole.UserRole, row["id"])
            self.listWidget__jobs.addItem(item)
        if not self.listWidget__jobs.count():
            self.label__status.setText("No pending registrations")

    def retry(self) -> None:
        self._change(self._retry)

    def discard(self) -> None:
        if self._tasks.busy or self.listWidget__jobs.currentItem() is None:
            return
        if (
            QtWidgets.QMessageBox.question(
                self,
                "Discard registration",
                "Discard this attempt and remove only files owned by it? Submitted Team requests must first be resolved by Retry.",
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self._change(self._discard)

    def _change(self, operation: Callable[[str], Any]) -> None:
        item = self.listWidget__jobs.currentItem()
        if item is not None:
            identity = item.data(QtCore.Qt.ItemDataRole.UserRole)
            self._tasks.start(lambda: operation(identity), self._changed)

    def _changed(self, result: Any) -> None:
        self._reload = True
        self.changed.emit()

    def _result(self, value: Any, error: Exception | None) -> None:
        self.label__status.setText(str(error) if error else "Completed")

    def _idle(self) -> None:
        if self._closing:
            super().done(QtWidgets.QDialog.DialogCode.Rejected)
        elif self._reload:
            self._reload = False
            self.reload()

    def shutdown(self) -> None:
        self._closing = True
        self._tasks.drain()

    def done(self, result: int) -> None:
        if self._tasks.busy:
            self._closing = True
        else:
            super().done(result)
