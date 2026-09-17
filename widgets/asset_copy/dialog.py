"""Small modal copy workflow; hashing, database and HTTP work run off the GUI thread."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from threading import Event
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs.runtime_settings import RuntimeSettings
from libs.task_controller import TaskController
from libs.team.client import HttpCatalog
from libs.team.contracts import Command
from libs.team.copy_source import CopySource
from widgets.asset_copy.presenter import CopyPresenter
from widgets.library_connection.dialog import ConnectionDialog


class CopyAssetDialog(QtWidgets.QDialog):
    progress = QtCore.Signal(str)

    def __init__(
        self,
        source: CopySource,
        config_root: Path,
        parent: QtWidgets.QWidget | None = None,
        *,
        runtime: RuntimeSettings = RuntimeSettings(),
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Copy to team")
        self.resize(640, 440)
        self._root = config_root
        self.runtime = runtime
        self._presenter = CopyPresenter(source, config_root)
        self._tasks = TaskController(self)
        self._tasks.result.connect(self._result)
        self._tasks.idle.connect(self._idle)
        self._cancel = Event()
        self._closing = False
        self._catalog: HttpCatalog | None = None
        self._prepared: dict[str, Any] | None = None
        self._connection: ConnectionDialog | None = None
        self._build_layout()
        self.progress.connect(self.label__copy_status.setText)

    def _build_layout(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        destination = QtWidgets.QHBoxLayout()
        self.label__destination = QtWidgets.QLabel("Choose a team project")
        self.label__destination.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.pushButton__choose_project = QtWidgets.QPushButton("Choose project…")
        destination.addWidget(self.label__destination, 1)
        destination.addWidget(self.pushButton__choose_project)
        layout.addLayout(destination)
        form = QtWidgets.QFormLayout()
        self.lineEdit__asset_name = QtWidgets.QLineEdit()
        self.lineEdit__asset_name.setPlaceholderText("Keep the personal asset name")
        form.addRow("Team asset name", self.lineEdit__asset_name)
        layout.addLayout(form)
        options = QtWidgets.QHBoxLayout()
        self.checkBox__all_versions = QtWidgets.QCheckBox("Include previous versions")
        self.checkBox__previews = QtWidgets.QCheckBox("Include thumbnails and videos")
        for checkbox in (self.checkBox__all_versions, self.checkBox__previews):
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._invalidate)
            options.addWidget(checkbox)
        layout.addLayout(options)
        self.tableWidget__versions = QtWidgets.QTableWidget(0, 4)
        self.tableWidget__versions.setHorizontalHeaderLabels(
            ["Personal version", "Team version", "Files", "Size"]
        )
        self.tableWidget__versions.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.tableWidget__versions)
        self.label__copy_status = QtWidgets.QLabel(
            "Preview the versions and files before copying. Your personal originals stay in place."
        )
        self.label__copy_status.setWordWrap(True)
        self.label__copy_status.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.label__copy_status)
        buttons = QtWidgets.QHBoxLayout()
        self.pushButton__preview = QtWidgets.QPushButton("Preview")
        self.pushButton__copy = QtWidgets.QPushButton("Copy")
        self.pushButton__change_selection = QtWidgets.QPushButton("Change selection")
        buttons.addWidget(self.pushButton__change_selection)
        self.pushButton__change_selection.setAutoDefault(False)
        self.pushButton__change_selection.clicked.connect(self._change_selection)
        self.pushButton__close = QtWidgets.QPushButton("Close")
        buttons.addStretch()
        for button in (
            self.pushButton__preview,
            self.pushButton__copy,
            self.pushButton__close,
        ):
            button.setAutoDefault(False)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        # Match the maintained Python UI naming style for inspection and later edits.
        for name, widget in vars(self).items():
            if "__" in name and isinstance(widget, QtWidgets.QWidget):
                widget.setObjectName(name)
        self.pushButton__choose_project.clicked.connect(self._choose_project)
        self.pushButton__preview.clicked.connect(self._preview)
        self.pushButton__copy.clicked.connect(self._copy)
        self.pushButton__close.clicked.connect(self.reject)
        self.lineEdit__asset_name.textEdited.connect(self._invalidate)
        self._idle()

    def _choose_project(self) -> None:
        dialog = ConnectionDialog(self._root, self, runtime=self.runtime)
        self._connection = dialog
        dialog.setWindowTitle("Choose copy destination")
        dialog.pushButton__open_library.setText("Use project")
        dialog.connected.connect(self._connected)
        try:
            dialog.exec()
        finally:
            dialog.shutdown()
            self._connection = None
            dialog.deleteLater()

    def _connected(self, catalog: HttpCatalog, project: dict[str, Any]) -> None:
        self._catalog = catalog
        self.label__destination.setText(project["name"])
        self._invalidate()

    def _invalidate(self, *args: Any) -> None:
        self._prepared = None
        self.tableWidget__versions.setRowCount(0)
        self.label__copy_status.setText(
            "Preview the destination and files before copying."
        )
        self._idle()

    def _preview(self) -> None:
        if self._catalog is None or self._tasks.busy:
            return
        catalog, name = self._catalog, self.lineEdit__asset_name.text().strip()
        all_versions, previews = (
            self.checkBox__all_versions.isChecked(),
            self.checkBox__previews.isChecked(),
        )
        self._cancel.clear()
        self.label__copy_status.setText("Reading versions and checking files…")
        self._tasks.start(
            lambda: self._presenter.prepare(
                catalog, name, all_versions, previews, self._cancel
            ),
            self._show_preview,
        )
        self._idle()

    def _show_preview(self, prepared: dict[str, Any]) -> None:
        self._prepared = prepared
        plan = prepared["plan"]
        for widget, key in (
            (self.checkBox__all_versions, "all_versions"),
            (self.checkBox__previews, "previews"),
        ):
            with QtCore.QSignalBlocker(widget):
                widget.setChecked(plan["options"][key])
        self.lineEdit__asset_name.setText(plan["values"]["name"])
        versions = plan["values"]["versions"]
        self.tableWidget__versions.setRowCount(len(versions))
        blobs = {}
        for row, version in enumerate(versions):
            files = version["values"]["files"]
            blobs.update({blob["digest"]: blob for blob in files.values()})
            columns = [
                version["origin"]["version"]
                + (" (current)" if row == len(versions) - 1 else ""),
                version["values"]["version"],
                ", ".join(files),
                f"{sum(blob['size'] for blob in files.values()) / 1024:.1f} KiB",
            ]
            for column, text in enumerate(columns):
                item = QtWidgets.QTableWidgetItem(text)
                if column != 1 or prepared["frozen"]:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidget__versions.setItem(row, column, item)
        total = sum(blob["size"] for blob in blobs.values())
        summary = f"{len(versions)} versions · {len(blobs)} unique files · {total / 1024**2:.2f} MiB"
        if prepared["result"]:
            summary += "\nAlready copied to this project."
        elif prepared["frozen"]:
            summary += (
                "\nAn unfinished copy was found. Resume uses the saved selection."
            )
        warnings = plan["warnings"]
        visible_warnings = warnings[:3]
        if len(warnings) > 3:
            visible_warnings = [
                *visible_warnings,
                f"{len(warnings) - 3} more notices (hover to read).",
            ]
        self.label__copy_status.setToolTip("\n".join(warnings))
        self.label__copy_status.setText("\n".join([summary, *visible_warnings]))

    def _copy(self) -> None:
        prepared = self._prepared
        if prepared is None or self._tasks.busy:
            return
        plan = deepcopy(prepared["plan"])
        if not prepared["frozen"]:
            for row, version in enumerate(plan["values"]["versions"]):
                item = self.tableWidget__versions.item(row, 1)
                assert item is not None
                version["values"]["version"] = item.text().strip()
        try:
            Command("copy_asset", values=plan["values"]).validate()
        except Exception as error:
            self.label__copy_status.setText(str(error))
            return
        prepared.update(plan=plan, frozen=True)
        self._cancel.clear()
        self._tasks.start(
            lambda: prepared["transfer"].run(plan, self._cancel, self.progress.emit),
            self._copied,
        )
        self._idle()

    def _change_selection(self) -> None:
        if self._prepared is None or self._tasks.busy:
            return
        store = self._prepared["transfer"].store
        self._tasks.start(store.discard_unsubmitted, lambda _: self._invalidate())
        self._idle()

    def _copied(self, result: dict[str, Any]) -> None:
        if self._prepared is not None:
            self._prepared["result"] = result
        self.label__copy_status.setText(
            f"Copied {result['name']} to the team project. Your personal originals are preserved."
        )

    def _result(self, value: Any, error: Any) -> None:
        if error is not None:
            self.label__copy_status.setText(str(error))

    def _idle(self) -> None:
        busy = self._tasks.busy
        frozen = bool(self._prepared and self._prepared["frozen"])
        complete = bool(self._prepared and self._prepared["result"])
        for widget in (
            self.lineEdit__asset_name,
            self.checkBox__all_versions,
            self.checkBox__previews,
        ):
            widget.setEnabled(not busy and not frozen)
        self.pushButton__change_selection.setVisible(frozen and not complete)
        self.pushButton__change_selection.setEnabled(not busy)
        self.tableWidget__versions.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
            if frozen
            else QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.tableWidget__versions.setEnabled(not busy)
        self.pushButton__choose_project.setEnabled(not busy)
        self.pushButton__preview.setEnabled(not busy and self._catalog is not None)
        self.pushButton__copy.setEnabled(
            not busy and self._prepared is not None and not complete
        )
        self.pushButton__copy.setText("Resume" if frozen and not complete else "Copy")
        self.pushButton__close.setText("Cancel" if busy else "Close")
        if self._closing and not busy:
            super().reject()

    def reject(self) -> None:
        self._closing = True
        self._cancel.set()
        if not self._tasks.busy:
            super().reject()
        else:
            self.label__copy_status.setText(
                "Stopping after the current transfer finishes…"
            )

    def closeEvent(self, event: Any) -> None:
        self.reject()
        if self._tasks.busy:
            event.ignore()
        else:
            event.accept()

    def shutdown(self) -> None:
        self._closing = True
        self._cancel.set()
        if self._connection is not None:
            self._connection.shutdown()
        self._tasks.drain()
        super().reject()
