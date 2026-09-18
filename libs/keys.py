"""Dictionary keys, setting names, constant values and UI defaults.

Pure data: no Qt, HOM or filesystem access. `public` re-exports these for the
panel; new code imports from here directly.
"""

from __future__ import annotations

from typing import Final

from libs.app_metadata import DISPLAY_VERSION
from libs.model_columns import AssetColumn, HistoryColumn, RecordColumn
from libs.platform_info import is_windows
from libs.runtime_settings import DEFAULT_RUNTIME


class Key:
    node: Final = "node"
    hda_id: Final = "hda_id"
    hda_name: Final = "hda_name"
    hda_cate: Final = "hda_cate"
    hda_icon: Final = "hda_icon"
    hda_tags: Final = "hda_tags"
    hda_note: Final = "hda_note"
    is_favorite_hda: Final = "is_favorite_hda"
    hip_filename: Final = "hip_filename"
    hip_dirpath: Final = "hip_dirpath"
    hda_load_count: Final = "hda_load_count"
    hda_ctime: Final = "hda_ctime"
    hda_mtime: Final = "hda_mtime"
    hou_version: Final = "hou_version"
    node_old_path: Final = "node_old_path"
    hda_license: Final = "hda_license"
    hda_version: Final = "hda_version"
    hda_dirpath: Final = "hda_dirpath"
    hda_filename: Final = "hda_filename"
    thumbnail_filename: Final = "thumbnail_filename"
    thumbnail_dirpath: Final = "thumbnail_dirpath"
    video_filename: Final = "video_filename"
    video_dirpath: Final = "video_dirpath"
    node_type_path_list: Final = "node_type_path_list"
    node_cate_path_list: Final = "node_cate_path_list"
    node_icon_path_list: Final = "node_icon_path_list"
    node_type_name: Final = "node_type_name"
    node_cate_name: Final = "node_cate_name"
    node_def_desc: Final = "node_def_desc"
    node_input_connections: Final = "node_input_connections"
    node_output_connections: Final = "node_output_connections"
    is_network: Final = "is_network"
    is_sub_network: Final = "is_sub_network"
    item_row: Final = "item_row"

    class History:
        hist_id: Final = "hist_id"
        hda_id: Final = "hda_id"
        comment: Final = "comment"
        org_hda_name: Final = "org_hda_name"
        version: Final = "version"
        ihda_filename: Final = "ihda_filename"
        ihda_dirpath: Final = "ihda_dirpath"
        reg_time: Final = "reg_time"
        hou_version: Final = "hou_version"
        hip_filename: Final = "hip_filename"
        hip_dirpath: Final = "hip_dirpath"
        hda_license: Final = "hda_license"
        os: Final = "os"
        node_old_path: Final = "node_old_path"
        node_def_desc: Final = "node_def_desc"
        node_type_name: Final = "node_type_name"
        node_category: Final = "node_category"
        userid: Final = "userid"
        icon: Final = "icon"
        tags: Final = "tags"
        hda_note: Final = "hda_note"
        thumb_dirpath: Final = "thumb_dirpath"
        thumb_filename: Final = "thumb_filename"
        video_dirpath: Final = "video_dirpath"
        video_filename: Final = "video_filename"
        item_row: Final = "item_row"

    class Record:
        record_id: Final = "record_id"
        hda_id: Final = "hda_id"
        hip_filename: Final = "hip_filename"
        hip_dirpath: Final = "hip_dirpath"
        hda_filename: Final = "hda_filename"
        hda_dirpath: Final = "hda_dirpath"
        parent_node_path: Final = "parent_node_path"
        node_type: Final = "node_type"
        node_cate: Final = "node_cate"
        node_name: Final = "node_name"
        org_node_name: Final = "org_node_name"
        node_ver: Final = "node_ver"
        houdini_version: Final = "houdini_version"
        houdini_license: Final = "houdini_license"
        operating_system: Final = "operating_system"
        sf: Final = "sf"
        ef: Final = "ef"
        fps: Final = "fps"
        ctime: Final = "ctime"
        mtime: Final = "mtime"
        thumb_dirpath: Final = "thumb_dirpath"
        thumb_filename: Final = "thumb_filename"
        video_dirpath: Final = "video_dirpath"
        video_filename: Final = "video_filename"

    # location 관련
    class Location:
        city: Final = "city"
        country: Final = "country"
        ip: Final = "ip"
        loc: Final = "loc"
        org: Final = "org"
        postal: Final = "postal"
        region: Final = "region"
        timezone: Final = "timezone"
        localx: Final = "localx"
        localy: Final = "localy"

    # resolution 관련
    class Resolution:
        sd: Final = "SD"
        hd: Final = "HD"
        fhd: Final = "FHD"
        qhd: Final = "QHD"
        uhd: Final = "UHD"
        _2k: Final = "2K"
        _4k: Final = "4K"

    class Comment:
        ihda_name: Final = "iHDA Name"
        ihda_version: Final = "iHDA Version"
        ihda_id: Final = "iHDA ID"


