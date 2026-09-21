from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import IndividualHDA

import logging
from re import compile as re_compile

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
from libs.domain import LibraryContext
from libs.host import IS_HOUDINI
from libs.paths import Paths
from widgets.asset_browser.integration import (
    AssetBrowserIntegration,
    BrowserActions,
    BrowserBindings,
)
from widgets.asset_details.integration import AssetDetailsIntegration, DetailsBindings
from widgets.make_video_info import make_video_info
from widgets.panel.ai_actions import PanelAIActions, PanelAIActionsBindings
from widgets.panel.archive_actions import PanelArchives, PanelArchivesBindings
from widgets.panel.asset_management import PanelAssetManagementBindings
from widgets.panel.asset_registration import PanelAssetRegistrationBindings
from widgets.panel.bootstrap import PanelBootstrap
from widgets.panel.context_menus import PanelContextMenusBindings
from widgets.panel.host_callbacks import PanelHostCallbacksBindings
from widgets.panel.houdini_actions import PanelHoudiniActionsBindings
from widgets.panel.library_port import LibraryPort, PersonalLibrary, TeamLibrary
from widgets.panel.library_queries import PanelLibraryQueriesBindings
from widgets.panel.library_session import PersonalPanelSession
from widgets.panel.library_sync import PanelLibrarySync, PanelLibrarySyncBindings
from widgets.panel.library_tools import PanelLibraryToolsBindings
from widgets.panel.lifetime import PanelLifetime
from widgets.panel.media_actions import PanelMediaActionsBindings
from widgets.panel.model_binding import PanelModelBindingBindings
from widgets.panel.notes import PanelNotesBindings
from widgets.panel.presentation import PanelPresentationBindings
from widgets.panel.selection import PanelSelectionBindings
from widgets.panel.services import PanelServices
from widgets.panel.shutdown import detach_host_callbacks
from widgets.preference import preference
from widgets.rename_ihda import rename_ihda
from widgets.video_player import make_video_player
from widgets.web_view import make_web_view


def _active_library(window: Any) -> LibraryPort:
    """The only place that knows whether a team library is in front."""
    team = window._team_library
    if team.active:
        return TeamLibrary(team)
    return PersonalLibrary(
        database=lambda: window.queries.db_filepath,
        writer=lambda: window._services.lifecycle(
            window.session.require_repository(), window._services.names
        ),
        reload=lambda: window._library_sync.reload_library(),
        paths_changed=lambda: window.tools._tools_paths_changed(),
    )


