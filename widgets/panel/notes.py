"""Notes for the Houdini panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6 import QtGui, QtWidgets

from libs import keys, log_handler, note_syntax
from libs.tags import normalize_tags
from libs.ui_icons import Icon
from widgets.asset_details.presenter import Field
from widgets.detail_view import detail_view
from widgets.ui_tokens import COMPACT_MARGIN, TAG_TEXT_COLOR

if TYPE_CHECKING:
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.ports import AssetModelPort, PresentationPort, SelectionPort
    from widgets.panel.state import PanelSessionState


@dataclass(frozen=True, slots=True)
class PanelNotesBindings:
    models: AssetModelPort
    parent: QtWidgets.QWidget
    presentation: PresentationPort
    selection: SelectionPort
    session: PanelSessionState
    ui: MainWindowLayout


class PanelNotes:
    bindings: PanelNotesBindings

    def set_hda_info_to_parms(self) -> None:
        self.bindings.session.actions.select(
            self.bindings.selection.state.asset.id,
            self.bindings.selection.state.asset.data,
        )

    def set_hda_hist_info_to_parms(self) -> None:
        if self.bindings.selection.state.history.data is None:
            self.bindings.ui.label__hist_tags.clear()
            return
        tags = self.bindings.selection.state.history.require_data().tags
        if tags is not None:
            if len(tags):
                self._set_label_hist_tags(tags)
            else:
                self.bindings.ui.label__hist_tags.clear()
        else:
            self.bindings.ui.label__hist_tags.clear()

    def set_label_tags(self, tags: Sequence[str]) -> None:
        self.bindings.ui.label__tags.setText(
            f"<font color={TAG_TEXT_COLOR}>{self.set_tag_string(tags)}</font>"
        )

    def _set_label_hist_tags(self, tags: Sequence[str]) -> None:
        self.bindings.ui.label__hist_tags.setText(
            f"<font color={TAG_TEXT_COLOR}>{self.set_tag_string(tags)}</font>"
        )

    def slot_hda_note_history(
        self, hist_note_data: Any = None, hda_name: str | None = None
    ) -> None:
        dialog = QtWidgets.QDialog(self.bindings.parent)
        dialog.setWindowTitle("iHDA note history")
        dialog.resize(840, 700)
        icon = QtGui.QIcon(QtGui.QPixmap(Icon.VIEWPORT_LOGO_TRANS))
        dialog.setWindowIcon(icon)
        font = QtGui.QFont()
        # if public.is_windows():
        #     font.setFamily("MS Shell Dlg 2")
        font.setPointSize(11)
        dialog.setFont(font)
        vertical_layout = QtWidgets.QVBoxLayout(dialog)
        vertical_layout.setContentsMargins(*([COMPACT_MARGIN] * 4))
        plain_textedit = QtWidgets.QPlainTextEdit(dialog)
        note_syntax.NoteHighLighter(plain_textedit)
        plain_textedit.setReadOnly(True)
        font_size, font_style = self.bindings.presentation.get_font_properties(
            keys.Name.PreferenceUI.spb_note_font_size,
            keys.Name.PreferenceUI.cmb_note_font_style,
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
            ctime, ver, note = data.registered_at, data.version, data.note
            res_contents = f"""
                    ***** Save Time: {ctime}, iHDA Version: {ver} *****
{note}
            """
            plain_textedit.appendPlainText(res_contents)
            plain_textedit.appendPlainText("-" * 88)
        dialog.show()

    def clear_hist_parms(self) -> None:
        self.bindings.ui.label__hist_cnt.setText(
            str(self.bindings.models.history_proxy_model.rowCount())
        )

    def clear_parms(self) -> None:
        self.bindings.ui.label__hda_count.setText(
            str(self.bindings.models.list_proxy_model.rowCount())
        )
        self.bindings.ui.label__cate_count.setText(
            str(self.bindings.models.get_category_count())
        )
        self.bindings.session.actions.select(None, None)

    def detail_view_ihda_data(self, data: Any = None) -> None:
        detailview = detail_view.DetailView(parent=self.bindings.parent)
        detailview.show_detail_ihda_data(
            data=data, is_histview=self.bindings.presentation.is_ihda_history_view
        )

    def detail_view_record_data(self, record_data: Any = None) -> None:
        if record_data is None:
            return
        detailview = detail_view.DetailView(parent=self.bindings.parent)
        detailview.show_detail_record_data(data=record_data)

    @staticmethod
    def _set_move_cursor_textedit(inst: Any) -> None:
        cursor = inst.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        scroll_bar = inst.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    @staticmethod
    def split_tag_string(tag_str: str = "") -> list[str]:

        return sorted(normalize_tags(tag_str))

    @staticmethod
    def set_tag_string(tag_lst: Sequence[str]) -> str:
        return " ".join(["#" + x for x in sorted(tag_lst)])

    def _slot_save_note_tags(self, choice: Field = "note") -> None:
        if (
            choice not in ("note", "tag")
            or not self.bindings.session.actions.capabilities.edit_metadata
        ):
            return
        if not self.bindings.session.actions.capabilities.confirm_metadata_save:
            self.bindings.session.actions.save(choice)
            return
        if self.bindings.selection.state.asset.data is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="iHDA node not clicked"
            )
            return
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.bindings.presentation.get_default_font())
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setWindowTitle(f"Save iHDA {choice}s")
        msgbox.setText(
            f'Save {choice}s to "{self.bindings.selection.state.asset.name} ({self.bindings.selection.state.asset.cate})" path iHDA node?'
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            if choice in ("note", "tag"):
                self.bindings.session.actions.save(choice)

    @property
    def hda_tags(self) -> str:
        return self.bindings.ui.textEdit__tag.toPlainText().strip()
