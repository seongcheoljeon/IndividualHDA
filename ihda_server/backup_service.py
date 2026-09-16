"""Backup/restore orchestration through a narrow database adapter port."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Protocol

from ihda_server.backup_files import (
    FORMAT_VERSION,
    copy_verified,
    fingerprint,
    verify_bundle,
)
from ihda_server.storage_lock import storage_lock
from libs.library_metadata import utc_now
from libs.operation_journal import sync_directory, sync_tree
from libs.settings_store import save_json


class BackupDatabase(Protocol):
    def snapshot(self) -> AbstractContextManager[tuple[str, dict[str, Any]]]: ...
    def dump(self, snapshot: str, output: Path) -> None: ...
    def restore_target(self) -> AbstractContextManager[None]: ...
    def restore(self, dump: Path) -> None: ...
    def inspect_restored(self) -> dict[str, Any]: ...


def separate_paths(first: Path, second: Path) -> None:
    if first.resolve().is_relative_to(
        second.resolve()
    ) or second.resolve().is_relative_to(first.resolve()):
        raise ValueError("Backup and blob directories must not overlap")


class BackupService:
    def __init__(
        self,
        database: BackupDatabase,
        progress: Callable[[str], None] = lambda message: None,
    ) -> None:
        self.database, self.progress = database, progress

    def create(self, blobs: Path, destination: Path) -> dict[str, Any]:
        separate_paths(blobs, destination)
        if blobs.is_symlink() or not blobs.is_dir():
            raise ValueError(
                "Source blob directory does not exist or is a symbolic link"
            )
        if destination.exists() or destination.is_symlink():
            raise ValueError("Backup destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with storage_lock(blobs), storage_lock(destination.parent):
            if destination.exists():
                raise ValueError("Backup destination already exists")
            staging = Path(
                tempfile.mkdtemp(prefix=".backup-partial-", dir=destination.parent)
            )
            try:
                with self.database.snapshot() as (snapshot, inventory):
                    self.progress("Creating PostgreSQL snapshot dump…")
                    self.database.dump(snapshot, staging / "database.dump")
                    files = {"database.dump": fingerprint(staging / "database.dump")}
                    for index, (digest, size) in enumerate(
                        sorted(inventory["blobs"].items()), 1
                    ):
                        self.progress(
                            f"Backing up file {index} of {len(inventory['blobs'])}…"
                        )
                        name = f"blobs/{digest[:2]}/{digest}"
                        expected = {"sha256": digest, "size": size}
                        source = blobs / digest[:2] / digest
                        if source.parent.is_symlink():
                            raise ValueError("Blob directory contains a symbolic link")
                        copy_verified(source, staging / name, expected)
                        files[name] = expected
                manifest = {
                    "format": FORMAT_VERSION,
                    "complete": True,
                    "created_at": utc_now(),
                    "inventory": inventory,
                    "files": files,
                }
                save_json(staging / "manifest.json", manifest)
                self.progress("Verifying the backup bundle…")
                verify_bundle(staging)
                sync_tree(staging)
                os.rename(staging, destination)
                sync_directory(destination.parent)
                return {
                    "status": "backup_complete",
                    "path": str(destination),
                    "files": len(files) - 1,
                    "bytes": sum(item["size"] for item in files.values()),
                }
            finally:
                if staging.exists():
                    shutil.rmtree(staging)

    def restore(self, bundle: Path, destination: Path) -> dict[str, Any]:
        separate_paths(bundle, destination)
        self.progress("Verifying the backup before restoring…")
        manifest = verify_bundle(bundle)
        if destination.exists() or destination.is_symlink():
            raise ValueError("Restore blob destination must be a new path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with storage_lock(destination.parent), self.database.restore_target():
            if destination.exists():
                raise ValueError("Restore blob destination must be a new path")
            staging = Path(
                tempfile.mkdtemp(prefix=".restore-partial-", dir=destination.parent)
            )
            try:
                for name, expected in manifest["files"].items():
                    if name.startswith("blobs/"):
                        copy_verified(
                            bundle / name,
                            staging / name.removeprefix("blobs/"),
                            expected,
                        )
                # Freeze the verified dump too, so replacement of the bundle during
                # restoration cannot change the executed archive after verification.
                dump = staging / "database.dump"
                copy_verified(
                    bundle / "database.dump", dump, manifest["files"]["database.dump"]
                )
                self.progress("Restoring into the empty PostgreSQL target…")
                self.database.restore(dump)
                self.progress("Comparing restored records and file ownership…")
                if self.database.inspect_restored() != manifest["inventory"]:
                    raise ValueError(
                        "Restored database differs from the backup. Keep the target offline and use a new empty target to retry."
                    )
                dump.unlink()
                report = {
                    "status": "restore_verified",
                    "verified_at": utc_now(),
                    "source_created_at": manifest["created_at"],
                    "inventory": manifest["inventory"],
                }
                save_json(staging / ".ihda-restore.json", report)
                sync_tree(staging)
                os.rename(staging, destination)
                sync_directory(destination.parent)
                return {
                    "status": "restore_verified",
                    "path": str(destination),
                    "files": len(manifest["files"]) - 1,
                }
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
