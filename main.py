#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# project name      : individualHDA/main
# create date       : 2020.01.27 11:15
# modify date       : 2020.06.22 21:40
# description       : Individual Houdini Digital Assets

import sys
import logging
from re import compile as re_compile
from imp import reload
from site import addsitedir
from datetime import datetime
from itertools import izip, imap
from bisect import bisect_right, insort_right
from operator import itemgetter

from PySide2 import QtWidgets, QtGui, QtCore

import public

reload(public)

addsitedir(public.Paths.python_packages_dirpath.as_posix())

# third-party modules
import pathlib2
if public.is_windows():
    from pathlib2 import WindowsPath
else:
    from pathlib2 import PosixPath
#

import main_ui
import ui_settings
from view import ihda_category_view, ihda_list_view, ihda_table_view, ihda_history_view
from view import ihda_record_view, ihda_inside_view
from model import ihda_category_model, ihda_category_proxy_model
from model import ihda_list_model, ihda_list_proxy_model
from model import ihda_table_model, ihda_table_proxy_model
from model import ihda_history_model, ihda_history_proxy_model
from model import ihda_record_model, ihda_record_proxy_model
from model import ihda_inside_model, ihda_inside_proxy_model
from libs import houdini_api, loading_indicator, note_syntax, log_handler, ihda_icons
from libs import ffmpeg_api, sqlite3_db_api, dragdrop_overlay, data_stream, ihda_system
from widgets.make_video_info import make_video_info
from widgets.video_player import video_player
from widgets.web_view import web_view
from widgets.preference import preference
from widgets.rename_ihda import rename_ihda
from widgets.detail_view import detail_view

reload(main_ui)
#
reload(ui_settings)
reload(ihda_category_view)
reload(ihda_list_view)
reload(ihda_table_view)
reload(ihda_history_view)
reload(ihda_record_view)
reload(ihda_inside_view)
#
reload(ihda_category_model)
reload(ihda_list_model)
reload(ihda_table_model)
reload(ihda_history_model)
reload(ihda_record_model)
reload(ihda_inside_model)
reload(ihda_category_proxy_model)
reload(ihda_list_proxy_model)
reload(ihda_table_proxy_model)
reload(ihda_history_proxy_model)
reload(ihda_record_proxy_model)
reload(ihda_inside_proxy_model)
#
reload(houdini_api)
reload(loading_indicator)
reload(note_syntax)
reload(log_handler)
reload(ihda_icons)
reload(ffmpeg_api)
reload(sqlite3_db_api)
reload(dragdrop_overlay)
reload(data_stream)
reload(ihda_system)
#
reload(make_video_info)
reload(video_player)
reload(web_view)
reload(preference)
reload(rename_ihda)
reload(detail_view)

try:
    import hou
    import hdefereval
except ImportError:
    pass

sys.setrecursionlimit(500000)

# ex) collections.Counter(p.suffix for p in pathlib2.Path.cwd().iterdir())
# ex) res: Counter({'.md': 2, '.txt': 4, '.pdf: 2, '.py': 1, ...})

__author__ = 'Seongcheol Jeon'
__version__ = public.Value.current_ver
__date__ = '2020.06.23'


