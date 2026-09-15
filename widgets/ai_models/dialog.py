"""Local AI Models: detect Ollama, download a recommended model, apply it.

All HTTP runs on a TaskController worker; the pull reports progress through a
Qt signal emitted from the worker thread (queued delivery to this dialog).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs import ollama
from libs.ai_backends import probe
from libs.ai_provider import AIProvider, AISettings, make_provider
from libs.ihda_system import IHDASystem
from libs.task_controller import TaskController


def _gb(size_bytes: int) -> str:
    return f"{size_bytes / 1024**3:.1f} GB"


def _installed_name(name: str) -> str:
    return name if ":" in name else f"{name}:latest"


class LocalModelsDialog(QtWidgets.QDialog):
    settingsChosen = QtCore.Signal(object)  # AISettings
    # status, completed bytes, total bytes. `object` keeps Python ints: a Qt `int`
    # argument is 32-bit and a 7 GB model overflows it (libshiboken Overflow).
    progress = QtCore.Signal(str, object, object)

    def __init__(
        self,
        endpoint: str = ollama.DEFAULT_ENDPOINT,
        parent: QtWidgets.QWidget | None = None,
        *,
        provider_factory: Callable[[AISettings], AIProvider] = make_provider,
        client: Any = ollama,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.provider_factory = provider_factory
        self.setWindowTitle("Local AI Models")
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.resize(720, 620)
        self.tasks = TaskController(self)
        self.tasks.result.connect(self._result)
        self.tasks.idle.connect(self._idle)
        self.cancel = threading.Event()
        self._closing = False
        self._destroying = False
        self._installed: set[str] = set()
        self._version: str | None = None
        self.progress.connect(self._on_progress)
        self._build(endpoint)
        QtCore.QTimer.singleShot(0, self.refresh)

    # --- layout -------------------------------------------------------------
    def _build(self, endpoint: str) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        server = QtWidgets.QGroupBox("Server")
        server_form = QtWidgets.QFormLayout(server)
        row = QtWidgets.QHBoxLayout()
        self.endpoint = QtWidgets.QLineEdit(endpoint)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        row.addWidget(self.endpoint)
        row.addWidget(self.refresh_button)
        server_form.addRow("Endpoint", row)
        self.server_status = QtWidgets.QLabel("Checking…")
        server_form.addRow("Status", self.server_status)
        self.install_box = QtWidgets.QWidget()
        install = QtWidgets.QVBoxLayout(self.install_box)
        install.setContentsMargins(0, 0, 0, 0)
        hint = QtWidgets.QLabel(
            "Ollama is not running. Install it, start it, then press Refresh.\n"
            f"Install: {self.client.install_hint()}"
        )
        hint.setWordWrap(True)
        hint.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        install.addWidget(hint)
        self.download_page = QtWidgets.QPushButton("Open download page")
        self.download_page.clicked.connect(
            lambda: IHDASystem.open_browser(self.client.DOWNLOAD_PAGE)
        )
        install.addWidget(self.download_page, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.install_box.hide()
        server_form.addRow(self.install_box)
        layout.addWidget(server)

        installed = QtWidgets.QGroupBox("Installed models")
        installed_layout = QtWidgets.QVBoxLayout(installed)
        self.installed_list = QtWidgets.QListWidget()
        self.installed_list.itemSelectionChanged.connect(self._sync_buttons)
        installed_layout.addWidget(self.installed_list)
        layout.addWidget(installed)

        recommended = QtWidgets.QGroupBox(
            "Recommended for this library (image + Korean/English)"
        )
        rec_layout = QtWidgets.QVBoxLayout(recommended)
        self.vram_label = QtWidgets.QLabel("GPU memory: detecting…")
        rec_layout.addWidget(self.vram_label)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Model", "Download", "Min GPU", "Vision", "Note"])
        self.tree.setRootIsDecorated(False)
        for choice in self.client.RECOMMENDED:
            item = QtWidgets.QTreeWidgetItem(
                [
                    choice.name,
                    f"{choice.download_gb:.1f} GB",
                    f"{choice.min_vram_gb:g} GB",
                    "yes" if choice.vision else "no",
                    choice.note,
                ]
            )
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, choice.name)
            self.tree.addTopLevelItem(item)
        self.tree.itemSelectionChanged.connect(self._sync_buttons)
        rec_layout.addWidget(self.tree)
        custom_row = QtWidgets.QHBoxLayout()
        custom_row.addWidget(QtWidgets.QLabel("Other model"))
        self.custom = QtWidgets.QLineEdit()
        self.custom.setPlaceholderText(
            "name:tag from ollama.com/library (overrides the table)"
        )
        self.custom.textChanged.connect(self._sync_buttons)
        custom_row.addWidget(self.custom)
        rec_layout.addLayout(custom_row)
        layout.addWidget(recommended)

        download = QtWidgets.QHBoxLayout()
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.download_button = QtWidgets.QPushButton("Download")
        self.download_button.clicked.connect(self.download)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_task)
        download.addWidget(self.progress_bar, 1)
        download.addWidget(self.download_button)
        download.addWidget(self.cancel_button)
        layout.addLayout(download)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QtWidgets.QHBoxLayout()
        self.use_button = QtWidgets.QPushButton("Use as AI backend")
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self.use_selected)
        self.test_button = QtWidgets.QPushButton("Test connection")
        self.test_button.clicked.connect(self.test_connection)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.close)
        buttons.addWidget(self.use_button)
        buttons.addWidget(self.test_button)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    # --- state ----------------------------------------------------------------
    def endpoint_url(self) -> str:
        return self.client.endpoint_url(self.endpoint.text())

    def selected_model(self) -> str:
        custom = self.custom.text().strip()
        if custom:
            return custom
        items = self.tree.selectedItems()
        if items:
            return str(items[0].data(0, QtCore.Qt.ItemDataRole.UserRole))
        chosen = self.installed_list.selectedItems()
        return chosen[0].text().split("  ")[0] if chosen else ""

    def _sync_buttons(self) -> None:
        model = self.selected_model()
        busy = self.tasks.busy
        self.download_button.setEnabled(
            bool(model) and self._version is not None and not busy
        )
        self.use_button.setEnabled(
            bool(model) and _installed_name(model) in self._installed and not busy
        )
        self.test_button.setEnabled(
            bool(model) and self._version is not None and not busy
        )

    def _settings(self) -> AISettings:
        return AISettings(
            kind="local", endpoint=self.endpoint_url(), model=self.selected_model()
        )

    # --- operations -------------------------------------------------------------
    def refresh(self) -> None:
        endpoint = self.endpoint_url()
        client = self.client

        def probe_server(token: threading.Event) -> tuple[Any, Any, Any]:
            version = client.version(endpoint)
            models = client.installed_models(endpoint) if version is not None else []
            return version, models, client.detect_vram_gb()

        self._run(probe_server, self._refreshed, cancellable=False)

    def _refreshed(self, snapshot: tuple[Any, Any, Any]) -> None:
        version, models, vram = snapshot
        self._version = version
        self.install_box.setVisible(version is None)
        self.server_status.setText(
            f"Ollama {version} at {self.endpoint_url()}" if version else "Not running"
        )
        self.installed_list.clear()
        self._installed = set()
        for model in models:
            self._installed.add(model.name)
            self.installed_list.addItem(f"{model.name}  ({_gb(model.size_bytes)})")
        self.vram_label.setText(
            f"GPU memory: {vram:g} GB" if vram is not None else "GPU memory: unknown"
        )
        recommended = self.client.choose_recommended(vram)
        for row in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(row)
            installed = _installed_name(
                str(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
            )
            item.setText(0, item.data(0, QtCore.Qt.ItemDataRole.UserRole))
            item.setForeground(
                0,
                QtGui.QBrush(
                    QtGui.QColor("#7fc97f")
                    if installed in self._installed
                    else QtGui.QBrush()
                ),
            )
            if (
                item.data(0, QtCore.Qt.ItemDataRole.UserRole) == recommended
                and not self.tree.selectedItems()
            ):
                item.setSelected(True)
        self._sync_buttons()

    def download(self) -> None:
        model = self.selected_model()
        endpoint = self.endpoint_url()
        client = self.client
        self.progress_bar.setRange(0, 0)  # busy until the first total arrives
        self.status.setText(f"Downloading {model}…")
        self._run(
            lambda token: client.pull(
                endpoint, model, progress=self.progress.emit, cancel=token
            ),
            self._pulled,
        )

    @QtCore.Slot(str, int, int)
    def _on_progress(self, status: str, completed: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(completed * 100 / total))
        self.status.setText(
            f"{status}  {_gb(completed)} / {_gb(total)}" if total else status
        )

    def _pulled(self, finished: Any) -> None:
        if finished:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.status.setText("Download complete")
            QtCore.QTimer.singleShot(0, self.refresh)
        else:
            self.progress_bar.setRange(0, 100)
            self.status.setText("Download cancelled (finished layers are kept)")

    def test_connection(self) -> None:
        settings = self._settings()
        factory = self.provider_factory
        self.status.setText("Testing…")
        self._run(
            lambda token: probe(factory(settings)), self._tested, cancellable=False
        )

    def _tested(self, answer: Any) -> None:
        self.status.setText(f"Connection OK, model answered: {answer!r}")

    def use_selected(self) -> None:
        settings = self._settings()
        self.settingsChosen.emit(settings)
        self.status.setText(
            f"Applied {settings.model} as the AI backend (save Preferences with OK)"
        )

    # --- worker plumbing (same shape as LibraryManager) -------------------------
    def _run(
        self,
        operation: Callable[[threading.Event], Any],
        completion: Callable[[Any], None],
        cancellable: bool = True,
    ) -> None:
        if self.tasks.busy:
            self.status.setText("Wait for the current operation to finish")
            return
        self.cancel = threading.Event()
        token = self.cancel
        self.cancel_button.setEnabled(cancellable)
        self.refresh_button.setEnabled(False)
        self.tasks.start(lambda: operation(token), completion)
        self._sync_buttons()

    def _result(self, value: Any, error: Exception | None) -> None:
        if error is not None:
            self.progress_bar.setRange(0, 100)
            self.status.setText(str(error))
            if not self._destroying:
                QtWidgets.QMessageBox.warning(self, "Local AI Models", str(error))

    def _idle(self) -> None:
        self.cancel_button.setEnabled(False)
        self.refresh_button.setEnabled(True)
        self._sync_buttons()
        if self._closing:
            self.accept()

    def cancel_task(self) -> None:
        self.cancel.set()
        self.status.setText("Cancelling…")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._closing = True
        if self.tasks.busy:
            self.cancel.set()
            event.ignore()
        else:
            super().closeEvent(event)

    def reject(self) -> None:
        self._closing = True
        if self.tasks.busy:
            self.cancel.set()
        else:
            super().reject()

    def shutdown(self) -> None:
        self._destroying = True
        self._closing = True
        self.cancel.set()
        self.tasks.drain()
        self.close()
