#!/usr/bin/env python
from __future__ import annotations

from widgets.panel.library_tools import LibraryToolsMixin
from widgets.panel.services import PanelServices
from libs.domain import LibraryContext, SelectionState
from libs.asset_store import AssetStore
from libs.archive_transfer import ArchiveTransfer

from PySide6 import QtGui, QtWidgets

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# project name      : individualHDA/main
# create date       : 2020.01.27 11:15
# modify date       : 2020.10.24 19:40

from libs.settings_store import initialize_config
import logging
import sqlite3
from re import compile as re_compile


from PySide6 import QtCore

import public

# third-party modules
import main_ui
import ui_settings
from libs import houdini_api, loading_indicator, log_handler, ihda_icons
from libs import dragdrop_overlay, ihda_system, identity
from libs.asset_search import AssetSearch
from widgets.make_video_info import make_video_info
from widgets.video_player import make_video_player
from widgets.web_view import make_web_view
from widgets.preference import preference
from widgets.rename_ihda import rename_ihda
from widgets.panel.context_menus import ContextMenusMixin
from widgets.panel.media_actions import MediaActionsMixin
from widgets.panel.archive_actions import ArchiveActionsMixin
from widgets.panel.asset_registration import AssetRegistrationMixin

from widgets.panel.houdini_actions import HoudiniActionsMixin
from widgets.panel.model_binding import ModelBindingMixin
from widgets.panel.library_sync import LibrarySyncMixin
from widgets.panel.ai_actions import AIActionsMixin

try:
    import hou
except ImportError:
    pass

__author__ = "Seongcheol Jeon"
__version__ = public.Value.current_ver
__date__ = "2026.09.11"

from widgets.panel.bootstrap import BootstrapMixin
from widgets.panel.presentation import PresentationMixin
from widgets.panel.selection import SelectionMixin
from widgets.panel.host_callbacks import HostCallbacksMixin
from widgets.panel.asset_management import AssetManagementMixin
from widgets.panel.library_queries import LibraryQueriesMixin
from widgets.panel.notes import NotesMixin


