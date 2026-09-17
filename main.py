#!/usr/bin/env python
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs.ai_features import Description
from libs.app_metadata import MINIMUM_HOUDINI_MAJOR
from libs.asset_contracts import LibrarySnapshot
from libs.keys import Type, Value

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# project name      : individualHDA/main
# create date       : 2020.01.27 11:15
# modify date       : 2020.10.24 19:40
from libs.settings_store import initialize_config
from widgets.panel.asset_registration import PanelAssetRegistration
from widgets.panel.composition import PanelComposition
from widgets.panel.context_menus import PanelContextMenus
from widgets.panel.houdini_actions import PanelHoudiniActions

# third-party modules
from widgets.panel.layout import MainWindowLayout
from widgets.panel.library_tools import PanelLibraryTools
from widgets.panel.media_actions import PanelMediaActions
from widgets.panel.model_binding import PanelModelBinding
from widgets.panel.services import PanelServices
from widgets.panel.shutdown import PanelShutdown
from widgets.panel.state import PanelSessionState, PanelStatus, PanelViews

if TYPE_CHECKING:
    from pathlib import Path
    from re import Pattern

    from libs.asset_search import AssetSearch
    from libs.debounce import DebouncedText
    from libs.dragdrop_overlay import Overlay as DragOverlay
    from libs.ihda_icons import IHDAIcons
    from libs.loading_indicator import Overlay
    from libs.log_handler import LogHandler
    from libs.task_controller import TaskController
    from ui_settings import UISettings
    from widgets.asset_browser.integration import AssetBrowserIntegration
    from widgets.asset_details.integration import AssetDetailsIntegration
    from widgets.make_video_info.make_video_info import MakeVideoInfo
    from widgets.panel.ai_actions import PanelAIActions
    from widgets.panel.archive_actions import PanelArchives
    from widgets.panel.library_sync import PanelLibrarySync
    from widgets.panel.scene_usage import SceneUsageIntegration
    from widgets.panel.services import PanelServices
    from widgets.preference.preference import Preference
    from widgets.rename_ihda.rename_ihda import RenameIHDA
    from widgets.team_library.integration import MainLibraryIntegration
    from widgets.video_player import UnavailableVideoPlayer
    from widgets.video_player.video_player import VideoPlayer

__author__ = "Seongcheol Jeon"
__version__ = Value.current_ver
__date__ = "2026.09.11"

from widgets.panel.asset_management import PanelAssetManagement
from widgets.panel.host_callbacks import PanelHostCallbacks
from widgets.panel.library_queries import PanelLibraryQueries
from widgets.panel.notes import PanelNotes
from widgets.panel.presentation import PanelPresentation
from widgets.panel.selection import PanelSelection


class IndividualHDA(QtWidgets.QMainWindow, MainWindowLayout):
    _services: PanelServices
    _tasks: TaskController
    _ai_tasks: TaskController
    _archives: PanelArchives
    _ai_actions: PanelAIActions
    _library_sync: PanelLibrarySync
    _loading: Overlay
    _dragdrop_overlay: DragOverlay
    _preference: Preference
    _ihda_icons: IHDAIcons
    _browser: AssetBrowserIntegration
    _details: AssetDetailsIntegration
    _rename_ihda: RenameIHDA
    _make_videoinfo: MakeVideoInfo
    _ui_settings: UISettings
    _team_library: MainLibraryIntegration
    _scene_usage: SceneUsageIntegration
    _history_search_debounce: DebouncedText
    _log_handler: LogHandler
    _asset_search: AssetSearch
    _asset_search_debounce: DebouncedText
    _log_dirpath: Path
    _regex_squence_str: Pattern[str]
    _not_have_null_node_context_lst: list[str]
    _web_view: QtWidgets.QWidget
    _video_player: VideoPlayer | UnavailableVideoPlayer

    # 한번에 등록할 수 있는 최대 노드 개수
    @property
    def _MAX_NUM_OF_NODE_REGIST(self) -> int:
        return self._services.policy.maximum_node_batch

    # 권장 Houdini 버전 >= 21
    _RECOMMENDED_HOUDINI_VERSION = MINIMUM_HOUDINI_MAJOR

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
        self.session = PanelSessionState()
        self.status = PanelStatus()
        self.views = PanelViews()
        self.callbacks = PanelHostCallbacks()
        self.houdini = PanelHoudiniActions()
        self.management = PanelAssetManagement()
        self.media = PanelMediaActions()
        self.menus = PanelContextMenus()
        self.models = PanelModelBinding()
        self.notes = PanelNotes()
        self.presentation = PanelPresentation()
        self.queries = PanelLibraryQueries()
        self.registration = PanelAssetRegistration()
        self.selection = PanelSelection()
        self.tools = PanelLibraryTools()
        self._composition = PanelComposition(
            self,
            services if services is not None else PanelServices.from_saved_settings(),
            embedded,
        )
        self._shutdown = PanelShutdown(self, self._composition.lifetime)
        self._composition.build()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._tasks.file_job is not None:
            self.status.close_requested = True
            event.ignore()
            return
        if self._shutdown.close():
            event.accept()
        else:
            event.ignore()

    @property
    def _ihda_view_idx(self) -> int:
        return self.stackedWidget__whole.indexOf(self.page__ihda)

    @property
    def _video_view_idx(self) -> int:
        return self.stackedWidget__whole.indexOf(self.page__video_player)

    @property
    def _web_view_idx(self) -> int:
        return self.stackedWidget__whole.indexOf(self.page__web_view)

    @property
    def _hist_view_idx(self) -> int:
        return self.stackedWidget__whole.indexOf(self.page__history)

    def reload_library(self) -> None:
        self._library_sync.reload_library()

    def _poll_library_revision(self) -> None:
        self._library_sync._poll_library_revision()

    def _apply_library_snapshot(self, snapshot: LibrarySnapshot) -> None:
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
            self.presentation._dragdrop_overlay_show(
                text="Drop the iHDA node onto the network", fontsize=15
            )
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
