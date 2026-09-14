"""Nodes queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from libs import log_handler
from libs.database.session import DatabaseSession


class NodesOperations(DatabaseSession):
    def insert_houdini_node_info(
        self,
        hda_key_id: int | None = None,
        type_name: Any = None,
        def_desc: Any = None,
        is_net: bool | None = None,
        is_sub_net: bool | None = None,
        old_path: Any = None,
    ) -> int | None:
        query = """
        INSERT INTO houdini_node_info
            (hda_key_id, node_type_name, node_def_desc, is_network, is_sub_network, node_old_path)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            dat: tuple[Any, ...] = (
                hda_key_id,
                type_name,
                def_desc,
                is_net,
                is_sub_net,
                old_path,
            )
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** node_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_category_path_info(
        self, info_id: int | None = None, node_category_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_category_lst):
            return None
        join_str = ",".join([x.strip() for x in node_category_lst])
        query = """INSERT INTO houdini_node_category_path_info (info_id, node_category) VALUES (?, ?)"""
        try:
            dat: tuple[Any, ...] = (info_id, join_str)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** node_category_path_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_type_path_info(
        self, info_id: int | None = None, node_type_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_type_lst):
            return None
        join_str = ",".join([x.strip() for x in node_type_lst])
        query = """INSERT INTO houdini_node_type_path_info (info_id, node_type) VALUES (?, ?)"""
        try:
            dat: tuple[Any, ...] = (info_id, join_str)
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** node_type_path_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_input_connect_info(
        self, info_id: int | None = None, node_input_connect_lst: Sequence[Any] = ()
    ) -> int | None:
        query = """
        INSERT INTO houdini_node_input_connect_info
            (info_id, curt_node_input_idx, connect_node_name, connect_node_type, connect_output_idx)
        VALUES
            (?, ?, ?, ?, ?)
        """
        try:
            dat = tuple([tuple([info_id] + x) for x in node_input_connect_lst])
            cursor = self._cursor.executemany(query, dat)
            self._commit()
            return cursor.rowcount
            # return True
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** node_input_connect_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_output_connect_info(
        self, info_id: int | None = None, node_output_connect_lst: Sequence[Any] = ()
    ) -> int | None:
        query = """
        INSERT INTO houdini_node_output_connect_info
            (info_id, curt_node_output_idx, connect_node_name, connect_node_type, connect_input_idx)
        VALUES
            (?, ?, ?, ?, ?)
        """
        try:
            dat = tuple([tuple([info_id] + x) for x in node_output_connect_lst])
            cursor = self._cursor.executemany(query, dat)
            self._commit()
            return cursor.rowcount
            # return True
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** node_output_connect_info (insert) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_info(
        self, hda_key_id: int | None = None, node_path: str | None = None
    ) -> int | None:
        query = """
        UPDATE houdini_node_info SET node_old_path = ? WHERE hda_key_id = ?
        """
        query_params: tuple[Any, ...] = (node_path, hda_key_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** houdini_node_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_category_path_info(
        self, info_id: int | None = None, node_category_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_category_lst):
            return None
        join_str = ",".join([x.strip() for x in node_category_lst])
        query = """
        UPDATE houdini_node_category_path_info SET node_category = ? WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (join_str, info_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="*** houdini_node_category_path_info (update) ***",
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_type_path_info(
        self, info_id: int | None = None, node_type_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_type_lst):
            return None
        join_str = ",".join([x.strip() for x in node_type_lst])
        query = """
        UPDATE houdini_node_type_path_info SET node_type = ? WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (join_str, info_id)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** houdini_node_type_path_info (update) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_input_connect_info(
        self, info_id: int | None = None, node_input_connect_lst: Sequence[Any] = ()
    ) -> int | None:
        _ = self.delete_houdini_node_input_connect_info(info_id=info_id)
        is_hou_node_input_connect_info = self.insert_houdini_node_input_connect_info(
            info_id=info_id, node_input_connect_lst=node_input_connect_lst
        )
        return is_hou_node_input_connect_info

    def update_houdini_node_output_connect_info(
        self, info_id: int | None = None, node_output_connect_lst: Sequence[Any] = ()
    ) -> int | None:
        _ = self.delete_houdini_node_output_connect_info(info_id=info_id)
        is_hou_node_output_connect_info = self.insert_houdini_node_output_connect_info(
            info_id=info_id, node_output_connect_lst=node_output_connect_lst
        )
        return is_hou_node_output_connect_info

    def delete_houdini_node_category_path_info(
        self, info_id: int | None = None
    ) -> int | None:
        query = """
        DELETE FROM houdini_node_category_path_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="*** houdini_node_category_path_info (delete) ***",
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_houdini_node_type_path_info(
        self, info_id: int | None = None
    ) -> int | None:
        query = """
        DELETE FROM houdini_node_type_path_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg="*** houdini_node_type_path_info (delete) ***"
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_houdini_node_input_connect_info(
        self, info_id: int | None = None
    ) -> int | None:
        query = """
        DELETE FROM houdini_node_input_connect_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="*** houdini_node_input_connect_info (delete) ***",
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_houdini_node_output_connect_info(
        self, info_id: int | None = None
    ) -> int | None:
        query = """
        DELETE FROM houdini_node_output_connect_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error,
                msg="*** houdini_node_output_connect_info (delete) ***",
            )
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def get_hou_node_info_id(self, hda_key_id: int | None = None) -> int | None:
        query = "SELECT id FROM houdini_node_info WHERE hda_key_id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_hda_node_type(self, hda_key_id: int | None = None) -> str | None:
        query = "SELECT node_type_name FROM houdini_node_info WHERE hda_key_id = ?"
        query_params: tuple[Any, ...] = (hda_key_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_houdini_node_input_connect_info(
        self, info_id: int | None = None
    ) -> None | list[Any]:
        query = """
        SELECT curt_node_input_idx, connect_node_name, connect_node_type, connect_output_idx
        FROM houdini_node_input_connect_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return None
        return [list(x) for x in dat]

    def get_houdini_node_output_connect_info(
        self, info_id: int | None = None
    ) -> None | list[Any]:
        query = """
        SELECT curt_node_output_idx, connect_node_name, connect_node_type, connect_input_idx
        FROM houdini_node_output_connect_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return None
        return [list(x) for x in dat]

    def get_houdini_node_category_path_info(
        self, info_id: int | None = None
    ) -> None | list[Any]:
        query = """
        SELECT node_category FROM houdini_node_category_path_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        return [x.strip() for x in fetch_dat[0].split(",")]

    def get_houdini_node_type_path_info(
        self, info_id: int | None = None
    ) -> None | list[Any]:
        query = """
        SELECT node_type FROM houdini_node_type_path_info WHERE info_id = ?
        """
        query_params: tuple[Any, ...] = (info_id,)
        cursor = self._cursor.execute(query, query_params)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        return [x.strip() for x in fetch_dat[0].split(",")]
