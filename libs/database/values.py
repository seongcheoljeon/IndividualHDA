"""Database value conversions and public row layouts."""

from __future__ import annotations

import socket
import struct
from collections.abc import Sequence

from libs.tags import normalize_tags as normalize_tags


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
