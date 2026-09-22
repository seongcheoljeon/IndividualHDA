"""Owner-only project membership settings, independent of asset editing."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from PySide6 import QtWidgets

from libs.task_controller import TaskController
from libs.team.client import Transport
from libs.team.contracts import API_PREFIX

COLUMNS = ("Name", "User ID", "Role")
REMOVE_ACCESS = "Remove access"
ERROR_STYLE = "color: #d9534f;"


def valid_user_id(text: str) -> bool:
    try:
        UUID(text)
    except ValueError:
        return False
    return True


class MembersDialog(QtWidgets.QDialog):
    def __init__(
        self,
        transport: Transport,
        project: dict[str, Any],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self._project_name = project["name"]
        self.setWindowTitle(self._project_name + " — Members")
        self.resize(520, 400)
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
        self.tableWidget__members = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.tableWidget__members.setObjectName("tableWidget__members")
        self.tableWidget__members.setHorizontalHeaderLabels(list(COLUMNS))
        self.tableWidget__members.verticalHeader().hide()
        self.tableWidget__members.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tableWidget__members.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tableWidget__members.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tableWidget__members.setAlternatingRowColors(True)
        self.tableWidget__members.setShowGrid(False)
        header = self.tableWidget__members.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.tableWidget__members.setToolTip("Select a member to change their role")
        layout.addWidget(self.tableWidget__members)
        form = QtWidgets.QFormLayout()
        self.lineEdit__member_id = QtWidgets.QLineEdit()
        self.lineEdit__member_id.setObjectName("lineEdit__member_id")
        self.lineEdit__member_id.setPlaceholderText(
            "User ID issued by the administrator"
        )
        self.lineEdit__member_id.setToolTip(
            "Paste a user ID to add someone who is not a member yet"
        )
        self.lineEdit__member_id.setClearButtonEnabled(True)
        self.comboBox__member_role = QtWidgets.QComboBox()
        self.comboBox__member_role.setObjectName("comboBox__member_role")
        self.comboBox__member_role.addItems(
            ["viewer", "editor", "owner", REMOVE_ACCESS]
        )
        self.comboBox__member_role.setToolTip(
            "viewer: read only · editor: edit assets · owner: manage members"
        )
        form.addRow("Member", self.lineEdit__member_id)
        form.addRow("Role", self.comboBox__member_role)
        layout.addLayout(form)
        self.label__member_status = QtWidgets.QLabel()
        self.label__member_status.setObjectName("label__member_status")
        self.label__member_status.setWordWrap(True)
        layout.addWidget(self.label__member_status)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        self.pushButton__save_member = buttons.addButton(
            "Save membership", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        self.pushButton__save_member.setObjectName("pushButton__save_member")
        self.pushButton__save_member.setDefault(True)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.tableWidget__members.currentCellChanged.connect(self._select)
        self.lineEdit__member_id.textChanged.connect(self._validate)
        self.pushButton__save_member.clicked.connect(self._save)
        self._members: list[dict[str, Any]] = []
        self._refresh()

    def _status(self, message: str, *, error: bool = False) -> None:
        self.label__member_status.setText(message)
        self.label__member_status.setStyleSheet(ERROR_STYLE if error else "")

    def _refresh(self) -> None:
        self.pushButton__save_member.setEnabled(False)
        self._tasks.start(
            lambda: self._transport.request("GET", self._base + "/members"),
            self._loaded,
        )

    def _loaded(self, members: list[dict[str, Any]]) -> None:
        if self._closing:
            return
        self._members = sorted(members, key=lambda m: str(m["name"]).casefold())
        table = self.tableWidget__members
        table.setRowCount(len(self._members))
        for row, member in enumerate(self._members):
            for column, key in enumerate(("name", "user_id", "role")):
                item = QtWidgets.QTableWidgetItem(str(member[key]))
                item.setToolTip(str(member["user_id"]))
                table.setItem(row, column, item)

    def _select(self, row: int, *_: Any) -> None:
        if 0 <= row < len(self._members):
            member = self._members[row]
            self.lineEdit__member_id.setText(member["user_id"])
            self.comboBox__member_role.setCurrentText(member["role"])

    def _validate(self, text: str) -> None:
        """Save only with a full user ID; typing shows what is missing."""
        valid = valid_user_id(text.strip())
        self.pushButton__save_member.setEnabled(valid and not self._tasks.busy)
        if text.strip() and not valid:
            self._status("Enter the user's full ID (a UUID).", error=True)
        elif self.label__member_status.styleSheet():
            self._status("")

    def _member_name(self, user_id: str) -> str:
        return next(
            (str(m["name"]) for m in self._members if m["user_id"] == user_id), user_id
        )

    def _save(self) -> None:
        user_id = self.lineEdit__member_id.text().strip()
        if not valid_user_id(user_id) or self._tasks.busy:
            return
        role = self.comboBox__member_role.currentText()
        value = None if role == REMOVE_ACCESS else role
        if value is None:
            answer = QtWidgets.QMessageBox.question(
                self,
                REMOVE_ACCESS,
                f"Remove {self._member_name(user_id)} from {self._project_name}?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        self.pushButton__save_member.setEnabled(False)
        self._status("Saving…")
        self._tasks.start(
            lambda: self._transport.request(
                "PUT", self._base + "/members/" + user_id, {"role": value}
            ),
            self._saved,
        )

    def _saved(self, result: Any) -> None:
        self._reload = True
        self._status(
            "Membership saved. Reconnect to update your current session's controls."
        )

    def _result(self, value: Any, error: Any) -> None:
        if error is not None and not self._closing:
            self._status(str(error), error=True)

    def _idle(self) -> None:
        if self._closing:
            super().reject()
        elif self._reload:
            self._reload = False
            self._refresh()
        else:
            self._validate(self.lineEdit__member_id.text())

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
