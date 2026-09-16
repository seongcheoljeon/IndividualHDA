"""Bootstrap for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

import logging
import pathlib
import sqlite3
from typing import Any

from PySide6 import QtGui

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
    def __init__(self, window: Any) -> None:
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
            db_filepath = window._db_filepath
            assert isinstance(db_filepath, pathlib.Path)
            try:
                recover_operations(db_filepath.parent)
                db_api = window._services.open_database(db_filepath)
                # A local library has one owner: adopt the row it already has.
                window._user = identity.resolve_local_user(db_api.list_user_ids())
                db_api.close()
                window._library = LibraryContext.from_preference(
                    window._preference, window._user
                )
                window._repository = window._services.repository(window._library)
                window._repository.ensure_user(window._user)
            except sqlite3.Error as error:
                # A locked or unreadable library must not surface as a raw traceback.
                raise LibraryUnavailable(
                    f"library database unavailable: {error}"
                ) from error

    def build_models(self) -> None:
        window = self.window
        # is ready iHDA
        window._set_is_ready()
        # hide parameters
        window._hide_parms()
        window._assets.reset(
            window._get_hda_data(user_id=window._user, db_filepath=window._db_filepath)
            or []
        )
        # combobox - search type
        window.comboBox__search_field_hist.addItems(["Name", "Tags", "Type"])
        # default font
        window.comboBox__search_type.setFont(window._get_default_font())
        window.comboBox__search_field_hist.setFont(window._get_default_font())
        window.comboBox__hist_ihda_node.setFont(window._get_default_font())
        window.comboBox__hda_inside_node.setFont(window._get_default_font())
        window.dateEdit__hist_search_start.setFont(window._get_default_font())
        window.dateEdit__hist_search_end.setFont(window._get_default_font())
        # main default icon size
        window._set_main_default_icon_size()
        window.doubleSpinBox__zoom.setMinimum(UISetting.min_zoom_value)
        window.doubleSpinBox__zoom.setMaximum(UISetting.max_zoom_value)
        note_syntax.NoteHighLighter(window.textEdit__note)
        note_syntax.NoteHighLighter(window.textEdit__tag)
        window._set_font_properties(
            window.textEdit__note,
            window._get_font_properties(
                Name.PreferenceUI.spb_note_font_size,
                Name.PreferenceUI.cmb_note_font_style,
            ),
        )
        window._set_font_properties(
            window.textEdit__tag,
            window._get_font_properties(
                Name.PreferenceUI.spb_tags_font_size,
                Name.PreferenceUI.cmb_tags_font_style,
            ),
        )
        window._set_font_properties(
            window.textBrowser__debug,
            window._get_font_properties(
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
            window._slot_select_view(index=window.stackedWidget__whole.currentIndex())
            # stackecdwidget hda infos
            window._slot_stackedwidget_hda_infos()
        else:
            # theme
            window._ui_settings.set_theme(theme=Name.default_theme)
        if window._repository is not None:
            window._ihda_icons.make_pixmap_ihda_data(
                icon_info=window._repository.asset_icons(window._user)
            )
            window._ihda_icons.make_pixmap_cate_data(
                cate_lst=window._repository.categories(window._user)
            )
            window._ihda_icons.make_pixmap_thumbnail_data(all_data=window._assets.rows)
            window._ihda_icons.make_pixmap_hist_thumbnail_data(
                all_data=window._repository.history_thumbnails(window._user)
            )
        window._ihda_category_view = ihda_category_view.CategoryView(window)
        window.verticalLayout__category.addWidget(window._ihda_category_view)
        window._init_set_ihda_category_model()
        window._ihda_list_view = window._browser.view.listView__hda
        window._init_set_ihda_list_model()
        window._ihda_table_view = window._browser.view.tableView__hda
        window._init_set_ihda_table_model()
        window._ihda_history_view = ihda_history_view.HistoryView(window)
        window.verticalLayout__history.addWidget(window._ihda_history_view)
        window._init_set_ihda_history_model()
        window._ihda_record_view = ihda_record_view.RecordView(window)
        window.verticalLayout__hda_loc_record.addWidget(window._ihda_record_view)
        window._init_set_ihda_record_model()
        window._ihda_inside_view = ihda_inside_view.InsideView(window)
        window.verticalLayout__hda_inside_node.addWidget(window._ihda_inside_view)
        window._init_set_ihda_inside_model()
        window._slot_chk_hist_search_data(window.checkBox__hist_search_date.isChecked())
        window._init_set_video_player()
        window._init_set_web_view()
        window._slot_set_view_mode()
        window._slot_thumbnails()
        window._slot_sync_hou_net_cate()
        window._slot_selection_node_sync()
        window._init_set_first_ihda_item()
        window._set_move_cursor_textedit(window.textBrowser__debug)

    def connect_signals(self) -> None:
        window = self.window
        window.stackedWidget__whole.currentChanged.connect(
            window._slot_stackedwidget_whole_curt_changed
        )
        window.pushButton__hda_info.clicked.connect(
            window._slot_stackedwidget_hda_infos
        )
        window.pushButton__hda_loc_record.clicked.connect(
            window._slot_stackedwidget_hda_infos
        )
        window.pushButton__hda_inside_node_view.clicked.connect(
            window._slot_stackedwidget_hda_infos
        )
        window.pushButton__zoomin.clicked.connect(window._slot_zoomin)
        window.pushButton__zoomout.clicked.connect(window._slot_zoomout)
        window.pushButton__favorite_node.clicked.connect(window._slot_favorite_node)
        window.pushButton__thumbnail.clicked.connect(window._slot_thumbnails)
        window.pushButton__donate.clicked.connect(window._slot_donate)
        window._ihda_category_view.customContextMenuRequested.connect(
            window._build_context_category_menu
        )
        window._ihda_category_view.selectionModel().selectionChanged.connect(
            window._slot_selected_category
        )
        window._ihda_record_view.customContextMenuRequested.connect(
            window._build_context_record_menu
        )
        window._ihda_record_view.selectionModel().selectionChanged.connect(
            window._slot_selected_record
        )
        window._ihda_inside_view.customContextMenuRequested.connect(
            window._build_context_inside_menu
        )
        window._ihda_history_view.doubleClicked.connect(window._slot_hda_double_clicked)
        window._ihda_history_view.selectionModel().selectionChanged.connect(
            window._slot_on_hda_item_clicked
        )
        window._ihda_history_view.clicked.connect(window._slot_on_hda_item_clicked)
        window._ihda_history_view.customContextMenuRequested.connect(
            window._build_context_history_menu
        )
        window._ihda_history_view.signal.signal_object.connect(
            window._slot_drop_node_into_hda_view
        )
        window._ihda_history_view.signal.mouse_signal_object.connect(
            window._slot_mouse_move_event_on_houdini
        )
        window.checkBox__hist_search_date.stateChanged.connect(
            window._slot_chk_hist_search_data
        )
        window.comboBox__hist_ihda_node.currentIndexChanged.connect(
            window._slot_hist_ihda_combobox
        )
        window.dateEdit__hist_search_start.dateChanged.connect(
            window._slot_hist_ihda_search_date
        )
        window.dateEdit__hist_search_end.dateChanged.connect(
            window._slot_hist_ihda_search_date
        )
        window.comboBox__search_field_hist.currentIndexChanged.connect(
            window._slot_set_search_hist_field_target
        )
        window.checkBox__casesensitive_hda_hist.stateChanged.connect(
            window._slot_checkbox_hist_hda_item_casesensitive
        )
        from libs.debounce import DebouncedText

        window._history_search_debounce = DebouncedText(
            window._search_filter_regexp_hist_hda_item,
            window,
            immediate=lambda: window._ihda_history_model.rowCount() < 1000,
        )
        window.lineEdit__search_hda_hist.textChanged.connect(
            window._history_search_debounce.submit
        )
        window.lineEdit__search_cate.textChanged.connect(
            window._search_filter_regexp_hda_cate
        )
        window.pushButton__note_save.clicked.connect(
            lambda: window._slot_save_note_tags(choice="note")
        )
        window.pushButton__tag_save.clicked.connect(
            lambda: window._slot_save_note_tags(choice="tag")
        )
        window.checkBox__casesensitive_cate.stateChanged.connect(
            window._slot_checkbox_hda_cate_casesensitive
        )
        window.pushButton__icon_mode.clicked.connect(window._slot_set_view_mode)
        window.pushButton__table_mode.clicked.connect(window._slot_set_view_mode)
        window.actionCategory_Synchronization.triggered.connect(
            window._slot_sync_hou_net_cate
        )
        window.pushButton__cleanup_hda_record.clicked.connect(
            window._slot_cleanup_hda_record
        )
        window.lineEdit__search_record.textChanged.connect(
            window._search_filter_regexp_hda_record
        )
        window.checkBox__record_only_current_hipfile.stateChanged.connect(
            window._slot_record_only_curt_filter
        )
        window.checkBox__record_only_current_ihda.stateChanged.connect(
            window._slot_record_only_curt_filter
        )
        window._ihda_record_view.doubleClicked.connect(
            window._slot_hda_record_double_clicked
        )
        window._ihda_record_view.signal.mouse_signal_object.connect(
            window._slot_mouse_move_event_on_houdini
        )
        window._ihda_record_view.signal.signal_object.connect(
            window._slot_drop_node_into_hda_view
        )
        window.pushButton__hda_inside_node_refresh.clicked.connect(
            window._slot_refresh_inside_nodes
        )
        window.comboBox__hda_inside_node.currentIndexChanged.connect(
            window._slot_search_inside_node_combobox
        )
        window.checkBox__hda_inside_connect_to_view.stateChanged.connect(
            window._slot_inside_only_curt_filter
        )
        window.lineEdit__search_found_hda_inside_node.textChanged.connect(
            window._search_filter_regexp_hda_inside
        )
        window._ihda_inside_view.doubleClicked.connect(
            window._slot_hda_inside_double_clicked
        )
        window.actionNode_Synchronization.triggered.connect(
            window._slot_selection_node_sync
        )
        window.actionDefault.triggered.connect(
            lambda: window._set_theme(theme=Name.default_theme)
        )
        window.actionDark_blue.triggered.connect(
            lambda: window._set_theme(theme=Name.darkblue_theme)
        )
        window.actionHelp.triggered.connect(window._slot_help)
        window.actionOpen_Log_Folder = QtGui.QAction("Open log folder", window)
        window.menuHelp.addAction(window.actionOpen_Log_Folder)
        window.actionOpen_Log_Folder.triggered.connect(
            lambda: ihda_system.IHDASystem.open_folder(dirpath=window._log_dirpath)
        )
        window.actionAbout.triggered.connect(window._slot_about)
        window.actionReset.triggered.connect(window._slot_cfg_reset)
        window.actionOpen_the_hda_directory.triggered.connect(
            lambda: ihda_system.IHDASystem.open_folder(dirpath=window._hda_base_dirpath)
        )
        window.actionQuit.triggered.connect(window.close)
        window.actioniHDA.triggered.connect(
            lambda: window._slot_select_view(inst=window.actioniHDA)
        )
        window.actionVideo_Player.triggered.connect(
            lambda: window._slot_select_view(inst=window.actionVideo_Player)
        )
        window.actionWeb.triggered.connect(
            lambda: window._slot_select_view(inst=window.actionWeb)
        )
        window.actionHistory.triggered.connect(
            lambda: window._slot_select_view(inst=window.actionHistory)
        )
        window.actionPreference.triggered.connect(lambda: window._preference.show())
        window.actionLocal_AI_Models = QtGui.QAction("Local AI Models…", window)
        window.menuTools.insertAction(
            window.menuDownload.menuAction(), window.actionLocal_AI_Models
        )
        window.actionLocal_AI_Models.triggered.connect(window._slot_local_ai_models)
        window.actionSubmit_a_Bug_Report.triggered.connect(
            window._slot_submit_bug_report
        )
        window.actionSubmit_Feedback.triggered.connect(window._slot_submit_feedback)
        window.actionFFmpeg.triggered.connect(window._slot_download_ffmpeg_site)
        window.actionCodec.triggered.connect(window._slot_download_codec_site)
        window.actionDonate.triggered.connect(window._slot_donate)
        window.actionImport_Data.triggered.connect(window._slot_import_data)
        window.actionExport_Data.triggered.connect(window._slot_export_data)
        window.actionDelete_All.triggered.connect(window._slot_delete_all_history)
        window.actionNull.triggered.connect(
            lambda: window._slot_node_connections(inst=window.actionNull)
        )
        window.actionInput.triggered.connect(
            lambda: window._slot_node_connections(inst=window.actionInput)
        )
        window.actionOuput.triggered.connect(
            lambda: window._slot_node_connections(inst=window.actionOuput)
        )
        window.actionBoth.triggered.connect(
            lambda: window._slot_node_connections(inst=window.actionBoth)
        )
        window.actionCleanup.triggered.connect(window._slot_db_cleanup)
        window._make_videoinfo.accepted.connect(window._slot_make_video)
        window._preference.accepted.connect(window._slot_preference)
        window._rename_ihda.accepted.connect(window._slot_hda_name_changed)
        window.doubleSpinBox__zoom.valueChanged.connect(window._slot_zoom_value)
