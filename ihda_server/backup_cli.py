"""Administrator backup commands, separate from identity provisioning."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def add_commands(commands: Any) -> None:
    backup = commands.add_parser(
        "backup", help="Create a consistent PostgreSQL/blob bundle"
    )
    backup.add_argument("destination", type=Path)
    verify = commands.add_parser(
        "verify-backup", help="Verify every backup file without a database connection"
    )
    verify.add_argument("bundle", type=Path)
    restore = commands.add_parser(
        "restore-backup", help="Restore and verify in an empty isolated database"
    )
    restore.add_argument("bundle", type=Path)
    restore.add_argument("--blob-destination", type=Path, required=True)
    restore.add_argument(
        "--target-url-env",
        default="IHDA_RESTORE_DATABASE_URL",
        help="Environment variable containing the separate target URL",
    )


def run(args: argparse.Namespace) -> None:
    from ihda_server.backup_files import verify_bundle
    from ihda_server.backup_postgres import PostgresBackup
    from ihda_server.backup_service import BackupService
    from ihda_server.database import make_engine

    if args.command == "verify-backup":
        manifest = verify_bundle(args.bundle)
        print(
            json.dumps(
                {
                    "status": "backup_verified",
                    "files": len(manifest["files"]) - 1,
                    "created_at": manifest["created_at"],
                }
            )
        )
        return
    url_key = (
        args.target_url_env if args.command == "restore-backup" else "IHDA_DATABASE_URL"
    )
    url = os.environ.get(url_key, "")
    if not url:
        raise ValueError(f"Set {url_key} to the PostgreSQL database URL")
    engine = make_engine(url)
    try:
        tools = (
            Path(os.environ["IHDA_PG_BIN"]) if os.environ.get("IHDA_PG_BIN") else None
        )
        service = BackupService(
            PostgresBackup(engine, url, tools),
            lambda message: print(message, file=sys.stderr, flush=True),
        )
        result = (
            service.create(Path(os.environ["IHDA_BLOB_ROOT"]), args.destination)
            if args.command == "backup"
            else service.restore(args.bundle, args.blob_destination)
        )
        print(json.dumps(result, ensure_ascii=False))
    finally:
        engine.dispose()
