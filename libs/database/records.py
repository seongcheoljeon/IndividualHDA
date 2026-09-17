"""Records queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from libs.database.rows import named_query
from libs.database.session import DatabaseSession
from libs.record_codec import decode_record
from libs.scene_contracts import SceneRecord
from libs.scene_record_cleanup import SceneRecordFiles


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
        version_uuid: str | None = None,
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
                houdini_version = :hou_version, houdini_license = :hou_license, operating_system = :operating_sys,
                sf = :sf, ef = :ef, fps = :fps
            WHERE hda_key_id = :hda_key_id AND hip_filename = :hip_filename AND hip_dirpath = :hip_dirpath
                AND parent_node_path = :parent_node_path AND node_name = :node_name AND node_version = :node_ver
            """
            query_params: dict[str, Any] = {
                "hou_version": hou_version,
                "hou_license": hou_license,
                "operating_sys": operating_sys,
                "sf": sf,
                "ef": ef,
                "fps": fps,
                "hda_key_id": hda_key_id,
                "hip_filename": hip_filename,
                "hip_dirpath": hip_dirpath.as_posix(),
                "parent_node_path": parent_node_path,
                "node_name": node_name,
                "node_ver": node_ver,
            }
            try:
                cursor = self._cursor.execute(query, query_params)
                if version_uuid is not None:
                    if not self._connect.execute(
                        "SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE v.uuid=:version_uuid AND h.hda_key_id=:hda_key_id AND v.deleted_at IS NULL",
                        {"version_uuid": version_uuid, "hda_key_id": hda_key_id},
                    ).fetchone():
                        raise ValueError("Scene version does not belong to this asset")
                    self._connect.execute(
                        """UPDATE hda_node_location_record SET library_uuid=(SELECT uuid FROM library_identity),asset_uuid=(SELECT uuid FROM asset_identity WHERE asset_id=:hda_key_id),version_uuid=:version_uuid,link_status='resolved'
                        WHERE hda_key_id=:hda_key_id AND hip_filename=:hip_filename AND hip_dirpath=:hip_dirpath AND parent_node_path=:parent_node_path AND node_name=:node_name AND node_version=:node_ver""",
                        {
                            "hda_key_id": hda_key_id,
                            "version_uuid": version_uuid,
                            "hip_filename": hip_filename,
                            "hip_dirpath": hip_dirpath.as_posix(),
                            "parent_node_path": parent_node_path,
                            "node_name": node_name,
                            "node_ver": node_ver,
                        },
                    )
                self._commit()
                return cursor.rowcount
            except Exception as err:
                self._rollback()
                logging.error("*** hda_node_location_record (update) ***")
                logging.error(err)
                return None
        else:
            query = """INSERT INTO hda_node_location_record
            (hda_key_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
            parent_node_path, node_type, node_category, node_name, node_version,
            houdini_version, houdini_license, operating_system, sf, ef, fps, ctime, mtime)
            VALUES (:hda_key_id, :hip_filename, :hip_dirpath, :hda_filename, :hda_dirpath, :parent_node_path, :node_type, :node_cate, :node_name, :node_ver, :hou_version, :hou_license, :operating_sys, :sf, :ef, :fps,
                (SELECT DATETIME('now', 'localtime')), (SELECT DATETIME('now', 'localtime')))"""
            query_params = {}
            try:
                dat: dict[str, Any] = {
                    "hda_key_id": hda_key_id,
                    "hip_filename": hip_filename,
                    "hip_dirpath": hip_dirpath.as_posix(),
                    "hda_filename": hda_filename,
                    "hda_dirpath": hda_dirpath.as_posix(),
                    "parent_node_path": parent_node_path,
                    "node_type": node_type,
                    "node_cate": node_cate,
                    "node_name": node_name,
                    "node_ver": node_ver,
                    "hou_version": hou_version,
                    "hou_license": hou_license,
                    "operating_sys": operating_sys,
                    "sf": sf,
                    "ef": ef,
                    "fps": fps,
                }
                cursor = self._cursor.execute(query, dat)
                if version_uuid is not None:
                    if not self._connect.execute(
                        "SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE v.uuid=:version_uuid AND h.hda_key_id=:hda_key_id AND v.deleted_at IS NULL",
                        {"version_uuid": version_uuid, "hda_key_id": hda_key_id},
                    ).fetchone():
                        raise ValueError("Scene version does not belong to this asset")
                    self._connect.execute(
                        """UPDATE hda_node_location_record SET library_uuid=(SELECT uuid FROM library_identity),asset_uuid=(SELECT uuid FROM asset_identity WHERE asset_id=:hda_key_id),version_uuid=:version_uuid,link_status='resolved'
                        WHERE hda_key_id=:hda_key_id AND hip_filename=:hip_filename AND hip_dirpath=:hip_dirpath AND parent_node_path=:parent_node_path AND node_name=:node_name AND node_version=:node_ver""",
                        {
                            "hda_key_id": hda_key_id,
                            "version_uuid": version_uuid,
                            "hip_filename": hip_filename,
                            "hip_dirpath": hip_dirpath.as_posix(),
                            "parent_node_path": parent_node_path,
                            "node_name": node_name,
                            "node_ver": node_ver,
                        },
                    )
                self._commit()
                return cursor.rowcount
            except Exception as err:
                self._rollback()
                logging.error("*** hda_node_location_record (insert) ***")
                logging.error(err)
                return None

    def delete_hda_record(
        self, hda_key_id: int | None = None, record_id: int | None = None
    ) -> int | None:
        if (hda_key_id is None) and (record_id is None):
            query = """DELETE FROM hda_node_location_record"""
            query_params: dict[str, Any] = {}
        elif (hda_key_id is not None) and (record_id is None):
            query = """
            DELETE FROM hda_node_location_record WHERE hda_key_id = :hda_key_id
            """
            query_params = {"hda_key_id": hda_key_id}
        elif (hda_key_id is None) and (record_id is not None):
            query = """
                DELETE FROM hda_node_location_record WHERE id = :record_id
                """
            query_params = {"record_id": record_id}
        else:
            query = """
            DELETE FROM hda_node_location_record WHERE hda_key_id = :hda_key_id AND id = :record_id
            """
            query_params = {"hda_key_id": hda_key_id, "record_id": record_id}
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** hda_node_location_record (delete) ***")
            logging.error(err)
            return None

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
        WHERE hda_key_id = :hda_key_id AND hip_filename = :hip_filename AND hip_dirpath = :hip_dirpath AND parent_node_path = :parent_node_path
            AND node_name = :node_name AND node_version = :node_ver
        """
        query_params: dict[str, Any] = {
            "hda_key_id": hda_key_id,
            "hip_filename": hip_filename,
            "hip_dirpath": hip_dirpath.as_posix(),
            "parent_node_path": parent_node_path,
            "node_name": node_name,
            "node_ver": node_ver,
        }
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def get_all_hda_record_fileinfo(
        self,
        hda_key_id: int | None = None,
        hip_filename: str | None = None,
        hip_dirpath: pathlib.Path | None = None,
        user_id: str | None = None,
    ) -> list[SceneRecordFiles]:
        query = """
        SELECT hrecord.id, hrecord.hip_dirpath, hrecord.hip_filename, hrecord.hda_dirpath, hrecord.hda_filename
        FROM hda_node_location_record AS hrecord
        INNER JOIN hda_key AS hkey
        ON hrecord.hda_key_id = hkey.id
        WHERE hkey.user_id = :user_id
        """
        query_params: dict[str, Any] = {"user_id": user_id}
        if hda_key_id is not None:
            query += " AND hda_key_id = :hda_key_id"
            query_params["hda_key_id"] = hda_key_id
        if (hip_filename is not None) and (hip_dirpath is not None):
            assert isinstance(hip_dirpath, pathlib.Path)
            query += " AND hip_filename = :hip_filename AND hip_dirpath = :hip_dirpath"
            query_params.update(
                hip_filename=hip_filename, hip_dirpath=hip_dirpath.as_posix()
            )
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return []
        return [
            SceneRecordFiles(
                record_id=row["id"],
                hip_path=pathlib.Path(row["hip_dirpath"]) / row["hip_filename"],
                hda_path=pathlib.Path(row["hda_dirpath"]) / row["hda_filename"],
            )
            for row in fetch_dat
        ]

    def get_hda_node_location_record(
        self,
        hda_key_id: int | None = None,
        hip_filename: str | None = None,
        hip_dirpath: pathlib.Path | None = None,
    ) -> tuple[SceneRecord, ...]:
        query = """
        SELECT library_uuid, asset_uuid, version_uuid, link_status, id AS record_id,
            hda_key_id AS hda_id,
            hip_filename AS hip_filename,
            hip_dirpath AS hip_dirpath,
            hda_filename AS hda_filename,
            hda_dirpath AS hda_dirpath,
            parent_node_path AS parent_node_path,
            node_type AS node_type,
            node_category AS node_cate,
            node_name AS node_name,
            node_version AS node_ver,
            houdini_version AS houdini_version,
            houdini_license AS houdini_license,
            operating_system AS operating_system,
            sf AS sf,
            ef AS ef,
            fps AS fps,
            ctime AS ctime,
            mtime AS mtime
        FROM hda_node_location_record"""
        parameters: dict[str, Any] = {}
        predicates = []
        if hda_key_id is not None:
            predicates.append("hda_key_id = :asset_id")
            parameters["asset_id"] = hda_key_id
        if hip_filename is not None and hip_dirpath is not None:
            predicates.extend(
                ("hip_filename = :hip_filename", "hip_dirpath = :hip_dirpath")
            )
            parameters.update(hip_filename=hip_filename, hip_dirpath=str(hip_dirpath))
        if predicates:
            query += " WHERE " + " AND ".join(predicates)
        query += " ORDER BY hip_dirpath, hip_filename, parent_node_path, node_name, node_version"
        return tuple(
            decode_record(SceneRecord, dict(row))
            for row in named_query(self._connect, query, parameters)
        )

    def get_only_detailview_record_data(
        self, record_id: int | None = None
    ) -> SceneRecord | None:
        query = """
        SELECT library_uuid, asset_uuid, version_uuid, link_status, id AS record_id,
            hda_key_id AS hda_id,
            hip_filename AS hip_filename,
            hip_dirpath AS hip_dirpath,
            hda_filename AS hda_filename,
            hda_dirpath AS hda_dirpath,
            parent_node_path AS parent_node_path,
            node_type AS node_type,
            node_category AS node_cate,
            node_name AS node_name,
            node_version AS node_ver,
            houdini_version AS houdini_version,
            houdini_license AS houdini_license,
            operating_system AS operating_system,
            sf AS sf,
            ef AS ef,
            fps AS fps,
            ctime AS ctime,
            mtime AS mtime,
            (SELECT thumb_dirpath FROM hda_history AS hhist
                WHERE hhist.hda_key_id = hrecord.hda_key_id AND hhist.version = hrecord.node_version) AS thumb_dirpath,
            (SELECT thumb_filename FROM hda_history AS hhist
                WHERE hhist.hda_key_id = hrecord.hda_key_id AND hhist.version = hrecord.node_version) AS thumb_filename
        FROM hda_node_location_record AS hrecord
        WHERE id = :record_id"""
        query_params: dict[str, Any] = {"record_id": record_id}
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchone()
        return (
            decode_record(SceneRecord, dict(fetch_dat))
            if fetch_dat is not None
            else None
        )
