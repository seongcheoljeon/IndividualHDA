"""Consistent library snapshots and validated, portable archive extraction."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from libs.database_migrations import backup_database, migrate


def extract_archive(archive: Any, destination: str | Path) -> None:
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as source:
        seen = set()
        total = 0
        for member in source.infolist():
            path = PurePosixPath(member.filename)
            windows = PureWindowsPath(member.filename)
            mode = member.external_attr >> 16
            if (
                path.is_absolute()
                or windows.drive
                or "\\" in member.filename
                or ".." in path.parts
                or stat.S_ISLNK(mode)
                or any(":" in part or part.endswith((" ", ".")) for part in path.parts)
            ):
                raise ValueError(f"Unsafe archive entry: {member.filename}")
            key = member.filename.rstrip("/").casefold()
            if key in seen:
                raise ValueError(f"Duplicate archive entry: {member.filename}")
            seen.add(key)
            total += member.file_size
            if total > 100 * 1024**3 or len(seen) > 1_000_000:
                raise ValueError("Archive exceeds supported library size")
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Archive entry escapes staging directory")
        if "ihda.db" not in source.namelist():
            raise ValueError("Archive has no iHDA database")
        if total > shutil.disk_usage(destination).free:
            raise OSError("Insufficient free space to extract library")
        source.extractall(destination)


def create_archive(
    database: str | Path,
    assets: str | Path,
    destination: str | Path,
    *,
    reason: str = "Library export",
) -> Path:
    database, assets, destination = map(Path, (database, assets, destination))
    if not database.is_file():
        raise FileNotFoundError(database)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".ihda-export-", dir=destination.parent
    ) as temporary_name:
        temporary = Path(temporary_name)
        snapshot = temporary / "ihda.db"
        with closing(sqlite3.connect(str(database))) as source:
            backup_database(source, snapshot)
        output = temporary / "library.zip"
        with zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            for path in assets.rglob("*"):
                if path.is_symlink():
                    raise ValueError(f"Library contains a symbolic link: {path}")
                if (
                    path.is_file()
                    and not path.is_relative_to(temporary)
                    and path != destination
                ):
                    archive.write(path, path.relative_to(assets).as_posix())
            archive.write(snapshot, "ihda.db")
            archive.writestr(
                "ihda-manifest.json",
                json.dumps(
                    {"format": 1, "asset_root": assets.as_posix(), "reason": reason},
                    ensure_ascii=False,
                ),
            )
        os.replace(output, destination)
    return destination


def prepare_database(stage: str | Path, target_assets: str | Path) -> None:
    stage = Path(stage)
    database = stage / "ihda.db"
    with closing(sqlite3.connect(str(database))) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        migrate(connection, database)
        manifest = stage / "ihda-manifest.json"
        old_root = None
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data.get("format") != 1:
                raise ValueError("Unsupported archive format")
            old_root = data.get("asset_root")
        else:
            # Legacy archives used .../individualHDA/<userid>/<category>/<name>.
            row = connection.execute("SELECT dirpath FROM hda_info LIMIT 1").fetchone()
            if row:
                path = PurePosixPath(row[0].replace("\\", "/"))
                old_root = str(path.parent.parent)
        if old_root:
            root = PurePosixPath(old_root.replace("\\", "/"))
            for table, columns in {
                "hda_info": ("dirpath",),
                "thumbnail_info": ("dirpath",),
                "video_info": ("dirpath",),
                "hda_history": ("hda_dirpath", "thumb_dirpath", "video_dirpath"),
                "hda_node_location_record": ("hda_dirpath",),
            }.items():
                for column in columns:
                    rows = connection.execute(
                        f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL"
                    ).fetchall()
                    for identifier, value in rows:
                        path = PurePosixPath(value.replace("\\", "/"))
                        if not path.is_relative_to(root):
                            raise ValueError(
                                f"Asset path is outside the archived library: {value}"
                            )
                        relative = path.relative_to(root)
                        if ".." in relative.parts:
                            raise ValueError("Asset path escapes library root")
                        connection.execute(
                            f"UPDATE {table} SET {column} = ? WHERE id = ?",
                            (
                                str(Path(target_assets).joinpath(*relative.parts)),
                                identifier,
                            ),
                        )
        connection.commit()
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("Imported database failed integrity check")
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            raise sqlite3.IntegrityError("Imported database contains orphaned records")
    # Migration backups belong outside the asset directory.
    for backup in stage.glob("ihda.db.pre-*.bak"):
        backup.unlink()
    (stage / "ihda-manifest.json").unlink(missing_ok=True)
