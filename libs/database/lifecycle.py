"""Personal lifecycle service; files stay in place until explicit, checked purge."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from libs.database.rows import named_query
from libs.file_integrity import FILE_READ_CHUNK_BYTES
from libs.library_metadata import new_identity, utc_now, validate_version_details
from libs.repository import LibraryConflict


class PersonalLifecycle:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def event(
        self,
        asset_id: int,
        operation: str,
        changes: dict[str, Any],
        request_id: str | None = None,
        version_uuid: str | None = None,
    ) -> None:
        request_id = (
            request_id
            or self.connection.execute(
                "SELECT request_id FROM write_context"
            ).fetchone()[0]
            or new_identity()
        )
        self.connection.execute(
            """INSERT INTO audit_events
            (id,asset_uuid,version_uuid,actor,occurred_at,request_id,operation,changes)
            SELECT :new_identity,a.uuid,:version_uuid,k.user_id,:utc_now,:request_id,:operation,:changes FROM asset_identity a JOIN hda_key k ON k.id=a.asset_id WHERE k.id=:asset_id""",
            {
                "new_identity": new_identity(),
                "version_uuid": version_uuid,
                "utc_now": utc_now(),
                "request_id": request_id,
                "operation": operation,
                "changes": json.dumps(changes),
                "asset_id": asset_id,
            },
        )

    def trash(self) -> list[dict[str, Any]]:
        rows = [
            dict(row)
            for row in named_query(
                self.connection,
                """SELECT k.id AS asset_id,k.name,a.deleted_at,NULL AS history_id
            FROM hda_key k JOIN asset_identity a ON a.asset_id=k.id WHERE a.deleted_at IS NOT NULL""",
            )
        ]
        rows.extend(
            dict(row)
            for row in named_query(
                self.connection,
                """SELECT k.id AS asset_id,k.name,h.id AS history_id,h.version,v.deleted_at
            FROM hda_key k JOIN asset_identity a ON a.asset_id=k.id JOIN hda_history h ON h.hda_key_id=k.id
            JOIN version_identity v ON v.history_id=h.id WHERE a.deleted_at IS NULL AND v.deleted_at IS NOT NULL""",
            )
        )
        return rows

    def change(
        self, asset_id: int, operation: str, history_id: int | None = None
    ) -> None:
        info = named_query(
            self.connection,
            "SELECT uuid,current_version_uuid,deleted_at FROM asset_identity WHERE asset_id=:asset_id",
            {"asset_id": asset_id},
        ).fetchone()
        if info is None:
            raise LibraryConflict("Asset no longer exists")
        table, key, identity = "asset_identity", "asset_id", asset_id
        deleted_at = info["deleted_at"]
        version_uuid = None
        if history_id is not None:
            if deleted_at is not None:
                raise LibraryConflict("Restore the asset first")
            row = named_query(
                self.connection,
                """SELECT v.uuid,v.deleted_at FROM version_identity v JOIN hda_history h ON h.id=v.history_id
                WHERE h.id=:history_id AND h.hda_key_id=:asset_id""",
                {"history_id": history_id, "asset_id": asset_id},
            ).fetchone()
            if row is None:
                raise LibraryConflict("Version no longer exists")
            version_uuid, deleted_at = row["uuid"], row["deleted_at"]
            if version_uuid == info["current_version_uuid"]:
                raise LibraryConflict(
                    "The current (most recent) version cannot be deleted"
                )
            table, key, identity = "version_identity", "history_id", history_id
        if (deleted_at is not None) != (operation != "delete"):
            raise LibraryConflict("Trash state changed; reload")
        if operation not in {"delete", "restore", "purge"}:
            raise ValueError("Invalid lifecycle operation")
        self.event(
            asset_id,
            operation,
            {
                "history_id": history_id,
                "before": deleted_at,
                "after": utc_now() if operation == "delete" else None,
            },
            version_uuid=version_uuid,
        )
        if operation == "purge":
            # Queue only registered library files. Shared/source files are checked again by cleanup.
            criteria = (
                "h.id=:identity" if history_id is not None else "h.hda_key_id=:identity"
            )
            files = named_query(
                self.connection,
                f"""SELECT f.directory,f.filename FROM version_files f
                JOIN hda_history h ON h.id=f.history_id WHERE {criteria}""",
                {"identity": identity},
            ).fetchall()
            if history_id is None:
                for source in ("hda_info", "thumbnail_info", "video_info"):
                    files.extend(
                        named_query(
                            self.connection,
                            f"SELECT dirpath AS directory,filename FROM {source} WHERE hda_key_id=:asset_id",
                            {"asset_id": asset_id},
                        ).fetchall()
                    )
            for file_row in files:
                directory, filename = file_row["directory"], file_row["filename"]
                self.connection.execute(
                    "INSERT OR IGNORE INTO file_cleanup(path) VALUES(:value)",
                    {"value": str(Path(directory) / filename)},
                )
            self.connection.execute(
                "DELETE FROM hda_history WHERE id=:identity"
                if history_id is not None
                else "DELETE FROM hda_key WHERE id=:identity",
                {"identity": identity},
            )
            return
        self.connection.execute(
            f"""UPDATE {table} SET deleted_at=:deleted_at,deleted_by=(SELECT user_id FROM hda_key WHERE id=:asset_id) WHERE {key}=:identity""",
            {
                "deleted_at": utc_now() if operation == "delete" else None,
                "asset_id": asset_id,
                "identity": identity,
            },
        )
        if operation == "restore":
            self.connection.execute(
                f"UPDATE {table} SET deleted_by=NULL WHERE {key}=:identity",
                {"identity": identity},
            )

    def favorite(
        self, asset_id: int, value: bool, expected_revision: int | None = None
    ) -> bool:
        row = named_query(
            self.connection,
            """SELECT p.user_id,p.revision FROM asset_user_preferences p
            JOIN asset_identity a ON a.asset_id=p.asset_id WHERE p.asset_id=:asset_id AND a.deleted_at IS NULL""",
            {"asset_id": asset_id},
        ).fetchone()
        if row is None:
            raise LibraryConflict("Asset does not exist")
        if expected_revision is not None and row["revision"] != expected_revision:
            raise LibraryConflict("Personal settings changed; reload")
        self.connection.execute(
            "UPDATE asset_user_preferences SET favorite=:value,revision=revision+1 WHERE asset_id=:asset_id AND user_id=:user_id",
            {"value": int(value), "asset_id": asset_id, "user_id": row["user_id"]},
        )
        self.connection.execute(
            "UPDATE hda_info SET is_favorite=:value WHERE hda_key_id=:asset_id",
            {"value": int(value), "asset_id": asset_id},
        )
        return value

    def record_use(self, asset_id: int, request_id: str) -> None:
        row = named_query(
            self.connection,
            """SELECT a.uuid AS asset_uuid,k.user_id FROM asset_identity a JOIN hda_key k ON k.id=a.asset_id
            WHERE a.asset_id=:asset_id AND a.deleted_at IS NULL""",
            {"asset_id": asset_id},
        ).fetchone()
        if row is None:
            raise LibraryConflict("Asset does not exist")
        existing = named_query(
            self.connection,
            "SELECT asset_uuid,user_id FROM usage_requests WHERE request_id=:request_id",
            {"request_id": request_id},
        ).fetchone()
        if existing is not None:
            if (existing["asset_uuid"], existing["user_id"]) != (
                row["asset_uuid"],
                row["user_id"],
            ):
                raise LibraryConflict("Usage request already belongs to another asset")
            return
        self.connection.execute(
            "INSERT INTO usage_requests (request_id,asset_uuid,user_id) VALUES(:request_id,:asset_uuid,:user_id)",
            {
                "request_id": request_id,
                "asset_uuid": row["asset_uuid"],
                "user_id": row["user_id"],
            },
        )
        self.connection.execute(
            "UPDATE asset_user_preferences SET use_count=use_count+1,last_used_at=:utc_now,revision=revision+1 WHERE asset_id=:asset_id AND user_id=:user_id",
            {"utc_now": utc_now(), "asset_id": asset_id, "user_id": row["user_id"]},
        )
        self.connection.execute(
            "UPDATE hda_info SET load_count=(SELECT use_count FROM asset_user_preferences WHERE asset_id=:asset_id AND user_id=:user_id) WHERE hda_key_id=:asset_id",
            {"asset_id": asset_id, "user_id": row["user_id"]},
        )

    def details(self, history_id: int, values: dict[str, Any]) -> None:
        validate_version_details(values)
        row = named_query(
            self.connection,
            """SELECT h.hda_key_id,v.uuid,v.details FROM hda_history h
            JOIN version_identity v ON v.history_id=h.id JOIN asset_identity a ON a.asset_id=h.hda_key_id
            WHERE h.id=:history_id AND v.deleted_at IS NULL AND a.deleted_at IS NULL""",
            {"history_id": history_id},
        ).fetchone()
        if row is None:
            raise LibraryConflict("Version no longer exists")
        details = {
            **json.loads(row["details"]),
            **{k: v for k, v in values.items() if k != "description"},
        }
        from libs.database.tracking import local_tracking

        tracking = local_tracking(self.connection)
        tracking.replace_dependencies(row["uuid"], details.get("dependencies", []))
        details["dependencies"] = tracking.dependencies(row["uuid"])
        self.connection.execute(
            "UPDATE version_identity SET details=:details WHERE history_id=:history_id",
            {"details": json.dumps(details), "history_id": history_id},
        )
        if "description" in values:
            self.connection.execute(
                "UPDATE hda_history SET comment=:description WHERE id=:history_id",
                {"description": values["description"], "history_id": history_id},
            )
        self.event(
            row["hda_key_id"],
            "version_details",
            {"before": json.loads(row["details"]), "after": details},
            version_uuid=row["uuid"],
        )


def inspect_files(connection: sqlite3.Connection) -> None:
    """Worker-only check; commits each result so interruption retains progress."""
    for row in named_query(
        connection,
        "SELECT history_id,kind,directory,filename,digest FROM version_files",
    ).fetchall():
        history_id, kind = row["history_id"], row["kind"]
        directory, filename, expected = row["directory"], row["filename"], row["digest"]
        path = Path(directory) / filename
        digest, size = None, None
        try:
            hasher = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(FILE_READ_CHUNK_BYTES), b""):
                    hasher.update(chunk)
                    size += len(chunk)
            digest = hasher.hexdigest()
            status = "ok" if expected in {None, digest} else "mismatch"
        except OSError:
            status = "missing"
        connection.execute(
            """UPDATE version_files SET digest=COALESCE(digest,:digest),size=COALESCE(size,:size),checked_at=:utc_now,status=:status
            WHERE history_id=:history_id AND kind=:kind AND directory=:directory AND filename=:filename""",
            {
                "digest": digest,
                "size": size,
                "utc_now": utc_now(),
                "status": status,
                "history_id": history_id,
                "kind": kind,
                "directory": directory,
                "filename": filename,
            },
        )
        connection.commit()
