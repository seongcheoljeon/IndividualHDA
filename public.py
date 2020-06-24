# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.01.27 23:21:25
# modified date:    
# description:      public file

from os import getenv as os_getenv
from platform import system as platform_system
from time import time, gmtime
from logging import info
from imp import reload
from functools import wraps

import pathlib2
from libs import log_handler

reload(log_handler)

try:
    import hou

    try:
        IS_HOUDINI = hou.isUIAvailable()
    except NameError:
        IS_HOUDINI = False
except ImportError:
    IS_HOUDINI = False


class Key:
    node = 'node'
    hda_id = 'hda_id'
    hda_name = 'hda_name'
    hda_cate = 'hda_cate'
    hda_icon = 'hda_icon'
    hda_tags = 'hda_tags'
    hda_note = 'hda_note'
    is_favorite_hda = 'is_favorite_hda'
    hip_filename = 'hip_filename'
    hip_dirpath = 'hip_dirpath'
    hda_load_count = 'hda_load_count'
    hda_ctime = 'hda_ctime'
    hda_mtime = 'hda_mtime'
    hou_version = 'hou_version'
    node_old_path = 'node_old_path'
    hda_license = 'hda_license'
    hda_version = 'hda_version'
    hda_dirpath = 'hda_dirpath'
    hda_filename = 'hda_filename'
    thumbnail_filename = 'thumbnail_filename'
    thumbnail_dirpath = 'thumbnail_dirpath'
    video_filename = 'video_filename'
    video_dirpath = 'video_dirpath'
    node_type_path_list = 'node_type_path_list'
    node_cate_path_list = 'node_cate_path_list'
    node_icon_path_list = 'node_icon_path_list'
    node_type_name = 'node_type_name'
    node_cate_name = 'node_cate_name'
    node_def_desc = 'node_def_desc'
    node_input_connections = 'node_input_connections'
    node_output_connections = 'node_output_connections'
    is_network = 'is_network'
    is_sub_network = 'is_sub_network'
    item_row = 'item_row'

    class History:
        hist_id = 'hist_id'
        hda_id = 'hda_id'
        comment = 'comment'
        org_hda_name = 'org_hda_name'
        version = 'version'
        ihda_filename = 'ihda_filename'
        ihda_dirpath = 'ihda_dirpath'
        reg_time = 'reg_time'
        hou_version = 'hou_version'
        hip_filename = 'hip_filename'
        hip_dirpath = 'hip_dirpath'
        hda_license = 'hda_license'
        os = 'os'
        node_old_path = 'node_old_path'
        node_def_desc = 'node_def_desc'
        node_type_name = 'node_type_name'
        node_category = 'node_category'
        userid = 'userid'
        icon = 'icon'
        tags = 'tags'
        hda_note = 'hda_note'
        thumb_dirpath = 'thumb_dirpath'
        thumb_filename = 'thumb_filename'
        video_dirpath = 'video_dirpath'
        video_filename = 'video_filename'
        item_row = 'item_row'

    class Record:
        record_id = 'record_id'
        hda_id = 'hda_id'
        hip_filename = 'hip_filename'
        hip_dirpath = 'hip_dirpath'
        hda_filename = 'hda_filename'
        hda_dirpath = 'hda_dirpath'
        parent_node_path = 'parent_node_path'
        node_type = 'node_type'
        node_cate = 'node_cate'
        node_name = 'node_name'
        org_node_name = 'org_node_name'
        node_ver = 'node_ver'
        houdini_version = 'houdini_version'
        houdini_license = 'houdini_license'
        operating_system = 'operating_system'
        sf = 'sf'
        ef = 'ef'
        fps = 'fps'
        ctime = 'ctime'
        mtime = 'mtime'
        thumb_dirpath = 'thumb_dirpath'
        thumb_filename = 'thumb_filename'
        video_dirpath = 'video_dirpath'
        video_filename = 'video_filename'

    # location 관련
    class Location:
        city = 'city'
        country = 'country'
        ip = 'ip'
        loc = 'loc'
        org = 'org'
        postal = 'postal'
        region = 'region'
        timezone = 'timezone'
        localx = 'localx'
        localy = 'localy'

    # resolution 관련
    class Resolution:
        sd = 'SD'
        hd = 'HD'
        fhd = 'FHD'
        qhd = 'QHD'
        uhd = 'UHD'
        _2k = '2K'
        _4k = '4K'

    class Comment:
        ihda_name = 'iHDA Name'
        ihda_version = 'iHDA Version'
        ihda_id = 'iHDA ID'


