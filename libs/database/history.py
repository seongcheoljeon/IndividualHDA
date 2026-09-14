"""History queries; transactions are owned by the shared session."""

from __future__ import annotations

import collections
import logging
import pathlib
from typing import Any, cast

import public
from libs import log_handler
from libs.database.session import DatabaseSession
from libs.database.values import DatabaseValues
from libs.domain import HistoryData
from libs.path_updates import PathMoves, relocated_path


class HistoryOperations(DatabaseSession):
    def insert_hda_history(self, data: Any = None) -> int | None:
        query = """
        INSERT INTO hda_history
            (hda_key_id, comment, org_hda_name, version, hda_filename, hda_dirpath,
            registration_datetime, houdini_version, hip_filename, hip_dirpath, hda_license, operating_system,
            node_old_path, node_def_desc, node_type_name, node_category, userid, icon,
            thumb_filename, thumb_dirpath, video_filename, video_dirpath)
        VALUES (?, ?, ?, ?, ?, ?,
            (SELECT DATETIME('now', 'localtime')), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        query_params: tuple[Any, ...] = ()
        try:
            hist_key_lst = [
                public.Key.History.hda_id,
                public.Key.History.comment,
                public.Key.History.org_hda_name,
                public.Key.History.version,
                public.Key.History.ihda_filename,
                public.Key.History.ihda_dirpath,
                public.Key.History.reg_time,
                public.Key.History.hou_version,
                public.Key.History.hip_filename,
                public.Key.History.hip_dirpath,
                public.Key.History.hda_license,
                public.Key.History.os,
                public.Key.History.node_old_path,
                public.Key.History.node_def_desc,
                public.Key.History.node_type_name,
                public.Key.History.node_category,
                public.Key.History.userid,
                public.Key.History.icon,
                public.Key.History.thumb_filename,
                public.Key.History.thumb_dirpath,
                public.Key.History.video_filename,
                public.Key.History.video_dirpath,
            ]
            assert len(hist_key_lst) == len(data)
            hist_dat = collections.OrderedDict(zip(hist_key_lst, data))
            del hist_dat[public.Key.History.reg_time]
            hist_dat[public.Key.History.ihda_dirpath] = hist_dat[
                public.Key.History.ihda_dirpath
            ].as_posix()
            hist_dat[public.Key.History.hip_dirpath] = hist_dat[
                public.Key.History.hip_dirpath
            ].as_posix()
            if hist_dat.get(public.Key.History.thumb_dirpath) is not None:
                hist_dat[public.Key.History.thumb_dirpath] = hist_dat[
                    public.Key.History.thumb_dirpath
                ].as_posix()
            if hist_dat.get(public.Key.History.video_dirpath) is not None:
                hist_dat[public.Key.History.video_dirpath] = hist_dat[
                    public.Key.History.video_dirpath
                ].as_posix()
            hist_dat[public.Key.History.icon] = DatabaseValues._make_icon_to_string(
                hist_dat[public.Key.History.icon]
            )
            dat = tuple(hist_dat.values())
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_history (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
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
            rows = self._cursor.execute(
                "SELECT id, hda_dirpath, hda_filename, thumb_dirpath, thumb_filename, video_dirpath, video_filename FROM hda_history WHERE hda_key_id = ?",
                (hda_key_id,),
            ).fetchall()
            updates = []
            for row in rows:
                values: list[str | None] = []
                for directory, filename in zip(row[1::2], row[2::2]):
                    if directory is not None and filename is not None:
                        path = relocated_path(
                            pathlib.Path(directory) / filename, path_moves
                        )
                        values.extend((path.parent.as_posix(), path.name))
                    else:
                        values.extend((directory, filename))
                updates.append((*values, row[0]))
            self._cursor.executemany(
                "UPDATE hda_history SET hda_dirpath=?, hda_filename=?, thumb_dirpath=?, thumb_filename=?, video_dirpath=?, video_filename=? WHERE id=?",
                updates,
            )
            self._commit()
            return len(updates)
        assert isinstance(hda_dirpath, pathlib.Path)
        if video_dirpath is not None:
            query_whole_dirpath = """
            UPDATE hda_history SET hda_dirpath = ?, thumb_dirpath = ?,
            video_dirpath =
            CASE
                WHEN video_dirpath IS NOT NULL
                    THEN ?
                ELSE video_dirpath
            END
            WHERE hda_key_id = ?
            """
            query_whole_dirpath_params: tuple[Any, ...] = (
                hda_dirpath.as_posix(),
                thumb_dirpath.as_posix() if thumb_dirpath is not None else None,
                video_dirpath.as_posix(),
                hda_key_id,
            )
            query_filename_by_ver = """
            UPDATE hda_history SET hda_filename = ?, thumb_filename = ?,
            video_filename =
            CASE
                WHEN video_filename IS NOT NULL
                    THEN ?
                ELSE video_filename
            END
            WHERE hda_key_id = ? AND version = ?
            """
            query_filename_by_ver_params: tuple[Any, ...] = (
                hda_filename,
                thumb_filename,
                video_filename,
                hda_key_id,
                hda_version,
            )
        else:
            query_whole_dirpath = """
            UPDATE hda_history SET hda_dirpath = ?, thumb_dirpath = ? WHERE hda_key_id = ?
            """
            query_whole_dirpath_params = (
                hda_dirpath.as_posix(),
                thumb_dirpath.as_posix() if thumb_dirpath is not None else None,
                hda_key_id,
            )
            query_filename_by_ver = """
            UPDATE hda_history SET hda_filename = ?, thumb_filename = ?
            WHERE hda_key_id = ? AND version = ?
            """
            query_filename_by_ver_params = (
                hda_filename,
                thumb_filename,
                hda_key_id,
                hda_version,
            )
        # most_recent_hist_id = self.get_most_recent_ihda_history_id(
        #     hda_key_id=hda_key_id, hda_version=hda_version)
        # query_comment = '''
        # UPDATE hda_history SET comment = '{0}' WHERE id = {1}
        # '''.format('NAME (CHANGE)', most_recent_hist_id)
        try:
            res_cnt = 0
            dirpath_cursor = self._cursor.execute(
                query_whole_dirpath, query_whole_dirpath_params
            )
            filename_cursor = self._cursor.execute(
                query_filename_by_ver, query_filename_by_ver_params
            )
            # comment_cursor = self._cursor.execute(query_comment, query_comment_params)
            self._commit()
            # res_cnt += (dirpath_cursor.rowcount + filename_cursor.rowcount + comment_cursor.rowcount)
            res_cnt += dirpath_cursor.rowcount + filename_cursor.rowcount
            return res_cnt
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_name_to_history (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def is_library_file_referenced(
        self, path: pathlib.Path, excluding_history_id: int
    ) -> bool:
        """Check surviving current/history references inside the delete transaction."""
        rows = self._cursor.execute(
            """SELECT dirpath, filename FROM hda_info WHERE filename = ? COLLATE NOCASE
            UNION ALL SELECT dirpath, filename FROM thumbnail_info WHERE filename = ? COLLATE NOCASE
            UNION ALL SELECT dirpath, filename FROM video_info WHERE filename = ? COLLATE NOCASE
            UNION ALL SELECT hda_dirpath, hda_filename FROM hda_history WHERE id != ? AND hda_filename = ? COLLATE NOCASE
            UNION ALL SELECT thumb_dirpath, thumb_filename FROM hda_history WHERE id != ? AND thumb_filename = ? COLLATE NOCASE
            UNION ALL SELECT video_dirpath, video_filename FROM hda_history WHERE id != ? AND video_filename = ? COLLATE NOCASE""",
            (
                path.name,
                path.name,
                path.name,
                excluding_history_id,
                path.name,
                excluding_history_id,
                path.name,
                excluding_history_id,
                path.name,
            ),
        )
        target = path.resolve()
        return any(
            directory is not None
            and (pathlib.Path(directory) / filename).resolve() == target
            for directory, filename in rows
        )

    def delete_hda_history(
        self, hda_key_id: int | None = None, hist_id: int | None = None
    ) -> int | None:
        if (hda_key_id is None) and (hist_id is None):
            query = """DELETE FROM hda_history"""
            query_params: tuple[Any, ...] = ()
        elif (hda_key_id is not None) and (hist_id is None):
            query = """
            DELETE FROM hda_history WHERE hda_key_id = ?
            """
            query_params = (hda_key_id,)
        elif (hda_key_id is None) and (hist_id is not None):
            query = """
                DELETE FROM hda_history WHERE id = ?
                """
            query_params = (hist_id,)
        else:
            query = """
            DELETE FROM hda_history WHERE hda_key_id = ? AND id = ?
            """
            query_params = (hda_key_id, hist_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_history (delete) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_hda_note_history(self, hda_key_id: int | None = None) -> int | None:
        if hda_key_id is None:
            query = """DELETE FROM hda_note_history"""
            query_params: tuple[Any, ...] = ()
        else:
            query = "DELETE FROM hda_note_history WHERE hda_key_id = ?"
            query_params = (hda_key_id,)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_note_history (delete) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def is_exist_hda_history(self, hda_key_id: int | None = None) -> bool:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_history"""
            query_params: tuple[Any, ...] = ()
        else:
            query = """SELECT COUNT(*) FROM hda_history WHERE hda_key_id = ?
            """
            query_params = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_exist_hda_note_history(self, hda_key_id: int | None = None) -> bool:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_note_history"""
            query_params: tuple[Any, ...] = ()
        else:
            query = """SELECT COUNT(*) FROM hda_note_history WHERE hda_key_id = ?
            """
            query_params = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_most_recent_ihda_history(
        self, hda_key_id: int | None = None, hist_id: int | None = None
    ) -> bool:
        query = """SELECT MAX(id) FROM hda_history WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat == hist_id

    def get_most_recent_ihda_history_id(
        self, hda_key_id: int | None = None, hda_version: str | None = None
    ) -> int | None:
        query = """SELECT MAX(id) FROM hda_history WHERE hda_key_id = ? AND version = ?
        """
        query_params: tuple[Any, ...] = (hda_key_id, hda_version)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def count_hda_history(self, hda_key_id: int | None = None) -> int:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_history"""
            query_params: tuple[Any, ...] = ()
        else:
            query = """SELECT COUNT(*) FROM hda_history WHERE hda_key_id = ?
            """
            query_params = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def count_hda_note_history(self, hda_key_id: int | None = None) -> int:
        if hda_key_id is None:
            query = """SELECT COUNT(*) FROM hda_note_history"""
            query_params: tuple[Any, ...] = ()
        else:
            query = """SELECT COUNT(*) FROM hda_note_history WHERE hda_key_id = ?
            """
            query_params = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_all_hda_history_fileinfo(
        self, user_id: str | None = None
    ) -> list[tuple[Any, ...]]:
        query = """
        SELECT id, hda_key_id, hda_dirpath, hda_filename FROM hda_history WHERE userid = ?
        """
        query_params: tuple[Any, ...] = (user_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        return fetch_dat

    def get_hist_hda_license(
        self,
        hda_key_id: int | None = None,
        version: str | None = None,
        user_id: str | None = None,
    ) -> str | None:
        query = """
        SELECT hda_license FROM hda_history WHERE hda_key_id = ? AND version = ? AND userid = ?
        """
        query_params: tuple[Any, ...] = (hda_key_id, version, user_id)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_history_video_info(self, hda_key_id: int | None = None) -> None | list[Any]:
        query = """
        SELECT dirpath, filename FROM video_info WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if fetch_dat is None:
            return None
        dat = list()
        for video_info in fetch_dat:
            dat.append(pathlib.Path(video_info[0]) / video_info[1])
        return dat

    def get_thumbnail_by_hda_history(self, user_id: str | None = None) -> list[Any]:
        query = """
        SELECT id, thumb_dirpath, thumb_filename FROM hda_history WHERE userid = ? ORDER BY id
        """
        query_params: tuple[Any, ...] = (user_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        dat = list()
        key_lst = [
            public.Key.History.hist_id,
            public.Key.History.thumb_dirpath,
            public.Key.History.thumb_filename,
        ]
        for row_val in fetch_dat:
            tmp_dict = dict(zip(key_lst, row_val))
            tmp_dict[public.Key.History.thumb_dirpath] = pathlib.Path(
                tmp_dict[public.Key.History.thumb_dirpath]
            )
            dat.append(tmp_dict)
        return dat

    def get_hda_history(
        self,
        hda_key_id: int | None = None,
        user_id: str | None = None,
        search_date: Any = None,
    ) -> list[HistoryData]:
        if hda_key_id is not None:
            query = """
            SELECT id, hda_key_id, comment, org_hda_name, version, hda_filename, hda_dirpath,
                registration_datetime, houdini_version, hip_filename, hip_dirpath, hda_license,
                operating_system, node_old_path, node_def_desc, node_type_name, node_category, userid, icon,
                (SELECT tag FROM tag_info WHERE hda_key_id = hda_history.hda_key_id),
                thumb_filename, thumb_dirpath, video_filename, video_dirpath
            FROM hda_history WHERE hda_key_id = ? AND userid = ?
            """
            query_params: tuple[Any, ...] = (hda_key_id, user_id)
        else:
            query = """
            SELECT id, hda_key_id, comment, org_hda_name, version, hda_filename, hda_dirpath,
                registration_datetime, houdini_version, hip_filename, hip_dirpath, hda_license,
                operating_system, node_old_path, node_def_desc, node_type_name, node_category, userid, icon,
                (SELECT tag FROM tag_info WHERE hda_key_id = hda_history.hda_key_id),
                thumb_filename, thumb_dirpath, video_filename, video_dirpath
            FROM hda_history WHERE userid = ?
            """
            query_params = (user_id,)
        if search_date is not None:
            query = (
                query
                + " AND registration_datetime BETWEEN "
                + "?"
                + " AND "
                + "?"
                + "\n            "
            )
            query_params = query_params + (search_date[0], search_date[1])
        query = query + " ORDER BY id"
        query_params = query_params + ()
        cursor = self._cursor.execute(query, query_params)
        key_lst = DatabaseValues.hda_history_key_lst()
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        dat = list()
        for row_val in fetch_dat:
            tmp_dict = dict(zip(key_lst, row_val))
            tags = tmp_dict[public.Key.History.tags]
            if tags is None:
                tmp_dict[public.Key.History.tags] = list()
            else:
                tmp_dict[public.Key.History.tags] = tags.split("#")
            tmp_dict[public.Key.History.icon] = tmp_dict[public.Key.History.icon].split(
                ","
            )
            tmp_dict[public.Key.History.ihda_dirpath] = pathlib.Path(
                tmp_dict[public.Key.History.ihda_dirpath]
            )
            tmp_dict[public.Key.History.hip_dirpath] = pathlib.Path(
                tmp_dict[public.Key.History.hip_dirpath]
            )
            tmp_dict[public.Key.History.thumb_dirpath] = pathlib.Path(
                tmp_dict[public.Key.History.thumb_dirpath]
            )
            if tmp_dict[public.Key.History.video_dirpath] is not None:
                tmp_dict[public.Key.History.video_dirpath] = pathlib.Path(
                    tmp_dict[public.Key.History.video_dirpath]
                )
            dat.append(cast(HistoryData, tmp_dict))
        return dat

    def get_hda_history_columns(self) -> list[Any]:
        query = """ SELECT * FROM hda_history"""
        query_params: tuple[Any, ...] = ()
        cursor = self._cursor.execute(query, query_params)
        columns = [x[0] for x in cursor.description]
        return columns

    def get_hda_history_id(self, hda_key_id: int | None = None) -> list[Any]:
        if hda_key_id is None:
            query = """SELECT id FROM hda_history"""
            query_params: tuple[Any, ...] = ()
        else:
            query = "SELECT id FROM hda_history WHERE hda_key_id = ?"
            query_params = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return list()
        return [x[0] for x in dat]

    def get_hda_note_history(
        self, hda_key_id: int | None = None, with_datetime: bool = False
    ) -> list[tuple[Any, ...]] | None:
        if with_datetime:
            query = """
            SELECT registration_datetime, hda_version, note FROM hda_note_history
            WHERE hda_key_id = ?"""
            query_params: tuple[Any, ...] = (hda_key_id,)
        else:
            query = "SELECT note FROM hda_note_history WHERE hda_key_id = ?"
            query_params = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return None
        return dat

    def get_hda_history_video_most_recent_by_ver(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> None | list[Any]:
        query_most_recent_id = """
        SELECT MAX(id) FROM hda_history WHERE hda_key_id = ? AND version = ?
        """
        query_most_recent_id_params = (hda_key_id, version)
        cursor = self._cursor.execute(query_most_recent_id, query_most_recent_id_params)
        most_recent_id = cursor.fetchone()[0]
        if most_recent_id is None:
            return None
        query = """SELECT video_dirpath, video_filename FROM hda_history
        WHERE id = ?"""
        query_params: tuple[Any, ...] = (most_recent_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()
        if (dat is None) or (not len(dat)):
            return None
        if any(map(lambda x: x is None, dat)):
            return None
        # dirpath
        dat = list(dat)
        dat[0] = pathlib.Path(dat[0])
        return dat

    def get_hda_note_history_most_recent_by_ver(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> str | None:
        query_most_recent_id = """
        SELECT MAX(id) FROM hda_note_history WHERE hda_key_id = ? AND hda_version = ?
        """
        query_most_recent_id_params = (hda_key_id, version)
        cursor = self._cursor.execute(query_most_recent_id, query_most_recent_id_params)
        most_recent_id = cursor.fetchone()[0]
        if most_recent_id is None:
            return None
        query = "SELECT note FROM hda_note_history WHERE id = ?"
        query_params: tuple[Any, ...] = (most_recent_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        if (dat is None) or (not len(dat)):
            return None
        return dat
