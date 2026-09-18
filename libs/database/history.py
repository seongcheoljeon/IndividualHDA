"""History queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
import pathlib
from dataclasses import asdict
from typing import Any

from libs.asset_contracts import HistoryData, HistoryThumbnail, NoteHistory
from libs.database.rows import (
    LIVE_ASSET_IDS,
    LIVE_HISTORY_IDS,
    history_record,
    named_query,
)
from libs.database.session import DatabaseSession
from libs.database.values import DatabaseValues
from libs.keys import Key
from libs.path_updates import PathMoves, relocated_path
from libs.record_codec import decode_record


class HistoryOperations(DatabaseSession):
    def insert_hda_history(self, data: HistoryData) -> int | None:
        query = """
        INSERT INTO hda_history
            (hda_key_id, comment, org_hda_name, version, hda_filename, hda_dirpath,
            registration_datetime, houdini_version, hip_filename, hip_dirpath, hda_license, operating_system,
            node_old_path, node_def_desc, node_type_name, node_category, userid, icon,
            thumb_filename, thumb_dirpath, video_filename, video_dirpath)
        VALUES (:hda_id, :comment, :org_hda_name, :version, :ihda_filename, :ihda_dirpath,
            (SELECT DATETIME('now', 'localtime')), :hou_version, :hip_filename, :hip_dirpath,
            :hda_license, :os, :node_old_path, :node_def_desc, :node_type_name, :node_category,
            :userid, :icon, :thumb_filename, :thumb_dirpath, :video_filename, :video_dirpath)
        """
        try:
            hist_dat: dict[str, Any] = asdict(data)
            del hist_dat[Key.History.reg_time]
            hist_dat[Key.History.ihda_dirpath] = hist_dat[
                Key.History.ihda_dirpath
            ].as_posix()
            hist_dat[Key.History.hip_dirpath] = hist_dat[
                Key.History.hip_dirpath
            ].as_posix()
            if hist_dat.get(Key.History.thumb_dirpath) is not None:
                hist_dat[Key.History.thumb_dirpath] = hist_dat[
                    Key.History.thumb_dirpath
                ].as_posix()
            if hist_dat.get(Key.History.video_dirpath) is not None:
                hist_dat[Key.History.video_dirpath] = hist_dat[
                    Key.History.video_dirpath
                ].as_posix()
            hist_dat[Key.History.icon] = DatabaseValues._make_icon_to_string(
                hist_dat[Key.History.icon]
            )
            cursor = self._cursor.execute(query, hist_dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** hda_history (insert) ***")
            logging.error(err)
            return None

    def update_hda_name_to_history(
        self,
        hda_key_id: int | None = None,
        hda_version: str | None = None,
        hda_filename: str | None = None,
        hda_dirpath: pathlib.Path | None = None,
        thumb_dirpath: pathlib.Path | None = None,
        thumb_filename: Any = None,
        video_dirpath: pathlib.Path | None = None,
        video_filename: str | None = None,
        path_moves: PathMoves | None = None,
    ) -> int | None:
        if path_moves is not None:
            rows = named_query(
                self._connect,
                "SELECT id, hda_dirpath, hda_filename, thumb_dirpath, thumb_filename, video_dirpath, video_filename FROM hda_history WHERE hda_key_id = :hda_key_id",
                {"hda_key_id": hda_key_id},
            ).fetchall()
            updates = []
            for row in rows:
                values: dict[str, Any] = {"id": row["id"]}
                for directory_key, filename_key in (
                    ("hda_dirpath", "hda_filename"),
                    ("thumb_dirpath", "thumb_filename"),
                    ("video_dirpath", "video_filename"),
                ):
                    directory, filename = row[directory_key], row[filename_key]
                    if directory is not None and filename is not None:
                        path = relocated_path(
                            pathlib.Path(directory) / filename, path_moves
                        )
                        values[directory_key] = path.parent.as_posix()
                        values[filename_key] = path.name
                    else:
                        values[directory_key] = directory
                        values[filename_key] = filename
                updates.append(values)
            self._cursor.executemany(
                "UPDATE hda_history SET hda_dirpath=:hda_dirpath, hda_filename=:hda_filename, thumb_dirpath=:thumb_dirpath, thumb_filename=:thumb_filename, video_dirpath=:video_dirpath, video_filename=:video_filename WHERE id=:id",
                updates,
            )
            self._commit()
            return len(updates)
        assert isinstance(hda_dirpath, pathlib.Path)
        if video_dirpath is not None:
            query_whole_dirpath = """
            UPDATE hda_history SET hda_dirpath = :hda_dirpath, thumb_dirpath = :value,
            video_dirpath =
            CASE
                WHEN video_dirpath IS NOT NULL
                    THEN :video_dirpath
                ELSE video_dirpath
            END
            WHERE hda_key_id = :hda_key_id
            """
            query_whole_dirpath_params: dict[str, Any] = {
                "hda_dirpath": hda_dirpath.as_posix(),
                "value": thumb_dirpath.as_posix()
                if thumb_dirpath is not None
                else None,
                "video_dirpath": video_dirpath.as_posix(),
                "hda_key_id": hda_key_id,
            }
            query_filename_by_ver = """
            UPDATE hda_history SET hda_filename = :hda_filename, thumb_filename = :thumb_filename,
            video_filename =
            CASE
                WHEN video_filename IS NOT NULL
                    THEN :video_filename
                ELSE video_filename
            END
            WHERE hda_key_id = :hda_key_id AND version = :hda_version
            """
            query_filename_by_ver_params: dict[str, Any] = {
                "hda_filename": hda_filename,
                "thumb_filename": thumb_filename,
                "video_filename": video_filename,
                "hda_key_id": hda_key_id,
                "hda_version": hda_version,
            }
        else:
            query_whole_dirpath = """
            UPDATE hda_history SET hda_dirpath = :hda_dirpath, thumb_dirpath = :value WHERE hda_key_id = :hda_key_id
            """
            query_whole_dirpath_params = {
                "hda_dirpath": hda_dirpath.as_posix(),
                "value": thumb_dirpath.as_posix()
                if thumb_dirpath is not None
                else None,
                "hda_key_id": hda_key_id,
            }
            query_filename_by_ver = """
            UPDATE hda_history SET hda_filename = :hda_filename, thumb_filename = :thumb_filename
            WHERE hda_key_id = :hda_key_id AND version = :hda_version
            """
            query_filename_by_ver_params = {
                "hda_filename": hda_filename,
                "thumb_filename": thumb_filename,
                "hda_key_id": hda_key_id,
                "hda_version": hda_version,
            }
        # most_recent_hist_id = self.get_most_recent_ihda_history_id(
        #     hda_key_id=hda_key_id, hda_version=hda_version)
        # query_comment = '''
        # UPDATE hda_history SET comment = '{0}' WHERE id = {1}
        # '''.format('NAME (CHANGE)', most_recent_hist_id)
        try:
            with self.transaction():
                res_cnt = 0
                dirpath_cursor = self._cursor.execute(
                    query_whole_dirpath, query_whole_dirpath_params
                )
                filename_cursor = self._cursor.execute(
                    query_filename_by_ver, query_filename_by_ver_params
                )
                # comment_cursor = self._cursor.execute(query_comment, query_comment_params)
            # res_cnt += (dirpath_cursor.rowcount + filename_cursor.rowcount + comment_cursor.rowcount)
            res_cnt += dirpath_cursor.rowcount + filename_cursor.rowcount
            return res_cnt
        except Exception as err:
            logging.error("*** hda_name_to_history (update) ***")
            logging.error(err)
            return None

    def delete_hda_note_history(self, hda_key_id: int | None = None) -> int | None:
        if hda_key_id is None:
            query = """DELETE FROM hda_note_history"""
            query_params: dict[str, Any] = {}
        else:
            query = "DELETE FROM hda_note_history WHERE hda_key_id = :hda_key_id"
            query_params = {"hda_key_id": hda_key_id}
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** hda_note_history (delete) ***")
            logging.error(err)
            return None

    def is_exist_hda_history(self, hda_key_id: int | None = None) -> bool:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_history"""
            query_params: dict[str, Any] = {}
        else:
            query = """SELECT COUNT(*) FROM hda_history WHERE hda_key_id = :hda_key_id
            """
            query_params = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_exist_hda_note_history(self, hda_key_id: int | None = None) -> bool:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_note_history"""
            query_params: dict[str, Any] = {}
        else:
            query = """SELECT COUNT(*) FROM hda_note_history WHERE hda_key_id = :hda_key_id
            """
            query_params = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_most_recent_ihda_history(
        self, hda_key_id: int | None = None, hist_id: int | None = None
    ) -> bool:
        query = """SELECT MAX(id) FROM hda_history WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat == hist_id

    def get_most_recent_ihda_history_id(
        self, hda_key_id: int | None = None, hda_version: str | None = None
    ) -> int | None:
        query = """SELECT MAX(id) FROM hda_history WHERE hda_key_id = :hda_key_id AND version = :hda_version
        """
        query_params: dict[str, Any] = {
            "hda_key_id": hda_key_id,
            "hda_version": hda_version,
        }
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def count_hda_history(self, hda_key_id: int | None = None) -> int:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_history"""
            query_params: dict[str, Any] = {}
        else:
            query = """SELECT COUNT(*) FROM hda_history WHERE hda_key_id = :hda_key_id
            """
            query_params = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def count_hda_note_history(self, hda_key_id: int | None = None) -> int:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_note_history"""
            query_params: dict[str, Any] = {}
        else:
            query = """SELECT COUNT(*) FROM hda_note_history WHERE hda_key_id = :hda_key_id
            """
            query_params = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_hist_hda_license(
        self,
        hda_key_id: int | None = None,
        version: str | None = None,
        user_id: str | None = None,
    ) -> str | None:
        query = """
        SELECT hda_license FROM hda_history WHERE hda_key_id = :hda_key_id AND version = :version AND userid = :user_id
        """
        query_params: dict[str, Any] = {
            "hda_key_id": hda_key_id,
            "version": version,
            "user_id": user_id,
        }
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_history_video_info(self, hda_key_id: int | None = None) -> None | list[Any]:
        query = """
        SELECT dirpath, filename FROM video_info WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchall()
        if fetch_dat is None:
            return None
        dat = []
        for video_info in fetch_dat:
            dat.append(pathlib.Path(video_info["dirpath"]) / video_info["filename"])
        return dat

    def get_thumbnail_by_hda_history(
        self, user_id: str | None = None
    ) -> list[HistoryThumbnail]:
        query = f"""
        SELECT id AS hist_id,
            thumb_dirpath AS thumb_dirpath,
            thumb_filename AS thumb_filename
        FROM hda_history
        WHERE id {LIVE_HISTORY_IDS} AND hda_key_id {LIVE_ASSET_IDS} AND userid = :user_id
        ORDER BY id
        """
        query_params: dict[str, Any] = {"user_id": user_id}
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return []
        return [decode_record(HistoryThumbnail, dict(row)) for row in fetch_dat]

    def get_hda_history(
        self,
        hda_key_id: int | None = None,
        user_id: str | None = None,
        search_date: Any = None,
    ) -> list[HistoryData]:
        if hda_key_id is not None:
            query = """
            SELECT id AS hist_id,
            hda_key_id AS hda_id,
            comment AS comment,
            org_hda_name AS org_hda_name,
            version AS version,
            hda_filename AS ihda_filename,
            hda_dirpath AS ihda_dirpath,
            registration_datetime AS reg_time,
            houdini_version AS hou_version,
            hip_filename AS hip_filename,
            hip_dirpath AS hip_dirpath,
            hda_license AS hda_license,
            operating_system AS os,
            node_old_path AS node_old_path,
            node_def_desc AS node_def_desc,
            node_type_name AS node_type_name,
            node_category AS node_category,
            userid AS userid,
            icon AS icon,
            (SELECT tag FROM tag_info WHERE hda_key_id = hda_history.hda_key_id) AS tags,
            thumb_filename AS thumb_filename,
            thumb_dirpath AS thumb_dirpath,
            video_filename AS video_filename,
            video_dirpath AS video_dirpath
        FROM hda_history WHERE id IN (SELECT history_id FROM version_identity WHERE deleted_at IS NULL) AND hda_key_id IN (SELECT asset_id FROM asset_identity WHERE deleted_at IS NULL) AND hda_key_id = :hda_key_id AND userid = :user_id
            """
            query_params: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "user_id": user_id,
            }
        else:
            query = """
            SELECT id AS hist_id,
            hda_key_id AS hda_id,
            comment AS comment,
            org_hda_name AS org_hda_name,
            version AS version,
            hda_filename AS ihda_filename,
            hda_dirpath AS ihda_dirpath,
            registration_datetime AS reg_time,
            houdini_version AS hou_version,
            hip_filename AS hip_filename,
            hip_dirpath AS hip_dirpath,
            hda_license AS hda_license,
            operating_system AS os,
            node_old_path AS node_old_path,
            node_def_desc AS node_def_desc,
            node_type_name AS node_type_name,
            node_category AS node_category,
            userid AS userid,
            icon AS icon,
            (SELECT tag FROM tag_info WHERE hda_key_id = hda_history.hda_key_id) AS tags,
            thumb_filename AS thumb_filename,
            thumb_dirpath AS thumb_dirpath,
            video_filename AS video_filename,
            video_dirpath AS video_dirpath
        FROM hda_history WHERE id IN (SELECT history_id FROM version_identity WHERE deleted_at IS NULL) AND hda_key_id IN (SELECT asset_id FROM asset_identity WHERE deleted_at IS NULL) AND userid = :user_id
            """
            query_params = {"user_id": user_id}
        if search_date is not None:
            query += " AND registration_datetime BETWEEN :start_date AND :end_date"
            query_params.update(start_date=search_date[0], end_date=search_date[1])
        query = query + " ORDER BY id"
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return []
        dat = []
        for row_val in fetch_dat:
            tmp_dict = dict(row_val)
            dat.append(history_record(tmp_dict))
        return dat

    def get_hda_note_history(self, hda_key_id: int | None = None) -> list[NoteHistory]:
        query = """SELECT registration_datetime AS registered_at, hda_version AS version, note
            FROM hda_note_history WHERE hda_key_id=:hda_key_id ORDER BY id"""
        return [
            NoteHistory(**dict(row))
            for row in named_query(self._connect, query, {"hda_key_id": hda_key_id})
        ]

    def get_hda_history_video_most_recent_by_ver(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> pathlib.Path | None:
        query_most_recent_id = """
        SELECT MAX(id) FROM hda_history WHERE hda_key_id = :hda_key_id AND version = :version
        """
        query_most_recent_id_params = {"hda_key_id": hda_key_id, "version": version}
        cursor = self._cursor.execute(query_most_recent_id, query_most_recent_id_params)
        most_recent_id = cursor.fetchone()[0]
        if most_recent_id is None:
            return None
        query = """SELECT video_dirpath, video_filename FROM hda_history
        WHERE id = :most_recent_id"""
        query_params: dict[str, Any] = {"most_recent_id": most_recent_id}
        cursor = named_query(self._connect, query, query_params)
        dat = cursor.fetchone()
        if (dat is None) or (not len(dat)):
            return None
        if any(x is None for x in dat):
            return None
        # dirpath
        return pathlib.Path(dat["video_dirpath"]) / dat["video_filename"]

    def get_hda_note_history_most_recent_by_ver(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> str | None:
        query_most_recent_id = """
        SELECT MAX(id) FROM hda_note_history WHERE hda_key_id = :hda_key_id AND hda_version = :version
        """
        query_most_recent_id_params = {"hda_key_id": hda_key_id, "version": version}
        cursor = self._cursor.execute(query_most_recent_id, query_most_recent_id_params)
        most_recent_id = cursor.fetchone()[0]
        if most_recent_id is None:
            return None
        query = "SELECT note FROM hda_note_history WHERE id = :most_recent_id"
        query_params: dict[str, Any] = {"most_recent_id": most_recent_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        if (dat is None) or (not len(dat)):
            return None
        return dat
