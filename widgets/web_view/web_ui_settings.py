from __future__ import annotations

import copy

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.19 18:45:32
# modified date:
# description:
import os

from PySide6 import QtCore, QtWidgets

import public
from libs.qt_helpers import center_on_screen
from libs.settings_store import apply_settings, load_json, save_json


class WebUISettings:
    def __init__(self, window: QtWidgets.QWidget | None = None) -> None:
        self.__window = window
        self.__setting_ini = QtCore.QSettings(
            public.Paths.ini_web_filepath.as_posix(), QtCore.QSettings.Format.IniFormat
        )
        self.__setting_json = public.Paths.json_web_filepath
        self.__cfg_dict = {}

    def save_cfg_dict_to_file(self) -> None:
        self.__cfg_dict[public.Name.WebUI.url_addr] = (
            self.__window.lineEdit__address.text()
        )
        #
        if not public.Paths.config_dirpath.exists():
            os.makedirs(public.Paths.config_dirpath.as_posix())
        save_json(self.__setting_json, self.__cfg_dict)

    def save_main_window_geometry(self) -> None:
        self.__setting_ini.setValue(
            public.Name.WebUI.main_window_geometry, self.__window.saveGeometry()
        )

    def save_splitter_status(self) -> None:
        vertical = self.__window.splitter__webview_whole_vertical.saveState()
        if vertical:
            self.__setting_ini.setValue(
                public.Name.WebUI.splitter_whole_vertical, vertical
            )

    def load_main_window_geometry(self) -> None:
        main_window_geo = self.__setting_ini.value(
            public.Name.WebUI.main_window_geometry
        )
        if main_window_geo:
            self.__window.restoreGeometry(main_window_geo)
        else:
            center_on_screen(self.__window)

    def load_splitter_status(self) -> None:
        vertical = self.__setting_ini.value(public.Name.WebUI.splitter_whole_vertical)
        if vertical:
            self.__window.splitter__webview_whole_vertical.restoreState(vertical)

    def load_cfg_dict_from_file(self) -> None:
        self.__cfg_dict = copy.copy(load_json(self.__setting_json))
        if not self.__cfg_dict:
            return
        apply_settings(
            self.__cfg_dict,
            [(public.Name.WebUI.url_addr, self.__window.lineEdit__address.setText)],
        )


if __name__ == "__main__":
    pass
