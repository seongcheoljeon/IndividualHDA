"""Stable view column identities; numeric values preserve saved header layouts."""

from enum import IntEnum
from typing import Self


class ViewColumn(IntEnum):
    label: str
    field: str

    def __new__(cls, position: int, label: str = "", field: str = "") -> Self:
        member = int.__new__(cls, position)
        member._value_ = position
        member.label = label
        member.field = field
        return member


class AssetColumn(ViewColumn):
    NAME = (0, "Name", "hda_name")
    DEFINITION = (1, "Definition", "node_def_desc")
    FAVORITE = (2, "Like", "is_favorite_hda")
    VERSION = (3, "Version", "hda_version")
    USE_COUNT = (4, "Count", "hda_load_count")
    CREATED = (5, "Created Date", "hda_ctime")
    MODIFIED = (6, "Modified Date", "hda_mtime")
    HOUDINI = (7, "Houdini", "hou_version")
    LICENSE = (8, "License", "hda_license")


class HistoryColumn(ViewColumn):
    ID = (0, "ID", "hist_id")
    NAME = (1, "Name", "org_hda_name")
    DEFINITION = (2, "Definition", "node_def_desc")
    CATEGORY = (3, "Category", "node_category")
    COMMENT = (4, "Comment", "comment")
    VERSION = (5, "Version", "version")
    CREATED = (6, "Date Time", "reg_time")
    TYPE = (7, "Type", "node_type_name")
    NODE_PATH = (8, "Node Path", "node_old_path")
    HOUDINI = (9, "Houdini", "hou_version")
    LICENSE = (10, "License", "hda_license")
    OS = (11, "OS", "os")
    HIP_FOLDER = (12, "HIP Folder", "hip_dirpath")
    HIP_FILE = (13, "HIP File", "hip_filename")


class RecordColumn(ViewColumn):
    NAME = (0, "Record", "name")
    TYPE = (1, "Type", "node_type")
    CATEGORY = (2, "Category", "category")
    VERSION = (3, "Version", "version")
    CREATED = (4, "Created", "ctime")
    MODIFIED = (5, "Modified", "mtime")
    HOUDINI = (6, "HIP Version", "houdini_version")
    LICENSE = (7, "HIP License", "houdini_license")
    OS = (8, "OS", "operating_system")
    START_FRAME = (9, "SF", "sf")
    END_FRAME = (10, "EF", "ef")
    FPS = (11, "FPS", "fps")


class InsideColumn(ViewColumn):
    NAME = (0, "Name", "name")
    TYPE = (1, "Type", "node_type")
    CATEGORY = (2, "Category", "category")
    VERSION = (3, "Version", "version")
    DESCRIPTION = (4, "Descript", "node_descript")
    CREATED = (5, "Created", "created_time")
    MODIFIED = (6, "Modified", "modified_time")
