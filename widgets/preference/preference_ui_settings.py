# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.28 18:45:32
# modified date:    
# description:      preference UI 관련

import os
import json
import copy
from imp import reload

from PySide2 import QtWidgets, QtCore

import public

reload(public)


class PreferenceUISettings(object):
    def __init__(self, window=None):
        self.__window = window
        self.__setting_ini = QtCore.QSettings(public.Paths.ini_pref_filepath.as_posix(), QtCore.QSettings.IniFormat)
        self.__setting_json = public.Paths.json_pref_filepath
        self.__cfg_dict = dict()

    @property
    def cfg_dict(self):
        return self.__cfg_dict

    def save_cfg_dict_to_file(self):
        self.__cfg_dict[public.Name.PreferenceUI.lineedit_data_dirpath] = self.__window.data_dirpath.as_posix()
        ffmpeg_dirpath = ''
        if self.__window.ffmpeg_dirpath is not None:
            ffmpeg_dirpath = self.__window.ffmpeg_dirpath.as_posix()
        self.__cfg_dict[public.Name.PreferenceUI.lineedit_ffmpeg_dirpath] = ffmpeg_dirpath
        # properties
        view_font_size = self.__window.spinBox__view_font_size.value()
        view_font_style = self.__window.fontComboBox__view_font_style.currentText()
        listview_icon_size = self.__window.spinBox__default_listview_icon_size.value()
        tableview_icon_size = self.__window.spinBox__default_tableview_icon_size.value()
        treeview_icon_size = self.__window.spinBox__default_treeview_icon_size.value()
        listview_thumb_scale = self.__window.doubleSpinBox__default_listview_thumb_scale.value()
        tableview_thumb_scale = self.__window.doubleSpinBox__default_tableview_thumb_scale.value()
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
        self.__cfg_dict[public.Name.PreferenceUI.cmb_view_font_style] = view_font_style
        self.__cfg_dict[public.Name.PreferenceUI.spb_view_font_size] = view_font_size
        self.__cfg_dict[public.Name.PreferenceUI.spb_listview_icon_size] = listview_icon_size
        self.__cfg_dict[public.Name.PreferenceUI.spb_tableview_icon_size] = tableview_icon_size
        self.__cfg_dict[public.Name.PreferenceUI.spb_treeview_icon_size] = treeview_icon_size
        self.__cfg_dict[public.Name.PreferenceUI.dspb_listview_thumb_scale] = listview_thumb_scale
        self.__cfg_dict[public.Name.PreferenceUI.dspb_tableview_thumb_scale] = tableview_thumb_scale
        self.__cfg_dict[public.Name.PreferenceUI.spb_note_font_size] = note_font_size
        self.__cfg_dict[public.Name.PreferenceUI.spb_tags_font_size] = tags_font_size
        self.__cfg_dict[public.Name.PreferenceUI.spb_debug_font_size] = debug_font_size
        self.__cfg_dict[public.Name.PreferenceUI.cmb_note_font_style] = note_font_style
        self.__cfg_dict[public.Name.PreferenceUI.cmb_tags_font_style] = tags_font_style
        self.__cfg_dict[public.Name.PreferenceUI.cmb_debug_font_style] = debug_font_style
        # main
        self.__cfg_dict[public.Name.PreferenceUI.spb_main_icon_size] = main_icon_size
        # padding
        self.__cfg_dict[public.Name.PreferenceUI.pad_listview] = pad_listview
        self.__cfg_dict[public.Name.PreferenceUI.pad_tableview] = pad_tableview
        self.__cfg_dict[public.Name.PreferenceUI.pad_history] = pad_history
        self.__cfg_dict[public.Name.PreferenceUI.pad_category] = pad_category
        self.__cfg_dict[public.Name.PreferenceUI.pad_record] = pad_record
        self.__cfg_dict[public.Name.PreferenceUI.pad_inside] = pad_inside
        #
        if not public.Paths.config_dirpath.exists():
            os.makedirs(public.Paths.config_dirpath.as_posix())
        with open(self.__setting_json.as_posix(), 'w') as fp:
            json.dump(self.__cfg_dict, fp, encoding='utf-8', indent=2)

    def save_main_window_geometry(self):
        self.__setting_ini.setValue(public.Name.PreferenceUI.main_window_geometry, self.__window.saveGeometry())

    def save_splitter_status(self):
        pass

    def load_main_window_geometry(self):
        main_window_geo = self.__setting_ini.value(public.Name.PreferenceUI.main_window_geometry)
        if main_window_geo:
            self.__window.restoreGeometry(main_window_geo)
        else:
            PreferenceUISettings.center_on_screen(self.__window)

    def load_splitter_status(self):
        pass

    def load_cfg_dict_from_file(self):
        if not self.__setting_json.exists():
            return
        with self.__setting_json.open('r') as fp:
            try:
                data = json.load(fp, encoding='utf-8')
                self.__cfg_dict = copy.copy(data)
            except ValueError as err:
                self.__cfg_dict = None
                os.remove(self.__setting_json.as_posix())
                return
        try:
            self.__window.data_dirpath = self.__cfg_dict[public.Name.PreferenceUI.lineedit_data_dirpath]
            self.__window.ffmpeg_dirpath = self.__cfg_dict[public.Name.PreferenceUI.lineedit_ffmpeg_dirpath]
            #
            view_font_size = self.__cfg_dict[public.Name.PreferenceUI.spb_view_font_size]
            view_font_style = self.__cfg_dict[public.Name.PreferenceUI.cmb_view_font_style]
            listview_icon_size = self.__cfg_dict[public.Name.PreferenceUI.spb_listview_icon_size]
            tableview_icon_size = self.__cfg_dict[public.Name.PreferenceUI.spb_tableview_icon_size]
            treeview_icon_size = self.__cfg_dict[public.Name.PreferenceUI.spb_treeview_icon_size]
            listview_thumb_scale = self.__cfg_dict[public.Name.PreferenceUI.dspb_listview_thumb_scale]
            tableview_thumb_scale = self.__cfg_dict[public.Name.PreferenceUI.dspb_tableview_thumb_scale]
            note_font_size = self.__cfg_dict[public.Name.PreferenceUI.spb_note_font_size]
            tags_font_size = self.__cfg_dict[public.Name.PreferenceUI.spb_tags_font_size]
            debug_font_size = self.__cfg_dict[public.Name.PreferenceUI.spb_debug_font_size]
            note_font_style = self.__cfg_dict[public.Name.PreferenceUI.cmb_note_font_style]
            tags_font_style = self.__cfg_dict[public.Name.PreferenceUI.cmb_tags_font_style]
            debug_font_style = self.__cfg_dict[public.Name.PreferenceUI.cmb_debug_font_style]
            # main
            main_icon_size = self.__cfg_dict[public.Name.PreferenceUI.spb_main_icon_size]
            # padding
            pad_listview = self.__cfg_dict[public.Name.PreferenceUI.pad_listview]
            pad_tableview = self.__cfg_dict[public.Name.PreferenceUI.pad_tableview]
            pad_history = self.__cfg_dict[public.Name.PreferenceUI.pad_history]
            pad_category = self.__cfg_dict[public.Name.PreferenceUI.pad_category]
            pad_record = self.__cfg_dict[public.Name.PreferenceUI.pad_record]
            pad_inside = self.__cfg_dict[public.Name.PreferenceUI.pad_inside]
            #
            find_idx = self.__window.fontComboBox__view_font_style.findText(view_font_style)
            if find_idx != -1:
                self.__window.fontComboBox__view_font_style.setCurrentIndex(find_idx)
            note_find_idx = self.__window.fontComboBox__note_font_style.findText(note_font_style)
            if note_find_idx != -1:
                self.__window.fontComboBox__note_font_style.setCurrentIndex(note_find_idx)
            tags_find_idx = self.__window.fontComboBox__tags_font_style.findText(tags_font_style)
            if tags_find_idx != -1:
                self.__window.fontComboBox__tags_font_style.setCurrentIndex(tags_find_idx)
            debug_find_idx = self.__window.fontComboBox__debug_font_style.findText(debug_font_style)
            if debug_find_idx != -1:
                self.__window.fontComboBox__debug_font_style.setCurrentIndex(debug_find_idx)
            #
            self.__window.spinBox__view_font_size.setValue(view_font_size)
            self.__window.spinBox__default_listview_icon_size.setValue(listview_icon_size)
            self.__window.spinBox__default_tableview_icon_size.setValue(tableview_icon_size)
            self.__window.spinBox__default_treeview_icon_size.setValue(treeview_icon_size)
            self.__window.doubleSpinBox__default_listview_thumb_scale.setValue(listview_thumb_scale)
            self.__window.doubleSpinBox__default_tableview_thumb_scale.setValue(tableview_thumb_scale)
            self.__window.spinBox__note_font_size.setValue(note_font_size)
            self.__window.spinBox__tags_font_size.setValue(tags_font_size)
            self.__window.spinBox__debug_font_size.setValue(debug_font_size)
            # main
            self.__window.spinBox__default_main_icon_size.setValue(main_icon_size)
            # padding
            self.__window.doubleSpinBox__default_list_item_padding.setValue(pad_listview)
            self.__window.doubleSpinBox__default_table_item_padding.setValue(pad_tableview)
            self.__window.doubleSpinBox__default_history_item_padding.setValue(pad_history)
            self.__window.doubleSpinBox__default_cate_item_padding.setValue(pad_category)
            self.__window.doubleSpinBox__default_record_item_padding.setValue(pad_record)
            self.__window.doubleSpinBox__default_inside_item_padding.setValue(pad_inside)
        except KeyError as err:
            os.remove(self.__setting_json.as_posix())
            return

    def get_data_dirpath_from_saved(self):
        return self.cfg_dict.get(public.Name.PreferenceUI.lineedit_data_dirpath)

    def get_ffmpeg_dirpath_from_saved(self):
        return self.cfg_dict.get(public.Name.PreferenceUI.lineedit_ffmpeg_dirpath)

    @staticmethod
    def center_on_screen(inst):
        res = QtWidgets.QDesktopWidget().screenGeometry()
        inst.move((res.width() / 2) - (inst.frameSize().width() / 2),
                  (res.height() / 2) - (inst.frameSize().height() / 2))


if __name__ == '__main__':
    pass
