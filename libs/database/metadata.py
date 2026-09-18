"""Icon, tag and note queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from libs.asset_contracts import AssetIcon
from libs.database.rows import LIVE_ASSET_IDS, named_query
from libs.database.session import DatabaseSession
from libs.database.values import DatabaseValues, normalize_tags


class MetadataOperations(DatabaseSession):
    def insert_icon_info(
        self, hda_key_id: int | None = None, icon_lst: Sequence[str] = ()
    ) -> int | None:
        if not icon_lst:
            return None
        query = "INSERT INTO icon_info (hda_key_id, icon) VALUES (:hda_key_id, :value)"
        try:
            dat: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "value": DatabaseValues._make_icon_to_string(icon_lst=icon_lst),
            }
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** icon_info (insert) ***")
            logging.error(err)
            return None

    def update_icon_info(
        self, hda_key_id: int | None = None, icon_lst: Sequence[str] = ()
    ) -> int | None:
        if not icon_lst:
            return None
        icon_join_str = ",".join([x.strip() for x in icon_lst])
        query = """
        UPDATE icon_info SET icon = :icon_join_str WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {
            "icon_join_str": icon_join_str,
            "hda_key_id": hda_key_id,
        }
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** icon_info (update) ***")
            logging.error(err)
            return None

    def get_icon_info_by_user(self, user_id: str | None = None) -> list[AssetIcon]:
        query = f"""
        SELECT hkey.id, (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id) AS icon
        FROM hda_key AS hkey
        WHERE (:user_id IS NULL OR hkey.user_id = :user_id) AND hkey.id {LIVE_ASSET_IDS}
        """
        query_params: dict[str, Any] = {"user_id": user_id}
        cursor = named_query(self._connect, query, query_params)
        fetch_dat = cursor.fetchall()
        return [
            AssetIcon(
                asset_id=row["id"],
                icon=tuple(row["icon"].split(",")) if row["icon"] else (),
            )
            for row in sorted(fetch_dat, key=lambda row: row["id"])
        ]

    def insert_tag_info(
        self, hda_key_id: int | None = None, tag_lst: list[str] | None = None
    ) -> int | None:
        if tag_lst is None:
            return None
        query = "INSERT INTO tag_info (hda_key_id, tag) VALUES (:hda_key_id, :value)"
        try:
            dat: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "value": DatabaseValues._make_tag_to_string(tag_lst=tag_lst) or "",
            }
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** tag_info (insert) ***")
            logging.error(err)
            return None

    def update_tag_info(
        self, hda_key_id: int | None = None, tag_lst: Sequence[str] = ()
    ) -> int | None:
        tag_join_str = "#".join(normalize_tags(tag_lst))
        query = """
        UPDATE tag_info SET tag = :tag_join_str WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {
            "tag_join_str": tag_join_str,
            "hda_key_id": hda_key_id,
        }
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** tag_info (update) ***")
            logging.error(err)
            return None

    def is_exist_tag(self, hda_key_id: int | None = None) -> bool:
        query = """SELECT hda_key_id FROM tag_info"""
        query_params: dict[str, Any] = {}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if dat is not None:
            dat = [x[0] for x in dat]
            return hda_key_id in dat
        return False

    def get_tag_info(self, hda_key_id: int | None = None) -> None | list[Any]:
        query = "SELECT tag FROM tag_info WHERE hda_key_id = :hda_key_id"
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()
        if dat is None:
            return None
        dat = dat[0]
        if not len(dat):
            return None
        return [x.strip() for x in dat.split("#")]

    def distinct_tags(self, user_id: str | None = None) -> list[str]:
        """Vocabulary for completion and AI prompts; reads the trigger-maintained index."""
        query = f"""
        SELECT DISTINCT t.tag FROM asset_tags AS t
        JOIN hda_key AS k ON k.id = t.hda_key_id
        WHERE (:user_id IS NULL OR k.user_id = :user_id) AND k.id {LIVE_ASSET_IDS}
        ORDER BY t.tag COLLATE NOCASE
        """
        cursor = self._cursor.execute(query, {"user_id": user_id})
        return [row[0] for row in cursor.fetchall()]

    def insert_note_info(
        self, hda_key_id: int | None = None, note: str | None = None
    ) -> int | None:
        query = "INSERT INTO note_info (hda_key_id, note) VALUES (:hda_key_id, :note)"
        try:
            dat: dict[str, Any] = {"hda_key_id": hda_key_id, "note": note}
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** note_info (insert) ***")
            logging.error(err)
            return None

    def update_note_info(
        self, hda_key_id: int | None = None, note: str = ""
    ) -> int | None:
        query = """
        UPDATE note_info SET note = :note WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {"note": note, "hda_key_id": hda_key_id}
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** note_info (update) ***")
            logging.error(err)
            return None

    def is_exist_note(self, hda_key_id: int | None = None) -> bool:
        query = """SELECT hda_key_id FROM note_info"""
        query_params: dict[str, Any] = {}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if dat is not None:
            dat = [x[0] for x in dat]
            return hda_key_id in dat
        return False

    def get_note_info(self, hda_key_id: int | None = None) -> str | None:
        query = "SELECT note FROM note_info WHERE hda_key_id = :hda_key_id"
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()
        if dat is None:
            return None
        return dat[0]
