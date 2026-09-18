"""Archive actions for the Individual HDA panel.

Owns staged imports and archive callbacks on the panel GUI thread.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtWidgets

from libs import ihda_system

if TYPE_CHECKING:
    from libs.task_controller import TaskController
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.ports import LibraryQueryPort, PresentationPort
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState, PanelStatus
    from widgets.video_player import UnavailableVideoPlayer
    from widgets.video_player.video_player import VideoPlayer


@dataclass(frozen=True, slots=True)
class PanelArchivesBindings:
    parent: QtWidgets.QWidget
    presentation: PresentationPort
    queries: LibraryQueryPort
    services: PanelServices
    session: PanelSessionState
    status: PanelStatus
    tasks: TaskController
    ui: MainWindowLayout
    video_player: VideoPlayer | UnavailableVideoPlayer


class PanelArchives:
    bindings: PanelArchivesBindings

    def __init__(self) -> None:
        self.stream: Any = None
        self.imported = False

    def start(
        self, operation: Callable[..., Any], completion: Callable[..., Any]
    ) -> None:
        if self.bindings.tasks.busy:
            return
        self.bindings.presentation.loading_show()
        self.bindings.ui.centralwidget.setEnabled(False)
        self.bindings.ui.toolBar.setEnabled(False)
        self.bindings.ui.menubar.setEnabled(False)
        try:
            self.bindings.tasks.start(operation, completion)
        except Exception as error:
            self.result(None, error)

    @QtCore.Slot(object, object)
    def result(self, result: Any, error: Exception | None) -> None:
        self.bindings.presentation.loading_close()
        self.bindings.ui.centralwidget.setEnabled(True)
        self.bindings.ui.toolBar.setEnabled(True)
        self.bindings.ui.menubar.setEnabled(True)
        if error is not None:
            logging.error("Library operation failed: %s", error)

    @QtCore.Slot()
    def idle(self) -> None:
        if self.bindings.status.close_requested:
            QtCore.QTimer.singleShot(0, self.bindings.parent.close)

    def shutdown_for_host(self) -> None:
        self.bindings.status.host_destroying = True
        self.bindings.status.close_requested = False
        self.bindings.tasks.drain()
        self.bindings.parent.close()

    def import_data(self) -> None:
        source, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.bindings.parent,
            "Select Import iHDA Data File",
            str(pathlib.Path.home()),
            "iHDA file (*.zip *.ZIP)",
        )
        if not source:
            return
        self.bindings.video_player.player_stop()
        stream = self.bindings.services.archives(
            self.bindings.session.require_context().hda_base_dirpath,
            self.bindings.session.require_context().data_dirpath,
        )
        self.stream = stream
        self.start(lambda: stream.import_ihda_data(source), self.import_complete)

    def stage_import(self, stream: Any) -> None:
        """Owns the staged-import state that is committed on shutdown."""
        self.stream = stream
        self.imported = True

    def import_complete(self, backup: Any) -> None:
        if backup is None:
            return
        self.bindings.ui.centralwidget.setEnabled(False)
        self.bindings.ui.toolBar.setEnabled(False)
        self.bindings.ui.menubar.setEnabled(False)
        self.stage_import(self.stream)
        if self.bindings.status.host_destroying:
            return
        QtWidgets.QMessageBox.information(
            self.bindings.parent,
            "Individual HDA",
            "Import is complete. restart iHDA app\nThe existing iHDA data was backed up\n"
            + str(backup),
        )

    def commit_import(self) -> None:
        if self.imported and self.stream is not None:
            self.stream.commit_import()
            self.imported = False

    def export_data(self) -> None:
        destination = QtWidgets.QFileDialog.getExistingDirectory(
            self.bindings.parent, "Select Export Directory", str(pathlib.Path.home())
        )
        if not destination:
            return
        stream = self.bindings.services.archives(
            self.bindings.session.require_context().hda_base_dirpath,
            self.bindings.session.require_context().data_dirpath,
        )
        self.start(lambda: stream.export_ihda_data(destination), self.export_complete)

    def export_complete(self, directory: Any) -> None:
        if directory is not None:
            ihda_system.IHDASystem.open_folder(directory)
