"""Notes for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

import public
from libs import log_handler, note_syntax
from libs.database.values import normalize_tags
from widgets.detail_view import detail_view


class NotesMixin:
    def _set_hda_info_to_parms(self) -> None:
        if self._selection.asset.data is None:
            return
        note = self._selection.asset.data.get(public.Key.hda_note)
        if note is not None:
            self.textEdit__note.setPlainText(note)
            self._set_move_cursor_textedit(self.textEdit__note)
        else:
            self.textEdit__note.clear()
        tags = self._selection.asset.data.get(public.Key.hda_tags)
        if tags is not None:
            if len(tags):
                self.textEdit__tag.setPlainText(self._set_tag_string(tags))
                self._set_label_tags(tags)
            else:
                self.textEdit__tag.clear()
                self.label__tags.clear()
        else:
            self.textEdit__tag.clear()
            self.label__tags.clear()

    def _set_hda_hist_info_to_parms(self) -> None:
        if self._selection.history.data is None:
            return
        tags = self._selection.history.data.get(public.Key.History.tags)
        if tags is not None:
            if len(tags):
                self._set_label_hist_tags(tags)
            else:
                self.label__hist_tags.clear()
        else:
            self.label__hist_tags.clear()

    def _set_label_tags(self, tags: list[str]) -> None:
        self.label__tags.setText(
            f"<font color=#bfff00>{self._set_tag_string(tags)}</font>"
        )

    def _set_label_hist_tags(self, tags: list[str]) -> None:
        self.label__hist_tags.setText(
            f"<font color=#bfff00>{self._set_tag_string(tags)}</font>"
        )

    def _slot_hda_note_history(
        self, hist_note_data: Any = None, hda_name: str | None = None
    ) -> None:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("iHDA note history")
        dialog.resize(840, 700)
        icon = QtGui.QIcon(QtGui.QPixmap(":/main/icons/viewport_logo_trans.png"))
        dialog.setWindowIcon(icon)
        font = QtGui.QFont()
        # if public.is_windows():
        #     font.setFamily("MS Shell Dlg 2")
        font.setPointSize(11)
        dialog.setFont(font)
        vertical_layout = QtWidgets.QVBoxLayout(dialog)
        vertical_layout.setContentsMargins(3, 3, 3, 3)
        plain_textedit = QtWidgets.QPlainTextEdit(dialog)
        note_syntax.NoteHighLighter(plain_textedit)
        plain_textedit.setReadOnly(True)
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_note_font_size,
            public.Name.PreferenceUI.cmb_note_font_style,
        )
        font = QtGui.QFont()
        font.setFamily(font_style)
        font.setPointSize(font_size)
        plain_textedit.setFont(font)
        vertical_layout.addWidget(plain_textedit)
        if hist_note_data is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg=f'note history information of "{hda_name}" iHDA node does not exist',
            )
            return
        plain_textedit.appendPlainText(f"iHDA: {hda_name}")
        for data in hist_note_data:
            ctime, ver, note = data
            res_contents = f"""
                    ***** Save Time: {ctime}, iHDA Version: {ver} *****
{note}
            """
            plain_textedit.appendPlainText(res_contents)
            plain_textedit.appendPlainText("-" * 88)
        dialog.show()

    def _clear_hist_parms(self) -> None:
        self.label__hist_cnt.setText(str(self._ihda_history_proxy_model.rowCount()))

    def _clear_parms(self) -> None:
        self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))
        self.label__cate_count.setText(str(self._get_category_count()))
        self.textEdit__note.clear()
        self.textEdit__tag.clear()
        self.label__tags.clear()

    def _detail_view_ihda_data(self, data: Any = None) -> None:
        detailview = detail_view.DetailView(parent=self)
        detailview.show_detail_ihda_data(
            data=data, is_histview=self._is_ihda_history_view
        )

    def _detail_view_record_data(self, record_data: Any = None) -> None:
        if record_data is None:
            return
        detailview = detail_view.DetailView(parent=self)
        detailview.show_detail_record_data(data=record_data)

    @property
    def _hda_note(self) -> str:
        try:
            return self.textEdit__note.toPlainText()
        except TypeError:
            return self.textEdit__note.toPlainText()

    @staticmethod
    def _set_curt_datetime_to_note(inst: Any, flag: bool) -> None:
        if flag:
            datetime_text = NotesMixin._reshape_datetime(
                QtCore.QDateTime.currentDateTime()
            )
            text = f"{datetime_text}\n"
            # inst.setPlainText('%s\n\n%s' % (text, inst.toPlainText()))
            cursor = inst.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            cursor.insertText(text)
            scroll_bar = inst.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

    @staticmethod
    def _set_move_cursor_textedit(inst: Any) -> None:
        cursor = inst.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        scroll_bar = inst.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    @staticmethod
    def _reshape_datetime(inst_datetime: Any) -> str:
        try:
            inst_date = inst_datetime.date()
            inst_time = inst_datetime.time()
        except AttributeError:
            inst_date = inst_datetime.toDate()
            inst_time = inst_datetime.toTime()
        created_date = inst_date.toString(public.Value.qt_date_fmt_str)
        inst_week = inst_date.dayOfWeek()
        created_week = QtCore.QLocale().dayName(inst_week)
        created_time = inst_time.toString("hh:mm:ss AP")
        return f"{created_date} {created_week} {created_time}"

    @staticmethod
    def _split_tag_string(tag_str: str = "") -> list[str]:

        return sorted(normalize_tags(tag_str))

    @staticmethod
    def _set_tag_string(tag_lst: list[str]) -> str:
        return " ".join(["#" + x for x in sorted(tag_lst)])

    def _slot_save_note_tags(self, choice: str = "note") -> None:
        if self._selection.asset.data is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="iHDA node not clicked"
            )
            return
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setFont(self._get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setWindowTitle(f"Save iHDA {choice}s")
        msgbox.setText(
            f'Save {choice}s to "{self._selection.asset.name} ({self._selection.asset.cate})" path iHDA node?'
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            db_api = self._db_api_wrap(self._db_filepath)
            if db_api is None:
                return
            if choice == "note":
                self._repository.set_note(self._selection.asset.id, self._hda_note)
                self._change_hda_data(
                    row=self._assets.id_rows.get(self._selection.asset.id),
                    key=public.Key.hda_note,
                    val=self._hda_note,
                )
            elif choice == "tag":
                tag_lst = self._split_tag_string(tag_str=self._hda_tags)
                self._repository.set_tags(self._selection.asset.id, tag_lst)
                self._set_label_tags(tag_lst)
                self._change_hda_data(
                    row=self._assets.id_rows.get(self._selection.asset.id),
                    key=public.Key.hda_tags,
                    val=tag_lst,
                )
                self._ihda_history_model.update_item_data_by_hkey_id_from_model(
                    hkey_id=self._selection.asset.id,
                    key=public.Key.History.tags,
                    val=tag_lst,
                )
                self._refresh_asset_search()
            else:
                log_handler.LogHandler.log_msg(
                    method=logging.error, msg="invalid value (note/tag)"
                )
                return
            log_handler.LogHandler.log_msg(
                method=logging.info,
                msg=f'{choice}s from the "{self._selection.asset.name} ({self._selection.asset.cate})" iHDA node have been saved',
            )

    @property
    def _hda_tags(self) -> str:
        return self.textEdit__tag.toPlainText().strip()
