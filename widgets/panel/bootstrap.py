"""Bootstrap for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations


import logging
import public
import pathlib
from view import ihda_category_view, ihda_list_view, ihda_table_view, ihda_history_view
from view import ihda_record_view, ihda_inside_view
from libs.operation_journal import recover_operations
from libs import note_syntax, log_handler
from libs import ihda_system


class BootstrapMixin:
    def _init_set_basic(self) -> None:
        if not self._preference.is_data_valid:
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="you did not specify a location where data is stored",
            )
            self._preference.show()
        else:
            db_filepath = self._db_filepath
            assert isinstance(db_filepath, pathlib.Path)
            recover_operations(db_filepath.parent)
            db_api = self._services.open_database(db_filepath)
            if not db_api.is_exist_user_id(self._user):
                db_api.insert_users(user_id=self._user, email="anonymous@temp.com")
            db_api.close()

    def _init_set(self) -> None:
        # is ready iHDA
        self._set_is_ready()
        # hide parameters
        self._hide_parms()
        self._assets.reset(
            self._get_hda_data(user_id=self._user, db_filepath=self._db_filepath) or []
        )
        # combobox - search type
        self.comboBox__search_type.addItems(["Name", "Tags", "Type"])
        self.comboBox__search_field_hist.addItems(["Name", "Tags", "Type"])
        # default font
        self.comboBox__search_type.setFont(self._get_default_font())
        self.comboBox__search_field_hist.setFont(self._get_default_font())
        self.comboBox__hist_ihda_node.setFont(self._get_default_font())
        self.comboBox__hda_inside_node.setFont(self._get_default_font())
        self.dateEdit__hist_search_start.setFont(self._get_default_font())
        self.dateEdit__hist_search_end.setFont(self._get_default_font())
        # main default icon size
        self._set_main_default_icon_size()
        self.doubleSpinBox__zoom.setMinimum(public.UISetting.min_zoom_value)
        self.doubleSpinBox__zoom.setMaximum(public.UISetting.max_zoom_value)
        note_syntax.NoteHighLighter(self.textEdit__note)
        note_syntax.NoteHighLighter(self.textEdit__tag)
        self._set_font_properties(
            self.textEdit__note,
            self._get_font_properties(
                public.Name.PreferenceUI.spb_note_font_size,
                public.Name.PreferenceUI.cmb_note_font_style,
            ),
        )
        self._set_font_properties(
            self.textEdit__tag,
            self._get_font_properties(
                public.Name.PreferenceUI.spb_tags_font_size,
                public.Name.PreferenceUI.cmb_tags_font_style,
            ),
        )
        self._set_font_properties(
            self.textBrowser__debug,
            self._get_font_properties(
                public.Name.PreferenceUI.spb_debug_font_size,
                public.Name.PreferenceUI.cmb_debug_font_style,
            ),
        )
        # geometry & config setting
        if public.Paths.json_filepath.exists():
            self._log_handler.log_msg(logging.info, msg="load the configuration file")
            self._ui_settings.load_main_window_geometry()
            self._ui_settings.load_splitter_status()
            self._ui_settings.load_cfg_dict_from_file()
            # theme
            self._ui_settings.set_theme(theme=self._ui_settings.get_theme)
            # stackedwidget & view tool button
            self._slot_select_view(index=self.stackedWidget__whole.currentIndex())
            # stackecdwidget hda infos
            self._slot_stackedwidget_hda_infos()
        else:
            # theme
            self._ui_settings.set_theme(theme=public.Name.default_theme)
        db_api = self._db_api_wrap(self._db_filepath)
        if db_api is not None:
            self._ihda_icons.make_pixmap_ihda_data(
                icon_info=db_api.get_icon_info_by_user(user_id=self._user)
            )
            self._ihda_icons.make_pixmap_cate_data(
                cate_lst=db_api.get_hda_category(user_id=self._user)
            )
            self._ihda_icons.make_pixmap_thumbnail_data(all_data=self._assets.rows)
            self._ihda_icons.make_pixmap_hist_thumbnail_data(
                all_data=db_api.get_thumbnail_by_hda_history(user_id=self._user)
            )
        self._ihda_category_view = ihda_category_view.CategoryView(self)
        self.verticalLayout__category.addWidget(self._ihda_category_view)
        self._init_set_ihda_category_model()
        self._ihda_list_view = ihda_list_view.ListView(self)
        self.verticalLayout__listview.addWidget(self._ihda_list_view)
        self._init_set_ihda_list_model()
        self._ihda_table_view = ihda_table_view.TableView(self)
        self.verticalLayout__tableview.addWidget(self._ihda_table_view)
        self._init_set_ihda_table_model()
        self._ihda_history_view = ihda_history_view.HistoryView(self)
        self.verticalLayout__history.addWidget(self._ihda_history_view)
        self._init_set_ihda_history_model()
        self._ihda_record_view = ihda_record_view.RecordView(self)
        self.verticalLayout__hda_loc_record.addWidget(self._ihda_record_view)
        self._init_set_ihda_record_model()
        self._ihda_inside_view = ihda_inside_view.InsideView(self)
        self.verticalLayout__hda_inside_node.addWidget(self._ihda_inside_view)
        self._init_set_ihda_inside_model()
        self._slot_chk_hist_search_data(self.checkBox__hist_search_date.isChecked())
        self._init_set_video_player()
        self._init_set_web_view()
        self._slot_set_view_mode()
        self._slot_thumbnails()
        self._slot_sync_hou_net_cate()
        self._slot_selection_node_sync()
        self._init_set_first_ihda_item()
        self._set_move_cursor_textedit(self.textBrowser__debug)

    def _signal_func(self) -> None:
        self.stackedWidget__whole.currentChanged.connect(
            self._slot_stackedwidget_whole_curt_changed
        )
        self.pushButton__hda_info.clicked.connect(self._slot_stackedwidget_hda_infos)
        self.pushButton__hda_loc_record.clicked.connect(
            self._slot_stackedwidget_hda_infos
        )
        self.pushButton__hda_inside_node_view.clicked.connect(
            self._slot_stackedwidget_hda_infos
        )
        self.pushButton__zoomin.clicked.connect(self._slot_zoomin)
        self.pushButton__zoomout.clicked.connect(self._slot_zoomout)
        self.pushButton__favorite_node.clicked.connect(self._slot_favorite_node)
        self.pushButton__thumbnail.clicked.connect(self._slot_thumbnails)
        self.pushButton__donate.clicked.connect(self._slot_donate)
        self._ihda_category_view.customContextMenuRequested.connect(
            self._build_context_category_menu
        )
        self._ihda_category_view.selectionModel().selectionChanged.connect(
            self._slot_selected_category
        )
        self._ihda_record_view.customContextMenuRequested.connect(
            self._build_context_record_menu
        )
        self._ihda_record_view.selectionModel().selectionChanged.connect(
            self._slot_selected_record
        )
        self._ihda_inside_view.customContextMenuRequested.connect(
            self._build_context_inside_menu
        )
        self._ihda_list_view.doubleClicked.connect(self._slot_hda_double_clicked)
        # clicked 시그널로만 했을 경우, 마우스 우측클릭 시 갱신이 안되는 문제로인해 selectionModel 추가
        self._ihda_list_view.selectionModel().selectionChanged.connect(
            self._slot_on_hda_item_clicked
        )
        # 마지막 하나 남았을 때 selection이 이미 되어있는 상태라 클릭 시그널 추가함.
        self._ihda_list_view.clicked.connect(self._slot_on_hda_item_clicked)
        self._ihda_list_view.customContextMenuRequested.connect(
            self._build_context_ihda_menu
        )
        self._ihda_list_view.signal.signal_object.connect(
            self._slot_drop_node_into_hda_view
        )
        self._ihda_list_view.signal.mouse_signal_object.connect(
            self._slot_mouse_move_event_on_houdini
        )
        self._ihda_table_view.doubleClicked.connect(self._slot_hda_double_clicked)
        self._ihda_table_view.selectionModel().selectionChanged.connect(
            self._slot_on_hda_item_clicked
        )
        self._ihda_table_view.clicked.connect(self._slot_on_hda_item_clicked)
        self._ihda_table_view.customContextMenuRequested.connect(
            self._build_context_ihda_menu
        )
        self._ihda_table_view.signal.signal_object.connect(
            self._slot_drop_node_into_hda_view
        )
        self._ihda_table_view.signal.mouse_signal_object.connect(
            self._slot_mouse_move_event_on_houdini
        )
        self._ihda_history_view.doubleClicked.connect(self._slot_hda_double_clicked)
        self._ihda_history_view.selectionModel().selectionChanged.connect(
            self._slot_on_hda_item_clicked
        )
        self._ihda_history_view.clicked.connect(self._slot_on_hda_item_clicked)
        self._ihda_history_view.customContextMenuRequested.connect(
            self._build_context_history_menu
        )
        self._ihda_history_view.signal.signal_object.connect(
            self._slot_drop_node_into_hda_view
        )
        self._ihda_history_view.signal.mouse_signal_object.connect(
            self._slot_mouse_move_event_on_houdini
        )
        self.checkBox__hist_search_date.stateChanged.connect(
            self._slot_chk_hist_search_data
        )
        self.comboBox__hist_ihda_node.currentIndexChanged.connect(
            self._slot_hist_ihda_combobox
        )
        self.dateEdit__hist_search_start.dateChanged.connect(
            self._slot_hist_ihda_search_date
        )
        self.dateEdit__hist_search_end.dateChanged.connect(
            self._slot_hist_ihda_search_date
        )
        self.comboBox__search_field_hist.currentIndexChanged.connect(
            self._slot_set_search_hist_field_target
        )
        self.checkBox__casesensitive_hda_hist.stateChanged.connect(
            self._slot_checkbox_hist_hda_item_casesensitive
        )
        from libs.debounce import DebouncedText

        self._history_search_debounce = DebouncedText(
            self._search_filter_regexp_hist_hda_item,
            self,
            immediate=lambda: self._ihda_history_model.rowCount() < 1000,
        )
        self._asset_search_debounce = DebouncedText(
            self._search_filter_regexp_hda_item,
            self,
            immediate=lambda: len(self._assets.rows) < 1000,
        )
        self.lineEdit__search_hda_hist.textChanged.connect(
            self._history_search_debounce.submit
        )
        self.lineEdit__search_hda.textChanged.connect(
            self._asset_search_debounce.submit
        )
        self.lineEdit__search_cate.textChanged.connect(
            self._search_filter_regexp_hda_cate
        )
        self.pushButton__note_save.clicked.connect(
            lambda: self._slot_save_note_tags(choice="note")
        )
        self.pushButton__tag_save.clicked.connect(
            lambda: self._slot_save_note_tags(choice="tag")
        )
        self.comboBox__search_type.currentIndexChanged.connect(
            self._slot_set_search_target
        )
        self.checkBox__casesensitive_cate.stateChanged.connect(
            self._slot_checkbox_hda_cate_casesensitive
        )
        self.checkBox__casesensitive_hda.stateChanged.connect(
            self._slot_checkbox_hda_item_casesensitive
        )
        self.pushButton__icon_mode.clicked.connect(self._slot_set_view_mode)
        self.pushButton__table_mode.clicked.connect(self._slot_set_view_mode)
        self.actionCategory_Synchronization.triggered.connect(
            self._slot_sync_hou_net_cate
        )
        self.pushButton__cleanup_hda_record.clicked.connect(
            self._slot_cleanup_hda_record
        )
        self.lineEdit__search_record.textChanged.connect(
            self._search_filter_regexp_hda_record
        )
        self.checkBox__record_only_current_hipfile.stateChanged.connect(
            self._slot_record_only_curt_filter
        )
        self.checkBox__record_only_current_ihda.stateChanged.connect(
            self._slot_record_only_curt_filter
        )
        self._ihda_record_view.doubleClicked.connect(
            self._slot_hda_record_double_clicked
        )
        self._ihda_record_view.signal.mouse_signal_object.connect(
            self._slot_mouse_move_event_on_houdini
        )
        self._ihda_record_view.signal.signal_object.connect(
            self._slot_drop_node_into_hda_view
        )
        self.pushButton__hda_inside_node_refresh.clicked.connect(
            self._slot_refresh_inside_nodes
        )
        self.comboBox__hda_inside_node.currentIndexChanged.connect(
            self._slot_search_inside_node_combobox
        )
        self.checkBox__hda_inside_connect_to_view.stateChanged.connect(
            self._slot_inside_only_curt_filter
        )
        self.lineEdit__search_found_hda_inside_node.textChanged.connect(
            self._search_filter_regexp_hda_inside
        )
        self._ihda_inside_view.doubleClicked.connect(
            self._slot_hda_inside_double_clicked
        )
        self.actionNode_Synchronization.triggered.connect(
            self._slot_selection_node_sync
        )
        self.actionDefault.triggered.connect(
            lambda: self._set_theme(theme=public.Name.default_theme)
        )
        self.actionDark_blue.triggered.connect(
            lambda: self._set_theme(theme=public.Name.darkblue_theme)
        )
        self.actionHelp.triggered.connect(self._slot_help)
        self.actionAbout.triggered.connect(self._slot_about)
        self.actionReset.triggered.connect(self._slot_cfg_reset)
        self.actionOpen_the_hda_directory.triggered.connect(
            lambda: ihda_system.IHDASystem.open_folder(dirpath=self._hda_base_dirpath)
        )
        self.actionQuit.triggered.connect(self.close)
        self.actioniHDA.triggered.connect(
            lambda: self._slot_select_view(inst=self.actioniHDA)
        )
        self.actionVideo_Player.triggered.connect(
            lambda: self._slot_select_view(inst=self.actionVideo_Player)
        )
        self.actionWeb.triggered.connect(
            lambda: self._slot_select_view(inst=self.actionWeb)
        )
        self.actionHistory.triggered.connect(
            lambda: self._slot_select_view(inst=self.actionHistory)
        )
        self.actionPreference.triggered.connect(lambda: self._preference.show())
        self.actionSubmit_a_Bug_Report.triggered.connect(self._slot_submit_bug_report)
        self.actionSubmit_Feedback.triggered.connect(self._slot_submit_feedback)
        self.actionFFmpeg.triggered.connect(self._slot_download_ffmpeg_site)
        self.actionCodec.triggered.connect(self._slot_download_codec_site)
        self.actionDonate.triggered.connect(self._slot_donate)
        self.actionImport_Data.triggered.connect(self._slot_import_data)
        self.actionExport_Data.triggered.connect(self._slot_export_data)
        self.actionDelete_All.triggered.connect(self._slot_delete_all_history)
        self.actionNull.triggered.connect(
            lambda: self._slot_node_connections(inst=self.actionNull)
        )
        self.actionInput.triggered.connect(
            lambda: self._slot_node_connections(inst=self.actionInput)
        )
        self.actionOuput.triggered.connect(
            lambda: self._slot_node_connections(inst=self.actionOuput)
        )
        self.actionBoth.triggered.connect(
            lambda: self._slot_node_connections(inst=self.actionBoth)
        )
        self.actionCleanup.triggered.connect(self._slot_db_cleanup)
        self._make_videoinfo.buttonBox__confirm.accepted.connect(self._slot_make_video)
        self._preference.buttonBox__confirm.accepted.connect(self._slot_preference)
        self._rename_ihda.buttonBox__confirm.accepted.connect(
            self._slot_hda_name_changed
        )
        self.doubleSpinBox__zoom.valueChanged.connect(self._slot_zoom_value)
