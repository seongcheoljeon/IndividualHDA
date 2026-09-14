from __future__ import annotations

import copy

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.19 18:45:32
# modified date:
# description:      video UI 관련
import os
from typing import Any

from PySide6 import QtCore, QtWidgets

import public
from libs.qt_helpers import center_on_screen
from libs.settings_store import apply_settings, load_json, save_json


class VideoUISettings:
    def __init__(self, window: QtWidgets.QWidget | None = None) -> None:
        self.__window = window
        self.__setting_ini = QtCore.QSettings(
            public.Paths.ini_video_filepath.as_posix(),
            QtCore.QSettings.Format.IniFormat,
        )
        self.__setting_json = public.Paths.json_video_filepath
        self.__cfg_dict = {}

    def save_cfg_dict_to_file(self) -> None:
        # button
        self.__cfg_dict[public.Name.VideoUI.btn_volume] = (
            self.__window.pushButton__volume.isChecked()
        )
        # slider
        self.__cfg_dict[public.Name.VideoUI.slider_volume] = (
            self.__window.horizontalSlider__volume.value()
        )
        # playback index
        self.__cfg_dict[public.Name.VideoUI.playback_idx] = self.__window.playback_idx
        # playlist
        playlist = [x.as_posix() for x in self.__window.get_all_playlist_path()]
        self.__cfg_dict[public.Name.VideoUI.playlist] = playlist
        # last dirpath
        last_dirpath = self.__window.last_dirpath
        if last_dirpath is not None:
            self.__cfg_dict[public.Name.VideoUI.last_dirpath] = last_dirpath.as_posix()
        #
        if not public.Paths.config_dirpath.exists():
            os.makedirs(public.Paths.config_dirpath.as_posix())
        save_json(self.__setting_json, self.__cfg_dict)

    def save_main_window_geometry(self) -> None:
        self.__setting_ini.setValue(
            public.Name.VideoUI.main_window_geometry, self.__window.saveGeometry()
        )

    def save_splitter_status(self) -> None:
        horizon = self.__window.splitter__horizontal.saveState()
        vertical = self.__window.splitter__vertical.saveState()
        if horizon:
            self.__setting_ini.setValue(
                public.Name.VideoUI.splitter_horizontal, horizon
            )
        if vertical:
            self.__setting_ini.setValue(public.Name.VideoUI.splitter_vertical, vertical)

    def load_main_window_geometry(self) -> None:
        main_window_geo = self.__setting_ini.value(
            public.Name.VideoUI.main_window_geometry
        )
        if main_window_geo:
            self.__window.restoreGeometry(main_window_geo)
        else:
            center_on_screen(self.__window)

    def load_splitter_status(self) -> None:
        horizon = self.__setting_ini.value(public.Name.VideoUI.splitter_horizontal)
        vertical = self.__setting_ini.value(public.Name.VideoUI.splitter_vertical)
        if horizon:
            self.__window.splitter__horizontal.restoreState(horizon)
        if vertical:
            self.__window.splitter__vertical.restoreState(vertical)

    def load_cfg_dict_from_file(self) -> None:
        self.__cfg_dict = copy.copy(load_json(self.__setting_json))
        if not self.__cfg_dict:
            return
        window = self.__window
        keys = public.Name.VideoUI

        def playlist(value: Any) -> None:
            if value:
                window.add_playlist(filepath_lst=list(value))

        def last_dirpath(value: Any) -> None:
            if value is not None:
                window.last_dirpath = value

        apply_settings(
            self.__cfg_dict,
            [
                (
                    keys.playback_idx,
                    lambda value: setattr(window, "playback_idx", value),
                ),
                (keys.btn_volume, window.pushButton__volume.setChecked),
                (keys.slider_volume, window.horizontalSlider__volume.setValue),
                (keys.playlist, playlist),
                (keys.last_dirpath, last_dirpath),
            ],
        )


if __name__ == "__main__":
    pass
