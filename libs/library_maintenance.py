"""Read-only library diagnostics and previewed, backed-up path repairs."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from libs.database_migrations import backup_database
from libs.operation_journal import operation_lock

# table, directory, filename; HIP files are source references, not library assets.
FILE_COLUMNS = (
    ("hda_info", "dirpath", "filename"),
    ("thumbnail_info", "dirpath", "filename"),
    ("video_info", "dirpath", "filename"),
    ("hda_history", "hda_dirpath", "hda_filename"),
    ("hda_history", "thumb_dirpath", "thumb_filename"),
    ("hda_history", "video_dirpath", "video_filename"),
    ("hda_node_location_record", "hda_dirpath", "hda_filename"),
    ("hipfile_info", "dirpath", "filename"),
    ("hda_history", "hip_dirpath", "hip_filename"),
    ("hda_node_location_record", "hip_dirpath", "hip_filename"),
)


class Cancelled(Exception):
    pass


def check_cancel(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise Cancelled("Cancelled")


@contextmanager
def read_database(
    path: Path, cancel: threading.Event | None = None
) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.set_progress_handler(
        lambda: int(cancel is not None and cancel.is_set()), 1000
    )
    try:
        connection.execute("BEGIN")
        yield connection
    except sqlite3.OperationalError:
        check_cancel(cancel)
        raise
    finally:
        connection.close()


@dataclass(frozen=True)
class FileReference:
    table: str
    row_id: int
    column: str
    directory: str
    filename: str

    @property
    def path(self) -> Path:
        return Path(self.directory) / self.filename


@dataclass(frozen=True)
class Issue:
    severity: str
    location: str
    message: str


def references(connection: sqlite3.Connection) -> Iterator[FileReference]:
    for table, directory, filename in FILE_COLUMNS:
        for row in connection.execute(
            f"SELECT id, {directory}, {filename} FROM {table}"
        ):
            if row[1] is not None and row[2] is not None:
                yield FileReference(table, row[0], directory, row[1], row[2])


def inspect_library(
    database: Path, cancel: threading.Event | None = None
) -> list[Issue]:
    issues: list[Issue] = []
    with read_database(database, cancel) as connection:
        for row in connection.execute("PRAGMA integrity_check"):
            if row[0] != "ok":
                issues.append(Issue("error", "SQLite", row[0]))
        for row in connection.execute("PRAGMA foreign_key_check"):
            issues.append(Issue("error", str(row[0]), f"Orphaned row {row[1]}"))
        for row in connection.execute("""SELECT k.id FROM hda_key k LEFT JOIN hda_info i ON i.hda_key_id=k.id
            LEFT JOIN hipfile_info h ON h.hda_key_id=k.id LEFT JOIN houdini_node_info n ON n.hda_key_id=k.id
            WHERE i.id IS NULL OR h.id IS NULL OR n.id IS NULL"""):
            issues.append(
                Issue("error", f"asset {row[0]}", "Incomplete asset metadata")
            )
        for ref in references(connection):
            check_cancel(cancel)
            if not ref.path.is_file():
                source = ref.column == "hip_dirpath" or ref.table == "hipfile_info"
                issues.append(
                    Issue(
                        "source" if source else "missing",
                        f"{ref.table}:{ref.row_id}",
                        str(ref.path),
                    )
                )
    return issues


@dataclass(frozen=True)
class PathChange:
    table: str
    row_id: int
    column: str
    before: str
    after: str
    target_file: Path
    exists: bool


def plan_paths(
    database: Path, old_root: str, new_root: Path, cancel: threading.Event | None = None
) -> list[PathChange]:
    old = (
        PureWindowsPath(old_root)
        if PureWindowsPath(old_root).drive
        else PurePosixPath(old_root)
    )
    if not old.is_absolute() or not new_root.is_absolute() or not new_root.is_dir():
        raise ValueError(
            "Use an absolute old root and an existing absolute destination directory"
        )
    changes: list[PathChange] = []
    with read_database(database, cancel) as connection:
        for ref in references(connection):
            check_cancel(cancel)
            path = type(old)(ref.directory)
            try:
                relative = path.relative_to(old)
            except ValueError:
                continue
            if ".." in relative.parts:
                raise ValueError("Parent traversal in stored path")
            destination = new_root.joinpath(*relative.parts)
            if str(destination) != ref.directory:
                target = destination / ref.filename
                changes.append(
                    PathChange(
                        ref.table,
                        ref.row_id,
                        ref.column,
                        ref.directory,
                        str(destination),
                        target,
                        target.is_file(),
                    )
                )
    return changes


def apply_paths(database: Path, changes: list[PathChange]) -> Path:
    if not changes or any(not item.target_file.is_file() for item in changes):
        raise ValueError("Every selected destination file must exist")
    allowed = {
        (table, directory): filename for table, directory, filename in FILE_COLUMNS
    }
    if any((item.table, item.column) not in allowed for item in changes):
        raise ValueError("Unknown path field")
    with operation_lock(database.parent):
        connection = sqlite3.connect(database)
        try:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup = database.with_name(f"{database.name}.paths-{stamp}.bak")
            backup_database(connection, backup)
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            # Check all preconditions before triggers can change other referenced rows.
            for item in changes:
                row = connection.execute(
                    f"SELECT {item.column}, {allowed[(item.table, item.column)]} FROM {item.table} WHERE id=?",
                    (item.row_id,),
                ).fetchone()
                if (
                    row is None
                    or row[0] != item.before
                    or row[1] != item.target_file.name
                ):
                    raise RuntimeError(
                        "Library changed since preview; generate a new preview"
                    )
            # hda_info triggers also update record paths. Preserve unaffected records.
            records = connection.execute(
                "SELECT id, hda_dirpath, hda_filename, node_name FROM hda_node_location_record"
            ).fetchall()
            for item in changes:
                if item.table != "hda_node_location_record":
                    connection.execute(
                        f"UPDATE {item.table} SET {item.column}=? WHERE id=?",
                        (item.after, item.row_id),
                    )
            connection.executemany(
                "UPDATE hda_node_location_record SET hda_dirpath=?,hda_filename=?,node_name=? WHERE id=?",
                [(r[1], r[2], r[3], r[0]) for r in records],
            )
            for item in changes:
                if item.table == "hda_node_location_record":
                    connection.execute(
                        f"UPDATE {item.table} SET {item.column}=? WHERE id=?",
                        (item.after, item.row_id),
                    )
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise sqlite3.IntegrityError("Path repair failed foreign-key check")
            connection.commit()
            return backup
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
