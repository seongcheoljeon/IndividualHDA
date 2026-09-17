"""Versioned backup bundles and streaming file verification."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from libs.file_integrity import FILE_READ_CHUNK_BYTES, measure_file

FORMAT_VERSION = 1
MAX_MANIFEST_BYTES = 64 * 1024**2


def fingerprint(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or unsafe backup file: {path.name}")
    content = measure_file(path)
    return {"sha256": content.digest, "size": content.size}


def copy_verified(source: Path, target: Path, expected: dict[str, Any]) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"Missing or unsafe source file: {source.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as incoming, target.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, FILE_READ_CHUNK_BYTES)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if fingerprint(target) != expected:
        raise ValueError(f"File size or SHA-256 mismatch: {source.name}")


def verify_bundle(root: Path) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Backup must be a completed directory bundle")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Invalid backup manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("format") != FORMAT_VERSION
        or manifest.get("complete") is not True
        or not isinstance(manifest.get("created_at"), str)
    ):
        raise ValueError("Unsupported or incomplete backup")
    files = manifest.get("files")
    if not isinstance(files, dict) or "database.dump" not in files:
        raise ValueError("Backup has no database dump")
    inventory = manifest.get("inventory", {})
    if (
        not isinstance(inventory, dict)
        or not isinstance(inventory.get("blobs"), dict)
        or not isinstance(inventory.get("tables"), dict)
    ):
        raise ValueError("Backup inventory is missing")
    from ihda_server.backup_schema import backup_tables

    version = inventory.get("schema_version")
    if type(version) is not int:
        raise ValueError("Backup schema version must be an integer")
    if set(inventory["tables"]) != {table.name for table in backup_tables(version)}:
        raise ValueError("Backup schema is unsupported or incomplete")
    for summary in inventory["tables"].values():
        if (
            not isinstance(summary, dict)
            or set(summary) != {"rows", "sha256"}
            or type(summary["rows"]) is not int
            or summary["rows"] < 0
            or not isinstance(summary["sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", summary["sha256"])
        ):
            raise ValueError("Invalid backup table inventory")
    blob_files = {}
    for digest, size in inventory["blobs"].items():
        if (
            not re.fullmatch(r"[a-f0-9]{64}", digest)
            or not isinstance(size, int)
            or size < 0
        ):
            raise ValueError("Invalid backup blob inventory")
        blob_files[f"blobs/{digest[:2]}/{digest}"] = {"sha256": digest, "size": size}
    if {
        name: entry for name, entry in files.items() if name != "database.dump"
    } != blob_files:
        raise ValueError("Backup files do not match the database inventory")
    expected_paths = {"manifest.json"}
    for name, expected in files.items():
        if name != "database.dump" and not re.fullmatch(
            r"blobs/[a-f0-9]{2}/[a-f0-9]{64}", name
        ):
            raise ValueError("Unsafe backup file path")
        if name.startswith("blobs/") and name.split("/")[1] != name.split("/")[2][:2]:
            raise ValueError("Invalid blob directory")
        path = root / name
        for parent in path.parents:
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError("Backup contains a symbolic link")
        if fingerprint(path) != expected:
            raise ValueError(f"Backup file size or SHA-256 mismatch: {name}")
        if name.startswith("blobs/") and expected["sha256"] != path.name:
            raise ValueError("Blob content does not match its identity")
        expected_paths.add(name)
    for path in root.rglob("*"):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ValueError("Backup contains an unsafe entry")
        if path.is_file() and path.relative_to(root).as_posix() not in expected_paths:
            raise ValueError("Backup contains unlisted files")
    return dict(manifest)