class Type:
    shop = 'shop'
    chop = 'chop'
    root = 'root'
    manager = 'mgr'
    network = 'network'
    element = 'element'
    folder = 'dir'
    file = 'file'
    ihda = 'iHDA'
    # houdini
    subnet_node = 'subnet'
    mime_type = 'application/node-key-mimetype'
    vop = 'vop'


# 노드를 hda로 만드려고할 때 오류가 발생하는 후디니 노드들의 모음
class InvalidNode:
    node_descript_list = [
        'UV Noise', 'UV Coords'
    ]
    node_type_list = [
        'uvnoise::2.0', 'uvcoords::2.0'
    ]


class Value:
    init_hda_version = '1.0'
    thumbnail_resolution = (400, 400)
    SD_res = (720, 480)
    HD_res = (1280, 720)
    FHD_res = (1920, 1080)
    QHD_res = (2560, 1440)
    UHD_res = (3840, 2160)
    _2K_res = (2048, 1080)
    _4K_res = (4096, 2160)
    current_ver = 'v1.7.1'
    qt_datetime_fmt_str = 'yyyy-MM-dd hh:mm:ss'
    qt_date_fmt_str = 'yyyy-MM-dd'
    datetime_fmt_str = '%Y-%m-%d %H:%M:%S'
    # Drag&Drop할 때 선택되어지는 컬럼
    drag_column_table_view = 0
    drag_column_history_view = 2
    drag_column_record_view = 0
    # 경로가 뜨는 노드 개수
    warning_num_of_node_regist = 10