class IndividualHDA(
    LibraryToolsMixin,
    BootstrapMixin,
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
    ArchiveActionsMixin,
    AssetRegistrationMixin,
    LibrarySyncMixin,
    AIActionsMixin,
    QtWidgets.QMainWindow,
    main_ui.Ui_MainWindow__individualHDA,
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
        super(IndividualHDA, self).__init__(parent)
        self.setupUi(self)
        self._services = services if services is not None else PanelServices()
        self._tasks = self._services.tasks(self)
        self._tasks.result.connect(self._file_result)
        self._tasks.idle.connect(self._file_finished)
        # AI calls get their own controller so network latency never shares the
        # archive/encoder busy gate or the whole-window lock of _start_file_job.
        self._ai_tasks = self._services.tasks(self)
        self._asset_search = AssetSearch(self)
        self._asset_search.results.connect(self._apply_search_ids)
        self._asset_search.failed.connect(self._asset_search_failed)
        self._import_stream: ArchiveTransfer | None = None
        self._close_requested = False
        self._closing = False
        self._host_destroying = False
        self._embedded = embedded
        if public.IS_HOUDINI and not embedded:
            self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setAcceptDrops(True)
        self.centralwidget.setEnabled(False)
        self.toolBar.setEnabled(False)
        # status
        self._is_ready = False
        # regex
        self._regex_squence_str = re_compile(r"\$F4")
        # user id
        self._user = identity.current_user()
        # ui_settings
        self._ui_settings = ui_settings.UISettings(window=self)
        # logging
        self._log_handler = log_handler.LogHandler(out_stream=self.textBrowser__debug)
        # loading indicator class
        self._loading = loading_indicator.Overlay(parent=self)
        self._loading_close()
        # dragdrop indicator class
        self._dragdrop_overlay = dragdrop_overlay.Overlay(text="", parent=self)
        self._dragdrop_overlay_close()
        # widgets
        self._rename_ihda = rename_ihda.RenameIHDA(parent=self)
        self._preference = preference.Preference(parent=self)
        self._library = LibraryContext.from_preference(self._preference, self._user)
        self._repository = self._services.repository(self._library)
        self._make_videoinfo = make_video_info.MakeVideoInfo(parent=self)
        self._video_player = make_video_player(self._preference.ffmpeg_dirpath, self)
        _help_site = hou.helpServerUrl if public.IS_HOUDINI else None
        self._web_view = make_web_view(_help_site, self)
        # iHDA icons
        self._ihda_icons = ihda_icons.IHDAIcons()
        # not have null node context
        # /ch, /shop, /img, /vex    -> null 이 없음.
        self._not_have_null_node_context_lst = ["/ch", "/shop", "/img", "/vex"]
        # app properties 초기화
        self._is_reset_app_properties = False
        # import data 했는 지의 대한 변수
        self._is_imported_data = False
        # current pane tab
        self._current_panetab = None
        # iHDA data
        self._assets = AssetStore()
        self._infoDat = None
        self._ihda_category_view = None
        self._ihda_category_model = None
        self._ihda_category_proxy_model = None
        self._ihda_list_view = None
        self._ihda_list_model = None
        self._ihda_list_proxy_model = None
        self._ihda_table_view = None
        self._ihda_table_model = None
        self._ihda_table_proxy_model = None
        self._ihda_history_view = None
        self._ihda_history_model = None
        self._ihda_history_proxy_model = None
        self._ihda_record_view = None
        self._ihda_record_model = None
        self._ihda_record_proxy_model = None
        self._ihda_inside_view = None
        self._ihda_inside_model = None
        self._ihda_inside_proxy_model = None
        self._ihda_view_idx = 0
        self._video_view_idx = 1
        self._web_view_idx = 2
        self._hist_view_idx = 3
        self._selection = SelectionState()
        # initialization basic setting
        self._init_set_basic()
        # initialization setting
        self._init_set()
        self._ihda_icons.pixmap_thumbnail_data.changed.connect(self._thumbnail_ready)
        self._ihda_icons.pixmap_hist_thumbnail_data.changed.connect(
            self._history_thumbnail_ready
        )
        # signal & slot
        self._signal_func()
        # initialize select model
        self._init_select_ihda_category_model()
        self._setup_library_tools()
        self._init_library_sync()
        self._init_ai_actions()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        manager = getattr(self, "_library_manager", None)
        if manager is not None:
            self._library_manager = None
            manager.shutdown()
            manager.deleteLater()
        self._preference.shutdown()
        if self._tasks.file_job is not None:
            self._close_requested = True
            event.ignore()
            return
        self._ihda_icons.shutdown()
        self._closing = True
        self._tasks.shutdown_process()
        self._ai_tasks.drain()
        self._asset_search.drain()
        self._stop_library_sync()
        if public.IS_HOUDINI:
            # clean event
            self._loading_close()
            self._dragdrop_overlay_close()
            self._remove_event_loop_callback(self._wrapper_current_panetab)
            self._remove_event_loop_callback(self._loading_counter)
            self._remove_selection_callback(
                self._wrapper_selection_callback_item_by_ihda
            )
            # preference 설정 하지 않아 hda_base_dirpath가 None Type이라 예외처리함.
            try:
                if self._hda_base_dirpath is None:
                    data_dirpath = self._preference.get_data_dirpath_from_saved()
                    if data_dirpath is not None:
                        houdini_api.HoudiniAPI.clean_hda_library(data_dirpath)
                else:
                    houdini_api.HoudiniAPI.clean_hda_library(self._hda_base_dirpath)
            except TypeError as err:
                pass
            if not self._embedded:
                self.setParent(None)
        # 앱 속성 초기화를 선택했다면
        if self._is_reset_app_properties:
            if public.Paths.config_dirpath.exists():
                ihda_system.IHDASystem.remove_dir(dirpath=public.Paths.config_dirpath)
        else:
            self._ui_settings.save_main_window_geometry()
            self._ui_settings.save_splitter_status()
            self._ui_settings.save_cfg_dict_to_file()
        # import data로 데이터를 새로이 가져왔다면
        try:
            self._solve_before_app_terminate_import_data()
        except (OSError, sqlite3.Error, RuntimeError, ValueError) as error:
            self._closing = False
            logging.error(
                "Import activation failed; original library restored: %s", error
            )
            QtWidgets.QMessageBox.critical(self, "Individual HDA", str(error))
            event.ignore()
            return
        self._video_player.close()
        self._web_view.close()
        self._log_handler.close()
        event.accept()

    # node location record data

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._loading.resize(event.size())
        self._dragdrop_overlay.resize(event.size())
        super(IndividualHDA, self).resizeEvent(event)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(public.Type.mime_type):
            self._dragdrop_overlay_show(
                text="Drop the iHDA node onto the network", fontsize=15
            )
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
        else:
            super(IndividualHDA, self).dragEnterEvent(event)
