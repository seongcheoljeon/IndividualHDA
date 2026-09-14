"""Presentation for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

from typing import Any
import pathlib
from PySide6 import QtGui
import logging
from PySide6 import QtWidgets, QtCore
import public
from libs import log_handler
from libs import ihda_system
from libs.domain import LibraryContext

try:
    import hou
except ImportError:
    pass


class PresentationMixin:
    @staticmethod
    def _get_default_font(font_size: int | None = None) -> QtGui.QFont:
        font = QtGui.QFont()
        font.setFamily(public.UISetting.dft_font_style)
        if font_size is None:
            font.setPointSize(public.UISetting.dft_font_size)
        else:
            font.setPointSize(font_size)
        return font

    @staticmethod
    def _set_font_properties(textedit: Any = None, font_property: Any = None) -> None:
        font_size, font_style = font_property
        font = QtGui.QFont()
        font.setFamily(font_style)
        font.setPointSize(font_size)
        textedit.setFont(font)

    def _get_font_properties(self, size_key: Any, style_key: Any) -> list[Any]:
        font_size = public.UISetting.view_font_size
        if public.IS_HOUDINI:
            font_size = hou.ui.scaledSize(int(font_size))
        font_style = public.UISetting.view_font_style
        properties_data = self._preference.get_properties_data()
        if properties_data is not None:
            if size_key in properties_data:
                font_size = properties_data.get(size_key)
                font_style = properties_data.get(style_key)
        return [font_size, font_style]

    def _get_padding_properties(self, dft_pad: Any, pad_key: Any) -> float:
        padding = dft_pad
        properties_data = self._preference.get_properties_data()
        if properties_data is not None:
            if pad_key in properties_data:
                padding = properties_data.get(pad_key)
        return padding

    def _get_treeview_properties(self) -> int:
        icon_size = public.UISetting.treeview_node_icon_size
        properties_data = self._preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_treeview_icon_size in properties_data:
                icon_size = properties_data.get(
                    public.Name.PreferenceUI.spb_treeview_icon_size
                )
                if public.IS_HOUDINI:
                    icon_size = hou.ui.scaledSize(int(icon_size))
        return icon_size

    def _get_listview_properties(self, zoom_val: float) -> list[Any]:
        size_ratio = self._get_ratio_icon_size(zoom_val)
        icon_size = public.UISetting.listview_node_icon_size * size_ratio
        thumb_scale = public.UISetting.listview_thumbnail_scale
        properties_data = self._preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_listview_icon_size in properties_data:
                icon_size = (
                    properties_data.get(public.Name.PreferenceUI.spb_listview_icon_size)
                    * size_ratio
                )
                if public.IS_HOUDINI:
                    icon_size = hou.ui.scaledSize(int(icon_size))
                thumb_scale = properties_data.get(
                    public.Name.PreferenceUI.dspb_listview_thumb_scale
                )
        thumb_size = icon_size * thumb_scale
        return [icon_size, thumb_size]

    def _get_tableview_properties(self, zoom_val: float) -> list[Any]:
        size_ratio = self._get_ratio_icon_size(zoom_val)
        icon_size = public.UISetting.tableview_node_icon_size * size_ratio
        thumb_scale = public.UISetting.tableview_thumbnail_scale
        properties_data = self._preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_tableview_icon_size in properties_data:
                icon_size = (
                    properties_data.get(
                        public.Name.PreferenceUI.spb_tableview_icon_size
                    )
                    * size_ratio
                )
                if public.IS_HOUDINI:
                    icon_size = hou.ui.scaledSize(int(icon_size))
                thumb_scale = properties_data.get(
                    public.Name.PreferenceUI.dspb_tableview_thumb_scale
                )
        thumb_size = icon_size * thumb_scale
        return [icon_size, thumb_size]

    def _init_set_video_player(self) -> None:
        self.verticalLayout__video_player.addWidget(self._video_player)

    def _init_set_web_view(self) -> None:
        self.verticalLayout__web_view.addWidget(self._web_view)

    def _hide_parms(self) -> None:
        self.actionLogin.setVisible(False)
        self.actionLogout.setVisible(False)
        self.actionCreate_Account.setVisible(False)
        self.actionQuit.setVisible(False)
        self.actionUpdate.setVisible(False)
        # user info hide
        self.label__logged_id.setHidden(True)
        self.label__logged_id_pixmap.setHidden(True)

    def _dragdrop_overlay_show(
        self, text: str | None = None, fontsize: int | None = None
    ) -> None:
        self._dragdrop_overlay.text = text
        if fontsize is not None:
            self._dragdrop_overlay.fontsize = 30
        self._dragdrop_overlay.show()

    def _dragdrop_overlay_close(self) -> None:
        self._dragdrop_overlay.close()

    def _loading_show(self) -> None:
        if public.IS_HOUDINI:
            self._add_event_loop_callback(self._loading_counter)
        self._loading.show()

    def _loading_close(self) -> None:
        if public.IS_HOUDINI:
            self._remove_event_loop_callback(self._loading_counter)
        self._loading.close()

    def _loading_counter(self) -> None:
        self._loading.counter = 1
        self._loading.update()

    def _slot_node_connections(self, inst: Any = None) -> None:
        if not inst.isChecked():
            inst.setChecked(True)
        lst = [self.actionNull, self.actionInput, self.actionOuput, self.actionBoth]
        for i in lst:
            if i != inst:
                i.setChecked(False)

    def _resizing_listview(self) -> None:
        self._ihda_list_view.setResizeMode(QtWidgets.QListView.Adjust)
        self._ihda_list_view.setSpacing(3)

    def _open_houdini_file(self, hip_filepath: pathlib.Path | None = None) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("Open Houdini File")
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText("""
<font color=white size=3>Open the Houdini file?</font><br><br>
<font color=red size=5>[Note]</font> <font color=white size=4>Open the file with the new Houdini.</font>""")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.Yes:
            ihda_system.IHDASystem.open_hipfile_using_thread(hip_filepath)

    def _slot_preference(self) -> None:
        if self._preference.is_ffmpeg_valid:
            self._video_player.ffmpeg_dirpath = self._preference.ffmpeg_dirpath
        self._library = LibraryContext.from_preference(self._preference, self._user)
        if self._library is not None:
            self._library.asset_root.mkdir(parents=True, exist_ok=True)
            # DB 파일이 존재하지 않는다면 생성
            db_filepath = self._db_filepath
            assert isinstance(db_filepath, pathlib.Path)
            if not db_filepath.exists():
                db_api = self._services.open_database(db_filepath)
                db_api.create_tables()
                is_done = db_api.insert_users(
                    user_id=self._user, email=f"{self._user}@local"
                )
                if not is_done:
                    log_handler.LogHandler.log_msg(
                        method=logging.error, msg="user creation failed"
                    )
                    return
                msgbox = QtWidgets.QMessageBox(self)
                msgbox.setFont(self._get_default_font())
                msgbox.setIcon(QtWidgets.QMessageBox.Information)
                msgbox.setWindowTitle("Individual iHDA")
                msgbox.setText("Please restart the app.")
                _ = msgbox.exec()
        # app properties
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size,
            public.Name.PreferenceUI.cmb_view_font_style,
        )
        self._ihda_list_model.set_font(style=font_style, size=font_size)
        self._ihda_table_model.set_font(style=font_style, size=font_size)
        self._ihda_history_model.set_font(style=font_style, size=font_size)
        self._ihda_category_model.set_font(style=font_style, size=font_size)
        self._ihda_record_model.set_font(style=font_style, size=font_size)
        self._ihda_inside_model.set_font(style=font_style, size=font_size)
        treeview_icon_size = self._get_treeview_properties()
        self._set_tree_view_item_icon_size(treeview_icon_size)
        self._set_view_item_icon_size(self.doubleSpinBox__zoom.value())
        # text view의 font size, style 적용
        self._set_font_properties(
            self.textEdit__note,
            self._get_font_properties(
                public.Name.PreferenceUI.spb_note_font_size,
                public.Name.PreferenceUI.cmb_note_font_style,
            ),
        )
        self._set_font_properties(
            self.textEdit__tag,
            self._get_font_properties(
                public.Name.PreferenceUI.spb_tags_font_size,
                public.Name.PreferenceUI.cmb_tags_font_style,
            ),
        )
        self._set_font_properties(
            self.textBrowser__debug,
            self._get_font_properties(
                public.Name.PreferenceUI.spb_debug_font_size,
                public.Name.PreferenceUI.cmb_debug_font_style,
            ),
        )
        # padding 적용
        self._set_view_padding(self.doubleSpinBox__zoom.value())
        # main icon size
        self._set_main_default_icon_size()

    def _set_main_default_icon_size(self) -> None:
        icon_size = public.UISetting.dft_icon_size
        properties_data = self._preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_main_icon_size in properties_data:
                icon_size = properties_data.get(
                    public.Name.PreferenceUI.spb_main_icon_size
                )
        if public.IS_HOUDINI:
            icon_size = hou.ui.scaledSize(int(icon_size))
        self.toolBar.setIconSize(QtCore.QSize(icon_size, icon_size))
        for inst in self._icon_variables():
            qsize = QtCore.QSize(icon_size, icon_size)
            inst.setIconSize(qsize)

    def _icon_variables(self) -> list[QtWidgets.QAbstractButton]:
        lst = self.centralwidget.findChildren(QtWidgets.QCheckBox)
        lst.extend(self.centralwidget.findChildren(QtWidgets.QPushButton))
        lst.extend(self._video_player.findChildren(QtWidgets.QPushButton))
        lst.extend(self._web_view.findChildren(QtWidgets.QPushButton))
        lst.extend(self._preference.findChildren(QtWidgets.QToolButton))
        lst.extend(self._rename_ihda.findChildren(QtWidgets.QPushButton))
        lst.extend(self._make_videoinfo.findChildren(QtWidgets.QPushButton))
        return lst

    def _set_is_ready(self) -> None:
        self._is_ready = False
        if self._library is not None:
            if self._library.db_filepath.exists():
                self._is_ready = True
                self.centralwidget.setEnabled(True)
                self.toolBar.setEnabled(True)

    @staticmethod
    def _change_org_node_name(parent_node: Any = None, node_name: Any = None) -> None:
        for child in parent_node.children():
            if child.name() == node_name:
                child.setName(child.name() + "_", unique_name=True)

    def _slot_zoomin(self) -> None:
        zoom_val = (
            self.doubleSpinBox__zoom.value() + public.UISetting.interval_zoom_value
        )
        if zoom_val > public.UISetting.max_zoom_value:
            zoom_val = public.UISetting.max_zoom_value
        self.doubleSpinBox__zoom.setValue(zoom_val)

    def _slot_zoomout(self) -> None:
        zoom_val = (
            self.doubleSpinBox__zoom.value() - public.UISetting.interval_zoom_value
        )
        if zoom_val < public.UISetting.min_zoom_value:
            zoom_val = public.UISetting.min_zoom_value
        self.doubleSpinBox__zoom.setValue(zoom_val)

    def _slot_zoom_value(self, zoom_val: float) -> None:
        self._set_view_item_icon_size(zoom_val)
        log_handler.LogHandler.log_msg(
            method=logging.info, msg="zoom value: {0} %".format(zoom_val)
        )

    def _set_tree_view_item_icon_size(self, val: Any) -> None:
        # treeview는 zoom 영향이 없도록. 이것은 preference에서만 조절 할 수 있다.
        self._ihda_category_model.set_icon_size(val)
        self._ihda_record_model.set_icon_size(val)
        self._ihda_inside_model.set_icon_size(val)
        self._ihda_category_view.expandAll()
        self._ihda_record_view.expandAll()
        self._ihda_inside_view.expandAll()

    def _set_view_padding(self, val: Any) -> None:
        tableview_icon_size, tableview_thumb_size = self._get_tableview_properties(val)
        # get padding
        pad_listview = self._get_padding_properties(
            public.UISetting.padding_listview, public.Name.PreferenceUI.pad_listview
        )
        pad_tableview = self._get_padding_properties(
            public.UISetting.padding_tableview, public.Name.PreferenceUI.pad_tableview
        )
        pad_history = self._get_padding_properties(
            public.UISetting.padding_history, public.Name.PreferenceUI.pad_history
        )
        pad_category = self._get_padding_properties(
            public.UISetting.padding_category, public.Name.PreferenceUI.pad_category
        )
        pad_record = self._get_padding_properties(
            public.UISetting.padding_record, public.Name.PreferenceUI.pad_record
        )
        pad_inside = self._get_padding_properties(
            public.UISetting.padding_inside, public.Name.PreferenceUI.pad_inside
        )
        # set padding
        self._ihda_list_model.set_padding(pad_listview)
        self._ihda_category_model.set_padding(pad_category)
        self._ihda_record_model.set_padding(pad_record)
        self._ihda_inside_model.set_padding(pad_inside)
        # inside model 구현 되면 추가
        # tableview
        if self._is_show_thumbnail:
            vertical_cell_size = tableview_thumb_size
        else:
            vertical_cell_size = tableview_icon_size
        self._ihda_table_view.verticalHeader().setDefaultSectionSize(
            vertical_cell_size + pad_tableview
        )
        self._ihda_history_view.verticalHeader().setDefaultSectionSize(
            tableview_thumb_size + pad_history
        )

    def _set_view_item_icon_size(self, val: Any) -> None:
        listview_icon_size, listview_thumb_size = self._get_listview_properties(val)
        tableview_icon_size, tableview_thumb_size = self._get_tableview_properties(val)
        self._ihda_list_model.set_icon_size(
            icon_size=listview_icon_size, thumb_size=listview_thumb_size
        )
        self._ihda_table_model.set_icon_size(
            icon_size=tableview_icon_size, thumb_size=tableview_thumb_size
        )
        self._ihda_history_model.set_icon_size(
            icon_size=tableview_icon_size, thumb_size=tableview_thumb_size
        )
        # tableview
        if self._is_show_thumbnail:
            vertical_cell_size = tableview_thumb_size
        else:
            vertical_cell_size = tableview_icon_size
        self._ihda_table_view.verticalHeader().setDefaultSectionSize(vertical_cell_size)
        self._ihda_history_view.verticalHeader().setDefaultSectionSize(
            tableview_thumb_size
        )

    @property
    def _is_show_thumbnail(self) -> bool:
        return self.pushButton__thumbnail.isChecked()

    @staticmethod
    def _get_ratio_icon_size(val: Any) -> float:
        return val / 100.0

    @property
    def _is_icon_mode(self) -> bool:
        return self.pushButton__icon_mode.isChecked()

    @property
    def _is_ihda_history_view(self) -> bool:
        return self.stackedWidget__whole.currentIndex() == self._hist_view_idx

    def _slot_cfg_reset(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("iHDA Reset APP Properties")
        msgbox.setIcon(QtWidgets.QMessageBox.Question)
        msgbox.setText("Do you want to reset app properties?")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.No:
            return
        self._is_reset_app_properties = True
        self.centralwidget.setDisabled(True)
        self.toolBar.setDisabled(True)
        self.menubar.setDisabled(True)
        log_handler.LogHandler.log_msg(
            method=logging.debug, msg="initialized application properties"
        )
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setWindowTitle("iHDA Reset APP Properties")
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText("App property initialization is complete. Please start again.")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        _ = msgbox.exec()

    def _set_theme(self, theme: str = "Default") -> None:
        self._ui_settings.set_theme(theme=theme)

    def _slot_about(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font(font_size=15))
        msgbox.setWindowTitle("Individual HDA (Houdini built-in app)")
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIconPixmap(QtGui.QPixmap(":/main/icons/viewport_logo_trans.png"))
        msgbox.setText(public.Info.app_info(self._RECOMMENDED_HOUDINI_VERSION))
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setDetailedText(public.Info.license_info())
        msgbox.setStyleSheet("""
