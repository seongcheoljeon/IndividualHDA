"""Nodes queries; transactions are owned by the shared session."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from libs.asset_contracts import NodeConnection
from libs.database.rows import named_query
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
        VALUES (:hda_key_id, :type_name, :def_desc, :is_net, :is_sub_net, :old_path)
        """
        try:
            dat: dict[str, Any] = {
                "hda_key_id": hda_key_id,
                "type_name": type_name,
                "def_desc": def_desc,
                "is_net": is_net,
                "is_sub_net": is_sub_net,
                "old_path": old_path,
            }
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** node_info (insert) ***")
            logging.error(err)
            return None

    def insert_houdini_node_category_path_info(
        self, info_id: int | None = None, node_category_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_category_lst):
            return None
        join_str = ",".join([x.strip() for x in node_category_lst])
        query = "INSERT INTO houdini_node_category_path_info (info_id, node_category) VALUES (:info_id, :join_str)"
        try:
            dat: dict[str, Any] = {"info_id": info_id, "join_str": join_str}
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** node_category_path_info (insert) ***")
            logging.error(err)
            return None

    def insert_houdini_node_type_path_info(
        self, info_id: int | None = None, node_type_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_type_lst):
            return None
        join_str = ",".join([x.strip() for x in node_type_lst])
        query = "INSERT INTO houdini_node_type_path_info (info_id, node_type) VALUES (:info_id, :join_str)"
        try:
            dat: dict[str, Any] = {"info_id": info_id, "join_str": join_str}
            cursor = self._cursor.execute(query, dat)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** node_type_path_info (insert) ***")
            logging.error(err)
            return None

    def insert_houdini_node_input_connect_info(
        self,
        info_id: int | None = None,
        node_input_connect_lst: Sequence[NodeConnection] = (),
    ) -> int | None:
        query = """
        INSERT INTO houdini_node_input_connect_info
            (info_id, curt_node_input_idx, connect_node_name, connect_node_type, connect_output_idx)
        VALUES
            (:info_id, :port, :node_name, :node_type, :peer_port)
        """
        try:
            dat = [
                {"info_id": info_id, **asdict(connection)}
                for connection in node_input_connect_lst
            ]
            cursor = self._cursor.executemany(query, dat)
            self._commit()
            return cursor.rowcount
            # return True
        except Exception as err:
            self._rollback()
            logging.error("*** node_input_connect_info (insert) ***")
            logging.error(err)
            return None

    def insert_houdini_node_output_connect_info(
        self,
        info_id: int | None = None,
        node_output_connect_lst: Sequence[NodeConnection] = (),
    ) -> int | None:
        query = """
        INSERT INTO houdini_node_output_connect_info
            (info_id, curt_node_output_idx, connect_node_name, connect_node_type, connect_input_idx)
        VALUES
            (:info_id, :port, :node_name, :node_type, :peer_port)
        """
        try:
            dat = [
                {"info_id": info_id, **asdict(connection)}
                for connection in node_output_connect_lst
            ]
            cursor = self._cursor.executemany(query, dat)
            self._commit()
            return cursor.rowcount
            # return True
        except Exception as err:
            self._rollback()
            logging.error("*** node_output_connect_info (insert) ***")
            logging.error(err)
            return None

    def update_houdini_node_info(
        self, hda_key_id: int | None = None, node_path: str | None = None
    ) -> int | None:
        query = """
        UPDATE houdini_node_info SET node_old_path = :node_path WHERE hda_key_id = :hda_key_id
        """
        query_params: dict[str, Any] = {
            "node_path": node_path,
            "hda_key_id": hda_key_id,
        }
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** houdini_node_info (update) ***")
            logging.error(err)
            return None

    def update_houdini_node_category_path_info(
        self, info_id: int | None = None, node_category_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_category_lst):
            return None
        join_str = ",".join([x.strip() for x in node_category_lst])
        query = """
        UPDATE houdini_node_category_path_info SET node_category = :join_str WHERE info_id = :info_id
        """
        query_params: dict[str, Any] = {"join_str": join_str, "info_id": info_id}
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** houdini_node_category_path_info (update) ***")
            logging.error(err)
            return None

    def update_houdini_node_type_path_info(
        self, info_id: int | None = None, node_type_lst: Sequence[Any] = ()
    ) -> int | None:
        if not len(node_type_lst):
            return None
        join_str = ",".join([x.strip() for x in node_type_lst])
        query = """
        UPDATE houdini_node_type_path_info SET node_type = :join_str WHERE info_id = :info_id
        """
        query_params: dict[str, Any] = {"join_str": join_str, "info_id": info_id}
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** houdini_node_type_path_info (update) ***")
            logging.error(err)
            return None

    def update_houdini_node_input_connect_info(
        self,
        info_id: int | None = None,
        node_input_connect_lst: Sequence[NodeConnection] = (),
    ) -> int | None:
        _ = self.delete_houdini_node_input_connect_info(info_id=info_id)
        is_hou_node_input_connect_info = self.insert_houdini_node_input_connect_info(
            info_id=info_id, node_input_connect_lst=node_input_connect_lst
        )
        return is_hou_node_input_connect_info

    def update_houdini_node_output_connect_info(
        self,
        info_id: int | None = None,
        node_output_connect_lst: Sequence[NodeConnection] = (),
    ) -> int | None:
        _ = self.delete_houdini_node_output_connect_info(info_id=info_id)
        is_hou_node_output_connect_info = self.insert_houdini_node_output_connect_info(
            info_id=info_id, node_output_connect_lst=node_output_connect_lst
        )
        return is_hou_node_output_connect_info

    def delete_houdini_node_input_connect_info(
        self, info_id: int | None = None
    ) -> int | None:
        query = """
        DELETE FROM houdini_node_input_connect_info WHERE info_id = :info_id
        """
        query_params: dict[str, Any] = {"info_id": info_id}
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** houdini_node_input_connect_info (delete) ***")
            logging.error(err)
            return None

    def delete_houdini_node_output_connect_info(
        self, info_id: int | None = None
    ) -> int | None:
        query = """
        DELETE FROM houdini_node_output_connect_info WHERE info_id = :info_id
        """
        query_params: dict[str, Any] = {"info_id": info_id}
        try:
            cursor = self._cursor.execute(query, query_params)
            self._commit()
            return cursor.rowcount
        except Exception as err:
            self._rollback()
            logging.error("*** houdini_node_output_connect_info (delete) ***")
            logging.error(err)
            return None

    def get_hou_node_info_id(self, hda_key_id: int | None = None) -> int | None:
        query = "SELECT id FROM houdini_node_info WHERE hda_key_id = :hda_key_id"
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_hda_node_type(self, hda_key_id: int | None = None) -> str | None:
        query = "SELECT node_type_name FROM houdini_node_info WHERE hda_key_id = :hda_key_id"
        query_params: dict[str, Any] = {"hda_key_id": hda_key_id}
        cursor = self._cursor.execute(query, query_params)
        dat = cursor.fetchone()[0]
        return dat

    def get_houdini_node_input_connect_info(
        self, info_id: int | None = None
    ) -> tuple[NodeConnection, ...]:
        query = """SELECT curt_node_input_idx AS port, connect_node_name AS node_name,
            connect_node_type AS node_type, connect_output_idx AS peer_port
            FROM houdini_node_input_connect_info WHERE info_id=:info_id"""
        return tuple(
            NodeConnection(**dict(row))
            for row in named_query(self._connect, query, {"info_id": info_id})
        )

    def get_houdini_node_output_connect_info(
        self, info_id: int | None = None
    ) -> tuple[NodeConnection, ...]:
        query = """SELECT curt_node_output_idx AS port, connect_node_name AS node_name,
            connect_node_type AS node_type, connect_input_idx AS peer_port
            FROM houdini_node_output_connect_info WHERE info_id=:info_id"""
        return tuple(
            NodeConnection(**dict(row))
            for row in named_query(self._connect, query, {"info_id": info_id})
        )
