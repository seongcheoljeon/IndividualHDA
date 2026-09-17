from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from widgets.preference.preference import Preference

import copy
import dataclasses

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.28 18:45:32
# modified date:
# description:      preference UI 관련
import os
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore, QtWidgets

from libs import keys as app_keys
from libs import paths
from libs.ai_provider import AISettings
from libs.qt_helpers import center_on_screen
from libs.runtime_settings import RUNTIME_SETTINGS_KEY, RuntimeSettings
from libs.settings_store import apply_settings, load_json, save_json


class PreferenceUISettings:
    def __init__(self, window: Preference) -> None:
        self.__window = window
        self.__setting_ini = QtCore.QSettings(
            paths.Paths.ini_pref_filepath.as_posix(), QtCore.QSettings.Format.IniFormat
        )
        self.__setting_json = paths.Paths.json_pref_filepath
        self.__cfg_dict: dict[str, Any] = {}

    @property
    def cfg_dict(self) -> dict[str, Any]:
        return self.__cfg_dict

    def save_cfg_dict_to_file(self) -> None:
        runtime = self.__window.runtime_settings
        cfg = copy.deepcopy(self.__cfg_dict)
        previous = cfg.get(RUNTIME_SETTINGS_KEY)
        cfg[RUNTIME_SETTINGS_KEY] = {
            **(previous if isinstance(previous, dict) else {}),
            **dataclasses.asdict(runtime),
        }
        cfg[app_keys.Name.PreferenceUI.lineedit_data_dirpath] = (
            self.__window.data_dirpath.as_posix()
        )
        ffmpeg_dirpath = ""
        if self.__window.ffmpeg_dirpath is not None:
            ffmpeg_dirpath = self.__window.ffmpeg_dirpath.as_posix()
        cfg[app_keys.Name.PreferenceUI.lineedit_ffmpeg_dirpath] = ffmpeg_dirpath
        cfg[app_keys.Name.PreferenceUI.ai] = dataclasses.asdict(
            self.__window.ai_settings
        )
        # properties
        view_font_size = self.__window.spinBox__view_font_size.value()
        view_font_style = self.__window.fontComboBox__view_font_style.currentText()
        listview_icon_size = self.__window.spinBox__default_listview_icon_size.value()
        tableview_icon_size = self.__window.spinBox__default_tableview_icon_size.value()
        treeview_icon_size = self.__window.spinBox__default_treeview_icon_size.value()
        listview_thumb_scale = (
            self.__window.doubleSpinBox__default_listview_thumb_scale.value()
        )
        tableview_thumb_scale = (
            self.__window.doubleSpinBox__default_tableview_thumb_scale.value()
        )
        note_font_size = self.__window.spinBox__note_font_size.value()
        tags_font_size = self.__window.spinBox__tags_font_size.value()
        debug_font_size = self.__window.spinBox__debug_font_size.value()
        note_font_style = self.__window.fontComboBox__note_font_style.currentText()
        tags_font_style = self.__window.fontComboBox__tags_font_style.currentText()
        debug_font_style = self.__window.fontComboBox__debug_font_style.currentText()
        # main
        main_icon_size = self.__window.spinBox__default_main_icon_size.value()
        # padding
        pad_listview = self.__window.doubleSpinBox__default_list_item_padding.value()
        pad_tableview = self.__window.doubleSpinBox__default_table_item_padding.value()
        pad_history = self.__window.doubleSpinBox__default_history_item_padding.value()
        pad_category = self.__window.doubleSpinBox__default_cate_item_padding.value()
        pad_record = self.__window.doubleSpinBox__default_record_item_padding.value()
        pad_inside = self.__window.doubleSpinBox__default_inside_item_padding.value()
        #
        cfg[app_keys.Name.PreferenceUI.cmb_view_font_style] = view_font_style
        cfg[app_keys.Name.PreferenceUI.spb_view_font_size] = view_font_size
        cfg[app_keys.Name.PreferenceUI.spb_listview_icon_size] = listview_icon_size
        cfg[app_keys.Name.PreferenceUI.spb_tableview_icon_size] = tableview_icon_size
        cfg[app_keys.Name.PreferenceUI.spb_treeview_icon_size] = treeview_icon_size
        cfg[app_keys.Name.PreferenceUI.dspb_listview_thumb_scale] = listview_thumb_scale
        cfg[app_keys.Name.PreferenceUI.dspb_tableview_thumb_scale] = (
            tableview_thumb_scale
        )
        cfg[app_keys.Name.PreferenceUI.spb_note_font_size] = note_font_size
        cfg[app_keys.Name.PreferenceUI.spb_tags_font_size] = tags_font_size
        cfg[app_keys.Name.PreferenceUI.spb_debug_font_size] = debug_font_size
        cfg[app_keys.Name.PreferenceUI.cmb_note_font_style] = note_font_style
        cfg[app_keys.Name.PreferenceUI.cmb_tags_font_style] = tags_font_style
        cfg[app_keys.Name.PreferenceUI.cmb_debug_font_style] = debug_font_style
        # main
        cfg[app_keys.Name.PreferenceUI.spb_main_icon_size] = main_icon_size
        # padding
        cfg[app_keys.Name.PreferenceUI.pad_listview] = pad_listview
        cfg[app_keys.Name.PreferenceUI.pad_tableview] = pad_tableview
        cfg[app_keys.Name.PreferenceUI.pad_history] = pad_history
        cfg[app_keys.Name.PreferenceUI.pad_category] = pad_category
        cfg[app_keys.Name.PreferenceUI.pad_record] = pad_record
        cfg[app_keys.Name.PreferenceUI.pad_inside] = pad_inside
        #
        if not paths.Paths.config_dirpath.exists():
            os.makedirs(paths.Paths.config_dirpath.as_posix())
        save_json(self.__setting_json, cfg)
        self.__cfg_dict = cfg

    def save_main_window_geometry(self) -> None:
        self.__setting_ini.setValue(
            app_keys.Name.PreferenceUI.main_window_geometry,
            self.__window.saveGeometry(),
        )

    def save_splitter_status(self) -> None:
        pass

    def load_main_window_geometry(self) -> None:
        main_window_geo = self.__setting_ini.value(
            app_keys.Name.PreferenceUI.main_window_geometry
        )
        if main_window_geo:
            self.__window.restoreGeometry(main_window_geo)
        else:
            center_on_screen(self.__window)

    def load_splitter_status(self) -> None:
        pass

    def load_cfg_dict_from_file(self) -> None:
        self.__cfg_dict = copy.copy(load_json(self.__setting_json))
        self.__window.runtime_settings = RuntimeSettings.from_mapping(
            self.__cfg_dict.get(RUNTIME_SETTINGS_KEY)
        )
        if not self.__cfg_dict:
            return
        window = self.__window
        keys = app_keys.Name.PreferenceUI
        known = {field.name for field in dataclasses.fields(AISettings)}
        ai = self.__cfg_dict.get(keys.ai) or {}
        window.ai_settings = AISettings(**{k: v for k, v in ai.items() if k in known})

        def font(combo: QtWidgets.QFontComboBox) -> Callable[[Any], None]:
            def apply(value: Any) -> None:
                index = combo.findText(str(value))
                if index != -1:
                    combo.setCurrentIndex(index)

            return apply

        def path(name: str) -> Callable[[Any], None]:
            return lambda value: setattr(window, name, value)

        apply_settings(
            self.__cfg_dict,
            [
                (keys.lineedit_data_dirpath, path("data_dirpath")),
                (keys.lineedit_ffmpeg_dirpath, path("ffmpeg_dirpath")),
                (keys.cmb_view_font_style, font(window.fontComboBox__view_font_style)),
                (keys.cmb_note_font_style, font(window.fontComboBox__note_font_style)),
                (keys.cmb_tags_font_style, font(window.fontComboBox__tags_font_style)),
                (
                    keys.cmb_debug_font_style,
                    font(window.fontComboBox__debug_font_style),
                ),
                (keys.spb_view_font_size, window.spinBox__view_font_size.setValue),
                (
                    keys.spb_listview_icon_size,
                    window.spinBox__default_listview_icon_size.setValue,
                ),
                (
                    keys.spb_tableview_icon_size,
                    window.spinBox__default_tableview_icon_size.setValue,
                ),
                (
                    keys.spb_treeview_icon_size,
                    window.spinBox__default_treeview_icon_size.setValue,
                ),
                (
                    keys.dspb_listview_thumb_scale,
                    window.doubleSpinBox__default_listview_thumb_scale.setValue,
                ),
                (
                    keys.dspb_tableview_thumb_scale,
                    window.doubleSpinBox__default_tableview_thumb_scale.setValue,
                ),
                (keys.spb_note_font_size, window.spinBox__note_font_size.setValue),
                (keys.spb_tags_font_size, window.spinBox__tags_font_size.setValue),
                (keys.spb_debug_font_size, window.spinBox__debug_font_size.setValue),
                (
                    keys.spb_main_icon_size,
                    window.spinBox__default_main_icon_size.setValue,
                ),
                (
                    keys.pad_listview,
                    window.doubleSpinBox__default_list_item_padding.setValue,
                ),
                (
                    keys.pad_tableview,
                    window.doubleSpinBox__default_table_item_padding.setValue,
                ),
                (
                    keys.pad_history,
                    window.doubleSpinBox__default_history_item_padding.setValue,
                ),
                (
                    keys.pad_category,
                    window.doubleSpinBox__default_cate_item_padding.setValue,
                ),
                (
                    keys.pad_record,
                    window.doubleSpinBox__default_record_item_padding.setValue,
                ),
                (
                    keys.pad_inside,
                    window.doubleSpinBox__default_inside_item_padding.setValue,
                ),
            ],
        )

    def get_data_dirpath_from_saved(self) -> str | None:
        return self.cfg_dict.get(app_keys.Name.PreferenceUI.lineedit_data_dirpath)

    def get_ffmpeg_dirpath_from_saved(self) -> str | None:
        return self.cfg_dict.get(app_keys.Name.PreferenceUI.lineedit_ffmpeg_dirpath)


if __name__ == "__main__":
    pass
