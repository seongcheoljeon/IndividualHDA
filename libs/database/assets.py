"""Assets queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from libs.asset_contracts import AssetBeforeUpdate, AssetData, AssetName
from libs.database.rows import LIVE_ASSET_IDS, asset_data, named_query
from libs.database.session import DatabaseSession
from libs.database.values import normalize_tags
from libs.keys import Key, Type
from libs.record_codec import decode_record


class AssetsOperations(DatabaseSession):
    def asset_available(self, asset_id: int, history_id: int | None = None) -> bool:
        if (
            self._connect.execute(
                "SELECT 1 FROM asset_identity WHERE asset_id=:asset_id AND deleted_at IS NULL",
                {"asset_id": asset_id},
            ).fetchone()
            is None
        ):
            return False
        return (
            history_id is None
            or self._connect.execute(
                """SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id
            WHERE h.id=:history_id AND h.hda_key_id=:asset_id AND v.deleted_at IS NULL""",
                {"history_id": history_id, "asset_id": asset_id},
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
        VALUES (:hda_key_id, :version, :is_favorite, :load_count, :filename, :dirpath, (SELECT DATETIME('now', 'localtime')), (SELECT DATETIME('now', 'localtime')))
        """
        try:
            dat: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "version": version,
                "is_favorite": is_favorite,
                "load_count": load_count,
                "filename": filename,
                "dirpath": dirpath.as_posix(),
            }
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** hda_info (insert) ***")
            logging.error(err)
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
        VALUES (:hda_key_id, :filename, :dirpath, :houdini_version, :hda_license, :operating_system, :sf, :ef, :fps)
        """
        try:
            dat: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "filename": filename,
                "dirpath": dirpath.as_posix(),
                "houdini_version": houdini_version,
                "hda_license": hda_license,
                "operating_system": operating_system,
                "sf": sf,
                "ef": ef,
                "fps": fps,
            }
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** hipfile_info (insert) ***")
            logging.error(err)
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
        UPDATE hda_info SET version = :version, filename = :filename, dirpath = :dirpath,
        modified_registration_datetime = (SELECT DATETIME('now', 'localtime')) WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {
            "version": version,
            "filename": filename,
            "dirpath": dirpath.as_posix(),
            "hda_key_id": hda_key_id,
        }
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** hda_info (update) ***")
            logging.error(err)
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
        query_hda_key = "UPDATE hda_key SET name = :name WHERE id = :hda_key_id"
        query_hda_key_params = {"name": name, "hda_key_id": hda_key_id}
        query_hda_info = """
        UPDATE hda_info SET filename = :filename, dirpath = :dirpath,
        modified_registration_datetime = (SELECT DATETIME('now', 'localtime')) WHERE hda_key_id = :hda_key_id
        """
        query_hda_info_params = {
            "filename": filename,
            "dirpath": dirpath.as_posix(),
            "hda_key_id": hda_key_id,
        }
        query_hou_node_info = """
        UPDATE houdini_node_info SET node_old_path = :node_old_path WHERE hda_key_id = :hda_key_id
        """
        query_hou_node_info_params = {
            "node_old_path": node_old_path,
            "hda_key_id": hda_key_id,
        }
        query_thumb_info = None
        query_video_info = None
        if thumbnail_dirpath is not None:
            assert isinstance(thumbnail_dirpath, pathlib.Path)
            query_thumb_info = """
            UPDATE thumbnail_info SET dirpath = :thumbnail_dirpath, filename = :thumbnail_filename WHERE hda_key_id = :hda_key_id
            """
            query_thumb_info_params = {
                "thumbnail_dirpath": thumbnail_dirpath.as_posix(),
                "thumbnail_filename": thumbnail_filename,
                "hda_key_id": hda_key_id,
            }
        if video_dirpath is not None:
            assert isinstance(video_dirpath, pathlib.Path)
            query_video_info = """
            UPDATE video_info SET dirpath = :video_dirpath, filename = :video_filename WHERE hda_key_id = :hda_key_id
            """
            query_video_info_params = {
                "video_dirpath": video_dirpath.as_posix(),
                "video_filename": video_filename,
                "hda_key_id": hda_key_id,
            }
        try:
            with self.transaction():
                res_cnt = 0
                cursor_hda_key = self._cursor.execute(
                    query_hda_key, query_hda_key_params
                )
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
            res_cnt += (
                cursor_hda_key.rowcount
                + cursor_hda_info.rowcount
                + cursor_hou_node_info.rowcount
            )
            res_cnt += rows_thumb_info + rows_video_info
            return res_cnt
        except Exception as err:
            logging.error("*** hda_name (update) ***")
            logging.error(err)
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
                "SELECT favorite FROM asset_user_preferences WHERE asset_id=:hda_key_id",
                {"hda_key_id": hda_key_id},
            ).fetchone()
            if row is None:
                return 0
            PersonalLifecycle(self._connect).favorite(hda_key_id, not bool(row[0]))
        return 1

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
        UPDATE hipfile_info SET filename = :filename, dirpath = :dirpath, houdini_version = :houdini_version,
            hda_license = :hda_license, operating_system = :operating_system, sf = :sf, ef = :ef, fps = :fps
        WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {
            "filename": filename,
            "dirpath": dirpath.as_posix(),
            "houdini_version": houdini_version,
            "hda_license": hda_license,
            "operating_system": operating_system,
            "sf": sf,
            "ef": ef,
            "fps": fps,
            "hda_key_id": hda_key_id,
        }
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** hipfile_info (update) ***")
            logging.error(err)
            return None

    def is_exist_hda_name(
        self,
        user_id: str | None = None,
        category: str | None = None,
        hda_name: str | None = None,
    ) -> bool:
        query = """
        SELECT COUNT(*) FROM hda_key WHERE user_id = :user_id AND category = :category AND name = :hda_name
        """
        query_params: dict[str, Any] = {
            "user_id": user_id,
            "category": category,
            "hda_name": hda_name,
        }
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_ihda_lastest_version(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> bool:
        query = """SELECT COUNT(*) FROM hda_info WHERE hda_key_id = :hda_key_id AND version = :version
        """
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id, "version": version}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def get_hda_name(
        self,
        category: str | None = None,
        user_id: str | None = None,
        with_id: bool = False,
    ) -> list[AssetName]:
        query = f"SELECT id AS asset_id, name FROM hda_key WHERE user_id=:user_id AND id {LIVE_ASSET_IDS}"
        parameters: dict[str, Any] = {"user_id": user_id}
        if category is not None:
            query += " AND category=:category"
            parameters["category"] = category
        return [
            AssetName(**dict(row))
            for row in named_query(self._connect, query, parameters)
        ]

    def get_all_hda_fileinfo(self, user_id: str | None = None) -> list[tuple[Any, ...]]:
        query = f"""
        SELECT hinfo.hda_key_id, hinfo.dirpath, hinfo.filename, hkey.category FROM hda_info AS hinfo
        INNER JOIN hda_key AS hkey
        ON hinfo.hda_key_id = hkey.id
        WHERE hkey.user_id = :user_id AND hkey.id {LIVE_ASSET_IDS}
        """
        query_params: dict[str, Any] = {"user_id": user_id}
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return []
        return fetch_dat

    def get_update_before_data(
        self, hda_key_id: int | None = None
    ) -> AssetBeforeUpdate | None:
        query = """
        SELECT is_favorite AS is_favorite_hda,
            load_count AS hda_load_count,
            initial_registration_datetime AS hda_ctime,
            (SELECT tag_info.tag FROM tag_info WHERE tag_info.hda_key_id = :hda_key_id) AS hda_tags,
            (SELECT note_info.note FROM note_info WHERE note_info.hda_key_id = :hda_key_id) AS hda_note,
            (SELECT video_info.dirpath FROM video_info WHERE video_info.hda_key_id = :hda_key_id) AS video_dirpath,
            (SELECT video_info.filename FROM video_info WHERE video_info.hda_key_id = :hda_key_id) AS video_filename
        FROM hda_info WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        data = dict(fetch_dat)
        data["is_favorite_hda"] = bool(data["is_favorite_hda"])
        # dirpath
        tags = data.get(Key.hda_tags)
        if tags is None:
            data[Key.hda_tags] = []
        else:
            data[Key.hda_tags] = normalize_tags(tags)
        video_dirpath = data.get(Key.video_dirpath)
        if video_dirpath is not None:
            data[Key.video_dirpath] = pathlib.Path(video_dirpath)
        return decode_record(AssetBeforeUpdate, data)

    def get_hda_filepath(self, hda_key_id: int | None = None) -> pathlib.Path | None:
        query = "SELECT dirpath, filename FROM hda_info WHERE hda_key_id = :hda_key_id"
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        if any(x is None for x in fetch_dat):
            return None
        filepath = pathlib.Path(fetch_dat["dirpath"]) / fetch_dat["filename"]
        return filepath

    def get_hda_version(self, hda_key_id: int | None = None) -> str | None:
        query = "SELECT version FROM hda_info WHERE hda_key_id = :hda_key_id"
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_hda_data(
        self, category: str | None = None, user_id: str | None = None
    ) -> list[AssetData]:
        if category == Type.root:
            category = None
        query = """
SELECT hkey.id AS hda_id,
            hkey.name AS hda_name,
            hkey.category AS hda_cate,
            hinfo.version AS hda_version,
            hinfo.filename AS hda_filename,
            hinfo.dirpath AS hda_dirpath,
            hinfo.is_favorite AS is_favorite_hda,
            hinfo.load_count AS hda_load_count,
            hinfo.initial_registration_datetime AS hda_ctime,
            hinfo.modified_registration_datetime AS hda_mtime,
            hipinfo.houdini_version AS hou_version,
            ninfo.node_type_name AS node_type_name,
            ninfo.node_def_desc AS node_def_desc,
            ninfo.is_network AS is_network,
            ninfo.is_sub_network AS is_sub_network,
            ninfo.node_old_path AS node_old_path,
            hipinfo.hda_license AS hda_license,
            hipinfo.filename AS hip_filename,
            hipinfo.dirpath AS hip_dirpath,
            (SELECT filename FROM thumbnail_info WHERE thumbnail_info.hda_key_id = hkey.id) AS thumbnail_filename,
            (SELECT dirpath FROM thumbnail_info WHERE thumbnail_info.hda_key_id = hkey.id) AS thumbnail_dirpath,
            (SELECT filename FROM video_info WHERE video_info.hda_key_id = hkey.id) AS video_filename,
            (SELECT dirpath FROM video_info WHERE video_info.hda_key_id = hkey.id) AS video_dirpath,
            (SELECT note FROM note_info WHERE hda_key_id = hkey.id) AS hda_note,
            (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id) AS hda_icon,
            (SELECT tag FROM tag_info WHERE hda_key_id = hkey.id) AS hda_tags
        FROM hda_key AS hkey
         INNER JOIN hda_info AS hinfo
         INNER JOIN houdini_node_info AS ninfo
         INNER JOIN hipfile_info AS hipinfo
            ON hkey.id = hinfo.hda_key_id AND hkey.id = ninfo.hda_key_id AND hkey.id = hipinfo.hda_key_id
WHERE (:user_id IS NULL OR hkey.user_id = :user_id)
AND hkey.id IN (SELECT asset_id FROM asset_identity WHERE deleted_at IS NULL)
        """
        query_params: dict[str, Any] = {"user_id": user_id}
        if category is not None:
            query += " AND hkey.category = :category"
            query_params["category"] = category
        query = query + " ORDER BY hkey.name"
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchall()
        if fetch_dat is None:
            return []
        dat = []
        for row_val in fetch_dat:
            tmp_dict = dict(row_val)
            dat.append(asset_data(tmp_dict))
        return dat
