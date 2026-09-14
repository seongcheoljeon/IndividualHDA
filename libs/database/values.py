"""Database value conversions and public row layouts."""

from __future__ import annotations

import re
import socket
import struct
from collections.abc import Iterable, Sequence

from libs.keys import Key

_TAG_SEPARATORS = re.compile(r"[#,\r\n]+")


def normalize_tags(tags: str | Iterable[str] | None) -> list[str]:
    """Split on #, comma or newline; strip; drop empties and case-insensitive repeats.

    Order of first appearance is kept. Tags never contain "#" because tag_info stores
    them "#"-joined (asset_tags is derived from that column by triggers).
    """
    if not tags:
        return []
    parts = [tags] if isinstance(tags, str) else list(tags)
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        for tag in _TAG_SEPARATORS.split(str(part)):
            tag = tag.strip()
            if not tag or tag.casefold() in seen:
                continue
            seen.add(tag.casefold())
            result.append(tag)
    return result


class DatabaseValues:
    @staticmethod
    def inet_aton(ip_str: str | None = None) -> int:
        if ip_str is None:
            raise ValueError("IP address is required")
        return struct.unpack(">L", socket.inet_aton(ip_str))[0]

    @staticmethod
    def inet_ntoa(packed_ip: int | None = None) -> str:
        return socket.inet_ntoa(struct.pack(">L", packed_ip))

    @staticmethod
    def _make_icon_to_string(icon_lst: Sequence[str] | None = None) -> None | str:
        if not icon_lst:
            return None
        return ",".join([x.strip() for x in icon_lst])

    @staticmethod
    def _make_tag_to_string(tag_lst: list[str] | None = None) -> None | str:
        tags = normalize_tags(tag_lst)
        return "#".join(tags) if tags else None

    @staticmethod
    def hda_record_key_lst() -> list[str]:
        key_lst = [
            Key.Record.record_id,
            Key.Record.hda_id,
            Key.Record.hip_filename,
            Key.Record.hip_dirpath,
            Key.Record.hda_filename,
            Key.Record.hda_dirpath,
            Key.Record.parent_node_path,
            Key.Record.node_type,
            Key.Record.node_cate,
            Key.Record.node_name,
            Key.Record.node_ver,
            Key.Record.houdini_version,
            Key.Record.houdini_license,
            Key.Record.operating_system,
            Key.Record.sf,
            Key.Record.ef,
            Key.Record.fps,
            Key.Record.ctime,
            Key.Record.mtime,
        ]
        return key_lst

    @staticmethod
    def hda_history_key_lst() -> list[str]:
        key_lst = [
            Key.History.hist_id,
            Key.History.hda_id,
            Key.History.comment,
            Key.History.org_hda_name,
            Key.History.version,
            Key.History.ihda_filename,
            Key.History.ihda_dirpath,
            Key.History.reg_time,
            Key.History.hou_version,
            Key.History.hip_filename,
            Key.History.hip_dirpath,
            Key.History.hda_license,
            Key.History.os,
            Key.History.node_old_path,
            Key.History.node_def_desc,
            Key.History.node_type_name,
            Key.History.node_category,
            Key.History.userid,
            Key.History.icon,
            Key.History.tags,
            Key.History.thumb_filename,
            Key.History.thumb_dirpath,
            Key.History.video_filename,
            Key.History.video_dirpath,
        ]
        return key_lst

    @staticmethod
    def hda_info_key_lst() -> list[str]:
        key_lst = [
            Key.hda_id,
            Key.hda_name,
            Key.hda_cate,
            Key.hda_version,
            Key.hda_filename,
            Key.hda_dirpath,
            Key.is_favorite_hda,
            Key.hda_load_count,
            Key.hda_ctime,
            Key.hda_mtime,
            Key.hou_version,
            Key.node_type_name,
            Key.node_def_desc,
            Key.is_network,
            Key.is_sub_network,
            Key.node_old_path,
            Key.hda_license,
            Key.hip_filename,
            Key.hip_dirpath,
            Key.thumbnail_filename,
            Key.thumbnail_dirpath,
            Key.video_filename,
            Key.video_dirpath,
            Key.hda_note,
            # list
            Key.hda_icon,
            Key.hda_tags,
        ]
        return key_lst
