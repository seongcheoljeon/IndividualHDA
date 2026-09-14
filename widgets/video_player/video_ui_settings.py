from __future__ import annotations

# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.19 18:45:32
# modified date:
# description:      video UI 관련

import os
import json
from libs.settings_store import save_json
import copy

from PySide6 import QtWidgets, QtCore, QtGui

import public


class VideoUISettings(object):
    def __init__(self, window: QtWidgets.QWidget | None = None) -> None:
        self.__window = window
        self.__setting_ini = QtCore.QSettings(
            public.Paths.ini_video_filepath.as_posix(), QtCore.QSettings.IniFormat
        )
        self.__setting_json = public.Paths.json_video_filepath
        self.__cfg_dict = dict()

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
            VideoUISettings.__center_on_screen(self.__window)

    def load_splitter_status(self) -> None:
        horizon = self.__setting_ini.value(public.Name.VideoUI.splitter_horizontal)
        vertical = self.__setting_ini.value(public.Name.VideoUI.splitter_vertical)
        if horizon:
            self.__window.splitter__horizontal.restoreState(horizon)
        if vertical:
            self.__window.splitter__vertical.restoreState(vertical)

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
            self.__window.playback_idx = self.__cfg_dict[
                public.Name.VideoUI.playback_idx
            ]
            self.__window.pushButton__volume.setChecked(
                self.__cfg_dict[public.Name.VideoUI.btn_volume]
            )
            self.__window.horizontalSlider__volume.setValue(
                self.__cfg_dict[public.Name.VideoUI.slider_volume]
            )
            # playlist
            playlist = self.__cfg_dict.get(public.Name.VideoUI.playlist)
            if (playlist is not None) and (len(playlist)):
                self.__window.add_playlist(filepath_lst=[x for x in playlist])
            # last dirpath
            last_dirpath = self.__cfg_dict.get(public.Name.VideoUI.last_dirpath)
            if last_dirpath is not None:
                self.__window.last_dirpath = last_dirpath
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
