"""Ports: what panel features may use of each other.

Bindings are typed with these protocols instead of the concrete feature classes,
so a feature can only reach what another feature deliberately exposes. Add a
member here when a feature needs it; do not reach for an underscore name.
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence
from typing import Any, Protocol

from PySide6 import QtCore, QtGui

from libs.asset_contracts import AssetData, HistoryData
from libs.asset_store import AssetStore
from libs.scene_contracts import SceneRecord
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


class LibraryQueryPort(Protocol):
    def change_hda_data(
        self, row: int | None = None, key: Any = None, val: Any = None
    ) -> None: ...
    @property
    def db_filepath(self) -> pathlib.Path | None: ...
    def find_hda_id_by_model_item(
        self, model_hda: Any = None, find_hda_id: int | None = None
    ) -> QtCore.QModelIndex | None: ...
    def find_tree_element_model(
        self, index: QtCore.QModelIndex | None = None, find_name: str = ""
    ) -> QtCore.QModelIndex | None: ...
    def get_all_category_parent_by_selected_item(
        self, index: QtCore.QModelIndex
    ) -> list[Any]: ...
    def get_hda_category(
        self, user_id: str | None = None, db_filepath: pathlib.Path | None = None
    ) -> dict[str, Any] | None: ...
    def get_hda_hist_data(
        self,
        hda_key_id: int | None = None,
        user_id: str | None = None,
        search_date: Any = None,
        db_filepath: pathlib.Path | None = None,
    ) -> list[HistoryData]: ...
    def get_hda_loc_record_data(
        self, db_filepath: pathlib.Path | None
    ) -> tuple[SceneRecord, ...]: ...
    def get_ihda_data_by_id(
        self, hda_id: int | None = None, key: Any = None
    ) -> Any: ...
    @property
    def hda_base_dirpath(self) -> pathlib.Path | None: ...
    @property
    def is_valid_current_hda_item_data(self) -> bool: ...
    @property
    def is_valid_hist_current_item_data(self) -> bool: ...


class AssetModelPort(Protocol):
    def add_category_item(self, category: str | None = None) -> None: ...
    def add_pixmap_hist_thumbnail(
        self, hist_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None: ...
    def add_pixmap_ihda(
        self, hkey_id: int | None = None, icon_lst: list[str] | None = None
    ) -> None: ...
    def add_pixmap_thumbnail(
        self, hkey_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None: ...
    def add_record_item(self, data: Any = None) -> None: ...

    assets: AssetStore
    category_model: ihda_category_model.CategoryModel
    category_proxy_model: ihda_category_proxy_model.CategoryProxyModel

    def get_category_count(self) -> int: ...

    history_model: ihda_history_model.HistoryModel
    history_proxy_model: ihda_history_proxy_model.HistoryProxyModel

    def insert_ihda_data_model(self, data: AssetData) -> None: ...
    def insert_ihda_history_data_model(
        self,
        data: HistoryData,
        hist_id: int | None = None,
        tags: Sequence[str] | None = None,
        comment: str | None = None,
    ) -> None: ...

    inside_model: ihda_inside_model.InsideModel
    inside_proxy_model: ihda_inside_proxy_model.InsideProxyModel
    list_model: ihda_list_model.ListModel
    list_proxy_model: ihda_list_proxy_model.ListProxyModel
    record_model: ihda_record_model.RecordModel
    record_proxy_model: ihda_record_proxy_model.RecordProxyModel

    def refresh_asset_search(self) -> None: ...
    def remove_category_item(
        self, category: str | None = None, category_list: Any = None
    ) -> None: ...
    def remove_hda_data(self, item_row: int | None = None) -> None: ...
    def remove_pixmap_hist_thumbnail(self, hist_id: int | None = None) -> None: ...
    def remove_pixmap_ihda(self, hkey_id: int | None = None) -> None: ...
    def remove_pixmap_thumbnail(self, hkey_id: int | None = None) -> None: ...
    def search_filter_regexp_hda_cate(self, text: str) -> None: ...
    def search_filter_regexp_hist_hda_item(self, text: str) -> None: ...

    table_model: ihda_table_model.TableModel
    table_proxy_model: ihda_table_proxy_model.TableProxyModel

    def update_item_row_data(
        self, row: int | None = None, row_data: AssetData | None = None
    ) -> None: ...
    def update_pixmap_hist_thumbnail(
        self, hist_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None: ...
    def update_pixmap_thumbnail(
        self, hkey_id: int | None = None, thumb_filepath: pathlib.Path | None = None
    ) -> None: ...


class PresentationPort(Protocol):
    def change_org_node_name(
        self, parent_node: Any = None, node_name: Any = None
    ) -> None: ...
    def dragdrop_overlay_close(self) -> None: ...
    def dragdrop_overlay_show(
        self, text: str | None = None, fontsize: int | None = None
    ) -> None: ...
    def get_default_font(self, font_size: int | None = None) -> QtGui.QFont: ...
    def get_font_properties(self, size_key: Any, style_key: Any) -> list[Any]: ...
    def get_listview_properties(self, zoom_val: float) -> list[Any]: ...
    def get_padding_properties(self, dft_pad: Any, pad_key: Any) -> int: ...
    def get_tableview_properties(self, zoom_val: float) -> list[Any]: ...
    def get_treeview_properties(self) -> int: ...
    @property
    def is_icon_mode(self) -> bool: ...
    @property
    def is_ihda_history_view(self) -> bool: ...
    @property
    def is_show_thumbnail(self) -> bool: ...
    def loading_close(self) -> None: ...
    def loading_show(self) -> None: ...
    def open_houdini_file(self, hip_filepath: pathlib.Path | None = None) -> None: ...
    def resizing_listview(self) -> None: ...
    def set_view_item_icon_size(self, val: Any) -> None: ...