class Name:
    houdini_node_function = 'run'
    current_app = 'individualHDA'
    hda_prefix_str = 'iHDA'
    # thumbnail dirname
    thumbnail_dirname = 'thumbnail'
    # preview image sequence dirname
    preview_dirname = 'preview'
    # video dirname
    video_dirname = 'video'
    # company
    company_icon_dirname = '__company__'
    company_initial = 'scii'
    company_log_icon_filename = 'viewport_logo_trans'
    # system
    win = 'windows'
    lnx = 'linux'
    mac = 'darwin'
    bin_dirname = 'bin'
    # ##### settings name ##### #
    # ini file names
    main_window_geometry = 'main_window_geometry'
    main_window_state = 'main_window_state'
    # splitter names
    whole_horizontal = 'whole_horizontal'
    whole_vertical = 'whole_vertical'
    hda_info_vertical = 'hda_info_vertical'
    # 추가 함.
    hda_info_whole_vertical = 'hda_info_whole_vertical'
    ihda_whole_vertical = 'ihda_whole_vertical'
    cate_whole_vertical = 'cate_whole_vertical'
    ihda_hist_whole_vertical = 'ihda_hist_whole_vertical'
    # ui names
    # checkbox
    chk_casesensitive_hda = 'chk_casesensitive_hda'
    chk_casesensitive_cate = 'chk_casesensitive_cate'
    chk_unpack_subnet = 'chk_unpack_subnet'
    chk_sync_network_cate = 'chk_sync_network_cate'
    chk_sync_node = 'chk_sync_node'
    chk_note_to_sticky = 'chk_note_to_sticky'
    chk_action_default = 'chk_action_default'
    chk_action_darkblue = 'chk_action_darkblue'
    chk_action_null = 'chk_action_null'
    chk_action_input = 'chk_action_input'
    chk_action_output = 'chk_action_output'
    chk_action_both = 'chk_action_both'
    chk_action_comment = 'chk_action_comment'
    chk_auto_rename = 'chk_auto_rename'
    # record checkbox
    chk_record_only_curt_hipfile = 'chk_record_only_curt_hipfile'
    chk_record_only_curt_ihda = 'chk_record_only_curt_ihda'
    # inside checkbox
    chk_inside_connect_to_view = 'chk_inside_connect_to_view'
    # button
    btn_icon_mode = 'btn_icon_mode'
    btn_table_mode = 'btn_table_mode'
    btn_hda_info = 'btn_hda_info'
    btn_hda_loc_record = 'btn_hda_loc_record'
    btn_hda_inside_node = 'btn_hda_inside_node'
    btn_show_thumbnail = 'btn_show_thumbnail'
    # combobox
    cmb_search_type = 'cmb_search_type'
    # zoom value
    zoom_value = 'zoom_value'
    # double spinbox
    spinbox_zoom = 'spinbox_zoom'
    # stacked widget whole
    stacked_widget_whole = 'stacked_widget_whole'
    # houdini name
    houdini_name = 'houdini'
    houdinifx_name = 'houdinifx'
    # theme (toolbar에 등록된 디스플레이 이름이랑 똑같아야 한다)
    default_theme = 'Default'
    darkblue_theme = 'Dark blue'
    # 임시 사용자 이름
    username = 'anonymous'
    # ######################### #

    class Icons:
        filename = 'IconMapping'
        networks = 'NETWORKS'
        desktop = 'DESKTOP'
        blank = 'blank'
        root = 'root'

    class FFmpeg:
        # FFmpeg bin file name
        ffmpeg_bin_filename = 'ffmpeg'
        # FFmpeg play file name
        ffmpeg_play_filename = 'ffplay'
        # FFmpeg probe file name
        ffmpeg_probe_filename = 'ffprobe'

        class Metadata:
            author = 'author'
            year = 'year'
            title = 'title'
            desc = 'description'

    class VideoUI:
        btn_volume = 'btn_volume'
        slider_volume = 'slider_volume'
        playback_idx = 'playback_idx'
        # splitter names
        splitter_horizontal = 'splitter_horizontal'
        splitter_vertical = 'splitter_vertical'
        # ini file names
        main_window_geometry = 'main_window_geometry'
        main_window_state = 'main_window_state'
        # playlist
        playlist = 'playlist'
        last_dirpath = 'last_dirpath'

    class WebUI:
        # url address
        url_addr = 'url_addr'
        # splitter names
        splitter_whole_vertical = 'splitter_whole_vertical'
        # ini file names
        main_window_geometry = 'main_window_geometry'
        main_window_state = 'main_window_state'

    class PreferenceUI:
        lineedit_data_dirpath = 'lineedit_data_dirpath'
        lineedit_ffmpeg_dirpath = 'lineedit_ffmpeg_dirpath'
        cmb_view_font_style = 'cmb_view_font_style'
        spb_view_font_size = 'spb_view_font_size'
        spb_listview_icon_size = 'dspb_listview_icon_size'
        spb_tableview_icon_size = 'dspb_tableview_icon_size'
        spb_treeview_icon_size = 'dspb_treeview_icon_size'
        dspb_listview_thumb_scale = 'dspb_listview_thumb_scale'
        dspb_tableview_thumb_scale = 'dspb_tableview_thumb_scale'
        spb_note_font_size = 'spb_note_font_size'
        spb_tags_font_size = 'spb_tags_font_size'
        spb_debug_font_size = 'spb_debug_font_size'
        cmb_note_font_style = 'cmb_note_font_style'
        cmb_tags_font_style = 'cmb_note_tags_style'
        cmb_debug_font_style = 'cmb_note_debug_style'
        # main
        spb_main_icon_size = 'spb_main_icon_size'
        # padding
        pad_listview = 'pad_listview'
        pad_tableview = 'pad_tableview'
        pad_history = 'pad_history'
        pad_category = 'pad_category'
        pad_record = 'pad_record'
        pad_inside = 'pad_inside'
        # ini file names
        main_window_geometry = 'main_window_geometry'
        main_window_state = 'main_window_state'

    class LoginUI:
        logid = 'logid'
        chk_stay_signed = 'chk_stay_signed'
        # ini file names
        main_window_geometry = 'main_window_geometry'
        main_window_state = 'main_window_state'

    class Python:
        lib = 'libs'
        packages = 'site-packages'
        dll_library = 'library'

    class IHDAData:
        filename = 'iHDA'
        backup_dirname = 'backup'


def is_linux():
    return platform_system().lower() == Name.lnx


def is_windows():
    return platform_system().lower() == Name.win


def is_mac():
    return platform_system().lower() == Name.mac


def current_system():
    if is_windows():
        return Name.win
    elif is_mac():
        return Name.mac
    elif is_linux():
        return Name.lnx
    else:
        return 'unknown'


def current_houdini_version():
    if IS_HOUDINI:
        return str(hou.applicationVersion()[0])
    return 'unknown'


class Extensions:
    houdini_icons = '.svg'
    ihda_file = '.ihda'
    company_log_icon_file_ext = '.png'
    image = '.jpg'
    video = '.mp4'
    zip_file = '.zip'
    database_file = '.db'
    if is_windows():
        executable = '.exe'
    else:
        executable = ''


