"""Manual check entry and paged tracking views inside the existing details dialog."""

from __future__ import annotations

import json
from typing import Any, Literal, get_args

from PySide6 import QtCore, QtWidgets

from libs.library_metadata import new_identity, utc_now

TrackingPage = Literal["checks", "dependents", "scenes"]


def tracking_page(value: str) -> TrackingPage | None:
    """A page name from a Qt signal, or None when it is not one of ours."""
    return value if value in get_args(TrackingPage) else None  # type: ignore[return-value]


class TrackingDetails(QtWidgets.QWidget):
    check_requested = QtCore.Signal(object)
    page_requested = QtCore.Signal(str, int)

    def __init__(self, writable: bool, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.version_uuid: str | None = None
        self.pending: dict[str, Any] | None = None
        self.pages: dict[str, list[dict[str, Any]]] = {}
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.lineEdit__houdini_version = QtWidgets.QLineEdit()
        self.lineEdit__os = QtWidgets.QLineEdit()
        self.lineEdit__scope = QtWidgets.QLineEdit()
        self.lineEdit__notes = QtWidgets.QLineEdit()
        self.comboBox__result = QtWidgets.QComboBox()
        self.comboBox__result.addItems(["passed", "failed"])
        self.comboBox__supersedes = QtWidgets.QComboBox()
        for title, widget in (
            ("Houdini version", self.lineEdit__houdini_version),
            ("OS", self.lineEdit__os),
            ("What you checked", self.lineEdit__scope),
            ("Result", self.comboBox__result),
            ("Notes", self.lineEdit__notes),
            ("Corrects", self.comboBox__supersedes),
        ):
            form.addRow(title, widget)
            widget.setEnabled(writable)
        layout.addLayout(form)
        layout.addWidget(
            QtWidgets.QLabel(
                "Manual report for the selected version. Other environments remain unverified."
            )
        )
        self.pushButton__record_check = QtWidgets.QPushButton("Record check / Retry")
        self.pushButton__record_check.setEnabled(writable)
        self.pushButton__record_check.clicked.connect(self._record)
        layout.addWidget(self.pushButton__record_check)
        self.tabWidget__tracking = QtWidgets.QTabWidget()
        self.views: dict[TrackingPage, QtWidgets.QTextEdit] = {}
        pages: tuple[tuple[TrackingPage, str], ...] = (
            ("checks", "Checks"),
            ("dependents", "Used by assets"),
            ("scenes", "Used in scenes"),
        )
        for kind, label in pages:
            page = QtWidgets.QWidget()
            box = QtWidgets.QVBoxLayout(page)
            view = QtWidgets.QTextEdit()
            view.setReadOnly(True)
            self.views[kind] = view
            box.addWidget(view)
            more = QtWidgets.QPushButton("Load more")
            more.clicked.connect(
                lambda checked=False, k=kind: self.page_requested.emit(
                    k, len(self.pages.get(k, []))
                )
            )
            box.addWidget(more)
            self.tabWidget__tracking.addTab(page, label)
        layout.addWidget(self.tabWidget__tracking)

    def show_page(
        self, kind: TrackingPage, rows: list[dict[str, Any]], append: bool = False
    ) -> None:
        self.pages[kind] = self.pages.get(kind, []) + rows if append else rows
        lines = []
        for row in self.pages[kind]:
            document = row.get("document", {})
            if kind == "checks":
                lines.append(
                    f"{row['checked_at']} · {document['result']} · Houdini {document['houdini_version']} / {document['os']}\n{document['scope']} · {document.get('notes', '')}\nRecorded by {row['actor']} · {row['id']}"
                )
                if document.get("provenance"):
                    lines.append(
                        "Imported report from "
                        + document["provenance"].get("library_uuid", "another library")
                        + "; destination environment remains unverified."
                    )
            elif kind == "scenes":
                lines.append(
                    f"{document.get('scene_path') or 'Unsaved scene'} · {document.get('node_path', '')}\n{row['actor']} · {row['last_seen']} · {document.get('version', '')}"
                )
            else:
                source = row["source_version"]
                lines.append(
                    f"{source['name']} ({source['version']}) · {'required' if row['required'] else 'optional'}"
                )
        self.views[kind].setPlainText("\n\n".join(lines) or "No records")
        self.select_version(self.version_uuid)

    def select_version(self, uuid: str | None) -> None:
        self.version_uuid = uuid
        self.comboBox__supersedes.clear()
        self.comboBox__supersedes.addItem("New report", None)
        for row in self.pages.get("checks", []):
            if row["version_uuid"] == uuid:
                self.comboBox__supersedes.addItem(
                    f"{row['checked_at']} · {row['document']['result']}", row["id"]
                )

    def _record(self) -> None:
        if not self.version_uuid:
            return
        values = {
            "version_uuid": self.version_uuid,
            "houdini_version": self.lineEdit__houdini_version.text(),
            "os": self.lineEdit__os.text(),
            "scope": self.lineEdit__scope.text(),
            "notes": self.lineEdit__notes.text(),
            "result": self.comboBox__result.currentText(),
            "supersedes": self.comboBox__supersedes.currentData(),
        }
        content = json.dumps(values, sort_keys=True)
        if self.pending is None or self.pending.get("content") != content:
            self.pending = {
                "content": content,
                "body": {
                    "request_id": new_identity(),
                    "operation": "check",
                    "values": {**values, "checked_at": utc_now()},
                },
            }
        self.check_requested.emit(self.pending["body"])