QLabel {
    min-width: 800px;
}
QTextEdit {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop: 0 white, stop: 0.4 gray, stop: 1 green);
    font: 30px;
    color: black;
    min-height: 300px;
}
        """)
        btn_detail = None
        for btn in msgbox.buttons():
            if msgbox.buttonRole(btn) == QtWidgets.QMessageBox.ActionRole:
                btn_detail = btn
                break
        if btn_detail is not None:
            btn_detail.click()
        # msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec()

    def _slot_help(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font(font_size=15))
        msgbox.setWindowTitle("Individual HDA Help")
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText(
            """
            <a href="https://www.youtube.com/watch?v=XR7h8uGR_iI" style="color:red"
            target="_blank">iHDA Help video</a><br>
            <br>
            <a href="https://www.youtube.com/watch?v=MYkK8c2KOCA" style="color:red"
            target="_blank">Codec & FFmpeg Setup Help video</a>
            """
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setStyleSheet("QLabel {min-width: 500px;}")
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec()

    def _slot_submit_bug_report(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font(font_size=15))
        msgbox.setWindowTitle("Submit Bug Report")
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText(
            '<a href="mailto:saelly55@gmail.com?Subject=[iHDA] Bug Report" style="color:red"'
            'target="_top">Send Bug Report</a><br>'
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setDetailedText("Click the link to send an email.")
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec()

    def _slot_submit_feedback(self) -> None:
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font(font_size=15))
        msgbox.setWindowTitle("Submit Feedback")
        msgbox.setTextFormat(QtCore.Qt.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText(
            '<a href="mailto:saelly55@gmail.com?Subject=[iHDA] Feedback" style="color:red"'
            'target="_top">Send Feedback</a><br>'
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgbox.setDetailedText("Click the link to send an email.")
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec()

    def _set_icon_size_from_widget(
        self, widget: QtWidgets.QWidget | None = None
    ) -> None:
        icon_lst = widget.findChildren(QtWidgets.QPushButton)
        icon_lst.extend(widget.findChildren(QtWidgets.QToolButton))
        icon_lst.extend(widget.findChildren(QtWidgets.QCheckBox))
        icon_size = public.UISetting.dft_icon_size
        properties_data = self._preference.get_properties_data()
        if properties_data is not None:
            if public.Name.PreferenceUI.spb_main_icon_size in properties_data:
                icon_size = properties_data.get(
                    public.Name.PreferenceUI.spb_main_icon_size
                )
        if public.IS_HOUDINI:
            icon_size = hou.ui.scaledSize(int(icon_size))
        for inst in icon_lst:
            qsize = QtCore.QSize(icon_size, icon_size)
            inst.setIconSize(qsize)

    @staticmethod
    def _copy_to_clipboard(text: str = "") -> None:
        clip = QtWidgets.QApplication.clipboard()
        clip.clear()
        clip.setText(text)

    @staticmethod
    def _slot_donate() -> None:
        is_done = ihda_system.IHDASystem.open_browser(
            "https://buymeacoffee.com/seongcheol"
        )

    @staticmethod
    def _slot_download_ffmpeg_site() -> None:
        is_done = ihda_system.IHDASystem.open_browser(
            "https://ffmpeg.org/download.html"
        )
        if is_done:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="opened ffmpeg download site"
            )
        else:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="ffmpeg download site could not be opened"
            )

    @staticmethod
    def _slot_download_codec_site() -> None:
        is_done = ihda_system.IHDASystem.open_browser(
            "http://www.codecguide.com/download_k-lite_codec_pack_basic.htm"
        )
        if is_done:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="opened codec download site"
            )
        else:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="codec download site could not be opened"
            )
