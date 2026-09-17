"""Read-only decoding of historical on-disk formats. Never used by live APIs."""

from __future__ import annotations

from typing import Any

_V1_HISTORY_FIELDS = (
    "hda_id",
    "comment",
    "org_hda_name",
    "version",
    "ihda_filename",
    "ihda_dirpath",
    "reg_time",
    "hou_version",
    "hip_filename",
    "hip_dirpath",
    "hda_license",
    "os",
    "node_old_path",
    "node_def_desc",
    "node_type_name",
    "node_category",
    "userid",
    "icon",
    "thumb_filename",
    "thumb_dirpath",
    "video_filename",
    "video_dirpath",
)


def receipt_history_v1(value: Any) -> dict[str, Any]:
    if not isinstance(value, list) or len(value) != len(_V1_HISTORY_FIELDS):
        raise ValueError("Invalid v1 registration history")
    return dict(zip(_V1_HISTORY_FIELDS, value, strict=True))


def receipt_connections_v1(value: Any) -> list[dict[str, Any]]:
    """Historical capture jobs stored each connection as four positional values."""
    if not isinstance(value, list):
        raise ValueError("Invalid v1 node connections")
    fields = ("port", "node_name", "node_type", "peer_port")
    result = []
    for connection in value:
        if not isinstance(connection, list) or len(connection) != len(fields):
            raise ValueError("Invalid v1 node connection")
        result.append(dict(zip(fields, connection, strict=True)))
    return result


def fingerprint_connections(value: list[dict[str, Any]]) -> list[list[Any]]:
    """Keep operation fingerprints identical to pre-v2 capture jobs.

    This representation is used only for hashing, never by a live record API.
    """
    return [
        [item["port"], item["node_name"], item["node_type"], item["peer_port"]]
        for item in value
    ]


def journal_moves_v1(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("Invalid v1 journal moves")
    result = []
    for move in value:
        if (
            not isinstance(move, list)
            or len(move) != 2
            or not all(isinstance(path, str) for path in move)
        ):
            raise ValueError("Invalid v1 journal move")
        source, destination = move
        result.append({"source": source, "destination": destination})
    return result


def receipt_owner_v1(value: Any) -> dict[str, int] | None:
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise ValueError("Invalid v1 file ownership")
    device, inode = value
    return {"device": device, "inode": inode}