class UISetting:
    if is_windows():
        dft_font_style = 'MS Shell Dlg 2'
        view_font_style = 'MS Shell Dlg 2'
    else:
        dft_font_style = 'Courier'
        view_font_style = 'Courier'
    dft_font_size = 10
    view_font_size = 11
    #
    dft_icon_size = 20
    listview_node_icon_size = 38
    tableview_node_icon_size = 38
    treeview_node_icon_size = 24
    listview_thumbnail_scale = 2.0
    tableview_thumbnail_scale = 1.3
    # zoom
    interval_zoom_value = 10.0
    min_zoom_value = 30.0
    max_zoom_value = 500.0
    # padding
    padding_listview = 20.0
    padding_tableview = 0.0
    padding_history = 0.0
    padding_category = 15.0
    padding_record = 5.0
    padding_inside = 5.0


class Paths:
    houdini_path_sep = '/'
    hfs_dirpath = pathlib2.Path(os_getenv('HFS'))
    hb_dirpath = pathlib2.Path(os_getenv('HB'))
    hh_dirpath = pathlib2.Path(os_getenv('HH'))
    houdini_user_pref_dirpath = pathlib2.Path(os_getenv('HOUDINI_USER_PREF_DIR'))
    user_home_dirpath = pathlib2.Path.home().parent
    tmp_dirpath = pathlib2.Path(os_getenv('TEMP')) / 'houdini_temp'
    if IS_HOUDINI:
        hfs_dirpath = pathlib2.Path(hou.getenv('HFS'))
        hb_dirpath = pathlib2.Path(hou.getenv('HB'))
        hh_dirpath = pathlib2.Path(hou.getenv('HH'))
        houdini_user_pref_dirpath = pathlib2.Path(hou.getenv('HOUDINI_USER_PREF_DIR'))
        if is_windows():
            user_home_dirpath = pathlib2.Path(hou.getenv('USERPROFILE'))
            tmp_dirpath = pathlib2.Path(hou.getenv('TEMP'))
        else:
            user_home_dirpath = pathlib2.Path(hou.getenv('HOME'))
            tmp_dirpath = pathlib2.Path(hou.getenv('HOUDINI_TEMP_DIR'))
    # import data할 때의 임시 저장 디렉토리
    tmp_ihda_dirpath = tmp_dirpath / 'tmp_ihda_dir'
    # current script dir path
    curt_script_dirpath = houdini_user_pref_dirpath / 'scripts' / 'python' / Name.current_app
    # config
    config_dirpath = curt_script_dirpath / '.config'
    __json_filename = 'config.json'
    __json_video_filename = 'video_config.json'
    __json_web_filename = 'web_config.json'
    __json_pref_filename = 'preference.json'
    __json_login_filename = 'login.json'
    __ini_filename = 'window_ui.ini'
    __ini_video_filename = 'video_window_ui.ini'
    __ini_web_filename = 'web_window_ui.ini'
    __ini_pref_filename = 'preference_ui.ini'
    __ini_login_filename = 'login_ui.ini'
    json_filepath = config_dirpath / __json_filename
    json_video_filepath = config_dirpath / __json_video_filename
    json_web_filepath = config_dirpath / __json_web_filename
    json_pref_filepath = config_dirpath / __json_pref_filename
    json_login_filepath = config_dirpath / __json_login_filename
    ini_filepath = config_dirpath / __ini_filename
    ini_video_filepath = config_dirpath / __ini_video_filename
    ini_web_filepath = config_dirpath / __ini_web_filename
    ini_pref_filepath = config_dirpath / __ini_pref_filename
    ini_login_filepath = config_dirpath / __ini_login_filename
    # HDA default icon dir path
    icons_hda_default_dirpath = curt_script_dirpath / 'icons'
    # HDA default icon file path
    __company_log_icon = Name.company_log_icon_filename + Extensions.company_log_icon_file_ext
    icons_hda_default_filepath = icons_hda_default_dirpath / __company_log_icon
    # python site-packages dir path
    python_packages_dirpath = curt_script_dirpath / Name.Python.lib / Name.Python.packages
    # houdini fx cmd file path
    houdinifx_cmd = hb_dirpath.joinpath(Name.houdinifx_name).with_suffix(Extensions.executable)


class SQLite:
    db_filename = 'ihda{0}'.format(Extensions.database_file)
    # 임시 ihda database name
    tmp_db_filename = 'tmp_ihda{0}'.format(Extensions.database_file)
    tmp_db_filepath = Paths.tmp_dirpath / tmp_db_filename


