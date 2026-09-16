"""Local SQLite adapter for LibraryRepository.

Composes the existing SQLite3DatabaseAPI facade (one connection per operation)
and the journaled file commands. Registration bodies moved here from the panel
unchanged in logic; HOM work (HDA/thumbnail files) happens before they run.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager, closing, suppress
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
        *,
        session_factory: Callable[[], AbstractContextManager[SQLite3DatabaseAPI]]
        | None = None,
    ) -> None:
        self._db_filepath = Path(db_filepath)
        self._open_database = open_database
        self._session_factory = session_factory

    @property
    def db_filepath(self) -> Path:
        return self._db_filepath

    def _open(self) -> SQLite3DatabaseAPI:
        if not self._db_filepath.is_file():
            raise LibraryUnavailable(f"database file not found: {self._db_filepath}")
        return self._open_database(self._db_filepath)

    def _session(self) -> AbstractContextManager[SQLite3DatabaseAPI]:
        return (
            self._session_factory()
            if self._session_factory is not None
            else closing(self._open())
        )

    # --- session / identity -------------------------------------------------
    def ensure_user(self, user: str) -> None:
        with self._session() as db:
            if not db.is_exist_user_id(user):
                if db.insert_users(user_id=user, email=f"{user}@local") is None:
                    raise LibraryError(f"could not create library user {user!r}")

    def revision(self) -> int:
        # ponytail: file mtime is enough for a per-operation-connection design;
        # the server adapter returns a real monotonically increasing counter.
        newest = 0
        for path in (
            self._db_filepath,
            self._db_filepath.with_name(self._db_filepath.name + "-wal"),
        ):
            try:
                newest = max(newest, path.stat().st_mtime_ns)
            except OSError:
                continue
        return newest

    # --- reads ---------------------------------------------------------------
    def list_assets(
        self, owner: str | None = None, category: str | None = None
    ) -> list[AssetData]:
        if not self._db_filepath.is_file():
            return []
        with self._session() as db:
            return db.get_hda_data(category=category, user_id=owner)

    def asset_available(self, asset_id: int, history_id: int | None = None) -> bool:
        with self._session() as db:
            return db.asset_available(asset_id, history_id)

    def record_use(self, asset_id: int) -> None:
        try:
            with self._session() as db:
                db.update_load_count(asset_id)
        except Exception as error:
            log.warning("Imported asset, but usage could not be recorded: %s", error)

    def categories(self, owner: str | None = None) -> list[str]:
        if not self._db_filepath.is_file():
            return []
        with self._session() as db:
            return db.get_hda_category(user_id=owner) or []

    def histories(
        self, asset_id: int | None, owner: str | None = None, search_date: Any = None
    ) -> list[HistoryData]:
        if not self._db_filepath.is_file():
            return []
        with self._session() as db:
            return db.get_hda_history(
                hda_key_id=asset_id, user_id=owner, search_date=search_date
            )

    def asset_icons(self, owner: str | None = None) -> list[Any]:
        if not self._db_filepath.is_file():
            return []
        with self._session() as db:
            return db.get_icon_info_by_user(user_id=owner) or []

    def history_thumbnails(self, owner: str | None = None) -> list[Any]:
        if not self._db_filepath.is_file():
            return []
        with self._session() as db:
            return db.get_thumbnail_by_hda_history(user_id=owner) or []

    def history_videos(self, asset_id: int) -> list[Path]:
        with self._session() as db:
            return list(db.get_history_video_info(hda_key_id=asset_id) or [])

    def video_matches_version(self, asset_id: int, version: str) -> bool:
        with self._session() as db:
            return bool(
                db.is_video_and_ihda_same_version(hda_key_id=asset_id, version=version)
            )

    def is_latest_history(self, asset_id: int, history_id: int) -> bool:
        with self._session() as db:
            return bool(
                db.is_most_recent_ihda_history(hda_key_id=asset_id, hist_id=history_id)
            )

    def is_latest_version(self, asset_id: int, version: str) -> bool:
        with self._session() as db:
            return bool(
                db.is_ihda_lastest_version(hda_key_id=asset_id, version=version)
            )

    # --- lookups the panel used to make on the facade directly -----------
    def has_asset(self, owner: str, category: str, name: str) -> bool:
        with self._session() as db:
            return bool(
                db.is_exist_hda_name(user_id=owner, category=category, hda_name=name)
            )

    def asset_identity(
        self, owner: str, category: str, name: str
    ) -> tuple[int, str | None, str | None] | None:
        """(asset id, stored node type, current version) for an existing asset."""
        with self._session() as db:
            ids = db.get_hda_key_id(category=category, name=name, user_id=owner)
            if not ids:
                return None
            asset_id = int(ids[0])
            return (
                asset_id,
                db.get_hda_node_type(hda_key_id=asset_id),
                db.get_hda_version(hda_key_id=asset_id),
            )

    def asset_ids(self, owner: str | None = None) -> list[int]:
        with self._session() as db:
            return [int(i) for i in (db.get_hda_key_id(user_id=owner) or [])]

    def asset_names(self, owner: str | None = None) -> list[tuple[int, str]]:
        with self._session() as db:
            rows = db.get_hda_name(user_id=owner, with_id=True) or []
            return [(int(row[0]), str(row[1])) for row in rows]

    def asset_filepath(self, asset_id: int) -> Path | None:
        with self._session() as db:
            path = db.get_hda_filepath(hda_key_id=asset_id)
            return Path(path) if path is not None else None

    def has_history(self, asset_id: int) -> bool:
        with self._session() as db:
            return bool(db.is_exist_hda_history(hda_key_id=asset_id))

    def has_note_history(self, asset_id: int) -> bool:
        with self._session() as db:
            return bool(db.is_exist_hda_note_history(hda_key_id=asset_id))

    def note_history(self, asset_id: int) -> list[Any]:
        with self._session() as db:
            return list(
                db.get_hda_note_history(hda_key_id=asset_id, with_datetime=True) or []
            )

    def history_counts(self) -> tuple[int, int]:
        with self._session() as db:
            return int(db.count_hda_history() or 0), int(
                db.count_hda_note_history() or 0
            )

    def latest_video(self, asset_id: int, version: str) -> Any:
        with self._session() as db:
            return db.get_hda_history_video_most_recent_by_ver(
                hda_key_id=asset_id, version=version
            )

    def record_detail(self, record_id: int) -> Any:
        with self._session() as db:
            return db.get_only_detailview_record_data(record_id=record_id)

    def set_thumbnail(
        self, asset_id: int, directory: Path, filename: str, version: str
    ) -> bool:
        with self._session() as db:
            done = db.update_thumbnail_info(
                hda_key_id=asset_id,
                dirpath=directory,
                filename=filename,
                version=version,
            )
        if done is None:
            raise LibraryError("thumbnail was not updated")
        return bool(done)

    def set_video(
        self, asset_id: int, directory: Path, filename: str, version: str
    ) -> str:
        """Insert or update the preview video row; returns "insert" or "update"."""
        with self._session() as db:
            kind = (
                "update"
                if db.get_video_info(hda_key_id=asset_id) is not None
                else "insert"
            )
            write = db.update_video_info if kind == "update" else db.insert_video_info
            done = write(
                hda_key_id=asset_id,
                dirpath=directory,
                filename=filename,
                version=version,
            )
        if done is None:
            raise LibraryError("video was not stored")
        return kind

    def add_history_row(self, row: Sequence[Any]) -> int:
        """Append one hda_history row (column order of the facade) and return its id."""
        with self._session() as db:
            if db.insert_hda_history(data=list(row)) is None:
                raise LibraryError("history row was not inserted")
            history_id = db.get_last_insert_id
        if history_id is None:
            raise LibraryError("history row has no id")
        return int(history_id)

    def delete_note_history(self, asset_id: int | None = None) -> None:
        with self._session() as db:
            if db.delete_hda_note_history(hda_key_id=asset_id) is None:
                raise LibraryError("note history was not deleted")

    def delete_scene_record(self, record_id: int) -> bool:
        with self._session() as db:
            done = db.delete_hda_record(record_id=record_id)
        if done is None:
            raise LibraryError("scene record was not deleted")
        return bool(done)

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
        with self._session() as db:
            return db.distinct_tags(user_id=owner)

    # --- writes --------------------------------------------------------------
    def register_asset(self, payload: RegistrationPayload) -> RegistrationResult:
        try:
            return self._register_asset(payload)
        except Exception:
            self._discard_registration_files(payload)
            raise

    def add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult:
        try:
            return self._add_version(asset_id, payload)
        except Exception:
            self._discard_registration_files(payload)
            raise

    def _discard_registration_files(self, p: RegistrationPayload) -> None:
        """HOM wrote the HDA and thumbnail before the database write; both are new
        files (names carry the version), so a failed registration removes them."""
        from libs.library_maintenance import references

        try:
            with self._session() as db:
                referenced = {ref.path.resolve() for ref in references(db._connect)}
        except Exception as error:
            # A failed verification cannot prove rollback: retain files and keep
            # the original registration error instead of masking it with cleanup.
            log.warning(
                "Registration files retained; references could not be checked: %s",
                error,
            )
            return
        for path in (
            p.hda_dirpath / p.hda_filename,
            p.thumb_dirpath / p.thumb_filename,
        ):
            if path.resolve() in referenced:
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError as error:
                log.warning(
                    "Could not remove %s after a failed registration: %s", path, error
                )
        for directory in (p.thumb_dirpath, p.hda_dirpath):
            with suppress(OSError):  # only when nothing else lives there
                directory.rmdir()

    def _register_asset(self, payload: RegistrationPayload) -> RegistrationResult:
        p = payload
        thumb_filepath = p.thumb_dirpath / p.thumb_filename
        with self._session() as db:
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
                    if key_id is None:
                        raise sqlite3.DatabaseError("No asset id after insert")
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
                    ok.append(
                        db.insert_thumbnail_info(
                            hda_key_id=key_id,
                            dirpath=p.thumb_dirpath,
                            filename=p.thumb_filename,
                            version=p.version,
                        )
                    )
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
                    history = self._history_row(key_id, p.description, p, None, None)
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

    def _add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult:
        p = payload
        thumb_filepath = p.thumb_dirpath / p.thumb_filename
        with self._session() as db:
            try:
                with db.transaction():
                    if db._connect.execute(
                        "SELECT 1 FROM hda_history WHERE hda_key_id=? AND version=?",
                        (asset_id, p.version),
                    ).fetchone():
                        raise LibraryConflict(
                            "This version already exists, including Trash"
                        )
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
                    before = db.get_update_before_data(hda_key_id=asset_id) or {}
                    video = (before.get("video_dirpath"), before.get("video_filename"))
                    history = self._history_row(
                        asset_id, p.description, p, video[1], video[0]
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
        with self._session() as db:
            if db.is_exist_note(hda_key_id=asset_id):
                done = db.update_note_info(hda_key_id=asset_id, note=note)
            else:
                done = db.insert_note_info(hda_key_id=asset_id, note=note)
        if done != 1:
            raise LibraryError("note was not saved")

    def set_tags(self, asset_id: int, tags: Sequence[str]) -> None:
        with self._session() as db:
            if db.is_exist_tag(hda_key_id=asset_id):
                done = db.update_tag_info(hda_key_id=asset_id, tag_lst=list(tags))
            else:
                done = db.insert_tag_info(hda_key_id=asset_id, tag_lst=list(tags))
        if done != 1:
            raise LibraryError("tags were not saved")

    def toggle_favorite(self, asset_id: int) -> bool:
        with self._session() as db:
            done = db.update_hda_favorite(hda_key_id=asset_id)
        if done is None:
            raise LibraryError("favorite flag was not saved")
        return bool(done)

    def rename_asset(self, plan: RenamePlan) -> tuple[int, int]:
        with self._session() as db:
            return rename_asset(SQLiteRenameRepository(db), plan)

    def delete_asset(self, asset_id: int, directory: Path) -> None:
        with self._session() as db:
            try:
                asset_commands.delete_asset(db, asset_id, directory)
            except RuntimeError as error:
                raise LibraryError(str(error)) from error

    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None:
        with self._session() as db:
            try:
                asset_commands.delete_history(db, asset_id, history_id, list(files))
            except ValueError as error:  # most recent history
                raise LibraryConflict(str(error)) from error
            except RuntimeError as error:
                raise LibraryError(str(error)) from error

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