class Type:
    shop: Final = "shop"
    chop: Final = "chop"
    root: Final = "root"
    manager: Final = "mgr"
    network: Final = "network"
    element: Final = "element"
    folder: Final = "dir"
    file: Final = "file"
    ihda: Final = "iHDA"
    # houdini
    subnet_node: Final = "subnet"
    mime_type: Final = "application/node-key-mimetype"
    vop: Final = "vop"


class InvalidNode:
    node_descript_list = ["UV Noise", "UV Coords"]
    node_type_list = ["uvnoise::2.0", "uvcoords::2.0"]


class Value:
    init_hda_version: Final = "1.0"
    thumbnail_resolution = (400, 400)
    SD_res = (720, 480)
    HD_res = (1280, 720)
    FHD_res = (1920, 1080)
    QHD_res = (2560, 1440)
    UHD_res = (3840, 2160)
    _2K_res = (2048, 1080)
    _4K_res = (4096, 2160)
    current_ver = DISPLAY_VERSION
    qt_datetime_fmt_str: Final = "yyyy-MM-dd hh:mm:ss"
    qt_date_fmt_str: Final = "yyyy-MM-dd"
    datetime_fmt_str: Final = "%Y-%m-%d %H:%M:%S"
    # Drag&Drop할 때 선택되어지는 컬럼
    drag_column_table_view = AssetColumn.NAME
    drag_column_history_view = HistoryColumn.DEFINITION
    drag_column_record_view = RecordColumn.NAME
    # 경로가 뜨는 노드 개수
    warning_num_of_node_regist = DEFAULT_RUNTIME.warn_node_batch


