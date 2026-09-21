from __future__ import annotations

import pathlib
from dataclasses import replace
from typing import Any

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.28 15:04:12
# modified date:
# description:
from PySide6 import QtGui, QtWidgets

from libs import keys, paths
from libs.ai_provider import FIELDS, KINDS, PLACEHOLDERS, AISettings, ai_kind
from libs.ffmpeg_api import FFmpegAPI
from libs.runtime_settings import RuntimeSettings
from libs.ui_icons import Icon
from widgets.preference import preference_ui_settings
from widgets.preference.layout import PreferenceLayout
from widgets.preference.presenter import PreferencePresenter
from widgets.preference.runtime_group import RuntimeGroup


class Preference(QtWidgets.QDialog, PreferenceLayout):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.build_ui(self)
        self._presenter = PreferencePresenter(self)
        self.__build_ai_group()
        self.runtime_group = RuntimeGroup(self)
        self.add_page("Advanced").addWidget(self.runtime_group)
        self.listWidget__pages.setCurrentRow(0)
        self.__pref_settings = preference_ui_settings.PreferenceUISettings(window=self)
        self.__data_final_dirpath: pathlib.Path | None = None
        self.__ffmpeg_final_dirpath: pathlib.Path | None = None
        self.__is_data_valid = False
        self.__is_ffmpeg_valid = False
        self.__init_set()
        self.__connections()

    @property
    def runtime_settings(self) -> RuntimeSettings:
        return self.runtime_group.settings()

    @runtime_settings.setter
    def runtime_settings(self, value: RuntimeSettings) -> None:
        self.runtime_group.set_settings(value)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        # Keep confirmation buttons accessible when the advanced group is expanded.
        available = self.screen().availableGeometry().adjusted(16, 16, -16, -16)
        self.resize(self.size().boundedTo(available.size()))
        super().showEvent(event)

    def reject(self) -> None:
        # Reopening the retained dialog must not resurrect cancelled edits.
        self.__pref_settings.load_cfg_dict_from_file()
        super().reject()

    def __build_ai_group(self) -> None:
        # Built in code rather than Designer: four fields, no styling of its own.
        box = QtWidgets.QGroupBox("AI (Optional)", self)
        form = QtWidgets.QFormLayout(box)
        self.comboBox__ai_kind = QtWidgets.QComboBox(box)
        self.comboBox__ai_kind.addItems(KINDS)
        self.lineEdit__ai_endpoint = QtWidgets.QLineEdit(box)
        self.lineEdit__ai_model = QtWidgets.QLineEdit(box)
        self.lineEdit__ai_api_key_env = QtWidgets.QLineEdit(box)
        self.__ai_fields = {
            "endpoint": self.lineEdit__ai_endpoint,
            "model": self.lineEdit__ai_model,
            "api_key_env": self.lineEdit__ai_api_key_env,
        }
        form.addRow("Backend", self.comboBox__ai_kind)
        form.addRow("Endpoint", self.lineEdit__ai_endpoint)
        form.addRow("Model", self.lineEdit__ai_model)
        form.addRow("API key env var", self.lineEdit__ai_api_key_env)
        self.pushButton__ai_models = QtWidgets.QPushButton("Manage local models…", box)
        self.pushButton__ai_models.clicked.connect(self.open_local_models)
        form.addRow("Local models", self.pushButton__ai_models)
        self.__local_models: Any = None
        self.add_page("AI").addWidget(box)
        self.comboBox__ai_kind.currentTextChanged.connect(self.__slot_ai_kind_changed)
        self.__slot_ai_kind_changed(self.comboBox__ai_kind.currentText())

    def __slot_ai_kind_changed(self, kind: str) -> None:
        # Only the fields a backend reads are editable; the rest keep their text
        # so switching back and forth loses nothing.
        needed = FIELDS.get(kind, ())
        hints = PLACEHOLDERS.get(kind, {})
        for name, edit in self.__ai_fields.items():
            edit.setEnabled(name in needed)
            edit.setPlaceholderText(hints.get(name, ""))

    def open_local_models(self) -> None:
        """Ollama manager; Use applies kind/endpoint/model here, OK saves them."""
        if self.__local_models is None:
            from widgets.ai_models.dialog import LocalModelsDialog

            endpoint = (
                self.lineEdit__ai_endpoint.text().strip()
                or PLACEHOLDERS["local"]["endpoint"]
            )
            self.__local_models = LocalModelsDialog(endpoint, parent=self)
            self.__local_models.settingsChosen.connect(self.__apply_local_settings)
            self.__local_models.finished.connect(self.__local_models_closed)
        self.__local_models.show()
        self.__local_models.raise_()

    def __apply_local_settings(self, settings: Any) -> None:
        self.ai_settings = replace(
            self.ai_settings,
            kind="local",
            endpoint=settings.endpoint,
            model=settings.model,
        )

    def __local_models_closed(self, result: int) -> None:
        dialog, self.__local_models = self.__local_models, None
        if dialog is not None:
            dialog.deleteLater()

    def shutdown(self) -> None:
        if self.__local_models is not None:
            self.__local_models.shutdown()

    @property
    def ai_settings(self) -> AISettings:
        return AISettings(
            kind=ai_kind(self.comboBox__ai_kind.currentText()),
            endpoint=self.lineEdit__ai_endpoint.text().strip(),
            model=self.lineEdit__ai_model.text().strip(),
            api_key_env=self.lineEdit__ai_api_key_env.text().strip(),
        )

    @ai_settings.setter
    def ai_settings(self, val: AISettings) -> None:
        index = self.comboBox__ai_kind.findText(val.kind)
        self.comboBox__ai_kind.setCurrentIndex(index if index >= 0 else 0)
        self.lineEdit__ai_endpoint.setText(val.endpoint)
        self.lineEdit__ai_model.setText(val.model)
        self.lineEdit__ai_api_key_env.setText(val.api_key_env)

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
        self.buttonBox__confirm.clicked.connect(self.__slot_dialog_button)

    def __slot_dialog_button(self, button: QtWidgets.QAbstractButton) -> None:
        role = self.buttonBox__confirm.buttonRole(button)
        if role == QtWidgets.QDialogButtonBox.ButtonRole.ApplyRole:
            self._save()
        elif role == QtWidgets.QDialogButtonBox.ButtonRole.ResetRole:
            self.restore_defaults()

    def restore_defaults(self) -> None:
        """Appearance, icon, padding and font defaults; paths and AI stay as set."""
        answer = QtWidgets.QMessageBox.question(
            self,
            "Restore defaults",
            "Restore the appearance settings to their defaults? The data folder,"
            " FFmpeg, AI and advanced settings keep their values.",
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.__set_default_settings()
            self.show_page("Appearance")

    def __set_default_settings(self) -> None:
        view_font_style = keys.UISetting.view_font_style
        view_font_size = keys.UISetting.view_font_size
        listview_icon_size = keys.UISetting.listview_node_icon_size
        tableview_icon_size = keys.UISetting.tableview_node_icon_size
        treeview_icon_size = keys.UISetting.treeview_node_icon_size
        listview_thumb_scale = keys.UISetting.listview_thumbnail_scale
        tableview_thumb_scale = keys.UISetting.tableview_thumbnail_scale
        # main
        main_icon_size = keys.UISetting.dft_icon_size
        # padding
        pad_listview = keys.UISetting.padding_listview
        pad_tableview = keys.UISetting.padding_tableview
        pad_history = keys.UISetting.padding_history
        pad_category = keys.UISetting.padding_category
        pad_record = keys.UISetting.padding_record
        pad_inside = keys.UISetting.padding_inside
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
        font_lst = {}
        for idx in range(self.fontComboBox__view_font_style.count()):
            font = self.fontComboBox__view_font_style.itemText(idx)
            font_lst[font] = idx
        return font_lst

    def __get_font_by_index(self, index: int = 0) -> str:
        return self.fontComboBox__view_font_style.itemText(index)

    def __slot_data_textchanged(self, text: str) -> None:
        dirpath = pathlib.Path(text.strip())
        self.__data_final_dirpath = paths.hda_base_dirpath(base_dirpath=dirpath)
        if dirpath.exists():
            icon = Icon.IC_DONE_WHITE
            self.lineEdit__result.setStyleSheet("")
        else:
            icon = Icon.IC_CLEAR_WHITE
            self.lineEdit__result.setStyleSheet("background-color: red;color: gray;")
        self.label__valid_chk_pixmap.setPixmap(QtGui.QPixmap(icon))
        self.lineEdit__result.setText(self.__data_final_dirpath.as_posix())

    def __slot_ffmpeg_textchanged(self, text: str) -> None:
        dirpath = pathlib.Path(text.strip())
        self.__ffmpeg_final_dirpath = dirpath
        # Match the gate the feature actually uses: a directory that merely exists
        # (or an empty field, which resolves to ".") is not a usable FFmpeg.
        if self.is_valid_ffmpeg_dirpath():
            icon = Icon.IC_DONE_WHITE
            self.lineEdit__ffmpeg_result.setStyleSheet("")
        else:
            icon = Icon.IC_CLEAR_WHITE
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
        if self.data_dirpath is not None and self.data_dirpath.exists():
            start_dirpath = self.data_dirpath.resolve().as_posix()
        sel_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Data Directory", start_dirpath
        )
        if not len(sel_dir):
            return
        self.data_dirpath = sel_dir

    def __slot_select_ffmpeg_dir(self) -> None:
        start_dirpath = pathlib.Path.home().as_posix()
        if self.ffmpeg_dirpath is not None and self.ffmpeg_dirpath.exists():
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
        return pathlib.Path(data_dirpath).exists()

    def is_valid_ffmpeg_dirpath(self) -> bool:
        try:
            FFmpegAPI.executable("ffmpeg", self.ffmpeg_dirpath)
            FFmpegAPI.executable("ffprobe", self.ffmpeg_dirpath)
            return True
        except FileNotFoundError:
            return False

    def _save(self) -> bool:
        """Validate and write every setting; Apply and OK share this."""
        if not self._presenter.validate(self.lineEdit__data_dirpath.text()):
            return False
        try:
            self.__pref_settings.save_cfg_dict_to_file()
        except (ValueError, OSError) as error:
            self.show_preference_error(str(error))
            return False
        self.__pref_settings.save_main_window_geometry()
        self.__pref_settings.save_splitter_status()
        self.__is_data_valid = True
        if len(self.lineEdit__ffmpeg_dirpath.text().strip()):
            if self.ffmpeg_dirpath is not None and self.ffmpeg_dirpath.exists():
                self.__is_ffmpeg_valid = True
        return True

    def accept(self) -> None:
        if self._save():
            super().accept()

    def show_preference_error(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, "iHDA Preference", message)

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
