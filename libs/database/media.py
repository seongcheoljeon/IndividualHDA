"""Thumbnail and video queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from libs.database.rows import named_query
from libs.database.session import DatabaseSession


class MediaOperations(DatabaseSession):
    def insert_video_info(
        self,
        hda_key_id: int | None = None,
        dirpath: pathlib.Path | None = None,
        filename: str | None = None,
        version: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """INSERT INTO video_info (hda_key_id, filename, dirpath, version)
        VALUES (:hda_key_id, :filename, :dirpath, :version)"""
        try:
            dat: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "filename": filename,
                "dirpath": dirpath.as_posix(),
                "version": version,
            }
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** video_info (insert) ***")
            logging.error(err)
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
        VALUES (:hda_key_id, :filename, :dirpath, :version)"""
        try:
            dat: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "filename": filename,
                "dirpath": dirpath.as_posix(),
                "version": version,
            }
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** thumbnail_info (insert) ***")
            logging.error(err)
            return None

    def update_video_info(
        self,
        hda_key_id: int | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
        version: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """UPDATE video_info SET filename = :filename, dirpath = :dirpath, version = :version
        WHERE hda_key_id = :hda_key_id"""
        query_params: dict[str, Any] = {
            "filename": filename,
            "dirpath": dirpath.as_posix(),
            "version": version,
            "hda_key_id": hda_key_id,
        }
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** video_info (update) ***")
            logging.error(err)
            return None

    def update_thumbnail_info(
        self,
        hda_key_id: int | None = None,
        filename: str | None = None,
        dirpath: pathlib.Path | None = None,
        version: str | None = None,
    ) -> int | None:
        assert isinstance(dirpath, pathlib.Path)
        query = """UPDATE thumbnail_info SET filename = :filename, dirpath = :dirpath, version = :version
        WHERE hda_key_id = :hda_key_id"""
        query_params: dict[str, Any] = {
            "filename": filename,
            "dirpath": dirpath.as_posix(),
            "version": version,
            "hda_key_id": hda_key_id,
        }
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** thumbnail_info (update) ***")
            logging.error(err)
            return None

    def is_video_and_ihda_same_version(
        self, hda_key_id: int | None = None, version: str | None = None
    ) -> bool:
        query = """
        SELECT COUNT(*) FROM video_info WHERE hda_key_id = :hda_key_id AND version = :version
        """
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id, "version": version}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def get_video_info(self, hda_key_id: int | None = None) -> pathlib.Path | None:
        query = (
            "SELECT dirpath, filename FROM video_info WHERE hda_key_id = :hda_key_id"
        )
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = named_query(self._connect, query, query_params)
        dat = cursor.fetchone()
        if dat is None:
            return None
        if dat["dirpath"] is None or dat["filename"] is None:
            return None
        return pathlib.Path(dat["dirpath"]) / dat["filename"]
