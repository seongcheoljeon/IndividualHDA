"""Explicit, restartable file checks and global reference-safe cleanup."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import Engine, delete, select, update

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from ihda_server.storage import FileBlobStore
from ihda_server.storage_lock import storage_lock
from libs.library_metadata import utc_now


def check_files(engine: Engine, storage: FileBlobStore) -> None:
    with engine.connect() as connection:
        files = connection.execute(select(state.file_refs)).mappings().all()
    for file in files:
        path = storage.path(file["digest"])
        try:
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            status = (
                "ok"
                if digest == file["digest"] and path.stat().st_size == file["size"]
                else "mismatch"
            )
        except OSError:
            status = "missing"
        with engine.begin() as connection:
            connection.execute(
                update(state.file_refs)
                .where(
                    state.file_refs.c.history_id == file["history_id"],
                    state.file_refs.c.kind == file["kind"],
                    state.file_refs.c.digest == file["digest"],
                )
                .values(checked_at=utc_now(), status=status)
            )


def cleanup(
    engine: Engine, storage: FileBlobStore, *, apply: bool = False
) -> list[dict[str, Any]]:
    results = []
    # Upload holds this same lock until ownership is registered. Lock all projects
    # before reading refs, so catalog commits cannot acquire references during cleanup.
    with storage_lock(storage.root), engine.begin() as connection:
        connection.execute(
            update(tables.projects).values(revision=tables.projects.c.revision)
        )
        referenced = set(connection.execute(select(state.file_refs.c.digest)).scalars())
        digests = set(connection.execute(select(tables.blobs.c.digest)).scalars())
        for digest in sorted(digests - referenced):
            error = ""
            if apply:
                try:
                    storage.path(digest).unlink(missing_ok=True)
                    connection.execute(
                        delete(tables.blobs).where(tables.blobs.c.digest == digest)
                    )
                except OSError as exception:
                    error = str(exception)
            results.append(
                {
                    "digest": digest,
                    "status": error or ("removed" if apply else "candidate"),
                }
            )
    return results
