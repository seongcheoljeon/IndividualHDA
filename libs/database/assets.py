"""Assets queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Sequence
from typing import Any, cast

from libs import log_handler
from libs.database.session import DatabaseSession
from libs.database.values import DatabaseValues, normalize_tags
from libs.domain import AssetData
from libs.keys import Key, Type


class AssetsOperations(DatabaseSession):
    def asset_available(self, asset_id: int, history_id: int | None = None) -> bool:
        if (
            self._connect.execute(
                "SELECT 1 FROM asset_identity WHERE asset_id=? AND deleted_at IS NULL",
                (asset_id,),
            ).fetchone()
            is None
        ):
            return False
        return (
            history_id is None
            or self._connect.execute(
                """SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id
            WHERE h.id=? AND h.hda_key_id=? AND v.deleted_at IS NULL""",
                (history_id, asset_id),
            ).fetchone()
            is not None
        )

    def insert_hda_info(
        self,
        hda_key_id: int | None = None,
        version: str | None = None,
        is_favorite: bool = False,
        load_count: int = 0,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """
        INSERT INTO hda_info
            (hda_key_id, version, is_favorite, load_count, filename, dirpath,
            initial_registration_datetime, modified_registration_datetime)
        VALUES (?, ?, ?, ?, ?, ?, (SELECT DATETIME('now', 'localtime')), (SELECT DATETIME('now', 'localtime')))
        """
        try:
            dat: tuple[Any, ...] = (
                hda_key_id,
                version,
                is_favorite,
                load_count,
                filename,
                dirpath.as_posix(),
            )
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_icon_info(
        self, hda_key_id: int | None = None, icon_lst: Sequence[str] = ()
    ) -> int | None:
        if not icon_lst:
            return None
        query = """INSERT INTO icon_info (hda_key_id, icon) VALUES (?, ?)"""
        try:
            dat: tuple[Any, ...] = (
                hda_key_id,
                DatabaseValues._make_icon_to_string(icon_lst=icon_lst),
            )
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** icon_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_tag_info(
        self, hda_key_id: int | None = None, tag_lst: list[str] | None = None
    ) -> int | None:
        if tag_lst is None:
            return None
        query = """INSERT INTO tag_info (hda_key_id, tag) VALUES (?, ?)"""
        try:
            dat: tuple[Any, ...] = (
                hda_key_id,
                DatabaseValues._make_tag_to_string(tag_lst=tag_lst) or "",
            )
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** tag_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hipfile_info(
        self,
        hda_key_id: int | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
        houdini_version: str | None = None,
        hda_license: str | None = None,
        operating_system: str | None = None,
        sf: float | None = None,
        ef: float | None = None,
        fps: float | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """
        INSERT INTO hipfile_info
        (hda_key_id, filename, dirpath, houdini_version, hda_license, operating_system, sf, ef, fps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            dat: tuple[Any, ...] = (
                hda_key_id,
                filename,
                dirpath.as_posix(),
                houdini_version,
                hda_license,
                operating_system,
                sf,
                ef,
                fps,
            )
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hipfile_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_video_info(
        self,
        hda_key_id: int | None = None,
        dirpath: pathlib.Path | None = None,
        filename: str | None = None,
        version: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """INSERT INTO video_info (hda_key_id, filename, dirpath, version)
        VALUES (?, ?, ?, ?)"""
        try:
            dat: tuple[Any, ...] = (hda_key_id, filename, dirpath.as_posix(), version)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** video_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_thumbnail_info(
        self,
        hda_key_id: int | None = None,
        dirpath: pathlib.Path | None = None,
        filename: str | None = None,
        version: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """INSERT INTO thumbnail_info (hda_key_id, filename, dirpath, version)
        VALUES (?, ?, ?, ?)"""
        try:
            dat: tuple[Any, ...] = (hda_key_id, filename, dirpath.as_posix(), version)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** thumbnail_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_note_info(
        self, hda_key_id: int | None = None, note: str | None = None
    ) -> int | None:
        query = """INSERT INTO note_info (hda_key_id, note) VALUES (?, ?)"""
        try:
            dat: tuple[Any, ...] = (hda_key_id, note)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** note_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_hda_info(
        self,
        hda_key_id: int | None = None,
        version: str | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """
        UPDATE hda_info SET version = ?, filename = ?, dirpath = ?,
        modified_registration_datetime = (SELECT DATETIME('now', 'localtime')) WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (
            version,
            filename,
            dirpath.as_posix(),
            hda_key_id,
        )
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_hda_name(
        self,
        hda_key_id: int | None = None,
        name: str | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
        node_old_path: str | None = None,
        thumbnail_dirpath: pathlib.Path | None = None,
        thumbnail_filename: str | None = None,
        video_dirpath: pathlib.Path | None = None,
        video_filename: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query_hda_key = "UPDATE hda_key SET name = ? WHERE id = ?"
        query_hda_key_params = (name, hda_key_id)
        query_hda_info = """
        UPDATE hda_info SET filename = ?, dirpath = ?,
        modified_registration_datetime = (SELECT DATETIME('now', 'localtime')) WHERE hda_key_id = ?
        """
        query_hda_info_params = (filename, dirpath.as_posix(), hda_key_id)
        query_hou_node_info = """
        UPDATE houdini_node_info SET node_old_path = ? WHERE hda_key_id = ?
        """
        query_hou_node_info_params = (node_old_path, hda_key_id)
        query_thumb_info = None
        query_video_info = None
        if thumbnail_dirpath is not None:
            assert isinstance(thumbnail_dirpath, pathlib.Path)
            query_thumb_info = """
            UPDATE thumbnail_info SET dirpath = ?, filename = ? WHERE hda_key_id = ?
            """
            query_thumb_info_params = (
                thumbnail_dirpath.as_posix(),
                thumbnail_filename,
                hda_key_id,
            )
        if video_dirpath is not None:
            assert isinstance(video_dirpath, pathlib.Path)
            query_video_info = """
            UPDATE video_info SET dirpath = ?, filename = ? WHERE hda_key_id = ?
            """
            query_video_info_params = (
                video_dirpath.as_posix(),
                video_filename,
                hda_key_id,
            )
        try:
            res_cnt = 0
            cursor_hda_key = self._cursor.execute(query_hda_key, query_hda_key_params)
            cursor_hda_info = self._cursor.execute(
                query_hda_info, query_hda_info_params
            )
            cursor_hou_node_info = self._cursor.execute(
                query_hou_node_info, query_hou_node_info_params
            )
            rows_thumb_info = 0
            rows_video_info = 0
            if query_thumb_info is not None:
                cursor_thumb_info = self._cursor.execute(
                    query_thumb_info, query_thumb_info_params
                )
                rows_thumb_info = cursor_thumb_info.rowcount
            if query_video_info is not None:
                cursor_video_info = self._cursor.execute(
                    query_video_info, query_video_info_params
                )
                rows_video_info = cursor_video_info.rowcount
            self._commit()
            res_cnt += (
                cursor_hda_key.rowcount
                + cursor_hda_info.rowcount
                + cursor_hou_node_info.rowcount
            )
            res_cnt += rows_thumb_info + rows_video_info
            return res_cnt
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_name (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_load_count(self, hda_key_id: int | None = None) -> int | None:
        from libs.database.lifecycle import PersonalLifecycle
        from libs.library_metadata import new_identity

        if hda_key_id is None:
            return 0
        try:
            with self.transaction():
                PersonalLifecycle(self._connect).record_use(hda_key_id, new_identity())
            return 1
        except Exception as error:
            logging.getLogger(__name__).warning(
                "Could not record successful import: %s", error
            )
            return None

    def update_hda_favorite(self, hda_key_id: int | None = None) -> int | None:
        from libs.database.lifecycle import PersonalLifecycle

        if hda_key_id is None:
            return 0
        with self.transaction():
            row = self._connect.execute(
                "SELECT favorite FROM asset_user_preferences WHERE asset_id=?",
                (hda_key_id,),
            ).fetchone()
            if row is None:
                return 0
            PersonalLifecycle(self._connect).favorite(hda_key_id, not bool(row[0]))
        return 1

    def update_note_info(
        self, hda_key_id: int | None = None, note: str = ""
    ) -> int | None:
        query = """
        UPDATE note_info SET note = ? WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (note, hda_key_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** note_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_video_info(
        self,
        hda_key_id: int | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
        version: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """UPDATE video_info SET filename = ?, dirpath = ?, version = ?
        WHERE hda_key_id = ?"""
        query_params: tuple[Any, ...] = (
            filename,
            dirpath.as_posix(),
            version,
            hda_key_id,
        )
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** video_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_thumbnail_info(
        self,
        hda_key_id: int | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
        version: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """UPDATE thumbnail_info SET filename = ?, dirpath = ?, version = ?
        WHERE hda_key_id = ?"""
        query_params: tuple[Any, ...] = (
            filename,
            dirpath.as_posix(),
            version,
            hda_key_id,
        )
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** thumbnail_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_hipfile_info(
        self,
        hda_key_id: int | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
        houdini_version: str | None = None,
        hda_license: str | None = None,
        operating_system: str | None = None,
        sf: float | None = None,
        ef: float | None = None,
        fps: float | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """
        UPDATE hipfile_info SET filename = ?, dirpath = ?, houdini_version = ?,
            hda_license = ?, operating_system = ?, sf = ?, ef = ?, fps = ?
        WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (
            filename,
            dirpath.as_posix(),
            houdini_version,
            hda_license,
            operating_system,
            sf,
            ef,
            fps,
            hda_key_id,
        )
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hipfile_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_icon_info(
        self, hda_key_id: int | None = None, icon_lst: Sequence[str] = ()
    ) -> int | None:
        if not icon_lst:
            return None
        icon_join_str = ",".join([x.strip() for x in icon_lst])
        query = """
        UPDATE icon_info SET icon = ? WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (icon_join_str, hda_key_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** icon_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_tag_info(
        self, hda_key_id: int | None = None, tag_lst: Sequence[str] = ()
    ) -> int | None:
        tag_join_str = "#".join(normalize_tags(tag_lst))
        query = """
        UPDATE tag_info SET tag = ? WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (tag_join_str, hda_key_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** tag_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def is_exist_tag(self, hda_key_id: int | None = None) -> bool:
        query = """SELECT hda_key_id FROM tag_info"""
        query_params: tuple[Any, ...] = ()
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if dat is not None:
            dat = [x[0] for x in dat]
            return hda_key_id in dat
        return False

    def is_exist_note(self, hda_key_id: int | None = None) -> bool:
        query = """SELECT hda_key_id FROM note_info"""
        query_params: tuple[Any, ...] = ()
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if dat is not None:
            dat = [x[0] for x in dat]
            return hda_key_id in dat
        return False

    def is_exist_hda_name(
        self,
        user_id: str | None = None,
        category: str | None = None,
        hda_name: str | None = None,
    ) -> bool:
        query = """
        SELECT COUNT(*) FROM hda_key WHERE user_id = ? AND category = ? AND name = ?
        """
        query_params: tuple[Any, ...] = (user_id, category, hda_name)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_ihda_lastest_version(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> bool:
        query = """SELECT COUNT(*) FROM hda_info WHERE hda_key_id = ? AND version = ?
        """
        query_params: tuple[Any, ...] = (hda_key_id, version)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_video_and_ihda_same_version(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> bool:
        query = """
        SELECT COUNT(*) FROM video_info WHERE hda_key_id = ? AND version = ?
        """
        query_params: tuple[Any, ...] = (hda_key_id, version)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def get_hda_name(
        self,
        category: str | None = None,
        user_id: str | None = None,
        with_id: bool = False,
    ) -> list[list[Any]]:
        if category is None:
            if with_id:
                query = """
                SELECT id, name FROM hda_key WHERE user_id = ?
                """
                query_params: tuple[Any, ...] = (user_id,)
            else:
                query = """
                SELECT name FROM hda_key WHERE user_id = ?
                """
                query_params = (user_id,)
        else:
            if with_id:
                query = """
                SELECT id, name FROM hda_key WHERE category = ? AND user_id = ?
                """
                query_params = (category, user_id)
            else:
                query = """
                SELECT name FROM hda_key WHERE category = ? AND user_id = ?
                """
                query_params = (category, user_id)
        query = query + " ORDER BY name"
        query_params = query_params + ()
        cursor = self._cursor.execute(query, query_params)
        dat = [list(x) for x in cursor.fetchall()]
        return dat

    def get_all_hda_fileinfo(self, user_id: str | None = None) -> list[tuple[Any, ...]]:
        query = """
        SELECT hinfo.hda_key_id, hinfo.dirpath, hinfo.filename, hkey.category FROM hda_info AS hinfo
        INNER JOIN hda_key AS hkey
        ON hinfo.hda_key_id = hkey.id
        WHERE hkey.user_id = ?
        """
        query_params: tuple[Any, ...] = (user_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return []
        return fetch_dat

    def get_update_before_data(
        self, hda_key_id: int | None = None
    ) -> None | dict[str, Any]:
        query = """
        SELECT is_favorite, load_count, initial_registration_datetime,
            (SELECT tag_info.tag FROM tag_info WHERE tag_info.hda_key_id = ?),
            (SELECT note_info.note FROM note_info WHERE note_info.hda_key_id = ?),
            (SELECT video_info.dirpath FROM video_info WHERE video_info.hda_key_id = ?),
            (SELECT video_info.filename FROM video_info WHERE video_info.hda_key_id = ?)
        FROM hda_info WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (
            hda_key_id,
            hda_key_id,
            hda_key_id,
            hda_key_id,
            hda_key_id,
        )
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        key_lst = [
            Key.is_favorite_hda,
            Key.hda_load_count,
            Key.hda_ctime,
            Key.hda_tags,
            Key.hda_note,
            Key.video_dirpath,
            Key.video_filename,
        ]
        data = dict(zip(key_lst, fetch_dat, strict=False))
        # dirpath
        tags = data.get(Key.hda_tags)
        if tags is None:
            data[Key.hda_tags] = []
        else:
            data[Key.hda_tags] = normalize_tags(tags)
        video_dirpath = data.get(Key.video_dirpath)
        if video_dirpath is not None:
            data[Key.video_dirpath] = pathlib.Path(video_dirpath)
        return data

    def get_hda_filepath(self, hda_key_id: int | None = None) -> pathlib.Path | None:
        query = "SELECT dirpath, filename FROM hda_info WHERE hda_key_id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        if any(x is None for x in fetch_dat):
            return None
        filepath = pathlib.Path(fetch_dat[0]) / fetch_dat[1]
        return filepath

    def get_hda_version(self, hda_key_id: int | None = None) -> str | None:
        query = "SELECT version FROM hda_info WHERE hda_key_id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_icon_info_by_user(self, user_id: str | None = None) -> list[Any]:
        if user_id is None:
            query = """
            SELECT hkey.id, (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id)
            FROM hda_key AS hkey
            """
            query_params: tuple[Any, ...] = ()
        else:
            query = """
            SELECT hkey.id, (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id)
            FROM hda_key AS hkey WHERE user_id = ?
            """
            query_params = (user_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        dat = []
        for row_val in sorted(fetch_dat, key=lambda x: x[0]):
            tmp_dat = list(row_val)
            tmp_dat[-1] = list(map(str, tmp_dat[-1].split(",")))
            dat.append(tmp_dat)
        return dat

    def get_note_info(self, hda_key_id: int | None = None) -> str | None:
        query = "SELECT note FROM note_info WHERE hda_key_id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()
        if dat is None:
            return None
        return dat[0]

    def get_video_info(self, hda_key_id: int | None = None) -> pathlib.Path | None:
        query = "SELECT dirpath, filename FROM video_info WHERE hda_key_id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()
        if dat is None:
            return None
        dat = list(dat)
        dat[0] = pathlib.Path(dat[0])
        return dat[0] / dat[1]

    def distinct_tags(self, user_id: str | None = None) -> list[str]:
        """Vocabulary for completion and AI prompts; reads the trigger-maintained index."""
        query = """
        SELECT DISTINCT t.tag FROM asset_tags AS t
        JOIN hda_key AS k ON k.id = t.hda_key_id
        WHERE (? IS NULL OR k.user_id = ?)
        ORDER BY t.tag COLLATE NOCASE
        """
        cursor = self._cursor.execute(query, (user_id, user_id))
        return [row[0] for row in cursor.fetchall()]

    def get_tag_info(self, hda_key_id: int | None = None) -> None | list[Any]:
        query = "SELECT tag FROM tag_info WHERE hda_key_id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()
        if dat is None:
            return None
        dat = dat[0]
        if not len(dat):
            return None
        return [x.strip() for x in dat.split("#")]

    def get_hda_data(
        self, category: str | None = None, user_id: str | None = None
    ) -> list[AssetData]:
        if category == Type.root:
            category = None
        query = """
SELECT hkey.id,
       hkey.name,
       hkey.category,
       hinfo.version,
       hinfo.filename,
       hinfo.dirpath,
       hinfo.is_favorite,
       hinfo.load_count,
       hinfo.initial_registration_datetime,
       hinfo.modified_registration_datetime,
       hipinfo.houdini_version,
       ninfo.node_type_name,
       ninfo.node_def_desc,
       ninfo.is_network,
       ninfo.is_sub_network,
       ninfo.node_old_path,
       hipinfo.hda_license,
       hipinfo.filename,
       hipinfo.dirpath,
       (SELECT filename FROM thumbnail_info WHERE thumbnail_info.hda_key_id = hkey.id),
       (SELECT dirpath FROM thumbnail_info WHERE thumbnail_info.hda_key_id = hkey.id),
       (SELECT filename FROM video_info WHERE video_info.hda_key_id = hkey.id),
       (SELECT dirpath FROM video_info WHERE video_info.hda_key_id = hkey.id),
       (SELECT note FROM note_info WHERE hda_key_id = hkey.id),
       (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id),
       (SELECT tag FROM tag_info WHERE hda_key_id = hkey.id)
FROM hda_key AS hkey
         INNER JOIN hda_info AS hinfo
         INNER JOIN houdini_node_info AS ninfo
         INNER JOIN hipfile_info AS hipinfo
            ON hkey.id = hinfo.hda_key_id AND hkey.id = ninfo.hda_key_id AND hkey.id = hipinfo.hda_key_id
WHERE (? IS NULL OR hkey.user_id = ?)
AND hkey.id IN (SELECT asset_id FROM asset_identity WHERE deleted_at IS NULL)
        """
        query_params: tuple[Any, ...] = (user_id, user_id)
        if category is not None:
            query = (
                "\n            "
                + query
                + " AND hkey.category = "
                + "?"
                + "\n            "
            )
            query_params = query_params + (category,)
        query = query + " ORDER BY hkey.name"
        query_params = query_params + ()
        cursor = self._cursor.execute(query, query_params)
        key_lst = DatabaseValues.hda_info_key_lst()
        fetch_dat = cursor.fetchall()
        if fetch_dat is None:
            return []
        dat = []
        for row_val in fetch_dat:
            tmp_dict = dict(zip(key_lst, row_val, strict=False))
            icon = tmp_dict[Key.hda_icon]
            tmp_dict[Key.hda_icon] = icon.split(",") if icon else []
            for flag in (
                Key.is_favorite_hda,
                Key.is_network,
                Key.is_sub_network,
            ):
                tmp_dict[flag] = bool(tmp_dict[flag])
            tags = tmp_dict[Key.hda_tags]
            if tags is None:
                tmp_dict[Key.hda_tags] = []
            else:
                tmp_dict[Key.hda_tags] = normalize_tags(tags)
            tmp_dict[Key.hda_dirpath] = pathlib.Path(tmp_dict[Key.hda_dirpath])
            tmp_dict[Key.hip_dirpath] = pathlib.Path(tmp_dict[Key.hip_dirpath])
            if tmp_dict[Key.thumbnail_dirpath] is not None:
                tmp_dict[Key.thumbnail_dirpath] = pathlib.Path(
                    tmp_dict[Key.thumbnail_dirpath]
                )
            if tmp_dict[Key.video_dirpath] is not None:
                tmp_dict[Key.video_dirpath] = pathlib.Path(tmp_dict[Key.video_dirpath])
            dat.append(cast(AssetData, tmp_dict))
        return dat
