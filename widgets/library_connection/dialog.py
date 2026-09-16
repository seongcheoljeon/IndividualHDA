"""A focused connection dialog. Credentials live only in the current session."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs.settings_store import save_json
from libs.task_controller import TaskController
from libs.team.client import BlobCache, HttpCatalog, HttpTransport
from libs.team.contracts import API_PREFIX


class ConnectionDialog(QtWidgets.QDialog):
    connected = QtCore.Signal(object, object)

    def __init__(
        self, config_root: Path, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Connect team library")
        self.setMinimumWidth(420)
        self._root = config_root
        self._tasks = TaskController(self)
        self._tasks.result.connect(self._result)
        self._tasks.idle.connect(self._idle)
        self._closing = False
        self._transport: HttpTransport | None = None
        self._identity: dict[str, Any] = {}
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.lineEdit__server_url = QtWidgets.QLineEdit()
        self.lineEdit__server_url.setObjectName("lineEdit__server_url")
        self.lineEdit__server_url.setPlaceholderText("https://library.studio.example")
        self.lineEdit__access_token = QtWidgets.QLineEdit()
        self.lineEdit__access_token.setObjectName("lineEdit__access_token")
        self.lineEdit__access_token.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.lineEdit__access_token.setPlaceholderText(
            "Access token from your administrator"
        )
        self.lineEdit__access_token.setText(os.environ.get("IHDA_TEAM_TOKEN", ""))
        self.comboBox__project = QtWidgets.QComboBox()
        self.comboBox__project.setObjectName("comboBox__project")
        form.addRow("Server", self.lineEdit__server_url)
        form.addRow("Access token", self.lineEdit__access_token)
        form.addRow("Project", self.comboBox__project)
        self.comboBox__project.setEnabled(False)
        layout.addLayout(form)
        self.label__connection_status = QtWidgets.QLabel(
            "The access token is not saved on disk."
        )
        self.label__connection_status.setObjectName("label__connection_status")
        self.label__connection_status.setWordWrap(True)
        layout.addWidget(self.label__connection_status)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.pushButton__connect = buttons.addButton(
            "Connect", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        self.pushButton__connect.setObjectName("pushButton__connect")
        self.pushButton__open_library = buttons.addButton(
            "Open library", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.pushButton__open_library.setObjectName("pushButton__open_library")
        self.pushButton__open_library.setEnabled(False)
        self.pushButton__connect.clicked.connect(self._connect)
        buttons.accepted.connect(self._open)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        try:
            settings = json.loads(
                (config_root / "workspace.json").read_text(encoding="utf-8")
            )
            self.lineEdit__server_url.setText(settings.get("server_url", ""))
        except (OSError, ValueError):
            pass
        self.lineEdit__server_url.textChanged.connect(self._invalidate)
        self.lineEdit__access_token.textChanged.connect(self._invalidate)

    def _invalidate(self) -> None:
        self._transport = None
        self.comboBox__project.clear()
        self.comboBox__project.setEnabled(False)
        self.pushButton__open_library.setEnabled(False)

    def _connect(self) -> None:
        if self._tasks.busy:
            return
        self._invalidate()
        url = self.lineEdit__server_url.text().strip()
        token = self.lineEdit__access_token.text().strip()

        def connect() -> tuple[HttpTransport, dict[str, Any]]:
            transport = HttpTransport(url, lambda: token)
            from libs.team.contracts import API_VERSION, TeamError

            if transport.request("GET", "/health").get("api_version") != API_VERSION:
                raise TeamError(
                    "Update the app and server together: API v2 is required"
                )
            return transport, transport.request("GET", API_PREFIX + "/me")

        self.lineEdit__server_url.setEnabled(False)
        self.lineEdit__access_token.setEnabled(False)
        self.pushButton__connect.setEnabled(False)
        self.label__connection_status.setText("Connecting…")
        self._tasks.start(connect, self._ready)

    def _ready(self, result: tuple[HttpTransport, dict[str, Any]]) -> None:
        if self._closing:
            return
        self._transport, self._identity = result
        for project in self._identity["projects"]:
            self.comboBox__project.addItem(project["name"], project)
        available = self.comboBox__project.count() > 0
        self.comboBox__project.setEnabled(available)
        self.pushButton__open_library.setEnabled(available)
        self.label__connection_status.setText(
            "Choose a project."
            if available
            else "No projects are available. Ask your administrator for access."
        )

    def _result(self, value: Any, error: Any) -> None:
        if error is not None and not self._closing:
            self.label__connection_status.setText(str(error))

    def _idle(self) -> None:
        if self._closing:
            super().reject()
        else:
            self.lineEdit__server_url.setEnabled(True)
            self.lineEdit__access_token.setEnabled(True)
            self.pushButton__connect.setEnabled(True)

    def _open(self) -> None:
        project = self.comboBox__project.currentData()
        if self._transport is None or project is None or self._tasks.busy:
            return
        namespace = (
            self._transport.url + "/" + project["id"] + "/" + self._identity["user_id"]
        )
        backend = HttpCatalog(
            self._transport, project["id"], BlobCache(self._root / "cache", namespace)
        )
        save_json(self._root / "workspace.json", {"server_url": self._transport.url})
        self.connected.emit(backend, project)
        self.accept()

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
