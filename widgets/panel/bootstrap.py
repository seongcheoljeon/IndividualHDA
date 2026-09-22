"""Bootstrap for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from libs.ui_icons import Icon

if TYPE_CHECKING:
    from main import IndividualHDA

import logging
import pathlib
import sqlite3

from PySide6 import QtCore, QtGui

from libs import identity, ihda_system, log_handler, note_syntax
from libs.domain import LibraryContext
from libs.keys import Name, UISetting
from libs.operation_journal import recover_operations
from libs.paths import Paths
from libs.repository import LibraryUnavailable
from view import (
    ihda_category_view,
    ihda_history_view,
    ihda_inside_view,
    ihda_record_view,
)


class PanelBootstrap:
    def __init__(self, window: IndividualHDA) -> None:
        self.window = window

    def open_library(self) -> None:
        window = self.window
        if not window._preference.is_data_valid:
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="you did not specify a location where data is stored",
            )
            window._preference.show()
        else:
            db_filepath = window.queries.db_filepath
            assert isinstance(db_filepath, pathlib.Path)
            try:
                recover_operations(db_filepath.parent)
                db_api = window._services.open_database(db_filepath)
                # A local library has one owner: adopt the row it already has.
                window.session.user = identity.resolve_local_user(
                    db_api.list_user_ids()
                )
                db_api.close()
                window.session.context = LibraryContext.from_preference(
                    window._preference, window.session.user
                )
                window.session.repository = window._services.repository(
                    window.session.context
                )
                window.session.require_repository().ensure_user(window.session.user)
            except sqlite3.Error as error:
                # A locked or unreadable library must not surface as a raw traceback.
                raise LibraryUnavailable(
                    f"library database unavailable: {error}"
                ) from error

    def build_models(self) -> None:
        window = self.window
        # is ready iHDA
        window.presentation._set_is_ready()
        # hide parameters
        window.presentation._hide_parms()
        window.models.assets.reset(
            window.queries._get_hda_data(
                user_id=window.session.user, db_filepath=window.queries.db_filepath
            )
            or []
        )
        # combobox - search type
        window.comboBox__search_field_hist.addItems(["Name", "Tags", "Type"])
        # default font
        window.comboBox__search_type.setFont(window.presentation.get_default_font())
        window.comboBox__search_field_hist.setFont(
            window.presentation.get_default_font()
        )
        window.comboBox__hist_ihda_node.setFont(window.presentation.get_default_font())
        window.comboBox__hda_inside_node.setFont(window.presentation.get_default_font())
        window.dateEdit__hist_search_start.setFont(
            window.presentation.get_default_font()
        )
        window.dateEdit__hist_search_end.setFont(window.presentation.get_default_font())
        # main default icon size
        window.presentation._set_main_default_icon_size()
        window.doubleSpinBox__zoom.setMinimum(UISetting.min_zoom_value)
        window.doubleSpinBox__zoom.setMaximum(UISetting.max_zoom_value)
        note_syntax.NoteHighLighter(window.textEdit__note)
        note_font = window.presentation.get_font_properties(
            Name.PreferenceUI.spb_note_font_size,
            Name.PreferenceUI.cmb_note_font_style,
        )
        window.presentation._set_font_properties(window.textEdit__note, note_font)
        window.presentation._set_font_properties(
            window.textBrowser__note_preview, note_font
        )
        window.presentation._set_font_properties(
            window.textEdit__tag,
            window.presentation.get_font_properties(
                Name.PreferenceUI.spb_tags_font_size,
                Name.PreferenceUI.cmb_tags_font_style,
            ),
        )
        window.presentation._set_font_properties(
            window.textBrowser__debug,
            window.presentation.get_font_properties(
                Name.PreferenceUI.spb_debug_font_size,
                Name.PreferenceUI.cmb_debug_font_style,
            ),
        )
        # geometry & config setting
        if Paths.json_filepath.exists():
            window._log_handler.log_msg(logging.info, msg="load the configuration file")
            window._ui_settings.load_main_window_geometry()
            window._ui_settings.load_splitter_status()
            window._ui_settings.load_cfg_dict_from_file()
            # theme
            window._ui_settings.set_theme(theme=window._ui_settings.get_theme)
            # stackedwidget & view tool button
            window.selection.slot_select_view(
                index=window.stackedWidget__whole.currentIndex()
            )
            # stackecdwidget hda infos
            window.selection._slot_stackedwidget_hda_infos()
        else:
            # theme
            window._ui_settings.set_theme(theme=Name.default_theme)
        if window.session.repository is not None:
            window._ihda_icons.make_pixmap_ihda_data(
                icon_info=window.session.require_repository().asset_icons(
                    window.session.user
                )
            )
            window._ihda_icons.make_pixmap_cate_data(
                cate_lst=window.session.require_repository().categories(
                    window.session.user
                )
            )
            window._ihda_icons.make_pixmap_thumbnail_data(
                all_data=window.models.assets.rows
            )
            window._ihda_icons.make_pixmap_hist_thumbnail_data(
                all_data=window.session.require_repository().history_thumbnails(
                    window.session.user
                )
            )
        window.views.category = ihda_category_view.CategoryView(window)
        window.verticalLayout__category.addWidget(window.views.category)
        window.models._init_set_ihda_category_model()
        window.views.assets_list = window._browser.view.listView__hda
        window.models._init_set_ihda_list_model()
        window.views.assets_table = window._browser.view.tableView__hda
        window.models._init_set_ihda_table_model()
        window.views.history = ihda_history_view.HistoryView(window)
        window.verticalLayout__history.addWidget(window.views.history)
        window.models._init_set_ihda_history_model()
        window.views.record = ihda_record_view.RecordView(window)
        window.verticalLayout__hda_loc_record.addWidget(window.views.record)
        window.models._init_set_ihda_record_model()
        window.views.inside = ihda_inside_view.InsideView(window)
        window.verticalLayout__hda_inside_node.addWidget(window.views.inside)
        window.models._init_set_ihda_inside_model()
        from widgets.empty_state import attach_empty_state

        attach_empty_state(window.views.history).set_content(
            "No versions", "Select an asset to see its versions and activity."
        )
        window.views.record_empty = attach_empty_state(window.views.record)
        window.views.record_empty.set_content(
            "No scene records",
            "Records appear when iHDA nodes are imported into a saved scene.",
        )
        window.views.inside_empty = attach_empty_state(window.views.inside)
        from widgets.panel.inside_page import InsidePageBindings, InsidePageController

        window._inside_page = InsidePageController(
            InsidePageBindings(
                scan_scene=window._services.host_scene.scan_ihda_nodes,
                model=window.models.inside_model,
                proxy=window.models.inside_proxy_model,
                view=window.views.inside,
                empty=window.views.inside_empty,
                combo=window.comboBox__hda_inside_node,
                count_label=window.label__found_hda_inside_hipfile_count,
                connect_checkbox=window.checkBox__hda_inside_connect_to_view,
                search_edit=window.lineEdit__search_found_hda_inside_node,
                nav_button=window.pushButton__hda_inside_node_view,
                icons=window._ihda_icons,
                selected_asset_id=lambda: window.selection.state.asset.id,
                go_to_node=lambda path: window.selection.go_to_houdini_node(path),
                presentation=window.presentation,
            )
        )

        # Opening the page scans it; the saved page was restored before the
        # models existed, so models_ready() covers that first show.
        def find_page_toggled(checked: bool) -> None:
            if checked:
                window._inside_page.page_shown()

        window.pushButton__hda_inside_node_view.toggled.connect(find_page_toggled)
        window._inside_page.models_ready()
        from model.ihda_list_model import ListModel
        from widgets.item_delegates import CardDelegate

        # Items are drawn by delegates; models keep providing data only.
        card = CardDelegate(
            window.views.assets_list,
            data_role=ListModel.data_role,
            favorite_role=ListModel.favorite_role,
            version_role=ListModel.version_role,
        )
        window.views.assets_list.setItemDelegate(card)
        window.views.assets_list.viewport().setAttribute(
            QtCore.Qt.WidgetAttribute.WA_Hover, True
        )
        card.favoriteToggled.connect(window.management.toggle_favorite_at)
        from libs.model_columns import AssetColumn, HistoryColumn
        from model.ihda_history_model import HistoryModel
        from model.ihda_table_model import TableModel
        from widgets.item_delegates import RowDelegate

        rows = RowDelegate(
            window.views.assets_table,
            data_role=TableModel.data_role,
            name_column=AssetColumn.NAME,
            secondary_column=AssetColumn.DEFINITION,
            version_column=AssetColumn.VERSION,
            favorite_column=AssetColumn.FAVORITE,
            favorite_role=TableModel.favorite_role,
        )
        window.views.assets_table.setItemDelegate(rows)
        rows.favoriteToggled.connect(window.management.toggle_favorite_at)
        window.views.history.setItemDelegate(
            RowDelegate(
                window.views.history,
                data_role=HistoryModel.data_role,
                name_column=HistoryColumn.NAME,
                secondary_column=HistoryColumn.DEFINITION,
                version_column=HistoryColumn.VERSION,
            )
        )
        for view in (window.views.assets_table, window.views.history):
            view.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        from model.ihda_category_model import CategoryModel
        from widgets.item_delegates import CountBadgeDelegate

        window.views.category.setItemDelegate(
            CountBadgeDelegate(
                window.views.category, count_role=CategoryModel.count_role
            )
        )
        from model.ihda_record_model import RecordModel

        window.views.record.setItemDelegate(
            CountBadgeDelegate(window.views.record, count_role=RecordModel.count_role)
        )
        window.selection._slot_chk_hist_search_data(
            window.checkBox__hist_search_date.isChecked()
        )
        window.presentation._init_set_video_player()
        window.presentation._init_set_web_view()
        window.selection._slot_set_view_mode()
        window.selection._slot_thumbnails()
        window.callbacks._slot_sync_hou_net_cate()
        window.callbacks._slot_selection_node_sync()
        window.selection._init_set_first_ihda_item()
        window.notes._set_move_cursor_textedit(window.textBrowser__debug)

    def connect_signals(self) -> None:
        window = self.window
        window.stackedWidget__whole.currentChanged.connect(
            window.callbacks._slot_stackedwidget_whole_curt_changed
        )
        window.pushButton__hda_info.clicked.connect(
            window.selection._slot_stackedwidget_hda_infos
        )
        window.pushButton__hda_loc_record.clicked.connect(
            window.selection._slot_stackedwidget_hda_infos
        )
        window.pushButton__hda_inside_node_view.clicked.connect(
            window.selection._slot_stackedwidget_hda_infos
        )
        window.pushButton__zoomin.clicked.connect(window.presentation._slot_zoomin)
        window.pushButton__zoomout.clicked.connect(window.presentation._slot_zoomout)
        window.pushButton__favorite_node.clicked.connect(
            window.management._slot_favorite_node
        )
        window.pushButton__thumbnail.clicked.connect(window.selection._slot_thumbnails)
        window.pushButton__donate.clicked.connect(window.presentation._slot_donate)
        window.views.category.customContextMenuRequested.connect(
            window.menus._build_context_category_menu
        )
        window.views.category.selectionModel().selectionChanged.connect(
            window.selection._slot_selected_category
        )
        window.views.record.customContextMenuRequested.connect(
            window.menus._build_context_record_menu
        )
        window.views.record.selectionModel().selectionChanged.connect(
            window.selection._slot_selected_record
        )
        window.views.inside.customContextMenuRequested.connect(
            window.menus._build_context_inside_menu
        )
        window.views.history.doubleClicked.connect(
            window.selection._slot_hda_double_clicked
        )
        window.views.history.selectionModel().selectionChanged.connect(
            window.selection._slot_on_hda_item_clicked
        )
        window.views.history.clicked.connect(window.selection._slot_on_hda_item_clicked)
        window.views.history.customContextMenuRequested.connect(
            window.menus._build_context_history_menu
        )
        window.views.history.signal.signal_object.connect(
            window.registration._slot_drop_node_into_hda_view
        )
        window.views.history.signal.mouse_signal_object.connect(
            window.houdini._slot_mouse_move_event_on_houdini
        )
        window.checkBox__hist_search_date.stateChanged.connect(
            window.selection._slot_chk_hist_search_data
        )
        window.comboBox__hist_ihda_node.currentIndexChanged.connect(
            window.selection._slot_hist_ihda_combobox
        )
        window.dateEdit__hist_search_start.dateChanged.connect(
            window.selection._slot_hist_ihda_search_date
        )
        window.dateEdit__hist_search_end.dateChanged.connect(
            window.selection._slot_hist_ihda_search_date
        )
        window.comboBox__search_field_hist.currentIndexChanged.connect(
            window.selection._slot_set_search_hist_field_target
        )
        window.checkBox__casesensitive_hda_hist.stateChanged.connect(
            window.selection._slot_checkbox_hist_hda_item_casesensitive
        )
        from libs.debounce import DebouncedText

        window._history_search_debounce = DebouncedText(
            window.models.search_filter_regexp_hist_hda_item,
            window,
            delay=window._services.policy.search.delay_ms,
            immediate=lambda: (
                window.models.history_model.rowCount()
                < window._services.policy.search.immediate_rows
            ),
        )
        window.lineEdit__search_hda_hist.textChanged.connect(
            window._history_search_debounce.submit
        )
        window.lineEdit__search_cate.textChanged.connect(
            window.models.search_filter_regexp_hda_cate
        )
        window.pushButton__metadata_save.clicked.connect(
            window.notes._slot_save_metadata
        )
        window.toolButton__note_preview.toggled.connect(
            window.notes._slot_toggle_note_preview
        )
        from widgets.panel.shortcuts import install_shortcuts

        window._shortcuts = install_shortcuts(window)
        window.textEdit__note.textChanged.connect(window.notes.refresh_note_preview)
        # Personal edits autosave; the button appears when a team library is active.
        window.pushButton__metadata_save.setVisible(False)
        window.checkBox__casesensitive_cate.stateChanged.connect(
            window.selection._slot_checkbox_hda_cate_casesensitive
        )
        window.pushButton__icon_mode.clicked.connect(
            window.selection._slot_set_view_mode
        )
        window.pushButton__table_mode.clicked.connect(
            window.selection._slot_set_view_mode
        )
        window.actionCategory_Synchronization.triggered.connect(
            window.callbacks._slot_sync_hou_net_cate
        )
        window.pushButton__cleanup_hda_record.clicked.connect(
            window.management._slot_cleanup_hda_record
        )
        window.lineEdit__search_record.textChanged.connect(
            window.models._search_filter_regexp_hda_record
        )
        window.checkBox__record_only_current_hipfile.stateChanged.connect(
            window.selection._slot_record_only_curt_filter
        )
        window.checkBox__record_only_current_ihda.stateChanged.connect(
            window.selection._slot_record_only_curt_filter
        )
        window.views.record.doubleClicked.connect(
            window.selection._slot_hda_record_double_clicked
        )
        window.views.record.signal.mouse_signal_object.connect(
            window.houdini._slot_mouse_move_event_on_houdini
        )
        window.views.record.signal.signal_object.connect(
            window.registration._slot_drop_node_into_hda_view
        )
        inside_page = window._inside_page
        window.pushButton__hda_inside_node_refresh.clicked.connect(inside_page.refresh)
        window.comboBox__hda_inside_node.currentIndexChanged.connect(
            inside_page.filter_by_combo
        )
        window.checkBox__hda_inside_connect_to_view.stateChanged.connect(
            inside_page.connect_to_selection
        )
        window.lineEdit__search_found_hda_inside_node.textChanged.connect(
            inside_page.search
        )
        window.views.inside.doubleClicked.connect(inside_page.double_clicked)
        window.actionNode_Synchronization.triggered.connect(
            window.callbacks._slot_selection_node_sync
        )
        window.actionDefault.triggered.connect(
            lambda: window.presentation._set_theme(theme=Name.default_theme)
        )
        window.actionDark_blue.triggered.connect(
            lambda: window.presentation._set_theme(theme=Name.darkblue_theme)
        )
        window.actionHelp.triggered.connect(window.presentation._slot_help)
        window.actionOpen_Log_Folder = QtGui.QAction(
            QtGui.QIcon(Icon.IC_FOLDER_WHITE), "Open log folder", window
        )
        window.menuHelp.addAction(window.actionOpen_Log_Folder)
        window.actionOpen_Log_Folder.triggered.connect(
            lambda: ihda_system.IHDASystem.open_folder(dirpath=window._log_dirpath)
        )
        window.actionAbout.triggered.connect(window.presentation._slot_about)
        window.actionReset.triggered.connect(window.presentation._slot_cfg_reset)
        window.actionOpen_the_hda_directory.triggered.connect(
            lambda: ihda_system.IHDASystem.open_folder(
                dirpath=window.queries.hda_base_dirpath
            )
        )
        window.actionQuit.triggered.connect(window.close)
        window.actioniHDA.triggered.connect(
            lambda: window.selection.slot_select_view(inst=window.actioniHDA)
        )
        window.actionVideo_Player.triggered.connect(
            lambda: window.selection.slot_select_view(inst=window.actionVideo_Player)
        )
        window.actionWeb.triggered.connect(
            lambda: window.selection.slot_select_view(inst=window.actionWeb)
        )
        window.actionHistory.triggered.connect(
            lambda: window.selection.slot_select_view(inst=window.actionHistory)
        )
        window.actionPreference.triggered.connect(lambda: window._preference.show())
        window.actionLocal_AI_Models = QtGui.QAction(
            QtGui.QIcon(Icon.NETWORK_INTELLIGENCE),
            "Local AI Models…",
            window,
        )
        window.menuTools.insertAction(
            window.menuDownload.menuAction(), window.actionLocal_AI_Models
        )
        window.actionLocal_AI_Models.triggered.connect(
            window.presentation._slot_local_ai_models
        )
        window.actionSubmit_a_Bug_Report.triggered.connect(
            window.presentation._slot_submit_bug_report
        )
        window.actionSubmit_Feedback.triggered.connect(
            window.presentation._slot_submit_feedback
        )
        window.actionFFmpeg.triggered.connect(
            window.presentation._slot_download_ffmpeg_site
        )
        window.actionCodec.triggered.connect(
            window.presentation._slot_download_codec_site
        )
        window.actionDonate.triggered.connect(window.presentation._slot_donate)
        window.actionImport_Data.triggered.connect(window._slot_import_data)
        window.actionExport_Data.triggered.connect(window._slot_export_data)
        window.actionDelete_All.triggered.connect(
            window.management._slot_delete_all_history
        )
        window.actionNull.triggered.connect(
            lambda: window.presentation._slot_node_connections(inst=window.actionNull)
        )
        window.actionInput.triggered.connect(
            lambda: window.presentation._slot_node_connections(inst=window.actionInput)
        )
        window.actionOuput.triggered.connect(
            lambda: window.presentation._slot_node_connections(inst=window.actionOuput)
        )
        window.actionBoth.triggered.connect(
            lambda: window.presentation._slot_node_connections(inst=window.actionBoth)
        )
        window.actionCleanup.triggered.connect(window.management._slot_db_cleanup)
        window._make_videoinfo.accepted.connect(window.media._slot_make_video)
        window._preference.accepted.connect(window.presentation._slot_preference)
        window._rename_ihda.accepted.connect(window.management._slot_hda_name_changed)
        window.doubleSpinBox__zoom.valueChanged.connect(
            window.presentation._slot_zoom_value
        )
