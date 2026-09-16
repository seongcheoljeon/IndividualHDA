#!/usr/bin/env python
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs.ai_features import Description
from libs.keys import Type, Value

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# project name      : individualHDA/main
# create date       : 2020.01.27 11:15
# modify date       : 2020.10.24 19:40
from libs.settings_store import initialize_config
from widgets.panel.asset_registration import AssetRegistrationMixin
from widgets.panel.composition import PanelComposition
from widgets.panel.context_menus import ContextMenusMixin
from widgets.panel.houdini_actions import HoudiniActionsMixin

# third-party modules
from widgets.panel.layout import MainWindowLayout
from widgets.panel.library_tools import LibraryToolsMixin
from widgets.panel.media_actions import MediaActionsMixin
from widgets.panel.model_binding import ModelBindingMixin
from widgets.panel.services import PanelServices
from widgets.panel.shutdown import PanelShutdown

__author__ = "Seongcheol Jeon"
__version__ = Value.current_ver
__date__ = "2026.09.11"

from widgets.panel.asset_management import AssetManagementMixin
from widgets.panel.host_callbacks import HostCallbacksMixin
from widgets.panel.library_queries import LibraryQueriesMixin
from widgets.panel.notes import NotesMixin
from widgets.panel.presentation import PresentationMixin
from widgets.panel.selection import SelectionMixin


class IndividualHDA(
    LibraryToolsMixin,
    PresentationMixin,
    SelectionMixin,
    HostCallbacksMixin,
    AssetManagementMixin,
    LibraryQueriesMixin,
    NotesMixin,
    HoudiniActionsMixin,
    ModelBindingMixin,
    ContextMenusMixin,
    MediaActionsMixin,
    AssetRegistrationMixin,
    QtWidgets.QMainWindow,
    MainWindowLayout,
):
    # 한번에 등록할 수 있는 최대 노드 개수
    _MAX_NUM_OF_NODE_REGIST = 30
    # 권장 Houdini 버전 >= 21
    _RECOMMENDED_HOUDINI_VERSION = 21

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        embedded: bool = False,
        services: PanelServices | None = None,
    ) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None or QtCore.QThread.currentThread() != app.thread():
            raise RuntimeError("Create Individual HDA on the Houdini GUI thread")
        initialize_config()
        super().__init__(parent)
        self.build_ui(self)
        self._composition = PanelComposition(
            self, services or PanelServices(), embedded
        )
        self._shutdown = PanelShutdown(self, self._composition.lifetime)
        self._composition.build()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._tasks.file_job is not None:
            self._close_requested = True
            event.ignore()
            return
        if self._shutdown.close():
            event.accept()
        else:
            event.ignore()

    def reload_library(self) -> None:
        self._library_sync.reload_library()

    def _poll_library_revision(self) -> None:
        self._library_sync._poll_library_revision()

    def _apply_library_snapshot(self, snapshot: tuple[Any, ...]) -> None:
        self._library_sync._apply_library_snapshot(snapshot)

    @property
    def _known_revision(self) -> int:
        return self._library_sync._known_revision

    @_known_revision.setter
    def _known_revision(self, value: int) -> None:
        self._library_sync._known_revision = value

    @property
    def _reload_pending(self) -> bool:
        return self._library_sync._reload_pending

    # Explicit compatibility entry points for existing Qt wiring and host scripts.
    def _start_file_job(
        self, operation: Callable[..., Any], completion: Callable[..., Any]
    ) -> None:
        self._archives.start(operation, completion)

    def _stage_import(self, stream: Any) -> None:
        self._archives.stage_import(stream)

    def _slot_import_data(self) -> None:
        self._archives.import_data()

    def _slot_export_data(self) -> None:
        self._archives.export_data()

    def shutdown_for_host(self) -> None:
        self._archives.shutdown_for_host()

    @property
    def _is_imported_data(self) -> bool:
        return self._archives.imported

    @_is_imported_data.setter
    def _is_imported_data(self, value: bool) -> None:
        self._archives.imported = value

    @property
    def _ai_target_id(self) -> int | None:
        return self._ai_actions.target_id

    @_ai_target_id.setter
    def _ai_target_id(self, value: int | None) -> None:
        self._ai_actions.target_id = value

    def _slot_ai_suggest(self) -> None:
        self._ai_actions.suggest()

    def _ai_describe_done(self, description: Description) -> None:
        self._ai_actions.describe_done(description)

    # node location record data

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._loading.resize(event.size())
        self._dragdrop_overlay.resize(event.size())
        super().resizeEvent(event)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(Type.mime_type):
            self._dragdrop_overlay_show(
                text="Drop the iHDA node onto the network", fontsize=15
            )
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
