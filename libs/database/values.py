"""Database value conversions and public row layouts."""

from __future__ import annotations

import re
import socket
import struct
from collections.abc import Iterable, Sequence

import public

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
            public.Key.Record.record_id,
            public.Key.Record.hda_id,
            public.Key.Record.hip_filename,
            public.Key.Record.hip_dirpath,
            public.Key.Record.hda_filename,
            public.Key.Record.hda_dirpath,
            public.Key.Record.parent_node_path,
            public.Key.Record.node_type,
            public.Key.Record.node_cate,
            public.Key.Record.node_name,
            public.Key.Record.node_ver,
            public.Key.Record.houdini_version,
            public.Key.Record.houdini_license,
            public.Key.Record.operating_system,
            public.Key.Record.sf,
            public.Key.Record.ef,
            public.Key.Record.fps,
            public.Key.Record.ctime,
            public.Key.Record.mtime,
        ]
        return key_lst

    @staticmethod
    def hda_history_key_lst() -> list[str]:
        key_lst = [
            public.Key.History.hist_id,
            public.Key.History.hda_id,
            public.Key.History.comment,
            public.Key.History.org_hda_name,
            public.Key.History.version,
            public.Key.History.ihda_filename,
            public.Key.History.ihda_dirpath,
            public.Key.History.reg_time,
            public.Key.History.hou_version,
            public.Key.History.hip_filename,
            public.Key.History.hip_dirpath,
            public.Key.History.hda_license,
            public.Key.History.os,
            public.Key.History.node_old_path,
            public.Key.History.node_def_desc,
            public.Key.History.node_type_name,
            public.Key.History.node_category,
            public.Key.History.userid,
            public.Key.History.icon,
            public.Key.History.tags,
            public.Key.History.thumb_filename,
            public.Key.History.thumb_dirpath,
            public.Key.History.video_filename,
            public.Key.History.video_dirpath,
        ]
        return key_lst

    @staticmethod
    def hda_info_key_lst() -> list[str]:
        key_lst = [
            public.Key.hda_id,
            public.Key.hda_name,
            public.Key.hda_cate,
            public.Key.hda_version,
            public.Key.hda_filename,
            public.Key.hda_dirpath,
            public.Key.is_favorite_hda,
            public.Key.hda_load_count,
            public.Key.hda_ctime,
            public.Key.hda_mtime,
            public.Key.hou_version,
            public.Key.node_type_name,
            public.Key.node_def_desc,
            public.Key.is_network,
            public.Key.is_sub_network,
            public.Key.node_old_path,
            public.Key.hda_license,
            public.Key.hip_filename,
            public.Key.hip_dirpath,
            public.Key.thumbnail_filename,
            public.Key.thumbnail_dirpath,
            public.Key.video_filename,
            public.Key.video_dirpath,
            public.Key.hda_note,
            # list
            public.Key.hda_icon,
            public.Key.hda_tags,
        ]
        return key_lst