class Info:
    @staticmethod
    def app_info(houdini_ver=None):
        info = '''
<p>Individual HDA (Houdini built-in app)<br><br>
Release Date: 2020.06.24<br>
Release Version: {0}<br>
OS Available: {1}<br>
Recommended Houdini Version: {2}<br>
<br>
<b><i>Please donate if you like this app.<i><b><br>
<br>
<a href="https://www.buymeacoffee.com/seongcheoljeon" style="color:#ff6f00" target="_blank">Buy Me A Coffee</a><br>
<br>
<a href="https://www.youtube.com/channel/UCy4fuTNjIPeKPB4hacaP_6A?view_as=subscriber" style="color:red" 
target="_blank">Youtube</a><br>
        '''.format(
            Value.current_ver, platform_system().title(), houdini_ver)
        return info

    @staticmethod
    def license_info():
        lic_info = '''
MIT License

Copyright (c) 2020 Seongcheol Jeon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.



        '''
        return lic_info


def hda_base_dirpath(base_dirpath=None):
    assert isinstance(base_dirpath, pathlib2.Path)
    return base_dirpath / Name.houdini_name / Name.current_app


def runtime_check(func):
    @wraps(func)
    def __wrapper(*args, **kwargs):
        start_time = time()
        s_time = gmtime(start_time)
        log_handler.LogHandler.log_msg(method=info, msg='( {0} ) Start Time: {1}/{2} - {3}:{4}:{5}'.format(
            func.__name__, s_time.tm_mon, s_time.tm_mday, s_time.tm_hour + 9, s_time.tm_min, s_time.tm_sec))
        func_result = func(*args, **kwargs)
        end_time = time()
        e_time = gmtime(end_time)
        log_handler.LogHandler.log_msg(method=info, msg='( {0} ) End Time: {1}/{2} - {3}:{4}:{5}'.format(
            func.__name__, e_time.tm_mon, e_time.tm_mday, e_time.tm_hour + 9, e_time.tm_min, e_time.tm_sec))
        run_time = end_time - start_time
        log_handler.LogHandler.log_msg(method=info, msg='( {0} ) Running Time: {1}m {2}s'.format(
            func.__name__, int(run_time // 60), int(run_time % 60)))
        return func_result

    return __wrapper


def runtime_check_with_param(param):
    def wrapper(func):
        @wraps(func)
        def __wrapper(*args, **kwargs):
            start_time = time()
            s_time = gmtime(start_time)
            log_handler.LogHandler.log_msg(method=info, msg='( {0} ) Start Time: {1}/{2} - {3}:{4}:{5}'.format(
                param, s_time.tm_mon, s_time.tm_mday, s_time.tm_hour + 9, s_time.tm_min, s_time.tm_sec))
            func_result = func(*args, **kwargs)
            end_time = time()
            e_time = gmtime(end_time)
            log_handler.LogHandler.log_msg(method=info, msg='( {0} ) End Time: {1}/{2} - {3}:{4}:{5}'.format(
                param, e_time.tm_mon, e_time.tm_mday, e_time.tm_hour + 9, e_time.tm_min, e_time.tm_sec))
            run_time = end_time - start_time
            log_handler.LogHandler.log_msg(method=info, msg='( {0} ) Running Time: {1}m {2}s'.format(
                param, int(run_time // 60), int(run_time % 60)))
            return func_result

        return __wrapper

    return wrapper


def runtime_check_simple(func):
    @wraps(func)
    def __wrapper(*args, **kwargs):
        start_time = time()
        func_result = func(*args, **kwargs)
        end_time = time()
        run_time = end_time - start_time
        log_handler.LogHandler.log_msg(
            method=info, msg='elapsed time: {0}m {1}s'.format(int(run_time // 60), int(run_time % 60)))
        return func_result

    return __wrapper


def runtime_check_simple_with_param(param):
    def wrapper(func):
        @wraps(func)
        def __wrapper(*args, **kwargs):
            start_time = time()
            func_result = func(*args, **kwargs)
            end_time = time()
            run_time = end_time - start_time
            log_handler.LogHandler.log_msg(method=info, msg='( {0} ) elapsed time: {1}m {2}s'.format(
                param, int(run_time // 60), int(run_time % 60)))
            return func_result

        return __wrapper

    return wrapper

