"""Explicit personal file checking/cleanup. Preview precedes deletion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from libs.database.lifecycle import inspect_files
from libs.library_maintenance import references
from libs.operation_journal import operation_lock
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def cleanup(
    database: Path, asset_root: Path, *, apply: bool = False
) -> list[dict[str, Any]]:
    results = []
    root = asset_root.resolve()
    with (
        operation_lock(database.parent),
        SQLite3DatabaseAPI(database) as db,
        db.transaction(),
    ):
        referenced = {ref.path.resolve() for ref in references(db._connect)}
        for (stored,) in db._connect.execute(
            "SELECT path FROM file_cleanup"
        ).fetchall():
            path = Path(stored)
            resolved = path.resolve()
            size = path.stat().st_size if path.is_file() else 0
            error = ""
            if resolved in referenced:
                error = "Still referenced"
            elif (
                not resolved.is_relative_to(root)
                or resolved == root
                or path.is_symlink()
            ):
                error = "Outside the managed asset root or symbolic link"
            if apply and not error:
                try:
                    path.unlink(missing_ok=True)
                    db._connect.execute(
                        "DELETE FROM file_cleanup WHERE path=:stored",
                        {"stored": stored},
                    )
                    for directory in _prune_empty_directories(path.parent, root):
                        results.append(
                            {
                                "path": str(directory),
                                "bytes": 0,
                                "status": "removed directory",
                            }
                        )
                except OSError as exception:
                    error = str(exception)
            if apply and error:
                db._connect.execute(
                    "UPDATE file_cleanup SET error=:error WHERE path=:stored",
                    {"error": error, "stored": stored},
                )
            results.append(
                {
                    "path": stored,
                    "bytes": size,
                    "status": error or ("removed" if apply else "candidate"),
                }
            )
    return results


def _prune_empty_directories(start: Path, root: Path) -> list[Path]:
    """Remove ``start`` and its parents while they are empty, stopping at ``root``.

    A purged asset leaves ``<asset>/thumbnail`` and ``<asset>/`` behind once its
    files are gone; every writer recreates directories with parents=True, so an
    empty user or category directory can go too. The root itself always stays.
    """
    removed: list[Path] = []
    directory = start
    while (
        directory.resolve() != root
        and directory.resolve().is_relative_to(root)
        and directory.is_dir()
        and not directory.is_symlink()
        and not any(directory.iterdir())
    ):
        directory.rmdir()
        removed.append(directory)
        directory = directory.parent
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["check", "cleanup"])
    parser.add_argument("database", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.operation == "check":
        with SQLite3DatabaseAPI(args.database) as db:
            inspect_files(db._connect)
    else:
        if args.asset_root is None:
            parser.error("cleanup requires --asset-root")
        print(
            json.dumps(
                cleanup(args.database, args.asset_root, apply=args.apply),
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
