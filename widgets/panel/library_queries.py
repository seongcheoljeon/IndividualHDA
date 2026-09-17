"""Library queries for the Houdini panel.

Explicit bindings connect this feature to its view and collaborators.
"""

from __future__ import annotations

import pathlib
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore

from libs.asset_contracts import AssetData, HistoryData
from libs.item_paths import item_path
from libs.record_codec import decode_record
from libs.repository import LibraryError
from libs.scene_contracts import SceneRecord
from model.asset_notifications import QtAssetNotifications

if TYPE_CHECKING:
    pass
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from libs import houdini_api, keys, log_handler, platform_info

if TYPE_CHECKING:
    from widgets.panel.asset_management import PanelAssetManagement
    from widgets.panel.model_binding import PanelModelBinding
    from widgets.panel.presentation import PanelPresentation
    from widgets.panel.selection import PanelSelection
    from widgets.panel.state import PanelSessionState


@dataclass(frozen=True, slots=True)
class PanelLibraryQueriesBindings:
    management: PanelAssetManagement
    models: PanelModelBinding
    presentation: PanelPresentation
    selection: PanelSelection
    session: PanelSessionState


class PanelLibraryQueries:
    bindings: PanelLibraryQueriesBindings

    @property
    def _db_filepath(self) -> pathlib.Path | None:
        return (
            self.bindings.session.context.db_filepath
            if self.bindings.session.context is not None
            else None
        )

    def _get_ihda_data_by_id(self, hda_id: int | None = None, key: Any = None) -> Any:
        if hda_id is None:
            return None
        item_row = self.bindings.management._get_hda_id_row_map().get(hda_id)
        if item_row is None:
            return None
        if key == keys.Key.item_row:
            return item_row
        return getattr(self.bindings.models.assets.rows[item_row], key)

    def _find_tree_element_model(
        self, index: QtCore.QModelIndex | None = None, find_name: str = ""
    ) -> QtCore.QModelIndex | None:
        if index is None:
            index = QtCore.QModelIndex()
        for row in range(0, self.bindings.models.category_proxy_model.rowCount(index)):
            child_idx = self.bindings.models.category_proxy_model.index(row, 0, index)
            if child_idx.data() == find_name:
                return child_idx
            found = self._find_tree_element_model(child_idx, find_name)
            if found is not None:
                return found
        return None

    def _find_hda_id_by_model_item(
        self, model_hda: Any = None, find_hda_id: int | None = None
    ) -> QtCore.QModelIndex | None:
        if find_hda_id is None:
            return None
        hda_id_row_map = self.bindings.management._get_hda_id_row_map()
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
        self.bindings.models.assets.observe(
            QtAssetNotifications(
                self.bindings.models.list_model, self.bindings.models.table_model
            )
        )
        self.bindings.models.assets.update(
            row, replace(self.bindings.models.assets.rows[row], **{key: val})
        )
        if (
            self.bindings.selection.state.asset.id
            == self.bindings.models.assets.rows[row].hda_id
        ):
            self.bindings.selection.state.select_asset(
                self.bindings.models.assets.rows[row],
                row,
                self.bindings.selection.state.asset.field,
            )

    def _insert_hist_db_from_curt_hist_data(
        self,
        comment: str | None = None,
        *,
        data: AssetData | None = None,
    ) -> None:
        # history를 위한 변수
        data = data if data is not None else self.bindings.selection.state.asset.data
        if data is None or self.bindings.session.repository is None:
            return
        hda_dirpath = data.hda_dirpath
        hda_name = data.hda_name
        hda_version = data.hda_version
        hda_id = data.hda_id
        hda_filename = data.hda_filename
        node_path = data.node_old_path
        def_desc = data.node_def_desc
        type_name = data.node_type_name
        cate_name = data.hda_cate
        icon_lst = data.hda_icon
        tag_lst = data.hda_tags
        thumb_filename = data.thumbnail_filename
        thumb_dirpath = data.thumbnail_dirpath
        thumb_filepath = item_path(thumb_dirpath, thumb_filename)
        video_filename = data.video_filename
        video_dirpath = data.video_dirpath
        hou_version = houdini_api.HoudiniAPI.current_houdini_version()
        hou_license = houdini_api.HoudiniAPI.current_houdini_license()
        hip_filepath = houdini_api.HoudiniAPI.current_hipfile()
        hip_dirpath = hip_filepath.parent
        hip_filename = hip_filepath.name
        declare_os = platform_info.platform_system()
        val_datetime = datetime.today().strftime(keys.Value.datetime_fmt_str)
        hist_data = decode_record(
            HistoryData,
            {
                "hda_id": hda_id,
                "comment": comment,
                "org_hda_name": hda_name,
                "version": hda_version,
                "ihda_filename": hda_filename,
                "ihda_dirpath": hda_dirpath,
                "reg_time": val_datetime,
                "hou_version": hou_version,
                "hip_filename": hip_filename,
                "hip_dirpath": hip_dirpath,
                "hda_license": hou_license,
                "os": declare_os,
                "node_old_path": node_path,
                "node_def_desc": def_desc,
                "node_type_name": type_name,
                "node_category": cate_name,
                "userid": self.bindings.session.user,
                "icon": icon_lst,
                "thumb_filename": thumb_filename,
                "thumb_dirpath": thumb_dirpath,
                "video_filename": video_filename,
                "video_dirpath": video_dirpath,
            },
        )
        try:
            last_hda_hist_id = (
                self.bindings.session.require_repository().add_history_row(hist_data)
            )
        except LibraryError:
            logging.exception("Could not record history for %s", hda_name)
            self.bindings.presentation._loading_close()
            return
        self.bindings.models._add_pixmap_hist_thumbnail(
            hist_id=last_hda_hist_id, thumb_filepath=thumb_filepath
        )
        self.bindings.models._insert_ihda_history_data_model(
            data=hist_data, hist_id=last_hda_hist_id, tags=tag_lst
        )

    def _get_hda_data(
        self,
        category: str | None = None,
        user_id: str | None = None,
        db_filepath: pathlib.Path | None = None,
    ) -> list[AssetData]:
        if self.bindings.session.repository is None:
            return []
        return self.bindings.session.require_repository().list_assets(
            owner=user_id, category=category
        )

    def _get_hda_hist_data(
        self,
        hda_key_id: int | None = None,
        user_id: str | None = None,
        search_date: Any = None,
        db_filepath: pathlib.Path | None = None,
    ) -> list[HistoryData]:
        if self.bindings.session.repository is None:
            return []
        return self.bindings.session.require_repository().histories(
            hda_key_id, owner=user_id, search_date=search_date
        )

    def _get_hda_category(
        self, user_id: str | None = None, db_filepath: pathlib.Path | None = None
    ) -> dict[str, Any] | None:
        if user_id is None or self.bindings.session.repository is None:
            return {}
        cate_lst = self.bindings.session.require_repository().categories(owner=user_id)
        return dict(zip(cate_lst, [None] * len(cate_lst), strict=False))

    def _get_hda_loc_record_data(
        self, db_filepath: pathlib.Path | None
    ) -> tuple[SceneRecord, ...]:
        return (
            self.bindings.session.require_repository().scene_records()
            if self.bindings.session.repository
            else ()
        )

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
        return (
            self.bindings.session.context.hda_base_dirpath
            if self.bindings.session.context is not None
            else None
        )

    @property
    def _is_valid_current_hda_item_data(self) -> bool:
        if self.bindings.selection.state.asset.data is not None:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning,
            msg="<font color=#cc6600>node is not selected</font>",
        )
        return False

    @property
    def _is_valid_hist_current_item_data(self) -> bool:
        if self.bindings.selection.state.history.data is not None:
            return True
        log_handler.LogHandler.log_msg(
            method=logging.warning,
            msg="<font color=#cc6600>iHDA history node is not selected</font>",
        )
        return False
