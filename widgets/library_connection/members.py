"""Owner-only project membership settings, independent of asset editing."""

from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from libs.task_controller import TaskController
from libs.team.client import Transport
from libs.team.contracts import API_PREFIX


class MembersDialog(QtWidgets.QDialog):
    def __init__(
        self,
        transport: Transport,
        project: dict[str, Any],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(project["name"] + " — Members")
        self.resize(480, 380)
        self._transport, self._base = (
            transport,
            API_PREFIX + "/projects/" + project["id"],
        )
        self._tasks = TaskController(self)
        self._tasks.result.connect(self._result)
        self._tasks.idle.connect(self._idle)
        self._closing = False
        self._reload = False
        layout = QtWidgets.QVBoxLayout(self)
        self.listWidget__members = QtWidgets.QListWidget()
        self.listWidget__members.setObjectName("listWidget__members")
        layout.addWidget(self.listWidget__members)
        form = QtWidgets.QFormLayout()
        self.lineEdit__member_id = QtWidgets.QLineEdit()
        self.lineEdit__member_id.setObjectName("lineEdit__member_id")
        self.lineEdit__member_id.setPlaceholderText(
            "User ID issued by the administrator"
        )
        self.comboBox__member_role = QtWidgets.QComboBox()
        self.comboBox__member_role.setObjectName("comboBox__member_role")
        self.comboBox__member_role.addItems(
            ["viewer", "editor", "owner", "Remove access"]
        )
        form.addRow("Member", self.lineEdit__member_id)
        form.addRow("Role", self.comboBox__member_role)
        layout.addLayout(form)
        self.pushButton__save_member = QtWidgets.QPushButton("Save membership")
        self.pushButton__save_member.setObjectName("pushButton__save_member")
        layout.addWidget(self.pushButton__save_member)
        self.label__member_status = QtWidgets.QLabel()
        self.label__member_status.setObjectName("label__member_status")
        self.label__member_status.setWordWrap(True)
        layout.addWidget(self.label__member_status)
        self.listWidget__members.currentRowChanged.connect(self._select)
        self.pushButton__save_member.clicked.connect(self._save)
        self._members: list[dict[str, Any]] = []
        self._refresh()

    def _refresh(self) -> None:
        self.pushButton__save_member.setEnabled(False)
        self._tasks.start(
            lambda: self._transport.request("GET", self._base + "/members"),
            self._loaded,
        )

    def _loaded(self, members: list[dict[str, Any]]) -> None:
        if self._closing:
            return
        self._members = members
        self.listWidget__members.clear()
        for member in members:
            self.listWidget__members.addItem(member["name"] + " · " + member["role"])

    def _select(self, row: int) -> None:
        if 0 <= row < len(self._members):
            member = self._members[row]
            self.lineEdit__member_id.setText(member["user_id"])
            self.comboBox__member_role.setCurrentText(member["role"])

    def _save(self) -> None:
        from uuid import UUID

        user_id = self.lineEdit__member_id.text().strip()
        try:
            UUID(user_id)
        except ValueError:
            self.label__member_status.setText("Enter the user's full ID.")
            return
        role = self.comboBox__member_role.currentText()
        value = None if role == "Remove access" else role
        self.pushButton__save_member.setEnabled(False)
        self._tasks.start(
            lambda: self._transport.request(
                "PUT", self._base + "/members/" + user_id, {"role": value}
            ),
            self._saved,
        )

    def _saved(self, result: Any) -> None:
        self._reload = True
        self.label__member_status.setText(
            "Membership saved. Reconnect to update your current session's controls."
        )

    def _result(self, value: Any, error: Any) -> None:
        if error is not None and not self._closing:
            self.label__member_status.setText(str(error))

    def _idle(self) -> None:
        if self._closing:
            super().reject()
        elif self._reload:
            self._reload = False
            self._refresh()
        else:
            self.pushButton__save_member.setEnabled(True)

    def reject(self) -> None:
        self._closing = True
        if not self._tasks.busy:
            super().reject()

    def closeEvent(self, event: Any) -> None:
        self.reject()
        if self._tasks.busy:
            event.ignore()
        else:
            event.accept()

    def shutdown(self) -> None:
        self._closing = True
        self._tasks.drain()
        super().reject()
