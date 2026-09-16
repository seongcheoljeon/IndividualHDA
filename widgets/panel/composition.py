from __future__ import annotations

import logging
from re import compile as re_compile
from typing import Any

from PySide6 import QtCore

import ui_settings
from libs import (
    dragdrop_overlay,
    houdini_api,
    identity,
    ihda_icons,
    loading_indicator,
    log_handler,
)
from libs.asset_store import AssetStore
from libs.domain import LibraryContext, SelectionState
from libs.host import IS_HOUDINI
from libs.paths import Paths
from widgets.asset_browser.integration import AssetBrowserIntegration
from widgets.asset_details.integration import AssetDetailsIntegration
from widgets.make_video_info import make_video_info
from widgets.panel.ai_actions import PanelAIActions
from widgets.panel.archive_actions import PanelArchives
from widgets.panel.bootstrap import PanelBootstrap
from widgets.panel.library_session import PersonalPanelSession
from widgets.panel.library_sync import PanelLibrarySync
from widgets.panel.lifetime import PanelLifetime
from widgets.panel.selection_presenter import PanelSelectionPresenter
from widgets.panel.services import PanelServices
from widgets.panel.shutdown import detach_host_callbacks
from widgets.preference import preference
from widgets.rename_ihda import rename_ihda
from widgets.video_player import make_video_player
from widgets.web_view import make_web_view


