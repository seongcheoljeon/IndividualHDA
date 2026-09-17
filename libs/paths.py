"""Filesystem locations derived from the Houdini environment at import time.

Only `libs.paths` and its `public` re-export may compute these; tests point
IHDA_CONFIG_DIR at a temporary directory before importing.
"""

from __future__ import annotations

import pathlib
from os import W_OK
from os import access as os_access
from os import getenv as os_getenv
from tempfile import gettempdir

from libs.app_metadata import LEGACY_HOUDINI_PREF_FOLDER
from libs.keys import Extensions, Name


class Paths:
    houdini_path_sep = "/"
    hfs_dirpath = pathlib.Path(os_getenv("HFS") or pathlib.Path.home())
    hb_dirpath = pathlib.Path(os_getenv("HB") or hfs_dirpath / "bin")
    hh_dirpath = pathlib.Path(os_getenv("HH") or hfs_dirpath / "houdini")
    houdini_user_pref_dirpath = pathlib.Path(
        os_getenv("HOUDINI_USER_PREF_DIR")
        or pathlib.Path.home() / LEGACY_HOUDINI_PREF_FOLDER
    )
    user_home_dirpath = pathlib.Path.home()
    tmp_dirpath = pathlib.Path(os_getenv("HOUDINI_TEMP_DIR") or gettempdir())
    tmp_ihda_dirpath = tmp_dirpath / "tmp_ihda_dir"
    curt_script_dirpath = pathlib.Path(__file__).resolve().parent
    # Preserve existing settings while allowing read-only/shared installations.
    _legacy_config = (
        houdini_user_pref_dirpath / "scripts" / "python" / Name.current_app / ".config"
    )
    config_dirpath = pathlib.Path(
        os_getenv("IHDA_CONFIG_DIR")
        or (
            _legacy_config
            if _legacy_config.exists() and os_access(_legacy_config, W_OK)
            else houdini_user_pref_dirpath / "IndividualHDA" / ".config"
        )
    )
    __json_filename = "config.json"
    __json_video_filename = "video_config.json"
    __json_web_filename = "web_config.json"
    __json_pref_filename = "preference.json"
    __ini_filename = "window_ui.ini"
    __ini_video_filename = "video_window_ui.ini"
    __ini_web_filename = "web_window_ui.ini"
    __ini_pref_filename = "preference_ui.ini"
    json_filepath = config_dirpath / __json_filename
    json_video_filepath = config_dirpath / __json_video_filename
    json_web_filepath = config_dirpath / __json_web_filename
    json_pref_filepath = config_dirpath / __json_pref_filename
    ini_filepath = config_dirpath / __ini_filename
    ini_video_filepath = config_dirpath / __ini_video_filename
    ini_web_filepath = config_dirpath / __ini_web_filename
    ini_pref_filepath = config_dirpath / __ini_pref_filename
    # HDA default icon dir path
    icons_hda_default_dirpath = curt_script_dirpath / "icons"
    # HDA default icon file path
    __company_log_icon = (
        Name.company_log_icon_filename + Extensions.company_log_icon_file_ext
    )
    icons_hda_default_filepath = icons_hda_default_dirpath / __company_log_icon
    # houdini fx cmd file path
    houdinifx_cmd = hb_dirpath.joinpath(Name.houdinifx_name).with_suffix(
        Extensions.executable
    )


class SQLite:
    db_filename = f"ihda{Extensions.database_file}"
    # 임시 ihda database name
    tmp_db_filename = f"tmp_ihda{Extensions.database_file}"
    tmp_db_filepath = Paths.tmp_dirpath / tmp_db_filename


def hda_base_dirpath(base_dirpath: pathlib.Path | None = None) -> pathlib.Path:
    assert isinstance(base_dirpath, pathlib.Path)
    return base_dirpath / Name.houdini_name / Name.current_app
