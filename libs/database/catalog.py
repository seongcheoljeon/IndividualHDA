"""Catalog queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
from typing import Any

from libs import log_handler
from libs.database.session import DatabaseSession


class CatalogOperations(DatabaseSession):
    def insert_users(
        self, user_id: str | None = None, email: str | None = None
    ) -> int | None:
        query = """
        INSERT INTO users (user_id, email, join_datetime)
        VALUES (?, ?, (SELECT DATETIME('now', 'localtime')))
        """
        try:
            dat: tuple[Any, ...] = (user_id, email)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** users (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hda_category(
        self, category: str | None = None, user_id: str | None = None
    ) -> int | None:
        query = """
        INSERT INTO hda_category (category, user_id)
            SELECT ?, ?
            WHERE NOT EXISTS (SELECT * FROM hda_category WHERE category = ? AND user_id = ?)
        """
        try:
            dat: tuple[Any, ...] = (category, user_id, category, user_id)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_category (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hda_key(
        self,
        name: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> int | None:
        query = """INSERT INTO hda_key (name, category, user_id) VALUES (?, ?, ?)"""
        try:
            dat: tuple[Any, ...] = (name, category, user_id)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_key (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_hda_key_with_id(self, hda_key_id: int | None = None) -> int | None:
        query = "DELETE FROM hda_key WHERE id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** hda_key (delete) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def list_user_ids(self) -> list[str]:
        cursor = self._cursor.execute("SELECT user_id FROM users ORDER BY user_id")
        return [row[0] for row in cursor.fetchall()]

    def is_exist_user_id(self, user_id: str) -> bool:
        query = """SELECT COUNT(user_id) FROM users WHERE user_id = ?
        """
        query_params: tuple[Any, ...] = (user_id,)
        cursor = self._cursor.execute(query, query_params)
        return bool(cursor.fetchone()[0])

    def get_user_id(self) -> list[str]:
        query = "SELECT user_id FROM users"
        query_params: tuple[Any, ...] = ()
        cursor = self._cursor.execute(query, query_params)
        dat = [x[0] for x in cursor.fetchall()]
        return dat

    def get_hda_category(self, user_id: str | None = None) -> list[str]:
        query = """
        SELECT category FROM hda_category WHERE user_id = ? ORDER BY category
        """
        query_params: tuple[Any, ...] = (user_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = [x[0] for x in cursor.fetchall()]
        return dat

    def get_hda_key_id(
        self,
        category: str | None = None,
        name: str | None = None,
        user_id: str | None = None,
    ) -> list[int] | None:
        filters = [("user_id", user_id), ("category", category), ("name", name)]
        selected = [(column, value) for column, value in filters if value is not None]
        query = "SELECT id FROM hda_key"
        query_params: tuple[Any, ...] = tuple(value for _, value in selected)
        if selected:
            query += " WHERE " + " AND ".join(column + " = ?" for column, _ in selected)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        return [x[0] for x in fetch_dat]

    def get_count_hda_key(
        self,
        name: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> int:
        filters = {"name": name, "category": category, "user_id": user_id}
        selected = [(key, value) for key, value in filters.items() if value is not None]
        query = "SELECT COUNT(*) FROM hda_key"
        if selected:
            query += " WHERE " + " AND ".join(key + " = ?" for key, _ in selected)
        return self._cursor.execute(
            query, tuple(value for _, value in selected)
        ).fetchone()[0]
