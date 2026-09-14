"""Records queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
import pathlib
from typing import Any, cast

import public
from libs import log_handler
from libs.database.session import DatabaseSession
from libs.database.values import DatabaseValues
from libs.domain import SceneRecord


class RecordsOperations(DatabaseSession):
    def insert_hda_node_location_record(
        self,
        hda_key_id: int | None = None,
        hip_filename: str | None = None,
        hip_dirpath: pathlib.Path | None = None,
        hda_filename: str | None = None,
        hda_dirpath: pathlib.Path | None = None,
        parent_node_path: str | None = None,
        node_type: str | None = None,
        node_cate: Any = None,
        node_name: str | None = None,
        node_ver: str | None = None,
        hou_version: Any = None,
        hou_license: Any = None,
        operating_sys: Any = None,
        sf: float | None = None,
        ef: float | None = None,
        fps: float | None = None,
    ) -> int | None:
        assert isinstance(hip_dirpath, pathlib.Path)
        assert isinstance(hda_dirpath, pathlib.Path)
        is_exist = self.is_exist_hda_node_loc_record(
            hda_key_id=hda_key_id,
            hip_filename=hip_filename,
            hip_dirpath=hip_dirpath,
            parent_node_path=parent_node_path,
            node_name=node_name,
            node_ver=node_ver,
        )
        if is_exist:
            query = """UPDATE hda_node_location_record SET mtime = (SELECT DATETIME('now', 'localtime')),
                houdini_version = ?, houdini_license = ?, operating_system = ?,
                sf = ?, ef = ?, fps = ?
            WHERE hda_key_id = ? AND hip_filename = ? AND hip_dirpath = ?
                AND parent_node_path = ? AND node_name = ?
            """
            query_params: tuple[Any, ...] = (
                hou_version,
                hou_license,
                operating_sys,
                sf,
                ef,
                fps,
                hda_key_id,
                hip_filename,
                hip_dirpath.as_posix(),
                parent_node_path,
                node_name,
            )
            try:
                cursor = self._cursor.execute(query, query_params)
                self._commit()
                return cursor.rowcount
            except Exception as err:
                self._rollback()
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg="*** hda_node_location_record (update) ***",
                )
                log_handler.LogHandler.log_msg(method=logging.error, msg=err)
                return None
        else:
            query = """INSERT INTO hda_node_location_record
            (hda_key_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
            parent_node_path, node_type, node_category, node_name, node_version,
            houdini_version, houdini_license, operating_system, sf, ef, fps, ctime, mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                (SELECT DATETIME('now', 'localtime')), (SELECT DATETIME('now', 'localtime')))"""
            query_params = ()
            try:
                dat: tuple[Any, ...] = (
                    hda_key_id,
                    hip_filename,
                    hip_dirpath.as_posix(),
                    hda_filename,
                    hda_dirpath.as_posix(),
                    parent_node_path,
                    node_type,
                    node_cate,
                    node_name,
                    node_ver,
                    hou_version,
                    hou_license,
                    operating_sys,
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
                    method=logging.error,
                    msg="*** hda_node_location_record (insert) ***",
                )
                log_handler.LogHandler.log_msg(method=logging.error, msg=err)
                return None

    def delete_hda_record(
        self, hda_key_id: int | None = None, record_id: int | None = None
    ) -> int | None:
        if (hda_key_id is None) and (record_id is None):
            query = """DELETE FROM hda_node_location_record"""
            query_params: tuple[Any, ...] = ()
        elif (hda_key_id is not None) and (record_id is None):
            query = """
            DELETE FROM hda_node_location_record WHERE hda_key_id = ?
            """
            query_params = (hda_key_id,)
        elif (hda_key_id is None) and (record_id is not None):
            query = """
                DELETE FROM hda_node_location_record WHERE id = ?
                """
            query_params = (record_id,)
        else:
            query = """
            DELETE FROM hda_node_location_record WHERE hda_key_id = ? AND id = ?
            """
            query_params = (hda_key_id, record_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_node_location_record (delete) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def is_exist_hda_node_loc_file(
        self,
        hda_key_id: int | None = None,
        version: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        query = """
        SELECT COUNT(*) FROM hda_history WHERE hda_key_id = ? AND version = ? AND userid = ?
        """
        query_params: tuple[Any, ...] = (hda_key_id, version, user_id)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_exist_hda_node_loc_record(
        self,
        hda_key_id: int | None = None,
        hip_filename: str | None = None,
        hip_dirpath: pathlib.Path | None = None,
        parent_node_path: str | None = None,
        node_name: str | None = None,
        node_ver: str | None = None,
    ) -> bool:
        assert isinstance(hip_dirpath, pathlib.Path)
        query = """
        SELECT COUNT(*) FROM hda_node_location_record
        WHERE hda_key_id = ? AND hip_filename = ? AND hip_dirpath = ? AND parent_node_path = ?
            AND node_name = ? AND node_version = ?
        """
        query_params: tuple[Any, ...] = (
            hda_key_id,
            hip_filename,
            hip_dirpath.as_posix(),
            parent_node_path,
            node_name,
            node_ver,
        )
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def get_all_hda_record_fileinfo(
        self,
        hda_key_id: int | None = None,
        hip_filename: str | None = None,
        hip_dirpath: pathlib.Path | None = None,
        user_id: str | None = None,
    ) -> list[tuple[Any, ...]]:
        query = """
        SELECT hrecord.id, hrecord.hip_dirpath, hrecord.hip_filename, hrecord.hda_dirpath, hrecord.hda_filename
        FROM hda_node_location_record AS hrecord
        INNER JOIN hda_key AS hkey
        ON hrecord.hda_key_id = hkey.id
        WHERE hkey.user_id = ?
        """
        query_params: tuple[Any, ...] = (user_id,)
        if hda_key_id is not None:
            query = query + " AND hda_key_id = " + "?"
            query_params = query_params + (hda_key_id,)
        if (hip_filename is not None) and (hip_dirpath is not None):
            assert isinstance(hip_dirpath, pathlib.Path)
            query = (
                query
                + " AND hip_filename = "
                + "?"
                + " AND hip_dirpath = "
                + "?"
                + "\n            "
            )
            query_params = query_params + (hip_filename, hip_dirpath.as_posix())
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return []
        return fetch_dat

    def get_hda_node_location_record(
        self,
        hda_key_id: int | None = None,
        hip_filename: str | None = None,
        hip_dirpath: pathlib.Path | None = None,
    ) -> dict[str, Any]:
        query = """
        SELECT id, hda_key_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
            parent_node_path, node_type, node_category, node_name, node_version,
            houdini_version, houdini_license, operating_system, sf, ef, fps, ctime, mtime
        FROM hda_node_location_record"""
        query_params: tuple[Any, ...] = ()
        if hda_key_id is not None:
            query = query + " WHERE hda_key_id = " + "?"
            query_params = query_params + (hda_key_id,)
        if (hip_filename is not None) and (hip_dirpath is not None):
            assert isinstance(hip_dirpath, pathlib.Path)
            if hda_key_id is None:
                query = (
                    query
                    + " WHERE hip_filename = "
                    + "?"
                    + " AND hip_dirpath = "
                    + "?"
                    + "\n                "
                )
                query_params = query_params + (hip_filename, hip_dirpath.as_posix())
            else:
                query = (
                    query
                    + " AND hip_filename = "
                    + "?"
                    + " AND hip_dirpath = "
                    + "?"
                    + "\n                "
                )
                query_params = query_params + (hip_filename, hip_dirpath.as_posix())
        query = (
            query
            + " ORDER BY hip_dirpath, hip_filename, parent_node_path, node_name, node_version"
        )
        query_params = query_params + ()
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return {}
        key_lst = DatabaseValues.hda_record_key_lst()
        assert len(fetch_dat[0]) == len(key_lst)
        dat: dict[str, Any] = {}
        for row_val in fetch_dat:
            tmp_dict = dict(zip(key_lst, row_val, strict=False))
            hip_dpath = tmp_dict[public.Key.Record.hip_dirpath]
            hip_fname = tmp_dict[public.Key.Record.hip_filename]
            hda_dpath = tmp_dict[public.Key.Record.hda_dirpath]
            hda_fname = tmp_dict[public.Key.Record.hda_filename]
            pnode_path = tmp_dict[public.Key.Record.parent_node_path]
            node_name = tmp_dict[public.Key.Record.node_name]
            node_ver = tmp_dict[public.Key.Record.node_ver]
            node_type = tmp_dict[public.Key.Record.node_type]
            node_cate = tmp_dict[public.Key.Record.node_cate]
            record_id = tmp_dict[public.Key.Record.record_id]
            hda_id = tmp_dict[public.Key.Record.hda_id]
            ctime = tmp_dict[public.Key.Record.ctime]
            mtime = tmp_dict[public.Key.Record.mtime]
            hou_version = tmp_dict[public.Key.Record.houdini_version]
            hou_license = tmp_dict[public.Key.Record.houdini_license]
            operating_system = tmp_dict[public.Key.Record.operating_system]
            sf = tmp_dict[public.Key.Record.sf]
            ef = tmp_dict[public.Key.Record.ef]
            fps = tmp_dict[public.Key.Record.fps]
            # 노드와 버전이 함께 보여지도록. 그리고 이래야 key data로 record데이터를 지울 때 명확하다.
            node_name_with_ver = f"{node_name} (v{node_ver})"
            if hip_dpath not in dat:
                dat[hip_dpath] = {}
            if hip_fname not in dat[hip_dpath]:
                dat[hip_dpath][hip_fname] = {}
            if pnode_path not in dat[hip_dpath][hip_fname]:
                dat[hip_dpath][hip_fname][pnode_path] = []
            dat[hip_dpath][hip_fname][pnode_path].append(
                [
                    record_id,
                    hda_id,
                    node_name_with_ver,
                    node_type,
                    node_cate,
                    node_ver,
                    ctime,
                    mtime,
                    pathlib.Path(hip_dpath),
                    hip_fname,
                    pathlib.Path(hda_dpath),
                    hda_fname,
                    hou_version,
                    hou_license,
                    operating_system,
                    sf,
                    ef,
                    fps,
                    node_name,
                ]
            )
        return dat

    def get_only_detailview_record_data(
        self, record_id: int | None = None
    ) -> SceneRecord:
        query = """
        SELECT id, hda_key_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
            parent_node_path, node_type, node_category, node_name, node_version,
            houdini_version, houdini_license, operating_system, sf, ef, fps, ctime, mtime,
            (SELECT thumb_dirpath FROM hda_history AS hhist
                WHERE hhist.hda_key_id = hrecord.hda_key_id AND hhist.version = hrecord.node_version),
            (SELECT thumb_filename FROM hda_history AS hhist
                WHERE hhist.hda_key_id = hrecord.hda_key_id AND hhist.version = hrecord.node_version)
        FROM hda_node_location_record AS hrecord
        WHERE id = ?"""
        query_params: tuple[Any, ...] = (record_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return {}
        key_lst = DatabaseValues.hda_record_key_lst()
        key_lst.append(public.Key.Record.thumb_dirpath)
        key_lst.append(public.Key.Record.thumb_filename)
        assert len(fetch_dat) == len(key_lst)
        dat: dict[str, Any] = dict(zip(key_lst, fetch_dat, strict=False))
        thumb_dirpath = dat.get(public.Key.Record.thumb_dirpath)
        if thumb_dirpath is not None:
            dat[public.Key.Record.thumb_dirpath] = pathlib.Path(thumb_dirpath)
        for key in (public.Key.Record.hip_dirpath, public.Key.Record.hda_dirpath):
            if dat.get(key) is not None:
                dat[key] = pathlib.Path(dat[key])
        return cast(SceneRecord, dat)
