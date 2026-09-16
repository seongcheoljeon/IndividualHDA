"""Library queries for the Houdini panel.

Shares protected panel state; Qt and HOM calls stay on the GUI thread.
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore

from libs.domain import AssetData, HistoryData
from libs.repository import LibraryError
from model.asset_notifications import QtAssetNotifications

if TYPE_CHECKING:
    pass
import logging
from datetime import datetime

import public
from libs import houdini_api, log_handler, sqlite3_db_api


class LibraryQueriesMixin:
    @property
    def _db_filepath(self) -> pathlib.Path | None:
        return self._library.db_filepath if self._library is not None else None

    def _db_api_wrap(
        self,
        db_filepath: pathlib.Path | None,
    ) -> sqlite3_db_api.SQLite3DatabaseAPI | None:
        if db_filepath is None:
            log_handler.LogHandler.log_msg(method=logging.critical, msg="no data path")
            return None
        assert isinstance(db_filepath, pathlib.Path)
        if not db_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.critical,
                msg=f'the database file does not exist in the path "{db_filepath.as_posix()}"',
            )
            return None
        return self._services.open_database(db_filepath)

    def _get_ihda_data_by_id(self, hda_id: int | None = None, key: Any = None) -> Any:
        item_row = self._get_hda_id_row_map().get(hda_id)
        if item_row is None:
            return None
        if key == public.Key.item_row:
            return item_row
        return self._assets.rows[item_row].get(key)

    def _find_tree_element_model(
        self, index: QtCore.QModelIndex = None, find_name: str = ""
    ) -> QtCore.QModelIndex | None:
        if index is None:
            index = QtCore.QModelIndex()
        for row in range(0, self._ihda_category_proxy_model.rowCount(index)):
            child_idx = self._ihda_category_proxy_model.index(row, 0, index)
            if child_idx.data() == find_name:
                return child_idx
            found = self._find_tree_element_model(child_idx, find_name)
            if found is not None:
                return found
        return None

    def _find_hda_id_by_model_item(
        self, model_hda: Any = None, find_hda_id: int | None = None
    ) -> QtCore.QModelIndex | None:
        hda_id_row_map = self._get_hda_id_row_map()
        find_row = hda_id_row_map.get(find_hda_id)
        if find_row is None:
            return None
        if isinstance(model_hda, QtCore.QAbstractProxyModel):
            source = model_hda.sourceModel()
            index = model_hda.mapFromSource(source.index(find_row, 0))
        else:
            index = model_hda.index(find_row, 0)
        return index if index.isValid() else None

    def _change_hda_data(
        self, row: int | None = None, key: Any = None, val: Any = None
    ) -> None:
        if row is None:
            return
        self._assets.observe(
            QtAssetNotifications(self._ihda_list_model, self._ihda_table_model)
        )
        self._assets.update(row, {key: val})
        if self._selection.asset.id == self._assets.rows[row]["hda_id"]:
            self._selection.select_asset(
                self._assets.rows[row], row, self._selection.asset.field
            )

    def _insert_hist_db_from_curt_hist_data(
        self,
        comment: str | None = None,
        *,
        data: AssetData | None = None,
    ) -> None:
        # history를 위한 변수
        data = data if data is not None else self._selection.asset.data
        if data is None or self._repository is None:
            return
        hda_dirpath = data.get(public.Key.hda_dirpath)
        hda_name = data.get(public.Key.hda_name)
        hda_version = data.get(public.Key.hda_version)
        hda_id = data.get(public.Key.hda_id)
        hda_filename = data.get(public.Key.hda_filename)
        node_path = data.get(public.Key.node_old_path)
        def_desc = data.get(public.Key.node_def_desc)
        type_name = data.get(public.Key.node_type_name)
        cate_name = data.get(public.Key.hda_cate)
        icon_lst = data.get(public.Key.hda_icon)
        tag_lst = data.get(public.Key.hda_tags)
        thumb_filename = data.get(public.Key.thumbnail_filename)
        thumb_dirpath = data.get(public.Key.thumbnail_dirpath)
        thumb_filepath = thumb_dirpath / thumb_filename
        video_filename = data.get(public.Key.video_filename)
        video_dirpath = data.get(public.Key.video_dirpath)
        hou_version = houdini_api.HoudiniAPI.current_houdini_version()
        hou_license = houdini_api.HoudiniAPI.current_houdini_license()
        hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        hip_dirpath = hip_filepath.parent
        hip_filename = hip_filepath.name
        declare_os = public.platform_system()
        val_datetime = datetime.today().strftime(public.Value.datetime_fmt_str)
        hist_data = [
            hda_id,
            comment,
            hda_name,
            hda_version,
            hda_filename,
            hda_dirpath,
            val_datetime,
            hou_version,
            hip_filename,
            hip_dirpath,
            hou_license,
            declare_os,
            node_path,
            def_desc,
            type_name,
            cate_name,
            self._user,
            icon_lst,
            thumb_filename,
            thumb_dirpath,
            video_filename,
            video_dirpath,
        ]
        try:
            last_hda_hist_id = self._repository.add_history_row(hist_data)
        except LibraryError:
            logging.exception("Could not record history for %s", hda_name)
            self._loading_close()
            return
        self._add_pixmap_hist_thumbnail(
            hist_id=last_hda_hist_id, thumb_filepath=thumb_filepath
        )
        self._insert_ihda_history_data_model(
            data=hist_data, hist_id=last_hda_hist_id, tags=tag_lst
        )

    def _get_hda_data(
        self,
        category: str | None = None,
        user_id: str | None = None,
        db_filepath: pathlib.Path | None = None,
    ) -> list[AssetData]:
        if self._repository is None:
            return []
        return self._repository.list_assets(owner=user_id, category=category)

    def _get_hda_hist_data(
        self,
        hda_key_id: int | None = None,
        user_id: str | None = None,
        search_date: Any = None,
        db_filepath: pathlib.Path | None = None,
    ) -> list[HistoryData]:
        if self._repository is None:
            return []
        return self._repository.histories(
            hda_key_id, owner=user_id, search_date=search_date
        )

    def _get_hda_category(
        self, user_id: str | None = None, db_filepath: pathlib.Path | None = None
    ) -> dict[str, Any] | None:
        if user_id is None or self._repository is None:
            return {}
        cate_lst = self._repository.categories(owner=user_id)
        return dict(zip(cate_lst, [None] * len(cate_lst), strict=False))

    def _get_hda_loc_record_data(
        self, db_filepath: pathlib.Path
    ) -> dict[str, Any] | None:
        db_api = self._db_api_wrap(db_filepath)
        if db_api is None:
            return
        with db_api:
            record_data = db_api.get_hda_node_location_record()
        return record_data

    def _get_all_category_parent_by_selected_item(
        self, index: QtCore.QModelIndex
    ) -> list[Any]:
        plist = []
        if not index.isValid():
            return []
        plist.append(index.data(QtCore.Qt.ItemDataRole.DisplayRole))
        return self._get_all_category_parent_by_selected_item(index.parent()) + plist

    @property
    def _hda_base_dirpath(self) -> pathlib.Path | None:
        return self._library.hda_base_dirpath if self._library is not None else None

    @property
    def _is_valid_current_hda_item_data(self) -> bool:
        if self._selection.asset.data is not None:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning,
            msg="<font color=#cc6600>node is not selected</font>",
        )
        return False

    @property
    def _is_valid_hist_current_item_data(self) -> bool:
        if self._selection.history.data is not None:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning,
            msg="<font color=#cc6600>iHDA history node is not selected</font>",
        )
        return False
