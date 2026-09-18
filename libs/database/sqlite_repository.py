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
from dataclasses import asdict
from pathlib import Path
from typing import Any

from libs import asset_commands
from libs.asset_contracts import (
    AssetData,
    AssetIcon,
    AssetIdentity,
    AssetName,
    HistoryCounts,
    HistoryData,
    HistoryThumbnail,
    NodeConnections,
    NoteHistory,
)
from libs.asset_rename import RenameCounts, RenamePlan, rename_asset
from libs.database.lifecycle import PersonalLifecycle
from libs.database.rename_repository import SQLiteRenameRepository
from libs.database.rows import named_query
from libs.history_activity import activity_rows
from libs.library_explorer import search_asset_ids
from libs.operation_journal import durable_operation
from libs.record_codec import decode_record
from libs.repository import (
    LibraryConflict,
    LibraryError,
    LibraryNotFound,
    LibraryUnavailable,
    RegistrationPayload,
    RegistrationResult,
)
from libs.scene_contracts import SceneRecord, SceneRecordInput
from libs.scene_record_cleanup import SceneRecordFiles
from libs.search_limits import SEARCH_RESULT_LIMIT
from libs.sqlite3_db_api import SQLite3DatabaseAPI

log = logging.getLogger(__name__)


def _history_comment(kind: str, description: str) -> str:
    """What happened, then the user's note about it.

    The kind is intrinsic to the operation and the only thing that says whether a
    row added a node or updated one; the description is optional and usually
    empty. Recording only the description left every history row blank.
    """
    return f"NODE ({kind}) {description}".rstrip()


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

    def import_note(self, asset_id: int, version: str | None = None) -> str | None:
        with self._session() as db:
            if version is None:
                return db.get_note_info(asset_id)
            return db.get_hda_note_history_most_recent_by_ver(asset_id, version)

    def import_license(self, asset_id: int, version: str, owner: str) -> str | None:
        with self._session() as db:
            return db.get_hist_hda_license(asset_id, version, owner)

    def node_connections(self, asset_id: int) -> NodeConnections:
        with self._session() as db:
            info_id = db.get_hou_node_info_id(asset_id)
            return NodeConnections(
                inputs=db.get_houdini_node_input_connect_info(info_id),
                outputs=db.get_houdini_node_output_connect_info(info_id),
            )

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

    def asset_icons(self, owner: str | None = None) -> list[AssetIcon]:
        if not self._db_filepath.is_file():
            return []
        with self._session() as db:
            return db.get_icon_info_by_user(user_id=owner) or []

    def history_thumbnails(self, owner: str | None = None) -> list[HistoryThumbnail]:
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
    ) -> AssetIdentity | None:
        """(asset id, stored node type, current version) for an existing asset."""
        with self._session() as db:
            ids = db.get_hda_key_id(category=category, name=name, user_id=owner)
            if not ids:
                return None
            asset_id = int(ids[0])
            return AssetIdentity(
                asset_id=asset_id,
                node_type=db.get_hda_node_type(hda_key_id=asset_id),
                version=db.get_hda_version(hda_key_id=asset_id),
            )

    def asset_ids(self, owner: str | None = None) -> list[int]:
        with self._session() as db:
            return [int(i) for i in (db.get_hda_key_id(user_id=owner) or [])]

    def asset_names(self, owner: str | None = None) -> list[AssetName]:
        with self._session() as db:
            rows = db.get_hda_name(user_id=owner, with_id=True) or []
            return rows

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

    def note_history(self, asset_id: int) -> list[NoteHistory]:
        with self._session() as db:
            return list(db.get_hda_note_history(hda_key_id=asset_id) or [])

    def history_counts(self) -> HistoryCounts:
        with self._session() as db:
            return HistoryCounts(
                versions=int(db.count_hda_history() or 0),
                notes=int(db.count_hda_note_history() or 0),
            )

    def latest_video(self, asset_id: int, version: str) -> Path | None:
        with self._session() as db:
            return db.get_hda_history_video_most_recent_by_ver(
                hda_key_id=asset_id, version=version
            )

    def record_detail(self, record_id: int) -> SceneRecord | None:
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
        with self._session() as db, db.transaction():
            current = db.get_video_info(hda_key_id=asset_id)
            kind = "update" if current is not None else "insert"
            write = db.update_video_info if kind == "update" else db.insert_video_info
            done = write(
                hda_key_id=asset_id,
                dirpath=directory,
                filename=filename,
                version=version,
            )
            if done is not None and current == directory / filename:
                # Re-recording the same version keeps the path, so the audit
                # trigger sees no change; record the replacement ourselves.
                snapshot = {"filename": filename, "dirpath": str(directory)}
                PersonalLifecycle(db._connect).event(
                    asset_id,
                    "video_info.update",
                    {"before": snapshot, "after": snapshot},
                )
        if done is None:
            raise LibraryError("video was not stored")
        return kind

    def activity(self, owner: str | None = None) -> list[HistoryData]:
        """Renames and preview-video changes as non-version rows.

        Read from audit_events, never hda_history: the v6 trigger would turn a
        history row into a version. The actor is the asset owner, matching the
        ``userid`` filter of ``histories``.
        """
        if not self._db_filepath.is_file():
            return []
        with self._session() as db:
            rows = named_query(
                db._connect,
                """SELECT e.operation,e.actor,e.occurred_at,e.request_id,e.changes,
                          k.id AS hda_id,k.name AS org_hda_name,k.category AS node_category
                   FROM audit_events e
                   JOIN asset_identity a ON a.uuid=e.asset_uuid
                   JOIN hda_key k ON k.id=a.asset_id
                   WHERE a.deleted_at IS NULL AND e.actor=:user_id
                     AND e.operation IN ('hda_key.update','video_info.insert','video_info.update')
                   ORDER BY e.occurred_at,e.rowid""",
                {"user_id": owner},
            ).fetchall()
        return activity_rows(dict(row) for row in rows)

    def add_history_row(self, row: HistoryData) -> int:
        """Append a named history record and return its identity."""
        data = row
        with self._session() as db, db.transaction():
            previous = named_query(
                db._connect,
                "SELECT current_version_uuid FROM asset_identity WHERE asset_id=:hda_id",
                {"hda_id": data.hda_id},
            ).fetchone()
            if db.insert_hda_history(data=data) is None:
                raise LibraryError("history row was not inserted")
            history_id = db.get_last_insert_id
            # This API appends activity; only registration selects a current version.
            if previous is not None:
                db._connect.execute(
                    "UPDATE asset_identity SET current_version_uuid=:current_version_uuid WHERE asset_id=:hda_id",
                    {
                        "current_version_uuid": previous["current_version_uuid"],
                        "hda_id": data.hda_id,
                    },
                )
        if history_id is None:
            raise LibraryError("history row has no id")
        return int(history_id)

    def delete_note_history(self, asset_id: int | None = None) -> None:
        with self._session() as db:
            if db.delete_hda_note_history(hda_key_id=asset_id) is None:
                raise LibraryError("note history was not deleted")

    def scene_record_files(self, user: str) -> list[SceneRecordFiles]:
        with self._session() as db:
            return db.get_all_hda_record_fileinfo(user_id=user)

    def scene_records(self) -> tuple[SceneRecord, ...]:
        with self._session() as db:
            return db.get_hda_node_location_record()

    def record_scene_usage(self, record: SceneRecordInput) -> int:
        try:
            with self._session() as db, db.transaction():
                if db.insert_hda_node_location_record(**asdict(record)) is None:
                    raise LibraryError("Scene usage could not be saved")
                # An existing scene entry is updated, so lastrowid is not its identity.
                rows = named_query(
                    db._connect,
                    """SELECT id FROM hda_node_location_record
                    WHERE hda_key_id=:hda_key_id AND hip_filename=:hip_filename AND hip_dirpath=:hip_dirpath
                        AND parent_node_path=:parent_node_path AND node_name=:node_name AND node_version=:node_ver""",
                    {
                        "hda_key_id": record.hda_key_id,
                        "hip_filename": record.hip_filename,
                        "hip_dirpath": record.hip_dirpath.as_posix(),
                        "parent_node_path": record.parent_node_path,
                        "node_name": record.node_name,
                        "node_ver": record.node_ver,
                    },
                ).fetchall()
                if len(rows) != 1:
                    raise LibraryError("Scene usage has no unique identity")
                return int(rows[0]["id"])
        except (sqlite3.Error, ValueError) as error:
            raise LibraryError("Scene usage could not be saved") from error

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
        limit: int = SEARCH_RESULT_LIMIT,
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
        receipt = self._registration_receipt(payload, None)
        if receipt is not None:
            return receipt
        try:
            result = self._register_asset(payload)
            return self._registration_receipt(payload, None) or result
        except Exception:
            if payload.operation_id is None:
                self._discard_registration_files(payload)
            raise

    def add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult:
        receipt = self._registration_receipt(payload, asset_id)
        if receipt is not None:
            return receipt
        try:
            result = self._add_version(asset_id, payload)
            return self._registration_receipt(payload, asset_id) or result
        except Exception:
            if payload.operation_id is None:
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

    @staticmethod
    def _name_conflict(db: SQLite3DatabaseAPI, p: RegistrationPayload) -> str:
        """Why a name cannot be registered; live and trashed assets differ.

        hda_key keeps UNIQUE(name, category, user_id) until a purge, so a name in
        the Trash is taken as well -- the user needs to know which case this is.
        """
        live = db.get_hda_key_id(category=p.cate_name, name=p.node_name, user_id=p.user)
        if live:
            return f"{p.node_name} already exists in {p.cate_name}"
        return (
            f"{p.node_name} is in the Trash; restore or purge it before "
            f"registering it again in {p.cate_name}"
        )

    def _register_asset(self, payload: RegistrationPayload) -> RegistrationResult:
        p = payload
        thumb_filepath = p.thumb_dirpath / p.thumb_filename
        with self._session() as db:
            try:
                with db.transaction():
                    # Inside the transaction so no other writer can register the
                    # same name between this check and the INSERT below.
                    if db.is_exist_hda_name(
                        user_id=p.user, category=p.cate_name, hda_name=p.node_name
                    ):
                        raise LibraryConflict(self._name_conflict(db, p))
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
                    history = self._history_data(
                        key_id, _history_comment("INSERT", p.description), p, None, None
                    )
                    ok.append(db.insert_hda_history(data=history))
                    history_id = db.get_last_insert_id
                    if any(value is None for value in ok):
                        raise sqlite3.DatabaseError("Incomplete asset registration")
                    self._registration_commit(db, p, key_id, history_id, history)
            except sqlite3.Error as error:
                log.error("Asset registration rolled back: %s", error)
                raise LibraryError(f"asset registration failed: {error}") from error
        asset = self._asset_row(
            key_id,
            p,
            is_favorite=0,
            load_count=0,
            ctime=p.registered_at,
            video_filename=None,
            video_dirpath=None,
            note=None,
            tags=[],
        )
        return RegistrationResult(
            asset=asset,
            history=history,
            history_id=int(history_id or 0),
            thumb_filepath=thumb_filepath,
        )

    def _add_version(
        self, asset_id: int, payload: RegistrationPayload
    ) -> RegistrationResult:
        p = payload
        thumb_filepath = p.thumb_dirpath / p.thumb_filename
        with self._session() as db:
            try:
                with db.transaction():
                    if db._connect.execute(
                        "SELECT 1 FROM hda_history WHERE hda_key_id=:asset_id AND version=:version",
                        {"asset_id": asset_id, "version": p.version},
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
                    before = db.get_update_before_data(hda_key_id=asset_id)
                    if before is None:
                        raise LibraryNotFound("Asset disappeared during update")
                    video_dirpath = before.video_dirpath
                    video_filename = before.video_filename
                    history = self._history_data(
                        asset_id,
                        _history_comment("UPDATE", p.description),
                        p,
                        video_filename,
                        video_dirpath,
                    )
                    if db.insert_hda_history(data=history) is None:
                        raise sqlite3.DatabaseError("Could not write asset history")
                    history_id = db.get_last_insert_id
                    self._registration_commit(db, p, asset_id, history_id, history)
            except sqlite3.Error as error:
                log.error("Asset update rolled back: %s", error)
                raise LibraryError(f"asset update failed: {error}") from error
        asset = self._asset_row(
            asset_id,
            p,
            is_favorite=before.is_favorite_hda,
            load_count=before.hda_load_count,
            ctime=before.hda_ctime,
            video_filename=video_filename,
            video_dirpath=video_dirpath,
            note=before.hda_note,
            tags=before.hda_tags,
        )
        return RegistrationResult(
            asset=asset,
            history=history,
            history_id=int(history_id or 0),
            thumb_filepath=thumb_filepath,
        )

    def set_note(self, asset_id: int, note: str) -> None:
        # Existence check and write in one transaction: without it, statements
        # auto-commit and a concurrent writer can make the INSERT collide.
        try:
            with self._session() as db, db.transaction():
                if db.is_exist_note(hda_key_id=asset_id):
                    done = db.update_note_info(hda_key_id=asset_id, note=note)
                else:
                    done = db.insert_note_info(hda_key_id=asset_id, note=note)
        except sqlite3.Error as error:  # e.g. the trigger refusing a trashed asset
            raise LibraryError(f"note was not saved: {error}") from error
        if done != 1:
            raise LibraryError("note was not saved")

    def set_tags(self, asset_id: int, tags: Sequence[str]) -> None:
        try:
            with self._session() as db, db.transaction():
                if db.is_exist_tag(hda_key_id=asset_id):
                    done = db.update_tag_info(hda_key_id=asset_id, tag_lst=list(tags))
                else:
                    done = db.insert_tag_info(hda_key_id=asset_id, tag_lst=list(tags))
        except sqlite3.Error as error:
            raise LibraryError(f"tags were not saved: {error}") from error
        if done != 1:
            raise LibraryError("tags were not saved")

    def toggle_favorite(self, asset_id: int) -> bool:
        with self._session() as db:
            done = db.update_hda_favorite(hda_key_id=asset_id)
        if done is None:
            raise LibraryError("favorite flag was not saved")
        return bool(done)

    def rename_asset(self, plan: RenamePlan) -> RenameCounts:
        with self._session() as db:
            return rename_asset(
                SQLiteRenameRepository(db), plan, operations=durable_operation
            )

    def delete_asset(self, asset_id: int, directory: Path) -> None:
        with self._session() as db:
            try:
                asset_commands.delete_asset(db, asset_id)
            except RuntimeError as error:
                raise LibraryError(str(error)) from error

    def delete_history(
        self, asset_id: int, history_id: int, files: Sequence[Path]
    ) -> None:
        with self._session() as db:
            try:
                asset_commands.delete_history(db, asset_id, history_id)
            except ValueError as error:  # most recent history
                raise LibraryConflict(str(error)) from error
            except RuntimeError as error:
                raise LibraryError(str(error)) from error

    # --- named record builders ----------
    @staticmethod
    def _history_data(
        asset_id: int,
        comment: str,
        p: RegistrationPayload,
        video_filename: Any,
        video_dirpath: Any,
    ) -> HistoryData:
        return decode_record(
            HistoryData,
            {
                "hda_id": asset_id,
                "comment": comment,
                "org_hda_name": p.node_name,
                "version": p.version,
                "ihda_filename": p.hda_filename,
                "ihda_dirpath": p.hda_dirpath,
                "reg_time": p.registered_at,
                "hou_version": p.hou_version,
                "hip_filename": p.hip_filename,
                "hip_dirpath": p.hip_dirpath,
                "hda_license": p.hou_license,
                "os": p.operating_system,
                "node_old_path": p.node_path,
                "node_def_desc": p.def_desc,
                "node_type_name": p.type_name,
                "node_category": p.cate_name,
                "userid": p.user,
                "icon": p.icon_path_lst,
                "thumb_filename": p.thumb_filename,
                "thumb_dirpath": p.thumb_dirpath,
                "video_filename": video_filename,
                "video_dirpath": video_dirpath,
            },
        )

    @staticmethod
    def _asset_row(
        asset_id: int,
        p: RegistrationPayload,
        *,
        is_favorite: Any,
        load_count: Any,
        ctime: Any,
        video_filename: str | None,
        video_dirpath: Path | None,
        note: Any,
        tags: Any,
    ) -> AssetData:
        values = {
            "hda_id": asset_id,
            "hda_name": p.node_name,
            "hda_cate": p.cate_name,
            "hda_version": p.version,
            "hda_filename": p.hda_filename,
            "hda_dirpath": p.hda_dirpath,
            "is_favorite_hda": bool(is_favorite),
            "hda_load_count": load_count,
            "hda_ctime": ctime,
            "hda_mtime": p.registered_at,
            "hou_version": p.hou_version,
            "node_type_name": p.type_name,
            "node_def_desc": p.def_desc,
            "is_network": p.is_network,
            "is_sub_network": p.is_sub_network,
            "node_old_path": p.node_path,
            "hda_license": p.hou_license,
            "hip_filename": p.hip_filename,
            "hip_dirpath": p.hip_dirpath,
            "thumbnail_filename": p.thumb_filename,
            "thumbnail_dirpath": p.thumb_dirpath,
            "video_filename": video_filename,
            "video_dirpath": video_dirpath,
            "hda_note": note,
            "hda_icon": p.icon_path_lst,
            "hda_tags": tags,
        }
        return decode_record(AssetData, values)

    def version_identity(
        self,
        asset_id: int,
        history_id: int | None = None,
        version_uuid: str | None = None,
    ) -> str | None:
        with self._session() as db:
            if version_uuid:
                row = db._connect.execute(
                    "SELECT v.uuid FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE h.hda_key_id=:asset_id AND v.uuid=:version_uuid AND v.deleted_at IS NULL",
                    {"asset_id": asset_id, "version_uuid": version_uuid},
                ).fetchone()
            elif history_id:
                row = db._connect.execute(
                    "SELECT v.uuid FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE h.hda_key_id=:asset_id AND h.id=:history_id AND v.deleted_at IS NULL",
                    {"asset_id": asset_id, "history_id": history_id},
                ).fetchone()
            else:
                row = db._connect.execute(
                    "SELECT current_version_uuid FROM asset_identity WHERE asset_id=:asset_id AND deleted_at IS NULL",
                    {"asset_id": asset_id},
                ).fetchone()
            return row[0] if row else None

    def registration_recovery(self) -> Any:
        from libs.registration_recovery import RegistrationRecovery

        return RegistrationRecovery(self._db_filepath)

    def _registration_receipt(
        self, payload: RegistrationPayload, asset_id: int | None
    ) -> RegistrationResult | None:
        if payload.operation_id is None:
            return None
        from libs.registration_recovery import decode_result, fingerprint

        job = self.registration_recovery().load(payload.operation_id)
        if job is None or job["fingerprint"] != fingerprint(payload, asset_id):
            raise LibraryConflict("Invalid registration receipt")
        return decode_result(job["result"]) if job["phase"] == "committed" else None

    @staticmethod
    def _registration_commit(
        db: SQLite3DatabaseAPI,
        payload: RegistrationPayload,
        asset_id: int,
        history_id: int | None,
        history: HistoryData,
    ) -> None:
        if payload.operation_id is None:
            return
        from libs.library_metadata import utc_now
        from libs.registration_recovery import encode_result

        asset = next(
            row
            for row in db.get_hda_data(user_id=payload.user)
            if row.hda_id == asset_id
        )
        result = RegistrationResult(
            asset=asset,
            history=history,
            history_id=int(history_id or 0),
            thumb_filepath=payload.thumb_dirpath / payload.thumb_filename,
        )
        db._connect.execute(
            "UPDATE registration_jobs SET phase='committed',result=:result,error=NULL,updated_at=:utc_now WHERE id=:operation_id",
            {
                "result": encode_result(result),
                "utc_now": utc_now(),
                "operation_id": payload.operation_id,
            },
        )
