"""Model binding on the panel GUI thread.

Uses the shared panel protected state; no independent QObject ownership.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from PySide6 import QtCore

import public
from libs import log_handler, sqlite3_db_api
from libs.domain import AssetData
from libs.library_explorer import search_asset_ids
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


class ModelBindingMixin:
    @QtCore.Slot(int)
    def _thumbnail_ready(self, asset_id: int) -> None:
        row = self._assets.id_rows.get(asset_id)
        if row is not None:
            for model in (self._ihda_list_model, self._ihda_table_model):
                model.dataChanged.emit(
                    model.index(row, 0),
                    model.index(row, model.columnCount() - 1),
                    [QtCore.Qt.DecorationRole],
                )

    @QtCore.Slot(int)
    def _history_thumbnail_ready(self, history_id: int) -> None:
        # Repaint visible cells only; avoid rebuilding filters on image completion.
        self._ihda_history_view.viewport().update()

    def _init_set_ihda_category_model(self) -> None:
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size,
            public.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size = self._get_treeview_properties()
        padding = self._get_padding_properties(
            public.UISetting.padding_category, public.Name.PreferenceUI.pad_category
        )
        self.stackedWidget__category.setCurrentIndex(0)
        # tree model
        self._ihda_category_model = ihda_category_model.CategoryModel(
            data=self._get_hda_category(
                user_id=self._user, db_filepath=self._db_filepath
            ),
            pixmap_cate_data=self._ihda_icons.pixmap_cate_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            padding=padding,
        )
        self._ihda_category_proxy_model = ihda_category_proxy_model.CategoryProxyModel()
        self._ihda_category_proxy_model.setSourceModel(self._ihda_category_model)
        self._ihda_category_view.setModel(self._ihda_category_proxy_model)
        self._ihda_category_view.expandAll()

    def _init_set_ihda_list_model(self) -> None:
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size,
            public.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size, thumb_size = self._get_listview_properties(
            self.doubleSpinBox__zoom.value()
        )
        padding = self._get_padding_properties(
            public.UISetting.padding_listview, public.Name.PreferenceUI.pad_listview
        )
        # ihda list model
        self._ihda_list_model = ihda_list_model.ListModel(
            items=self._assets.rows,
            pixmap_ihda_data=self._ihda_icons.pixmap_ihda_data,
            pixmap_thumb_data=self._ihda_icons.pixmap_thumbnail_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            thumb_size=thumb_size,
            padding=padding,
        )
        # proxy ihda list model
        self._ihda_list_proxy_model = ihda_list_proxy_model.ListProxyModel(
            search_target_idx=self.comboBox__search_type.currentIndex()
        )
        self._ihda_list_proxy_model.setSourceModel(self._ihda_list_model)
        self._ihda_list_view.setModel(self._ihda_list_proxy_model)
        self._resizing_listview()

    def _init_set_ihda_table_model(self) -> None:
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size,
            public.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size, thumb_size = self._get_tableview_properties(
            self.doubleSpinBox__zoom.value()
        )
        padding = self._get_padding_properties(
            public.UISetting.padding_tableview, public.Name.PreferenceUI.pad_tableview
        )
        # table model
        self._ihda_table_model = ihda_table_model.TableModel(
            items=self._assets.rows,
            pixmap_ihda_data=self._ihda_icons.pixmap_ihda_data,
            pixmap_thumb_data=self._ihda_icons.pixmap_thumbnail_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            thumb_size=thumb_size,
        )
        # proxy table model
        self._ihda_table_proxy_model = ihda_table_proxy_model.TableProxyModel(
            search_target_idx=self.comboBox__search_type.currentIndex()
        )
        self._ihda_table_proxy_model.setSourceModel(self._ihda_table_model)
        self._ihda_table_view.setModel(self._ihda_table_proxy_model)
        self._ihda_table_view.setColumnWidth(0, 250)
        self._ihda_table_view.setColumnWidth(1, 130)
        self._ihda_table_view.setColumnWidth(2, 10)
        self._ihda_table_view.setColumnWidth(3, 60)
        self._ihda_table_view.setColumnWidth(4, 50)
        self._ihda_table_view.resizeColumnToContents(5)
        self._ihda_table_view.resizeColumnToContents(6)
        self._ihda_table_view.resizeColumnToContents(7)
        self._ihda_table_view.resizeColumnToContents(8)
        if self._is_show_thumbnail:
            self._ihda_table_view.verticalHeader().setDefaultSectionSize(
                thumb_size + padding
            )
        else:
            self._ihda_table_view.verticalHeader().setDefaultSectionSize(
                icon_size + padding
            )

    def _init_set_ihda_history_model(self) -> None:
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size,
            public.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size, thumb_size = self._get_tableview_properties(
            self.doubleSpinBox__zoom.value()
        )
        padding = self._get_padding_properties(
            public.UISetting.padding_history, public.Name.PreferenceUI.pad_history
        )
        # ihda history model
        get_data = self._get_hda_hist_data(
            user_id=self._user, db_filepath=self._db_filepath
        )
        self._ihda_history_model = ihda_history_model.HistoryModel(
            items=get_data,
            pixmap_ihda_data=self._ihda_icons.pixmap_ihda_data,
            pixmap_cate_data=self._ihda_icons.pixmap_cate_data,
            pixmap_hist_thumb_data=self._ihda_icons.pixmap_hist_thumbnail_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            thumb_size=thumb_size,
        )
        # proxy history model
        self._ihda_history_proxy_model = ihda_history_proxy_model.HistoryProxyModel(
            search_target_idx=self.comboBox__search_field_hist.currentIndex()
        )
        self._ihda_history_proxy_model.setSourceModel(self._ihda_history_model)
        self._ihda_history_view.setModel(self._ihda_history_proxy_model)
        self._init_set_hist_ihda_combobox()
        self.label__hist_cnt.setText(str(self._ihda_history_proxy_model.rowCount()))
        self._ihda_history_view.setColumnWidth(0, 80)
        self._ihda_history_view.setColumnWidth(1, 255)
        self._ihda_history_view.setColumnWidth(2, 185)
        self._ihda_history_view.resizeColumnToContents(3)
        self._ihda_history_view.resizeColumnToContents(4)
        self._ihda_history_view.setColumnWidth(5, 80)
        self._ihda_history_view.setColumnWidth(7, 150)
        self._ihda_history_view.resizeColumnToContents(9)
        self._ihda_history_view.resizeColumnToContents(10)
        self._ihda_history_view.resizeColumnToContents(11)
        self._ihda_history_view.verticalHeader().setDefaultSectionSize(
            thumb_size + padding
        )

    def _init_set_ihda_record_model(self) -> None:
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size,
            public.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size = self._get_treeview_properties()
        padding = self._get_padding_properties(
            public.UISetting.padding_record, public.Name.PreferenceUI.pad_record
        )
        # tree model
        self._ihda_record_model = ihda_record_model.RecordModel(
            data=self._get_hda_loc_record_data(self._db_filepath),
            pixmap_cate_data=self._ihda_icons.pixmap_cate_data,
            pixmap_ihda_data=self._ihda_icons.pixmap_ihda_data,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            padding=padding,
        )
        self._ihda_record_proxy_model = ihda_record_proxy_model.RecordProxyModel()
        self._ihda_record_proxy_model.setSourceModel(self._ihda_record_model)
        self._ihda_record_view.setModel(self._ihda_record_proxy_model)
        self._ihda_record_view.expandAll()
        # self._ihda_record_view.setColumnWidth(0, 100)
        self._ihda_record_view.header().resizeSection(0, 350)
        self._ihda_record_view.header().resizeSection(1, 100)
        self._ihda_record_view.header().resizeSection(2, 100)
        self._ihda_record_view.header().resizeSection(3, 50)
        self._ihda_record_view.header().resizeSection(6, 100)
        self._ihda_record_view.header().resizeSection(7, 100)
        self._ihda_record_view.header().resizeSection(8, 100)
        self._ihda_record_view.header().resizeSection(9, 100)
        self._ihda_record_view.header().resizeSection(10, 100)
        self._ihda_record_view.header().resizeSection(11, 50)
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
        )

    def _init_set_ihda_inside_model(self) -> None:
        font_size, font_style = self._get_font_properties(
            public.Name.PreferenceUI.spb_view_font_size,
            public.Name.PreferenceUI.cmb_view_font_style,
        )
        icon_size = self._get_treeview_properties()
        padding = self._get_padding_properties(
            public.UISetting.padding_inside, public.Name.PreferenceUI.pad_inside
        )
        self._ihda_inside_model = ihda_inside_model.InsideModel(
            data={},
            pixmap_cate_data=self._ihda_icons.pixmap_cate_data,
            pixmap_ihda_data=self._ihda_icons.pixmap_ihda_data,
            inst_ihda_icon=self._ihda_icons,
            font_size=font_size,
            font_style=font_style,
            icon_size=icon_size,
            padding=padding,
        )
        self._ihda_inside_proxy_model = ihda_inside_proxy_model.InsideProxyModel()
        self._ihda_inside_proxy_model.setSourceModel(self._ihda_inside_model)
        self._ihda_inside_view.setModel(self._ihda_inside_proxy_model)
        self._ihda_inside_view.expandAll()
        self._ihda_inside_view.header().resizeSection(0, 350)
        self._ihda_inside_view.header().resizeSection(1, 100)
        self._ihda_inside_view.header().resizeSection(2, 120)
        self._ihda_inside_view.header().resizeSection(3, 50)

    def _insert_ihda_history_data_model(
        self,
        data: Any = None,
        hist_id: int | None = None,
        tags: list[str] | None = None,
        comment: str | None = None,
    ) -> None:
        key_lst = sqlite3_db_api.SQLite3DatabaseAPI.hda_history_key_lst()
        index_hist_id = key_lst.index(public.Key.History.hist_id)
        index_tags = key_lst.index(public.Key.History.tags)
        data.insert(index_hist_id, hist_id)
        data.insert(index_tags, tags)
        assert len(key_lst) == len(data)
        dat = dict(zip(key_lst, data, strict=False))
        if comment is not None:
            dat[public.Key.History.comment] = comment
        self._ihda_history_model.append_item(dat)
        self.label__hist_cnt.setText(str(self._ihda_history_proxy_model.rowCount()))

    def _insert_ihda_data_model(self, data: AssetData) -> None:
        self._assets.observe(
            QtAssetNotifications(self._ihda_list_model, self._ihda_table_model)
        )
        self._assets.insert(data)

    def _update_item_row_data(
        self, row: int | None = None, row_data: AssetData | None = None
    ) -> None:
        if row is not None and row_data is not None:
            self._assets.observe(
                QtAssetNotifications(self._ihda_list_model, self._ihda_table_model)
            )
            self._assets.update(row, row_data)

    @QtCore.Slot(str)
    def _search_filter_regexp_hist_hda_item(self, text: str) -> None:
        if self.checkBox__casesensitive_hda_hist.isChecked():
            casesensitivity = QtCore.Qt.CaseSensitive
        else:
            casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self._ihda_history_proxy_model.setFilterRegularExpression(regexp)
        self.label__hist_cnt.setText(str(self._ihda_history_proxy_model.rowCount()))

    @QtCore.Slot(str)
    def _search_filter_regexp_hda_item(self, text: str) -> None:
        text = text.strip()
        case_sensitive = self.checkBox__casesensitive_hda.isChecked()
        database = self._db_filepath
        proxies = (self._ihda_list_proxy_model, self._ihda_table_proxy_model)
        if not text or database is None or not database.is_file():
            # Empty query: purely local, no job. Regex "" accepts every row.
            self._asset_search.cancel()
            casesensitivity = (
                QtCore.Qt.CaseSensitive if case_sensitive else QtCore.Qt.CaseInsensitive
            )
            regexp = wildcard_expression(text, casesensitivity)
            for proxy in proxies:
                proxy.set_id_filter(None)
                proxy.setFilterRegularExpression(regexp)
            self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))
            return
        field = self.comboBox__search_type.currentText() or "All"

        def search(query: str, cancel: Any) -> list[int]:
            return search_asset_ids(
                database,
                query,
                field=field,
                case_sensitive=case_sensitive,
                cancel=cancel,
            )

        self._asset_search.submit(text, search)

    @QtCore.Slot(object)
    def _apply_search_ids(self, ids: object) -> None:
        for proxy in (self._ihda_list_proxy_model, self._ihda_table_proxy_model):
            proxy.setFilterRegularExpression("")
            proxy.set_id_filter(frozenset(ids) if ids is not None else None)
        self.label__hda_count.setText(str(self._ihda_list_proxy_model.rowCount()))

    @QtCore.Slot(object)
    def _asset_search_failed(self, error: object) -> None:
        log_handler.LogHandler.log_msg(
            method=logging.error, msg=f"search failed: {error}"
        )

    def _refresh_asset_search(self) -> None:
        """Re-run the current query after local edits so the id filter is not stale."""
        if self.lineEdit__search_hda.text().strip():
            self._search_filter_regexp_hda_item(self.lineEdit__search_hda.text())

    @QtCore.Slot(str)
    def _search_filter_regexp_hda_cate(self, text: str) -> None:
        if self.checkBox__casesensitive_cate.isChecked():
            casesensitivity = QtCore.Qt.CaseSensitive
        else:
            casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self._ihda_category_proxy_model.setFilterRegularExpression(regexp)
        self.label__cate_count.setText(str(self._get_category_count()))
        self._ihda_category_view.expandAll()

    @QtCore.Slot(str)
    def _search_filter_regexp_hda_record(self, text: str) -> None:
        # 대소문자 구별하지 않음.
        casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self._ihda_record_proxy_model.setFilterRegularExpression(regexp)
        self.label__loc_record_count.setText(
            str(self._ihda_record_proxy_model.get_row_count())
        )
        self._ihda_record_view.expandAll()

    @QtCore.Slot(str)
    def _search_filter_regexp_hda_inside(self, text: str) -> None:
        # 대소문자 구별하지 않음.
        casesensitivity = QtCore.Qt.CaseInsensitive
        regexp = wildcard_expression(text.strip(), casesensitivity)
        self._ihda_inside_proxy_model.setFilterRegularExpression(regexp)
        self.label__found_hda_inside_hipfile_count.setText(
            str(self._ihda_inside_proxy_model.get_row_count())
        )
        self._ihda_inside_view.expandAll()

    def _add_pixmap_category(self, category: str | None = None) -> None:
        self._ihda_icons.add_pixmap_cate_data(category=category)

    def _add_pixmap_ihda(
        self, hkey_id: int | None = None, icon_lst: list[str] | None = None
    ) -> None:
        self._ihda_icons.add_pixmap_ihda_data(hkey_id=hkey_id, icon_lst=icon_lst)

    def _add_pixmap_thumbnail(
        self, hkey_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        assert isinstance(thumb_filepath, pathlib.Path)
        self._ihda_icons.add_pixmap_thumbnail_data(
            hkey_id=hkey_id, thumb_filepath=thumb_filepath
        )

    def _add_pixmap_hist_thumbnail(
        self, hist_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        assert isinstance(thumb_filepath, pathlib.Path)
        self._ihda_icons.add_pixmap_hist_thumbnail_data(
            hist_id=hist_id, thumb_filepath=thumb_filepath
        )

    def _update_pixmap_thumbnail(
        self, hkey_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        assert isinstance(thumb_filepath, pathlib.Path)
        self._ihda_icons.update_pixmap_thumbnail_data(
            hkey_id=hkey_id, thumb_filepath=thumb_filepath
        )

    def _update_pixmap_hist_thumbnail(
        self, hist_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None:
        assert isinstance(thumb_filepath, pathlib.Path)
        self._ihda_icons.update_pixmap_hist_thumbnail_data(
            hist_id=hist_id, thumb_filepath=thumb_filepath
        )

    def _remove_pixmap_category(self, category: str | None = None) -> None:
        self._ihda_icons.remove_pixmap_cate_data(category=category)

    def _remove_pixmap_ihda(self, hkey_id: int | None = None) -> None:
        self._ihda_icons.remove_pixmap_ihda_data(hkey_id=hkey_id)

    def _remove_pixmap_thumbnail(self, hkey_id: int | None = None) -> None:
        self._ihda_icons.remove_pixmap_thumbnail_data(hkey_id=hkey_id)

    def _remove_pixmap_hist_thumbnail(self, hist_id: int | None = None) -> None:
        self._ihda_icons.remove_pixmap_hist_thumbnail_data(hist_id=hist_id)

    def _clear_pixmap_histotry(self) -> None:
        self._ihda_icons.clear_pixmap_hist_thumbnail_data()

    def _add_record_item(self, data: Any = None) -> None:
        self._ihda_record_model.insert_record_data(data=data)
        self._ihda_record_model.reload()
        self._ihda_record_view.expandAll()

    def _add_category_item(self, category: str | None = None) -> None:
        self._add_pixmap_category(category=category)
        self._ihda_category_model.add_item(data={category: None})
        self._ihda_category_model.reload()
        self._ihda_category_view.expandAll()

    def _remove_category_item(
        self, category: str | None = None, category_list: Any = None
    ) -> None:
        if category_list is None:
            self._ihda_category_model.remove_item(category=category)
            self._remove_pixmap_category(category=category)
            self._ihda_category_model.reload()
        else:
            if category not in category_list:
                self._ihda_category_model.remove_item(category=category)
                self._remove_pixmap_category(category=category)
                self._ihda_category_model.reload()
                self._ihda_category_view.expandAll()

    def _get_category_count(self) -> int:
        return self._ihda_category_proxy_model.rowCount(
            self._ihda_category_proxy_model.index(0, 0, QtCore.QModelIndex())
        )

    def _remove_hda_data(self, item_row: int | None = None) -> None:
        if item_row is not None:
            self._assets.observe(
                QtAssetNotifications(self._ihda_list_model, self._ihda_table_model)
            )
            self._assets.remove(item_row)
