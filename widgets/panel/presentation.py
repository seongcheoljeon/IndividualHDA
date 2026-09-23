"""Presentation for the Houdini panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from PySide6 import QtCore, QtGui, QtWidgets

from libs import host, houdini_api, ihda_system, keys, log_handler
from libs.app_metadata import FFMPEG_DOWNLOAD_URL, SUPPORT_URL
from libs.domain import LibraryContext

if TYPE_CHECKING:
    from libs.dragdrop_overlay import Overlay as DragOverlay
    from libs.loading_indicator import Overlay
    from ui_settings import UISettings
    from widgets.asset_browser.integration import AssetBrowserIntegration
    from widgets.asset_details.integration import AssetDetailsIntegration
    from widgets.make_video_info.make_video_info import MakeVideoInfo
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.ports import AssetModelPort, CallbacksPort, LibraryQueryPort
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState, PanelStatus, PanelViews
    from widgets.preference.preference import Preference
    from widgets.rename_ihda.rename_ihda import RenameIHDA
    from widgets.toast import ToastStack
    from widgets.video_player import UnavailableVideoPlayer
    from widgets.video_player.video_player import VideoPlayer


@dataclass(frozen=True, slots=True)
class PanelPresentationBindings:
    browser: AssetBrowserIntegration
    callbacks: CallbacksPort
    details: AssetDetailsIntegration
    drag_overlay: DragOverlay
    loading: Overlay
    models: AssetModelPort
    parent: QtWidgets.QWidget
    preference: Preference
    queries: LibraryQueryPort
    rename_dialog: RenameIHDA
    services: PanelServices
    session: PanelSessionState
    status: PanelStatus
    toasts: ToastStack
    ui: MainWindowLayout
    ui_settings: UISettings
    video_info: MakeVideoInfo
    video_player: VideoPlayer | UnavailableVideoPlayer
    views: PanelViews
    web_view: QtWidgets.QWidget


class PanelPresentation:
    bindings: PanelPresentationBindings

    @staticmethod
    def get_default_font(font_size: int | None = None) -> QtGui.QFont:
        font = QtGui.QFont()
        font.setFamily(keys.UISetting.dft_font_style)
        if font_size is None:
            font.setPointSize(keys.UISetting.dft_font_size)
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

    def get_font_properties(self, size_key: Any, style_key: Any) -> list[Any]:
        font_size = keys.UISetting.view_font_size
        if host.IS_HOUDINI:
            font_size = houdini_api.HoudiniAPI.scaled_size(int(font_size))
        font_style = keys.UISetting.view_font_style
        properties_data = self.bindings.preference.get_properties_data()
        if properties_data is not None and size_key in properties_data:
            font_size = properties_data[size_key]
            font_style = properties_data.get(style_key, font_style)
        return [font_size, font_style]

    def get_padding_properties(self, dft_pad: Any, pad_key: Any) -> int:
        padding = dft_pad
        properties_data = self.bindings.preference.get_properties_data()
        if properties_data is not None and pad_key in properties_data:
            padding = properties_data.get(pad_key)
        return int(padding)

    def get_treeview_properties(self) -> int:
        icon_size = keys.UISetting.treeview_node_icon_size
        properties_data = self.bindings.preference.get_properties_data()
        if properties_data is not None:
            if keys.Name.PreferenceUI.spb_treeview_icon_size in properties_data:
                icon_size = properties_data[
                    keys.Name.PreferenceUI.spb_treeview_icon_size
                ]
                if host.IS_HOUDINI:
                    icon_size = houdini_api.HoudiniAPI.scaled_size(int(icon_size))
        return icon_size

    def get_listview_properties(self, zoom_val: float) -> list[Any]:
        size_ratio = self._get_ratio_icon_size(zoom_val)
        icon_size = keys.UISetting.listview_node_icon_size * size_ratio
        thumb_scale = keys.UISetting.listview_thumbnail_scale
        properties_data = self.bindings.preference.get_properties_data()
        if properties_data is not None:
            if keys.Name.PreferenceUI.spb_listview_icon_size in properties_data:
                icon_size = (
                    properties_data[keys.Name.PreferenceUI.spb_listview_icon_size]
                    * size_ratio
                )
                if host.IS_HOUDINI:
                    icon_size = houdini_api.HoudiniAPI.scaled_size(int(icon_size))
                thumb_scale = properties_data.get(
                    keys.Name.PreferenceUI.dspb_listview_thumb_scale, thumb_scale
                )
        thumb_size = icon_size * thumb_scale
        return [icon_size, thumb_size]

    def get_tableview_properties(self, zoom_val: float) -> list[Any]:
        size_ratio = self._get_ratio_icon_size(zoom_val)
        icon_size = keys.UISetting.tableview_node_icon_size * size_ratio
        thumb_scale = keys.UISetting.tableview_thumbnail_scale
        properties_data = self.bindings.preference.get_properties_data()
        if properties_data is not None:
            if keys.Name.PreferenceUI.spb_tableview_icon_size in properties_data:
                icon_size = (
                    properties_data[keys.Name.PreferenceUI.spb_tableview_icon_size]
                    * size_ratio
                )
                if host.IS_HOUDINI:
                    icon_size = houdini_api.HoudiniAPI.scaled_size(int(icon_size))
                thumb_scale = properties_data.get(
                    keys.Name.PreferenceUI.dspb_tableview_thumb_scale, thumb_scale
                )
        thumb_size = icon_size * thumb_scale
        return [icon_size, thumb_size]

    def _init_set_video_player(self) -> None:
        self.bindings.ui.verticalLayout__video_player.addWidget(
            self.bindings.video_player
        )

    def _init_set_web_view(self) -> None:
        self.bindings.ui.verticalLayout__web_view.addWidget(self.bindings.web_view)

    def _hide_parms(self) -> None:
        self.bindings.ui.actionLogin.setVisible(False)
        self.bindings.ui.actionLogout.setVisible(False)
        self.bindings.ui.actionCreate_Account.setVisible(False)
        self.bindings.ui.actionQuit.setVisible(False)
        self.bindings.ui.actionUpdate.setVisible(False)
        # user info hide
        self.bindings.ui.label__logged_id.setHidden(True)
        self.bindings.ui.label__logged_id_pixmap.setHidden(True)

    def dragdrop_overlay_show(
        self, text: str | None = None, fontsize: int | None = None
    ) -> None:
        self.bindings.drag_overlay.text = text
        if fontsize is not None:
            self.bindings.drag_overlay.fontsize = 30
        self.bindings.drag_overlay.show()

    def dragdrop_overlay_close(self) -> None:
        self.bindings.drag_overlay.close()

    def loading_show(self) -> None:
        if host.IS_HOUDINI:
            self.bindings.callbacks.add_event_loop_callback(self._loading_counter)
        self.bindings.loading.show()

    def loading_close(self) -> None:
        if host.IS_HOUDINI:
            self.bindings.callbacks.remove_event_loop_callback(self._loading_counter)
        self.bindings.loading.close()

    def notify(
        self,
        message: str,
        *,
        action: str | None = None,
        on_action: Callable[[], None] | None = None,
        level: Literal["info", "warning", "error"] = "info",
    ) -> None:
        """Non-modal feedback: a toast (with an optional action), the status bar
        and the log. Modal boxes stay for questions and irreversible steps."""
        method = {
            "info": logging.info,
            "warning": logging.warning,
            "error": logging.error,
        }
        log_handler.LogHandler.log_msg(method=method[level], msg=message)
        self.bindings.toasts.push(
            message, action=action, on_action=on_action, level=level
        )
        self.bindings.ui.statusbar.showMessage(message, 5000)

    def _loading_counter(self) -> None:
        self.bindings.loading.counter = 1
        self.bindings.loading.update()

    def _slot_node_connections(self, inst: Any = None) -> None:
        if not inst.isChecked():
            inst.setChecked(True)
        lst = [
            self.bindings.ui.actionNull,
            self.bindings.ui.actionInput,
            self.bindings.ui.actionOuput,
            self.bindings.ui.actionBoth,
        ]
        for i in lst:
            if i != inst:
                i.setChecked(False)

    def resizing_listview(self) -> None:
        self.bindings.views.assets_list.setResizeMode(
            QtWidgets.QListView.ResizeMode.Adjust
        )
        self.bindings.views.assets_list.setSpacing(3)

    def open_houdini_file(self, hip_filepath: pathlib.Path | None = None) -> None:
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.get_default_font())
        msgbox.setWindowTitle("Open Houdini File")
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setText("Open the Houdini file?")
        msgbox.setInformativeText("It opens in a new Houdini session.")
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            ihda_system.IHDASystem.open_hipfile_using_thread(hip_filepath)

    def _slot_local_ai_models(self) -> None:
        self.bindings.preference.show()
        self.bindings.preference.open_local_models()

    def _slot_preference(self) -> None:
        if self.bindings.preference.is_ffmpeg_valid:
            self.bindings.video_player.ffmpeg_dirpath = (
                self.bindings.preference.ffmpeg_dirpath
            )
        self.bindings.details.close()
        self.bindings.session.context = LibraryContext.from_preference(
            self.bindings.preference, self.bindings.session.user
        )
        self.bindings.session.repository = self.bindings.services.repository(
            self.bindings.session.context
        )
        self.bindings.browser.change_repository(self.bindings.session.repository)
        self.bindings.details.change_repository(
            self.bindings.session.repository,
            self.bindings.session.context,
            vocabulary=self.bindings.session.tag_vocabulary,
        )
        if self.bindings.session.context is not None:
            self.bindings.session.context.asset_root.mkdir(parents=True, exist_ok=True)
            # DB 파일이 존재하지 않는다면 생성
            db_filepath = self.bindings.queries.db_filepath
            assert isinstance(db_filepath, pathlib.Path)
            if not db_filepath.exists():
                db_api = self.bindings.services.open_database(db_filepath)
                db_api.create_tables()
                is_done = db_api.insert_users(
                    user_id=self.bindings.session.user,
                    email=f"{self.bindings.session.user}@local",
                )
                if not is_done:
                    log_handler.LogHandler.log_msg(
                        method=logging.error, msg="user creation failed"
                    )
                    return
                msgbox = QtWidgets.QMessageBox(self.bindings.parent)
                msgbox.setFont(self.get_default_font())
                msgbox.setIcon(QtWidgets.QMessageBox.Icon.Information)
                msgbox.setWindowTitle("Individual iHDA")
                msgbox.setText("Please restart the app.")
                _ = msgbox.exec()
        # app properties
        font_size, font_style = self.get_font_properties(
            keys.Name.PreferenceUI.spb_view_font_size,
            keys.Name.PreferenceUI.cmb_view_font_style,
        )
        self.bindings.models.list_model.set_font(style=font_style, size=font_size)
        self.bindings.models.table_model.set_font(style=font_style, size=font_size)
        self.bindings.models.history_model.set_font(style=font_style, size=font_size)
        self.bindings.models.category_model.set_font(style=font_style, size=font_size)
        self.bindings.models.record_model.set_font(style=font_style, size=font_size)
        self.bindings.models.inside_model.set_font(style=font_style, size=font_size)
        treeview_icon_size = self.get_treeview_properties()
        self._set_tree_view_item_icon_size(treeview_icon_size)
        self.set_view_item_icon_size(self.bindings.ui.doubleSpinBox__zoom.value())
        # text view의 font size, style 적용
        note_font = self.get_font_properties(
            keys.Name.PreferenceUI.spb_note_font_size,
            keys.Name.PreferenceUI.cmb_note_font_style,
        )
        self._set_font_properties(self.bindings.ui.textEdit__note, note_font)
        self._set_font_properties(self.bindings.ui.textBrowser__note_preview, note_font)
        self._set_font_properties(
            self.bindings.ui.textEdit__tag,
            self.get_font_properties(
                keys.Name.PreferenceUI.spb_tags_font_size,
                keys.Name.PreferenceUI.cmb_tags_font_style,
            ),
        )
        self._set_font_properties(
            self.bindings.ui.textBrowser__debug,
            self.get_font_properties(
                keys.Name.PreferenceUI.spb_debug_font_size,
                keys.Name.PreferenceUI.cmb_debug_font_style,
            ),
        )
        # padding 적용
        self._set_view_padding(self.bindings.ui.doubleSpinBox__zoom.value())
        # main icon size
        self._set_main_default_icon_size()
        self.bindings.browser.refresh()

    def _set_main_default_icon_size(self) -> None:
        icon_size = keys.UISetting.dft_icon_size
        properties_data = self.bindings.preference.get_properties_data()
        if properties_data is not None:
            if keys.Name.PreferenceUI.spb_main_icon_size in properties_data:
                icon_size = properties_data.get(
                    keys.Name.PreferenceUI.spb_main_icon_size, icon_size
                )
        if host.IS_HOUDINI:
            icon_size = houdini_api.HoudiniAPI.scaled_size(int(icon_size))
        self.bindings.ui.toolBar.setIconSize(QtCore.QSize(icon_size, icon_size))
        for inst in self._icon_variables():
            qsize = QtCore.QSize(icon_size, icon_size)
            inst.setIconSize(qsize)

    def _icon_variables(self) -> list[QtWidgets.QAbstractButton]:
        lst: list[QtWidgets.QAbstractButton] = list(
            self.bindings.ui.centralwidget.findChildren(QtWidgets.QCheckBox)
        )
        lst.extend(self.bindings.ui.centralwidget.findChildren(QtWidgets.QPushButton))
        lst.extend(self.bindings.video_player.findChildren(QtWidgets.QPushButton))
        lst.extend(self.bindings.web_view.findChildren(QtWidgets.QPushButton))
        lst.extend(self.bindings.preference.findChildren(QtWidgets.QToolButton))
        lst.extend(self.bindings.rename_dialog.findChildren(QtWidgets.QPushButton))
        lst.extend(self.bindings.video_info.findChildren(QtWidgets.QPushButton))
        return lst

    def _set_is_ready(self) -> None:
        self.bindings.status.ready = False
        if (
            self.bindings.session.context is not None
            and self.bindings.session.context.db_filepath.exists()
        ):
            self.bindings.status.ready = True
            self.bindings.ui.centralwidget.setEnabled(True)
            self.bindings.ui.toolBar.setEnabled(True)

    @staticmethod
    def change_org_node_name(parent_node: Any = None, node_name: Any = None) -> None:
        for child in parent_node.children():
            if child.name() == node_name:
                child.setName(child.name() + "_", unique_name=True)

    def _slot_zoomin(self) -> None:
        zoom_val = (
            self.bindings.ui.doubleSpinBox__zoom.value()
            + keys.UISetting.interval_zoom_value
        )
        if zoom_val > keys.UISetting.max_zoom_value:
            zoom_val = keys.UISetting.max_zoom_value
        self.bindings.ui.doubleSpinBox__zoom.setValue(zoom_val)

    def _slot_zoomout(self) -> None:
        zoom_val = (
            self.bindings.ui.doubleSpinBox__zoom.value()
            - keys.UISetting.interval_zoom_value
        )
        if zoom_val < keys.UISetting.min_zoom_value:
            zoom_val = keys.UISetting.min_zoom_value
        self.bindings.ui.doubleSpinBox__zoom.setValue(zoom_val)

    def _slot_zoom_value(self, zoom_val: float) -> None:
        self.set_view_item_icon_size(zoom_val)
        log_handler.LogHandler.log_msg(
            method=logging.info, msg=f"zoom value: {zoom_val} %"
        )

    def _set_tree_view_item_icon_size(self, val: Any) -> None:
        # treeview는 zoom 영향이 없도록. 이것은 preference에서만 조절 할 수 있다.
        self.bindings.models.category_model.set_icon_size(val)
        self.bindings.models.record_model.set_icon_size(val)
        self.bindings.models.inside_model.set_icon_size(val)
        self.bindings.views.category.expandAll()
        self.bindings.views.record.expandAll()
        self.bindings.views.inside.expandAll()

    def _set_view_padding(self, val: Any) -> None:
        tableview_icon_size, tableview_thumb_size = self.get_tableview_properties(val)
        # get padding
        pad_listview = self.get_padding_properties(
            keys.UISetting.padding_listview, keys.Name.PreferenceUI.pad_listview
        )
        pad_tableview = self.get_padding_properties(
            keys.UISetting.padding_tableview, keys.Name.PreferenceUI.pad_tableview
        )
        pad_history = self.get_padding_properties(
            keys.UISetting.padding_history, keys.Name.PreferenceUI.pad_history
        )
        pad_category = self.get_padding_properties(
            keys.UISetting.padding_category, keys.Name.PreferenceUI.pad_category
        )
        pad_record = self.get_padding_properties(
            keys.UISetting.padding_record, keys.Name.PreferenceUI.pad_record
        )
        pad_inside = self.get_padding_properties(
            keys.UISetting.padding_inside, keys.Name.PreferenceUI.pad_inside
        )
        # set padding
        self.bindings.models.list_model.set_padding(pad_listview)
        self.bindings.models.category_model.set_padding(pad_category)
        self.bindings.models.record_model.set_padding(pad_record)
        self.bindings.models.inside_model.set_padding(pad_inside)
        # inside model 구현 되면 추가
        # tableview
        if self.is_show_thumbnail:
            vertical_cell_size = tableview_thumb_size
        else:
            vertical_cell_size = tableview_icon_size
        self.bindings.views.assets_table.verticalHeader().setDefaultSectionSize(
            vertical_cell_size + pad_tableview
        )
        self.bindings.views.history.verticalHeader().setDefaultSectionSize(
            tableview_thumb_size + pad_history
        )

    def set_view_item_icon_size(self, val: Any) -> None:
        listview_icon_size, listview_thumb_size = self.get_listview_properties(val)
        tableview_icon_size, tableview_thumb_size = self.get_tableview_properties(val)
        self.bindings.models.list_model.set_icon_size(
            icon_size=listview_icon_size, thumb_size=listview_thumb_size
        )
        self.bindings.models.table_model.set_icon_size(
            icon_size=tableview_icon_size, thumb_size=tableview_thumb_size
        )
        self.bindings.models.history_model.set_icon_size(
            icon_size=tableview_icon_size, thumb_size=tableview_thumb_size
        )
        # tableview: the name cell shows two lines, so rows are never shorter than that
        from widgets.item_delegates import two_line_row_height

        minimum = two_line_row_height(self.bindings.views.assets_table.font())
        if self.is_show_thumbnail:
            vertical_cell_size = tableview_thumb_size
        else:
            vertical_cell_size = tableview_icon_size
        self.bindings.views.assets_table.verticalHeader().setDefaultSectionSize(
            max(int(vertical_cell_size), minimum)
        )
        self.bindings.views.history.verticalHeader().setDefaultSectionSize(
            max(int(tableview_thumb_size), minimum)
        )

    @property
    def is_show_thumbnail(self) -> bool:
        return self.bindings.ui.pushButton__thumbnail.isChecked()

    @staticmethod
    def _get_ratio_icon_size(val: Any) -> float:
        return val / 100.0

    @property
    def is_icon_mode(self) -> bool:
        return self.bindings.ui.pushButton__icon_mode.isChecked()

    @property
    def is_ihda_history_view(self) -> bool:
        return (
            self.bindings.ui.stackedWidget__whole.currentIndex()
            == self.bindings.ui.stackedWidget__whole.indexOf(
                self.bindings.ui.page__history
            )
        )

    def _slot_cfg_reset(self) -> None:
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.get_default_font())
        msgbox.setWindowTitle("iHDA Reset APP Properties")
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msgbox.setText("Do you want to reset app properties?")
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        reply = msgbox.exec()
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return
        self.bindings.status.reset_settings = True
        self.bindings.ui.centralwidget.setDisabled(True)
        self.bindings.ui.toolBar.setDisabled(True)
        self.bindings.ui.menubar.setDisabled(True)
        log_handler.LogHandler.log_msg(
            method=logging.debug, msg="initialized application properties"
        )
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.get_default_font())
        msgbox.setWindowTitle("iHDA Reset APP Properties")
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msgbox.setText("App property initialization is complete. Please start again.")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        _ = msgbox.exec()

    def _set_theme(self, theme: str = "Default") -> None:
        self.bindings.ui_settings.set_theme(theme=theme)

    def _slot_about(self) -> None:
        from libs import paths
        from widgets.about_dialog import AboutDialog

        houdini_version = (
            houdini_api.HoudiniAPI.current_houdini_version()
            if host.IS_HOUDINI
            else None
        )
        dialog = AboutDialog(
            self.bindings.parent,
            houdini_version=houdini_version,
            config_dir=paths.Paths.config_dirpath,
            open_url=ihda_system.IHDASystem.open_browser,
            open_folder=ihda_system.IHDASystem.open_folder,
        )
        dialog.exec()
        dialog.deleteLater()

    def _slot_help(self) -> None:
        from widgets.help_dialog import HelpDialog

        dialog = HelpDialog(
            self.bindings.parent, open_url=ihda_system.IHDASystem.open_browser
        )
        dialog.exec()
        dialog.deleteLater()

    def _slot_submit_bug_report(self) -> None:
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.get_default_font(font_size=15))
        msgbox.setWindowTitle("Submit Bug Report")
        msgbox.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msgbox.setText(
            '<a href="mailto:saelly55@gmail.com?Subject=[iHDA] Bug Report" style="color:red"'
            'target="_top">Send Bug Report</a><br>'
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msgbox.setDetailedText("Click the link to send an email.")
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec()

    def _slot_submit_feedback(self) -> None:
        msgbox = QtWidgets.QMessageBox(self.bindings.parent)
        msgbox.setFont(self.get_default_font(font_size=15))
        msgbox.setWindowTitle("Submit Feedback")
        msgbox.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msgbox.setText(
            '<a href="mailto:saelly55@gmail.com?Subject=[iHDA] Feedback" style="color:red"'
            'target="_top">Send Feedback</a><br>'
        )
        msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msgbox.setDetailedText("Click the link to send an email.")
        msgbox.resize(msgbox.sizeHint())
        _ = msgbox.exec()

    @staticmethod
    def _slot_donate() -> None:
        ihda_system.IHDASystem.open_browser(SUPPORT_URL)

    @staticmethod
    def _slot_download_ffmpeg_site() -> None:
        is_done = ihda_system.IHDASystem.open_browser(FFMPEG_DOWNLOAD_URL)
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
