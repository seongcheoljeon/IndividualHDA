"""Small management views; persistence and remote IO belong to gateway workers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs.history_activity import rename_names, video_action
from libs.library_management import ManagementGateway
from libs.resource_policy import CallbackPolicy
from libs.task_controller import TaskController


class LibraryMetadataDialog(QtWidgets.QDialog):
    changed = QtCore.Signal()

    def __init__(
        self,
        gateway: ManagementGateway,
        parent: QtWidgets.QWidget,
        *,
        asset_id: int | None = None,
        writable: bool = True,
        owner: bool = True,
        callbacks: CallbackPolicy = CallbackPolicy(),
    ) -> None:
        super().__init__(parent)
        self.gateway, self.asset_id, self.writable = gateway, asset_id, writable
        self.callbacks = callbacks
        self.setWindowTitle("Trash" if asset_id is None else "Version details")
        self.resize(720, 480)
        self._tasks = TaskController(self)
        self._tasks.result.connect(self._finished)
        self._callback: Callable[[Any], None] | None = None
        self._closing = False
        self._reload_pending = False
        self._tasks.idle.connect(self._idle)
        self._items: list[dict[str, Any]] = []
        layout = QtWidgets.QVBoxLayout(self)
        self.label__status = QtWidgets.QLabel()
        self.tableWidget__items = QtWidgets.QTableWidget(0, 3)
        self.tableWidget__items.setHorizontalHeaderLabels(
            ["Asset", "Version", "Deleted"]
        )
        self.tableWidget__items.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tableWidget__items.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tableWidget__items.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tableWidget__items.horizontalHeader().setStretchLastSection(True)
        self.comboBox__version = QtWidgets.QComboBox()
        self.textEdit__description = QtWidgets.QPlainTextEdit()
        self.textEdit__description.setPlaceholderText(
            "Describe the changes in this version (optional)"
        )
        self.tableWidget__dependencies = QtWidgets.QTableWidget(0, 4)
        self.tableWidget__dependencies.setHorizontalHeaderLabels(
            ["Kind", "Target", "Version", "Required"]
        )
        self.tableWidget__dependencies.horizontalHeader().setStretchLastSection(True)
        self.textEdit__activity = QtWidgets.QPlainTextEdit()
        self.textEdit__activity.setReadOnly(True)
        self.tabWidget__details = QtWidgets.QTabWidget()
        self.tabWidget__details.addTab(self.textEdit__description, "Change description")
        dependency_page = QtWidgets.QWidget()
        dependencies_layout = QtWidgets.QVBoxLayout(dependency_page)
        dependencies_layout.addWidget(
            QtWidgets.QLabel(
                "Unrecorded dependencies and compatibility remain unverified."
            )
        )
        dependencies_layout.addWidget(self.tableWidget__dependencies)
        self.pushButton__add_dependency = QtWidgets.QPushButton("Add dependency")
        self.pushButton__add_dependency.clicked.connect(lambda: self._dependency({}))
        self.pushButton__remove_dependency = QtWidgets.QPushButton(
            "Remove selected dependency"
        )
        self.pushButton__remove_dependency.clicked.connect(
            lambda: self.tableWidget__dependencies.removeRow(
                self.tableWidget__dependencies.currentRow()
            )
        )
        dependencies_layout.addWidget(self.pushButton__add_dependency)
        dependencies_layout.addWidget(self.pushButton__remove_dependency)
        self.tabWidget__details.addTab(dependency_page, "Dependencies")
        self.tabWidget__details.addTab(self.textEdit__activity, "Activity and files")
        layout.addWidget(self.tableWidget__items)
        layout.addWidget(self.comboBox__version)
        from widgets.library_metadata.tracking import TrackingDetails

        self._tracking = TrackingDetails(writable, self)
        self._tracking_index = self.tabWidget__details.addTab(
            self._tracking, "Verification and usage"
        )
        self._tracking.check_requested.connect(self._record_check)
        self._tracking.page_requested.connect(self._tracking_page)
        self._asset_uuid = ""
        layout.addWidget(self.tabWidget__details)
        buttons = QtWidgets.QHBoxLayout()
        self.pushButton__restore = QtWidgets.QPushButton("Restore")
        self.pushButton__purge = QtWidgets.QPushButton("Delete permanently…")
        self.pushButton__save = QtWidgets.QPushButton("Save")
        self.pushButton__refresh = QtWidgets.QPushButton("Refresh")
        self.pushButton__check_files = QtWidgets.QPushButton("Check files")
        check_files = getattr(gateway, "inspect", None)
        self.pushButton__check_files.setVisible(
            asset_id is not None and check_files is not None
        )
        if check_files is not None:
            self.pushButton__check_files.clicked.connect(
                lambda: self._run(check_files, self._saved)
            )
        for button in (
            self.pushButton__restore,
            self.pushButton__purge,
            self.pushButton__save,
            self.pushButton__refresh,
            self.pushButton__check_files,
        ):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(self.label__status)
        self.pushButton__restore.clicked.connect(lambda: self._change("restore"))
        self.pushButton__purge.clicked.connect(lambda: self._change("purge"))
        self.pushButton__save.clicked.connect(self._save)
        self.pushButton__refresh.clicked.connect(self.reload)
        self.comboBox__version.currentIndexChanged.connect(self._version)
        trash = asset_id is None
        self.tableWidget__items.setVisible(trash)
        self.comboBox__version.setVisible(not trash)
        self.tabWidget__details.setVisible(not trash)
        self.pushButton__restore.setVisible(trash and writable)
        self.pushButton__purge.setVisible(trash and owner)
        self.pushButton__save.setVisible(not trash and writable)
        self.textEdit__description.setReadOnly(not writable)
        self.tableWidget__dependencies.setEnabled(writable)
        self.pushButton__add_dependency.setEnabled(writable)
        self.pushButton__remove_dependency.setEnabled(writable)
        self.reload()

    def _run(
        self, operation: Callable[[], Any], callback: Callable[[Any], None]
    ) -> None:
        if self._tasks.busy or self._closing:
            return
        self._callback = callback
        self.setEnabled(False)
        self.label__status.setText("Working…")
        self._tasks.start(operation, lambda _: None)

    def _finished(self, result: Any, error: Exception | None) -> None:
        self.setEnabled(True)
        callback, self._callback = self._callback, None
        if self._closing:
            self.reject()
            return
        self.label__status.setText(str(error) if error else "")
        if error is None and callback:
            callback(result)

    def reload(self) -> None:
        asset_id = self.asset_id
        self._run(
            self.gateway.trash
            if asset_id is None
            else lambda: self.gateway.details(asset_id),
            self._loaded,
        )

    def _loaded(self, result: Any) -> None:
        if self.asset_id is None:
            self._items = result
            self.tableWidget__items.setRowCount(len(result))
            for row, item in enumerate(result):
                for col, value in enumerate(
                    (item["name"], item.get("version", "All"), item["deleted_at"])
                ):
                    self.tableWidget__items.setItem(
                        row, col, QtWidgets.QTableWidgetItem(str(value))
                    )
        else:
            self._items = result["versions"]
            self._asset_uuid = result.get("asset_uuid", "")
            tracking = result.get("tracking")
            self.tabWidget__details.setTabVisible(
                self._tracking_index, tracking is not None
            )
            for kind, rows in (tracking or {}).items():
                self._tracking.show_page(kind, rows)
            self.comboBox__version.blockSignals(True)
            self.comboBox__version.clear()
            self.comboBox__version.addItems([item["version"] for item in self._items])
            self.comboBox__version.blockSignals(False)
            self._version(0)
            self.textEdit__activity.setPlainText(
                "\n".join(self._activity(item) for item in result["events"])
                + "\n\n"
                + "\n".join(
                    f"{item['version']} · {item['filename']} · {item['status']}"
                    for item in result["files"]
                )
            )

    @staticmethod
    def _activity(item: dict[str, Any]) -> str:
        from uuid import UUID

        actor = item.get("actor_name") or item.get("actor") or "Unknown"
        try:
            UUID(actor)
            actor = "Former member"
        except ValueError:
            pass
        operation = item["operation"]
        labels = {
            "create": "Registered",
            "version": "Version added",
            "rename": "Renamed",
            "metadata": "Notes or tags changed",
            "media": "Preview changed",
            "media_snapshot": "Version preview changed",
            "version_details": "Version details changed",
            "version_details_snapshot": "Version details changed",
            "delete": "Moved to Trash",
            "restore": "Restored",
            "purge": "Permanently deleted",
            "delete_history": "Version moved to Trash",
            "restore_history": "Version restored",
            "purge_history": "Version permanently deleted",
        }
        names = rename_names(item)
        video = video_action(item)
        if names is not None:
            title = f'Renamed "{names[0]}" → "{names[1]}"'
        elif video is not None:
            title = "Video attached" if video == "insert" else "Video replaced"
        elif "." in operation:
            table, action = operation.split(".", 1)
            label = {
                "hda_key": "Name or category",
                "hda_info": "Asset",
                "note_info": "Note",
                "tag_info": "Tags",
                "hda_history": "Version",
                "video_info": "Video",
                "thumbnail_info": "Thumbnail",
            }.get(table, "Details")
            title = label + (" added" if action == "insert" else " changed")
        else:
            title = labels.get(operation, "Changed")
        return f"{item['occurred_at']} · {actor} · {title}"

    def _version(self, index: int) -> None:
        self.tableWidget__dependencies.setRowCount(0)
        item = self._items[index] if 0 <= index < len(self._items) else {}
        self._tracking.select_version(
            item.get("version_uuid") or item.get("document", {}).get("version_uuid")
        )
        self.textEdit__description.clear()
        if 0 <= index < len(self._items):
            document = self._items[index]["document"]
            self.textEdit__description.setPlainText(document.get("description", ""))
            for dependency in document.get("dependencies", []):
                self._dependency(dependency)

    def _dependency(self, dependency: dict[str, Any]) -> None:
        row = self.tableWidget__dependencies.rowCount()
        self.tableWidget__dependencies.insertRow(row)
        kind = QtWidgets.QComboBox()
        kind.addItems(["asset", "plugin", "file", "package"])
        kind.setCurrentText(dependency.get("kind", "file"))
        self.tableWidget__dependencies.setCellWidget(row, 0, kind)
        for column, key in ((1, "target"), (2, "version")):
            self.tableWidget__dependencies.setItem(
                row, column, QtWidgets.QTableWidgetItem(dependency.get(key, ""))
            )
        required = QtWidgets.QCheckBox()
        required.setChecked(dependency.get("required", True))
        self.tableWidget__dependencies.setCellWidget(row, 3, required)

    def _save(self) -> None:
        index = self.comboBox__version.currentIndex()
        if (
            not self.writable
            or self.asset_id is None
            or not 0 <= index < len(self._items)
        ):
            return
        dependencies = []
        for row in range(self.tableWidget__dependencies.rowCount()):
            kind = self.tableWidget__dependencies.cellWidget(row, 0)
            required = self.tableWidget__dependencies.cellWidget(row, 3)
            assert isinstance(kind, QtWidgets.QComboBox) and isinstance(
                required, QtWidgets.QCheckBox
            )
            dependencies.append(
                {
                    "kind": kind.currentText(),
                    "target": (
                        self.tableWidget__dependencies.item(row, 1)
                        or QtWidgets.QTableWidgetItem()
                    ).text(),
                    "version": (
                        self.tableWidget__dependencies.item(row, 2)
                        or QtWidgets.QTableWidgetItem()
                    ).text(),
                    "required": required.isChecked(),
                    "source": "manual",
                }
            )
        values = {
            "description": self.textEdit__description.toPlainText(),
            "dependencies": dependencies,
            "dependency_status": (
                "recorded"
                if dependencies
                else self._items[index]["document"].get("dependency_status", "unknown")
            ),
        }
        asset_id, version = self.asset_id, self._items[index]
        self._run(
            lambda: self.gateway.save_details(asset_id, version, values), self._saved
        )

    def _change(self, operation: str) -> None:
        row = self.tableWidget__items.currentRow()
        if not 0 <= row < len(self._items):
            return
        item = self._items[row]
        if operation != "purge":
            self._run(lambda: self.gateway.change(item, operation), self._saved)
            return
        from widgets.library_metadata.dependency_warning import dependency_message

        def confirm(rows: list[dict[str, Any]]) -> None:
            def apply() -> None:
                if self._closing:
                    return
                if self._tasks.busy:
                    QtCore.QTimer.singleShot(self.callbacks.retry_delay_ms, apply)
                    return
                if (
                    QtWidgets.QMessageBox.question(
                        self,
                        "Delete permanently",
                        f"Permanently delete {item['name']} ({item.get('version', 'all versions')})? This cannot be restored from Trash."
                        + dependency_message(rows),
                    )
                    == QtWidgets.QMessageBox.StandardButton.Yes
                ):
                    self._run(
                        lambda: self.gateway.change(item, operation), self._purged
                    )

            QtCore.QTimer.singleShot(0, apply)

        self._run(lambda: self.gateway.dependents(item), confirm)

    def _saved(self, result: Any) -> None:
        self.changed.emit()
        self._reload_pending = True

    def _purged(self, result: Any) -> None:
        self._saved(result)
        self._when_idle(
            lambda: self._run(lambda: self.gateway.reclaim(False), self._offer_reclaim)
        )

    def _when_idle(self, action: Callable[[], None]) -> None:
        # A result can arrive before the worker clears busy; wait, do not drop it.
        if self._closing:
            return
        if self._tasks.busy:
            QtCore.QTimer.singleShot(
                self.callbacks.retry_delay_ms, lambda: self._when_idle(action)
            )
            return
        action()

    def _offer_reclaim(self, rows: list[dict[str, Any]]) -> None:
        """Purge only dropped rows; ask before the queued files leave the disk."""
        candidates = [row for row in rows if row["status"] == "candidate"]
        if self._closing or not candidates:
            return
        kept = len(rows) - len(candidates)
        megabytes = sum(row.get("bytes", 0) for row in candidates) / 1_000_000
        message = (
            f"Delete {len(candidates)} file(s) ({megabytes:.1f} MB) that no version "
            "references anymore?"
        )
        if kept:
            message += (
                f"\n{kept} file(s) stay: still referenced or outside the library."
            )
        if (
            QtWidgets.QMessageBox.question(self, "Free disk space", message)
            == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self._run(lambda: self.gateway.reclaim(True), lambda rows: None)

    def _idle(self) -> None:
        if self._closing:
            super().done(QtWidgets.QDialog.DialogCode.Rejected)
        elif self._reload_pending:
            self._reload_pending = False
            self.reload()

    def shutdown(self) -> None:
        self._closing = True
        self._tasks.drain()

    def done(self, result: int) -> None:
        if self._tasks.busy:
            self._closing = True
            return
        super().done(result)

    def closeEvent(self, event: Any) -> None:
        if self._tasks.busy:
            self._closing = True
            event.ignore()
            return
        self._tasks.drain()
        super().closeEvent(event)

    def _record_check(self, body: dict[str, Any]) -> None:
        asset_id = self.asset_id
        if asset_id is None:
            return

        def recorded(result: Any) -> None:
            self._tracking.pending = None
            self._saved(result)

        self._run(lambda: self.gateway.record_check(asset_id, body), recorded)

    def _tracking_page(self, kind: str, offset: int) -> None:
        self._run(
            lambda: self.gateway.tracking_read(kind, self._asset_uuid, offset),
            lambda rows: self._tracking.show_page(kind, rows, True),
        )
