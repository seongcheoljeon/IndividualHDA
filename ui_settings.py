from __future__ import annotations

import copy

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.02.17 02:17:32
# modified date:
# description:
import os
from typing import Any

from PySide6 import QtCore, QtWidgets

import public
from libs.houdini_api import HoudiniAPI
from libs.qt_helpers import center_on_screen, dark_stylesheet
from libs.settings_store import apply_settings, load_json, save_json


class UISettings:
    def __init__(self, window: QtWidgets.QWidget | None = None) -> None:
        self.__window = window
        self.__setting_ini = QtCore.QSettings(
            public.Paths.ini_filepath.as_posix(), QtCore.QSettings.Format.IniFormat
        )
        self.__setting_json = public.Paths.json_filepath
        self.__zoom_val = 1.0
        self.__cfg_dict = {}

    @property
    def zoom_val(self) -> int:
        return self.__zoom_val

    @zoom_val.setter
    def zoom_val(self, val: Any) -> None:
        self.__zoom_val = val

    @property
    def get_theme(self) -> str:
        is_default = self.__cfg_dict.get(public.Name.chk_action_default)
        if is_default is None:
            return public.Name.default_theme
        if is_default:
            return public.Name.default_theme
        return public.Name.darkblue_theme

    def set_theme(self, theme: str = "Default") -> None:
        if theme == public.Name.default_theme:
            self.__window.actionDefault.setChecked(True)
            self.__window.actionDark_blue.setChecked(False)
            if public.IS_HOUDINI:
                self.__window.setProperty("houdiniStyle", True)
                add_style = """
QToolButton:pressed {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #dadbde, stop: 1 #f6f7fa);
}
QToolButton:checked {
    background-color: rgb(209, 118, 0, 85);
    border-style: outset;
}
QTreeView::item:hover {
    background-color: rgb(209, 118, 0, 85);
    border: 1px solid #ad5a00;
}
QListView::item:hover {
    background-color: rgb(209, 118, 0, 85);
    border: 1px solid #ad5a00;
}
QTableView::item:hover {
    background-color: rgb(209, 118, 0, 85);
    border: 1px solid #ad5a00;
}
QToolBar {
    spacing: 3px;
    border-style: none;
}
QMenuBar {
    border-style: none;
}
                """
                self.__window.setStyleSheet(
                    HoudiniAPI.host_stylesheet() + "\n" + add_style
                )
            else:
                self.__window.setStyleSheet("")
        else:
            self.__window.setProperty("houdiniStyle", False)
            self.__window.actionDefault.setChecked(False)
            self.__window.actionDark_blue.setChecked(True)
            self.__window.setStyleSheet(dark_stylesheet())

    def save_cfg_dict_to_file(self) -> None:
        # checkbox
        self.__cfg_dict[public.Name.chk_casesensitive_hda] = (
            self.__window.checkBox__casesensitive_hda.isChecked()
        )
        self.__cfg_dict[public.Name.chk_casesensitive_cate] = (
            self.__window.checkBox__casesensitive_cate.isChecked()
        )
        self.__cfg_dict[public.Name.chk_unpack_subnet] = (
            self.__window.actionUnpack_Subnet.isChecked()
        )
        self.__cfg_dict[public.Name.chk_auto_rename] = (
            self.__window.actionAutomatic_Name_Change.isChecked()
        )
        # network sync와 node sync는 항상 False가 저장되도록 변경
        # self.__cfg_dict[public.Name.chk_sync_network_cate] = self.__window.actionCategory_Synchronization.isChecked()
        # self.__cfg_dict[public.Name.chk_sync_node] = self.__window.actionNode_Synchronization.isChecked()
        self.__cfg_dict[public.Name.chk_sync_network_cate] = False
        self.__cfg_dict[public.Name.chk_sync_node] = False
        #
        self.__cfg_dict[public.Name.chk_note_to_sticky] = (
            self.__window.actionSticky_Note.isChecked()
        )
        self.__cfg_dict[public.Name.chk_action_default] = (
            self.__window.actionDefault.isChecked()
        )
        self.__cfg_dict[public.Name.chk_action_darkblue] = (
            self.__window.actionDark_blue.isChecked()
        )
        self.__cfg_dict[public.Name.chk_action_comment] = (
            self.__window.actionComment.isChecked()
        )
        self.__cfg_dict[public.Name.chk_action_null] = (
            self.__window.actionNull.isChecked()
        )
        self.__cfg_dict[public.Name.chk_action_input] = (
            self.__window.actionInput.isChecked()
        )
        self.__cfg_dict[public.Name.chk_action_output] = (
            self.__window.actionOuput.isChecked()
        )
        self.__cfg_dict[public.Name.chk_action_both] = (
            self.__window.actionBoth.isChecked()
        )
        # button
        self.__cfg_dict[public.Name.btn_icon_mode] = (
            self.__window.pushButton__icon_mode.isChecked()
        )
        self.__cfg_dict[public.Name.btn_table_mode] = (
            self.__window.pushButton__table_mode.isChecked()
        )
        self.__cfg_dict[public.Name.btn_hda_info] = (
            self.__window.pushButton__hda_info.isChecked()
        )
        self.__cfg_dict[public.Name.btn_hda_loc_record] = (
            self.__window.pushButton__hda_loc_record.isChecked()
        )
        self.__cfg_dict[public.Name.btn_hda_inside_node] = (
            self.__window.pushButton__hda_inside_node_view.isChecked()
        )
        self.__cfg_dict[public.Name.btn_show_thumbnail] = (
            self.__window.pushButton__thumbnail.isChecked()
        )
        # record checkbox
        self.__cfg_dict[public.Name.chk_record_only_curt_hipfile] = (
            self.__window.checkBox__record_only_current_hipfile.isChecked()
        )
        self.__cfg_dict[public.Name.chk_record_only_curt_ihda] = (
            self.__window.checkBox__record_only_current_ihda.isChecked()
        )
        # inside checkbox
        self.__cfg_dict[public.Name.chk_inside_connect_to_view] = (
            self.__window.checkBox__hda_inside_connect_to_view.isChecked()
        )
        # combobox
        self.__cfg_dict[public.Name.cmb_search_type] = (
            self.__window.comboBox__search_type.currentIndex()
        )
        # zoom value
        self.__cfg_dict[public.Name.zoom_value] = self.__zoom_val
        # spinbox
        self.__cfg_dict[public.Name.spinbox_zoom] = (
            self.__window.doubleSpinBox__zoom.value()
        )
        # stacked widget whole
        self.__cfg_dict[public.Name.stacked_widget_whole] = (
            self.__window.stackedWidget__whole.currentIndex()
        )

        if not public.Paths.config_dirpath.exists():
            os.makedirs(public.Paths.config_dirpath.as_posix())
        save_json(self.__setting_json, self.__cfg_dict)

    def save_main_window_geometry(self) -> None:
        self.__setting_ini.setValue(
            public.Name.main_window_geometry, self.__window.saveGeometry()
        )
        self.__setting_ini.setValue(
            public.Name.main_window_state, self.__window.saveState()
        )

    def save_splitter_status(self) -> None:
        whole_horizon = self.__window.splitter__whole_horizontal.saveState()
        whole_vertical = self.__window.splitter__whole_vertical.saveState()
        hda_info_vertical = self.__window.splitter__hda_info_vertical.saveState()
        #
        hda_info_whole_vertical = (
            self.__window.splitter__hda_info_whole_vertical.saveState()
        )
        ihda_whole_vertical = self.__window.splitter__ihda_whole_vertical.saveState()
        cate_whole_vertical = self.__window.splitter__cate_whole_vertical.saveState()
        ihda_hist_whole_vertical = (
            self.__window.splitter__ihda_hist_whole_vertical.saveState()
        )
        #
        if whole_horizon:
            self.__setting_ini.setValue(public.Name.whole_horizontal, whole_horizon)
        if whole_vertical:
            self.__setting_ini.setValue(public.Name.whole_vertical, whole_vertical)
        if hda_info_vertical:
            self.__setting_ini.setValue(
                public.Name.hda_info_vertical, hda_info_vertical
            )
        #
        if hda_info_whole_vertical:
            self.__setting_ini.setValue(
                public.Name.hda_info_whole_vertical, hda_info_whole_vertical
            )
        if ihda_whole_vertical:
            self.__setting_ini.setValue(
                public.Name.ihda_whole_vertical, ihda_whole_vertical
            )
        if cate_whole_vertical:
            self.__setting_ini.setValue(
                public.Name.cate_whole_vertical, cate_whole_vertical
            )
        if ihda_hist_whole_vertical:
            self.__setting_ini.setValue(
                public.Name.ihda_hist_whole_vertical, ihda_hist_whole_vertical
            )

    def load_main_window_geometry(self) -> None:
        main_window_geo = self.__setting_ini.value(public.Name.main_window_geometry)
        main_window_ste = self.__setting_ini.value(public.Name.main_window_state)
        if main_window_geo:
            self.__window.restoreGeometry(main_window_geo)
        else:
            center_on_screen(self.__window)
        if main_window_ste:
            self.__window.restoreState(main_window_ste)

    def load_splitter_status(self) -> None:
        whole_horizon = self.__setting_ini.value(public.Name.whole_horizontal)
        whole_vertical = self.__setting_ini.value(public.Name.whole_vertical)
        hda_info_vertical = self.__setting_ini.value(public.Name.hda_info_vertical)
        #
        hda_info_whole_vertical = self.__setting_ini.value(
            public.Name.hda_info_whole_vertical
        )
        ihda_whole_vertical = self.__setting_ini.value(public.Name.ihda_whole_vertical)
        cate_whole_vertical = self.__setting_ini.value(public.Name.cate_whole_vertical)
        ihda_hist_whole_vertical = self.__setting_ini.value(
            public.Name.ihda_hist_whole_vertical
        )
        #
        if whole_horizon:
            self.__window.splitter__whole_horizontal.restoreState(whole_horizon)
        if whole_vertical:
            self.__window.splitter__whole_vertical.restoreState(whole_vertical)
        if hda_info_vertical:
            self.__window.splitter__hda_info_vertical.restoreState(hda_info_vertical)
        #
        if hda_info_whole_vertical:
            self.__window.splitter__hda_info_whole_vertical.restoreState(
                hda_info_whole_vertical
            )
        if ihda_whole_vertical:
            self.__window.splitter__ihda_whole_vertical.restoreState(
                ihda_whole_vertical
            )
        if cate_whole_vertical:
            self.__window.splitter__cate_whole_vertical.restoreState(
                cate_whole_vertical
            )
        if ihda_hist_whole_vertical:
            self.__window.splitter__ihda_hist_whole_vertical.restoreState(
                ihda_hist_whole_vertical
            )

    def load_cfg_dict_from_file(self) -> None:
        self.__cfg_dict = copy.copy(load_json(self.__setting_json))
        if not self.__cfg_dict:
            return
        w = self.__window
        names = public.Name

        def zoom(value: Any) -> None:
            self.__zoom_val = float(value)

        apply_settings(
            self.__cfg_dict,
            [
                (names.chk_casesensitive_hda, w.checkBox__casesensitive_hda.setChecked),
                (
                    names.chk_casesensitive_cate,
                    w.checkBox__casesensitive_cate.setChecked,
                ),
                (names.chk_unpack_subnet, w.actionUnpack_Subnet.setChecked),
                (
                    names.chk_sync_network_cate,
                    w.actionCategory_Synchronization.setChecked,
                ),
                (names.chk_sync_node, w.actionNode_Synchronization.setChecked),
                (names.chk_note_to_sticky, w.actionSticky_Note.setChecked),
                (names.chk_action_default, w.actionDefault.setChecked),
                (names.chk_action_darkblue, w.actionDark_blue.setChecked),
                (names.chk_action_comment, w.actionComment.setChecked),
                (names.chk_action_null, w.actionNull.setChecked),
                (names.chk_action_input, w.actionInput.setChecked),
                (names.chk_action_output, w.actionOuput.setChecked),
                (names.chk_action_both, w.actionBoth.setChecked),
                (names.chk_auto_rename, w.actionAutomatic_Name_Change.setChecked),
                (
                    names.chk_record_only_curt_hipfile,
                    w.checkBox__record_only_current_hipfile.setChecked,
                ),
                (
                    names.chk_record_only_curt_ihda,
                    w.checkBox__record_only_current_ihda.setChecked,
                ),
                (
                    names.chk_inside_connect_to_view,
                    w.checkBox__hda_inside_connect_to_view.setChecked,
                ),
                (names.btn_icon_mode, w.pushButton__icon_mode.setChecked),
                (names.btn_table_mode, w.pushButton__table_mode.setChecked),
                (names.btn_hda_info, w.pushButton__hda_info.setChecked),
                (names.btn_hda_loc_record, w.pushButton__hda_loc_record.setChecked),
                (
                    names.btn_hda_inside_node,
                    w.pushButton__hda_inside_node_view.setChecked,
                ),
                (names.btn_show_thumbnail, w.pushButton__thumbnail.setChecked),
                (names.cmb_search_type, w.comboBox__search_type.setCurrentIndex),
                (names.zoom_value, zoom),
                (names.spinbox_zoom, w.doubleSpinBox__zoom.setValue),
                (names.stacked_widget_whole, w.stackedWidget__whole.setCurrentIndex),
            ],
        )


if __name__ == "__main__":
    pass
