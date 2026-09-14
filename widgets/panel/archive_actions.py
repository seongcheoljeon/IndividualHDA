"""Archive actions for the Individual HDA panel.

Mixin methods run on the panel GUI thread and share its protected state.
They do not own a separate QWidget or change the public panel interface.
"""

from __future__ import annotations

from typing import Any, Callable

import logging
from PySide6 import QtWidgets, QtCore
import pathlib
from libs import ihda_system


class ArchiveActionsMixin:
    def _start_file_job(
        self, operation: Callable[..., Any], completion: Callable[..., Any]
    ) -> None:
        if self._tasks.busy:
            return
        self._loading_show()
        self.centralwidget.setEnabled(False)
        self.toolBar.setEnabled(False)
        self.menubar.setEnabled(False)
        try:
            self._tasks.start(operation, completion)
        except Exception as error:
            self._file_result(None, error)

    @QtCore.Slot(object, object)
    def _file_result(self, result: Any, error: Exception | None) -> None:
        self._loading_close()
        self.centralwidget.setEnabled(True)
        self.toolBar.setEnabled(True)
        self.menubar.setEnabled(True)
        if error is not None:
            logging.error("Library operation failed: %s", error)

    @QtCore.Slot()
    def _file_finished(self) -> None:
        if self._close_requested:
            QtCore.QTimer.singleShot(0, self.close)

    def shutdown_for_host(self) -> None:
        self._host_destroying = True
        self._close_requested = False
        self._tasks.drain()
        self.close()

    def _slot_import_data(self) -> None:
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Import iHDA Data File",
            str(pathlib.Path.home()),
            "iHDA file (*.zip *.ZIP)",
        )
        if not source:
            return
        self._video_player.player_stop()
        stream = self._services.archives(
            self._hda_base_dirpath,
            self._preference.data_dirpath,
        )
        self._import_stream = stream
        self._start_file_job(
            lambda: stream.import_ihda_data(source), self._import_complete
        )

    def _import_complete(self, backup: Any) -> None:
        if backup is None:
            return
        self.centralwidget.setEnabled(False)
        self.toolBar.setEnabled(False)
        self.menubar.setEnabled(False)
        self._is_imported_data = True
        if self._host_destroying:
            return
        QtWidgets.QMessageBox.information(
            self,
            "Individual HDA",
            "Import is complete. restart iHDA app\nThe existing iHDA data was backed up\n"
            + str(backup),
        )

    def _solve_before_app_terminate_import_data(self) -> None:
        if self._is_imported_data and self._import_stream is not None:
            self._import_stream.commit_import()

    def _slot_export_data(self) -> None:
        destination = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Export Directory", str(pathlib.Path.home())
        )
        if not destination:
            return
        stream = self._services.archives(
            self._hda_base_dirpath,
            self._preference.data_dirpath,
        )
        self._start_file_job(
            lambda: stream.export_ihda_data(destination), self._export_complete
        )

    def _export_complete(self, directory: Any) -> None:
        if directory is not None:
            ihda_system.IHDASystem.open_folder(directory)