class Name:
    houdini_node_function: Final = "run"
    current_app: Final = "individualHDA"
    hda_prefix_str: Final = "iHDA"
    # thumbnail dirname
    thumbnail_dirname: Final = "thumbnail"
    # preview image sequence dirname
    preview_dirname: Final = "preview"
    # video dirname
    video_dirname: Final = "video"
    # company
    company_icon_dirname: Final = "__company__"
    company_initial: Final = "scii"
    company_log_icon_filename: Final = "viewport_logo_trans"
    # system
    win: Final = "windows"
    lnx: Final = "linux"
    mac: Final = "darwin"
    bin_dirname: Final = "bin"
    # ##### settings name ##### #
    # ini file names
    main_window_geometry: Final = "main_window_geometry"
    main_window_state: Final = "main_window_state"
    # splitter names
    whole_horizontal: Final = "whole_horizontal"
    whole_vertical: Final = "whole_vertical"
    hda_info_vertical: Final = "hda_info_vertical"
    # 추가 함.
    hda_info_whole_vertical: Final = "hda_info_whole_vertical"
    ihda_whole_vertical: Final = "ihda_whole_vertical"
    cate_whole_vertical: Final = "cate_whole_vertical"
    ihda_hist_whole_vertical: Final = "ihda_hist_whole_vertical"
    # ui names
    # checkbox
    chk_casesensitive_hda: Final = "chk_casesensitive_hda"
    chk_casesensitive_cate: Final = "chk_casesensitive_cate"
    chk_unpack_subnet: Final = "chk_unpack_subnet"
    chk_sync_network_cate: Final = "chk_sync_network_cate"
    chk_sync_node: Final = "chk_sync_node"
    chk_note_to_sticky: Final = "chk_note_to_sticky"
    chk_action_default: Final = "chk_action_default"
    chk_action_darkblue: Final = "chk_action_darkblue"
    chk_action_null: Final = "chk_action_null"
    chk_action_input: Final = "chk_action_input"
    chk_action_output: Final = "chk_action_output"
    chk_action_both: Final = "chk_action_both"
    chk_action_comment: Final = "chk_action_comment"
    chk_auto_rename: Final = "chk_auto_rename"
    # record checkbox
    chk_record_only_curt_hipfile: Final = "chk_record_only_curt_hipfile"
    chk_record_only_curt_ihda: Final = "chk_record_only_curt_ihda"
    # inside checkbox
    chk_inside_connect_to_view: Final = "chk_inside_connect_to_view"
    # button
    btn_icon_mode: Final = "btn_icon_mode"
    btn_table_mode: Final = "btn_table_mode"
    btn_hda_info: Final = "btn_hda_info"
    btn_hda_loc_record: Final = "btn_hda_loc_record"
    btn_hda_inside_node: Final = "btn_hda_inside_node"
    btn_show_thumbnail: Final = "btn_show_thumbnail"
    # combobox
    cmb_search_type: Final = "cmb_search_type"
    # zoom value
    zoom_value: Final = "zoom_value"
    # double spinbox
    spinbox_zoom: Final = "spinbox_zoom"
    # stacked widget whole
    stacked_widget_whole: Final = "stacked_widget_whole"
    # houdini name
    houdini_name: Final = "houdini"
    houdinifx_name: Final = "houdinifx"
    # theme (toolbar에 등록된 디스플레이 이름이랑 똑같아야 한다)
    default_theme: Final = "Default"
    darkblue_theme: Final = "Dark blue"
    # ######################### #

    class Icons:
        filename: Final = "IconMapping"
        networks: Final = "NETWORKS"
        desktop: Final = "DESKTOP"
        blank: Final = "blank"
        root: Final = "root"

    class FFmpeg:
        # FFmpeg bin file name
        ffmpeg_bin_filename: Final = "ffmpeg"
        # FFmpeg play file name
        ffmpeg_play_filename: Final = "ffplay"
        # FFmpeg probe file name
        ffmpeg_probe_filename: Final = "ffprobe"

        class Metadata:
            author: Final = "author"
            year: Final = "year"
            title: Final = "title"
            desc: Final = "description"

    class VideoUI:
        btn_volume: Final = "btn_volume"
        slider_volume: Final = "slider_volume"
        playback_idx: Final = "playback_idx"
        # splitter names
        splitter_horizontal: Final = "splitter_horizontal"
        splitter_vertical: Final = "splitter_vertical"
        # ini file names
        main_window_geometry: Final = "main_window_geometry"
        main_window_state: Final = "main_window_state"
        # playlist
        playlist: Final = "playlist"
        last_dirpath: Final = "last_dirpath"

    class WebUI:
        # url address
        url_addr: Final = "url_addr"
        # splitter names
        splitter_whole_vertical: Final = "splitter_whole_vertical"
        # ini file names
        main_window_geometry: Final = "main_window_geometry"
        main_window_state: Final = "main_window_state"

    class PreferenceUI:
        ai: Final = "ai"
        lineedit_data_dirpath: Final = "lineedit_data_dirpath"
        lineedit_ffmpeg_dirpath: Final = "lineedit_ffmpeg_dirpath"
        cmb_view_font_style: Final = "cmb_view_font_style"
        spb_view_font_size: Final = "spb_view_font_size"
        spb_listview_icon_size: Final = "dspb_listview_icon_size"
        spb_tableview_icon_size: Final = "dspb_tableview_icon_size"
        spb_treeview_icon_size: Final = "dspb_treeview_icon_size"
        dspb_listview_thumb_scale: Final = "dspb_listview_thumb_scale"
        dspb_tableview_thumb_scale: Final = "dspb_tableview_thumb_scale"
        spb_note_font_size: Final = "spb_note_font_size"
        spb_tags_font_size: Final = "spb_tags_font_size"
        spb_debug_font_size: Final = "spb_debug_font_size"
        cmb_note_font_style: Final = "cmb_note_font_style"
        cmb_tags_font_style: Final = "cmb_note_tags_style"
        cmb_debug_font_style: Final = "cmb_note_debug_style"
        # main
        spb_main_icon_size: Final = "spb_main_icon_size"
        # padding
        pad_listview: Final = "pad_listview"
        pad_tableview: Final = "pad_tableview"
        pad_history: Final = "pad_history"
        pad_category: Final = "pad_category"
        pad_record: Final = "pad_record"
        pad_inside: Final = "pad_inside"
        # ini file names
        main_window_geometry: Final = "main_window_geometry"
        main_window_state: Final = "main_window_state"

    class IHDAData:
        filename: Final = "iHDA"
        backup_dirname: Final = "backup"


class Extensions:
    houdini_icons: Final = ".svg"
    ihda_file: Final = ".ihda"
    company_log_icon_file_ext: Final = ".png"
    image: Final = ".jpg"
    video: Final = ".mp4"
    zip_file: Final = ".zip"
    database_file: Final = ".db"
    executable = ".exe" if is_windows() else ""


class UISetting:
    # Bundled with the panel (resource/fonts), so it is the same on every platform.
    # libs.app_fonts registers the files; this is the family they expose.
    dft_font_style: Final = "MaruBuri"
    view_font_style: Final = dft_font_style
    dft_font_size: Final = 10
    view_font_size: Final = 11
    #
    dft_icon_size: Final = 20
    listview_node_icon_size: Final = 38
    tableview_node_icon_size: Final = 38
    treeview_node_icon_size: Final = 24
    listview_thumbnail_scale: Final = 2.0
    tableview_thumbnail_scale: Final = 1.3
    # zoom
    interval_zoom_value: Final = 10.0
    min_zoom_value: Final = 30.0
    max_zoom_value: Final = 500.0
    # padding
    padding_listview: Final = 20.0
    padding_tableview: Final = 0.0
    padding_history: Final = 0.0
    padding_category: Final = 15.0
    padding_record: Final = 5.0
    padding_inside: Final = 5.0
