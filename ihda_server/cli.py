"""Explicit administrator provisioning; credentials are emitted only on request."""

from __future__ import annotations

import argparse
import json
import os

from ihda_server.auth import TokenIdentity
from ihda_server.catalog import SqlCatalog
from ihda_server.database import initialize, make_engine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")
    commands.add_parser("upgrade-db")
    commands.add_parser("check-files")
    clean = commands.add_parser("cleanup-files")
    clean.add_argument("--apply", action="store_true")
    create = commands.add_parser("create-user")
    create.add_argument("name")
    token = commands.add_parser("issue-token")
    token.add_argument("user_id")
    token.add_argument("--days", type=int, default=30)
    revoke = commands.add_parser("revoke-user")
    revoke.add_argument("user_id")
    project = commands.add_parser("create-project")
    project.add_argument("user_id")
    project.add_argument("name")
    from ihda_server import backup_cli

    backup_cli.add_commands(commands)
    args = parser.parse_args()
    if args.command in {"backup", "verify-backup", "restore-backup"}:
        try:
            backup_cli.run(args)
        except (ValueError, RuntimeError, OSError, KeyError) as error:
            parser.exit(1, f"Backup operation failed: {error}\n")
        except Exception:
            parser.exit(
                1,
                "Backup operation failed; check database access, schema and storage availability.\n",
            )
        return
    engine = make_engine(os.environ["IHDA_DATABASE_URL"])
    identity = TokenIdentity(engine)
    try:
        if args.command == "init-db":
            initialize(engine)
        elif args.command == "upgrade-db":
            from ihda_server.migrations import upgrade

            upgrade(engine)
        elif args.command in {"check-files", "cleanup-files"}:
            from pathlib import Path

            from ihda_server.database import verify_schema
            from ihda_server.file_maintenance import check_files, cleanup
            from ihda_server.storage import FileBlobStore

            verify_schema(engine)
            storage = FileBlobStore(Path(os.environ["IHDA_BLOB_ROOT"]))
            if args.command == "check-files":
                check_files(engine, storage)
            else:
                print(json.dumps(cleanup(engine, storage, apply=args.apply), indent=2))
        elif args.command == "create-user":
            print(identity.create_user(args.name))
        elif args.command == "issue-token":
            print(identity.issue(args.user_id, args.days))
        elif args.command == "revoke-user":
            identity.revoke_user(args.user_id)
        elif args.command == "create-project":
            print(
                json.dumps(SqlCatalog(engine).create_project(args.user_id, args.name))
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
