"""Archive actions for the Individual HDA panel.

Owns staged imports and archive callbacks on the panel GUI thread.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs import ihda_system


class PanelArchives:
    def __init__(self, window: Any) -> None:
        self.window = window
        self.stream: Any = None
        self.imported = False

    def start(
        self, operation: Callable[..., Any], completion: Callable[..., Any]
    ) -> None:
        window = self.window
        if window._tasks.busy:
            return
        window._loading_show()
        window.centralwidget.setEnabled(False)
        window.toolBar.setEnabled(False)
        window.menubar.setEnabled(False)
        try:
            window._tasks.start(operation, completion)
        except Exception as error:
            self.result(None, error)

    @QtCore.Slot(object, object)
    def result(self, result: Any, error: Exception | None) -> None:
        window = self.window
        window._loading_close()
        window.centralwidget.setEnabled(True)
        window.toolBar.setEnabled(True)
        window.menubar.setEnabled(True)
        if error is not None:
            logging.error("Library operation failed: %s", error)

    @QtCore.Slot()
    def idle(self) -> None:
        window = self.window
        if window._close_requested:
            QtCore.QTimer.singleShot(0, window.close)

    def shutdown_for_host(self) -> None:
        window = self.window
        window._host_destroying = True
        window._close_requested = False
        window._tasks.drain()
        window.close()

    def import_data(self) -> None:
        window = self.window
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            window,
            "Select Import iHDA Data File",
            str(pathlib.Path.home()),
            "iHDA file (*.zip *.ZIP)",
        )
        if not source:
            return
        window._video_player.player_stop()
        stream = window._services.archives(
            window._hda_base_dirpath,
            window._library.data_dirpath,
        )
        self.stream = stream
        self.start(lambda: stream.import_ihda_data(source), self.import_complete)

    def stage_import(self, stream: Any) -> None:
        """Owns the staged-import state that is committed on shutdown."""
        self.stream = stream
        self.imported = True

    def import_complete(self, backup: Any) -> None:
        window = self.window
        if backup is None:
            return
        window.centralwidget.setEnabled(False)
        window.toolBar.setEnabled(False)
        window.menubar.setEnabled(False)
        self.stage_import(self.stream)
        if window._host_destroying:
            return
        QtWidgets.QMessageBox.information(
            window,
            "Individual HDA",
            "Import is complete. restart iHDA app\nThe existing iHDA data was backed up\n"
            + str(backup),
        )

    def commit_import(self) -> None:
        if self.imported and self.stream is not None:
            self.stream.commit_import()
            self.imported = False

    def export_data(self) -> None:
        window = self.window
        destination = QtWidgets.QFileDialog.getExistingDirectory(
            window, "Select Export Directory", str(pathlib.Path.home())
        )
        if not destination:
            return
        stream = window._services.archives(
            window._hda_base_dirpath,
            window._library.data_dirpath,
        )
        self.start(lambda: stream.export_ihda_data(destination), self.export_complete)

    def export_complete(self, directory: Any) -> None:
        if directory is not None:
            ihda_system.IHDASystem.open_folder(directory)
