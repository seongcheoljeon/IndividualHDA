from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from widgets.web_view.web_view import WebView

import copy
import ipaddress

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.19 18:45:32
# modified date:
# description:
import os
import urllib.parse

from PySide6 import QtCore

from libs import keys, paths
from libs.qt_helpers import center_on_screen
from libs.settings_store import apply_settings, load_json, save_json


def _is_loopback(url: Any) -> bool:
    """Is this a session-scoped address that must not outlive the session?

    Houdini's help server listens on a loopback port that changes per launch, so
    persisting it makes the next session restore a dead URL and render Chromium's
    error page. Addresses the user navigated to are kept as before.
    """
    if not isinstance(url, str):
        return False
    hostname = urllib.parse.urlsplit(url).hostname or ""
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return hostname == "localhost"


class WebUISettings:
    def __init__(self, window: WebView) -> None:
        self.__window = window
        self.__setting_ini = QtCore.QSettings(
            paths.Paths.ini_web_filepath.as_posix(), QtCore.QSettings.Format.IniFormat
        )
        self.__setting_json = paths.Paths.json_web_filepath
        self.__cfg_dict: dict[str, Any] = {}

    def save_cfg_dict_to_file(self) -> None:
        address = self.__window.lineEdit__address.text()
        if not _is_loopback(address):
            self.__cfg_dict[keys.Name.WebUI.url_addr] = address
        #
        if not paths.Paths.config_dirpath.exists():
            os.makedirs(paths.Paths.config_dirpath.as_posix())
        save_json(self.__setting_json, self.__cfg_dict)

    def save_main_window_geometry(self) -> None:
        self.__setting_ini.setValue(
            keys.Name.WebUI.main_window_geometry, self.__window.saveGeometry()
        )

    def save_splitter_status(self) -> None:
        vertical = self.__window.splitter__webview_whole_vertical.saveState()
        if vertical:
            self.__setting_ini.setValue(
                keys.Name.WebUI.splitter_whole_vertical, vertical
            )

    def load_main_window_geometry(self) -> None:
        main_window_geo = self.__setting_ini.value(keys.Name.WebUI.main_window_geometry)
        if main_window_geo:
            self.__window.restoreGeometry(main_window_geo)
        else:
            center_on_screen(self.__window)

    def load_splitter_status(self) -> None:
        vertical = self.__setting_ini.value(keys.Name.WebUI.splitter_whole_vertical)
        if vertical:
            self.__window.splitter__webview_whole_vertical.restoreState(vertical)

    def load_cfg_dict_from_file(self) -> None:
        self.__cfg_dict = copy.copy(load_json(self.__setting_json))
        if not self.__cfg_dict:
            return
        # Drop a stale help-server address so it is neither restored nor re-saved;
        # apply_settings leaves a missing key at its widget default.
        if _is_loopback(self.__cfg_dict.get(keys.Name.WebUI.url_addr)):
            self.__cfg_dict.pop(keys.Name.WebUI.url_addr)
        apply_settings(
            self.__cfg_dict,
            [(keys.Name.WebUI.url_addr, self.__window.lineEdit__address.setText)],
        )


if __name__ == "__main__":
    pass
