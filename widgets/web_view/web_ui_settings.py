from __future__ import annotations

# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.19 18:45:32
# modified date:
# description:

import os
import json
from libs.settings_store import save_json
import copy

from PySide6 import QtWidgets, QtCore, QtGui

import public


class WebUISettings(object):
    def __init__(self, window: QtWidgets.QWidget | None = None) -> None:
        self.__window = window
        self.__setting_ini = QtCore.QSettings(
            public.Paths.ini_web_filepath.as_posix(), QtCore.QSettings.IniFormat
        )
        self.__setting_json = public.Paths.json_web_filepath
        self.__cfg_dict = dict()

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
            WebUISettings.__center_on_screen(self.__window)

    def load_splitter_status(self) -> None:
        vertical = self.__setting_ini.value(public.Name.WebUI.splitter_whole_vertical)
        if vertical:
            self.__window.splitter__webview_whole_vertical.restoreState(vertical)

    def load_cfg_dict_from_file(self) -> None:
        if not self.__setting_json.exists():
            return
        with self.__setting_json.open("r", encoding="utf-8") as fp:
            try:
                data = json.load(fp)
                if not isinstance(data, dict):
                    raise ValueError("Settings must contain a JSON object")
                self.__cfg_dict = copy.copy(data)
            except ValueError as err:
                self.__cfg_dict = {}
                self.__setting_json.replace(self.__setting_json.with_suffix(".corrupt"))
                return
        try:
            self.__window.lineEdit__address.setText(
                self.__cfg_dict[public.Name.WebUI.url_addr]
            )
        except KeyError:
            # Retain older/partial settings; unspecified controls keep their defaults.
            return

    @staticmethod
    def __center_on_screen(inst: QtWidgets.QWidget) -> None:
        res = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        inst.move(
            (res.width() // 2) - (inst.frameSize().width() // 2),
            (res.height() // 2) - (inst.frameSize().height() // 2),
        )


if __name__ == "__main__":
    pass
