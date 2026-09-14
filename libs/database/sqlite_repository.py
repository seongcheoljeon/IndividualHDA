"""Local SQLite adapter for LibraryRepository.

Composes the existing SQLite3DatabaseAPI facade (one connection per operation)
and the journaled file commands. Registration bodies moved here from the panel
unchanged in logic; HOM work (HDA/thumbnail files) happens before they run.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
import threading
from collections.abc import Callable, Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

from libs import asset_commands
from libs.asset_rename import RenamePlan, rename_asset
from libs.database.rename_repository import SQLiteRenameRepository
from libs.database.values import DatabaseValues
from libs.domain import AssetData, HistoryData
from libs.library_explorer import search_asset_ids
from libs.repository import (
    LibraryConflict,
    LibraryError,
    LibraryUnavailable,
    RegistrationPayload,
    RegistrationResult,
)
from libs.sqlite3_db_api import SQLite3DatabaseAPI

log = logging.getLogger(__name__)


class SqliteLibraryRepository:
    def __init__(
        self,
        db_filepath: Path,
        open_database: Callable[[Path], SQLite3DatabaseAPI] = SQLite3DatabaseAPI,
    ) -> None:
        self._db_filepath = Path(db_filepath)
        self._open_database = open_database

    @property
    def db_filepath(self) -> Path:
        return self._db_filepath

    def _open(self) -> SQLite3DatabaseAPI:
        if not self._db_filepath.is_file():
            raise LibraryUnavailable(f"database file not found: {self._db_filepath}")
        return self._open_database(self._db_filepath)

    # --- session / identity -------------------------------------------------
    def ensure_user(self, user: str) -> None:
        with closing(self._open()) as db:
            if not db.is_exist_user_id(user):
                db.insert_users(user_id=user, email=f"{user}@local")

    def revision(self) -> int:
        # ponytail: file mtime is enough for a per-operation-connection design;
        # the server adapter returns a real monotonically increasing counter.
        try:
            return self._db_filepath.stat().st_mtime_ns
        except OSError:
            return 0

    # --- reads ---------------------------------------------------------------
    def list_assets(
        self, owner: str | None = None, category: str | None = None
    ) -> list[AssetData]:
        if not self._db_filepath.is_file():
            return []
        with closing(self._open()) as db:
            return db.get_hda_data(category=category, user_id=owner)

    def categories(self, owner: str | None = None) -> list[str]:
        if not self._db_filepath.is_file():
            return []
        with closing(self._open()) as db:
            return db.get_hda_category(user_id=owner) or []

    def histories(
        self, asset_id: int | None, owner: str | None = None, search_date: Any = None
    ) -> list[HistoryData]:
        if not self._db_filepath.is_file():
            return []
        with closing(self._open()) as db:
            return db.get_hda_history(
                hda_key_id=asset_id, user_id=owner, search_date=search_date
            )

    def asset_icons(self, owner: str | None = None) -> list[Any]:
        if not self._db_filepath.is_file():
            return []
        with closing(self._open()) as db:
            return db.get_icon_info_by_user(user_id=owner) or []

    def history_thumbnails(self, owner: str | None = None) -> list[Any]:
        if not self._db_filepath.is_file():
            return []
        with closing(self._open()) as db:
            return db.get_thumbnail_by_hda_history(user_id=owner) or []

    def history_videos(self, asset_id: int) -> list[Path]:
        with closing(self._open()) as db:
            return list(db.get_history_video_info(hda_key_id=asset_id) or [])

    def video_matches_version(self, asset_id: int, version: str) -> bool:
        with closing(self._open()) as db:
            return bool(
                db.is_video_and_ihda_same_version(hda_key_id=asset_id, version=version)
            )

    def is_latest_history(self, asset_id: int, history_id: int) -> bool:
        with closing(self._open()) as db:
            return bool(
                db.is_most_recent_ihda_history(hda_key_id=asset_id, hist_id=history_id)
            )

    def is_latest_version(self, asset_id: int, version: str) -> bool:
        with closing(self._open()) as db:
            return bool(
                db.is_ihda_lastest_version(hda_key_id=asset_id, version=version)
            )

    def search_asset_ids(
        self,
        query: str,
        *,
        field: str = "All",
        case_sensitive: bool = False,
        limit: int = 5000,
        cancel: threading.Event | None = None,
    ) -> list[int]:
        if not self._db_filepath.is_file():
            return []
        return search_asset_ids(
            self._db_filepath,
            query,
            field=field,
            case_sensitive=case_sensitive,
            limit=limit,
            cancel=cancel,
        )

    def distinct_tags(self, owner: str | None = None) -> list[str]:
        if not self._db_filepath.is_file():
            return []
        with closing(self._open()) as db:
            return db.distinct_tags(user_id=owner)

    # --- writes --------------------------------------------------------------
    def register_asset(self, payload: RegistrationPayload) -> RegistrationResult:
        p = payload
        thumb_filepath = p.thumb_dirpath / p.thumb_filename
        with closing(self._open()) as db:
            if db.is_exist_hda_name(
                user_id=p.user, category=p.cate_name, hda_name=p.node_name
            ):
                raise LibraryConflict(f"{p.node_name} already exists in {p.cate_name}")
            try:
                with db.transaction():
                    if (
                        db.insert_hda_category(category=p.cate_name, user_id=p.user)
                        is None
                    ):
                        raise sqlite3.DatabaseError("Could not create asset category")
                    if not db.insert_hda_key(
                        name=p.node_name, category=p.cate_name, user_id=p.user
                    ):
                        raise sqlite3.DatabaseError("Could not create asset key")
                    key_id = db.get_last_insert_id
                    ok = [
                        db.insert_hda_info(
                            hda_key_id=key_id,
                            version=p.version,
                            is_favorite=False,
                            load_count=0,
                            filename=p.hda_filename,
                            dirpath=p.hda_dirpath,
                        ),
                        db.insert_icon_info(
                            hda_key_id=key_id, icon_lst=p.icon_path_lst
                        ),
                        db.insert_hipfile_info(
                            hda_key_id=key_id,
                            filename=p.hip_filename,
                            dirpath=p.hip_dirpath,
                            houdini_version=p.hou_version,
                            hda_license=p.hou_license,
                            operating_system=p.operating_system,
                            sf=p.sf,
                            ef=p.ef,
                            fps=p.fps,
                        ),
                    ]
                    if not db.insert_thumbnail_info(
                        hda_key_id=key_id,
                        dirpath=p.thumb_dirpath,
                        filename=p.thumb_filename,
                        version=p.version,
                    ):
                        shutil.rmtree(p.thumb_dirpath, ignore_errors=True)
                    ok.append(
                        db.insert_houdini_node_info(
                            hda_key_id=key_id,
                            type_name=p.type_name,
                            def_desc=p.def_desc,
                            is_net=p.is_network,
                            is_sub_net=p.is_sub_network,
                            old_path=p.node_path,
                        )
                    )
                    info_id = db.get_last_insert_id
                    ok += [
                        db.insert_houdini_node_category_path_info(
                            info_id=info_id, node_category_lst=p.cate_path_lst
                        ),
                        db.insert_houdini_node_type_path_info(
                            info_id=info_id, node_type_lst=p.type_path_lst
                        ),
                        db.insert_houdini_node_input_connect_info(
                            info_id=info_id, node_input_connect_lst=p.input_conn
                        ),
                        db.insert_houdini_node_output_connect_info(
                            info_id=info_id, node_output_connect_lst=p.output_conn
                        ),
                    ]
                    history = self._history_row(key_id, "NODE (INSERT)", p, None, None)
                    ok.append(db.insert_hda_history(data=history))
                    history_id = db.get_last_insert_id
                    if any(value is None for value in ok):
                        raise sqlite3.DatabaseError("Incomplete asset registration")
            except sqlite3.Error as error:
                log.error("Asset registration rolled back: %s", error)
                raise LibraryError(f"asset registration failed: {error}") from error
        asset = self._asset_row(
            key_id,
            p,
            is_favorite=0,
            load_count=0,
            ctime=p.registered_at,
            video=(None, None),
            note=None,
            tags=[],
        )
        return RegistrationResult(asset, history, int(history_id or 0), thumb_filepath)

    def add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult:
        p = payload
        thumb_filepath = p.thumb_dirpath / p.thumb_filename
        with closing(self._open()) as db:
            try:
                with db.transaction():
                    ok = [
                        db.update_hda_info(
                            hda_key_id=asset_id,
                            version=p.version,
                            filename=p.hda_filename,
                            dirpath=p.hda_dirpath,
                        ),
                        db.update_icon_info(
                            hda_key_id=asset_id, icon_lst=p.icon_path_lst
                        ),
                        db.update_hipfile_info(
                            hda_key_id=asset_id,
                            filename=p.hip_filename,
                            dirpath=p.hip_dirpath,
                            houdini_version=p.hou_version,
                            hda_license=p.hou_license,
                            operating_system=p.operating_system,
                            sf=p.sf,
                            ef=p.ef,
                            fps=p.fps,
                        ),
                    ]
                    db.update_thumbnail_info(
                        hda_key_id=asset_id,
                        dirpath=p.thumb_dirpath,
                        filename=p.thumb_filename,
                        version=p.version,
                    )
                    ok.append(
                        db.update_houdini_node_info(
                            hda_key_id=asset_id, node_path=p.node_path
                        )
                    )
                    info_id = db.get_hou_node_info_id(hda_key_id=asset_id)
                    ok += [
                        db.update_houdini_node_category_path_info(
                            info_id=info_id, node_category_lst=p.cate_path_lst
                        ),
                        db.update_houdini_node_type_path_info(
                            info_id=info_id, node_type_lst=p.type_path_lst
                        ),
                        db.update_houdini_node_input_connect_info(
                            info_id=info_id, node_input_connect_lst=p.input_conn
                        ),
                        db.update_houdini_node_output_connect_info(
                            info_id=info_id, node_output_connect_lst=p.output_conn
                        ),
                    ]
                    if any(value is None for value in ok):
                        raise sqlite3.DatabaseError("Incomplete asset update")
                    before = db.get_update_before_data(hda_key_id=asset_id)
                    video = (before.get("video_dirpath"), before.get("video_filename"))
                    history = self._history_row(
                        asset_id, "NODE (UPDATE)", p, video[1], video[0]
                    )
                    if db.insert_hda_history(data=history) is None:
                        raise sqlite3.DatabaseError("Could not write asset history")
                    history_id = db.get_last_insert_id
            except sqlite3.Error as error:
                log.error("Asset update rolled back: %s", error)
                raise LibraryError(f"asset update failed: {error}") from error
        asset = self._asset_row(
            asset_id,
            p,
            is_favorite=before.get("is_favorite_hda"),
            load_count=before.get("hda_load_count"),
            ctime=before.get("hda_ctime"),
            video=video,
            note=before.get("hda_note"),
            tags=before.get("hda_tags") or [],
        )
        return RegistrationResult(asset, history, int(history_id or 0), thumb_filepath)

    def set_note(self, asset_id: int, note: str) -> None:
        with closing(self._open()) as db:
            if db.is_exist_note(hda_key_id=asset_id):
                done = db.update_note_info(hda_key_id=asset_id, note=note)
            else:
                done = db.insert_note_info(hda_key_id=asset_id, note=note)
        if done is None:
            raise LibraryError("note was not saved")

    def set_tags(self, asset_id: int, tags: Sequence[str]) -> None:
        with closing(self._open()) as db:
            if db.is_exist_tag(hda_key_id=asset_id):
                done = db.update_tag_info(hda_key_id=asset_id, tag_lst=list(tags))
            else:
                done = db.insert_tag_info(hda_key_id=asset_id, tag_lst=list(tags))
        if done is None:
            raise LibraryError("tags were not saved")

    def toggle_favorite(self, asset_id: int) -> bool:
        with closing(self._open()) as db:
            return bool(db.update_hda_favorite(hda_key_id=asset_id))

    def rename_asset(self, plan: RenamePlan) -> tuple[int, int]:
        with closing(self._open()) as db:
            return rename_asset(SQLiteRenameRepository(db), plan)

    def delete_asset(self, asset_id: int, directory: Path) -> None:
        with closing(self._open()) as db:
            asset_commands.delete_asset(db, asset_id, directory)

    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None:
        with closing(self._open()) as db:
            try:
                asset_commands.delete_history(db, asset_id, history_id, list(files))
            except ValueError as error:  # most recent history
                raise LibraryConflict(str(error)) from error

    # --- row builders (same column order the panel models expect) ----------
    @staticmethod
    def _history_row(
        asset_id: int,
        comment: str,
        p: RegistrationPayload,
        video_filename: Any,
        video_dirpath: Any,
    ) -> list[Any]:
        return [
            asset_id,
            comment,
            p.node_name,
            p.version,
            p.hda_filename,
            p.hda_dirpath,
            p.registered_at,
            p.hou_version,
            p.hip_filename,
            p.hip_dirpath,
            p.hou_license,
            p.operating_system,
            p.node_path,
            p.def_desc,
            p.type_name,
            p.cate_name,
            p.user,
            p.icon_path_lst,
            p.thumb_filename,
            p.thumb_dirpath,
            video_filename,
            video_dirpath,
        ]

    @staticmethod
    def _asset_row(
        asset_id: int,
        p: RegistrationPayload,
        *,
        is_favorite: Any,
        load_count: Any,
        ctime: Any,
        video: tuple[Any, Any],
        note: Any,
        tags: Any,
    ) -> AssetData:
        values = [
            asset_id,
            p.node_name,
            p.cate_name,
            p.version,
            p.hda_filename,
            p.hda_dirpath,
            is_favorite,
            load_count,
            ctime,
            p.registered_at,
            p.hou_version,
            p.type_name,
            p.def_desc,
            p.is_network,
            p.is_sub_network,
            p.node_path,
            p.hou_license,
            p.hip_filename,
            p.hip_dirpath,
            p.thumb_filename,
            p.thumb_dirpath,
            video[1],
            video[0],
            note,
            p.icon_path_lst,
            tags,
        ]
        keys = DatabaseValues.hda_info_key_lst()
        assert len(keys) == len(values)
        return dict(zip(keys, values, strict=False))  # type: ignore[return-value]