class PanelComposition:
    """Build the window in explicit phases; own acquired resources during startup."""

    def __init__(
        self, window: IndividualHDA, services: PanelServices, embedded: bool
    ) -> None:
        self.window, self.services, self.embedded = window, services, embedded
        self.lifetime = PanelLifetime()

    def build(self) -> None:
        try:
            self._create_features()
            self._create_session_and_widgets()
            self._initialize_models_and_state()
            self._bind_features()
            self._connect_features()
        except Exception:
            self.window.status.closing = True
            for name, error in self.lifetime.close():
                logging.error("Startup resource cleanup failed (%s): %s", name, error)
            raise

    def _create_features(self) -> None:
        window, services = self.window, self.services
        window._services = services
        window._ai_actions = PanelAIActions()
        window._archives = PanelArchives()
        window._library_sync = PanelLibrarySync()
        window._tasks = window._services.tasks(window)
        self.lifetime.add(
            "tasks",
            window._tasks.close,
            30,
        )
        window._tasks.result.connect(window._archives.result)
        window._tasks.idle.connect(window._archives.idle)
        # AI calls get their own controller so network latency never shares the
        # archive/encoder busy gate or the whole-window lock of _start_file_job.
        window._ai_tasks = window._services.tasks(window)
        self.lifetime.add("ai_tasks", lambda: window._ai_tasks.drain(), 30)
        window._details = AssetDetailsIntegration(
            DetailsBindings(
                note=window.textEdit__note,
                tags=window.textEdit__tag,
                status=window.label__metadata_status,
                tag_status=window.label__tag_status,
                show_tags=window.notes.set_label_tags,
                saved=self._metadata_saved,
            ),
            window._services.tasks(window),
            autosave_delay_ms=window._services.policy.autosave_delay_ms,
        )
        self.lifetime.add("details", lambda: window._details.close(), 30)
        window._asset_search = window._services.asset_search(window)
        window._browser = AssetBrowserIntegration(
            BrowserBindings(
                host=window.widget__asset_browser_host,
                counter_host=window.widget__asset_count_host,
                row_count=lambda: len(window.models.assets.rows),
                failed=window.models._asset_search_failed_message,
                open_preferences=lambda: window._preference.show(),
            ),
            window._asset_search,
            window._services.search_gateway,
            search_policy=window._services.policy.search,
        )
        window.splitter__ihda_whole_vertical = (
            window._browser.view.splitter__ihda_whole_vertical
        )
        window.stackedWidget__hda = window._browser.view.stackedWidget__hda
        window.verticalLayout__listview = window._browser.view.verticalLayout__listview
        window.verticalLayout__tableview = (
            window._browser.view.verticalLayout__tableview
        )
        window.pushButton__favorite_node = (
            window._browser.view.pushButton__favorite_node
        )
        window.pushButton__thumbnail = window._browser.view.pushButton__thumbnail
        window.pushButton__zoomin = window._browser.view.pushButton__zoomin
        window.pushButton__zoomout = window._browser.view.pushButton__zoomout
        window.doubleSpinBox__zoom = window._browser.view.doubleSpinBox__zoom
        window.pushButton__icon_mode = window._browser.view.pushButton__icon_mode
        window.pushButton__table_mode = window._browser.view.pushButton__table_mode
        window.comboBox__search_type = window._browser.view.comboBox__search_type
        window.checkBox__casesensitive_hda = (
            window._browser.view.checkBox__casesensitive_hda
        )
        window.lineEdit__search_hda = window._browser.view.lineEdit__search_hda
        window.textEdit__tag.tagClicked.connect(
            lambda tag: window.lineEdit__search_hda.setText(f"tag:{tag}")
        )
        window.label__hda_count = window._browser.view.label__hda_count
        window._asset_search_debounce = window._browser.debounce
        self.lifetime.add("browser", lambda: window._browser.close(), 20)

    def _create_session_and_widgets(self) -> None:
        window, embedded = self.window, self.embedded
        window.status.close_requested = False
        window.status.closing = False
        window.status.host_destroying = False
        window.status.embedded = embedded
        if IS_HOUDINI and not embedded:
            window.setParent(
                houdini_api.HoudiniAPI.main_window(), QtCore.Qt.WindowType.Window
            )
        window.setAcceptDrops(True)
        window.centralwidget.setEnabled(False)
        window.toolBar.setEnabled(False)
        # status
        window.status.ready = False
        # regex
        window._regex_squence_str = re_compile(r"\$F4")
        # user id
        window.session.user = identity.current_user()
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
        from widgets.toast import ToastStack

        window._toasts = ToastStack(parent=window)
        window._loading.close()
        # dragdrop indicator class
        window._dragdrop_overlay = dragdrop_overlay.Overlay(text="", parent=window)
        window._dragdrop_overlay.close()
        # widgets
        window._rename_ihda = rename_ihda.RenameIHDA(parent=window)
        self.lifetime.add("rename", lambda: window._rename_ihda.close(), 80)
        window._preference = preference.Preference(parent=window)
        self.lifetime.add("preference", lambda: window._preference.shutdown(), 30)
        window.session.context = LibraryContext.from_preference(
            window._preference, window.session.user
        )
        window.session.repository = window._services.repository(window.session.context)
        window._make_videoinfo = make_video_info.MakeVideoInfo(parent=window)
        window._video_player = make_video_player(
            window._preference.ffmpeg_dirpath, window, policy=self.services.media
        )
        self.lifetime.add("video", lambda: window._video_player.close(), 80)
        _help_site = self.services.help_site or houdini_api.HoudiniAPI.help_server_url()
        window._web_view = make_web_view(_help_site, window)
        self.lifetime.add("web", lambda: window._web_view.close(), 80)

    def _initialize_models_and_state(self) -> None:
        window = self.window
        # iHDA icons
        window._ihda_icons = ihda_icons.IHDAIcons(
            thumbnail_policy=self.services.thumbnails
        )
        self.lifetime.add("icons", lambda: window._ihda_icons.shutdown(), 50)
        # not have null node context
        # /ch, /shop, /img, /vex    -> null 이 없음.
        window._not_have_null_node_context_lst = ["/ch", "/shop", "/img", "/vex"]
        # app properties 초기화
        window.status.reset_settings = False
        # current pane tab
        window.callbacks.current_panetab = None
        # iHDA data
        window.session.actions = PersonalPanelSession(
            window.session,
            window._details.presenter,
            lambda: window._library_sync.presenter.refresh(),
        )

    def _connect_features(self) -> None:
        window = self.window
        self.lifetime.add("host_callbacks", lambda: detach_host_callbacks(window), 0)
        # initialization basic setting
        bootstrap = PanelBootstrap(window)
        bootstrap.open_library()
        window._browser.change_repository(window.session.repository)
        window._details.change_repository(
            window.session.repository,
            window.session.context,
            vocabulary=window.session.tag_vocabulary,
        )
        # initialization setting
        bootstrap.build_models()
        window._browser.connect(
            window.models.list_proxy_model,
            window.models.table_proxy_model,
            BrowserActions(
                selected=window.selection._slot_on_hda_item_clicked,
                double_clicked=window.selection._slot_hda_double_clicked,
                context_menu=window.menus._build_context_ihda_menu,
                dropped=window.registration._slot_drop_node_into_hda_view,
                mouse_moved=window.houdini._slot_mouse_move_event_on_houdini,
            ),
        )
        window._ihda_icons.pixmap_thumbnail_data.changed.connect(
            window.models._thumbnail_ready
        )
        window._ihda_icons.pixmap_hist_thumbnail_data.changed.connect(
            window.models._history_thumbnail_ready
        )
        # signal & slot
        bootstrap.connect_signals()
        # initialize select model
        window.selection.init_select_ihda_category_model()
        window.tools._setup_library_tools()
        self.lifetime.add(
            "registration_status",
            lambda: window.tools.registration_status_tasks.drain(),
            20,
        )
        self.lifetime.add("sync", lambda: window._library_sync._stop_library_sync(), 10)
        window._library_sync._init_library_sync()
        window._ai_actions.setup_ai_actions()
        from widgets.team_library.integration import (
            MainLibraryIntegration,
            TeamBindings,
        )

        window._team_library = MainLibraryIntegration(
            TeamBindings(
                parent=window,
                callbacks=window._services.callbacks,
                runtime=window._services.runtime,
                policy=window._services.policy,
                tasks=window._tasks,
                ai_tasks=window._ai_tasks,
                browser=window._browser,
                details=window._details,
                icons=window._ihda_icons,
                sync=window._library_sync,
                video_player=window._video_player,
                models=window.models,
                notes=window.notes,
                presentation=window.presentation,
                selection=window.selection,
                session=window.session,
                status=window.status,
                tools=window.tools,
                views=window.views,
                apply_snapshot=window._library_sync._apply_library_snapshot,
                refresh=window.reload_library,
                invalidate_ai=lambda: setattr(window._ai_actions, "target_id", -1),
                show_assets=lambda: window.selection.slot_select_view(
                    index=window._ihda_view_idx
                ),
                show_video=lambda: window.selection.slot_select_view(
                    index=window._video_view_idx
                ),
                personal_controls=(
                    window.actionImport_Data,
                    window.actionExport_Data,
                    window.actionDelete_All,
                    window.actionCleanup,
                    window.actionOpen_the_hda_directory,
                    window.actionPreference,
                    window.actionReset,
                    window.actionNode_Synchronization,
                    window.pushButton__hda_loc_record,
                    window.pushButton__hda_inside_node_view,
                ),
                label__hist_cnt=window.label__hist_cnt,
                label__hist_tags=window.label__hist_tags,
                label__metadata_status=window.label__metadata_status,
                label__tag_status=window.label__tag_status,
                lineEdit__search_hda=window.lineEdit__search_hda,
                pushButton__ai_suggest=window.pushButton__ai_suggest,
                pushButton__metadata_save=window.pushButton__metadata_save,
                stackedWidget__hda_infos=window.stackedWidget__hda_infos,
                textEdit__note=window.textEdit__note,
                textEdit__tag=window.textEdit__tag,
            )
        )
        self.lifetime.add("team", lambda: window._team_library.shutdown(), 20)

        from libs.database.tracking import deliver_local_scene_usage
        from libs.scene_outbox import SceneOutbox
        from widgets.panel.scene_usage import SceneUsageBindings, SceneUsageIntegration

        window._scene_usage = SceneUsageIntegration(
            SceneUsageBindings(
                host=window._services.host_scene,
                closing=lambda: window.status.closing,
                actor=lambda: window.session.user,
                catalog=lambda: (
                    window._team_library.require_catalog()
                    if window._team_library.active
                    else None
                ),
                database=lambda: (
                    Path(window.session.context.db_filepath)
                    if window.session.context
                    else None
                ),
                message=window.statusbar.showMessage,
                deliver_local=deliver_local_scene_usage,
            ),
            window._services.tasks(window),
            SceneOutbox(Paths.config_dirpath / "scene-outbox.sqlite3"),
        )
        window._library_sync.timer.timeout.connect(window._scene_usage.flush)
        self.lifetime.add("scene_usage", lambda: window._scene_usage.close(), 20)
        if not self.services.host_actions_enabled:
            self._disable_host_actions()

    def _disable_host_actions(self) -> None:
        window = self.window
        reason = "This action requires a running Houdini session."
        for action in (
            window.actionCategory_Synchronization,
            window.actionNode_Synchronization,
        ):
            action.setChecked(False)
            action.setEnabled(False)
            action.setToolTip(reason)
        window._browser.view.setAcceptDrops(False)
        window.views.assets_list.setAcceptDrops(False)
        window.views.assets_table.setAcceptDrops(False)

    def _bind_features(self) -> None:
        window = self.window
        window.callbacks.bindings = PanelHostCallbacksBindings(
            host=window._services.host_callbacks,
            enabled=window._services.host_actions_enabled and IS_HOUDINI,
            contexts_without_null=window._not_have_null_node_context_lst,
            selection=window.selection,
            status=window.status,
            ui=window,
        )
        window.houdini.bindings = PanelHoudiniActionsBindings(
            callbacks=window.callbacks,
            management=window.management,
            models=window.models,
            parent=window,
            presentation=window.presentation,
            queries=window.queries,
            scene_usage=lambda: window._scene_usage,
            selection=window.selection,
            services=window._services,
            session=window.session,
            library=lambda: _active_library(window),
            ui=window,
        )
        window.management.bindings = PanelAssetManagementBindings(
            details=window._details,
            icons=window._ihda_icons,
            models=window.models,
            notes=window.notes,
            parent=window,
            presentation=window.presentation,
            queries=window.queries,
            reload_library=lambda: window._library_sync.reload_library(),
            rename_dialog=window._rename_ihda,
            selection=window.selection,
            services=window._services,
            session=window.session,
            library=lambda: _active_library(window),
            tools=window.tools,
            ui=window,
            video_player=window._video_player,
            views=window.views,
        )
        window.media.bindings = PanelMediaActionsBindings(
            host_enabled=window._services.host_actions_enabled,
            capture=window._services.host_capture,
            models=window.models,
            parent=window,
            preference=window._preference,
            presentation=window.presentation,
            queries=window.queries,
            selection=window.selection,
            sequence_pattern=window._regex_squence_str,
            session=window.session,
            status=window.status,
            tasks=window._tasks,
            library=lambda: _active_library(window),
            ui=window,
            video_info=window._make_videoinfo,
        )
        window.menus.bindings = PanelContextMenusBindings(
            host_enabled=window._services.host_actions_enabled and IS_HOUDINI,
            callbacks=window.callbacks,
            management=window.management,
            media=window.media,
            models=window.models,
            notes=window.notes,
            parent=window,
            presentation=window.presentation,
            queries=window.queries,
            rename_dialog=window._rename_ihda,
            selection=window.selection,
            session=window.session,
            suggest=lambda: window._ai_actions.suggest(),
            library=lambda: _active_library(window),
            tools=window.tools,
            ui=window,
            video_info=window._make_videoinfo,
            video_player=window._video_player,
            views=window.views,
        )
        window.models.bindings = PanelModelBindingBindings(
            browser=window._browser,
            icons=window._ihda_icons,
            presentation=window.presentation,
            queries=window.queries,
            selection=window.selection,
            session=window.session,
            ui=window,
            views=window.views,
        )
        window.notes.bindings = PanelNotesBindings(
            models=window.models,
            parent=window,
            presentation=window.presentation,
            selection=window.selection,
            session=window.session,
            ui=window,
        )
        window.presentation.bindings = PanelPresentationBindings(
            browser=window._browser,
            callbacks=window.callbacks,
            details=window._details,
            drag_overlay=window._dragdrop_overlay,
            loading=window._loading,
            models=window.models,
            parent=window,
            preference=window._preference,
            queries=window.queries,
            rename_dialog=window._rename_ihda,
            services=window._services,
            session=window.session,
            status=window.status,
            toasts=window._toasts,
            ui=window,
            ui_settings=window._ui_settings,
            video_info=window._make_videoinfo,
            video_player=window._video_player,
            views=window.views,
            web_view=window._web_view,
        )
        window.queries.bindings = PanelLibraryQueriesBindings(
            management=window.management,
            models=window.models,
            presentation=window.presentation,
            selection=window.selection,
            session=window.session,
        )
        window.registration.bindings = PanelAssetRegistrationBindings(
            callbacks=window.callbacks,
            houdini=window.houdini,
            management=window.management,
            models=window.models,
            parent=window,
            preference=window._preference,
            presentation=window.presentation,
            queries=window.queries,
            reload_library=lambda: window._library_sync.reload_library(),
            selection=window.selection,
            services=window._services,
            session=window.session,
            library=lambda: _active_library(window),
            ui=window,
        )
        window.selection.bindings = PanelSelectionBindings(
            icons=window._ihda_icons,
            models=window.models,
            notes=window.notes,
            preference=window._preference,
            presentation=window.presentation,
            queries=window.queries,
            session=window.session,
            library=lambda: _active_library(window),
            ui=window,
            video_player=window._video_player,
            views=window.views,
            houdini=window.houdini,
        )
        window.tools.bindings = PanelLibraryToolsBindings(
            imported=lambda: window._archives.imported,
            presentation=window.presentation,
            models=window.models,
            parent=window,
            queries=window.queries,
            reload_library=lambda: window._library_sync.reload_library(),
            scene_usage=lambda: window._scene_usage,
            selection=window.selection,
            services=window._services,
            session=window.session,
            stage_import=lambda stream: window._archives.stage_import(stream),
            status=window.status,
            tasks=window._tasks,
            library=lambda: _active_library(window),
            team=lambda: window._team_library,
            ui=window,
            views=window.views,
        )

        window._ai_actions.bindings = PanelAIActionsBindings(
            notes=window.notes,
            preference=window._preference,
            selection=window.selection,
            services=window._services,
            session=window.session,
            tasks=window._ai_tasks,
            library=lambda: _active_library(window),
            ui=window,
        )

        window._archives.bindings = PanelArchivesBindings(
            parent=window,
            presentation=window.presentation,
            queries=window.queries,
            services=window._services,
            session=window.session,
            status=window.status,
            tasks=window._tasks,
            ui=window,
            video_player=window._video_player,
        )

        window._library_sync.bindings = PanelLibrarySyncBindings(
            details=window._details,
            icons=window._ihda_icons,
            models=window.models,
            notes=window.notes,
            parent=window,
            selection=window.selection,
            services=window._services,
            session=window.session,
            status=window.status,
            tasks=window._tasks,
            ui=window,
            views=window.views,
        )

    def _metadata_saved(
        self, asset_id: int, field: str, value: str | list[str]
    ) -> None:
        from libs.keys import Key
        from libs.tags import normalize_tags

        window = self.window
        row = window.models.assets.id_rows.get(asset_id)
        if row is None:
            return
        window.queries.change_hda_data(
            row=row,
            key=Key.hda_note if field == "note" else Key.hda_tags,
            val=value if field == "note" else tuple(normalize_tags(value)),
        )
        if field == "tag":
            tags = tuple(normalize_tags(value))
            window.models.history_model.update_item_data_by_hkey_id_from_model(
                hkey_id=asset_id, key=Key.History.tags, val=tags
            )
            if window.selection.state.asset.id == asset_id:
                window.notes.set_label_tags(tags)
        window.models.refresh_asset_search()
