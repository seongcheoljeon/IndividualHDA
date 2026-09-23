"""Library management UI. IO runs in owned workers; HOM remains on the GUI thread."""

from __future__ import annotations

import tempfile
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs.archive_transfer import ArchiveTransfer
from libs.library_backups import (
    cleanup_recovery,
    create_backup,
    list_backups,
    recovery_files,
    validate_backup,
)
from libs.library_explorer import history_versions, search_assets
from libs.library_maintenance import apply_paths, inspect_library, plan_paths
from libs.runtime_settings import RuntimeSettings
from libs.task_controller import TaskController
from libs.version_compare import compare_expanded, expand_asset
from widgets.empty_state import attach_empty_state
from widgets.library_manager.presenter import LibraryManagerPresenter
from widgets.tables import configure_table


class LibraryManager(QtWidgets.QDialog):
    restoreReady = QtCore.Signal(object)
    pathsChanged = QtCore.Signal()
    importVersion = QtCore.Signal(object)
    assetSelected = QtCore.Signal(int)

    def __init__(
        self,
        database: Path,
        assets: Path,
        user: str,
        asset_id: int | None = None,
        parent: QtWidgets.QWidget | None = None,
        *,
        runtime: RuntimeSettings = RuntimeSettings(),
    ) -> None:
        super().__init__(parent)
        self.database, self.assets, self.user = database, assets, user
        self.runtime = runtime
        self.setWindowTitle("Library Manager")
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.resize(1050, 680)
        self.tasks = TaskController(self)
        self.tasks.result.connect(self._result)
        self.tasks.idle.connect(self._idle)
        self.cancel = threading.Event()
        self._closing = False
        self._destroying = False
        self._pending_search = False
        self._presenter = LibraryManagerPresenter(page_size=runtime.explorer_page_size)
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)
        self.status = QtWidgets.QLabel(
            "Choose an operation. Existing library files are not changed by scans."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QtWidgets.QHBoxLayout()
        self.cancel_button = QtWidgets.QPushButton("Cancel task")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_task)
        row.addWidget(self.cancel_button)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.close)
        row.addWidget(close)
        layout.addLayout(row)
        self._health_tab()
        self._backups_tab()
        self._paths_tab()
        self._versions_tab(asset_id)
        self._explorer_tab()
        self._recovery_tab()

    def _page(self, title: str) -> tuple[QtWidgets.QWidget, QtWidgets.QVBoxLayout]:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        self.tabs.addTab(page, title)
        return page, layout

    @staticmethod
    def _button(
        layout: QtWidgets.QLayout, text: str, callback: Callable[[], None]
    ) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    @staticmethod
    def _table(
        layout: QtWidgets.QLayout,
        columns: list[str],
        empty: tuple[str, str] | None = None,
    ) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        configure_table(table, single_selection=False)
        if empty is not None:
            attach_empty_state(table).set_content(*empty)
        layout.addWidget(table)
        return table

    @staticmethod
    def _rows(
        table: QtWidgets.QTableWidget,
        rows: list[tuple[list[Any], Any]],
        checked: Callable[[Any], bool] | None = None,
        append: bool = False,
    ) -> None:
        if not append:
            table.setRowCount(0)
        for values, data in rows:
            row = table.rowCount()
            table.insertRow(row)
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, data)
                    if checked is not None:
                        item.setFlags(
                            item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                        )
                        item.setCheckState(
                            QtCore.Qt.CheckState.Checked
                            if checked(data)
                            else QtCore.Qt.CheckState.Unchecked
                        )
                table.setItem(row, column, item)
        if not append:
            table.resizeColumnsToContents()

    @staticmethod
    def _selected(table: QtWidgets.QTableWidget) -> Any:
        row = table.currentRow()
        if row < 0:
            raise ValueError("Select a row first")
        item = table.item(row, 0)
        if item is None:
            raise ValueError("Select a populated row")
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    @staticmethod
    def _checked(table: QtWidgets.QTableWidget) -> list[Any]:
        result = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.checkState() == QtCore.Qt.CheckState.Checked:
                result.append(item.data(QtCore.Qt.ItemDataRole.UserRole))
        return result

    def _guard(self, operation: Callable[[], None]) -> None:
        try:
            operation()
        except Exception as error:
            self.status.setText(str(error))

    def _run(
        self,
        operation: Callable[[threading.Event], Any],
        completion: Callable[[Any], None],
        cancellable: bool = True,
    ) -> None:
        if self.tasks.busy:
            raise RuntimeError("Wait for the current operation to finish")
        self.cancel = threading.Event()
        token = self.cancel
        self.tabs.setEnabled(False)
        self.cancel_button.setEnabled(cancellable)
        self.status.setText("Working…")
        try:
            self.tasks.start(lambda: operation(token), completion)
        except Exception:
            self.tabs.setEnabled(True)
            self.cancel_button.setEnabled(False)
            raise

    def _result(self, value: Any, error: Exception | None) -> None:
        if error is not None:
            self.status.setText(str(error))
        else:
            self.status.setText("Completed")

    def _idle(self) -> None:
        self.tabs.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
        if self._closing:
            self.accept()
        elif self._pending_search:
            self._pending_search = False
            QtCore.QTimer.singleShot(0, self._search)

    def cancel_task(self) -> None:
        self.cancel.set()
        self._presenter.invalidate()
        self.status.setText("Cancellation requested…")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.tasks.busy:
            self._closing = True
            self.cancel.set()
            event.ignore()
        else:
            self._closing = True
            self.search_timer.stop()
            super().closeEvent(event)

    def reject(self) -> None:
        if self.tasks.busy:
            self._closing = True
            self.cancel.set()
        else:
            self._closing = True
            self.search_timer.stop()
            super().reject()

    def shutdown(self) -> None:
        self._destroying = True
        self._closing = True
        self.cancel.set()
        self.tasks.drain()
        self.close()

    def _confirm(self, message: str) -> bool:
        return (
            QtWidgets.QMessageBox.question(
                self,
                "Library Manager",
                message,
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        )

    def _health_tab(self) -> None:
        _, layout = self._page("Health")
        self._button(
            layout,
            "Scan library",
            lambda: self._guard(
                lambda: self._run(
                    lambda token: inspect_library(self.database, token),
                    self._health_ready,
                )
            ),
        )
        self.health = self._table(
            layout,
            ["Severity", "Location", "Details"],
            ("Nothing to report", "Run a check to see what it finds."),
        )
        self._button(
            layout,
            "Export report…",
            lambda: self._guard(lambda: self._export_table(self.health)),
        )

    def _health_ready(self, issues: list[Any]) -> None:
        self._rows(
            self.health, [([i.severity, i.location, i.message], i) for i in issues]
        )
        self.status.setText(
            f"{len(issues)} issues. Source HIP paths may belong to another workstation."
            if issues
            else "No integrity or missing-file issues found."
        )

    def _export_table(self, table: QtWidgets.QTableWidget) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save report", "", "Text (*.txt)"
        )
        if filename:
            Path(filename).write_text(
                "\n".join(
                    "\t".join(
                        (item.text() if (item := table.item(r, c)) is not None else "")
                        for c in range(table.columnCount())
                    )
                    for r in range(table.rowCount())
                ),
                encoding="utf-8",
            )

    def _backups_tab(self) -> None:
        _, layout = self._page("Backups")
        self._button(
            layout,
            "Refresh backups",
            lambda: self._guard(
                lambda: self._run(
                    lambda token: list_backups(self.database.parent),
                    self._backups_ready,
                )
            ),
        )
        self.reason = QtWidgets.QLineEdit("Manual backup")
        layout.addWidget(self.reason)
        self._button(layout, "Create full backup", lambda: self._guard(self._backup))
        self.backups = self._table(
            layout,
            ["File", "Created / modified", "MiB", "Reason", "Restore"],
            ("No backups yet", "Create one before a risky change."),
        )
        self._button(
            layout, "Validate selected backup", lambda: self._guard(self._validate)
        )
        self._button(
            layout, "Restore selected backup…", lambda: self._guard(self._restore)
        )

    def _backups_ready(self, entries: list[Any]) -> None:
        self._rows(
            self.backups,
            [
                (
                    [
                        e.path.name,
                        datetime.fromtimestamp(e.modified).isoformat(
                            timespec="seconds"
                        ),
                        f"{e.size / 1024**2:.2f}",
                        e.reason,
                        "Full library" if e.restorable else "Manual only",
                    ],
                    e,
                )
                for e in entries
            ],
        )

    def _backup(self) -> None:
        reason = self.reason.text().strip() or "Manual backup"
        self._run(
            lambda token: create_backup(self.database, self.assets, reason),
            lambda path: self.status.setText(f"Backup created: {path}"),
            False,
        )

    def _validate(self) -> None:
        entry = self._selected(self.backups)
        if not entry.restorable:
            raise ValueError(
                "This is not a full-library backup. Use it only for manual recovery with matching asset files."
            )
        self._run(lambda token: validate_backup(entry.path, token), self.status.setText)

    def _restore(self) -> None:
        entry = self._selected(self.backups)
        if not entry.restorable:
            raise ValueError("Select a full-library backup")
        if not self._confirm(
            f"Restore {entry.path.name}?\nThe archive will be validated and the current library backed up first.\nThe panel will close to activate the restored library; reopen it afterward."
        ):
            return
        stream = ArchiveTransfer(self.assets, self.database.parent)

        def restore(token: threading.Event) -> Path:
            validate_backup(entry.path, token)
            return stream.import_ihda_data(entry.path)

        def ready(backup: Path) -> None:
            self.restoreReady.emit(stream)
            self.status.setText(
                f"Current library saved at {backup}. Closing to activate restore."
            )
            self._closing = True

        self._run(restore, ready, False)

    def _paths_tab(self) -> None:
        _, layout = self._page("Repair paths")
        layout.addWidget(
            QtWidgets.QLabel(
                "Replace a stored root after moving library files. Preview first; only checked rows are changed."
            )
        )
        self.old_root = QtWidgets.QLineEdit()
        self.old_root.setPlaceholderText(
            "Old root, for example C:/Library or /old/library"
        )
        self.new_root = QtWidgets.QLineEdit(str(self.assets))
        layout.addWidget(self.old_root)
        layout.addWidget(self.new_root)
        self._button(layout, "Choose new root…", self._choose_root)
        self._button(
            layout, "Preview changes", lambda: self._guard(self._preview_paths)
        )
        self.paths = self._table(
            layout,
            ["Field / row", "Old directory", "New directory", "File exists"],
            ("No changes to apply", "Choose the library's new location to preview."),
        )
        self._button(
            layout, "Apply checked changes…", lambda: self._guard(self._apply_paths)
        )

    def _choose_root(self) -> None:
        root = QtWidgets.QFileDialog.getExistingDirectory(
            self, "New root", self.new_root.text()
        )
        if root:
            self.new_root.setText(root)

    def _preview_paths(self) -> None:
        old, new = self.old_root.text().strip(), Path(self.new_root.text().strip())
        self._run(
            lambda token: plan_paths(self.database, old, new, token),
            lambda changes: self._rows(
                self.paths,
                [
                    (
                        [
                            f"{c.table}.{c.column}:{c.row_id}",
                            c.before,
                            c.after,
                            c.exists,
                        ],
                        c,
                    )
                    for c in changes
                ],
                lambda c: c.exists,
            ),
        )

    def _apply_paths(self) -> None:
        changes = self._checked(self.paths)
        if not changes:
            raise ValueError("Check at least one preview row")
        if self._confirm(
            f"Update {len(changes)} stored paths?\nA database backup will be created first. Files are not moved.\nThe panel will close; reopen it to refresh the library."
        ):

            def ready(backup: Path) -> None:
                self.pathsChanged.emit()
                self.status.setText(f"Paths updated. Backup: {backup}")
                self._closing = True

            self._run(lambda token: apply_paths(self.database, changes), ready, False)

    def _versions_tab(self, asset_id: int | None) -> None:
        _, layout = self._page("Versions")
        self.asset_id = QtWidgets.QLineEdit(
            str(asset_id) if asset_id is not None else ""
        )
        self.asset_id.setPlaceholderText("Asset ID — or choose an asset in Explorer")
        layout.addWidget(self.asset_id)
        self._button(layout, "Load versions", lambda: self._guard(self._versions))
        self.left = QtWidgets.QComboBox()
        self.right = QtWidgets.QComboBox()
        layout.addWidget(self.left)
        layout.addWidget(self.right)
        self._button(layout, "Compare versions", lambda: self._guard(self._compare))
        self.diff = QtWidgets.QPlainTextEdit()
        self.diff.setReadOnly(True)
        layout.addWidget(self.diff)
        self._button(layout, "Save comparison…", lambda: self._guard(self._save_diff))
        self._button(
            layout,
            "Import right version into current network",
            lambda: self._guard(self._import_version),
        )

    def _versions(self) -> None:
        identifier = int(self.asset_id.text())

        def ready(rows: list[dict[str, Any]]) -> None:
            for combo in (self.left, self.right):
                combo.clear()
                for row in rows:
                    combo.addItem(
                        f"#{row['id']} · {row['version']} · {row['registration_datetime']} · {row['comment']}",
                        row,
                    )
            if len(rows) > 1:
                self.left.setCurrentIndex(1)
            self.status.setText(f"{len(rows)} history snapshots")

        self._run(
            lambda token: history_versions(self.database, identifier, token), ready
        )

    def _compare(self) -> None:
        left, right = self.left.currentData(), self.right.currentData()
        if left is None or right is None:
            raise ValueError("Load and select two history snapshots")
        self._temporary = tempfile.TemporaryDirectory(prefix="ihda-compare-")
        root = Path(self._temporary.name)
        try:
            # Documented SideFX calls inspect files without installing assets or creating nodes.
            a = expand_asset(
                Path(left["hda_dirpath"]) / left["hda_filename"], root / "left"
            )
            b = expand_asset(
                Path(right["hda_dirpath"]) / right["hda_filename"], root / "right"
            )
            self._run(
                lambda token: compare_expanded(
                    root / "left", root / "right", left, right, a, b
                ),
                self.diff.setPlainText,
                False,
            )
        except BaseException:
            self._temporary.cleanup()
            self._temporary = None
            raise

    def _save_diff(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save comparison", "", "Text (*.txt)"
        )
        if filename:
            Path(filename).write_text(self.diff.toPlainText(), encoding="utf-8")

    def _import_version(self) -> None:
        row = self.right.currentData()
        if row is None:
            raise ValueError("Select a version first")
        self.importVersion.emit(row)

    def _explorer_tab(self) -> None:
        _, layout = self._page("Explorer")
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search library (literal substring)")
        self.field = QtWidgets.QComboBox()
        self.field.addItems(["Name", "Tags", "Type"])
        layout.addWidget(self.search)
        layout.addWidget(self.field)
        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(self.runtime.explorer_delay_ms)
        self.search_timer.timeout.connect(self._search)
        self.search.textChanged.connect(self._queue_search)
        self.field.currentIndexChanged.connect(self._queue_search)
        self._button(layout, "Search / reload", self._queue_search)
        self.explorer = self._table(
            layout,
            ["ID", "Name", "Category", "Version"],
            ("No results", "Search by name, category or version."),
        )
        self._button(
            layout,
            f"Load next {self.runtime.explorer_page_size}",
            lambda: self._guard(lambda: self._search(more=True)),
        )
        self._button(
            layout,
            "Compare selected asset versions",
            lambda: self._guard(self._explorer_versions),
        )
        self._button(
            layout,
            "Select asset in main panel",
            lambda: self._guard(self._select_asset),
        )

    def _queue_search(self, *_: Any) -> None:
        self._presenter.invalidate()
        self.cancel.set()
        self.search_timer.start()

    def _search(self, more: bool = False) -> None:
        if self._closing:
            return
        if self.tasks.busy:
            self._pending_search = True
            return
        request = self._presenter.request(more)
        offset = request.offset
        text, field = self.search.text(), self.field.currentText()

        def ready(rows: list[dict[str, Any]]) -> None:
            status = self._presenter.receive(request, len(rows))
            if status is None:
                return
            if not more:
                self.explorer.setRowCount(0)
            self._rows(
                self.explorer,
                [
                    ([row["id"], row["name"], row["category"], row["version"]], row)
                    for row in rows
                ],
                append=more,
            )
            self.status.setText(status)

        self._run(
            lambda token: search_assets(
                self.database,
                self.user,
                text,
                field,
                offset,
                limit=self.runtime.explorer_page_size,
                cancel=token,
            ),
            ready,
        )
        # Editing search remains possible to cancel/supersede the in-flight query.
        self.tabs.setEnabled(True)

    def _explorer_versions(self) -> None:
        row = self._selected(self.explorer)
        self.asset_id.setText(str(row["id"]))
        self.tabs.setCurrentIndex(3)
        self._versions()

    def _select_asset(self) -> None:
        self.assetSelected.emit(self._selected(self.explorer)["id"])

    def _recovery_tab(self) -> None:
        _, layout = self._page("Recovery files")
        self._button(
            layout,
            "Scan recovery files",
            lambda: self._guard(
                lambda: self._run(
                    lambda token: recovery_files(self.database, self.assets, token),
                    self._recovery_ready,
                )
            ),
        )
        self.recovery = self._table(
            layout,
            ["Path", "MiB", "Referenced"],
            ("No recovery files", "Interrupted operations would leave files here."),
        )
        self._button(
            layout,
            "Back up and remove checked files…",
            lambda: self._guard(self._cleanup),
        )

    def _recovery_ready(self, rows: list[Any]) -> None:
        self._rows(
            self.recovery,
            [([r.path, f"{r.size / 1024**2:.2f}", r.referenced], r) for r in rows],
            lambda r: False,
        )
        self.status.setText(
            "Check files to clean. Referenced files cannot be removed; selected files are saved in a safety ZIP first."
        )

    def _cleanup(self) -> None:
        selected = self._checked(self.recovery)
        if not selected:
            raise ValueError("Check recovery files first")
        if self._confirm(
            f"Back up and remove {len(selected)} recovery entries ({sum(e.size for e in selected) / 1024**2:.2f} MiB)?\nReferenced or changed files will be rejected."
        ):
            self._run(
                lambda token: cleanup_recovery(self.database, self.assets, selected),
                lambda path: self.status.setText(
                    f"Cleanup complete. Safety copy: {path}"
                ),
                False,
            )
