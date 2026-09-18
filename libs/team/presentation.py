"""Translate remote documents for the existing models; no Qt or local database."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from libs.asset_contracts import AssetData, HistoryData
from libs.history_activity import local_time


def display_time(value: str) -> str:
    # Local time, like the personal library, so mixed rows sort and filter alike.
    return local_time(value)


def asset_row(document: dict[str, Any], cache_root: Path) -> AssetData:
    metadata = document.get("metadata", {})
    files = document.get("files", {})
    asset = files.get("asset", {})
    thumbnail_blob = files.get("thumbnail")
    thumbnail = (
        cache_root / thumbnail_blob["digest"] / thumbnail_blob["filename"]
        if thumbnail_blob
        else None
    )
    return AssetData(
        hda_id=document["id"],
        hda_name=document["name"],
        hda_cate=document["category"],
        hda_version=document["version"],
        hda_note=document.get("note", ""),
        hda_tags=tuple(document.get("tags", [])),
        is_favorite_hda=bool(document.get("favorite")),
        hda_icon=tuple(
            metadata.get("node_icon_path_list")
            or metadata.get("hda_icon")
            or ["SOP", "box"]
        ),
        hda_dirpath=cache_root / asset.get("digest", "missing"),
        hda_filename=asset.get("filename", "asset.hda"),
        thumbnail_dirpath=Path(thumbnail).parent if thumbnail else None,
        thumbnail_filename=Path(thumbnail).name if thumbnail else None,
        video_dirpath=None,
        video_filename=None,
        hip_dirpath=None,
        hip_filename=None,
        hda_load_count=document.get("use_count", 0),
        hda_ctime=display_time(document.get("created_at", "")),
        hda_mtime=display_time(document.get("updated_at", "")),
        hou_version=metadata.get("hou_version", ""),
        node_old_path=metadata.get("node_old_path", ""),
        hda_license=metadata.get("hda_license", ""),
        node_type_name=metadata.get("node_type_name", ""),
        node_cate_name=document["category"],
        node_def_desc=metadata.get("node_def_desc", ""),
        node_type_path_list=metadata.get("node_type_path_list", []),
        node_cate_path_list=metadata.get("node_cate_path_list", []),
        node_input_connections=metadata.get("node_input_connections", []),
        node_output_connections=metadata.get("node_output_connections", []),
        is_network=bool(metadata.get("is_network")),
        is_sub_network=bool(metadata.get("is_sub_network")),
        remote=True,
        library_id=document.get("project_id", ""),
    )


def history_row(item: dict[str, Any], cache_root: Path) -> HistoryData:
    document = item["document"]
    row = asset_row(document, cache_root)
    return HistoryData(
        hist_id=item["id"],
        hda_id=document["id"],
        comment=document.get("description", ""),
        org_hda_name=document["name"],
        version=item["version"],
        ihda_filename=row.hda_filename,
        ihda_dirpath=row.hda_dirpath,
        reg_time=row.hda_mtime,
        hou_version=row.hou_version,
        hip_filename=None,
        hip_dirpath=None,
        hda_license=row.hda_license,
        os="",
        node_old_path=row.node_old_path,
        node_def_desc=row.node_def_desc,
        node_type_name=row.node_type_name,
        node_category=document["category"],
        userid=document.get("created_by", ""),
        icon=row.hda_icon,
        tags=row.hda_tags,
        hda_note=row.hda_note,
        thumb_dirpath=row.thumbnail_dirpath,
        thumb_filename=row.thumbnail_filename,
        video_dirpath=None,
        video_filename=None,
        remote=True,
        library_id=document.get("project_id", ""),
    )