class PanelComposition:
    """Build the window in explicit phases; own acquired resources during startup."""

    def __init__(self, window: Any, services: PanelServices, embedded: bool) -> None:
        self.window, self.services, self.embedded = window, services, embedded
        self.lifetime = PanelLifetime()

    def build(self) -> None:
        try:
            self._create_features()
            self._create_session_and_widgets()
            self._initialize_models_and_state()
            self._connect_features()
        except Exception:
            self.window._closing = True
            for name, error in self.lifetime.close():
                logging.error("Startup resource cleanup failed (%s): %s", name, error)
            raise

    def _create_features(self) -> None:
        window, services = self.window, self.services
        window._services = services
        window._tasks = window._services.tasks(window)
        self.lifetime.add(
            "tasks",
            lambda: (window._tasks.shutdown_process(), window._tasks.drain()),
            30,
        )
        window._archives = PanelArchives(window)
        window._tasks.result.connect(window._archives.result)
        window._tasks.idle.connect(window._archives.idle)
        # AI calls get their own controller so network latency never shares the
        # archive/encoder busy gate or the whole-window lock of _start_file_job.
        window._ai_tasks = window._services.tasks(window)
        self.lifetime.add("ai_tasks", lambda: window._ai_tasks.drain(), 30)
        window._details = AssetDetailsIntegration(
            window, window._services.tasks(window)
        )
        self.lifetime.add("details", lambda: window._details.close(), 30)
        window._asset_search = window._services.asset_search(window)
        window._browser = AssetBrowserIntegration(
            window, window._asset_search, window._services.search_gateway
        )
        window._asset_search_debounce = window._browser.debounce
        self.lifetime.add("browser", lambda: window._browser.close(), 20)

    def _create_session_and_widgets(self) -> None:
        window, embedded = self.window, self.embedded
        window._close_requested = False
        window._closing = False
        window._host_destroying = False
        window._embedded = embedded
        if IS_HOUDINI and not embedded:
            window.setParent(
                houdini_api.HoudiniAPI.main_window(), QtCore.Qt.WindowType.Window
            )
        window.setAcceptDrops(True)
        window.centralwidget.setEnabled(False)
        window.toolBar.setEnabled(False)
        # status
        window._is_ready = False
        # regex
        window._regex_squence_str = re_compile(r"\$F4")
        # user id
        window._user = identity.current_user()
        # ui_settings
        window._ui_settings = ui_settings.UISettings(window=window)
        # logging
        window._log_dirpath = Paths.config_dirpath / "logs"
        log_handler.install_file_logging(window._log_dirpath)
        window._log_handler = log_handler.LogHandler(
            out_stream=window.textBrowser__debug
        )
        self.lifetime.add("log", lambda: window._log_handler.close(), 100)
        # loading indicator class
        window._loading = loading_indicator.Overlay(parent=window)
        window._loading_close()
        # dragdrop indicator class
        window._dragdrop_overlay = dragdrop_overlay.Overlay(text="", parent=window)
        window._dragdrop_overlay_close()
        # widgets
        window._rename_ihda = rename_ihda.RenameIHDA(parent=window)
        self.lifetime.add("rename", lambda: window._rename_ihda.close(), 80)
        window._preference = preference.Preference(parent=window)
        self.lifetime.add("preference", lambda: window._preference.shutdown(), 30)
        window._library = LibraryContext.from_preference(
            window._preference, window._user
        )
        window._repository = window._services.repository(window._library)
        window._make_videoinfo = make_video_info.MakeVideoInfo(parent=window)
        window._video_player = make_video_player(
            window._preference.ffmpeg_dirpath, window
        )
        self.lifetime.add("video", lambda: window._video_player.close(), 80)
        _help_site = houdini_api.HoudiniAPI.help_server_url()
        window._web_view = make_web_view(_help_site, window)
        self.lifetime.add("web", lambda: window._web_view.close(), 80)

    def _initialize_models_and_state(self) -> None:
        window = self.window
        # iHDA icons
        window._ihda_icons = ihda_icons.IHDAIcons()
        self.lifetime.add("icons", lambda: window._ihda_icons.shutdown(), 50)
        # not have null node context
        # /ch, /shop, /img, /vex    -> null 이 없음.
        window._not_have_null_node_context_lst = ["/ch", "/shop", "/img", "/vex"]
        # app properties 초기화
        window._is_reset_app_properties = False
        # current pane tab
        window._current_panetab = None
        # iHDA data
        window._assets = AssetStore()
        window._infoDat = None
        window._ihda_category_view = None
        window._ihda_category_model = None
        window._ihda_category_proxy_model = None
        window._ihda_list_view = None
        window._ihda_list_model = None
        window._ihda_list_proxy_model = None
        window._ihda_table_view = None
        window._ihda_table_model = None
        window._ihda_table_proxy_model = None
        window._ihda_history_view = None
        window._ihda_history_model = None
        window._ihda_history_proxy_model = None
        window._ihda_record_view = None
        window._ihda_record_model = None
        window._ihda_record_proxy_model = None
        window._ihda_inside_view = None
        window._ihda_inside_model = None
        window._ihda_inside_proxy_model = None
        window._ihda_view_idx = 0
        window._video_view_idx = 1
        window._web_view_idx = 2
        window._hist_view_idx = 3
        window._selection = SelectionState()
        window._panel_selection = PanelSelectionPresenter(window._selection, window)
        window._panel_library = PersonalPanelSession(window)

    def _connect_features(self) -> None:
        window = self.window
        self.lifetime.add("host_callbacks", lambda: detach_host_callbacks(window), 0)
        # initialization basic setting
        bootstrap = PanelBootstrap(window)
        bootstrap.open_library()
        window._browser.change_repository(window._repository)
        window._details.change_repository(window._repository, window._library)
        # initialization setting
        bootstrap.build_models()
        window._browser.connect(window)
        window._ihda_icons.pixmap_thumbnail_data.changed.connect(
            window._thumbnail_ready
        )
        window._ihda_icons.pixmap_hist_thumbnail_data.changed.connect(
            window._history_thumbnail_ready
        )
        # signal & slot
        bootstrap.connect_signals()
        # initialize select model
        window._init_select_ihda_category_model()
        window._setup_library_tools()
        window._library_sync = PanelLibrarySync(window)
        self.lifetime.add("sync", lambda: window._library_sync._stop_library_sync(), 10)
        window._library_sync._init_library_sync()
        window._ai_actions = PanelAIActions(window)
        window._ai_actions.connect()
        from widgets.team_library.integration import MainLibraryIntegration

        window._team_library = MainLibraryIntegration(window)
        self.lifetime.add("team", lambda: window._team_library.shutdown(), 20)
