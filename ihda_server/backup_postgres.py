"""PostgreSQL snapshot/dump adapter. Credentials never enter command arguments."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, inspect, select, text
from sqlalchemy.engine import make_url

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from ihda_server.database import SCHEMA_VERSION

# Stable across processes and releases: changing this permits concurrent restores.
RESTORE_ADVISORY_LOCK_KEY = 7248335901
INVENTORY_BATCH_ROWS = 1000


def inventory(connection: Connection) -> dict[str, Any]:
    from ihda_server.backup_schema import backup_tables

    version = connection.execute(select(tables.versions.c.version)).scalar_one()
    inventory_tables = backup_tables(version)
    summaries = {}
    for table in inventory_tables:
        digest, count = hashlib.sha256(), 0
        rows = (
            connection.execution_options(yield_per=INVENTORY_BATCH_ROWS)
            .execute(select(table).order_by(*table.primary_key.columns))
            .mappings()
        )
        for row in rows:
            encoded = json.dumps(
                dict(row),
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode()
            digest.update(encoded + b"\n")
            count += 1
        summaries[table.name] = {"rows": count, "sha256": digest.hexdigest()}
    blobs: dict[str, int] = {}
    for digest, size in connection.execute(
        select(tables.blobs.c.digest, tables.blobs.c.size)
    ):
        if not re.fullmatch(r"[a-f0-9]{64}", digest) or size < 0:
            raise ValueError("Invalid stored blob identity or size")
        if digest in blobs and blobs[digest] != size:
            raise ValueError("Conflicting sizes for a shared blob")
        blobs[digest] = size
    missing = connection.execute(
        select(state.file_refs.c.digest)
        .select_from(
            state.file_refs.join(tables.history).outerjoin(
                tables.blobs,
                (tables.blobs.c.project_id == tables.history.c.project_id)
                & (tables.blobs.c.digest == state.file_refs.c.digest)
                & (tables.blobs.c.size == state.file_refs.c.size),
            )
        )
        .where(tables.blobs.c.digest.is_(None))
        .limit(1)
    ).first()
    if missing:
        raise ValueError(
            "A version references a file absent from project blob ownership"
        )
    return {"schema_version": version, "tables": summaries, "blobs": blobs}


class PostgresBackup:
    def __init__(
        self, engine: Engine, url: str, bin_directory: Path | None = None
    ) -> None:
        if engine.dialect.name != "postgresql" or engine.get_execution_options().get(
            "schema_translate_map"
        ):
            raise ValueError(
                "Backup requires a dedicated PostgreSQL database using public schema"
            )
        self.engine, self.url, self.bin_directory = engine, make_url(url), bin_directory

    @contextmanager
    def snapshot(self) -> Iterator[tuple[str, dict[str, Any]]]:
        with (
            self.engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection,
            connection.begin(),
        ):
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout=0"))
            if set(inspect(connection).get_table_names(schema="public")) != set(
                tables.metadata.tables
            ):
                raise ValueError(
                    "Backup requires the dedicated team database with its complete schema"
                )
            if (
                inspect(connection).get_view_names(schema="public")
                or connection.execute(
                    text(
                        "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' LIMIT 1"
                    )
                ).first()
            ):
                raise ValueError(
                    "Custom views or routines are not supported in the team backup schema"
                )
            if set(inspect(connection).get_schema_names()) - {
                "public",
                "information_schema",
            }:
                raise ValueError(
                    "Additional database schemas are not supported by this backup format"
                )
            if (
                connection.execute(select(tables.versions.c.version)).scalar_one()
                != SCHEMA_VERSION
            ):
                raise ValueError("Migrate the server before creating a new backup")
            snapshot = connection.execute(
                text("SELECT pg_export_snapshot()")
            ).scalar_one()
            yield snapshot, inventory(connection)

    def run(self, program: str, arguments: list[str]) -> None:
        from psycopg.conninfo import make_conninfo

        executable = (
            str(self.bin_directory / program) if self.bin_directory else program
        )
        values = {
            "host": self.url.host or "",
            "port": str(self.url.port or 5432),
            "user": self.url.username or "",
            "dbname": self.url.database or "",
            **dict(self.url.query),
        }
        if any("password" in key.casefold() for key in values) or any(
            not isinstance(value, str) for value in values.values()
        ):
            raise ValueError("Unsupported PostgreSQL connection parameters")
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith("PG")
        }
        with tempfile.TemporaryDirectory(prefix="ihda-pg-") as temporary:
            password_file = Path(temporary) / "pgpass"
            password = self.url.password or ""
            if "\n" in password or "\r" in password:
                raise ValueError("PostgreSQL password must not contain newlines")
            password_file.write_text(
                "*:*:*:*:" + password.replace("\\", "\\\\").replace(":", "\\:") + "\n",
                encoding="utf-8",
            )
            password_file.chmod(0o600)
            environment["PGPASSFILE"] = str(password_file)
            environment["PGCONNECT_TIMEOUT"] = "10"
            try:
                subprocess.run(
                    [
                        executable,
                        "--no-password",
                        "--dbname",
                        make_conninfo(
                            **{key: str(value) for key, value in values.items()}
                        ),
                        *arguments,
                    ],
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=True,
                )
            except FileNotFoundError as error:
                raise RuntimeError(
                    f"Install PostgreSQL client tools or set IHDA_PG_BIN ({program} missing)"
                ) from error
            except subprocess.CalledProcessError as error:
                # PostgreSQL can echo stored values in diagnostics. Keep credentials
                # and library contents out of CLI output and CI logs.
                raise RuntimeError(
                    f"{program} failed (exit {error.returncode}); check connectivity, privileges and matching client/server versions"
                ) from None

    def dump(self, snapshot: str, output: Path) -> None:
        self.run(
            "pg_dump",
            [
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                *["--table=public." + name for name in sorted(tables.metadata.tables)],
                "--snapshot=" + snapshot,
                "--file=" + str(output),
            ],
        )
        with output.open("rb") as stream:
            os.fsync(stream.fileno())

    @contextmanager
    def restore_target(self) -> Iterator[None]:
        with self.engine.connect() as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": RESTORE_ADVISORY_LOCK_KEY},
            ).scalar_one()
            if not acquired:
                raise ValueError("Another restore is active in the target database")
            try:
                schemas = set(inspect(connection).get_schema_names()) - {
                    "public",
                    "information_schema",
                }
                objects = connection.execute(
                    text(
                        "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' "
                        "UNION ALL SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' "
                        "UNION ALL SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public' LIMIT 1"
                    )
                ).first()
                if schemas or objects:
                    raise ValueError(
                        "Restore target must be an empty dedicated database; existing databases are never overwritten"
                    )
                yield
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": RESTORE_ADVISORY_LOCK_KEY},
                )

    def restore(self, dump: Path) -> None:
        self.run(
            "pg_restore",
            [
                "--single-transaction",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                str(dump),
            ],
        )

    def inspect_restored(self) -> dict[str, Any]:
        with (
            self.engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection,
            connection.begin(),
        ):
            return inventory(connection)
