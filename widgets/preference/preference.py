from __future__ import annotations

from typing import Any
import pathlib
from PySide6 import QtWidgets
# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.28 15:04:12
# modified date:
# description:


from PySide6 import QtGui

import public
from libs.ffmpeg_api import FFmpegAPI


from widgets.preference import preference_ui, preference_ui_settings


class Preference(QtWidgets.QDialog, preference_ui.Ui_Dialog__preference):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super(Preference, self).__init__(parent)
        self.setupUi(self)
        self.__pref_settings = preference_ui_settings.PreferenceUISettings(window=self)
        self.__data_final_dirpath = None
        self.__ffmpeg_final_dirpath = None
        self.__is_data_valid = False
        self.__is_ffmpeg_valid = False
        self.__init_set()
        self.__connections()

    def __init_set(self) -> None:
        self.__pref_settings.load_main_window_geometry()
        self.__pref_settings.load_splitter_status()
        self.__pref_settings.load_cfg_dict_from_file()
        self.__is_data_valid = self.is_valid_data_dirpath()
        self.__is_ffmpeg_valid = self.is_valid_ffmpeg_dirpath()
        if len(self.lineEdit__data_dirpath.text().strip()):
            self.__slot_data_textchanged(self.lineEdit__data_dirpath.text().strip())
        if len(self.lineEdit__ffmpeg_dirpath.text().strip()):
            self.__slot_ffmpeg_textchanged(self.lineEdit__ffmpeg_dirpath.text().strip())

    def __connections(self) -> None:
        self.lineEdit__data_dirpath.textChanged.connect(self.__slot_data_textchanged)
        self.lineEdit__ffmpeg_dirpath.textChanged.connect(
            self.__slot_ffmpeg_textchanged
        )
        self.toolButton__select_data_dirpath.clicked.connect(
            self.__slot_select_data_dir
        )
        self.toolButton__select_ffmpeg_dirpath.clicked.connect(
            self.__slot_select_ffmpeg_dir
        )
        self.pushButton__reset_default_app_properties.clicked.connect(
            self.__set_default_settings
        )

    def __set_default_settings(self) -> None:
        view_font_style = public.UISetting.view_font_style
        view_font_size = public.UISetting.view_font_size
        listview_icon_size = public.UISetting.listview_node_icon_size
        tableview_icon_size = public.UISetting.tableview_node_icon_size
        treeview_icon_size = public.UISetting.treeview_node_icon_size
        listview_thumb_scale = public.UISetting.listview_thumbnail_scale
        tableview_thumb_scale = public.UISetting.tableview_thumbnail_scale
        # main
        main_icon_size = public.UISetting.dft_icon_size
        # padding
        pad_listview = public.UISetting.padding_listview
        pad_tableview = public.UISetting.padding_tableview
        pad_history = public.UISetting.padding_history
        pad_category = public.UISetting.padding_category
        pad_record = public.UISetting.padding_record
        pad_inside = public.UISetting.padding_inside
        # settings
        find_idx = self.fontComboBox__view_font_style.findText(view_font_style)
        if find_idx != -1:
            self.fontComboBox__view_font_style.setCurrentIndex(find_idx)
            self.fontComboBox__note_font_style.setCurrentIndex(find_idx)
            self.fontComboBox__tags_font_style.setCurrentIndex(find_idx)
            self.fontComboBox__debug_font_style.setCurrentIndex(find_idx)
        self.spinBox__view_font_size.setValue(view_font_size)
        self.spinBox__default_listview_icon_size.setValue(listview_icon_size)
        self.spinBox__default_tableview_icon_size.setValue(tableview_icon_size)
        self.spinBox__default_treeview_icon_size.setValue(treeview_icon_size)
        self.doubleSpinBox__default_listview_thumb_scale.setValue(listview_thumb_scale)
        self.doubleSpinBox__default_tableview_thumb_scale.setValue(
            tableview_thumb_scale
        )
        self.spinBox__note_font_size.setValue(view_font_size)
        self.spinBox__tags_font_size.setValue(view_font_size)
        self.spinBox__debug_font_size.setValue(view_font_size)
        # main
        self.spinBox__default_main_icon_size.setValue(main_icon_size)
        # padding
        self.doubleSpinBox__default_list_item_padding.setValue(pad_listview)
        self.doubleSpinBox__default_table_item_padding.setValue(pad_tableview)
        self.doubleSpinBox__default_history_item_padding.setValue(pad_history)
        self.doubleSpinBox__default_cate_item_padding.setValue(pad_category)
        self.doubleSpinBox__default_record_item_padding.setValue(pad_record)
        self.doubleSpinBox__default_inside_item_padding.setValue(pad_inside)

    def get_properties_data(self) -> dict[str, Any]:
        return self.__pref_settings.cfg_dict

    def __get_font_data(self) -> dict[str, Any]:
        font_lst = dict()
        for idx in range(self.fontComboBox__view_font_style.count()):
            font = self.fontComboBox__view_font_style.itemText(idx)
            font_lst[font] = idx
        return font_lst

    def __get_font_by_index(self, index: int | None = None) -> str:
        return self.fontComboBox__view_font_style.itemText(index)

    def __slot_data_textchanged(self, text: str) -> None:
        dirpath = pathlib.Path(text.strip())
        self.__data_final_dirpath = public.hda_base_dirpath(base_dirpath=dirpath)
        if dirpath.exists():
            icon = ":/main/icons/ic_done_white.png"
            self.lineEdit__result.setStyleSheet("")
        else:
            icon = ":/main/icons/ic_clear_white.png"
            self.lineEdit__result.setStyleSheet("background-color: red;color: gray;")
        self.label__valid_chk_pixmap.setPixmap(QtGui.QPixmap(icon))
        self.lineEdit__result.setText(self.__data_final_dirpath.as_posix())

    def __slot_ffmpeg_textchanged(self, text: str) -> None:
        dirpath = pathlib.Path(text.strip())
        self.__ffmpeg_final_dirpath = dirpath
        if dirpath.exists():
            icon = ":/main/icons/ic_done_white.png"
            self.lineEdit__ffmpeg_result.setStyleSheet("")
        else:
            icon = ":/main/icons/ic_clear_white.png"
            self.lineEdit__ffmpeg_result.setStyleSheet(
                "background-color: red;color: gray;"
            )
        self.label__ffmpeg_valid_chk_pixmap.setPixmap(QtGui.QPixmap(icon))
        ffmpeg_dirpath = ""
        if self.__ffmpeg_final_dirpath.as_posix() != ".":
            ffmpeg_dirpath = self.__ffmpeg_final_dirpath.as_posix()
        self.lineEdit__ffmpeg_result.setText(ffmpeg_dirpath)

    def __slot_select_data_dir(self) -> None:
        start_dirpath = pathlib.Path.home().as_posix()
        if self.data_dirpath is not None:
            if self.data_dirpath.exists():
                start_dirpath = self.data_dirpath.resolve().as_posix()
        sel_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Data Directory", start_dirpath
        )
        if not len(sel_dir):
            return
        self.data_dirpath = sel_dir

    def __slot_select_ffmpeg_dir(self) -> None:
        start_dirpath = pathlib.Path.home().as_posix()
        if self.ffmpeg_dirpath is not None:
            if self.ffmpeg_dirpath.exists():
                start_dirpath = self.ffmpeg_dirpath.resolve().as_posix()
        sel_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select FFmpeg Directory", start_dirpath
        )
        if not len(sel_dir):
            return
        self.ffmpeg_dirpath = sel_dir

    @property
    def data_dirpath(self) -> pathlib.Path:
        return pathlib.Path(self.lineEdit__data_dirpath.text().strip())

    @data_dirpath.setter
    def data_dirpath(self, val: Any) -> None:
        self.lineEdit__data_dirpath.setText(pathlib.Path(val.strip()).as_posix())

    @property
    def ffmpeg_dirpath(self) -> pathlib.Path | None:
        ff_dirpath = self.lineEdit__ffmpeg_dirpath.text().strip()
        if len(ff_dirpath):
            return pathlib.Path(ff_dirpath)
        return None

    @ffmpeg_dirpath.setter
    def ffmpeg_dirpath(self, val: Any) -> None:
        if (val is not None) and len(val.strip()):
            self.lineEdit__ffmpeg_dirpath.setText(pathlib.Path(val.strip()).as_posix())
        else:
            self.lineEdit__ffmpeg_dirpath.setText("")

    def is_valid_data_dirpath(self) -> bool:
        data_dirpath = self.__pref_settings.get_data_dirpath_from_saved()
        if (data_dirpath is None) or (not len(data_dirpath)):
            return False
        data_dirpath = pathlib.Path(data_dirpath)
        if not data_dirpath.exists():
            return False
        return True

    def is_valid_ffmpeg_dirpath(self) -> bool:
        try:
            FFmpegAPI.executable("ffmpeg", self.ffmpeg_dirpath)
            FFmpegAPI.executable("ffprobe", self.ffmpeg_dirpath)
            return True
        except FileNotFoundError:
            return False

    def accept(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setWindowTitle("iHDA Preference")
        msgbox.setIcon(QtWidgets.QMessageBox.Warning)
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        if not len(self.lineEdit__data_dirpath.text().strip()):
            msgbox.setText("Please specify the folder where the data is stored")
            msgbox.exec()
        elif not self.data_dirpath.exists():
            msgbox.setText("Directory does not exist")
            msgbox.exec()
        else:
            self.__pref_settings.save_main_window_geometry()
            self.__pref_settings.save_splitter_status()
            self.__pref_settings.save_cfg_dict_to_file()
            self.__is_data_valid = True
            if len(self.lineEdit__ffmpeg_dirpath.text().strip()):
                if self.ffmpeg_dirpath.exists():
                    self.__is_ffmpeg_valid = True
            self.close()

    def get_data_dirpath_from_saved(self) -> pathlib.Path | None:
        data_dirpath = self.__pref_settings.get_data_dirpath_from_saved()
        if data_dirpath is None:
            return None
        return pathlib.Path(data_dirpath)

    def get_ffmpeg_dirpath_from_saved(self) -> pathlib.Path | None:
        ffmpeg_dirpath = self.__pref_settings.get_ffmpeg_dirpath_from_saved()
        if ffmpeg_dirpath is None:
            return None
        return pathlib.Path(ffmpeg_dirpath)

    @property
    def is_data_valid(self) -> bool:
        return self.__is_data_valid & self.is_valid_data_dirpath()

    @is_data_valid.setter
    def is_data_valid(self, val: Any) -> None:
        self.__is_data_valid = val

    @property
    def is_ffmpeg_valid(self) -> bool:
        return self.is_valid_ffmpeg_dirpath()

    @is_ffmpeg_valid.setter
    def is_ffmpeg_valid(self, val: Any) -> None:
        self.__is_ffmpeg_valid = val

    @property
    def data_final_dirpath(self) -> pathlib.Path | None:
        return self.__data_final_dirpath

    @property
    def ffmpeg_final_dirpath(self) -> pathlib.Path | None:
        return self.__ffmpeg_final_dirpath
