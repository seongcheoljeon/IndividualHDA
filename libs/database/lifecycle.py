"""Personal lifecycle service; files stay in place until explicit, checked purge."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

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
            SELECT ?,a.uuid,?,k.user_id,?,?,?,? FROM asset_identity a JOIN hda_key k ON k.id=a.asset_id WHERE k.id=?""",
            (
                new_identity(),
                version_uuid,
                utc_now(),
                request_id,
                operation,
                json.dumps(changes),
                asset_id,
            ),
        )

    def trash(self) -> list[dict[str, Any]]:
        rows = []
        for (
            asset_id,
            name,
            deleted_at,
        ) in self.connection.execute("""SELECT k.id,k.name,a.deleted_at
            FROM hda_key k JOIN asset_identity a ON a.asset_id=k.id WHERE a.deleted_at IS NOT NULL"""):
            rows.append(
                {
                    "asset_id": asset_id,
                    "name": name,
                    "deleted_at": deleted_at,
                    "history_id": None,
                }
            )
        for (
            asset_id,
            name,
            history_id,
            version,
            deleted_at,
        ) in self.connection.execute("""SELECT k.id,k.name,h.id,h.version,v.deleted_at
            FROM hda_key k JOIN asset_identity a ON a.asset_id=k.id JOIN hda_history h ON h.hda_key_id=k.id
            JOIN version_identity v ON v.history_id=h.id WHERE a.deleted_at IS NULL AND v.deleted_at IS NOT NULL"""):
            rows.append(
                {
                    "asset_id": asset_id,
                    "name": name,
                    "history_id": history_id,
                    "version": version,
                    "deleted_at": deleted_at,
                }
            )
        return rows

    def change(
        self, asset_id: int, operation: str, history_id: int | None = None
    ) -> None:
        info = self.connection.execute(
            "SELECT uuid,current_version_uuid,deleted_at FROM asset_identity WHERE asset_id=?",
            (asset_id,),
        ).fetchone()
        if info is None:
            raise LibraryConflict("Asset no longer exists")
        table, key, identity = "asset_identity", "asset_id", asset_id
        deleted_at = info[2]
        version_uuid = None
        if history_id is not None:
            if deleted_at is not None:
                raise LibraryConflict("Restore the asset first")
            row = self.connection.execute(
                """SELECT v.uuid,v.deleted_at FROM version_identity v JOIN hda_history h ON h.id=v.history_id
                WHERE h.id=? AND h.hda_key_id=?""",
                (history_id, asset_id),
            ).fetchone()
            if row is None:
                raise LibraryConflict("Version no longer exists")
            version_uuid, deleted_at = row
            if version_uuid == info[1]:
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
            criteria = "h.id=?" if history_id is not None else "h.hda_key_id=?"
            files = self.connection.execute(
                f"""SELECT f.directory,f.filename FROM version_files f
                JOIN hda_history h ON h.id=f.history_id WHERE {criteria}""",
                (identity,),
            ).fetchall()
            if history_id is None:
                for source in ("hda_info", "thumbnail_info", "video_info"):
                    files.extend(
                        self.connection.execute(
                            f"SELECT dirpath,filename FROM {source} WHERE hda_key_id=?",
                            (asset_id,),
                        ).fetchall()
                    )
            for directory, filename in files:
                self.connection.execute(
                    "INSERT OR IGNORE INTO file_cleanup(path) VALUES(?)",
                    (str(Path(directory) / filename),),
                )
            self.connection.execute(
                "DELETE FROM hda_history WHERE id=?"
                if history_id is not None
                else "DELETE FROM hda_key WHERE id=?",
                (identity,),
            )
            return
        self.connection.execute(
            f"""UPDATE {table} SET deleted_at=?,deleted_by=(SELECT user_id FROM hda_key WHERE id=?) WHERE {key}=?""",
            (utc_now() if operation == "delete" else None, asset_id, identity),
        )
        if operation == "restore":
            self.connection.execute(
                f"UPDATE {table} SET deleted_by=NULL WHERE {key}=?", (identity,)
            )

    def favorite(
        self, asset_id: int, value: bool, expected_revision: int | None = None
    ) -> bool:
        row = self.connection.execute(
            """SELECT p.user_id,p.revision FROM asset_user_preferences p
            JOIN asset_identity a ON a.asset_id=p.asset_id WHERE p.asset_id=? AND a.deleted_at IS NULL""",
            (asset_id,),
        ).fetchone()
        if row is None:
            raise LibraryConflict("Asset does not exist")
        if expected_revision is not None and row[1] != expected_revision:
            raise LibraryConflict("Personal settings changed; reload")
        self.connection.execute(
            "UPDATE asset_user_preferences SET favorite=?,revision=revision+1 WHERE asset_id=? AND user_id=?",
            (int(value), asset_id, row[0]),
        )
        self.connection.execute(
            "UPDATE hda_info SET is_favorite=? WHERE hda_key_id=?",
            (int(value), asset_id),
        )
        return value

    def record_use(self, asset_id: int, request_id: str) -> None:
        row = self.connection.execute(
            """SELECT a.uuid,k.user_id FROM asset_identity a JOIN hda_key k ON k.id=a.asset_id
            WHERE a.asset_id=? AND a.deleted_at IS NULL""",
            (asset_id,),
        ).fetchone()
        if row is None:
            raise LibraryConflict("Asset does not exist")
        existing = self.connection.execute(
            "SELECT asset_uuid,user_id FROM usage_requests WHERE request_id=?",
            (request_id,),
        ).fetchone()
        if existing is not None:
            if tuple(existing) != tuple(row):
                raise LibraryConflict("Usage request already belongs to another asset")
            return
        self.connection.execute(
            "INSERT INTO usage_requests VALUES(?,?,?)", (request_id, *row)
        )
        self.connection.execute(
            "UPDATE asset_user_preferences SET use_count=use_count+1,last_used_at=?,revision=revision+1 WHERE asset_id=? AND user_id=?",
            (utc_now(), asset_id, row[1]),
        )
        self.connection.execute(
            "UPDATE hda_info SET load_count=(SELECT use_count FROM asset_user_preferences WHERE asset_id=? AND user_id=?) WHERE hda_key_id=?",
            (asset_id, row[1], asset_id),
        )

    def details(self, history_id: int, values: dict[str, Any]) -> None:
        validate_version_details(values)
        row = self.connection.execute(
            """SELECT h.hda_key_id,v.uuid,v.details FROM hda_history h
            JOIN version_identity v ON v.history_id=h.id JOIN asset_identity a ON a.asset_id=h.hda_key_id
            WHERE h.id=? AND v.deleted_at IS NULL AND a.deleted_at IS NULL""",
            (history_id,),
        ).fetchone()
        if row is None:
            raise LibraryConflict("Version no longer exists")
        details = {
            **json.loads(row[2]),
            **{k: v for k, v in values.items() if k != "description"},
        }
        self.connection.execute(
            "UPDATE version_identity SET details=? WHERE history_id=?",
            (json.dumps(details), history_id),
        )
        if "description" in values:
            self.connection.execute(
                "UPDATE hda_history SET comment=? WHERE id=?",
                (values["description"], history_id),
            )
        self.event(
            row[0],
            "version_details",
            {"before": json.loads(row[2]), "after": details},
            version_uuid=row[1],
        )


def inspect_files(connection: sqlite3.Connection) -> None:
    """Worker-only check; commits each result so interruption retains progress."""
    for history_id, kind, directory, filename, expected in connection.execute(
        "SELECT history_id,kind,directory,filename,digest FROM version_files"
    ).fetchall():
        path = Path(directory) / filename
        digest, size = None, None
        try:
            hasher = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
                    size += len(chunk)
            digest = hasher.hexdigest()
            status = "ok" if expected in {None, digest} else "mismatch"
        except OSError:
            status = "missing"
        connection.execute(
            """UPDATE version_files SET digest=COALESCE(digest,?),size=COALESCE(size,?),checked_at=?,status=?
            WHERE history_id=? AND kind=? AND directory=? AND filename=?""",
            (digest, size, utc_now(), status, history_id, kind, directory, filename),
        )
        connection.commit()
