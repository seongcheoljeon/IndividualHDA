"""Model binding on the panel GUI thread.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore

from libs import keys, log_handler
from libs.asset_contracts import AssetData, HistoryData
from libs.asset_store import AssetStore
from libs.model_columns import AssetColumn, HistoryColumn
from libs.qt_helpers import wildcard_expression
from model import (
    ihda_category_model,
    ihda_category_proxy_model,
    ihda_history_model,
    ihda_history_proxy_model,
    ihda_inside_model,
    ihda_inside_proxy_model,
    ihda_list_model,
    ihda_list_proxy_model,
    ihda_record_model,
    ihda_record_proxy_model,
    ihda_table_model,
    ihda_table_proxy_model,
)
from model.asset_notifications import QtAssetNotifications
from widgets.ui_tokens import (
    ASSET_TABLE_COLUMN_WIDTHS,
    HISTORY_TABLE_COLUMN_WIDTHS,
    INSIDE_TREE_COLUMN_WIDTHS,
    RECORD_TREE_COLUMN_WIDTHS,
)

if TYPE_CHECKING:
    from libs.ihda_icons import IHDAIcons
    from widgets.asset_browser.integration import AssetBrowserIntegration
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.ports import LibraryQueryPort, PresentationPort, SelectionPort
    from widgets.panel.state import PanelSessionState, PanelViews


@dataclass(frozen=True, slots=True)
class PanelModelBindingBindings:
    browser: AssetBrowserIntegration
    icons: IHDAIcons
    presentation: PresentationPort
    queries: LibraryQueryPort
    selection: SelectionPort
    session: PanelSessionState
    ui: MainWindowLayout
    views: PanelViews


class PanelModelBinding:
    bindings: PanelModelBindingBindings

    category_model: ihda_category_model.CategoryModel
    category_proxy_model: ihda_category_proxy_model.CategoryProxyModel
    history_model: ihda_history_model.HistoryModel
    history_proxy_model: ihda_history_proxy_model.HistoryProxyModel
    inside_model: ihda_inside_model.InsideModel
    inside_proxy_model: ihda_inside_proxy_model.InsideProxyModel
    record_model: ihda_record_model.RecordModel
    record_proxy_model: ihda_record_proxy_model.RecordProxyModel
    list_model: ihda_list_model.ListModel
    list_proxy_model: ihda_list_proxy_model.ListProxyModel
    table_model: ihda_table_model.TableModel
    table_proxy_model: ihda_table_proxy_model.TableProxyModel

    def __init__(self) -> None:
        self.assets = AssetStore()

    @QtCore.Slot(int)
    def _thumbnail_ready(self, asset_id: int) -> None:
        row = self.assets.id_rows.get(asset_id)
        if row is not None:
            for model in (self.list_model, self.table_model):
                model.dataChanged.emit(
                    model.index(row, 0),
                    model.index(row, model.columnCount() - 1),
                    [QtCore.Qt.ItemDataRole.DecorationRole],
                )

    @QtCore.Slot(int)
    def _history_thumbnail_ready(self, history_id: int) -> None:
        # Repaint visible cells only; avoid rebuilding filters on image completion.
        self.bindings.views.history.viewport().update()

    def _init_set_ihda_category_model(self) -> None:
        font_size, font_style = self.bindings.presentation.get_font_properties(
            keys.Name.PreferenceUI.spb_view_font_size,
            keys.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size = self.bindings.presentation.get_treeview_properties()
        padding = self.bindings.presentation.get_padding_properties(
            keys.UISetting.padding_category, keys.Name.PreferenceUI.pad_category
        )
        self.bindings.ui.stackedWidget__category.setCurrentIndex(0)
        # tree model
        self.category_model = ihda_category_model.CategoryModel(
            data=self.bindings.queries.get_hda_category(
                user_id=self.bindings.session.user,
                db_filepath=self.bindings.queries.db_filepath,
            ),
            pixmap_cate_data=self.bindings.icons.pixmap_cate_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            padding=padding,
        )
        self.category_proxy_model = ihda_category_proxy_model.CategoryProxyModel()
        self.category_proxy_model.setSourceModel(self.category_model)
        self.bindings.views.category.setModel(self.category_proxy_model)
        self.bindings.views.category.expandAll()

    def _init_set_ihda_list_model(self) -> None:
        font_size, font_style = self.bindings.presentation.get_font_properties(
            keys.Name.PreferenceUI.spb_view_font_size,
            keys.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size, thumb_size = self.bindings.presentation.get_listview_properties(
            self.bindings.ui.doubleSpinBox__zoom.value()
        )
        padding = self.bindings.presentation.get_padding_properties(
            keys.UISetting.padding_listview, keys.Name.PreferenceUI.pad_listview
        )
        # ihda list model
        self.list_model = ihda_list_model.ListModel(
            items=self.assets.rows,
            pixmap_ihda_data=self.bindings.icons.pixmap_ihda_data,
            pixmap_thumb_data=self.bindings.icons.pixmap_thumbnail_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            thumb_size=thumb_size,
            padding=padding,
        )
        # proxy ihda list model
        self.list_proxy_model = ihda_list_proxy_model.ListProxyModel(
            search_target_idx=self.bindings.ui.comboBox__search_type.currentIndex()
        )
        self.list_proxy_model.setSourceModel(self.list_model)
        self.bindings.views.assets_list.setModel(self.list_proxy_model)
        self.bindings.presentation.resizing_listview()

    def _init_set_ihda_table_model(self) -> None:
        font_size, font_style = self.bindings.presentation.get_font_properties(
            keys.Name.PreferenceUI.spb_view_font_size,
            keys.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size, thumb_size = self.bindings.presentation.get_tableview_properties(
            self.bindings.ui.doubleSpinBox__zoom.value()
        )
        padding = self.bindings.presentation.get_padding_properties(
            keys.UISetting.padding_tableview, keys.Name.PreferenceUI.pad_tableview
        )
        # table model
        self.table_model = ihda_table_model.TableModel(
            items=self.assets.rows,
            pixmap_ihda_data=self.bindings.icons.pixmap_ihda_data,
            pixmap_thumb_data=self.bindings.icons.pixmap_thumbnail_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            thumb_size=thumb_size,
        )
        # proxy table model
        self.table_proxy_model = ihda_table_proxy_model.TableProxyModel(
            search_target_idx=self.bindings.ui.comboBox__search_type.currentIndex()
        )
        self.table_proxy_model.setSourceModel(self.table_model)
        self.bindings.views.assets_table.setModel(self.table_proxy_model)
        for column, width in ASSET_TABLE_COLUMN_WIDTHS:
            self.bindings.views.assets_table.setColumnWidth(column, width)
        self.bindings.views.assets_table.resizeColumnToContents(AssetColumn.CREATED)
        self.bindings.views.assets_table.resizeColumnToContents(AssetColumn.MODIFIED)
        self.bindings.views.assets_table.resizeColumnToContents(AssetColumn.HOUDINI)
        self.bindings.views.assets_table.resizeColumnToContents(AssetColumn.LICENSE)
        if self.bindings.presentation.is_show_thumbnail:
            self.bindings.views.assets_table.verticalHeader().setDefaultSectionSize(
                thumb_size + padding
            )
        else:
            self.bindings.views.assets_table.verticalHeader().setDefaultSectionSize(
                icon_size + padding
            )

    def _init_set_ihda_history_model(self) -> None:
        font_size, font_style = self.bindings.presentation.get_font_properties(
            keys.Name.PreferenceUI.spb_view_font_size,
            keys.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size, thumb_size = self.bindings.presentation.get_tableview_properties(
            self.bindings.ui.doubleSpinBox__zoom.value()
        )
        padding = self.bindings.presentation.get_padding_properties(
            keys.UISetting.padding_history, keys.Name.PreferenceUI.pad_history
        )
        # ihda history model
        get_data = self.bindings.queries.get_hda_hist_data(
            user_id=self.bindings.session.user,
            db_filepath=self.bindings.queries.db_filepath,
        )
        self.history_model = ihda_history_model.HistoryModel(
            items=get_data,
            pixmap_ihda_data=self.bindings.icons.pixmap_ihda_data,
            pixmap_cate_data=self.bindings.icons.pixmap_cate_data,
            pixmap_hist_thumb_data=self.bindings.icons.pixmap_hist_thumbnail_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            thumb_size=thumb_size,
        )
        # proxy history model
        self.history_proxy_model = ihda_history_proxy_model.HistoryProxyModel(
            search_target_idx=self.bindings.ui.comboBox__search_field_hist.currentIndex()
        )
        self.history_proxy_model.setSourceModel(self.history_model)
        self.bindings.views.history.setModel(self.history_proxy_model)
        self.bindings.selection.init_set_hist_ihda_combobox()
        self.bindings.ui.label__hist_cnt.setText(
            str(self.history_proxy_model.rowCount())
        )
        for column, width in HISTORY_TABLE_COLUMN_WIDTHS:
            self.bindings.views.history.setColumnWidth(column, width)
        self.bindings.views.history.resizeColumnToContents(HistoryColumn.CATEGORY)
        self.bindings.views.history.resizeColumnToContents(HistoryColumn.COMMENT)
        self.bindings.views.history.resizeColumnToContents(HistoryColumn.HOUDINI)
        self.bindings.views.history.resizeColumnToContents(10)
        self.bindings.views.history.resizeColumnToContents(11)
        self.bindings.views.history.verticalHeader().setDefaultSectionSize(
            thumb_size + padding
        )

    def _init_set_ihda_record_model(self) -> None:
        font_size, font_style = self.bindings.presentation.get_font_properties(
            keys.Name.PreferenceUI.spb_view_font_size,
            keys.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size = self.bindings.presentation.get_treeview_properties()
        padding = self.bindings.presentation.get_padding_properties(
            keys.UISetting.padding_record, keys.Name.PreferenceUI.pad_record
        )
        # tree model
        self.record_model = ihda_record_model.RecordModel(
            data=self.bindings.queries.get_hda_loc_record_data(
                self.bindings.queries.db_filepath
            ),
            pixmap_cate_data=self.bindings.icons.pixmap_cate_data,
            pixmap_ihda_data=self.bindings.icons.pixmap_ihda_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            padding=padding,
        )
        self.record_proxy_model = ihda_record_proxy_model.RecordProxyModel()
        self.record_proxy_model.setSourceModel(self.record_model)
        self.bindings.views.record.setModel(self.record_proxy_model)
        self.bindings.views.record.expandAll()
        # self._ihda_record_view.setColumnWidth(0, 100)
        for column, width in RECORD_TREE_COLUMN_WIDTHS:
            self.bindings.views.record.header().resizeSection(column, width)
        self.bindings.ui.label__loc_record_count.setText(
            str(self.record_proxy_model.get_row_count())
        )

    def _init_set_ihda_inside_model(self) -> None:
        font_size, font_style = self.bindings.presentation.get_font_properties(
            keys.Name.PreferenceUI.spb_view_font_size,
            keys.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size = self.bindings.presentation.get_treeview_properties()
        padding = self.bindings.presentation.get_padding_properties(
            keys.UISetting.padding_inside, keys.Name.PreferenceUI.pad_inside
        )
        self.inside_model = ihda_inside_model.InsideModel(
            data={},
            pixmap_cate_data=self.bindings.icons.pixmap_cate_data,
            pixmap_ihda_data=self.bindings.icons.pixmap_ihda_data,
            inst_ihda_icon=self.bindings.icons,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            padding=padding,
        )
        self.inside_proxy_model = ihda_inside_proxy_model.InsideProxyModel()
        self.inside_proxy_model.setSourceModel(self.inside_model)
        self.bindings.views.inside.setModel(self.inside_proxy_model)
        self.bindings.views.inside.expandAll()
        for column, width in INSIDE_TREE_COLUMN_WIDTHS:
            self.bindings.views.inside.header().resizeSection(column, width)

    def insert_ihda_history_data_model(
        self,
        data: HistoryData,
        hist_id: int | None = None,
        tags: Sequence[str] | None = None,
        comment: str | None = None,
    ) -> None:
        if hist_id is None:
            raise ValueError("A history ID is required")
        dat = replace(
            data,
            hist_id=hist_id,
            tags=tuple(tags or ()),
            comment=comment if comment is not None else data.comment,
        )
        self.history_model.append_item(dat)
        self.bindings.ui.label__hist_cnt.setText(
            str(self.history_proxy_model.rowCount())
        )

    def insert_ihda_data_model(self, data: AssetData) -> None:
        self.assets.observe(QtAssetNotifications(self.list_model, self.table_model))
        self.assets.insert(data)

    def update_item_row_data(
        self, row: int | None = None, row_data: AssetData | None = None
    ) -> None:
        if row is not None and row_data is not None:
            self.assets.observe(QtAssetNotifications(self.list_model, self.table_model))
            self.assets.update(row, row_data)

    @QtCore.Slot(str)
    def search_filter_regexp_hist_hda_item(self, text: str) -> None:
        if self.bindings.ui.checkBox__casesensitive_hda_hist.isChecked():
            casesensitivity = QtCore.Qt.CaseSensitivity.CaseSensitive
        else:
            casesensitivity = QtCore.Qt.CaseSensitivity.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self.history_proxy_model.setFilterRegularExpression(regexp)
        self.bindings.ui.label__hist_cnt.setText(
            str(self.history_proxy_model.rowCount())
        )

    def _asset_search_failed_message(self, message: str) -> None:
        log_handler.LogHandler.log_msg(method=logging.error, msg=message)

    def refresh_asset_search(self) -> None:
        """Re-run the current query after edits so the ID filter is not stale."""
        if self.bindings.ui.lineEdit__search_hda.text().strip():
            self.bindings.browser.refresh()

    @QtCore.Slot(str)
    def search_filter_regexp_hda_cate(self, text: str) -> None:
        if self.bindings.ui.checkBox__casesensitive_cate.isChecked():
            casesensitivity = QtCore.Qt.CaseSensitivity.CaseSensitive
        else:
            casesensitivity = QtCore.Qt.CaseSensitivity.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self.category_proxy_model.setFilterRegularExpression(regexp)
        self.bindings.ui.label__cate_count.setText(str(self.get_category_count()))
        self.bindings.views.category.expandAll()

    @QtCore.Slot(str)
    def _search_filter_regexp_hda_record(self, text: str) -> None:
        # 대소문자 구별하지 않음.
        casesensitivity = QtCore.Qt.CaseSensitivity.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self.record_proxy_model.setFilterRegularExpression(regexp)
        self.bindings.ui.label__loc_record_count.setText(
            str(self.record_proxy_model.get_row_count())
        )
        self.bindings.views.record.expandAll()

    @QtCore.Slot(str)
    def _search_filter_regexp_hda_inside(self, text: str) -> None:
        # 대소문자 구별하지 않음.
        casesensitivity = QtCore.Qt.CaseSensitivity.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self.inside_proxy_model.setFilterRegularExpression(regexp)
        self.bindings.ui.label__found_hda_inside_hipfile_count.setText(
            str(self.inside_proxy_model.get_row_count())
        )
        self.bindings.views.inside.expandAll()

    def _add_pixmap_category(self, category: str | None = None) -> None:
        self.bindings.icons.add_pixmap_cate_data(category=category)

    def add_pixmap_ihda(
        self, hkey_id: int | None = None, icon_lst: list[str] | None = None
    ) -> None:
        self.bindings.icons.add_pixmap_ihda_data(hkey_id=hkey_id, icon_lst=icon_lst)

    def add_pixmap_thumbnail(
        self, hkey_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        if hkey_id is None or thumb_filepath is None:
            return
        assert isinstance(thumb_filepath, pathlib.Path)
        self.bindings.icons.add_pixmap_thumbnail_data(
            hkey_id=hkey_id, thumb_filepath=thumb_filepath
        )

    def add_pixmap_hist_thumbnail(
        self, hist_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        if hist_id is None or thumb_filepath is None:
            return
        assert isinstance(thumb_filepath, pathlib.Path)
        self.bindings.icons.add_pixmap_hist_thumbnail_data(
            hist_id=hist_id, thumb_filepath=thumb_filepath
        )

    def update_pixmap_thumbnail(
        self, hkey_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        if hkey_id is None or thumb_filepath is None:
            return
        assert isinstance(thumb_filepath, pathlib.Path)
        self.bindings.icons.update_pixmap_thumbnail_data(
            hkey_id=hkey_id, thumb_filepath=thumb_filepath
        )

    def update_pixmap_hist_thumbnail(
        self, hist_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        if hist_id is None or thumb_filepath is None:
            return
        assert isinstance(thumb_filepath, pathlib.Path)
        self.bindings.icons.update_pixmap_hist_thumbnail_data(
            hist_id=hist_id, thumb_filepath=thumb_filepath
        )

    def _remove_pixmap_category(self, category: str | None = None) -> None:
        self.bindings.icons.remove_pixmap_cate_data(category=category)

    def remove_pixmap_ihda(self, hkey_id: int | None = None) -> None:
        self.bindings.icons.remove_pixmap_ihda_data(hkey_id=hkey_id)

    def remove_pixmap_thumbnail(self, hkey_id: int | None = None) -> None:
        self.bindings.icons.remove_pixmap_thumbnail_data(hkey_id=hkey_id)

    def remove_pixmap_hist_thumbnail(self, hist_id: int | None = None) -> None:
        self.bindings.icons.remove_pixmap_hist_thumbnail_data(hist_id=hist_id)

    def add_record_item(self, data: Any = None) -> None:
        self.record_model.insert_record_data(data=data)
        self.record_model.reload()
        self.bindings.views.record.expandAll()

    def add_category_item(self, category: str | None = None) -> None:
        self._add_pixmap_category(category=category)
        self.category_model.add_item(data={category: None})
        self.category_model.reload()
        self.bindings.views.category.expandAll()

    def remove_category_item(
        self, category: str | None = None, category_list: Any = None
    ) -> None:
        if category_list is None:
            self.category_model.remove_item(category=category)
            self._remove_pixmap_category(category=category)
            self.category_model.reload()
        else:
            if category not in category_list:
                self.category_model.remove_item(category=category)
                self._remove_pixmap_category(category=category)
                self.category_model.reload()
                self.bindings.views.category.expandAll()

    def get_category_count(self) -> int:
        return self.category_proxy_model.rowCount(
            self.category_proxy_model.index(0, 0, QtCore.QModelIndex())
        )

    def remove_hda_data(self, item_row: int | None = None) -> None:
        if item_row is not None:
            self.assets.observe(QtAssetNotifications(self.list_model, self.table_model))
            self.assets.remove(item_row)
