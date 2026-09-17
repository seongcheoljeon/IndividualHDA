"""Named application records, independent of storage and Qt."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class SceneRecord:
    library_uuid: str | None = None
    asset_uuid: str | None = None
    version_uuid: str | None = None
    link_status: str = ""
    record_id: int
    hda_id: int
    hip_filename: str | None = None
    hip_dirpath: Path | None = None
    hda_filename: str | None = None
    hda_dirpath: Path | None = None
    parent_node_path: str = ""
    node_type: str = ""
    node_cate: str = ""
    node_name: str
    node_ver: str
    houdini_version: str = ""
    houdini_license: str = ""
    operating_system: str = ""
    sf: float = 0.0
    ef: float = 0.0
    fps: float = 0.0
    ctime: str = ""
    mtime: str = ""
    thumb_dirpath: Path | None = None
    thumb_filename: str | None = None
    video_dirpath: Path | None = None
    video_filename: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SceneRecordInput:
    hda_key_id: int
    hip_filename: str
    hip_dirpath: Path
    hda_filename: str
    hda_dirpath: Path
    parent_node_path: str
    node_type: str
    node_cate: str
    node_name: str
    node_ver: str
    hou_version: str
    hou_license: str
    operating_sys: str
    sf: float
    ef: float
    fps: float
    version_uuid: str | None = None