class IndividualHDA(QtWidgets.QMainWindow, main_ui.Ui_MainWindow__individualHDA):
    # 한번에 등록할 수 있는 최대 노드 개수
    __MAX_NUM_OF_NODE_REGIST = 30
    # 권장 Houdini 버전 >= 18.0.460
    __RECOMMENDED_HOUDINI_VERSION = 18

    def __init__(self, parent=None):
        super(IndividualHDA, self).__init__(parent)
        self.setupUi(self)
        if public.IS_HOUDINI:
            self.setParent(hou.ui.mainQtWindow(), QtCore.Qt.Window)
        self.setAcceptDrops(True)
        self.centralwidget.setEnabled(False)
        # status
        self.__is_ready = False
        # regex
        self.__regex_squence_str = re_compile(r'\$F4')
        # user id
        self.__user = public.Name.username
        # self.label__logged_id.setText(self.__user)
        # ui_settings
        self.__ui_settings = ui_settings.UISettings(window=self)
        # logging
        self.__log_handler = log_handler.LogHandler(out_stream=self.textBrowser__debug)
        # loading indicator class
        self.__loading = loading_indicator.Overlay(parent=self)
        self.__loading_close()
        # dragdrop indicator class
        self.__dragdrop_overlay = dragdrop_overlay.Overlay(text='', parent=self)
        self.__dragdrop_overlay_close()
        # widgets
        self.__rename_ihda = rename_ihda.RenameIHDA(parent=self)
        self.__preference = preference.Preference(parent=self)
        self.__make_videoinfo = make_video_info.MakeVideoInfo(parent=self)
        self.__video_player = video_player.VideoPlayer(
            ffmpeg_dirpath=self.__preference.ffmpeg_dirpath, parent=self)
        __help_site = hou.helpServerUrl() if public.IS_HOUDINI else None
        self.__web_view = web_view.WebView(help_site=__help_site, parent=self)
        # iHDA icons
        self.__ihda_icons = ihda_icons.IHDAIcons()
        # not have null node context
        # /ch, /shop, /img, /vex    -> null 이 없음.
        self.__not_have_null_node_context_lst = ['/ch', '/shop', '/img', '/vex']
        # shortcut key
        self.__shortcut_copy_key = 'Ctrl+C'
        self.__shortcut_del_key = 'Delete'
        # app properties 초기화
        self.__is_reset_app_properties = False
        # import data 했는 지의 대한 변수
        self.__is_imported_data = False
        #
        # current pane tab
        self.__current_panetab = None
        # iHDA data
        self.__ihda_data = None
        #
        self.__sel_column_idx = None
        self.__sel_parent_lst = list()
        self.__sel_item_text = None
        self.__infoDat = None
        #
        self.__ihda_category_view = None
        self.__ihda_category_model = None
        self.__ihda_category_proxy_model = None
        #
        self.__ihda_list_view = None
        self.__ihda_list_model = None
        self.__ihda_list_proxy_model = None
        #
        self.__ihda_table_view = None
        self.__ihda_table_model = None
        self.__ihda_table_proxy_model = None
        #
        self.__ihda_history_view = None
        self.__ihda_history_model = None
        self.__ihda_history_proxy_model = None
        #
        self.__ihda_record_view = None
        self.__ihda_record_model = None
        self.__ihda_record_proxy_model = None
        #
        self.__ihda_inside_view = None
        self.__ihda_inside_model = None
        self.__ihda_inside_proxy_model = None
        #
        self.__ihda_view_idx = 0
        self.__video_view_idx = 1
        self.__web_view_idx = 2
        self.__hist_view_idx = 3
        #
        self.__hist_curt_item_data = None
        self.__hist_curt_item_id = None
        self.__hist_curt_item_row = None
        self.__hist_curt_item_name = None
        self.__hist_curt_item_filepath = None
        self.__hist_curt_item_field = None
        self.__hist_curt_item_hist_id = None
        self.__hist_curt_item_cate = None
        self.__hist_curt_item_version = None
        #
        self.__curt_hda_item_data = None
        self.__curt_hda_item_id = None
        self.__curt_hda_item_row = None
        self.__curt_hda_item_name = None
        self.__curt_hda_item_cate = None
        self.__curt_hda_item_filepath = None
        self.__curt_hda_item_field = None
        self.__curt_hda_item_version = None
        #
        # initialization basic setting
        self.__init_set_basic()
        # initialization setting
        self.__init_set()
        # signal & slot
        self.__signal_func()
        # initialize select model
        self.__init_select_ihda_category_model()

    def __init_set_basic(self):
        if not self.__preference.is_data_valid:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='you did not specify a location where data is stored')
            self.__preference.show()
        db_filepath = public.SQLite.db_filepath
        assert isinstance(db_filepath, pathlib2.Path)
        if not db_filepath.parent.exists():
            db_filepath.parent.mkdir(parents=True)
            db_api = sqlite3_db_api.SQLite3DatabaseAPI(db_filepath=db_filepath)
            db_api.create_tables()
            is_done = db_api.insert_users(user_id=self.__user, email='anonymous@temp.com')
            if not is_done:
                log_handler.LogHandler.log_msg(method=logging.error, msg='user creation failed')
            return
        db_api = sqlite3_db_api.SQLite3DatabaseAPI(db_filepath=db_filepath)
        if not db_api.is_exist_users_table():
            is_done = db_api.create_tables()
            if not is_done:
                log_handler.LogHandler.log_msg(method=logging.critical, msg='table creation failed')
            else:
                if not db_api.is_exist_user_id(self.__user):
                    is_done = db_api.insert_users(user_id=self.__user, email='anonymous@temp.com')
                    if not is_done:
                        log_handler.LogHandler.log_msg(method=logging.error, msg='user creation failed')

    def __init_set(self):
        # is ready iHDA
        self.__set_is_ready()
        # hide parameters
        self.__hide_parms()
        self.__ihda_data = IndividualHDA.__get_hda_data(user_id=self.__user)
        # combobox - search type
        self.comboBox__search_type.addItems(['Name', 'Tags', 'Type'])
        self.comboBox__search_field_hist.addItems(['Name', 'Tags', 'Type'])
        # default font
        self.comboBox__search_type.setFont(IndividualHDA.__get_default_font())
        self.comboBox__search_field_hist.setFont(IndividualHDA.__get_default_font())
        self.comboBox__hist_ihda_node.setFont(IndividualHDA.__get_default_font())
        self.comboBox__hda_inside_node.setFont(IndividualHDA.__get_default_font())
        self.dateEdit__hist_search_start.setFont(IndividualHDA.__get_default_font())
        self.dateEdit__hist_search_end.setFont(IndividualHDA.__get_default_font())
        # main default icon size
        self.__set_main_default_icon_size()
        #
        self.doubleSpinBox__zoom.setMinimum(public.UISetting.min_zoom_value)
        self.doubleSpinBox__zoom.setMaximum(public.UISetting.max_zoom_value)
        note_syntax.NoteHighLighter(self.textEdit__note)
        note_syntax.NoteHighLighter(self.textEdit__tag)
        IndividualHDA.__set_font_properties(
            self.textEdit__note,
            self.__get_font_properties(
                public.Name.PreferenceUI.spb_note_font_size, public.Name.PreferenceUI.cmb_note_font_style))
        IndividualHDA.__set_font_properties(
            self.textEdit__tag,
            self.__get_font_properties(
                public.Name.PreferenceUI.spb_tags_font_size, public.Name.PreferenceUI.cmb_tags_font_style))
        IndividualHDA.__set_font_properties(
            self.textBrowser__debug,
            self.__get_font_properties(
                public.Name.PreferenceUI.spb_debug_font_size, public.Name.PreferenceUI.cmb_debug_font_style))
        # geometry & config setting
        if public.Paths.json_filepath.exists():
            self.__log_handler.log_msg(logging.info, msg='load the configuration file')
            self.__ui_settings.load_main_window_geometry()
            self.__ui_settings.load_splitter_status()
            self.__ui_settings.load_cfg_dict_from_file()
            # theme
            self.__ui_settings.set_theme(theme=self.__ui_settings.get_theme)
            # stackedwidget & view tool button
            self.__slot_select_view(index=self.stackedWidget__whole.currentIndex())
            # stackecdwidget hda infos
            self.__slot_stackedwidget_hda_infos()
        else:
            # theme
            self.__ui_settings.set_theme(theme=public.Name.default_theme)
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        self.__ihda_icons.make_pixmap_ihda_data(icon_info=db_api.get_icon_info_by_user(user_id=self.__user))
        self.__ihda_icons.make_pixmap_cate_data(cate_lst=db_api.get_hda_category(user_id=self.__user))
        self.__ihda_icons.make_pixmap_thumbnail_data(all_data=self.__ihda_data)
        self.__ihda_icons.make_pixmap_hist_thumbnail_data(
            all_data=db_api.get_thumbnail_by_hda_history(user_id=self.__user))
        self.__ihda_category_view = ihda_category_view.CategoryView(self)
        self.verticalLayout__category.addWidget(self.__ihda_category_view)
        self.__init_set_ihda_category_model()
        self.__ihda_list_view = ihda_list_view.ListView(self)
        self.verticalLayout__listview.addWidget(self.__ihda_list_view)
        self.__init_set_ihda_list_model()
        self.__ihda_table_view = ihda_table_view.TableView(self)
        self.verticalLayout__tableview.addWidget(self.__ihda_table_view)
        self.__init_set_ihda_table_model()
        self.__ihda_history_view = ihda_history_view.HistoryView(self)
        self.verticalLayout__history.addWidget(self.__ihda_history_view)
        self.__init_set_ihda_history_model()
        self.__ihda_record_view = ihda_record_view.RecordView(self)
        self.verticalLayout__hda_loc_record.addWidget(self.__ihda_record_view)
        self.__init_set_ihda_record_model()
        self.__ihda_inside_view = ihda_inside_view.InsideView(self)
        self.verticalLayout__hda_inside_node.addWidget(self.__ihda_inside_view)
        self.__init_set_ihda_inside_model()
        self.__slot_chk_hist_search_data(self.checkBox__hist_search_date.isChecked())
        self.__init_set_video_player()
        self.__init_set_web_view()
        self.__slot_set_view_mode()
        self.__slot_thumbnails()
        self.__slot_sync_hou_net_cate()
        self.__slot_selection_node_sync()
        self.__init_set_first_ihda_item()
        IndividualHDA.__set_move_cursor_textedit(self.textBrowser__debug)

    def closeEvent(self, event):
        if public.IS_HOUDINI:
            # clean event
            self.__loading_close()
            self.__dragdrop_overlay_close()
            IndividualHDA.__remove_event_loop_callback(self.__wrapper_current_panetab)
            IndividualHDA.__remove_event_loop_callback(self.__loading_counter)
            IndividualHDA.__remove_selection_callback(self.__wrapper_selection_callback_item_by_ihda)
            # preference 설정 하지 않아 hda_base_dirpath가 None Type이라 예외처리함.
            try:
                if self.__hda_base_dirpath is None:
                    data_dirpath = self.__preference.get_data_dirpath_from_saved()
                    if data_dirpath is not None:
                        houdini_api.HoudiniAPI.clean_hda_library(data_dirpath)
                else:
                    houdini_api.HoudiniAPI.clean_hda_library(self.__hda_base_dirpath)
            except TypeError as err:
                pass
            self.setParent(None)
        # ui정보 저장을 위해 명시적으로 닫아줘야 함
        self.__video_player.close()
        self.__web_view.close()
        # 앱 속성 초기화를 선택했다면
        if self.__is_reset_app_properties:
            if public.Paths.config_dirpath.exists():
                ihda_system.IHDASystem.remove_dir(dirpath=public.Paths.config_dirpath)
        else:
            self.__ui_settings.save_main_window_geometry()
            self.__ui_settings.save_splitter_status()
            self.__ui_settings.save_cfg_dict_to_file()
        # import data로 데이터를 새로이 가져왔다면
        self.__solve_before_app_terminate_import_data()
        #
        event.accept()

    # SINGAL Function
    def __signal_func(self):
        self.stackedWidget__whole.currentChanged.connect(self.__slot_stackedwidget_whole_curt_changed)
        self.pushButton__hda_info.clicked.connect(self.__slot_stackedwidget_hda_infos)
        self.pushButton__hda_loc_record.clicked.connect(self.__slot_stackedwidget_hda_infos)
        self.pushButton__hda_inside_node_view.clicked.connect(self.__slot_stackedwidget_hda_infos)
        self.pushButton__zoomin.clicked.connect(self.__slot_zoomin)
        self.pushButton__zoomout.clicked.connect(self.__slot_zoomout)
        self.pushButton__favorite_node.clicked.connect(self.__slot_favorite_node)
        self.pushButton__thumbnail.clicked.connect(self.__slot_thumbnails)
        self.pushButton__donate.clicked.connect(IndividualHDA.__slot_donate)
        self.__ihda_category_view.customContextMenuRequested.connect(self.__build_context_category_menu)
        self.__ihda_category_view.selectionModel().selectionChanged.connect(self.__slot_selected_category)
        self.__ihda_record_view.customContextMenuRequested.connect(self.__build_context_record_menu)
        self.__ihda_record_view.selectionModel().selectionChanged.connect(self.__slot_selected_record)
        self.__ihda_inside_view.customContextMenuRequested.connect(self.__build_context_inside_menu)
        self.__ihda_list_view.doubleClicked.connect(self.__slot_hda_double_clicked)
        # clicked 시그널로만 했을 경우, 마우스 우측클릭 시 갱신이 안되는 문제로인해 selectionModel 추가
        self.__ihda_list_view.selectionModel().selectionChanged.connect(self.__slot_on_hda_item_clicked)
        # 마지막 하나 남았을 때 selection이 이미 되어있는 상태라 클릭 시그널 추가함.
        self.__ihda_list_view.clicked.connect(self.__slot_on_hda_item_clicked)
        self.__ihda_list_view.customContextMenuRequested.connect(self.__build_context_ihda_menu)
        self.__ihda_list_view.signal.signal_object.connect(self.__slot_drop_node_into_hda_view)
        self.__ihda_list_view.signal.mouse_signal_object.connect(self.__slot_mouse_move_event_on_houdini)
        self.__ihda_table_view.doubleClicked.connect(self.__slot_hda_double_clicked)
        self.__ihda_table_view.selectionModel().selectionChanged.connect(self.__slot_on_hda_item_clicked)
        self.__ihda_table_view.clicked.connect(self.__slot_on_hda_item_clicked)
        self.__ihda_table_view.customContextMenuRequested.connect(self.__build_context_ihda_menu)
        self.__ihda_table_view.signal.signal_object.connect(self.__slot_drop_node_into_hda_view)
        self.__ihda_table_view.signal.mouse_signal_object.connect(self.__slot_mouse_move_event_on_houdini)
        self.__ihda_history_view.doubleClicked.connect(self.__slot_hda_double_clicked)
        self.__ihda_history_view.selectionModel().selectionChanged.connect(self.__slot_on_hda_item_clicked)
        self.__ihda_history_view.clicked.connect(self.__slot_on_hda_item_clicked)
        self.__ihda_history_view.customContextMenuRequested.connect(self.__build_context_history_menu)
        self.__ihda_history_view.signal.signal_object.connect(self.__slot_drop_node_into_hda_view)
        self.__ihda_history_view.signal.mouse_signal_object.connect(self.__slot_mouse_move_event_on_houdini)
        self.checkBox__hist_search_date.stateChanged.connect(self.__slot_chk_hist_search_data)
        self.comboBox__hist_ihda_node.currentIndexChanged.connect(self.__slot_hist_ihda_combobox)
        self.dateEdit__hist_search_start.dateChanged.connect(self.__slot_hist_ihda_search_date)
        self.dateEdit__hist_search_end.dateChanged.connect(self.__slot_hist_ihda_search_date)
        self.comboBox__search_field_hist.currentIndexChanged.connect(self.__slot_set_search_hist_field_target)
        self.checkBox__casesensitive_hda_hist.stateChanged.connect(
            self.__slot_checkbox_hist_hda_item_casesensitive)
        self.lineEdit__search_hda_hist.textChanged.connect(self.__search_filter_regexp_hist_hda_item)
        self.lineEdit__search_hda.textChanged.connect(self.__search_filter_regexp_hda_item)
        self.lineEdit__search_cate.textChanged.connect(self.__search_filter_regexp_hda_cate)
        self.pushButton__note_save.clicked.connect(lambda: self.__slot_save_note_tags(choice='note'))
        self.pushButton__tag_save.clicked.connect(lambda: self.__slot_save_note_tags(choice='tag'))
        self.comboBox__search_type.currentIndexChanged.connect(self.__slot_set_search_target)
        self.checkBox__casesensitive_cate.stateChanged.connect(
            self.__slot_checkbox_hda_cate_casesensitive)
        self.checkBox__casesensitive_hda.stateChanged.connect(
            self.__slot_checkbox_hda_item_casesensitive)
        self.pushButton__icon_mode.clicked.connect(self.__slot_set_view_mode)
        self.pushButton__table_mode.clicked.connect(self.__slot_set_view_mode)
        self.actionCategory_Synchronization.triggered.connect(self.__slot_sync_hou_net_cate)
        self.pushButton__cleanup_hda_record.clicked.connect(self.__slot_cleanup_hda_record)
        self.lineEdit__search_record.textChanged.connect(self.__search_filter_regexp_hda_record)
        self.checkBox__record_only_current_hipfile.stateChanged.connect(self.__slot_record_only_curt_filter)
        self.checkBox__record_only_current_ihda.stateChanged.connect(self.__slot_record_only_curt_filter)
        self.__ihda_record_view.doubleClicked.connect(self.__slot_hda_record_double_clicked)
        self.__ihda_record_view.signal.mouse_signal_object.connect(self.__slot_mouse_move_event_on_houdini)
        self.__ihda_record_view.signal.signal_object.connect(self.__slot_drop_node_into_hda_view)
        self.pushButton__hda_inside_node_refresh.clicked.connect(self.__slot_refresh_inside_nodes)
        self.comboBox__hda_inside_node.currentIndexChanged.connect(self.__slot_search_inside_node_combobox)
        self.checkBox__hda_inside_connect_to_view.stateChanged.connect(self.__slot_inside_only_curt_filter)
        self.lineEdit__search_found_hda_inside_node.textChanged.connect(self.__search_filter_regexp_hda_inside)
        self.__ihda_inside_view.doubleClicked.connect(self.__slot_hda_inside_double_clicked)
        self.actionNode_Synchronization.triggered.connect(self.__slot_selection_node_sync)
        self.actionDefault.triggered.connect(lambda: self.__set_theme(theme=public.Name.default_theme))
        self.actionDark_blue.triggered.connect(lambda: self.__set_theme(theme=public.Name.darkblue_theme))
        self.actionHelp.triggered.connect(self.__slot_help)
        self.actionAbout.triggered.connect(self.__slot_about)
        self.actionReset.triggered.connect(self.__slot_cfg_reset)
        self.actionOpen_the_hda_directory.triggered.connect(
            lambda: ihda_system.IHDASystem.open_folder(dirpath=self.__hda_base_dirpath))
        self.actionQuit.triggered.connect(self.close)
        self.actioniHDA.triggered.connect(lambda: self.__slot_select_view(inst=self.actioniHDA))
        self.actionVideo_Player.triggered.connect(lambda: self.__slot_select_view(inst=self.actionVideo_Player))
        self.actionWeb.triggered.connect(lambda: self.__slot_select_view(inst=self.actionWeb))
        self.actionHistory.triggered.connect(lambda: self.__slot_select_view(inst=self.actionHistory))
        self.actionPreference.triggered.connect(lambda: self.__preference.show())
        self.actionSubmit_a_Bug_Report.triggered.connect(self.__slot_submit_bug_report)
        self.actionSubmit_Feedback.triggered.connect(self.__slot_submit_feedback)
        self.actionFFmpeg.triggered.connect(IndividualHDA.__slot_download_ffmpeg_site)
        self.actionCodec.triggered.connect(IndividualHDA.__slot_download_codec_site)
        self.actionDonate.triggered.connect(IndividualHDA.__slot_donate)
        self.actionImport_Data.triggered.connect(self.__slot_import_data)
        self.actionExport_Data.triggered.connect(self.__slot_export_data)
        self.actionDelete_All.triggered.connect(self.__slot_delete_all_history)
        self.actionNull.triggered.connect(lambda: self.__slot_node_connections(inst=self.actionNull))
        self.actionInput.triggered.connect(lambda: self.__slot_node_connections(inst=self.actionInput))
        self.actionOuput.triggered.connect(lambda: self.__slot_node_connections(inst=self.actionOuput))
        self.actionBoth.triggered.connect(lambda: self.__slot_node_connections(inst=self.actionBoth))
        self.actionCleanup.triggered.connect(self.__slot_db_cleanup)
        self.__make_videoinfo.buttonBox__confirm.accepted.connect(self.__slot_make_video)
        self.__preference.buttonBox__confirm.accepted.connect(self.__slot_preference)
        self.__rename_ihda.buttonBox__confirm.accepted.connect(self.__slot_hda_name_changed)
        self.doubleSpinBox__zoom.valueChanged.connect(self.__slot_zoom_value)

    @staticmethod
    def __db_api_wrap():
        db_filepath = public.SQLite.db_filepath
        assert isinstance(db_filepath, pathlib2.Path)
        if not db_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.critical,
                msg='the database file does not exist in the path "{0}"'.format(db_filepath.as_posix()))
            return None
        return sqlite3_db_api.SQLite3DatabaseAPI(db_filepath=db_filepath)

    def __init_set_first_ihda_item(self):
        # 처음 시작 시, 첫 번째 노드가 선택되어지도록
        self.__ihda_list_view.setCurrentIndex(self.__ihda_list_proxy_model.index(0, 0, QtCore.QModelIndex()))
        self.__ihda_table_view.setCurrentIndex(self.__ihda_table_proxy_model.index(0, 0, QtCore.QModelIndex()))
        self.__slot_on_hda_item_clicked(self.__ihda_list_proxy_model.index(0, 0, QtCore.QModelIndex()))

    @staticmethod
    def __get_default_font(font_size=None):
        font = QtGui.QFont()
        font.setFamily(public.UISetting.dft_font_style)
        if font_size is None:
            font.setPointSize(public.UISetting.dft_font_size)
        else:
            font.setPointSize(font_size)
        return font

    @staticmethod
    def __set_font_properties(textedit=None, font_property=None):
        font_size, font_style = font_property
        font = QtGui.QFont()
        font.setFamily(font_style)
        font.setPointSize(font_size)
        textedit.setFont(font)

    def __get_font_properties(self, size_key, style_key):
        font_size = public.UISetting.view_font_size
        if public.IS_HOUDINI:
            font_size = hou.ui.scaledSize(int(font_size))
        font_style = public.UISetting.view_font_style
        properties_data = self.__preference.get_properties_data()
        if properties_data is not None:
            if size_key in properties_data:
                font_size = properties_data.get(size_key)
                font_style = properties_data.get(style_key)
        return [font_size, font_style]

    def __get_padding_properties(self, dft_pad, pad_key):
        padding = dft_pad
        properties_data = self.__preference.get_properties_data()
        if properties_data is not None:
            if pad_key in properties_data:
                padding = properties_data.get(pad_key)
        return padding

    def __get_treeview_properties(self):
        icon_size = public.UISetting.treeview_node_icon_size
        properties_data = self.__preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_treeview_icon_size in properties_data:
                icon_size = properties_data.get(public.Name.PreferenceUI.spb_treeview_icon_size)
                if public.IS_HOUDINI:
                    icon_size = hou.ui.scaledSize(int(icon_size))
        return icon_size

    def __get_listview_properties(self, zoom_val):
        size_ratio = IndividualHDA.__get_ratio_icon_size(zoom_val)
        icon_size = public.UISetting.listview_node_icon_size * size_ratio
        thumb_scale = public.UISetting.listview_thumbnail_scale
        properties_data = self.__preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_listview_icon_size in properties_data:
                icon_size = properties_data.get(public.Name.PreferenceUI.spb_listview_icon_size) * size_ratio
                if public.IS_HOUDINI:
                    icon_size = hou.ui.scaledSize(int(icon_size))
                thumb_scale = properties_data.get(public.Name.PreferenceUI.dspb_listview_thumb_scale)
        thumb_size = icon_size * thumb_scale
        return [icon_size, thumb_size]

    def __get_tableview_properties(self, zoom_val):
        size_ratio = IndividualHDA.__get_ratio_icon_size(zoom_val)
        icon_size = public.UISetting.tableview_node_icon_size * size_ratio
        thumb_scale = public.UISetting.tableview_thumbnail_scale
        properties_data = self.__preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_tableview_icon_size in properties_data:
                icon_size = properties_data.get(public.Name.PreferenceUI.spb_tableview_icon_size) * size_ratio
                if public.IS_HOUDINI:
                    icon_size = hou.ui.scaledSize(int(icon_size))
                thumb_scale = properties_data.get(public.Name.PreferenceUI.dspb_tableview_thumb_scale)
        thumb_size = icon_size * thumb_scale
        return [icon_size, thumb_size]

    def __init_set_ihda_category_model(self):
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size, public.Name.PreferenceUI.cmb_view_font_style)
        icon_size = self.__get_treeview_properties()
        padding = self.__get_padding_properties(
            public.UISetting.padding_category, public.Name.PreferenceUI.pad_category)
        #
        self.stackedWidget__category.setCurrentIndex(0)
        # tree model
        self.__ihda_category_model = ihda_category_model.CategoryModel(
            data=IndividualHDA.__get_hda_category(user_id=self.__user), pixmap_cate_data=self.__ihda_icons.pixmap_cate_data,
            font_size=font_size, font_style=font_style, icon_size=icon_size, padding=padding)
        self.__ihda_category_proxy_model = ihda_category_proxy_model.CategoryProxyModel()
        self.__ihda_category_proxy_model.setSourceModel(self.__ihda_category_model)
        self.__ihda_category_view.setModel(self.__ihda_category_proxy_model)
        self.__ihda_category_view.expandAll()

    def __init_set_ihda_list_model(self):
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size, public.Name.PreferenceUI.cmb_view_font_style)
        icon_size, thumb_size = self.__get_listview_properties(self.doubleSpinBox__zoom.value())
        padding = self.__get_padding_properties(
            public.UISetting.padding_listview, public.Name.PreferenceUI.pad_listview)
        # ihda list model
        self.__ihda_list_model = ihda_list_model.ListModel(
            items=self.__ihda_data, pixmap_ihda_data=self.__ihda_icons.pixmap_ihda_data,
            pixmap_thumb_data=self.__ihda_icons.pixmap_thumbnail_data, font_size=font_size,
            font_style=font_style, icon_size=icon_size, thumb_size=thumb_size, padding=padding)
        # proxy ihda list model
        self.__ihda_list_proxy_model = ihda_list_proxy_model.ListProxyModel(
            search_target_idx=self.comboBox__search_type.currentIndex())
        self.__ihda_list_proxy_model.setSourceModel(self.__ihda_list_model)
        self.__ihda_list_view.setModel(self.__ihda_list_proxy_model)
        self.__resizing_listview()

    def __init_set_ihda_table_model(self):
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size, public.Name.PreferenceUI.cmb_view_font_style)
        icon_size, thumb_size = self.__get_tableview_properties(self.doubleSpinBox__zoom.value())
        padding = self.__get_padding_properties(
            public.UISetting.padding_tableview, public.Name.PreferenceUI.pad_tableview)
        # table model
        self.__ihda_table_model = ihda_table_model.TableModel(
            items=self.__ihda_data, pixmap_ihda_data=self.__ihda_icons.pixmap_ihda_data,
            pixmap_thumb_data=self.__ihda_icons.pixmap_thumbnail_data,
            font_size=font_size, font_style=font_style, icon_size=icon_size, thumb_size=thumb_size)
        # proxy table model
        self.__ihda_table_proxy_model = ihda_table_proxy_model.TableProxyModel(
            search_target_idx=self.comboBox__search_type.currentIndex())
        self.__ihda_table_proxy_model.setSourceModel(self.__ihda_table_model)
        self.__ihda_table_view.setModel(self.__ihda_table_proxy_model)
        self.__ihda_table_view.setColumnWidth(0, 250)
        self.__ihda_table_view.setColumnWidth(1, 130)
        self.__ihda_table_view.setColumnWidth(2, 10)
        self.__ihda_table_view.setColumnWidth(3, 60)
        self.__ihda_table_view.setColumnWidth(4, 50)
        self.__ihda_table_view.resizeColumnToContents(5)
        self.__ihda_table_view.resizeColumnToContents(6)
        self.__ihda_table_view.resizeColumnToContents(7)
        self.__ihda_table_view.resizeColumnToContents(8)
        if self.__is_show_thumbnail:
            self.__ihda_table_view.verticalHeader().setDefaultSectionSize(thumb_size + padding)
        else:
            self.__ihda_table_view.verticalHeader().setDefaultSectionSize(icon_size + padding)

    def __init_set_ihda_history_model(self):
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size, public.Name.PreferenceUI.cmb_view_font_style)
        icon_size, thumb_size = self.__get_tableview_properties(self.doubleSpinBox__zoom.value())
        padding = self.__get_padding_properties(
            public.UISetting.padding_history, public.Name.PreferenceUI.pad_history)
        # ihda history model
        get_data = IndividualHDA.__get_hda_hist_data(user_id=self.__user)
        self.__ihda_history_model = ihda_history_model.HistoryModel(
            items=get_data, pixmap_ihda_data=self.__ihda_icons.pixmap_ihda_data,
            pixmap_cate_data=self.__ihda_icons.pixmap_cate_data,
            pixmap_hist_thumb_data=self.__ihda_icons.pixmap_hist_thumbnail_data,
            font_size=font_size, font_style=font_style, icon_size=icon_size, thumb_size=thumb_size)
        # proxy history model
        self.__ihda_history_proxy_model = ihda_history_proxy_model.HistoryProxyModel(
            search_target_idx=self.comboBox__search_field_hist.currentIndex())
        self.__ihda_history_proxy_model.setSourceModel(self.__ihda_history_model)
        self.__ihda_history_view.setModel(self.__ihda_history_proxy_model)
        self.__init_set_hist_ihda_combobox()
        self.label__hist_cnt.setText(str(self.__ihda_history_proxy_model.rowCount()))
        self.__ihda_history_view.setColumnWidth(0, 80)
        self.__ihda_history_view.setColumnWidth(1, 255)
        self.__ihda_history_view.setColumnWidth(2, 185)
        self.__ihda_history_view.resizeColumnToContents(3)
        self.__ihda_history_view.resizeColumnToContents(4)
        self.__ihda_history_view.setColumnWidth(5, 80)
        self.__ihda_history_view.setColumnWidth(7, 150)
        self.__ihda_history_view.resizeColumnToContents(9)
        self.__ihda_history_view.resizeColumnToContents(10)
        self.__ihda_history_view.resizeColumnToContents(11)
        self.__ihda_history_view.verticalHeader().setDefaultSectionSize(thumb_size + padding)

    def __init_set_ihda_record_model(self):
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size, public.Name.PreferenceUI.cmb_view_font_style)
        icon_size = self.__get_treeview_properties()
        padding = self.__get_padding_properties(
            public.UISetting.padding_record, public.Name.PreferenceUI.pad_record)
        # tree model
        self.__ihda_record_model = ihda_record_model.RecordModel(
            data=IndividualHDA.__get_hda_loc_record_data(), pixmap_cate_data=self.__ihda_icons.pixmap_cate_data,
            pixmap_ihda_data=self.__ihda_icons.pixmap_ihda_data,
            font_size=font_size, font_style=font_style, icon_size=icon_size, padding=padding)
        self.__ihda_record_proxy_model = ihda_record_proxy_model.RecordProxyModel()
        self.__ihda_record_proxy_model.setSourceModel(self.__ihda_record_model)
        self.__ihda_record_view.setModel(self.__ihda_record_proxy_model)
        self.__ihda_record_view.expandAll()
        # self.__ihda_record_view.setColumnWidth(0, 100)
        self.__ihda_record_view.header().resizeSection(0, 350)
        self.__ihda_record_view.header().resizeSection(1, 100)
        self.__ihda_record_view.header().resizeSection(2, 100)
        self.__ihda_record_view.header().resizeSection(3, 50)
        self.__ihda_record_view.header().resizeSection(6, 100)
        self.__ihda_record_view.header().resizeSection(7, 100)
        self.__ihda_record_view.header().resizeSection(8, 100)
        self.__ihda_record_view.header().resizeSection(9, 100)
        self.__ihda_record_view.header().resizeSection(10, 100)
        self.__ihda_record_view.header().resizeSection(11, 50)
        self.label__loc_record_count.setText(str(self.__ihda_record_proxy_model.get_row_count()))

    def __init_set_ihda_inside_model(self):
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size, public.Name.PreferenceUI.cmb_view_font_style)
        icon_size = self.__get_treeview_properties()
        padding = self.__get_padding_properties(
            public.UISetting.padding_inside, public.Name.PreferenceUI.pad_inside)
        self.__ihda_inside_model = ihda_inside_model.InsideModel(
            data=dict(), pixmap_cate_data=self.__ihda_icons.pixmap_cate_data,
            pixmap_ihda_data=self.__ihda_icons.pixmap_ihda_data, inst_ihda_icon=self.__ihda_icons,
            font_size=font_size, font_style=font_style, icon_size=icon_size, padding=padding)
        self.__ihda_inside_proxy_model = ihda_inside_proxy_model.InsideProxyModel()
        self.__ihda_inside_proxy_model.setSourceModel(self.__ihda_inside_model)
        self.__ihda_inside_view.setModel(self.__ihda_inside_proxy_model)
        self.__ihda_inside_view.expandAll()
        self.__ihda_inside_view.header().resizeSection(0, 350)
        self.__ihda_inside_view.header().resizeSection(1, 100)
        self.__ihda_inside_view.header().resizeSection(2, 120)
        self.__ihda_inside_view.header().resizeSection(3, 50)

    def __init_set_video_player(self):
        self.verticalLayout__video_player.addWidget(self.__video_player)

    def __init_set_web_view(self):
        self.verticalLayout__web_view.addWidget(self.__web_view)

    def __init_select_ihda_category_model(self):
        idx = self.__ihda_category_proxy_model.index(0, 0, QtCore.QModelIndex())
        self.__ihda_category_view.setCurrentIndex(idx)
        self.__slot_selected_category(idx)

    def __init_set_hist_ihda_combobox(self):
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        self.__default_set_hist_ihda_combobox()
        for val_lst in db_api.get_hda_name(user_id=self.__user, with_id=True):
            hkey_id, hda_name = val_lst
            if not db_api.is_exist_hda_history(hda_key_id=hkey_id):
                continue
            self.__set_hist_ihda_to_combobox(hkey_id=hkey_id, hda_name=hda_name)

    def __default_set_hist_ihda_combobox(self):
        self.comboBox__hist_ihda_node.clear()
        root_icon = QtGui.QIcon(self.__ihda_icons.pixmap_cate_data.get(public.Name.Icons.root).scaled(30, 30))
        self.comboBox__hist_ihda_node.addItem(root_icon, 'ALL', -1)
        self.comboBox__hist_ihda_node.setCurrentIndex(0)

    def __init_set_inside_ihda_combobox(self):
        self.__default_set_inside_ihda_combobox()
        ihda_node_lst = self.__ihda_inside_model.get_ihda_node_list()
        if not len(ihda_node_lst):
            return
        for node_info in sorted(ihda_node_lst, key=itemgetter(0)):
            node_name, hda_id, node_path = node_info
            self.__set_inside_ihda_to_combobox(hkey_id=hda_id, hda_name=node_name, node_path=node_path)

    def __default_set_inside_ihda_combobox(self):
        self.comboBox__hda_inside_node.clear()
        root_icon = QtGui.QIcon(self.__ihda_icons.pixmap_cate_data.get(public.Name.Icons.root).scaled(30, 30))
        self.comboBox__hda_inside_node.addItem(root_icon, 'ALL', -1)
        self.comboBox__hda_inside_node.setCurrentIndex(0)

    def __set_hist_ihda_to_combobox(self, hkey_id=None, hda_name=None):
        if hkey_id not in self.__get_all_hist_ihda_combobox_data():
            icon = QtGui.QIcon(self.__ihda_icons.pixmap_ihda_data.get(hkey_id).scaled(30, 30))
            self.comboBox__hist_ihda_node.addItem(icon, hda_name, hkey_id)

    def __set_inside_ihda_to_combobox(self, hkey_id=None, hda_name=None, node_path=None):
        pixmap = self.__ihda_icons.pixmap_ihda_data.get(hkey_id)
        # 만약 iHDA 노드를 삭제해서 pixmap 데이터가 존재하지 않는다면 직접 후디니 icon을 가공하여 가져온다.
        if pixmap is None:
            node = hou.node(node_path)
            if node is None:
                icon_lst = None
            else:
                icon_lst = houdini_api.HoudiniAPI.node_icon_path_lst(node)
            pixmap = self.__ihda_icons.get_houdini_icon(icon_lst=icon_lst)
        icon = QtGui.QIcon(pixmap.scaled(30, 30))
        self.comboBox__hda_inside_node.addItem(icon, hda_name, hkey_id)

    def __get_all_hist_ihda_combobox_data(self):
        return [int(self.comboBox__hist_ihda_node.itemData(i)) for i in range(self.comboBox__hist_ihda_node.count())]

    def __select_hist_ihda_combobox_item(self, hkey_id=None):
        find_idx = self.__find_hist_ihda_combobox_index(hkey_id=hkey_id)
        if find_idx is not None:
            self.comboBox__hist_ihda_node.setCurrentIndex(find_idx)

    def __find_hist_ihda_combobox_index(self, hkey_id=None):
        find_idx = None
        for idx in range(self.comboBox__hist_ihda_node.count()):
            cm_item_hkey_id = int(self.comboBox__hist_ihda_node.itemData(idx))
            if hkey_id == cm_item_hkey_id:
                find_idx = idx
                break
        return find_idx

    def __hide_parms(self):
        self.actionLogin.setVisible(False)
        self.actionLogout.setVisible(False)
        self.actionCreate_Account.setVisible(False)
        self.actionQuit.setVisible(False)
        self.actionUpdate.setVisible(False)
        # user info hide
        self.label__logged_id.setHidden(True)
        self.label__logged_id_pixmap.setHidden(True)

    def __dragdrop_overlay_show(self, text=None, fontsize=None):
        self.__dragdrop_overlay.text = text
        if fontsize is not None:
            self.__dragdrop_overlay.fontsize = 30
        self.__dragdrop_overlay.show()

    def __dragdrop_overlay_close(self):
        self.__dragdrop_overlay.close()

    def __loading_show(self):
        if public.IS_HOUDINI:
            IndividualHDA.__add_event_loop_callback(self.__loading_counter)
        self.__loading.show()

    def __loading_close(self):
        if public.IS_HOUDINI:
            IndividualHDA.__remove_event_loop_callback(self.__loading_counter)
        self.__loading.close()

    def __loading_counter(self):
        self.__loading.counter = 1
        self.__loading.update()

    def __slot_node_connections(self, inst=None):
        if not inst.isChecked():
            inst.setChecked(True)
        lst = [self.actionNull, self.actionInput, self.actionOuput, self.actionBoth]
        for i in lst:
            if i != inst:
                i.setChecked(False)

    def __slot_select_view(self, inst=None, index=None):
        view_idx_lst = [self.__ihda_view_idx, self.__video_view_idx, self.__web_view_idx, self.__hist_view_idx]
        btn_lst = [self.actioniHDA, self.actionVideo_Player, self.actionWeb, self.actionHistory]
        if index is not None:
            inst = btn_lst[index]
        if not inst.isChecked():
            inst.setChecked(True)
        for idx in range(len(btn_lst)):
            btn = btn_lst[idx]
            if btn != inst:
                btn.setChecked(False)
            else:
                view_idx = view_idx_lst[idx]
                self.stackedWidget__whole.setCurrentIndex(view_idx)

    def __get_ihda_data_by_id(self, hda_id=None, key=None):
        item_row = self.__get_hda_id_row_map().get(hda_id)
        if item_row is None:
            return None
        return self.__ihda_data[item_row].get(key)

    @staticmethod
    def __binary_search(data=None, find=None):
        start = 0
        end = len(data) - 1
        while start <= end:
            mid = (start + end) // 2
            if data[mid] == find:
                return mid
            elif data[mid] < find:
                start = mid + 1
            else:
                end = mid - 1
        return None

    def __find_tree_element_model(self, index=None, find_name=''):
        for row in range(0, self.__ihda_category_proxy_model.rowCount(index)):
            child_idx = self.__ihda_category_proxy_model.index(row, 0, index)
            if child_idx.data() == find_name:
                return child_idx
            self.__find_tree_element_model(child_idx)

    def __find_hda_id_by_model_item(self, model_hda=None, find_hda_id=None):
        hda_id_row_map = self.__get_hda_id_row_map()
        find_row = hda_id_row_map.get(find_hda_id)
        if find_row is None:
            return None
        return model_hda.index(find_row, 0, QtCore.QModelIndex())

    def __slot_set_view_mode(self):
        if self.__is_icon_mode:
            self.stackedWidget__hda.setCurrentIndex(0)
        else:
            self.stackedWidget__hda.setCurrentIndex(1)

    @staticmethod
    def __add_event_loop_callback(event_func):
        if not public.IS_HOUDINI:
            return
        if not IndividualHDA.__is_exist_event_callbacks(event_func):
            hou.ui.addEventLoopCallback(event_func)

    @staticmethod
    def __add_selection_callback(event_func):
        if not public.IS_HOUDINI:
            return
        if not IndividualHDA.__is_exist_selection_callbacks(event_func):
            hou.ui.addSelectionCallback(event_func)

    @staticmethod
    def __remove_event_loop_callback(event_func):
        if not public.IS_HOUDINI:
            return
        if IndividualHDA.__is_exist_event_callbacks(event_func):
            hou.ui.removeEventLoopCallback(event_func)

    @staticmethod
    def __remove_selection_callback(event_func):
        if not public.IS_HOUDINI:
            return
        if IndividualHDA.__is_exist_selection_callbacks(event_func):
            hou.ui.removeSelectionCallback(event_func)

    @staticmethod
    def __is_exist_event_callbacks(event_func):
        if not public.IS_HOUDINI:
            return
        return event_func in hou.ui.eventLoopCallbacks()

    @staticmethod
    def __is_exist_selection_callbacks(event_func):
        if not public.IS_HOUDINI:
            return
        return event_func in hou.ui.selectionCallbacks()

    def __slot_stackedwidget_whole_curt_changed(self, index):
        # 만약 iHDA 뷰가 아닌데 category synchronize가 활성화 상태면, 이벤트 콜백 삭제
        if (index != self.__ihda_view_idx) and (self.actionCategory_Synchronization.isChecked()):
            IndividualHDA.__remove_event_loop_callback(self.__wrapper_current_panetab)
        else:
            if self.actionCategory_Synchronization.isChecked():
                IndividualHDA.__add_event_loop_callback(self.__wrapper_current_panetab)

    def __slot_sync_hou_net_cate(self):
        if not public.IS_HOUDINI:
            return
        if self.actionCategory_Synchronization.isChecked():
            if self.stackedWidget__whole.currentIndex() == self.__ihda_view_idx:
                IndividualHDA.__add_event_loop_callback(self.__wrapper_current_panetab)
            log_handler.LogHandler.log_msg(method=logging.debug, msg='enable category synchronization')
        else:
            IndividualHDA.__remove_event_loop_callback(self.__wrapper_current_panetab)
            log_handler.LogHandler.log_msg(method=logging.info, msg='disable category synchronization')

    def __slot_selection_node_sync(self):
        if not public.IS_HOUDINI:
            return
        if self.actionNode_Synchronization.isChecked():
            IndividualHDA.__add_selection_callback(self.__wrapper_selection_callback_item_by_ihda)
            log_handler.LogHandler.log_msg(method=logging.debug, msg='enable selection node synchronization')
        else:
            IndividualHDA.__remove_selection_callback(self.__wrapper_selection_callback_item_by_ihda)
            log_handler.LogHandler.log_msg(method=logging.info, msg='disable selection node synchronization')

    def __wrapper_current_panetab(self):
        IndividualHDA.__wrapper_execute_deferred(self.__set_current_panetab)

    def __set_current_panetab(self):
        desk = hou.ui.curDesktop()
        panetab = desk.paneTabUnderCursor()
        self.__current_panetab = panetab
        if self.__current_panetab is None:
            return
        net_type_name = houdini_api.HoudiniAPI.current_network_editor_type_name(
            network_editor=self.__current_panetab,
            not_have_null_node_context_lst=self.__not_have_null_node_context_lst)
        if net_type_name is None:
            return
        self.__select_category(category=net_type_name)

    def __wrapper_selection_callback_item_by_ihda(self, selection):
        # 굳이 execute deferred함수를 쓸 이유가 없다. 오히려 이 함수를 쓰게되면 딜레이가 생긴다.
        # IndividualHDA.__wrapper_execute_deferred(lambda: self.__set_selection_callback_item_by_ihda(selection))
        self.__set_selection_callback_item_by_ihda(selection)

    def __set_selection_callback_item_by_ihda(self, selection):
        if not len(selection):
            return
        node = selection[0]
        find_hda_info = houdini_api.HoudiniAPI.get_hda_info_by_selection_node(node=node)
        if find_hda_info is None:
            return
        self.__select_model_item_by_hda_id(hda_id=find_hda_info.get(public.Key.Comment.ihda_id))

    def __is_valid_network_category(self, network_editor=None, category=None, hda_name=None):
        net_category = houdini_api.HoudiniAPI.current_network_editor_type_name(
            network_editor, self.__not_have_null_node_context_lst)
        if net_category == category:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning, msg='current network category: {0}'.format(net_category))
        log_handler.LogHandler.log_msg(
            method=logging.warning, msg='"{0}" iHDA node category: {1}'.format(hda_name, category))
        return False

    @QtCore.Slot(bool)
    def __slot_checkbox_hda_cate_casesensitive(self, idx):
        self.__search_filter_regexp_hda_cate(self.lineEdit__search_cate.text().strip())

    @QtCore.Slot(bool)
    def __slot_checkbox_hda_item_casesensitive(self, idx):
        self.__search_filter_regexp_hda_item(self.lineEdit__search_hda.text().strip())

    @QtCore.Slot(bool)
    def __slot_checkbox_hist_hda_item_casesensitive(self, idx):
        self.__search_filter_regexp_hist_hda_item(self.lineEdit__search_hda_hist.text().strip())

    @QtCore.Slot(int)
    def __slot_set_search_target(self, idx):
        self.__ihda_list_proxy_model.set_search_target_idx(idx)
        self.__ihda_table_proxy_model.set_search_target_idx(idx)

    @QtCore.Slot(int)
    def __slot_set_search_hist_field_target(self, idx):
        self.__ihda_history_proxy_model.set_search_target_idx(idx)

    @QtCore.Slot(bool)
    def __slot_chk_hist_search_data(self, state):
        self.dateEdit__hist_search_start.setEnabled(state)
        self.dateEdit__hist_search_end.setEnabled(state)
        self.label__join_str.setEnabled(state)
        self.__slot_hist_ihda_search_date()

    @QtCore.Slot(int)
    def __slot_hist_ihda_combobox(self, idx):
        self.lineEdit__search_hda_hist.clear()
        hda_id = self.comboBox__hist_ihda_node.itemData(idx)
        self.__ihda_history_proxy_model.set_hda_id(hda_id=hda_id)
        self.label__hist_cnt.setText(str(self.__ihda_history_proxy_model.rowCount()))

    @QtCore.Slot(int)
    def __slot_search_inside_node_combobox(self, idx):
        hda_id = self.comboBox__hda_inside_node.itemData(idx)
        self.__ihda_inside_proxy_model.set_filter_attribute(hda_id=hda_id)
        self.label__found_hda_inside_hipfile_count.setText(str(self.__ihda_inside_proxy_model.get_row_count()))
        self.__ihda_inside_view.expandAll()

    def __slot_hist_ihda_search_date(self, *args):
        datetime_lst = list()
        if self.checkBox__hist_search_date.isChecked():
            date_start = self.dateEdit__hist_search_start.date()
            date_end = self.dateEdit__hist_search_end.date()
            if date_start > date_end:
                log_handler.LogHandler.log_msg(
                    method=logging.warning, msg='search date setting is wrong. please check and try again')
                return
            datetime_lst = [
                date_start.toString(public.Value.qt_date_fmt_str),
                date_end.toString(public.Value.qt_date_fmt_str)]
            log_handler.LogHandler.log_msg(
                method=logging.info,
                msg='historical data in the range of "{0} ~ {1}" were retrieved'.format(*datetime_lst))
        self.__ihda_history_proxy_model.set_datetime(datetime_lst=datetime_lst)
        self.label__hist_cnt.setText(str(self.__ihda_history_proxy_model.rowCount()))

    @staticmethod
    def __wrapper_execute_deferred(func):
        hdefereval.executeDeferred(func)

    @QtCore.Slot(object)
    def __slot_mouse_move_event_on_houdini(self, drop_data):
        # [[id, name, category, filename, dirpath, icon_lst, tag_lst], [...], ...]
        if not public.IS_HOUDINI:
            log_handler.LogHandler.log_msg(method=logging.warning, msg='please drag from houdini')
            self.__dragdrop_overlay_close()
            return
        drop_action, model_data_lst = drop_data
        assert isinstance(model_data_lst, list)
        if drop_action != QtCore.Qt.IgnoreAction:
            self.__dragdrop_overlay_close()
            return
        network_editor = houdini_api.HoudiniAPI.find_network_editor_by_cursor()
        if network_editor is None:
            log_handler.LogHandler.log_msg(method=logging.error, msg='houdini network not found')
            self.__dragdrop_overlay_close()
            return
        total_node_cnt = len(model_data_lst)
        if not total_node_cnt:
            log_handler.LogHandler.log_msg(method=logging.error, msg='imported iHDA data is empty')
            self.__dragdrop_overlay_close()
            return
        # 노드 개수가 30개를 초과하면 종료
        if total_node_cnt > IndividualHDA.__MAX_NUM_OF_NODE_REGIST:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setWindowTitle('Import iHDA Node')
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText('Too many nodes to import')
            msgbox.setDetailedText('''
            Please bring no more than {0} items.
            Total Nodes: {1}
            '''.format(IndividualHDA.__MAX_NUM_OF_NODE_REGIST, total_node_cnt))
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            _ = msgbox.exec_()
            return
        # 만약 등록하려는 노드 개수가 10개를 초과하면 등록할 것인지 메시지박스를 띄운다.
        if total_node_cnt > public.Value.warning_num_of_node_regist:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setWindowTitle('Import iHDA Node')
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText('''
            The number of iHDA nodes you are trying to import exceeds {0}.
            Should I bring it though?
            
            NOTE: Registering a large number of nodes at a time may make the Houdini appear to be stationary.
            But it didn't stop, so please wait a little longer.
            '''.format(public.Value.warning_num_of_node_regist))
            msgbox.setDetailedText('Total Nodes: {0}'.format(total_node_cnt))
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            reply = msgbox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg='importing iHDA nodes was canceled')
                self.__dragdrop_overlay_close()
                return
        # 기존에 선택된 노드가 존재한다면 모두 선택 해제
        old_selected_nodes = houdini_api.HoudiniAPI.get_selected_nodes()
        if old_selected_nodes is not None:
            houdini_api.HoudiniAPI.all_clear_selected(node=old_selected_nodes[0])
        # node 위치 옵셋 값
        offset_pos = hou.Vector2((1, -1))
        network_editor.setIsCurrentTab()
        cursor_pos = houdini_api.HoudiniAPI.get_cursor_pos(network_editor=network_editor)
        IndividualHDA.__wrapper_execute_deferred(lambda: self.__create_ihda_node_in_houdini(
            model_data_lst=model_data_lst, network_editor=network_editor, cursor_pos=cursor_pos,
            offset_pos=offset_pos, total_node_cnt=total_node_cnt))

    def __create_ihda_node_in_houdini(
            self, model_data_lst=None, network_editor=None, cursor_pos=None, offset_pos=None,
            total_node_cnt=None):
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        num_count = 0
        #
        for node_cnt, model_data in enumerate(model_data_lst):
            model_data = eval(model_data)
            # record data 인지 확인하는 변수
            is_record_data = model_data.get(public.Key.Record.record_id)
            # 만약 히스토리에서 드래그&드롭 하는 것이라면
            if self.__is_ihda_history_view:
                hda_cate = model_data.get(public.Key.History.node_category)
                hda_id = model_data.get(public.Key.History.hda_id)
                hda_name = model_data.get(public.Key.History.org_hda_name)
                hda_ver = model_data.get(public.Key.History.version)
                hda_dirpath = model_data.get(public.Key.History.ihda_dirpath)
                hda_filename = model_data.get(public.Key.History.ihda_filename)
                hda_license = model_data.get(public.Key.History.hda_license)
                hda_note = db_api.get_hda_note_history_most_recent_by_ver(hda_key_id=hda_id, version=hda_ver)
                item_row = model_data.get(public.Key.History.item_row)
            else:
                # record data가 아니라면
                if is_record_data is None:
                    hda_cate = model_data.get(public.Key.hda_cate)
                    hda_id = model_data.get(public.Key.hda_id)
                    hda_name = model_data.get(public.Key.hda_name)
                    hda_ver = model_data.get(public.Key.hda_version)
                    hda_dirpath = model_data.get(public.Key.hda_dirpath)
                    hda_filename = model_data.get(public.Key.hda_filename)
                    hda_license = model_data.get(public.Key.hda_license)
                    hda_note = db_api.get_note_info(hda_key_id=hda_id)
                    item_row = model_data.get(public.Key.item_row)
                # record data라면
                else:
                    hda_cate = model_data.get(public.Key.Record.node_cate)
                    hda_id = model_data.get(public.Key.Record.hda_id)
                    hda_name = model_data.get(public.Key.Record.org_node_name)
                    hda_ver = model_data.get(public.Key.Record.node_ver)
                    hda_dirpath = model_data.get(public.Key.Record.hda_dirpath)
                    hda_filename = model_data.get(public.Key.Record.hda_filename)
                    #
                    # 라이센스는 hda data 의 것을 가져와야 함. 왜냐면, loc data의 라이센스는 ihda노드를 후디니로
                    # 내보낼때 그 당시의 후디니 라이센스이기 때문이다. 허나 hda 데이터나 hda history 데이터는
                    # 후디니 노드를 hda로 만들 때의 후디니 라이센스라서 hda도 논커머셜인지 커머셜인지 결정 됨.
                    hda_license = db_api.get_hist_hda_license(
                        hda_key_id=hda_id, version=hda_ver, user_id=self.__user)
                    hda_note = db_api.get_hda_note_history_most_recent_by_ver(
                        hda_key_id=hda_id, version=hda_ver)
                    item_row = self.__get_ihda_data_by_id(hda_id=hda_id, key=public.Key.item_row)
            #
            hda_filepath = hda_dirpath / hda_filename
            assert isinstance(hda_dirpath, pathlib2.Path)
            # DB에는 존재하지만 지정된 곳에 파일이 존재하지 않는다면
            if not hda_filepath.exists():
                log_handler.LogHandler.log_msg(
                    method=logging.critical,
                    msg='[{0}/{1}] "{2} (v{3})" iHDA file does not exist'.format(
                        node_cnt+1, total_node_cnt, hda_name, hda_ver))
                continue
            # item의 row (model에서 셋팅해 놓았음)
            if self.__is_ihda_history_view:
                self.__hist_curt_item_row = item_row
                self.__hist_curt_item_filepath = hda_filepath
                self.__hist_curt_item_name = hda_name
                self.__hist_curt_item_id = hda_id
                self.__hist_curt_item_data = model_data
                self.__hist_curt_item_cate = hda_cate
                self.__hist_curt_item_hist_id = model_data.get(public.Key.History.hist_id)
                self.__hist_curt_item_version = hda_ver
            else:
                self.__curt_hda_item_row = item_row
                self.__curt_hda_item_filepath = hda_filepath
                self.__curt_hda_item_name = hda_name
                self.__curt_hda_item_id = hda_id
                self.__curt_hda_item_data = model_data
                self.__curt_hda_item_cate = hda_cate
                self.__curt_hda_item_version = hda_ver
            # 현재 Houdini 라이센스
            curt_houdini_license = houdini_api.HoudiniAPI.current_houdini_license()
            # 후디니는 commercial라이센스인데 iHDA는 아니라면
            if not IndividualHDA.__ihda_license_check(hda_license=hda_license):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='[{0}/{1}] houdini license and "{2} (v{3})" iHDA license are different'.format(
                        node_cnt+1, total_node_cnt, hda_name, hda_ver))
                msgbox = QtWidgets.QMessageBox(self)
                msgbox.setFont(IndividualHDA.__get_default_font())
                msgbox.setWindowTitle('Import iHDA Node')
                msgbox.setIcon(QtWidgets.QMessageBox.Warning)
                msgbox.setText('''
                [{0}/{1}] Imported "{2} (v{3})" iHDA are not commercial.
                When I import it into the current HIP file, the HIP file also becomes non-commercial.
                Should I bring it though?'''.format(node_cnt+1, total_node_cnt, hda_name, hda_ver))
                msgbox.setDetailedText('''
                Current HIP File License: {0}
                Current iHDA Node License: {1}
                '''.format(curt_houdini_license, hda_license))
                # msgbox.resize(msgbox.sizeHint())
                msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                reply = msgbox.exec_()
                if reply == QtWidgets.QMessageBox.No:
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg='[{0}/{1}] importing "{2} (v{3})" iHDA nodes was canceled'.format(
                            node_cnt+1, total_node_cnt, hda_name, hda_ver))
                    continue
            if not self.__is_valid_network_category(
                    network_editor=network_editor, category=hda_cate, hda_name=hda_name):
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] "{2} (v{3})" iHDA node\'s category and current network category are different'.format(
                        node_cnt+1, total_node_cnt, hda_name, hda_ver))
                continue
            node = self.__import_hda_into_houdini(
                parent_node=hou.node(network_editor.pwd().path()),
                position=cursor_pos+(offset_pos*num_count), data=model_data)
            if node is None:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] failed to get "{2} (v{3})" iHDA node'.format(
                        node_cnt+1, total_node_cnt, hda_name, hda_ver))
                continue
            db_api.update_load_count(hda_key_id=hda_id)
            # 서브넷인 경우 unpack할 수 있기때문에 unpack 함수 위에 둬야 한다.
            pnode_path = node.parent().path()
            node_type = houdini_api.HoudiniAPI.node_type_name(node)
            node_cate = houdini_api.HoudiniAPI.node_category_type_name(node)
            show_comments = self.actionComment.isChecked()
            IndividualHDA.__hda_info_to_node_comment(
                node=node, hda_name=hda_name, hda_ver=hda_ver, hda_id=hda_id, show_comments=show_comments,
                is_unpack_subnet=self.actionUnpack_Subnet.isChecked())
            # node connections
            info_id = db_api.get_hou_node_info_id(hda_key_id=hda_id)
            node_input_connections = db_api.get_houdini_node_input_connect_info(info_id=info_id)
            node_output_connections = db_api.get_houdini_node_output_connect_info(info_id=info_id)
            self.__set_node_connections(
                node=node, input_connectors=node_input_connections, output_connectors=node_output_connections)
            node.setSelected(True, clear_all_selected=False)
            if self.actionUnpack_Subnet.isChecked() and houdini_api.HoudiniAPI.is_subnet_nodetype(node):
                self.__extract_subnet(node=node, note_contents=hda_note, hda_name=hda_name)
            else:
                # subnet을 풀지 않았다면
                # iHDA 노트 내용을 Houdini Sticky Note로
                self.__create_sticky_netbox(
                    node=node.parent(), note_contents=hda_note, hda_name=hda_name, items=(node,))
            hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
            hip_dirpath = hip_filepath.parent
            hip_filename = hip_filepath.name
            hou_version = houdini_api.HoudiniAPI.current_houdini_version()
            declare_os = public.platform_system()
            frinfo = houdini_api.HoudiniAPI.frame_info()
            is_hda_node_loc_record = db_api.insert_hda_node_location_record(
                hda_key_id=hda_id, hip_filename=hip_filename, hip_dirpath=hip_dirpath,
                hda_filename=hda_filename, hda_dirpath=hda_dirpath, parent_node_path=pnode_path,
                node_type=node_type, node_cate=node_cate, node_name=hda_name, node_ver=hda_ver,
                hou_version=hou_version, hou_license=curt_houdini_license, operating_sys=declare_os,
                sf=frinfo[0], ef=frinfo[1], fps=frinfo[2])
            if is_hda_node_loc_record is None:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] cannot enter "{2} (v{3})" iHDA node information'.format(
                        node_cnt+1, total_node_cnt, hda_name, hda_ver))
                self.__dragdrop_overlay_close()
                return
            last_hda_record_id = db_api.get_last_insert_id
            val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
            record_data = [last_hda_record_id, hda_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
                           pnode_path, node_type, node_cate, hda_name, hda_ver,
                           hou_version, curt_houdini_license, declare_os, frinfo[0], frinfo[1], frinfo[2],
                           val_datetime, val_datetime]
            self.__insert_hda_node_loc_record(record_data=record_data)
            log_handler.LogHandler.log_msg(
                method=logging.debug,
                msg='[{0}/{1}] imported "{2} (v{3})" iHDA node'.format(node_cnt+1, total_node_cnt, hda_name, hda_ver))
            num_count += 1
        self.__dragdrop_overlay_close()

    def __insert_hda_node_loc_record(self, record_data=None):
        key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_record_key_lst()
        assert len(key_lst) == len(record_data)
        rdata = dict(izip(key_lst, record_data))
        hip_dpath = rdata.get(public.Key.Record.hip_dirpath).as_posix()
        hip_fname = rdata.get(public.Key.Record.hip_filename)
        hda_dpath = rdata.get(public.Key.Record.hda_dirpath)
        hda_fname = rdata.get(public.Key.Record.hda_filename)
        pnode_path = rdata.get(public.Key.Record.parent_node_path)
        node_name = rdata.get(public.Key.Record.node_name)
        node_ver = rdata.get(public.Key.Record.node_ver)
        node_type = rdata.get(public.Key.Record.node_type)
        node_cate = rdata.get(public.Key.Record.node_cate)
        record_id = rdata.get(public.Key.Record.record_id)
        hda_id = rdata.get(public.Key.Record.hda_id)
        hou_ver = rdata.get(public.Key.Record.houdini_version)
        hou_lic = rdata.get(public.Key.Record.houdini_license)
        curt_os = rdata.get(public.Key.Record.operating_system)
        sf = rdata.get(public.Key.Record.sf)
        ef = rdata.get(public.Key.Record.ef)
        fps = rdata.get(public.Key.Record.fps)
        ctime = rdata.get(public.Key.Record.ctime)
        mtime = rdata.get(public.Key.Record.mtime)
        # db_api 함수와 동일해야 한다. 그래서 노드 이름 변경함.
        node_name_with_ver = '{0} (v{1})'.format(node_name, node_ver)
        new_data = {
            public.Type.root: {
                hip_dpath: {
                    hip_fname: {
                        # 2차원 배열이라는 것에 주의
                        pnode_path: [[
                            record_id, hda_id, node_name_with_ver, node_type, node_cate, node_ver,
                            ctime, mtime, pathlib2.Path(hip_dpath), hip_fname, hda_dpath, hda_fname,
                            hou_ver, hou_lic, curt_os, sf, ef, fps, node_name
                        ]]
                    }
                }
            }
        }
        self.__add_record_item(data=new_data)
        self.label__loc_record_count.setText(str(self.__ihda_record_proxy_model.get_row_count()))

    @staticmethod
    def __hda_note_to_sticky_note(node=None, note_contents=None):
        if (note_contents is None) or (not len(note_contents)):
            return None
        sticky = houdini_api.HoudiniAPI.create_sticky_note(node=node, contents=note_contents)
        return sticky

    @staticmethod
    def __hda_info_to_node_comment(
            node=None, hda_name=None, hda_ver=None, hda_id=None, show_comments=False, is_unpack_subnet=False):
        ihda_name_key = public.Key.Comment.ihda_name
        ihda_ver_key = public.Key.Comment.ihda_version
        ihda_id_key = public.Key.Comment.ihda_id
        contents = '{0}: {1}\n{2}: {3}\n{4}: {5}'.format(
            ihda_name_key, hda_name, ihda_ver_key, hda_ver, ihda_id_key, hda_id)
        houdini_api.HoudiniAPI.set_node_comment(
            node=node, contents=contents, show_comments=show_comments, is_unpack_subnet=is_unpack_subnet)

    @QtCore.Slot(object)
    def __slot_drop_node_into_hda_view(self, node_lst):
        if not public.IS_HOUDINI:
            log_handler.LogHandler.log_msg(method=logging.warning, msg='houdini is not running')
            return
        if not self.__preference.is_valid_data_dirpath():
            log_handler.LogHandler.log_msg(
                method=logging.critical,
                msg='folder where the data is stored has not been set or the folder does not exist')
            self.__preference.show()
            return
        total_node_cnt = len(node_lst)
        # 만약 한번에 등록하려는 노드 개수가 30개를 초과하면 종료
        if total_node_cnt > IndividualHDA.__MAX_NUM_OF_NODE_REGIST:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setWindowTitle('iHDA Node Registration')
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText('Too many nodes to register')
            msgbox.setDetailedText('''
Please register less than {0} items.
Total Nodes: {1}
            '''.format(IndividualHDA.__MAX_NUM_OF_NODE_REGIST, total_node_cnt))
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            _ = msgbox.exec_()
            return
        # 만약 등록하려는 노드 개수가 10개를 초과하면 등록할 것인지 메시지박스를 띄운다.
        if total_node_cnt > public.Value.warning_num_of_node_regist:
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setWindowTitle('iHDA Node Registration')
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText('''
The number of nodes you are trying to register exceeds {0}.
Should I proceed with registration?

NOTE: Registering a large number of nodes at a time may make the Houdini appear to be stationary.
But it didn't stop, so please wait a little longer.
            '''.format(public.Value.warning_num_of_node_regist))
            msgbox.setDetailedText('Total Nodes: {0}'.format(total_node_cnt))
            # msgbox.resize(msgbox.sizeHint())
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            reply = msgbox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg='Node registration has been canceled')
                return
        self.__dragdrop_overlay_show(text='Create iHDA node\nPlease wait...')
        IndividualHDA.__wrapper_execute_deferred(
            lambda: self.__make_houdini_node_to_ihda_node(
                node_lst=node_lst, total_node_cnt=total_node_cnt))

    def __make_houdini_node_to_ihda_node(self, node_lst=None, total_node_cnt=None):
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        is_declare = False
        for node_cnt, node_dat in enumerate(node_lst):
            node_path = node_dat.data()
            node = hou.node(node_path)
            if node is None:
                continue
            node_name = node.name()
            # 유효한 후디니 노드인지
            if not houdini_api.HoudiniAPI.is_valid_node(node=node):
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='[{0}/{1}] "{2}" node cannot be registered. check the error message'.format(
                        node_cnt+1, total_node_cnt, node_name))
                continue
            # 유효한 후디니 노드 이름인지
            if (not houdini_api.HoudiniAPI.is_valid_node_name(node=node, verbose=False)) or \
                    (node_name.startswith('_')) or (node_name[0].isdigit()):
                # 자동 이름 변경이 활성화되어있다면
                if self.actionAutomatic_Name_Change.isChecked():
                    new_node_name = '{0}_{1}'.format(public.Name.hda_prefix_str.lower(), node_name)
                    # 노드 이름 변경
                    node.setName(new_node_name, unique_name=True)
                    node_path = node.path()
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg='[{0}/{1}] (automatically rename) "{2}" >>>>> "{3}"'.format(
                            node_cnt+1, total_node_cnt, node_name, new_node_name))
                else:
                    if not houdini_api.HoudiniAPI.is_valid_node_name(node=node, verbose=True):
                        log_handler.LogHandler.log_msg(
                            method=logging.error,
                            msg='[{0}/{1}] "{2}" node cannot be registered. check the error message'.format(
                                node_cnt + 1, total_node_cnt, node_name))
                        continue
                    # 현재 후디니버전 18.0.429 에서 노드이름이 _(언더바)/숫자로 처음 시작하게 되면 에러 발생한다. 그래서 아래 코드 추가함.
                    if (node_name.startswith('_')) or (node_name[0].isdigit()):
                        log_handler.LogHandler.log_msg(
                            method=logging.error,
                            msg='[{0}/{1}] "{2}" _(underline) or numbers should not be in the first \
                            word of the node name. change the node name'.format(
                                node_cnt+1, total_node_cnt, node_name))
                        continue
            node_cate = houdini_api.HoudiniAPI.node_category_type_name(node)
            is_done_node = self.__node_declare(node=node, db_api=db_api)
            if not is_done_node:
                node.setName(node_name, unique_name=True)
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='[{0}/{1}] "{2}" node DB input failed'.format(node_cnt+1, total_node_cnt, node_name))
                continue
            self.__add_category_item(category=node_cate)
            is_declare = True
            log_handler.LogHandler.log_msg(
                method=logging.debug,
                msg='[{0}/{1}] node dropped "{2}" ({3})'.format(
                    node_cnt+1, total_node_cnt, node_path, node_cate))
        if is_declare:
            self.__select_category(category=self.__sel_item_text)
        self.__dragdrop_overlay_close()

    def __select_category(self, category=None):
        root_idx = self.__ihda_category_proxy_model.index(0, 0, QtCore.QModelIndex())
        find_idx = self.__find_tree_element_model(index=root_idx, find_name=category)
        if find_idx is None:
            return
        self.__ihda_category_view.setCurrentIndex(find_idx)

    def __select_model_item_by_hda_id(self, hda_id=None):
        if self.__is_ihda_history_view:
            # history가 존재하지 않으면
            if not self.__ihda_history_model.is_exist_ihda_item_from_model(hkey_id=hda_id):
                return
            self.__select_hist_ihda_combobox_item(hkey_id=hda_id)
        else:
            if self.__is_icon_mode:
                model_hda = self.__ihda_list_proxy_model
                view_hda = self.__ihda_list_view
            else:
                model_hda = self.__ihda_table_proxy_model
                view_hda = self.__ihda_table_view
            find_idx = self.__find_hda_id_by_model_item(model_hda=model_hda, find_hda_id=hda_id)
            if find_idx is None:
                return
            view_hda.setCurrentIndex(find_idx)
            self.__slot_on_hda_item_clicked(find_idx)

    def __node_declare(self, node=None, db_api=None):
        node_name = node.name()
        is_display_flag = None
        is_render_flag = None
        if hasattr(node, 'isDisplayFlagSet'):
            is_display_flag = node.isDisplayFlagSet()
        if hasattr(node, 'isRenderFlagSet'):
            is_render_flag = node.isRenderFlagSet()
        node_cate = houdini_api.HoudiniAPI.node_category_type_name(node)
        item_key_lst = [node_cate, node_name]
        is_exist_hda_name = db_api.is_exist_hda_name(
            user_id=self.__user, category=node_cate, hda_name=node_name)
        self.__sel_parent_lst = item_key_lst
        # 만약 등록하려는 Category의 HDA의 이름이 DB에 존재한다면,
        if is_exist_hda_name:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='{0} in the {1} category exists...'.format(node_name, node_cate))
            # 업데이트 할 것인지 물어 본 다음 업데이트 진행
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setWindowTitle('Update iHDA Node')
            msgbox.setText('''
<font color=red size=5>{0}</font> the same name exists in the category<br>
<font color=red size=5>{1}</font> do you want to update iHDA node?'''.format(node_cate, node_name))
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            reply = msgbox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                log_handler.LogHandler.log_msg(method=logging.info, msg='update has been canceled')
                return False
            hda_key_id = db_api.get_hda_key_id(category=node_cate, name=node_name, user_id=self.__user)
            if hda_key_id is None:
                return False
            hda_key_id = hda_key_id[0]
            # 업데이트하려는 노드가 저장되어있는 노드 타입과 같은지 확인
            hda_node_type = db_api.get_hda_node_type(hda_key_id=hda_key_id)
            if hda_node_type != houdini_api.HoudiniAPI.node_type_name(node):
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='node you want to update is different from the node type stored in DB')
                return False
            version = IndividualHDA.__get_new_up_version(version=db_api.get_hda_version(hda_key_id=hda_key_id))
            node_info_dict = self.__node_info_data(key_lst=item_key_lst, node=node, version=version)
            if node_info_dict is None:
                return False
            # update 진행
            is_done_db = self.__update_to_hda_db(info_data=node_info_dict, hda_key_id=hda_key_id, db_api=db_api)
        else:
            node_info_dict = self.__node_info_data(
                key_lst=item_key_lst, node=node, version=public.Value.init_hda_version)
            if node_info_dict is None:
                return False
            is_done_db = self.__insert_to_hda_db(info_data=node_info_dict, db_api=db_api)
        #
        # DB 입력 실패면
        if not is_done_db:
            return False
        if is_display_flag is not None:
            node.setDisplayFlag(is_display_flag)
        if is_render_flag is not None:
            node.setRenderFlag(is_render_flag)
        return True

    def __node_info_data(self, key_lst=None, node=None, version=None):
        # hda info
        node_info_dict = self.__get_hda_info(key_lst=key_lst, node=node, version=version)
        if node_info_dict is None:
            log_handler.LogHandler.log_msg(method=logging.error, msg='invalid node. stop node creation')
            return None
        get_node = node_info_dict.get(public.Key.node)
        get_hda_dirpath = node_info_dict.get(public.Key.hda_dirpath)
        get_hda_filename = node_info_dict.get(public.Key.hda_filename)
        get_hda_version = node_info_dict.get(public.Key.hda_version)
        assert isinstance(get_hda_dirpath, pathlib2.Path)
        # hda_dirpath 경로에 HDA file 생성
        if not get_hda_dirpath.exists():
            get_hda_dirpath.mkdir(parents=True)
        is_houdini_api_file = houdini_api.HoudiniAPI.create_hda_file(
            node=get_node, hda_dirpath=get_hda_dirpath, hda_filename=get_hda_filename, hda_version=get_hda_version)
        if not is_houdini_api_file:
            return None
        return node_info_dict

    def __get_hda_info(self, key_lst=None, node=None, version=None):
        hda_dirpath = self.__hda_base_dirpath.joinpath('/'.join(key_lst))
        hda = houdini_api.HoudiniAPI(hda_version=version, node_path=node.path(), hda_dirpath=hda_dirpath)
        node_info_dict = hda.get_individual_hda_data()
        if not len(node_info_dict):
            return None
        return node_info_dict

    @staticmethod
    def __get_new_up_version(version=None):
        return str(eval(version) + 0.1)

    def __update_to_hda_db(self, info_data=None, hda_key_id=None, db_api=None):
        node = info_data.get(public.Key.node)
        node_name = node.name()
        node_path = node.path()
        node_ver = info_data.get(public.Key.hda_version)
        hda_dirpath = info_data.get(public.Key.hda_dirpath)
        hda_filename = info_data.get(public.Key.hda_filename)
        type_path_lst = info_data.get(public.Key.node_type_path_list)
        cate_path_lst = info_data.get(public.Key.node_cate_path_list)
        type_name = info_data.get(public.Key.node_type_name)
        cate_name = info_data.get(public.Key.node_cate_name)
        def_desc = info_data.get(public.Key.node_def_desc)
        icon_path_lst = info_data.get(public.Key.node_icon_path_list)
        is_net = info_data.get(public.Key.is_network)
        is_sub_net = info_data.get(public.Key.is_sub_network)
        input_conn = info_data.get(public.Key.node_input_connections)
        output_conn = info_data.get(public.Key.node_output_connections)
        hou_version = houdini_api.HoudiniAPI.current_houdini_version()
        hou_license = houdini_api.HoudiniAPI.current_houdini_license()
        declare_os = public.platform_system()
        assert isinstance(hda_dirpath, pathlib2.Path)
        # thumbnail
        thumb_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(hda_dirpath=hda_dirpath)
        thumb_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(name=node_name, version=node_ver)
        thumb_filepath = thumb_dirpath / thumb_filename
        if not thumb_dirpath.exists():
            thumb_dirpath.mkdir(parents=True)
        houdini_api.HoudiniAPI.create_thumbnail(output_filepath=thumb_filepath)
        is_hda_info = db_api.update_hda_info(
            hda_key_id=hda_key_id, version=node_ver, filename=hda_filename, dirpath=hda_dirpath)
        is_icon_info = db_api.update_icon_info(hda_key_id=hda_key_id, icon_lst=icon_path_lst)
        hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        hip_dirpath = hip_filepath.parent
        hip_filename = hip_filepath.name
        assert isinstance(hip_filepath, pathlib2.Path)
        frinfo = houdini_api.HoudiniAPI.frame_info()
        is_hipfile_info = db_api.update_hipfile_info(
            hda_key_id=hda_key_id, filename=hip_filepath.name, dirpath=hip_filepath.parent,
            houdini_version=hou_version, hda_license=hou_license,
            operating_system=declare_os, sf=frinfo[0], ef=frinfo[1], fps=frinfo[2])
        # loc = location.Location()
        # # 만약 인터넷에 연결되어 있다면
        # if location.Location.is_network_connected():
        #     loc_data = loc.get_loc()
        #     if loc_data is None:
        #         log_handler.LogHandler.log_msg(method=logging.warning, msg='IP information could not be verified')
        #     else:
        #         is_location_info = db_api.update_location_info(
        #             hda_key_id=hda_key_id, country=loc_data.get(public.Key.Location.country),
        #             timezone=loc_data.get(public.Key.Location.timezone),
        #             region=loc_data.get(public.Key.Location.region),
        #             city=loc_data.get(public.Key.Location.city),
        #             ip=loc_data.get(public.Key.Location.ip),
        #             localx=loc_data.get(public.Key.Location.localx),
        #             localy=loc_data.get(public.Key.Location.localy),
        #             org=loc_data.get(public.Key.Location.org),
        #             postal=loc_data.get(public.Key.Location.postal))
        # else:
        #     log_handler.LogHandler.log_msg(method=logging.warning, msg='not internet connected')
        is_update_thumb = db_api.update_thumbnail_info(
            hda_key_id=hda_key_id, dirpath=thumb_dirpath, filename=thumb_filename, version=node_ver)
        if is_update_thumb:
            log_handler.LogHandler.log_msg(method=logging.info, msg='thumbnail update complete')
        is_hou_node_info = db_api.update_houdini_node_info(hda_key_id=hda_key_id, node_path=node_path)
        # houdini node info 테이블의 id
        info_id = db_api.get_hou_node_info_id(hda_key_id=hda_key_id)
        is_hou_node_cate_path_info = db_api.update_houdini_node_category_path_info(
            info_id=info_id, node_category_lst=cate_path_lst)
        is_hou_node_type_path_info = db_api.update_houdini_node_type_path_info(
            info_id=info_id, node_type_lst=type_path_lst)
        is_hou_node_input_connect_info = db_api.update_houdini_node_input_connect_info(
            info_id=info_id, node_input_connect_lst=input_conn)
        is_hou_node_output_connect_info = db_api.update_houdini_node_output_connect_info(
            info_id=info_id, node_output_connect_lst=output_conn)
        if (is_hda_info is None) or (is_hou_node_info is None) or (is_icon_info is None) or \
                (is_hou_node_cate_path_info is None) or (is_hou_node_type_path_info is None) or \
                (is_hou_node_input_connect_info is None) or (is_hou_node_output_connect_info is None) or \
                (is_hipfile_info is None):
            log_handler.LogHandler.log_msg(method=logging.critical, msg='iHDA node update failed')
            houdini_api.HoudiniAPI.delete_hda_file(hda_path=hda_dirpath / hda_filename)
            if thumb_filepath.exists():
                ihda_system.IHDASystem.remove_file(filepath=thumb_filepath, verbose=False)
            return False
        else:
            log_handler.LogHandler.log_msg(method=logging.info, msg='iHDA node update complete')
        #
        self.__update_pixmap_thumbnail(hkey_id=hda_key_id, thumb_filepath=thumb_filepath)
        # ihda_data변수에 db데이터를 한번 읽어들여 그것을 운용하는 방식으로
        # 변경해야 할 데이터: is_favorite_hda, hda_load_count, hda_ctime, hda_tags
        key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_info_key_lst()
        #
        before_data = db_api.get_update_before_data(hda_key_id=hda_key_id)
        #
        is_favorite_hda = before_data.get(public.Key.is_favorite_hda)
        hda_load_count = before_data.get(public.Key.hda_load_count)
        hda_ctime = before_data.get(public.Key.hda_ctime)
        hda_tags = before_data.get(public.Key.hda_tags)
        video_dirpath = before_data.get(public.Key.video_dirpath)
        video_filename = before_data.get(public.Key.video_filename)
        hda_note = before_data.get(public.Key.hda_note)
        val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
        val_lst = [
            hda_key_id, node_name, cate_name, node_ver, hda_filename, hda_dirpath,
            is_favorite_hda, hda_load_count, hda_ctime, val_datetime, hou_version, type_name, def_desc,
            is_net, is_sub_net, node_path, hou_license, hip_filename, hip_dirpath, thumb_filename, thumb_dirpath,
            video_filename, video_dirpath, hda_note, icon_path_lst, hda_tags]
        assert len(key_lst) == len(val_lst)
        dat = dict(zip(key_lst, val_lst))
        #
        hda_id_row_map = self.__get_hda_id_row_map()
        self.__update_item_row_data(row=hda_id_row_map.get(hda_key_id), row_data=dat)
        #
        # history
        hist_data = [
            hda_key_id, 'NODE (UPDATE)', node_name, node_ver, hda_filename, hda_dirpath,
            val_datetime, hou_version, hip_filename, hip_dirpath, hou_license, declare_os, node_path, def_desc,
            type_name, cate_name, self.__user, icon_path_lst, thumb_filename, thumb_dirpath,
            video_filename, video_dirpath]
        #
        is_hda_history = db_api.insert_hda_history(data=hist_data)
        if is_hda_history is None:
            log_handler.LogHandler.log_msg(method=logging.critical, msg='iHDA history failed')
            return False
        # 추가 된 hda key의 id 반환
        last_hda_hist_id = db_api.get_last_insert_id
        # hist_id & tag 추가
        self.__add_pixmap_hist_thumbnail(hist_id=last_hda_hist_id, thumb_filepath=thumb_filepath)
        self.__insert_ihda_history_data_model(data=hist_data, hist_id=last_hda_hist_id, tags=hda_tags)
        # history combobox 아이템 추가
        self.__set_hist_ihda_to_combobox(hkey_id=hda_key_id, hda_name=node_name)
        return True

    def __insert_to_hda_db(self, info_data=None, db_api=None):
        node = info_data.get(public.Key.node)
        node_name = node.name()
        node_path = node.path()
        node_ver = info_data.get(public.Key.hda_version)
        hda_dirpath = info_data.get(public.Key.hda_dirpath)
        hda_filename = info_data.get(public.Key.hda_filename)
        type_path_lst = info_data.get(public.Key.node_type_path_list)
        cate_path_lst = info_data.get(public.Key.node_cate_path_list)
        type_name = info_data.get(public.Key.node_type_name)
        cate_name = info_data.get(public.Key.node_cate_name)
        def_desc = info_data.get(public.Key.node_def_desc)
        icon_path_lst = info_data.get(public.Key.node_icon_path_list)
        is_net = info_data.get(public.Key.is_network)
        is_sub_net = info_data.get(public.Key.is_sub_network)
        input_conn = info_data.get(public.Key.node_input_connections)
        output_conn = info_data.get(public.Key.node_output_connections)
        hou_version = houdini_api.HoudiniAPI.current_houdini_version()
        hou_license = houdini_api.HoudiniAPI.current_houdini_license()
        declare_os = public.platform_system()
        assert isinstance(hda_dirpath, pathlib2.Path)
        # thumbnail
        thumb_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(hda_dirpath=hda_dirpath)
        thumb_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(name=node_name, version=node_ver)
        thumb_filepath = thumb_dirpath / thumb_filename
        if not thumb_dirpath.exists():
            thumb_dirpath.mkdir(parents=True)
        houdini_api.HoudiniAPI.create_thumbnail(output_filepath=thumb_filepath)
        # insert db
        is_hda_cate = db_api.insert_hda_category(category=cate_name, user_id=self.__user)
        if is_hda_cate is None:
            log_handler.LogHandler.log_msg(method=logging.critical, msg='failed to enter iHDA category')
            houdini_api.HoudiniAPI.delete_hda_file(hda_path=hda_dirpath / hda_filename)
            # 실패 시, hda 저장 디렉토리 삭제
            if hda_dirpath.exists():
                ihda_system.IHDASystem.remove_dir(dirpath=hda_dirpath, verbose=False)
            return False
        is_hda_key = db_api.insert_hda_key(name=node_name, category=cate_name, user_id=self.__user)
        if not is_hda_key:
            log_handler.LogHandler.log_msg(method=logging.critical, msg='failed to enter iHDA key')
            houdini_api.HoudiniAPI.delete_hda_file(hda_path=hda_dirpath / hda_filename)
            # 실패 시, hda 저장 디렉토리 삭제
            if hda_dirpath.exists():
                ihda_system.IHDASystem.remove_dir(dirpath=hda_dirpath, verbose=False)
            return False
        # 추가 된 hda key의 id 반환
        last_hda_key_id = db_api.get_last_insert_id
        #
        is_hda_info = db_api.insert_hda_info(
            hda_key_id=last_hda_key_id, version=node_ver,
            is_favorite=False, load_count=0, filename=hda_filename, dirpath=hda_dirpath)
        is_icon_info = db_api.insert_icon_info(hda_key_id=last_hda_key_id, icon_lst=icon_path_lst)
        hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        hip_filename = hip_filepath.name
        hip_dirpath = hip_filepath.parent
        assert isinstance(hip_filepath, pathlib2.Path)
        frinfo = houdini_api.HoudiniAPI.frame_info()
        is_hipfile_info = db_api.insert_hipfile_info(
            hda_key_id=last_hda_key_id, filename=hip_filename, dirpath=hip_dirpath,
            houdini_version=hou_version, hda_license=hou_license, operating_system=declare_os,
            sf=frinfo[0], ef=frinfo[1], fps=frinfo[2])
        # loc = location.Location()
        # # 만약 인터넷에 연결되어 있다면
        # if location.Location.is_network_connected():
        #     loc_data = loc.get_loc()
        #     if loc_data is None:
        #         log_handler.LogHandler.log_msg(method=logging.warning, msg='IP information could not be verified')
        #     else:
        #         is_location_info = db_api.insert_location_info(
        #             hda_key_id=last_hda_key_id, country=loc_data.get(public.Key.Location.country),
        #             timezone=loc_data.get(public.Key.Location.timezone),
        #             region=loc_data.get(public.Key.Location.region),
        #             city=loc_data.get(public.Key.Location.city),
        #             ip=loc_data.get(public.Key.Location.ip),
        #             localx=loc_data.get(public.Key.Location.localx),
        #             localy=loc_data.get(public.Key.Location.localy),
        #             org=loc_data.get(public.Key.Location.org),
        #             postal=loc_data.get(public.Key.Location.postal))
        # else:
        #     log_handler.LogHandler.log_msg(method=logging.warning, msg='not internet connected')
        is_insert_thumb = db_api.insert_thumbnail_info(
            hda_key_id=last_hda_key_id, dirpath=thumb_dirpath, filename=thumb_filename, version=node_ver)
        if is_insert_thumb:
            log_handler.LogHandler.log_msg(method=logging.info, msg='finished creating thumbnails')
        else:
            ihda_system.IHDASystem.remove_dir(dirpath=thumb_dirpath, verbose=False)
        is_hou_node_info = db_api.insert_houdini_node_info(
            hda_key_id=last_hda_key_id, type_name=type_name, def_desc=def_desc,
            is_net=is_net, is_sub_net=is_sub_net, old_path=node_path)
        # 추가 된 houdini node info의 id 반환
        last_hou_node_info_id = db_api.get_last_insert_id
        #
        is_hou_node_cate_path_info = db_api.insert_houdini_node_category_path_info(
            info_id=last_hou_node_info_id, node_category_lst=cate_path_lst)
        is_hou_node_type_path_info = db_api.insert_houdini_node_type_path_info(
            info_id=last_hou_node_info_id, node_type_lst=type_path_lst)
        is_hou_node_input_conn_info = db_api.insert_houdini_node_input_connect_info(
            info_id=last_hou_node_info_id, node_input_connect_lst=input_conn)
        is_hou_node_output_conn_info = db_api.insert_houdini_node_output_connect_info(
            info_id=last_hou_node_info_id, node_output_connect_lst=output_conn)
        #
        val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
        # history
        hist_data = [
            last_hda_key_id, 'NODE (INSERT)', node_name, node_ver,
            hda_filename, hda_dirpath, val_datetime, hou_version, hip_filename, hip_dirpath, hou_license,
            declare_os, node_path, def_desc, type_name, cate_name, self.__user, icon_path_lst,
            thumb_filename, thumb_dirpath, None, None]
        #
        is_hda_history = db_api.insert_hda_history(data=hist_data)
        # 추가 된 hda history의 id 반환
        last_hda_hist_id = db_api.get_last_insert_id
        #
        if (is_hda_info is None) or (is_icon_info is None) or (is_hou_node_info is None) or \
                (is_hou_node_cate_path_info is None) or (is_hou_node_type_path_info is None) or \
                (is_hou_node_input_conn_info is None) or (is_hou_node_output_conn_info is None) or \
                (is_hipfile_info is None) or (is_hda_history is None):
            log_handler.LogHandler.log_msg(method=logging.critical, msg='failed to insert node')
            db_api.delete_hda_key_with_id(hda_key_id=last_hda_key_id)
            houdini_api.HoudiniAPI.delete_hda_file(hda_path=hda_dirpath / hda_filename)
            # 실패 시, hda 저장 디렉토리 삭제
            if hda_dirpath.exists():
                ihda_system.IHDASystem.remove_dir(dirpath=hda_dirpath, verbose=False)
            return False
        else:
            log_handler.LogHandler.log_msg(method=logging.info, msg='node inserted')
        #
        self.__add_pixmap_ihda(hkey_id=last_hda_key_id, icon_lst=icon_path_lst)
        self.__add_pixmap_thumbnail(hkey_id=last_hda_key_id, thumb_filepath=thumb_filepath)
        self.__add_pixmap_hist_thumbnail(hist_id=last_hda_hist_id, thumb_filepath=thumb_filepath)
        # ihda_data변수에 db데이터를 한번 읽어들여 그것을 운용하는 방식으로
        # sqlite3_db_api get_hda_data와 맞춰야 한다.
        val_lst = [
            last_hda_key_id, node_name, cate_name, node_ver, hda_filename, hda_dirpath,
            0, 0, val_datetime, val_datetime, hou_version, type_name, def_desc,
            is_net, is_sub_net, node_path, hou_license, hip_filename, hip_dirpath,
            thumb_filename, thumb_dirpath, None, None, None, icon_path_lst, list()]
        key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_info_key_lst()
        assert len(key_lst) == len(val_lst)
        dat = dict(izip(key_lst, val_lst))
        self.__insert_ihda_data_model(data=dat)
        self.label__hda_count.setText(str(self.__ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self.__get_category_count()))
        # history 모델에 아이템 add
        # hist_id & tag 추가
        self.__insert_ihda_history_data_model(data=hist_data, hist_id=last_hda_hist_id, tags=list())
        # history combobox 아이템 추가
        self.__set_hist_ihda_to_combobox(hkey_id=last_hda_key_id, hda_name=node_name)
        # 후디니 노드에 코멘트 추가
        self.__hda_info_to_node_comment(node=node, hda_name=node_name, hda_ver=node_ver, hda_id=last_hda_key_id)
        log_handler.LogHandler.log_msg(method=logging.info, msg='comments have been added to existing Houdini node(s)')
        return True

    def __insert_ihda_history_data_model(self, data=None, hist_id=None, tags=None, comment=None):
        key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_history_key_lst()
        index_hist_id = key_lst.index(public.Key.History.hist_id)
        index_tags = key_lst.index(public.Key.History.tags)
        data.insert(index_hist_id, hist_id)
        data.insert(index_tags, tags)
        assert len(key_lst) == len(data)
        dat = dict(izip(key_lst, data))
        if comment is not None:
            dat[public.Key.History.comment] = comment
        self.__ihda_history_model.append_item(dat)
        self.label__hist_cnt.setText(str(self.__ihda_history_proxy_model.rowCount()))

    # 이름 기준으로 정렬하여 삽입하는 함수
    def __insert_ihda_data_model(self, data=None):
        name_key = public.Key.hda_name
        keys = map(lambda x: x[name_key], self.__ihda_data)
        idx = bisect_right(keys, data[name_key])
        self.__ihda_data.insert(idx, data)
        self.__ihda_list_model.beginInsertRows(QtCore.QModelIndex(), idx, idx)
        self.__ihda_list_model.endInsertRows()
        self.__ihda_table_model.beginInsertRows(QtCore.QModelIndex(), idx, idx)
        self.__ihda_table_model.endInsertRows()

    # 행 단위의 아이템 데이터 업데이트
    def __update_item_row_data(self, row=None, row_data=None):
        if row is None:
            return
        self.__ihda_data[row].update(row_data)

    @QtCore.Slot(str)
    def __search_filter_regexp_hist_hda_item(self, text):
        if self.checkBox__casesensitive_hda_hist.isChecked():
            casesensitivity = QtCore.Qt.CaseSensitive
        else:
            casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = QtCore.QRegExp(text.strip(), casesensitivity, QtCore.QRegExp.Wildcard)
        self.__ihda_history_proxy_model.setFilterRegExp(regexp)
        self.label__hist_cnt.setText(str(self.__ihda_history_proxy_model.rowCount()))

    @QtCore.Slot(str)
    def __search_filter_regexp_hda_item(self, text):
        if self.checkBox__casesensitive_hda.isChecked():
            casesensitivity = QtCore.Qt.CaseSensitive
        else:
            casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = QtCore.QRegExp(text.strip(), casesensitivity, QtCore.QRegExp.Wildcard)
        self.__ihda_list_proxy_model.setFilterRegExp(regexp)
        self.__ihda_table_proxy_model.setFilterRegExp(regexp)
        self.label__hda_count.setText(str(self.__ihda_list_proxy_model.rowCount()))

    @QtCore.Slot(str)
    def __search_filter_regexp_hda_cate(self, text):
        if self.checkBox__casesensitive_cate.isChecked():
            casesensitivity = QtCore.Qt.CaseSensitive
        else:
            casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = QtCore.QRegExp(text.strip(), casesensitivity, QtCore.QRegExp.Wildcard)
        self.__ihda_category_proxy_model.setFilterRegExp(regexp)
        self.label__cate_count.setText(str(self.__get_category_count()))
        self.__ihda_category_view.expandAll()

    @QtCore.Slot(str)
    def __search_filter_regexp_hda_record(self, text):
        # 대소문자 구별하지 않음.
        casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = QtCore.QRegExp(text.strip(), casesensitivity, QtCore.QRegExp.Wildcard)
        self.__ihda_record_proxy_model.setFilterRegExp(regexp)
        self.label__loc_record_count.setText(str(self.__ihda_record_proxy_model.get_row_count()))
        self.__ihda_record_view.expandAll()

    @QtCore.Slot(str)
    def __search_filter_regexp_hda_inside(self, text):
        # 대소문자 구별하지 않음.
        casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = QtCore.QRegExp(text.strip(), casesensitivity, QtCore.QRegExp.Wildcard)
        self.__ihda_inside_proxy_model.setFilterRegExp(regexp)
        self.label__found_hda_inside_hipfile_count.setText(str(self.__ihda_inside_proxy_model.get_row_count()))
        self.__ihda_inside_view.expandAll()

    def __add_pixmap_category(self, category=None):
        self.__ihda_icons.add_pixmap_cate_data(category=category)

    def __add_pixmap_ihda(self, hkey_id=None, icon_lst=None):
        self.__ihda_icons.add_pixmap_ihda_data(hkey_id=hkey_id, icon_lst=icon_lst)

    def __add_pixmap_thumbnail(self, hkey_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        self.__ihda_icons.add_pixmap_thumbnail_data(hkey_id=hkey_id, thumb_filepath=thumb_filepath)

    def __add_pixmap_hist_thumbnail(self, hist_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        self.__ihda_icons.add_pixmap_hist_thumbnail_data(hist_id=hist_id, thumb_filepath=thumb_filepath)

    def __update_pixmap_thumbnail(self, hkey_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        self.__ihda_icons.update_pixmap_thumbnail_data(hkey_id=hkey_id, thumb_filepath=thumb_filepath)

    def __update_pixmap_hist_thumbnail(self, hist_id=None, thumb_filepath=None):
        assert isinstance(thumb_filepath, pathlib2.Path)
        self.__ihda_icons.update_pixmap_hist_thumbnail_data(hist_id=hist_id, thumb_filepath=thumb_filepath)

    def __remove_pixmap_category(self, category=None):
        self.__ihda_icons.remove_pixmap_cate_data(category=category)

    def __remove_pixmap_ihda(self, hkey_id=None):
        self.__ihda_icons.remove_pixmap_ihda_data(hkey_id=hkey_id)

    def __remove_pixmap_thumbnail(self, hkey_id=None):
        self.__ihda_icons.remove_pixmap_thumbnail_data(hkey_id=hkey_id)

    def __remove_pixmap_hist_thumbnail(self, hist_id=None):
        self.__ihda_icons.remove_pixmap_hist_thumbnail_data(hist_id=hist_id)

    # history pixmap 초기화
    def __clear_pixmap_histotry(self):
        self.__ihda_icons.clear_pixmap_hist_thumbnail_data()

    def __add_record_item(self, data=None):
        self.__ihda_record_model.insert_record_data(data=data)
        self.__ihda_record_model.reload()
        self.__ihda_record_view.expandAll()

    def __add_category_item(self, category=None):
        self.__add_pixmap_category(category=category)
        self.__ihda_category_model.add_item(data={category: None})
        self.__ihda_category_model.reload()
        self.__ihda_category_view.expandAll()

    def __remove_category_item(self, category=None, category_list=None):
        if category_list is None:
            self.__ihda_category_model.remove_item(category=category)
            self.__remove_pixmap_category(category=category)
            self.__ihda_category_model.reload()
        else:
            if category not in category_list:
                self.__ihda_category_model.remove_item(category=category)
                self.__remove_pixmap_category(category=category)
                self.__ihda_category_model.reload()
                self.__ihda_category_view.expandAll()

    def __get_category_count(self):
        return self.__ihda_category_proxy_model.rowCount(
            self.__ihda_category_proxy_model.index(0, 0, QtCore.QModelIndex()))

    # refresh history item info
    def __refresh_history_current_attribs(self):
        hist_data = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.data_role)
        hist_row = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.row_role)
        hist_col = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.col_role)
        hist_hkey_id = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.id_role)
        hist_fpath = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.filepath_role)
        hist_name = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.name_role)
        hist_id = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.hist_id_role)
        hist_cate = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.cate_role)
        hist_ver = self.__ihda_history_view.currentIndex().data(ihda_history_model.HistoryModel.version_role)
        self.__hist_curt_item_data = hist_data
        self.__hist_curt_item_row = hist_row
        self.__hist_curt_item_id = hist_hkey_id
        self.__hist_curt_item_filepath = hist_fpath
        self.__hist_curt_item_name = hist_name
        self.__hist_curt_item_hist_id = hist_id
        self.__hist_curt_item_cate = hist_cate
        self.__hist_curt_item_version = hist_ver

    # refresh item info
    def __refresh_current_attribs(self):
        if self.__is_icon_mode:
            row = self.__ihda_list_view.currentIndex().data(ihda_list_model.ListModel.row_role)
            column = 0
            # hda_data = self.__ihda_list_model.items[row]
            hda_data = self.__ihda_list_view.currentIndex().data(ihda_list_model.ListModel.data_role)
            hda_id = self.__ihda_list_view.currentIndex().data(ihda_list_model.ListModel.id_role)
            hda_filepath = self.__ihda_list_view.currentIndex().data(ihda_list_model.ListModel.filepath_role)
            hda_name = self.__ihda_list_view.currentIndex().data(ihda_list_model.ListModel.name_role)
            hda_cate = self.__ihda_list_view.currentIndex().data(ihda_list_model.ListModel.cate_role)
            hda_ver = self.__ihda_list_view.currentIndex().data(ihda_list_model.ListModel.version_role)
        else:
            row = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.row_role)
            column = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.col_role)
            # hda_data = self.__ihda_table_model.items[row]
            hda_data = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.data_role)
            hda_id = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.id_role)
            hda_filepath = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.filepath_role)
            hda_name = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.name_role)
            hda_cate = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.cate_role)
            hda_ver = self.__ihda_table_view.currentIndex().data(ihda_table_model.TableModel.version_role)
        self.__curt_hda_item_data = hda_data
        self.__curt_hda_item_row = row
        self.__curt_hda_item_id = hda_id
        self.__curt_hda_item_filepath = hda_filepath
        self.__curt_hda_item_name = hda_name
        self.__curt_hda_item_cate = hda_cate
        self.__curt_hda_item_version = hda_ver

    def __initialize_hist_current_attribs(self):
        self.__hist_curt_item_data = None
        self.__hist_curt_item_row = None
        self.__hist_curt_item_id = None
        self.__hist_curt_item_filepath = None
        self.__hist_curt_item_cate = None
        self.__hist_curt_item_hist_id = None
        self.__hist_curt_item_name = None
        self.__hist_curt_item_field = None
        self.__hist_curt_item_version = None

    def __initialize_current_attribs(self):
        self.__curt_hda_item_data = None
        self.__curt_hda_item_id = None
        self.__curt_hda_item_row = None
        self.__curt_hda_item_name = None
        self.__curt_hda_item_filepath = None
        self.__curt_hda_item_field = None
        self.__curt_hda_item_cate = None
        self.__curt_hda_item_version = None

    def __set_hda_info_to_parms(self):
        if self.__curt_hda_item_data is None:
            return
        note = self.__curt_hda_item_data.get(public.Key.hda_note)
        if note is not None:
            self.textEdit__note.setPlainText(note.decode('utf8'))
            IndividualHDA.__set_move_cursor_textedit(self.textEdit__note)
        else:
            self.textEdit__note.clear()
        tags = self.__curt_hda_item_data.get(public.Key.hda_tags)
        if tags is not None:
            if len(tags):
                self.textEdit__tag.setPlainText(IndividualHDA.__set_tag_string(tags))
                self.__set_label_tags(tags)
            else:
                self.textEdit__tag.clear()
                self.label__tags.clear()
        else:
            self.textEdit__tag.clear()
            self.label__tags.clear()

    def __set_hda_hist_info_to_parms(self):
        if self.__hist_curt_item_data is None:
            return
        tags = self.__hist_curt_item_data.get(public.Key.History.tags)
        if tags is not None:
            if len(tags):
                self.__set_label_hist_tags(tags)
            else:
                self.label__hist_tags.clear()
        else:
            self.label__hist_tags.clear()

    def __set_label_tags(self, tags):
        self.label__tags.setText('<font color=#bfff00>{0}</font>'.format(IndividualHDA.__set_tag_string(tags)))

    def __set_label_hist_tags(self, tags):
        self.label__hist_tags.setText('<font color=#bfff00>{0}</font>'.format(IndividualHDA.__set_tag_string(tags)))

    def __slot_cleanup_hda_record(self):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setWindowTitle('Cleanup iHDA Record')
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText('Are you sure you want to remove all unnecessary iHDA record data that does not exist?')
        msgbox.setDetailedText('NOTE: Don\'t worry. Only unused information is cleaned up.')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.Yes:
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            self.__delete_unused_hda_record_info(db_api=db_api)

    def __delete_unused_hda_record_info(self, db_api=None):
        record_data = db_api.get_all_hda_record_fileinfo(user_id=self.__user)
        if not len(record_data):
            log_handler.LogHandler.log_msg(method=logging.info, msg='record data does not exist')
            return
        for record_info_dat in record_data:
            record_id, hip_dirpath, hip_filename, hda_dirpath, hda_filename = record_info_dat
            hip_dirpath = pathlib2.Path(hip_dirpath)
            hip_filepath = hip_dirpath / hip_filename
            hda_dirpath = pathlib2.Path(hda_dirpath)
            hda_filepath = hda_dirpath / hda_filename
            if not hip_filepath.exists():
                db_api.delete_hda_record(record_id=record_id)
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='ID {0} record information has been deleted'.format(record_id))
            if not hda_filepath.exists():
                db_api.delete_hda_record(record_id=record_id)
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='ID {0} record information has been deleted'.format(record_id))
        self.__ihda_record_model.remove_invalid_record_data()
        self.label__loc_record_count.setText(str(self.__ihda_record_proxy_model.get_row_count()))
        log_handler.LogHandler.log_msg(
            method=logging.debug, msg='cleanup of iHDA record information is complete')

    def __slot_favorite_node(self):
        is_favorite_nodes = self.pushButton__favorite_node.isChecked()
        self.__ihda_list_proxy_model.is_favorite_nodes = is_favorite_nodes
        self.__ihda_table_proxy_model.is_favorite_nodes = is_favorite_nodes
        self.label__hda_count.setText(str(self.__ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self.__get_category_count()))
        if is_favorite_nodes:
            favorite_icon = 'ic_favorite_white.png'
            log_handler.LogHandler.log_msg(method=logging.info, msg='turn on favorite filtering')
        else:
            favorite_icon = 'ic_favorite_border_white.png'
            log_handler.LogHandler.log_msg(method=logging.info, msg='turn off favorite filtering')
        self.pushButton__favorite_node.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/{0}'.format(favorite_icon))))

    def __slot_record_only_curt_filter(self, *args):
        if self.checkBox__record_only_current_hipfile.isChecked():
            hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        else:
            hip_filepath = None
        if self.checkBox__record_only_current_ihda.isChecked():
            hda_id = self.__curt_hda_item_id
        else:
            hda_id = None
        self.__ihda_record_proxy_model.set_filter_attribute(hda_id=hda_id, hip_filepath=hip_filepath)
        self.__ihda_record_view.expandAll()
        self.label__loc_record_count.setText(str(self.__ihda_record_proxy_model.get_row_count()))

    def __slot_inside_only_curt_filter(self, *args):
        is_checked = self.checkBox__hda_inside_connect_to_view.isChecked()
        self.comboBox__hda_inside_node.setDisabled(is_checked)
        if is_checked:
            self.lineEdit__search_found_hda_inside_node.clear()
            hda_id = self.__curt_hda_item_id
            self.__ihda_inside_proxy_model.set_filter_attribute(hda_id=hda_id)
            self.label__found_hda_inside_hipfile_count.setText(str(self.__ihda_inside_proxy_model.get_row_count()))
            self.__ihda_inside_view.expandAll()
        else:
            self.__slot_search_inside_node_combobox(self.comboBox__hda_inside_node.currentIndex())

    @public.runtime_check_simple_with_param('iHDA node search')
    def __slot_refresh_inside_nodes(self):
        if not public.IS_HOUDINI:
            return
        root_node = hou.node('/')
        node_data = houdini_api.HoudiniAPI.get_ihda_node_instance_data(parent_node=root_node)
        if not len(node_data):
            node_data = dict()
            log_handler.LogHandler.log_msg(method=logging.debug, msg='iHDA node not found in current HIP file')
        self.__ihda_inside_model.make_node_tree(node_data=node_data)
        self.__ihda_inside_view.expandAll()
        self.label__found_hda_inside_hipfile_count.setText(str(self.__ihda_inside_proxy_model.get_row_count()))
        # inside node combobox 셋팅
        self.__init_set_inside_ihda_combobox()
        log_handler.LogHandler.log_msg(
            method=logging.info, msg='iHDA node search in the current HIP file has been updated')

    def __slot_thumbnails(self):
        if self.__is_show_thumbnail:
            thumb_icon = 'ic_photo_white.png'
            self.__ihda_list_model.show_thumbnail = True
            self.__ihda_table_model.show_thumbnail = True
            log_handler.LogHandler.log_msg(method=logging.info, msg='turn on thumbnail image')
        else:
            thumb_icon = 'network_sop.png'
            self.__ihda_list_model.show_thumbnail = False
            self.__ihda_table_model.show_thumbnail = False
            log_handler.LogHandler.log_msg(method=logging.info, msg='turn off thumbnail image')
        self.pushButton__thumbnail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/{0}'.format(thumb_icon))))
        self.__set_view_item_icon_size(self.doubleSpinBox__zoom.value())

    @staticmethod
    def __go_to_houdini_node(node_path=None):
        if not public.IS_HOUDINI:
            return
        if node_path is None:
            return
        node = hou.node(node_path)
        if node is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='path "{0}" does not exist'.format(node_path))
            return
        if houdini_api.HoudiniAPI.is_root_network(node):
            return
        houdini_api.HoudiniAPI.go_to_node(node=node)
        log_handler.LogHandler.log_msg(method=logging.info, msg='{0} moved to path'.format(node_path))

    @QtCore.Slot(QtCore.QModelIndex)
    def __slot_on_hda_item_clicked(self, *args):
        index = args[0]
        try:
            model_idx = index.indexes()
            if not len(model_idx):
                model_idx = index
        except AttributeError:
            model_idx = index
        if isinstance(model_idx, list) or isinstance(model_idx, tuple):
            model_idx = model_idx[0]
        if not isinstance(model_idx, QtCore.QModelIndex):
            return
        self.__selected_ihda_item(index=model_idx)

    def __play_video_most_recent_by_version(self, video_info=None):
        video_filepath = video_info[0] / video_info[1]
        if not video_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='the video file has been renamed or has no video file')
            return
        self.__slot_select_view(index=self.__video_view_idx)
        self.__video_player.play_after_add_playlist(filepath_lst=[video_filepath])

    # record double click signal
    @QtCore.Slot(QtCore.QModelIndex)
    def __slot_hda_record_double_clicked(self, *args):
        index = args[0]
        if not self.__preference.is_ffmpeg_valid:
            log_handler.LogHandler.log_msg(method=logging.error, msg='ffmpeg is not installed')
            return
        if not index.isValid():
            return
        record_data = index.data(ihda_record_model.RecordModel.record_data_role)
        if record_data is None:
            return
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        hda_id = index.data(ihda_record_model.RecordModel.hda_id_role)
        hda_name = index.data(ihda_record_model.RecordModel.name_role)
        hda_ver = record_data.get(public.Key.Record.node_ver)
        video_info = db_api.get_hda_history_video_most_recent_by_ver(hda_key_id=hda_id, version=hda_ver)
        if video_info is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='"{0} (v{1})" iHDA node has no video'.format(hda_name, hda_ver))
            return
        self.__play_video_most_recent_by_version(video_info=video_info)

    # inside double click signal
    @QtCore.Slot(QtCore.QModelIndex)
    def __slot_hda_inside_double_clicked(self, *args):
        index = args[0]
        if not index.isValid():
            return
        item_type = index.data(ihda_inside_model.InsideModel.node_type_role)
        if item_type != public.Type.ihda:
            return
        node_path = index.data(ihda_inside_model.InsideModel.node_path_role)
        IndividualHDA.__go_to_houdini_node(node_path=node_path)

    # double click signal
    @QtCore.Slot(QtCore.QModelIndex)
    def __slot_hda_double_clicked(self, *args):
        index = args[0]
        if not self.__preference.is_ffmpeg_valid:
            log_handler.LogHandler.log_msg(method=logging.error, msg='ffmpeg is not installed')
            return
        if not index.isValid():
            return
        # self.__selected_ihda_item(index=index)
        if self.__is_ihda_history_view:
            video_dirpath = self.__hist_curt_item_data.get(public.Key.History.video_dirpath)
            ihda_ver = self.__hist_curt_item_data.get(public.Key.History.version)
            hist_id = self.__hist_curt_item_data.get(public.Key.History.hist_id)
            if video_dirpath is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='id: {0} "{1} [{2}]" iHDA node has no video'.format(
                        hist_id, self.__hist_curt_item_name, ihda_ver))
                return
            video_filename = self.__hist_curt_item_data.get(public.Key.History.video_filename)
            video_filepath = video_dirpath / video_filename
        else:
            video_dirpath = self.__curt_hda_item_data.get(public.Key.video_dirpath)
            if video_dirpath is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='"{0}" iHDA node has no video'.format(self.__curt_hda_item_name))
                return
            video_filename = self.__curt_hda_item_data.get(public.Key.video_filename)
            video_filepath = video_dirpath / video_filename
        if not video_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg='the video file has been renamed or has no video file')
            return
        self.__slot_select_view(index=self.__video_view_idx)
        self.__video_player.play_after_add_playlist(filepath_lst=[video_filepath])

    def __selected_ihda_item(self, index=None):
        if not index.isValid():
            return
        if self.__is_ihda_history_view:
            self.__hist_curt_item_field = str(index.data())
            self.__refresh_history_current_attribs()
            self.__set_hda_hist_info_to_parms()
        else:
            self.__curt_hda_item_field = str(index.data())
            self.__refresh_current_attribs()
            self.__set_hda_info_to_parms()
        # record view 갱신
        if self.checkBox__record_only_current_ihda.isChecked():
            self.__slot_record_only_curt_filter()
        if self.checkBox__hda_inside_connect_to_view.isChecked():
            self.__slot_inside_only_curt_filter()

    def __slot_selected_category(self, *args):
        index = args[0]
        try:
            model_idx = index.indexes()
            if not len(model_idx):
                model_idx = index
        except AttributeError:
            model_idx = index
        if isinstance(model_idx, list) or isinstance(model_idx, tuple):
            model_idx = model_idx[0]
        # 카테고리를 검색했을 때, 아무것도 검색이 안되면 column 속성이 없다는 에러 발생하여 예외처리 함.
        try:
            self.__sel_column_idx = model_idx.column()
            index_item = self.__ihda_category_proxy_model.mapToSource(model_idx)
            item_text = str(index_item.data()).strip()
            self.__sel_item_text = item_text
            par_lst = self.__get_all_category_parent_by_selected_item(index_item)
            self.__sel_parent_lst = par_lst
            # 어느 카테고리를 클릭했는지 로깅하는 것인데 비활성화함.
            # log_handler.LogHandler.log_msg(method=logging.info, msg=' > '.join(par_lst))
            #
            node_cate = None if item_text == public.Type.root else item_text
            self.__ihda_list_proxy_model.node_category = node_cate
            self.__ihda_table_proxy_model.node_category = node_cate
            self.label__hda_count.setText(str(self.__ihda_list_proxy_model.rowCount()))
            self.label__cate_count.setText(str(self.__get_category_count()))
        except AttributeError as err:
            # log_handler.LogHandler.log_msg(method=logging.warning, msg='search results do not exist')
            pass

    def __slot_selected_record(self, *args):
        index = args[0]
        try:
            model_idx = index.indexes()
            if not len(model_idx):
                model_idx = index
        except AttributeError:
            model_idx = index
        if isinstance(model_idx, list) or isinstance(model_idx, tuple):
            model_idx = model_idx[0]

    @staticmethod
    def __ihda_license_check(hda_license=None):
        # 만약 현재 Houdini는 상업용 라이센스이면
        if houdini_api.HoudiniAPI.is_houdini_commercial_license():
            # iHDA는 상업용 라이센스가 아니라면
            if hda_license != houdini_api.HoudiniAPI.commercial_license():
                return False
        return True

    def __alert_invalid_rename(self, msg=None):
        self.__rename_ihda.set_confirm_pixmap(False)
        self.__rename_ihda.set_confirm_text(msg)
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setWindowTitle('iHDA Node Rename')
        msgbox.setIcon(QtWidgets.QMessageBox.Warning)
        msgbox.setText('It\'s not a valid iHDA name.')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        _ = msgbox.exec_()

    def __slot_hda_name_changed(self):
        if self.__rename_ihda.is_valid_ihda_name:
            category = self.__curt_hda_item_cate
            old_hda_name = self.__curt_hda_item_name
            new_hda_name = self.__rename_ihda.final_ihda_name
            hda_type_name = self.__curt_hda_item_data.get(public.Key.node_type_name)
            if hda_type_name.find(':') >= 0:
                hda_type_name = hda_type_name.split(':')[0].strip()
            wrong_name = '{0}1'.format(hda_type_name)
            # 등록해서는 안되는 노드 이름들
            if new_hda_name in [hda_type_name, wrong_name]:
                self.__alert_invalid_rename(msg='''
The "{0}" name is not allowed because it is the same or
similar to the current node type.

Type of current node: "{1}"
                '''.format(new_hda_name, hda_type_name))
            else:
                db_api = IndividualHDA.__db_api_wrap()
                if db_api is None:
                    return
                is_exist_hda_name = db_api.is_exist_hda_name(
                    user_id=self.__user, category=category, hda_name=new_hda_name)
                if is_exist_hda_name:
                    self.__alert_invalid_rename(msg='iHDA with the same name exists.')
                else:
                    # iHDA directory 정보가 없다면
                    hda_dirpath = self.__curt_hda_item_data.get(public.Key.hda_dirpath)
                    if hda_dirpath is None:
                        log_handler.LogHandler.log_msg(method=logging.error, msg='no iHDA folder information')
                        self.__rename_ihda.close()
                        return
                    # 만약 같은 공간에 같은 이름의 디렉토리가 존재한다면
                    dirname_lst = map(lambda x: x.name if x.is_dir() else None, hda_dirpath.glob('*'))
                    if new_hda_name in dirname_lst:
                        self.__alert_invalid_rename(msg='A folder with the same name exists')
                        log_handler.LogHandler.log_msg(
                            method=logging.error, msg='a folder with the same name exists in the "{0}" space'.format(
                                hda_dirpath.parent.as_posix()))
                    else:
                        self.__rename_ihda.close()
                        self.__dragdrop_overlay_show(text='Change iHDA Node Name')
                        is_done = self.__change_ihda_name(new_hda_name=new_hda_name, db_api=db_api)
                        self.__dragdrop_overlay_close()
                        if is_done:
                            log_handler.LogHandler.log_msg(
                                method=logging.debug,
                                msg='renamed "{0}" >>>>> "{1}"'.format(old_hda_name, new_hda_name))

    # 변경했던 iHDA 디렉토리/파일을 원래의 이름을 되돌리기 함수
    @staticmethod
    def __revert_orig_hda_folder_file(
            old_hda_dirpath=None, old_hda_filename=None, new_hda_dirpath=None, new_hda_filename=None):
        assert isinstance(old_hda_dirpath, pathlib2.Path)
        assert isinstance(new_hda_dirpath, pathlib2.Path)
        old_hda_filepath = old_hda_dirpath / old_hda_filename
        new_hda_filepath = new_hda_dirpath / new_hda_filename
        tmp_filepath = old_hda_dirpath / new_hda_filename
        if tmp_filepath.exists():
            tmp_filepath.rename(old_hda_filepath)
        else:
            if new_hda_filepath.exists():
                new_hda_filepath.rename(old_hda_filepath)
        if new_hda_dirpath.exists():
            new_hda_dirpath.rename(old_hda_dirpath)

    # 변경했던 thumbnail 파일을 원래의 이름을 되돌리기 함수
    @staticmethod
    def __revert_orig_thumbnail_file(
            old_thumb_dirpath=None, old_thumb_filename=None, new_thumb_dirpath=None, new_thumb_filename=None):
        assert isinstance(old_thumb_dirpath, pathlib2.Path)
        assert isinstance(new_thumb_dirpath, pathlib2.Path)
        old_thumb_filepath = old_thumb_dirpath / old_thumb_filename
        new_thumb_filepath = new_thumb_dirpath / new_thumb_filename
        tmp_filepath = old_thumb_dirpath / new_thumb_filename
        if tmp_filepath.exists():
            tmp_filepath.rename(old_thumb_filepath)
        else:
            if new_thumb_filepath.exists():
                new_thumb_filepath.rename(old_thumb_filepath)

    # 변경했던 video 파일을 원래의 이름을 되돌리기 함수
    @staticmethod
    def __revert_orig_video_file(
            old_video_dirpath=None, old_video_filename=None, new_video_dirpath=None, new_video_filename=None):
        assert isinstance(old_video_dirpath, pathlib2.Path)
        assert isinstance(new_video_dirpath, pathlib2.Path)
        old_video_filepath = old_video_dirpath / old_video_filename
        new_video_filepath = new_video_dirpath / new_video_filename
        tmp_filepath = old_video_dirpath / new_video_filename
        if tmp_filepath.exists():
            tmp_filepath.rename(old_video_filepath)
        else:
            if new_video_filepath.exists():
                new_video_filepath.rename(old_video_filepath)

    def __change_ihda_name(self, new_hda_name=None, db_api=None):
        # 비디오를 한번이라도 플레이했다면 파일이 열려있다는 에러가 발생해 이름이 바뀌지 않는다.
        # 그래서 이름 변환 노드가 플레이리스트에 존재한다면 제거해주고 이름을 변경.
        #
        data = self.__curt_hda_item_data
        row = data.get(public.Key.item_row)
        hda_id = data.get(public.Key.hda_id)
        hda_version = data.get(public.Key.hda_version)
        old_hda_dirpath = data.get(public.Key.hda_dirpath)
        assert isinstance(old_hda_dirpath, pathlib2.Path)
        new_hda_dirpath = old_hda_dirpath.with_name(new_hda_name)
        old_hda_filename = data.get(public.Key.hda_filename)
        new_hda_filename = houdini_api.HoudiniAPI.make_hda_filename(
            name=new_hda_name, version=hda_version, is_encrypt_ihda=False)
        old_node_old_path = data.get(public.Key.node_old_path)
        _plst = old_node_old_path.split(public.Paths.houdini_path_sep)[:-1] + [new_hda_name]
        new_node_old_path = public.Paths.houdini_path_sep.join(_plst)
        old_hda_filepath = old_hda_dirpath / old_hda_filename
        new_hda_filepath = new_hda_dirpath / new_hda_filename
        if not old_hda_dirpath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='iHDA folder does not exist')
            return False
        if not old_hda_filepath.exists():
            log_handler.LogHandler.log_msg(method=logging.error, msg='iHDA file is missing')
            return False
        # player가 재생중이거나 일시 정지상태면 정지
        self.__video_player.player_stop()
        # playlist에서 현 노드 정보 제거
        # 현재 iHDA 노드의 모든 video file 정보
        video_filepath_lst = db_api.get_history_video_info(hda_key_id=hda_id)
        self.__delete_video_playlist(video_filepath_list=video_filepath_lst)
        try:
            old_hda_filepath.rename(old_hda_dirpath / new_hda_filename)
            old_hda_dirpath.rename(new_hda_dirpath)
        except Exception as err:
            IndividualHDA.__revert_orig_hda_folder_file(
                old_hda_dirpath=old_hda_dirpath, old_hda_filename=old_hda_filename,
                new_hda_dirpath=new_hda_dirpath, new_hda_filename=new_hda_filename)
            log_handler.LogHandler.log_msg(method=logging.error, msg='failed to rename folder/file')
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='please empty the video on the node from the iHDA playlist and try again')
            return False
        # thumbnail & video
        new_thumbnail_dirpath = None
        new_thumbnail_filename = None
        new_video_dirpath = None
        new_video_filename = None
        old_thumbnail_dirpath = data.get(public.Key.thumbnail_dirpath)
        old_thumbnail_filename = data.get(public.Key.thumbnail_filename)
        old_video_dirpath = data.get(public.Key.video_dirpath)
        old_video_filename = data.get(public.Key.video_filename)
        if old_thumbnail_dirpath is not None:
            assert isinstance(old_thumbnail_dirpath, pathlib2.Path)
            new_thumbnail_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(hda_dirpath=new_hda_dirpath)
            if new_thumbnail_dirpath.exists():
                new_thumbnail_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(
                    name=new_hda_name, version=hda_version)
                new_thumbnail_filepath = new_thumbnail_dirpath / new_thumbnail_filename
                old_thumbnail_filepath = new_thumbnail_dirpath / old_thumbnail_filename
                if old_thumbnail_filepath.exists():
                    try:
                        old_thumbnail_filepath.rename(new_thumbnail_filepath)
                    except Exception as err:
                        IndividualHDA.__revert_orig_hda_folder_file(
                            old_hda_dirpath=old_hda_dirpath, old_hda_filename=old_hda_filename,
                            new_hda_dirpath=new_hda_dirpath, new_hda_filename=new_hda_filename)
                        IndividualHDA.__revert_orig_thumbnail_file(
                            old_thumb_dirpath=old_thumbnail_dirpath, old_thumb_filename=old_thumbnail_filename,
                            new_thumb_dirpath=new_thumbnail_dirpath, new_thumb_filename=new_thumbnail_filename)
                        log_handler.LogHandler.log_msg(method=logging.error, msg='failed to rename thumbnail file')
                        log_handler.LogHandler.log_msg(
                            method=logging.error, msg='thumbnail file is open, please close and try again')
                        return False
            else:
                new_thumbnail_filename = old_thumbnail_filename
        if old_video_dirpath is not None:
            # iHDA와 video의 버전이 동일하다면
            if db_api.is_video_and_ihda_same_version(hda_key_id=hda_id, version=hda_version):
                assert isinstance(old_video_dirpath, pathlib2.Path)
                new_video_dirpath = houdini_api.HoudiniAPI.make_video_dirpath(hda_dirpath=new_hda_dirpath)
                if new_video_dirpath.exists():
                    old_video_filepath = new_video_dirpath / old_video_filename
                    if old_video_filepath.exists():
                        new_video_filename = houdini_api.HoudiniAPI.make_video_filename(
                            name=new_hda_name, version=hda_version)
                        new_video_filepath = new_video_dirpath / new_video_filename
                        try:
                            old_video_filepath.rename(new_video_filepath)
                        except Exception as err:
                            IndividualHDA.__revert_orig_hda_folder_file(
                                old_hda_dirpath=old_hda_dirpath, old_hda_filename=old_hda_filename,
                                new_hda_dirpath=new_hda_dirpath, new_hda_filename=new_hda_filename)
                            IndividualHDA.__revert_orig_thumbnail_file(
                                old_thumb_dirpath=old_thumbnail_dirpath, old_thumb_filename=old_thumbnail_filename,
                                new_thumb_dirpath=new_thumbnail_dirpath, new_thumb_filename=new_thumbnail_filename)
                            IndividualHDA.__revert_orig_video_file(
                                old_video_dirpath=old_video_dirpath, old_video_filename=old_video_filename,
                                new_video_dirpath=new_video_dirpath, new_video_filename=new_video_filename)
                            log_handler.LogHandler.log_msg(method=logging.error, msg='failed to rename video file')
                            log_handler.LogHandler.log_msg(
                                method=logging.error,
                                msg='operation cannot be completed if the video file is running or the file is open')
                            log_handler.LogHandler.log_msg(
                                method=logging.error,
                                msg='empty the node\'s video from the iHDA playlist and try again')
                            log_handler.LogHandler.log_msg(
                                method=logging.error,
                                msg='if that doesn\'t work, restart Houdini and try again')
                            return False
                else:
                    new_video_filename = old_video_filename
            else:
                new_video_dirpath = None
        is_update_hda_name = db_api.update_hda_name(
            hda_key_id=hda_id, name=new_hda_name, filename=new_hda_filename, dirpath=new_hda_dirpath,
            node_old_path=new_node_old_path, thumbnail_dirpath=new_thumbnail_dirpath,
            thumbnail_filename=new_thumbnail_filename, video_dirpath=new_video_dirpath,
            video_filename=new_video_filename)
        is_update_hda_name_hist = db_api.update_hda_name_to_history(
            hda_key_id=hda_id, hda_version=hda_version, hda_filename=new_hda_filename, hda_dirpath=new_hda_dirpath,
            thumb_dirpath=new_thumbnail_dirpath, thumb_filename=new_thumbnail_filename,
            video_dirpath=new_video_dirpath, video_filename=new_video_filename)
        if bool(is_update_hda_name):
            val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
            self.__change_hda_data(row=row, key=public.Key.hda_name, val=new_hda_name)
            self.__change_hda_data(row=row, key=public.Key.hda_filename, val=new_hda_filename)
            self.__change_hda_data(row=row, key=public.Key.hda_dirpath, val=new_hda_dirpath)
            self.__change_hda_data(row=row, key=public.Key.node_old_path, val=new_node_old_path)
            self.__change_hda_data(row=row, key=public.Key.hda_mtime, val=val_datetime)
            if new_thumbnail_dirpath is not None:
                self.__change_hda_data(row=row, key=public.Key.thumbnail_dirpath, val=new_thumbnail_dirpath)
                self.__change_hda_data(row=row, key=public.Key.thumbnail_filename, val=new_thumbnail_filename)
            if new_video_dirpath is not None:
                self.__change_hda_data(row=row, key=public.Key.video_dirpath, val=new_video_dirpath)
                self.__change_hda_data(row=row, key=public.Key.video_filename, val=new_video_filename)
            self.__curt_hda_item_name = new_hda_name
            self.__curt_hda_item_filepath = new_hda_filepath
            #
            # record 데이터 갱신 함수 호출. 이 함수만 하면 data는 바뀌지만 뷰에서는 바뀌지 않늗 문제가 있다.
            self.__ihda_record_model.rename_record_item(
                hda_id=hda_id, new_name=new_hda_name, hda_dirpath=new_hda_dirpath, hda_version=hda_version)
            # 그래서 임시 방편으로 reload 함수를 강제 호출했다.
            self.__ihda_record_model.reload()
            #
            if bool(is_update_hda_name_hist):
                # history ihda combobox text 변경
                find_cmbox_idx = self.__find_hist_ihda_combobox_index(hkey_id=hda_id)
                if find_cmbox_idx is not None:
                    self.comboBox__hist_ihda_node.setItemText(find_cmbox_idx, new_hda_name)
                # history model data update
                self.__ihda_history_model.update_item_data_by_hkey_id_from_model(
                    hkey_id=hda_id, key=public.Key.History.ihda_dirpath, val=new_hda_dirpath)
                self.__ihda_history_model.update_item_data_by_hkey_id_version_from_model(
                    hkey_id=hda_id, version=hda_version, key=public.Key.History.ihda_filename, val=new_hda_filename)
                if new_thumbnail_dirpath is not None:
                    self.__ihda_history_model.update_item_data_by_hkey_id_from_model(
                        hkey_id=hda_id, key=public.Key.History.thumb_dirpath, val=new_thumbnail_dirpath)
                    self.__ihda_history_model.update_item_data_by_hkey_id_version_from_model(
                        hkey_id=hda_id, version=hda_version,
                        key=public.Key.History.thumb_filename, val=new_thumbnail_filename)
                if new_video_dirpath is not None:
                    self.__ihda_history_model.update_item_data_by_hkey_id_from_model(
                        hkey_id=hda_id, key=public.Key.History.video_dirpath, val=new_video_dirpath)
                    self.__ihda_history_model.update_item_data_by_hkey_id_version_from_model(
                        hkey_id=hda_id, version=hda_version,
                        key=public.Key.History.video_filename, val=new_video_filename)
                # history trigger 주석처리로 인해 DB 삽입을 직접해줘야 한다.
                self.__insert_hist_db_from_curt_hist_data(db_api=db_api, comment='NAME (CHANGE)')
            return True
        else:
            return False

    def __change_hda_data(self, row=None, key=None, val=None):
        self.__ihda_data[row][key] = val
        self.__curt_hda_item_data[key] = val

    def __insert_hist_db_from_curt_hist_data(self, db_api=None, comment=None):
        # history를 위한 변수
        data = self.__curt_hda_item_data
        hda_dirpath = data.get(public.Key.hda_dirpath)
        hda_name = data.get(public.Key.hda_name)
        hda_version = data.get(public.Key.hda_version)
        hda_id = data.get(public.Key.hda_id)
        hda_filename = data.get(public.Key.hda_filename)
        node_path = data.get(public.Key.node_old_path)
        def_desc = data.get(public.Key.node_def_desc)
        type_name = data.get(public.Key.node_type_name)
        cate_name = data.get(public.Key.hda_cate)
        icon_lst = data.get(public.Key.hda_icon)
        tag_lst = data.get(public.Key.hda_tags)
        thumb_filename = data.get(public.Key.thumbnail_filename)
        thumb_dirpath = data.get(public.Key.thumbnail_dirpath)
        thumb_filepath = thumb_dirpath / thumb_filename
        video_filename = data.get(public.Key.video_filename)
        video_dirpath = data.get(public.Key.video_dirpath)
        hou_version = houdini_api.HoudiniAPI.current_houdini_version()
        hou_license = houdini_api.HoudiniAPI.current_houdini_license()
        hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        hip_dirpath = hip_filepath.parent
        hip_filename = hip_filepath.name
        declare_os = public.platform_system()
        val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
        hist_data = [
            hda_id, comment, hda_name, hda_version, hda_filename, hda_dirpath,
            val_datetime, hou_version, hip_filename, hip_dirpath, hou_license, declare_os, node_path,
            def_desc, type_name, cate_name, self.__user, icon_lst, thumb_filename, thumb_dirpath,
            video_filename, video_dirpath]
        is_hda_history = db_api.insert_hda_history(data=hist_data)
        if is_hda_history is None:
            self.__loading_close()
            return
        last_hda_hist_id = db_api.get_last_insert_id
        self.__add_pixmap_hist_thumbnail(hist_id=last_hda_hist_id, thumb_filepath=thumb_filepath)
        self.__insert_ihda_history_data_model(data=hist_data, hist_id=last_hda_hist_id, tags=tag_lst)

    def __resizing_listview(self):
        self.__ihda_list_view.setResizeMode(QtWidgets.QListView.Adjust)
        self.__ihda_list_view.setSpacing(3)

    @staticmethod
    def __get_hda_data(category=None, user_id=None):
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        get_data = db_api.get_hda_data(category=category, user_id=user_id)
        if get_data is None:
            return list()
        return get_data

    @staticmethod
    def __get_hda_hist_data(hda_key_id=None, user_id=None, search_date=None):
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        get_data = db_api.get_hda_history(hda_key_id=hda_key_id, user_id=user_id, search_date=search_date)
        if get_data is None:
            return list()
        return get_data

    @staticmethod
    def __get_hda_category(user_id=None):
        if user_id is None:
            return dict()
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        cate_lst = db_api.get_hda_category(user_id=user_id)
        if cate_lst is None:
            return dict()
        return dict(izip(cate_lst, [None] * len(cate_lst)))

    # node location record data
    # 모두 가져온 후 proxy model로 필터링한다. 그래서 조건을 주지 않고 데이터를 가져오도록 하였다.
    @staticmethod
    def __get_hda_loc_record_data():
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        record_data = db_api.get_hda_node_location_record()
        return record_data

    def __get_all_category_parent_by_selected_item(self, index):
        plist = list()
        if not index.isValid():
            return list()
        plist.append(index.data(QtCore.Qt.DisplayRole))
        return self.__get_all_category_parent_by_selected_item(index.parent()) + plist

    @property
    def __hda_base_dirpath(self):
        try:
            return self.__preference.data_final_dirpath / self.__user
        except TypeError as err:
            return None

    @property
    def __is_valid_current_hda_item_data(self):
        if self.__curt_hda_item_data is not None:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning, msg='<font color=#cc6600>node is not selected</font>'
        )
        return False

    @property
    def __is_valid_hist_current_item_data(self):
        if self.__hist_curt_item_data is not None:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning, msg='<font color=#cc6600>iHDA history node is not selected</font>'
        )
        return False

    def __build_context_history_menu(self, point):
        index = self.__ihda_history_view.indexAt(point)
        if not index.isValid():
            return
        if not self.__is_valid_hist_current_item_data:
            return
        context_menu = QtWidgets.QMenu(self)
        #
        open_context_menu = QtWidgets.QMenu('Open', self)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_donut_large_white.png')))
        #
        action_open_context_ihda_folder = open_context_menu.addAction('iHDA Folder')
        action_open_context_ihda_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_folder_white.png')))
        # hip folder
        action_open_context_hip_folder = open_context_menu.addAction('HIP Folder')
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_folder_white.png')))
        open_context_menu.addSeparator()
        # hip file
        action_open_context_hip_file = open_context_menu.addAction('HIP File')
        action_open_context_hip_file.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/hipfile.png')))
        #
        action_context_menu_detail = context_menu.addAction('Detail')
        action_context_menu_detail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_format_quote_white.png')))
        #
        action_context_menu_remove = context_menu.addAction('Delete')
        action_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_delete_forever_white.png')))
        # 단축키 비활성화
        # action_context_menu_remove.setShortcut(QtGui.QKeySequence(self.__shortcut_del_key))
        context_menu.addMenu(open_context_menu)
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_detail)
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_remove)
        # refresh current data
        self.__hist_curt_item_field = index.data()
        self.__refresh_history_current_attribs()
        self.__set_hda_hist_info_to_parms()
        #
        if self.__hist_curt_item_data is None:
            return
        hip_dirpath = self.__hist_curt_item_data.get(public.Key.History.hip_dirpath)
        #
        action = context_menu.exec_(self.__ihda_history_view.mapToGlobal(point))
        #
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(dirpath=self.__hist_curt_item_filepath)
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            hip_filepath = hip_dirpath / self.__hist_curt_item_data.get(public.Key.History.hip_filename)
            self.__open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_context_menu_detail:
            self.__detail_view_ihda_data(data=self.__hist_curt_item_data)
        elif action == action_context_menu_remove:
            self.__remove_hist_item()
        else:
            pass

    def __build_context_ihda_menu(self, point):
        if self.__is_icon_mode:
            view = self.__ihda_list_view
        else:
            view = self.__ihda_table_view
        index = view.indexAt(point)
        if not index.isValid():
            return
        if not self.__is_valid_current_hda_item_data:
            return
        context_menu = QtWidgets.QMenu(self)
        #
        open_context_menu = QtWidgets.QMenu('Open', self)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_donut_large_white.png')))
        #
        action_open_context_ihda_folder = open_context_menu.addAction('iHDA Folder')
        action_open_context_ihda_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_folder_white.png')))
        #
        action_open_context_hip_folder = open_context_menu.addAction('HIP Folder')
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_folder_white.png')))
        open_context_menu.addSeparator()
        #
        action_open_context_hip_file = open_context_menu.addAction('HIP File')
        action_open_context_hip_file.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/hipfile.png')))

        hda_context_menu = QtWidgets.QMenu('iHDA', self)
        hda_context_menu.setIcon(QtGui.QIcon(QtGui.QPixmap(':/main/icons/houdini_logo_white.png')))

        action_hda_context_menu_favorite = hda_context_menu.addAction('Favorite')
        favorite_icon = 'ic_favorite_border_white.png'
        if self.__curt_hda_item_data.get(public.Key.is_favorite_hda):
            favorite_icon = 'ic_favorite_white.png'
        action_hda_context_menu_favorite.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/{0}'.format(favorite_icon))))

        action_hda_context_menu_detail = hda_context_menu.addAction('Detail')
        action_hda_context_menu_detail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_format_quote_white.png')))
        #
        action_hda_make_context_menu_rename = hda_context_menu.addAction('Rename')
        action_hda_make_context_menu_rename.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_border_color_white.png')))
        #
        hda_context_menu.addSeparator()
        #
        hda_make_context_menu = QtWidgets.QMenu('Make', self)
        hda_make_context_menu.setIcon(QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_camera_white.png')))
        #
        action_hda_make_context_menu_thumbnail = hda_make_context_menu.addAction('Thumbnail')
        action_hda_make_context_menu_thumbnail.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_camera_alt_white.png')))
        #
        action_hda_make_context_menu_video = hda_make_context_menu.addAction('Video')
        action_hda_make_context_menu_video.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_videocam_white.png')))
        #
        hda_context_menu.addMenu(hda_make_context_menu)
        #
        hda_context_menu.addSeparator()
        action_hda_context_menu_remove = hda_context_menu.addAction('Delete')
        action_hda_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_delete_forever_white.png')))
        # 단축키 비활성화
        # action_hda_context_menu_remove.setShortcut(QtGui.QKeySequence(self.__shortcut_del_key))
        # History
        hist_context_menu = QtWidgets.QMenu('History', self)
        hist_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_query_builder_white.png')))
        # history actions
        action_hist_context_menu_ihda_history = hist_context_menu.addAction('iHDA')
        action_hist_context_menu_ihda_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_find_in_page_white.png')))
        action_hist_context_menu_note_history = hist_context_menu.addAction('Note')
        action_hist_context_menu_note_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_assignment_white.png')))
        hist_context_menu.addSeparator()
        action_hist_context_menu_remove_history = hist_context_menu.addAction('Delete')
        action_hist_context_menu_remove_history.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_delete_forever_white.png')))
        context_menu.addMenu(open_context_menu)
        context_menu.addMenu(hda_context_menu)
        context_menu.addMenu(hist_context_menu)
        context_menu.addSeparator()
        # refresh current data
        self.__curt_hda_item_field = index.data()
        self.__refresh_current_attribs()
        self.__set_hda_info_to_parms()

        if self.__curt_hda_item_data is None:
            return
        hip_dirpath = self.__curt_hda_item_data.get(public.Key.hip_dirpath)
        #
        action = context_menu.exec_(view.mapToGlobal(point))
        #
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(dirpath=self.__curt_hda_item_filepath)
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            hip_filepath = hip_dirpath / self.__curt_hda_item_data.get(public.Key.hip_filename)
            self.__open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_hda_context_menu_favorite:
            self.__hda_favorite()
        elif action == action_hda_context_menu_detail:
            self.__detail_view_ihda_data(data=self.__curt_hda_item_data)
        elif action == action_hda_make_context_menu_thumbnail:
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            IndividualHDA.__wrapper_execute_deferred(lambda: self.__slot_make_thumbnail(db_api=db_api))
        elif action == action_hda_make_context_menu_video:
            if public.IS_HOUDINI:
                frinfo = houdini_api.HoudiniAPI.frame_info()
                self.__make_videoinfo.sf = frinfo[0]
                self.__make_videoinfo.ef = frinfo[1]
                self.__make_videoinfo.fps = frinfo[2]
            self.__make_videoinfo.show()
        elif action == action_hda_make_context_menu_rename:
            self.__rename_ihda.clear_parms()
            self.__rename_ihda.set_old_ihda_name(self.__curt_hda_item_name)
            self.__rename_ihda.show()
        elif action == action_hda_context_menu_remove:
            if self.__is_icon_mode:
                indexes = self.__ihda_list_view.selectedIndexes()
            else:
                # table 모델은 이렇게 해야한다. 왜냐면 cell 선택시 모든 cell을 선택되어지도록 했는데
                # 이것 때문에 중복 index가 생겨 첫번째 컬럼을 명확시 지정하였다.
                indexes = self.__ihda_table_view.selectionModel().selectedRows(0)
            if not len(indexes):
                log_handler.LogHandler.log_msg(method=logging.info, msg='iHDA node is not selected')
                return
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setIcon(QtWidgets.QMessageBox.Question)
            msgbox.setWindowTitle('Remove iHDA Node')
            msgbox.setText(
                'Delete the <font color=red>"{0}"</font> selected iHDA nodes?'.format(len(indexes)))
            msgbox.setInformativeText(
                'All information about that node, including previews, video, thumbnails\n'
                'history and reocrds, will be deleted. (Folder/File/DB is also deleted)')
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgbox.setStyleSheet('QLabel {min-width: 500px;}')
            msgbox.resize(msgbox.sizeHint())
            reply = msgbox.exec_()
            if reply != QtWidgets.QMessageBox.Yes:
                return
            self.__remove_hda_item(indexes=indexes)
        elif action == action_hist_context_menu_ihda_history:
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            hda_name = self.__curt_hda_item_name
            hda_id = self.__curt_hda_item_id
            if not db_api.is_exist_hda_history(hda_key_id=hda_id):
                log_handler.LogHandler.log_msg(
                    method=logging.warning, msg='node history of "{0}" iHDA node does not exist'.format(hda_name))
                return
            self.__slot_select_view(index=self.__hist_view_idx)
            self.__select_hist_ihda_combobox_item(hkey_id=hda_id)
        elif action == action_hist_context_menu_note_history:
            hda_name = self.__curt_hda_item_name
            hda_id = self.__curt_hda_item_id
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            hist_note_data = db_api.get_hda_note_history(hda_key_id=hda_id, with_datetime=True)
            self.__slot_hda_note_history(hist_note_data=hist_note_data, hda_name=hda_name)
        elif action == action_hist_context_menu_remove_history:
            if self.__is_icon_mode:
                indexes = self.__ihda_list_view.selectedIndexes()
            else:
                # table 모델은 이렇게 해야한다. 왜냐면 cell 선택시 모든 cell을 선택되어지도록 했는데
                # 이것 때문에 중복 index가 생겨 첫번째 컬럼을 명확시 지정하였다.
                indexes = self.__ihda_table_view.selectionModel().selectedRows(0)
            if not len(indexes):
                log_handler.LogHandler.log_msg(method=logging.info, msg='iHDA node is not selected')
                return
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setWindowTitle('Delete iHDA node history')
            msgbox.setIcon(QtWidgets.QMessageBox.Question)
            msgbox.setText(
                'Delete the selected <font color=red>"{0}"</font> iHDA node history?'.format(len(indexes)))
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            reply = msgbox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            # player가 재생중이거나 일시정지 상태면 정지
            self.__video_player.player_stop()
            del_hist_data_lst = list()
            for index in sorted(indexes, key=lambda x: x.row(), reverse=True):
                if not index.isValid():
                    continue
                if self.__is_icon_mode:
                    hda_id = index.data(ihda_list_model.ListModel.id_role)
                    hda_name = index.data(ihda_list_model.ListModel.name_role)
                else:
                    hda_id = index.data(ihda_table_model.TableModel.id_role)
                    hda_name = index.data(ihda_table_model.TableModel.name_role)
                if db_api.is_exist_hda_note_history(hda_key_id=hda_id):
                    db_api.delete_hda_note_history(hda_key_id=hda_id)
                    log_handler.LogHandler.log_msg(
                        method=logging.info,
                        msg='all the note history of "{0}" iHDA node has been deleted'.format(hda_name))
                if not db_api.is_exist_hda_history(hda_key_id=hda_id):
                    log_handler.LogHandler.log_msg(
                        method=logging.warning, msg='node history of "{0}" iHDA node does not exist'.format(hda_name))
                    continue
                # 삭제할 히스토리 데이터 수거
                hist_data_lst = self.__ihda_history_model.get_hist_data_by_hkey_id_from_model(hkey_id=hda_id)
                del_hist_data_lst.extend(hist_data_lst)
                # video playlist 삭제
                # 현재 iHDA 노드의 모든 video file 정보
                video_filepath_lst = db_api.get_history_video_info(hda_key_id=hda_id)
                self.__delete_video_playlist(video_filepath_list=video_filepath_lst)
            # 히스토리 데이터 삭제
            for hist_data in sorted(
                    del_hist_data_lst, key=lambda x: x.get(public.Key.History.item_row), reverse=True):
                self.__delete_each_hist_ihda_item(hist_data=hist_data, db_api=db_api, verbose=True)
            self.__initialize_hist_current_attribs()
            self.__clear_hist_parms()
        else:
            pass

    def __build_context_category_menu(self, point):
        index = self.__ihda_category_view.indexAt(point)
        if not index.isValid():
            return

    def __build_context_record_menu(self, point):
        index = self.__ihda_record_view.indexAt(point)
        if not index.isValid():
            return
        item_type = index.data(ihda_record_model.RecordModel.record_type_role)
        if item_type == public.Type.root:
            return
        #
        hip_dirpath = index.data(ihda_record_model.RecordModel.hip_dirpath_role)
        hip_filepath = index.data(ihda_record_model.RecordModel.hip_filepath_role)
        hda_filepath = index.data(ihda_record_model.RecordModel.hda_filepath_role)
        record_data = index.data(ihda_record_model.RecordModel.record_data_role)
        pnode_path = index.data(ihda_record_model.RecordModel.pnode_path_role)
        #
        context_menu = QtWidgets.QMenu(self)
        #
        open_context_menu = QtWidgets.QMenu('Open', self)
        open_context_menu.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_donut_large_white.png')))
        #
        # hip folder
        action_open_context_hip_folder = open_context_menu.addAction('HIP Folder')
        action_open_context_hip_folder.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_folder_white.png')))
        # hip file
        action_open_context_hip_file = None
        if hip_filepath is not None:
            action_open_context_hip_file = open_context_menu.addAction('HIP File')
            action_open_context_hip_file.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/main/icons/hipfile.png')))
            open_context_menu.addSeparator()
        # iHDA folder
        action_open_context_ihda_folder = None
        if hda_filepath is not None:
            action_open_context_ihda_folder = open_context_menu.addAction('iHDA Folder')
            action_open_context_ihda_folder.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_folder_white.png')))
        # go to network
        action_context_menu_go_to_network = None
        if pnode_path is not None:
            action_context_menu_go_to_network = context_menu.addAction('Go To Network')
            action_context_menu_go_to_network.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_flight_takeoff_white.png')))
            context_menu.addAction(action_context_menu_go_to_network)
        # detail view
        action_context_menu_detail = None
        if record_data is not None:
            action_context_menu_detail = context_menu.addAction('Detail')
            action_context_menu_detail.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_format_quote_white.png')))
            context_menu.addAction(action_context_menu_detail)
        #
        action_context_menu_remove = context_menu.addAction('Delete')
        action_context_menu_remove.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_delete_forever_white.png')))
        # 단축키 비활성화
        # action_context_menu_remove.setShortcut(QtGui.QKeySequence(self.__shortcut_del_key))
        context_menu.addMenu(open_context_menu)
        context_menu.addSeparator()
        context_menu.addSeparator()
        context_menu.addAction(action_context_menu_remove)
        #
        action = context_menu.exec_(self.__ihda_record_view.mapToGlobal(point))
        #
        if action == action_open_context_ihda_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hda_filepath)
        elif action == action_open_context_hip_folder:
            ihda_system.IHDASystem.open_folder(dirpath=hip_dirpath)
        elif action == action_open_context_hip_file:
            self.__open_houdini_file(hip_filepath=hip_filepath)
        elif action == action_context_menu_go_to_network:
            IndividualHDA.__go_to_houdini_node(node_path=pnode_path)
        elif action == action_context_menu_detail:
            record_id = index.data(ihda_record_model.RecordModel.record_id_role)
            if record_id is None:
                return
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            record_data = db_api.get_only_detailview_record_data(record_id=record_id)
            self.__detail_view_record_data(record_data=record_data)
        elif action == action_context_menu_remove:
            self.__remove_selected_record_item(index=index)
        else:
            pass

    def __build_context_inside_menu(self, point):
        index = self.__ihda_inside_view.indexAt(point)
        if not index.isValid():
            return
        item_type = index.data(ihda_inside_model.InsideModel.node_type_role)
        if item_type == public.Type.root:
            return
        is_ihda_node = bool(item_type == public.Type.ihda)
        hda_id = index.data(ihda_inside_model.InsideModel.hda_id_role)
        #
        context_menu = QtWidgets.QMenu(self)
        #
        # go to node
        action_context_menu_go_to_node = context_menu.addAction('Go To Node')
        action_context_menu_go_to_node.setIcon(
            QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_flight_takeoff_white.png')))
        context_menu.addAction(action_context_menu_go_to_node)
        context_menu.addSeparator()
        #
        action_open_context_ihda_folder = None
        action_open_context_ihda_video = None
        action_context_menu_detail = None
        if is_ihda_node:
            open_context_menu = QtWidgets.QMenu('Open', self)
            open_context_menu.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_donut_large_white.png')))
            #
            # iHDA folder
            action_open_context_ihda_folder = open_context_menu.addAction('iHDA Folder')
            action_open_context_ihda_folder.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_folder_white.png')))
            open_context_menu.addSeparator()
            # iHDA video
            action_open_context_ihda_video = open_context_menu.addAction('iHDA Video')
            action_open_context_ihda_video.setIcon(
                QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_movie_white.png')))
            context_menu.addMenu(open_context_menu)
            context_menu.addSeparator()
        #
        action = context_menu.exec_(self.__ihda_inside_view.mapToGlobal(point))
        #
        if action == action_open_context_ihda_folder:
            if hda_id is None:
                return
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            hda_fpath = db_api.get_hda_filepath(hda_key_id=hda_id)
            ihda_system.IHDASystem.open_folder(dirpath=hda_fpath)
        elif action == action_open_context_ihda_video:
            if hda_id is None:
                return
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            hda_ver = index.data(ihda_inside_model.InsideModel.version_role)
            hda_name = index.data(ihda_inside_model.InsideModel.hda_org_name_role)
            video_info = db_api.get_hda_history_video_most_recent_by_ver(hda_key_id=hda_id, version=hda_ver)
            if video_info is None:
                log_handler.LogHandler.log_msg(
                    method=logging.warning, msg='"{0} (v{1})" iHDA node has no video'.format(hda_name, hda_ver))
                return
            self.__play_video_most_recent_by_version(video_info=video_info)
        elif action == action_context_menu_go_to_node:
            node_path = index.data(ihda_inside_model.InsideModel.node_path_role)
            IndividualHDA.__go_to_houdini_node(node_path=node_path)
        else:
            pass

    def __open_houdini_file(self, hip_filepath=None):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setWindowTitle('Open Houdini File')
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText('''
<font color=white size=3>Open the Houdini file?</font><br><br>
<font color=red size=5>[Note]</font> <font color=white size=4>Open the file with the new Houdini.</font>''')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.Yes:
            ihda_system.IHDASystem.open_hipfile_using_thread(hip_filepath)

    def __slot_hda_note_history(self, hist_note_data=None, hda_name=None):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle('iHDA note history')
        dialog.resize(840, 700)
        icon = QtGui.QIcon(QtGui.QPixmap(':/main/icons/viewport_logo_trans.png'))
        dialog.setWindowIcon(icon)
        font = QtGui.QFont()
        # if public.is_windows():
        #     font.setFamily("MS Shell Dlg 2")
        font.setPointSize(11)
        dialog.setFont(font)
        vertical_layout = QtWidgets.QVBoxLayout(dialog)
        vertical_layout.setContentsMargins(3, 3, 3, 3)
        plain_textedit = QtWidgets.QPlainTextEdit(dialog)
        note_syntax.NoteHighLighter(plain_textedit)
        plain_textedit.setReadOnly(True)
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_note_font_size, public.Name.PreferenceUI.cmb_note_font_style)
        font = QtGui.QFont()
        font.setFamily(font_style)
        font.setPointSize(font_size)
        plain_textedit.setFont(font)
        vertical_layout.addWidget(plain_textedit)
        if hist_note_data is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg='note history information of "{0}" iHDA node does not exist'.format(hda_name))
            return
        plain_textedit.appendPlainText('iHDA: {0}'.format(hda_name))
        for data in hist_note_data:
            ctime, ver, note = data
            res_contents = '''
                    ***** Save Time: {0}, iHDA Version: {1} *****
{2}
            '''.format(ctime, ver, note)
            plain_textedit.appendPlainText(res_contents)
            plain_textedit.appendPlainText('-' * 88)
        dialog.show()

    # hda_id와 item_row의 맵 데이터
    def __get_hda_id_row_map(self):
        return dict(imap(lambda x: (x.get(public.Key.hda_id), x.get(public.Key.item_row)), self.__ihda_data))

    # database에서 불필요한 데이터를 정리
    def __slot_db_cleanup(self):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setWindowTitle('iHDA Database Optimization')
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText('Cleanup unnecessary information from database?')
        msgbox.setDetailedText('NOTE: Don\'t worry. Only unused information is cleaned up.')
        chkbox = QtWidgets.QCheckBox(msgbox)
        chkbox.setText('Cleanup other info together')
        chkbox.setChecked(True)
        chkbox.setIcon(QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_query_builder_white.png')))
        chkbox.setToolTip('Cleanup other information together (history & record)')
        msgbox.setCheckBox(chkbox)
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.Yes:
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            item_row_dat = dict()
            for hda_info_dat in db_api.get_all_hda_fileinfo(user_id=self.__user):
                hda_id, hda_dirpath, hda_filename, hda_cate = hda_info_dat
                hda_dirpath = pathlib2.Path(hda_dirpath)
                hda_filepath = hda_dirpath / hda_filename
                if not hda_filepath.exists():
                    db_api.delete_hda_key_with_id(hda_key_id=hda_id)
                    item_row = self.__get_hda_model_row_by_hda_id(hda_id=hda_id)
                    if item_row is not None:
                        item_row_dat[item_row] = [hda_id, hda_cate]
                    log_handler.LogHandler.log_msg(
                        method=logging.info, msg='ID {0} iHDA information has been cleaned up'.format(hda_id))
            if len(item_row_dat):
                cate_lst = db_api.get_hda_category(user_id=self.__user)
                for hrow, hval in sorted(item_row_dat.iteritems(), reverse=True):
                    hid, hcate = hval
                    self.__remove_hda_data(item_row=hrow)
                    self.__delete_hist_combobox_ihda_item(hkey_id=hid)
                    self.__remove_category_item(category=hcate, category_list=cate_lst)
            if chkbox.isChecked():
                # history 정리
                item_row_lst = list()
                for hist_info_dat in db_api.get_all_hda_history_fileinfo(user_id=self.__user):
                    hist_id, hda_id, hda_dirpath, hda_filename = hist_info_dat
                    hda_dirpath = pathlib2.Path(hda_dirpath)
                    hda_filepath = hda_dirpath / hda_filename
                    if not hda_filepath.exists():
                        db_api.delete_hda_history(hist_id=hist_id)
                        self.__delete_hist_combobox_ihda_item(hkey_id=hda_id)
                        item_row = self.__ihda_history_model.get_hist_item_row_by_hist_id_from_model(hist_id=hist_id)
                        if item_row is not None:
                            insort_right(item_row_lst, item_row)
                        log_handler.LogHandler.log_msg(
                            method=logging.info,
                            msg='ID {0} history information has been cleaned up'.format(hist_id))
                hist_id_row_map = self.__ihda_history_model.get_hist_id_row_map_from_model()
                for item_row in reversed(item_row_lst):
                    if item_row in hist_id_row_map.values():
                        self.__ihda_history_model.remove_item(row=item_row)
                # record 정리
                self.__delete_unused_hda_record_info(db_api=db_api)
            log_handler.LogHandler.log_msg(method=logging.debug, msg='iHDA database optimization is complete')
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setWindowTitle('Cleanup iHDA Database')
            msgbox.setIcon(QtWidgets.QMessageBox.Warning)
            msgbox.setText('iHDA database optimization is complete.')
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            _ = msgbox.exec_()

    # 모든 ihda/note history 삭제, 최신 버전의 파일을 제외한 파일들 삭제
    def __slot_delete_all_history(self):
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        cnt_hda_hist = db_api.count_hda_history()
        cnt_hda_note_hist = db_api.count_hda_note_history()
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setWindowTitle('Delete all iHDA history')
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText('Delete all iHDA node\'s node/note history?')
        # chkbox = QtWidgets.QCheckBox(msgbox)
        # chkbox.setText('Delete All History Files')
        # chkbox.setChecked(True)
        # chkbox.setIcon(QtGui.QIcon(QtGui.QPixmap(':/main/icons/ic_delete_forever_white.png')))
        # chkbox.setToolTip('Delete all iHDA history files')
        # msgbox.setCheckBox(chkbox)
        msgbox.setDetailedText('''
All of them are deleted, leaving minimal data for data tracking.
iHDA node history: {0}
iHDA note history: {1}
        '''.format(cnt_hda_hist, cnt_hda_note_hist))
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msgbox.setStyleSheet('QLabel {min-width: 500px;}')
        msgbox.resize(msgbox.sizeHint())
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.Yes:
            # 만약 파일들까지 삭제한다면
            # if chkbox.isChecked():
            all_hkey_id = db_api.get_hda_key_id(user_id=self.__user)
            if all_hkey_id is None:
                return
            # player가 재생중이거나 일시정지 상태면 정지
            self.__video_player.player_stop()
            del_hist_data_lst = list()
            for hkey_id in sorted(all_hkey_id, reverse=True):
                # video playlist 삭제
                # 현재 iHDA 노드의 모든 video file 정보
                video_filepath_lst = db_api.get_history_video_info(hda_key_id=hkey_id)
                self.__delete_video_playlist(video_filepath_list=video_filepath_lst)
                hist_data_lst = self.__ihda_history_model.get_hist_data_by_hkey_id_from_model(hkey_id=hkey_id)
                del_hist_data_lst.extend(hist_data_lst)
            for hist_data in sorted(
                    del_hist_data_lst, key=lambda x: x.get(public.Key.History.item_row), reverse=True):
                self.__delete_each_hist_ihda_item(hist_data=hist_data, db_api=db_api, verbose=True)
            # note history 정보 삭제
            db_api.delete_hda_note_history()
            self.__initialize_hist_current_attribs()
            self.__clear_hist_parms()

    def __slot_preference(self):
        self.__set_is_ready()
        if self.__preference.is_ffmpeg_valid:
            self.__video_player.ffmpeg_dirpath = self.__preference.ffmpeg_dirpath
        # data 디렉토리 명시함으로써 주석처리 함.
        # if self.__preference.is_data_valid:
        #     if not self.__preference.data_final_dirpath.exists():
        #         self.__preference.data_final_dirpath.mkdir(parents=True)
        # app properties
        font_size, font_style = self.__get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size, public.Name.PreferenceUI.cmb_view_font_style)
        self.__ihda_list_model.set_font(style=font_style, size=font_size)
        self.__ihda_table_model.set_font(style=font_style, size=font_size)
        self.__ihda_history_model.set_font(style=font_style, size=font_size)
        self.__ihda_category_model.set_font(style=font_style, size=font_size)
        self.__ihda_record_model.set_font(style=font_style, size=font_size)
        self.__ihda_inside_model.set_font(style=font_style, size=font_size)
        treeview_icon_size = self.__get_treeview_properties()
        self.__set_tree_view_item_icon_size(treeview_icon_size)
        self.__set_view_item_icon_size(self.doubleSpinBox__zoom.value())
        # text view의 font size, style 적용
        IndividualHDA.__set_font_properties(
            self.textEdit__note,
            self.__get_font_properties(
                public.Name.PreferenceUI.spb_note_font_size, public.Name.PreferenceUI.cmb_note_font_style))
        IndividualHDA.__set_font_properties(
            self.textEdit__tag,
            self.__get_font_properties(
                public.Name.PreferenceUI.spb_tags_font_size, public.Name.PreferenceUI.cmb_tags_font_style))
        IndividualHDA.__set_font_properties(
            self.textBrowser__debug,
            self.__get_font_properties(
                public.Name.PreferenceUI.spb_debug_font_size, public.Name.PreferenceUI.cmb_debug_font_style))
        # padding 적용
        self.__set_view_padding(self.doubleSpinBox__zoom.value())
        # main icon size
        self.__set_main_default_icon_size()

    def __set_main_default_icon_size(self):
        icon_size = public.UISetting.dft_icon_size
        properties_data = self.__preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_main_icon_size in properties_data:
                icon_size = properties_data.get(public.Name.PreferenceUI.spb_main_icon_size)
        if public.IS_HOUDINI:
            icon_size = hou.ui.scaledSize(int(icon_size))
        self.toolBar.setIconSize(QtCore.QSize(icon_size, icon_size))
        for inst in self.__icon_variables():
            qsize = QtCore.QSize(icon_size, icon_size)
            inst.setIconSize(qsize)

    def __icon_variables(self):
        lst = self.centralwidget.findChildren(QtWidgets.QCheckBox)
        lst.extend(self.centralwidget.findChildren(QtWidgets.QPushButton))
        lst.extend(self.__video_player.findChildren(QtWidgets.QPushButton))
        lst.extend(self.__web_view.findChildren(QtWidgets.QPushButton))
        lst.extend(self.__preference.findChildren(QtWidgets.QToolButton))
        lst.extend(self.__rename_ihda.findChildren(QtWidgets.QPushButton))
        lst.extend(self.__make_videoinfo.findChildren(QtWidgets.QPushButton))
        return lst

    def __set_is_ready(self):
        self.__is_ready = False
        if self.__preference.is_data_valid:
            self.__is_ready = True
            self.centralwidget.setEnabled(True)

    # preview 디렉토리 삭제 함수
    @staticmethod
    def __remove_preview_dir(preview_dirpath=None):
        assert isinstance(preview_dirpath, pathlib2.Path)
        is_del = False
        if preview_dirpath.parent.exists():
            if preview_dirpath.parent.name == public.Name.preview_dirname:
                is_del = ihda_system.IHDASystem.remove_dir(dirpath=preview_dirpath.parent, verbose=False)
        return is_del

    # thumbnail 만드는 함수
    def __slot_make_thumbnail(self, db_api=None):
        if public.IS_HOUDINI:
            hda_dirpath = self.__curt_hda_item_data.get(public.Key.hda_dirpath)
            hda_name = self.__curt_hda_item_data.get(public.Key.hda_name)
            hda_version = self.__curt_hda_item_data.get(public.Key.hda_version)
            hda_id = self.__curt_hda_item_data.get(public.Key.hda_id)
            # thumbnail
            thumb_dirpath = houdini_api.HoudiniAPI.make_thumbnail_dirpath(hda_dirpath=hda_dirpath)
            thumb_filename = houdini_api.HoudiniAPI.make_thumbnail_filename(name=hda_name, version=hda_version)
            thumb_filepath = thumb_dirpath / thumb_filename
            if not thumb_dirpath.exists():
                thumb_dirpath.mkdir(parents=True)
            houdini_api.HoudiniAPI.create_thumbnail(output_filepath=thumb_filepath)
            is_update_thumb = db_api.update_thumbnail_info(
                hda_key_id=hda_id, dirpath=thumb_dirpath, filename=thumb_filename, version=hda_version)
            # model에서 새로운 파일을 새롭게 읽을 수 있도록 thumb_filepath인자에 값을 배정하지 않았다.
            # self.__update_pixmap_thumbnail(hkey_id=hda_id, thumb_filepath=pathlib2.Path())
            self.__update_pixmap_thumbnail(hkey_id=hda_id, thumb_filepath=thumb_filepath)
            hist_id = self.__ihda_history_model.get_history_id_from_model(hkey_id=hda_id, version=hda_version)
            if hist_id is not None:
                self.__update_pixmap_hist_thumbnail(hist_id=hist_id, thumb_filepath=thumb_filepath)
            if is_update_thumb:
                log_handler.LogHandler.log_msg(method=logging.info, msg='thumbnail update completed')
        else:
            log_handler.LogHandler.log_msg(method=logging.warning, msg='run on the houdini')

    # video 만드는 시작 함수
    def __slot_make_video(self):
        if not self.__preference.is_ffmpeg_valid:
            log_handler.LogHandler.log_msg(method=logging.error, msg='ffmpeg is not installed')
            return
        if not public.IS_HOUDINI:
            log_handler.LogHandler.log_msg(method=logging.warning, msg='run on the houdini')
            return
        new_frinfo = [self.__make_videoinfo.sf, self.__make_videoinfo.ef, self.__make_videoinfo.fps]
        num_frame = (new_frinfo[1] - new_frinfo[0]) + 1
        if num_frame <= 0:
            log_handler.LogHandler.log_msg(method=logging.error, msg='frame range is wrong')
            return
        self.__loading_show()
        data = self.__curt_hda_item_data
        hda_dirpath = data.get(public.Key.hda_dirpath)
        hda_name = data.get(public.Key.hda_name)
        hda_version = data.get(public.Key.hda_version)
        hda_id = data.get(public.Key.hda_id)
        preview_dirpath = houdini_api.HoudiniAPI.make_preview_dirpath(hda_dirpath=hda_dirpath, version=hda_version)
        preview_filename = houdini_api.HoudiniAPI.make_preview_filename(name=hda_name, version=hda_version)
        preview_filepath = IndividualHDA.__make_preview(
            preview_dirpath=preview_dirpath, preview_filename=preview_filename, frinfo=new_frinfo,
            res=self.__make_videoinfo.get_resolution(), is_beauty=self.__make_videoinfo.is_beautypass,
            is_initsim=self.__make_videoinfo.is_init_sim, is_motion=self.__make_videoinfo.is_motionblur,
            is_crop=self.__make_videoinfo.is_crop_mask)
        if preview_filepath is None:
            is_del = IndividualHDA.__remove_preview_dir(preview_dirpath=preview_dirpath)
            self.__loading_close()
            return
        # $F4 --> %04d
        preview_filepath = preview_filepath.with_name(self.__regex_squence_str.sub('%04d', preview_filepath.name))
        log_handler.LogHandler.log_msg(
            method=logging.info, msg='[{0}-{1}, fps: {2}]'.format(new_frinfo[0], new_frinfo[1], new_frinfo[2]))
        meta_data = {
            public.Name.FFmpeg.Metadata.author: self.__user,
            public.Name.FFmpeg.Metadata.year: str(QtCore.QDate.currentDate().toString('yyyy')),
            public.Name.FFmpeg.Metadata.title: hda_name,
            public.Name.FFmpeg.Metadata.desc: '{0} Video'.format(public.Name.hda_prefix_str)
        }
        video_dirpath = houdini_api.HoudiniAPI.make_video_dirpath(hda_dirpath=hda_dirpath)
        video_filename = houdini_api.HoudiniAPI.make_video_filename(name=hda_name, version=hda_version)
        video_filepath = IndividualHDA.__make_video(
            ffmpeg_dirpath=self.__preference.ffmpeg_dirpath,
            preview_filepath=preview_filepath, video_dirpath=video_dirpath, video_filename=video_filename,
            sf=new_frinfo[0], num_frame=num_frame, fps=new_frinfo[2], meta_data=meta_data)
        if video_filepath is None:
            self.__loading_close()
            return
        comment = ''
        #
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        row = self.__curt_hda_item_row
        get_video_path = db_api.get_video_info(hda_key_id=hda_id)
        is_video_db_done = False
        if get_video_path is None:
            is_insert_video = db_api.insert_video_info(
                hda_key_id=hda_id, dirpath=video_dirpath, filename=video_filename, version=hda_version)
            if is_insert_video is not None:
                is_video_db_done = True
                comment = 'VIDEO (INSERT)'
                log_handler.LogHandler.log_msg(method=logging.info, msg='video insertion complete')
        else:
            is_update_video = db_api.update_video_info(
                hda_key_id=hda_id, dirpath=video_dirpath, filename=video_filename, version=hda_version)
            if is_update_video is not None:
                is_video_db_done = True
                comment = 'VIDEO (UPDATE)'
                log_handler.LogHandler.log_msg(method=logging.info, msg='video update complete')
        if is_video_db_done:
            self.__change_hda_data(row=row, key=public.Key.video_dirpath, val=video_dirpath)
            self.__change_hda_data(row=row, key=public.Key.video_filename, val=video_filename)
            # history
            self.__insert_hist_db_from_curt_hist_data(db_api=db_api, comment=comment)
        is_del = IndividualHDA.__remove_preview_dir(preview_dirpath=preview_dirpath)
        self.__loading_close()

    @staticmethod
    def __make_preview(
            preview_dirpath=None, preview_filename=None, frinfo=None, res=None,
            is_beauty=None, is_initsim=None, is_motion=None, is_crop=None):
        assert isinstance(preview_dirpath, pathlib2.Path)
        preview_filepath = preview_dirpath / preview_filename
        for pfile in preview_dirpath.glob('*.jpg'):
            pfile.unlink()
        if not preview_dirpath.exists():
            preview_dirpath.mkdir(parents=True)
        is_done_preview = houdini_api.HoudiniAPI.create_preview(
            output_filepath=preview_filepath, frame_info=frinfo, resolution=res,
            is_beautypass_only=is_beauty, is_init_sim=is_initsim, is_motionblur=is_motion, is_crop_out_mask=is_crop)
        if not is_done_preview:
            log_handler.LogHandler.log_msg(method=logging.error, msg='failed to create preview')
            ihda_system.IHDASystem.remove_dir(dirpath=preview_dirpath, verbose=False)
            return None
        return preview_filepath

    @staticmethod
    def __make_video(
            ffmpeg_dirpath=None, preview_filepath=None, video_dirpath=None, video_filename=None,
            sf=None, num_frame=None, fps=None, meta_data=None):
        assert isinstance(video_dirpath, pathlib2.Path)
        video_filepath = video_dirpath / video_filename
        if not video_dirpath.exists():
            video_dirpath.mkdir(parents=True)
        ff_api = ffmpeg_api.FFmpegAPI()
        exitcode = ff_api.make_image_seq_to_video(
            ffmpeg_dirpath=ffmpeg_dirpath, image_seq=preview_filepath, output=video_filepath,
            sf=sf, num_frame=num_frame, fps=fps, meta_data=meta_data
        )
        ihda_system.IHDASystem.remove_dir(dirpath=preview_filepath.parent, verbose=False)
        #
        if exitcode != 0:
            log_handler.LogHandler.log_msg(method=logging.error, msg='video creation failed')
            ihda_system.IHDASystem.remove_dir(dirpath=video_dirpath, verbose=False)
            return None
        log_handler.LogHandler.log_msg(method=logging.info, msg='video creation completed')
        return video_filepath

    def __hda_favorite(self):
        if self.__curt_hda_item_data is None:
            log_handler.LogHandler.log_msg(method=logging.error, msg='no node selected ')
            return
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        hda_id = self.__curt_hda_item_id
        is_update = db_api.update_hda_favorite(hda_key_id=hda_id)
        if bool(is_update):
            row = self.__curt_hda_item_row
            key = public.Key.is_favorite_hda
            val = self.__curt_hda_item_data.get(public.Key.is_favorite_hda) ^ 1
            hda_name = self.__curt_hda_item_name
            self.__change_hda_data(row=row, key=key, val=val)
            if val:
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg='the \"{0}\" node has been set as a favorite node'.format(hda_name))
            else:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='the \"{0}\" node has been released from the favorites node'.format(hda_name))

    def __remove_selected_record_item(self, index=None):
        if not index.isValid():
            return
        record_data_name = index.data(QtCore.Qt.DisplayRole)
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setWindowTitle('Remove iHDA Record Information')
        msgbox.setText(
            'Are you sure you want to delete the selected "{0}" record information?'.format(record_data_name))
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.No:
            return
        record_id_list = self.__ihda_record_model.remove_selected_record_data(index=index)
        # DB 삭제
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        for record_id in sorted(record_id_list):
            is_removed = db_api.delete_hda_record(record_id=record_id)
            if is_removed:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='"{0}" data on record ID {1} has been deleted'.format(record_data_name, record_id))
        # 유효한 데이터가 남아 있지 않은 껍데기 데이터 삭제하는 함수 호출
        self.__ihda_record_model.remove_invalid_hull_record_item_model()
        self.label__loc_record_count.setText(str(self.__ihda_record_proxy_model.get_row_count()))

    def __remove_hist_item(self):
        indexes = self.__ihda_history_view.selectionModel().selectedRows(0)
        if not len(indexes):
            log_handler.LogHandler.log_msg(method=logging.info, msg='iHDA history is not selected')
            return
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setWindowTitle('Remove iHDA History Node')
        msgbox.setText(
            'Delete the <font color=red>"{0}"</font> selected iHDA nodes?\n'
            'File/DB is also deleted'.format(len(indexes))
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.Yes:
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            # player가 재생중이거나 일시 정지상태면 정지
            self.__video_player.player_stop()
            for index in sorted(indexes, key=lambda x: x.row(), reverse=True):
                if not index.isValid():
                    continue
                hist_data = index.data(ihda_history_model.HistoryModel.data_role)
                self.__delete_each_hist_ihda_item(hist_data=hist_data, db_api=db_api, verbose=True)
        self.__initialize_hist_current_attribs()
        self.__clear_hist_parms()

    def __remove_hda_item(self, indexes=None):
        db_api = IndividualHDA.__db_api_wrap()
        if db_api is None:
            return
        # player가 재생중이거나 일시 정지상태면 정지
        self.__video_player.player_stop()
        # 삭제할 히스토리 데이터 수거
        del_hist_data_lst = list()
        # iHDA 노드 데이터 삭제
        for index in sorted(indexes, key=lambda x: x.row(), reverse=True):
            if not index.isValid():
                continue
            if self.__is_icon_mode:
                hda_id = index.data(ihda_list_model.ListModel.id_role)
                hda_name = index.data(ihda_list_model.ListModel.name_role)
                hda_dirpath = index.data(ihda_list_model.ListModel.filepath_role).parent
                hda_cate = index.data(ihda_list_model.ListModel.cate_role)
                item_row = index.data(ihda_list_model.ListModel.row_role)
            else:
                hda_id = index.data(ihda_table_model.TableModel.id_role)
                hda_name = index.data(ihda_table_model.TableModel.name_role)
                hda_dirpath = index.data(ihda_table_model.TableModel.filepath_role).parent
                hda_cate = index.data(ihda_table_model.TableModel.cate_role)
                item_row = index.data(ihda_table_model.TableModel.row_role)
            self.__delete_ihda_item(
                hda_id=hda_id, hda_cate=hda_cate, hda_name=hda_name,
                hda_dirpath=hda_dirpath, item_row=item_row, db_api=db_api)
            # 삭제할 히스토리 데이터 수거
            hist_data_lst = self.__ihda_history_model.get_hist_data_by_hkey_id_from_model(hkey_id=hda_id)
            del_hist_data_lst.extend(hist_data_lst)
        #
        # 히스토리 데이터 삭제 (DB는 삭제 안해도 된다. hda 데이터 지우면 자동 삭제 됨)
        # iHDA 데이터를 지우면 constraint로 인하여 history 데이터도 지워져서 DB는 지울 필요 없다.
        for hist_data in sorted(
                del_hist_data_lst, key=lambda x: x.get(public.Key.History.item_row), reverse=True):
            del_hist_row = hist_data.get(public.Key.History.item_row)
            del_hist_id = hist_data.get(public.Key.History.hist_id)
            del_hda_id = hist_data.get(public.Key.History.hda_id)
            self.__ihda_history_model.remove_item(row=del_hist_row)
            self.__remove_pixmap_hist_thumbnail(hist_id=del_hist_id)
            # 히스토리 콤보박스 아이템 삭제
            self.__delete_hist_combobox_ihda_item(hkey_id=del_hda_id)
        #
        self.__initialize_current_attribs()
        self.__initialize_hist_current_attribs()
        self.__clear_parms()
        self.__clear_hist_parms()
        self.label__loc_record_count.setText(str(self.__ihda_record_proxy_model.get_row_count()))

    # iHDA 노드의 video playlist 아이템 제거
    def __delete_video_playlist(self, video_filepath_list=None):
        for video_filepath in video_filepath_list:
            # iHDA video playlist 아이템 삭제 (이것을 삭제하지 않은 시, 파일이 삭제되지 않는다)
            self.__video_player.delete_playlist_item_by_filepath(filepath=video_filepath)

    # hda_id로 해당 모델의 row를 얻는 함수
    def __get_hda_model_row_by_hda_id(self, hda_id=None):
        for row_data in self.__ihda_data:
            if hda_id == row_data.get(public.Key.hda_id):
                return row_data.get(public.Key.item_row)
        return None

    def __remove_hda_data(self, item_row=None):
        self.__ihda_list_model.remove_item(row=item_row)
        self.__ihda_table_model.remove_item(row=item_row)
        del self.__ihda_data[item_row]

    def __delete_ihda_item(
            self, hda_id=None, hda_cate=None, hda_name=None, hda_dirpath=None,
            item_row=None, db_api=None):
        assert isinstance(hda_dirpath, pathlib2.Path)
        self.__remove_hda_data(item_row=item_row)
        # record 데이터 삭제
        self.__ihda_record_model.remove_record_item_by_hda_id(hda_id=hda_id)
        #
        self.__remove_pixmap_ihda(hkey_id=hda_id)
        self.__remove_pixmap_thumbnail(hkey_id=hda_id)
        # playlist 제거
        # 현재 iHDA 노드의 모든 video file 정보
        video_filepath_lst = db_api.get_history_video_info(hda_key_id=hda_id)
        self.__delete_video_playlist(video_filepath_list=video_filepath_lst)
        is_deleted = ihda_system.IHDASystem.remove_dir(dirpath=hda_dirpath, verbose=False)
        if is_deleted:
            rowcnt = db_api.delete_hda_key_with_id(hda_key_id=hda_id)
            if rowcnt is None:
                return
            if bool(rowcnt):
                cate_lst = db_api.get_hda_category(user_id=self.__user)
                self.__remove_category_item(category=hda_cate, category_list=cate_lst)
                log_handler.LogHandler.log_msg(
                    method=logging.info, msg='"{0}" iHDA node has been removed'.format(hda_name))

    # 단일 히스토리 아이템 삭제
    def __delete_each_hist_ihda_item(self, hist_data=None, db_api=None, verbose=True):
        hda_id = hist_data.get(public.Key.History.hda_id)
        hist_id = hist_data.get(public.Key.History.hist_id)
        hda_name = hist_data.get(public.Key.History.org_hda_name)
        row = hist_data.get(public.Key.History.item_row)
        hda_ver = hist_data.get(public.Key.History.version)
        hda_dirpath = hist_data.get(public.Key.History.ihda_dirpath)
        hda_filename = hist_data.get(public.Key.History.ihda_filename)
        hda_filepath = hda_dirpath / hda_filename
        thumb_dirpath = hist_data.get(public.Key.History.thumb_dirpath)
        video_dirpath = hist_data.get(public.Key.History.video_dirpath)
        # 가장 최근의 히스토리라면, 삭제를 진행하지 않는다.
        if db_api.is_most_recent_ihda_history(hda_key_id=hda_id, hist_id=hist_id):
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.warning,
                    msg='[{0}/{1}] node is the most recent iHDA history. it cannot be deleted'.format(
                        hda_name, hda_ver))
            return False
        self.__ihda_history_model.remove_item(row=row)
        self.__delete_hist_combobox_ihda_item(hkey_id=hda_id)
        self.__remove_pixmap_hist_thumbnail(hist_id=hist_id)
        # 만약 마지막 버전의 히스토리가 아니라면, 파일 삭제
        if not db_api.is_ihda_lastest_version(hda_key_id=hda_id, version=hda_ver):
            ihda_system.IHDASystem.remove_file(filepath=hda_filepath, verbose=False)
            if thumb_dirpath is not None:
                thumb_filename = hist_data.get(public.Key.History.thumb_filename)
                thumb_filepath = thumb_dirpath / thumb_filename
                ihda_system.IHDASystem.remove_file(filepath=thumb_filepath, verbose=False)
            if video_dirpath is not None:
                video_filename = hist_data.get(public.Key.History.video_filename)
                video_filepath = video_dirpath / video_filename
                # iHDA video playlist 아이템 삭제 (이것을 삭제하지 않은 시, 파일이 삭제되지 않는다)
                self.__video_player.delete_playlist_item_by_filepath(filepath=video_filepath)
                ihda_system.IHDASystem.remove_file(filepath=video_filepath, verbose=False)
        rowcnt = db_api.delete_hda_history(hda_key_id=hda_id, hist_id=hist_id)
        if bool(rowcnt):
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='[{0}/{1}] iHDA history removed'.format(hda_name, hda_ver))
            return True
        return False

    def __delete_hist_combobox_ihda_item(self, hkey_id=None):
        # history가 존재하지 않는다면
        if not self.__ihda_history_model.is_exist_ihda_item_from_model(hkey_id=hkey_id):
            for idx in range(self.comboBox__hist_ihda_node.count()):
                hid = self.comboBox__hist_ihda_node.itemData(idx)
                if hkey_id == hid:
                    self.comboBox__hist_ihda_node.removeItem(idx)

    def __clear_hist_parms(self):
        self.label__hist_cnt.setText(str(self.__ihda_history_proxy_model.rowCount()))
        # self.comboBox__hist_ihda_node.setCurrentIndex(0)

    def __clear_parms(self):
        self.label__hda_count.setText(str(self.__ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self.__get_category_count()))
        self.textEdit__note.clear()
        self.textEdit__tag.clear()
        self.label__tags.clear()

    def __detail_view_ihda_data(self, data=None):
        detailview = detail_view.DetailView(parent=self)
        detailview.show_detail_ihda_data(data=data, is_histview=self.__is_ihda_history_view)

    def __detail_view_record_data(self, record_data=None):
        if record_data is None:
            return
        detailview = detail_view.DetailView(parent=self)
        detailview.show_detail_record_data(data=record_data)

    @staticmethod
    def __change_org_node_name(parent_node=None, node_name=None):
        for child in parent_node.children():
            if child.name() == node_name:
                child.setName(child.name() + '_', unique_name=True)

    def __import_hda_into_houdini(self, parent_node=None, position=None, data=None):
        is_record_data = data.get(public.Key.Record.record_id)
        if self.__is_ihda_history_view:
            hda_dirpath = data.get(public.Key.History.ihda_dirpath)
            hda_filename = data.get(public.Key.History.ihda_filename)
            hda_filepath = hda_dirpath / hda_filename
            hda_name = data.get(public.Key.History.org_hda_name)
            hda_type_name = data.get(public.Key.History.node_type_name)
            hda_id = data.get(public.Key.hda_id)
        else:
            # record 데이터가 아니라면
            if is_record_data is None:
                hda_dirpath = data.get(public.Key.hda_dirpath)
                hda_filename = data.get(public.Key.hda_filename)
                hda_filepath = hda_dirpath / hda_filename
                hda_name = data.get(public.Key.hda_name)
                hda_type_name = data.get(public.Key.node_type_name)
                hda_id = data.get(public.Key.hda_id)
            # record 데이터라면
            else:
                hda_dirpath = data.get(public.Key.Record.hda_dirpath)
                hda_filename = data.get(public.Key.Record.hda_filename)
                hda_filepath = hda_dirpath / hda_filename
                # model/data에서는 version과 함께 새로운 이름 쓰고 있어서 오리지날 이름으로 가져와야 함.
                hda_name = data.get(public.Key.Record.org_node_name)
                hda_type_name = data.get(public.Key.Record.node_type)
                hda_id = data.get(public.Key.Record.hda_id)
        assert isinstance(hda_dirpath, pathlib2.Path)
        # 만약 hda 파일이 존재하지 않는다면
        if not hda_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='')
            return None
        # 임포트하려는 노드이름이 현재 네트워크에 존재한다면
        IndividualHDA.__change_org_node_name(parent_node=parent_node, node_name=hda_name)
        node = houdini_api.HoudiniAPI.import_individual_hda_into_houdini(
            node_filepath=hda_filepath, parent_node=parent_node,
            position=position, node_name=hda_name, node_type_name=hda_type_name)
        if node is None:
            return None
        #
        if not self.__is_ihda_history_view:
            if is_record_data:
                hda_item_row = self.__get_hda_id_row_map().get(hda_id)
                load_count = self.__ihda_data[hda_item_row].get(public.Key.hda_load_count) + 1
                self.__change_hda_data(row=hda_item_row, key=public.Key.hda_load_count, val=load_count)
            else:
                load_count = data.get(public.Key.hda_load_count) + 1
                self.__change_hda_data(row=self.__curt_hda_item_row, key=public.Key.hda_load_count, val=load_count)
        return node

    def __extract_subnet(self, node=None, note_contents=None, hda_name=''):
        if hasattr(node, 'extractAndDelete'):
            self.__create_sticky_netbox(node=node, note_contents=note_contents, hda_name=hda_name)
            node.extractAndDelete()

    def __create_sticky_netbox(self, node=None, note_contents=None, hda_name='', items=()):
        # iHDA 노트 내용을 Houdini Sticky Note로
        if self.actionSticky_Note.isChecked():
            net_item = map(lambda x: x, items)
            # hda note의 내용이 있다면, subnet안에 sticky note 생성 후 내용 입력
            sticky = self.__hda_note_to_sticky_note(node=node, note_contents=note_contents)
            if sticky is None:
                log_handler.LogHandler.log_msg(
                    method=logging.info,
                    msg='content of the iHDA note was empty, so didn\'t create houdini sticky note')
                if len(net_item) == 1:
                    return
            else:
                if len(net_item):
                    sticky.move(houdini_api.HoudiniAPI.items_position(items=items))
                    net_item.append(sticky)
                else:
                    sticky.move(houdini_api.HoudiniAPI.items_position(items=node.allItems()))
            # networkbox 생성
            net_box = houdini_api.HoudiniAPI.create_network_box(node=node, comment=hda_name, items=net_item)

    def __set_node_connections(self, node=None, input_connectors=None, output_connectors=None):
        if self.actionNull.isChecked():
            pass
        elif self.actionInput.isChecked():
            houdini_api.HoudiniAPI.set_node_input_connections(node=node, connection_lst=input_connectors)
        elif self.actionOuput.isChecked():
            houdini_api.HoudiniAPI.set_node_output_connections(node=node, connection_lst=output_connectors)
        else:
            houdini_api.HoudiniAPI.set_node_input_connections(node=node, connection_lst=input_connectors)
            houdini_api.HoudiniAPI.set_node_output_connections(node=node, connection_lst=output_connectors)

    @property
    def __hda_note(self):
        try:
            # return unicode(self.textEdit__note.toPlainText(), 'utf-8')
            return self.textEdit__note.toPlainText().decode('utf8')
        except TypeError:
            return self.textEdit__note.toPlainText()

    def __slot_zoomin(self):
        zoom_val = self.doubleSpinBox__zoom.value() + public.UISetting.interval_zoom_value
        if zoom_val > public.UISetting.max_zoom_value:
            zoom_val = public.UISetting.max_zoom_value
        self.doubleSpinBox__zoom.setValue(zoom_val)

    def __slot_zoomout(self):
        zoom_val = self.doubleSpinBox__zoom.value() - public.UISetting.interval_zoom_value
        if zoom_val < public.UISetting.min_zoom_value:
            zoom_val = public.UISetting.min_zoom_value
        self.doubleSpinBox__zoom.setValue(zoom_val)

    def __slot_zoom_value(self, zoom_val):
        self.__set_view_item_icon_size(zoom_val)
        log_handler.LogHandler.log_msg(method=logging.info, msg='zoom value: {0} %'.format(zoom_val))

    def __set_tree_view_item_icon_size(self, val):
        # treeview는 zoom 영향이 없도록. 이것은 preference에서만 조절 할 수 있다.
        self.__ihda_category_model.set_icon_size(val)
        self.__ihda_record_model.set_icon_size(val)
        self.__ihda_inside_model.set_icon_size(val)
        self.__ihda_category_view.expandAll()
        self.__ihda_record_view.expandAll()
        self.__ihda_inside_view.expandAll()

    def __set_view_padding(self, val):
        tableview_icon_size, tableview_thumb_size = self.__get_tableview_properties(val)
        # get padding
        pad_listview = self.__get_padding_properties(
            public.UISetting.padding_listview, public.Name.PreferenceUI.pad_listview)
        pad_tableview = self.__get_padding_properties(
            public.UISetting.padding_tableview, public.Name.PreferenceUI.pad_tableview)
        pad_history = self.__get_padding_properties(
            public.UISetting.padding_history, public.Name.PreferenceUI.pad_history)
        pad_category = self.__get_padding_properties(
            public.UISetting.padding_category, public.Name.PreferenceUI.pad_category)
        pad_record = self.__get_padding_properties(
            public.UISetting.padding_record, public.Name.PreferenceUI.pad_record)
        pad_inside = self.__get_padding_properties(
            public.UISetting.padding_inside, public.Name.PreferenceUI.pad_inside)
        # set padding
        self.__ihda_list_model.set_padding(pad_listview)
        self.__ihda_category_model.set_padding(pad_category)
        self.__ihda_record_model.set_padding(pad_record)
        self.__ihda_inside_model.set_padding(pad_inside)
        # inside model 구현 되면 추가
        # tableview
        if self.__is_show_thumbnail:
            vertical_cell_size = tableview_thumb_size
        else:
            vertical_cell_size = tableview_icon_size
        self.__ihda_table_view.verticalHeader().setDefaultSectionSize(vertical_cell_size + pad_tableview)
        self.__ihda_history_view.verticalHeader().setDefaultSectionSize(tableview_thumb_size + pad_history)

    def __set_view_item_icon_size(self, val):
        listview_icon_size, listview_thumb_size = self.__get_listview_properties(val)
        tableview_icon_size, tableview_thumb_size = self.__get_tableview_properties(val)
        #
        self.__ihda_list_model.set_icon_size(icon_size=listview_icon_size, thumb_size=listview_thumb_size)
        self.__ihda_table_model.set_icon_size(icon_size=tableview_icon_size, thumb_size=tableview_thumb_size)
        self.__ihda_history_model.set_icon_size(icon_size=tableview_icon_size, thumb_size=tableview_thumb_size)
        # tableview
        if self.__is_show_thumbnail:
            vertical_cell_size = tableview_thumb_size
        else:
            vertical_cell_size = tableview_icon_size
        self.__ihda_table_view.verticalHeader().setDefaultSectionSize(vertical_cell_size)
        self.__ihda_history_view.verticalHeader().setDefaultSectionSize(tableview_thumb_size)

    @property
    def __is_show_thumbnail(self):
        return self.pushButton__thumbnail.isChecked()

    @staticmethod
    def __get_ratio_icon_size(val):
        return val / 100.0

    @staticmethod
    def __set_curt_datetime_to_note(inst, flag):
        if flag:
            datetime_text = IndividualHDA.__reshape_datetime(QtCore.QDateTime.currentDateTime())
            text = '{0}\n'.format(datetime_text)
            # inst.setPlainText('%s\n\n%s' % (text, inst.toPlainText()))
            cursor = inst.textCursor()
            cursor.movePosition(cursor.End)
            cursor.insertText(text)
            scroll_bar = inst.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

    @staticmethod
    def __set_move_cursor_textedit(inst):
        cursor = inst.textCursor()
        cursor.movePosition(cursor.End)
        scroll_bar = inst.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    @staticmethod
    def __reshape_datetime(inst_datetime):
        try:
            inst_date = inst_datetime.date()
            inst_time = inst_datetime.time()
        except AttributeError:
            inst_date = inst_datetime.toDate()
            inst_time = inst_datetime.toTime()
        created_date = inst_date.toString(public.Value.qt_date_fmt_str)
        inst_week = inst_date.dayOfWeek()
        created_week = QtCore.QDate.longDayName(inst_week)
        created_time = inst_time.toString('hh:mm:ss AP')
        return '{0} {1} {2}'.format(created_date, created_week, created_time)

    @staticmethod
    def __split_tag_string(tag_str=''):

        hda_tag = map(
            lambda x: x.strip().strip('\n').strip('\r').strip('\t'),
            filter(lambda x: len(x), tag_str.split('#'))
        )
        return sorted(list(set(hda_tag)))

    @staticmethod
    def __set_tag_string(tag_lst):
        return ' '.join(map(lambda x: '#' + x, sorted(tag_lst)))

    def __slot_save_note_tags(self, choice='note'):
        if self.__curt_hda_item_data is None:
            log_handler.LogHandler.log_msg(method=logging.warning, msg='iHDA node not clicked')
            return
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setWindowTitle('Save iHDA {0}s'.format(choice))
        msgbox.setText('Save {0}s to "{1} ({2})" path iHDA node?'.format(
            choice, self.__curt_hda_item_name, self.__curt_hda_item_cate))
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.Yes:
            db_api = IndividualHDA.__db_api_wrap()
            if db_api is None:
                return
            if choice == 'note':
                is_exist_note = db_api.is_exist_note(hda_key_id=self.__curt_hda_item_id)
                if not is_exist_note:
                    db_api.insert_note_info(hda_key_id=self.__curt_hda_item_id, note=self.__hda_note)
                else:
                    db_api.update_note_info(hda_key_id=self.__curt_hda_item_id, note=self.__hda_note)
                self.__change_hda_data(row=self.__curt_hda_item_row, key=public.Key.hda_note, val=self.__hda_note)
            elif choice == 'tag':
                is_exist_tag = db_api.is_exist_tag(hda_key_id=self.__curt_hda_item_id)
                tag_lst = IndividualHDA.__split_tag_string(tag_str=self.__hda_tags)
                if not is_exist_tag:
                    db_api.insert_tag_info(hda_key_id=self.__curt_hda_item_id, tag_lst=tag_lst)
                else:
                    db_api.update_tag_info(hda_key_id=self.__curt_hda_item_id, tag_lst=tag_lst)
                self.__set_label_tags(tag_lst)
                self.__change_hda_data(row=self.__curt_hda_item_row, key=public.Key.hda_tags, val=tag_lst)
                self.__ihda_history_model.update_item_data_by_hkey_id_from_model(
                    hkey_id=self.__curt_hda_item_id, key=public.Key.History.tags, val=tag_lst)
            else:
                log_handler.LogHandler.log_msg(method=logging.error, msg='invalid value (note/tag)')
                return
            log_handler.LogHandler.log_msg(
                method=logging.info, msg='{0}s from the "{1} ({2})" iHDA node have been saved'.format(
                    choice, self.__curt_hda_item_name, self.__curt_hda_item_cate))

    @property
    def __hda_tags(self):
        return self.textEdit__tag.toPlainText().strip()

    @property
    def __is_icon_mode(self):
        return self.pushButton__icon_mode.isChecked()

    @property
    def __is_ihda_history_view(self):
        return self.stackedWidget__whole.currentIndex() == self.__hist_view_idx

    def resizeEvent(self, event):
        self.__loading.resize(event.size())
        self.__dragdrop_overlay.resize(event.size())
        super(IndividualHDA, self).resizeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(public.Type.mime_type):
            self.__dragdrop_overlay_show(text='Drop the iHDA node onto the network', fontsize=15)
            event.setDropAction(QtCore.Qt.CopyAction)
            event.acceptProposedAction()
        else:
            super(IndividualHDA, self).dragEnterEvent(event)

    def __slot_stackedwidget_hda_infos(self):
        if self.pushButton__hda_info.isChecked():
            self.stackedWidget__hda_infos.setCurrentIndex(0)
        elif self.pushButton__hda_loc_record.isChecked():
            self.stackedWidget__hda_infos.setCurrentIndex(1)
        elif self.pushButton__hda_inside_node_view.isChecked():
            self.stackedWidget__hda_infos.setCurrentIndex(2)

    def __slot_cfg_reset(self):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setWindowTitle('iHDA Reset APP Properties')
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText('Do you want to reset app properties?')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec_()
        if reply == QtWidgets.QMessageBox.No:
            return
        self.__is_reset_app_properties = True
        self.centralwidget.setDisabled(True)
        self.toolBar.setDisabled(True)
        self.menubar.setDisabled(True)
        log_handler.LogHandler.log_msg(method=logging.debug, msg='initialized application properties')
        #
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font())
        msgbox.setWindowTitle('iHDA Reset APP Properties')
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText('App property initialization is complete. Please start again.')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        _ = msgbox.exec_()

    def __slot_import_data(self):
        self.__video_player.player_stop()
        self.__loading_show()
        dat_stm = data_stream.DataStream(userid=self.__user, hda_base_dirpath=self.__hda_base_dirpath, parent=self)
        bak_fpath = dat_stm.import_ihda_data()
        self.__loading_close()
        if bak_fpath is not None:
            self.centralwidget.setEnabled(False)
            self.toolBar.setEnabled(False)
            self.menubar.setEnabled(False)
            self.__is_imported_data = True
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setFont(IndividualHDA.__get_default_font())
            msgbox.setWindowTitle('Individual HDA')
            msgbox.setText('''
            Import is complete. restart iHDA app<br>
            <font color=red>The existing iHDA data was backed up</font><br>
            {0}
            '''.format(bak_fpath.as_posix()))
            msgbox.setIcon(QtWidgets.QMessageBox.Information)
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            _ = msgbox.exec_()

    # import data로 데이터를 가져온 경우 앱 종료 시점에 데이터 트랜스하는 함수
    def __solve_before_app_terminate_import_data(self):
        # import data를 실행했다면
        if self.__is_imported_data:
            # .iHDAData의 houdini디렉토리 삭제
            data_stream.DataStream.remove_ihda_houdini_dir(hda_base_dirpath=self.__hda_base_dirpath)
            # tmp ihda dir .iHDAData로 옮김
            for child_dir in public.Paths.tmp_ihda_dirpath.glob('*'):
                dst_dpath = self.__hda_base_dirpath / child_dir.name
                if dst_dpath.exists():
                    ihda_system.IHDASystem.remove_dir(dirpath=dst_dpath, verbose=False)
                child_dir.rename(dst_dpath)
            # tmp DB파일 .iHDAData로 옮김
            is_moved = ihda_system.IHDASystem.rename_file(
                src_filepath=public.SQLite.tmp_db_filepath, dst_filepath=public.SQLite.db_filepath, verbose=True)
            if not is_moved:
                return
            # houdini_temp에 임시 디렉토리 삭제
            if public.Paths.tmp_ihda_dirpath.exists():
                ihda_system.IHDASystem.remove_dir(dirpath=public.Paths.tmp_ihda_dirpath, verbose=False)

    def __slot_export_data(self):
        self.__loading_show()
        dat_stm = data_stream.DataStream(userid=self.__user, hda_base_dirpath=self.__hda_base_dirpath, parent=self)
        data_dpath = dat_stm.export_ihda_data()
        self.__loading_close()
        if data_dpath is not None:
            if data_dpath.exists():
                ihda_system.IHDASystem.open_folder(data_dpath)

    def __set_theme(self, theme='Default'):
        self.__ui_settings.set_theme(theme=theme)

    def __slot_about(self):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font(font_size=15))
        msgbox.setWindowTitle('Individual HDA (Houdini built-in app)')
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIconPixmap(QtGui.QPixmap(':/main/icons/viewport_logo_trans.png'))
        msgbox.setText(public.Info.app_info(IndividualHDA.__RECOMMENDED_HOUDINI_VERSION))
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setDetailedText(public.Info.license_info())
        msgbox.setStyleSheet('''
QLabel {
    min-width: 800px;
}
QTextEdit {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop: 0 white, stop: 0.4 gray, stop: 1 green);
    font: 30px;
    color: black;
    min-height: 300px;
}
        ''')
        btn_detail = None
        for btn in msgbox.buttons():
            if msgbox.buttonRole(btn) == QtWidgets.QMessageBox.ActionRole:
                btn_detail = btn
                break
        if btn_detail is not None:
            btn_detail.click()
        # msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec_()

    def __slot_help(self):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font(font_size=15))
        msgbox.setWindowTitle('Individual HDA Help')
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText(
            '''
            <a href="https://www.youtube.com/watch?v=XR7h8uGR_iI" style="color:red" 
            target="_blank">iHDA Help video</a><br>
            <br>
            <a href="https://www.youtube.com/watch?v=MYkK8c2KOCA" style="color:red" 
            target="_blank">Codec & FFmpeg Setup Help video</a>
            ''')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setStyleSheet('QLabel {min-width: 500px;}')
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec_()

    def __slot_submit_bug_report(self):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font(font_size=15))
        msgbox.setWindowTitle('Submit Bug Report')
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText(
            '<a href="mailto:saelly55@gmail.com?Subject=[iHDA] Bug Report" style="color:red"'
            'target="_top">Send Bug Report</a><br>')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setDetailedText('Click the link to send an email.')
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec_()

    def __slot_submit_feedback(self):
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(IndividualHDA.__get_default_font(font_size=15))
        msgbox.setWindowTitle('Submit Feedback')
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText(
            '<a href="mailto:saelly55@gmail.com?Subject=[iHDA] Feedback" style="color:red"'
            'target="_top">Send Feedback</a><br>')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setDetailedText('Click the link to send an email.')
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec_()

    def __set_icon_size_from_widget(self, widget=None):
        icon_lst = widget.findChildren(QtWidgets.QPushButton)
        icon_lst.extend(widget.findChildren(QtWidgets.QToolButton))
        icon_lst.extend(widget.findChildren(QtWidgets.QCheckBox))
        icon_size = public.UISetting.dft_icon_size
        properties_data = self.__preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_main_icon_size in properties_data:
                icon_size = properties_data.get(public.Name.PreferenceUI.spb_main_icon_size)
        if public.IS_HOUDINI:
            icon_size = hou.ui.scaledSize(int(icon_size))
        for inst in icon_lst:
            qsize = QtCore.QSize(icon_size, icon_size)
            inst.setIconSize(qsize)

    @staticmethod
    def __copy_to_clipboard(text=''):
        clip = QtWidgets.QApplication.clipboard()
        clip.clear()
        clip.setText(text)

    @staticmethod
    def __slot_donate():
        is_done = ihda_system.IHDASystem.open_browser('https://www.buymeacoffee.com/seongcheoljeon')

    @staticmethod
    def __slot_download_ffmpeg_site():
        is_done = ihda_system.IHDASystem.open_browser('https://ffmpeg.zeranoe.com/builds/')
        if is_done:
            log_handler.LogHandler.log_msg(method=logging.info, msg='opened ffmpeg download site')
        else:
            log_handler.LogHandler.log_msg(method=logging.warning, msg='ffmpeg download site could not be opened')

    @staticmethod
    def __slot_download_codec_site():
        is_done = ihda_system.IHDASystem.open_browser(
            'http://www.codecguide.com/download_k-lite_codec_pack_basic.htm')
        if is_done:
            log_handler.LogHandler.log_msg(method=logging.info, msg='opened codec download site')
        else:
            log_handler.LogHandler.log_msg(method=logging.warning, msg='codec download site could not be opened')


# def __on_houdini():
#     for i in QtWidgets.QApplication.allWidgets():
#         if type(i).__name__ == 'IndividualHDA':
#             i.close()
#     fal = IndividualHDA()
#     # fal.setWindowFlags(main.windowFlags() | QtCore.Qt.Tool)
#     # fal.setStyleSheet(hou.ui.qtStyleSheet())
#     fal.show()


# def __on_system():
#     import sys
#     environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = public.Paths.qt_plugins_platforms_dirpath.as_posix()
#     app = QtWidgets.QApplication(sys.argv)
#     ihda = IndividualHDA()
#     ihda.show()
#     sys.exit(app.exec_())


# if __name__ == '__main__':
#     __on_system()
