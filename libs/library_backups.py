"""Full-library backups, staged restore validation and recovery-file cleanup."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from libs.archive_service import create_archive, extract_archive, prepare_database
from libs.library_maintenance import check_cancel, read_database, references
from libs.operation_journal import operation_lock


@dataclass(frozen=True)
class BackupEntry:
    path: Path
    size: int
    modified: float
    reason: str
    restorable: bool


def list_backups(directory: Path) -> list[BackupEntry]:
    result = []
    for path in sorted((directory / "backup").glob("*"), reverse=True):
        if path.is_file() and path.suffix.lower() == ".zip":
            reason, restorable = "Legacy backup", False
            try:
                with zipfile.ZipFile(path) as archive:
                    restorable = "ihda.db" in archive.namelist()
                    if "ihda-manifest.json" in archive.namelist():
                        info = archive.getinfo("ihda-manifest.json")
                        if info.file_size > 1024 * 1024:
                            raise ValueError("Manifest too large")
                        reason = json.loads(archive.read(info)).get("reason", reason)
                    if not restorable:
                        reason = "Recovery-file safety copy (manual recovery)"
            except (OSError, ValueError, zipfile.BadZipFile):
                reason = "Unreadable archive"
                restorable = False
            stat = path.stat()
            result.append(
                BackupEntry(path, stat.st_size, stat.st_mtime, str(reason), restorable)
            )
    for path in sorted(directory.glob("ihda.db.*.bak"), reverse=True):
        stat = path.stat()
        result.append(
            BackupEntry(
                path,
                stat.st_size,
                stat.st_mtime,
                "Database-only safety copy (manual recovery)",
                False,
            )
        )
    return result


def create_backup(database: Path, assets: Path, reason: str) -> Path:
    with operation_lock(database.parent):
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        return create_archive(
            database,
            assets,
            database.parent / "backup" / f"library-{stamp}.zip",
            reason=reason,
        )


def validate_backup(source: Path, cancel: threading.Event | None = None) -> str:
    check_cancel(cancel)
    with tempfile.TemporaryDirectory(prefix="ihda-validate-") as name:
        stage = Path(name)
        extract_archive(source, stage)
        check_cancel(cancel)
        prepare_database(stage, stage)
        missing = []
        with read_database(stage / "ihda.db", cancel) as connection:
            for ref in references(connection):
                check_cancel(cancel)
                if ref.table == "hipfile_info" or ref.column == "hip_dirpath":
                    continue
                if not ref.path.is_file():
                    missing.append(
                        str(ref.path.relative_to(stage))
                        if ref.path.is_relative_to(stage)
                        else str(ref.path)
                    )
        if missing:
            raise ValueError(
                "Backup has missing library files:\n" + "\n".join(missing[:30])
            )
    return "Archive, database constraints and all referenced library files verified."


@dataclass(frozen=True)
class RecoveryEntry:
    path: Path
    size: int
    fingerprint: str
    referenced: bool


def _inventory(path: Path) -> tuple[int, str]:
    digest, size = hashlib.sha256(), 0
    for item in [path, *sorted(path.rglob("*"))] if path.is_dir() else [path]:
        if item.is_symlink():
            raise ValueError(f"Symlink is not eligible for cleanup: {item}")
        info = item.stat()
        digest.update(
            f"{item}:{info.st_size}:{info.st_mtime_ns}:{info.st_ino}".encode()
        )
        if item.is_file():
            size += info.st_size
    return size, digest.hexdigest()


def recovery_files(
    database: Path, assets: Path, cancel: threading.Event | None = None
) -> list[RecoveryEntry]:
    with read_database(database, cancel) as connection:
        used = [ref.path.resolve() for ref in references(connection)]
    candidates = set(assets.parent.glob(assets.name + ".previous-*")) | set(
        database.parent.glob("ihda.db.previous-*")
    )
    candidates.update(
        path for path in assets.rglob(".ihda-deleted-*") if not path.is_symlink()
    )
    result = []
    for path in sorted(candidates):
        check_cancel(cancel)
        if not re.search(
            r"(?:\.ihda-deleted-[0-9a-f]{32}-.+|\.previous-[0-9a-f]{32})$", path.name
        ):
            continue
        if any(parent in candidates for parent in path.parents):
            continue
        size, fingerprint = _inventory(path)
        resolved = path.resolve()
        result.append(
            RecoveryEntry(
                path,
                size,
                fingerprint,
                any(p == resolved or p.is_relative_to(resolved) for p in used),
            )
        )
    return result


def cleanup_recovery(
    database: Path, assets: Path, selected: list[RecoveryEntry]
) -> Path:
    if not selected:
        raise ValueError("Select recovery files first")
    with operation_lock(database.parent):
        if list(database.parent.glob(".ihda-operation-*.json")):
            raise RuntimeError(
                "Pending operation journals must be recovered before cleanup"
            )
        current = {entry.path: entry for entry in recovery_files(database, assets)}
        for entry in selected:
            actual = current.get(entry.path)
            if (
                actual is None
                or actual.referenced
                or actual.fingerprint != entry.fingerprint
            ):
                raise RuntimeError(
                    f"Recovery file changed or is referenced: {entry.path}"
                )
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = database.parent / "backup" / f"recovery-{stamp}.zip"
        backup.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(backup, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "recovery-manifest.json",
                json.dumps(
                    {str(i): str(entry.path) for i, entry in enumerate(selected)},
                    ensure_ascii=False,
                ),
            )
            for i, entry in enumerate(selected):
                files = entry.path.rglob("*") if entry.path.is_dir() else [entry.path]
                for path in files:
                    if path.is_symlink():
                        raise ValueError("Recovery files changed during backup")
                    if path.is_file():
                        relative = (
                            path.relative_to(entry.path)
                            if entry.path.is_dir()
                            else Path(entry.path.name)
                        )
                        archive.write(path, f"{i}/{relative.as_posix()}")
        with zipfile.ZipFile(backup) as archive:
            if archive.testzip() is not None:
                raise OSError("Recovery backup verification failed")
        # Recheck after compression. No deletion occurs if the preview changed.
        for entry in selected:
            if _inventory(entry.path)[1] != entry.fingerprint:
                raise RuntimeError(
                    f"Recovery files changed; safety copy retained at {backup}"
                )
        for entry in selected:
            try:
                if entry.path.is_dir():
                    shutil.rmtree(entry.path)
                else:
                    entry.path.unlink()
            except OSError as error:
                raise OSError(
                    f"Cleanup stopped; safety copy retained at {backup}: {error}"
                ) from error
        return backup
