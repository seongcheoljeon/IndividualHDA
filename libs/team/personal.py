"""The same command contract over the existing personal SQLite library.

Revision triggers observe writes made through the original UI too. A borrowed
repository session lets the request receipt commit with the asset and file journal.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from libs import asset_commands
from libs.asset_contracts import AssetData
from libs.asset_rename import AssetNames, build_rename_plan, rename_asset
from libs.contracts import TransactionalRepository
from libs.database.lifecycle import PersonalLifecycle
from libs.database.rename_repository import SQLiteRenameRepository
from libs.database.rows import named_query
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.database.tracking import local_tracking
from libs.file_integrity import FILE_READ_CHUNK_BYTES
from libs.operation_journal import MoveJournal, durable_operation
from libs.record_codec import decode_record
from libs.repository import LibraryConflict, LibraryError, RegistrationPayload
from libs.search_limits import QUERY_TEXT_MAX, TEAM_PAGE_DEFAULT, TEAM_PAGE_MAX
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.team.contracts import (
    Blob,
    Command,
    Conflict,
    NotFound,
    Page,
    TeamError,
    parse_blob,
)
from libs.team.limits import DEFAULT_AUDIT_EVENT_LIMIT
from libs.team.storage import FileBlobStore


class PersonalCatalog:
    def __init__(
        self, database: Path, asset_root: Path, user: str, names: AssetNames
    ) -> None:
        self.database, self.asset_root, self.user, self._names = (
            database,
            asset_root,
            user,
            names,
        )
        self._files = FileBlobStore(database.parent / ".ihda-blobs")
        with SQLite3DatabaseAPI(database) as db:
            db._connect.executescript("""
                CREATE TABLE IF NOT EXISTS catalog_revisions(asset_id INTEGER PRIMARY KEY, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS catalog_requests(request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL);
                INSERT OR IGNORE INTO catalog_revisions SELECT id, 1 FROM hda_key;
            """)
            for table in (
                "hda_key",
                "hda_info",
                "note_info",
                "tag_info",
                "video_info",
                "thumbnail_info",
                "hda_history",
            ):
                key = "id" if table == "hda_key" else "hda_key_id"
                for event in ("INSERT", "UPDATE", "DELETE"):
                    row = "OLD" if event == "DELETE" else "NEW"
                    db._connect.execute(
                        f"DROP TRIGGER IF EXISTS catalog_revision_{table}_{event}"
                    )
                    condition = ""
                    if table == "hda_info" and event == "UPDATE":
                        condition = "WHEN old.version IS NOT new.version OR old.filename IS NOT new.filename OR old.dirpath IS NOT new.dirpath"
                    db._connect.execute(f"""CREATE TRIGGER catalog_revision_{table}_{event}
                        AFTER {event} ON {table} {condition} BEGIN
                        INSERT INTO catalog_revisions(asset_id, revision) VALUES ({row}.{key}, 1)
                        ON CONFLICT(asset_id) DO UPDATE SET revision=revision+1;
                        END""")
            for table, _key, asset in (
                ("asset_identity", "asset_id", "new.asset_id"),
                (
                    "version_identity",
                    "history_id",
                    "(SELECT hda_key_id FROM hda_history WHERE id=new.history_id)",
                ),
            ):
                db._connect.execute(
                    f"CREATE TRIGGER IF NOT EXISTS catalog_revision_{table} AFTER UPDATE ON {table} BEGIN UPDATE catalog_revisions SET revision=revision+1 WHERE asset_id={asset}; END"
                )
            db._connect.commit()
        SqliteLibraryRepository(database).ensure_user(user)

    @property
    def namespace(self) -> str:
        return "personal:" + str(self.database.resolve())

    @staticmethod
    def _repository(db: SQLite3DatabaseAPI) -> SqliteLibraryRepository:
        return SqliteLibraryRepository(
            db.db_filepath, session_factory=lambda: nullcontext(db)
        )

    def upload(self, path: Path) -> Blob:
        with path.open("rb") as file:
            digest, size = self._files.put(
                iter(lambda: file.read(FILE_READ_CHUNK_BYTES), b"")
            )
        blob = Blob(digest, size, path.name)
        blob.validate()
        return blob

    def download(self, blob: Blob) -> Path:
        from libs.team.client import BlobCache

        return BlobCache(
            self.database.parent / ".ihda-cache", str(self.database.resolve())
        ).fetch(blob, lambda: self._chunks(blob))

    def _chunks(self, blob: Blob) -> Iterator[bytes]:
        with self._files.path(blob.digest).open("rb") as file:
            while chunk := file.read(FILE_READ_CHUNK_BYTES):
                yield chunk

    def _document(self, db: SQLite3DatabaseAPI, data: dict[str, Any]) -> dict[str, Any]:
        files = {}
        for kind, directory, filename in (
            ("asset", "hda_dirpath", "hda_filename"),
            ("thumbnail", "thumbnail_dirpath", "thumbnail_filename"),
            ("video", "video_dirpath", "video_filename"),
        ):
            if data.get(directory) and data.get(filename):
                path = Path(data[directory]) / data[filename]
                if path.is_file():
                    files[kind] = asdict(self.upload(path))
        revision = named_query(
            db._connect,
            "SELECT revision FROM catalog_revisions WHERE asset_id=:hda_id",
            {"hda_id": data["hda_id"]},
        ).fetchone()
        identity = named_query(
            db._connect,
            "SELECT uuid,current_version_uuid,created_at,updated_at FROM asset_identity WHERE asset_id=:hda_id",
            {"hda_id": data["hda_id"]},
        ).fetchone()
        preference = named_query(
            db._connect,
            "SELECT revision,last_used_at,use_count FROM asset_user_preferences WHERE asset_id=:hda_id AND user_id=:user",
            {"hda_id": data["hda_id"], "user": self.user},
        ).fetchone()
        historical = named_query(
            db._connect,
            """SELECT v.uuid,v.details,h.comment FROM version_identity v JOIN hda_history h ON h.id=v.history_id
            WHERE h.hda_key_id=:hda_id AND v.uuid=:current_version_uuid""",
            {
                "hda_id": data["hda_id"],
                "current_version_uuid": identity["current_version_uuid"],
            },
        ).fetchone()
        return {
            **(json.loads(historical["details"]) if historical else {}),
            "dependencies": local_tracking(db._connect).dependencies(historical["uuid"])
            if historical
            else [],
            "description": historical["comment"] if historical else "",
            "asset_uuid": identity["uuid"],
            "version_uuid": historical["uuid"]
            if historical
            else identity["current_version_uuid"],
            "preference_revision": preference["revision"] if preference else 0,
            "last_used_at": preference["last_used_at"] if preference else None,
            "use_count": preference["use_count"] if preference else 0,
            "id": data["hda_id"],
            "name": data["hda_name"],
            "category": data["hda_cate"],
            "version": data["hda_version"],
            "revision": revision["revision"] if revision else 1,
            "note": data.get("hda_note") or "",
            "tags": list(data.get("hda_tags") or ()),
            "favorite": bool(data.get("is_favorite_hda")),
            "files": files,
            "metadata": json.loads(json.dumps(data, default=str)),
            "created_at": identity["created_at"] or data.get("hda_ctime", ""),
            "updated_at": identity["updated_at"] or data.get("hda_mtime", ""),
        }

    def _get(self, db: SQLite3DatabaseAPI, asset_id: int) -> dict[str, Any]:
        data = next(
            (
                row
                for row in self._repository(db).list_assets(self.user)
                if row.hda_id == asset_id
            ),
            None,
        )
        if data is None:
            raise NotFound("Asset does not exist")
        return asdict(data)

    def list_assets(
        self, query: str = "", offset: int = 0, limit: int = TEAM_PAGE_DEFAULT
    ) -> Page:
        if offset < 0 or not 1 <= limit <= TEAM_PAGE_MAX or len(query) > QUERY_TEXT_MAX:
            raise TeamError("Invalid pagination or query")
        query = query.strip()
        with SQLite3DatabaseAPI(self.database) as db, db.transaction():
            rows = [
                row
                for row in self._repository(db).list_assets(self.user)
                if not query
                or query.casefold() in row.hda_name.casefold()
                or query.casefold() in row.hda_cate.casefold()
            ]
            rows.sort(key=lambda row: (row.hda_name.casefold(), row.hda_id))
            revision = named_query(
                db._connect, "SELECT COALESCE(SUM(revision),0) FROM catalog_revisions"
            ).fetchone()[0]
            return Page(
                [
                    self._document(db, asdict(row))
                    for row in rows[offset : offset + limit]
                ],
                len(rows),
                offset,
                limit,
                revision,
            )

    def get_asset(self, asset_id: int) -> dict[str, Any]:
        with SQLite3DatabaseAPI(self.database) as db, db.transaction():
            return self._document(db, self._get(db, asset_id))

    def histories(self, asset_id: int) -> list[dict[str, Any]]:
        with SQLite3DatabaseAPI(self.database) as db, db.transaction():
            current = self._get(db, asset_id)
            rows = self._repository(db).histories(asset_id, self.user)
            result = []
            for row in reversed(rows):
                data = dict(current)
                data.update(
                    hda_version=row.version,
                    hda_dirpath=row.ihda_dirpath,
                    hda_filename=row.ihda_filename,
                    thumbnail_dirpath=row.thumb_dirpath,
                    thumbnail_filename=row.thumb_filename,
                    video_dirpath=row.video_dirpath,
                    video_filename=row.video_filename,
                )
                document = self._document(db, data)
                version_identity = named_query(
                    db._connect,
                    "SELECT uuid,details FROM version_identity WHERE history_id=:hist_id",
                    {"hist_id": row.hist_id},
                ).fetchone()
                document.update(
                    version_uuid=version_identity["uuid"],
                    description=row.comment,
                    **json.loads(version_identity["details"]),
                )
                document["dependencies"] = local_tracking(db._connect).dependencies(
                    version_identity["uuid"]
                )
                document["metadata"] = json.loads(json.dumps(row, default=str))
                result.append(
                    {
                        "id": row.hist_id,
                        "version": row.version,
                        "document": document,
                    }
                )
            return result

    def trash(self) -> list[dict[str, Any]]:
        with SQLite3DatabaseAPI(self.database) as db:
            items = PersonalLifecycle(db._connect).trash()
            for item in items:
                item["revision"] = db._connect.execute(
                    "SELECT revision FROM catalog_revisions WHERE asset_id=:asset_id",
                    {"asset_id": item["asset_id"]},
                ).fetchone()[0]
            return items

    def events(self, asset_uuid: str) -> list[dict[str, Any]]:
        with SQLite3DatabaseAPI(self.database) as db:
            cursor = named_query(
                db._connect,
                "SELECT * FROM audit_events WHERE asset_uuid=:asset_uuid ORDER BY occurred_at DESC LIMIT :DEFAULT_AUDIT_EVENT_LIMIT",
                {
                    "asset_uuid": asset_uuid,
                    "DEFAULT_AUDIT_EVENT_LIMIT": DEFAULT_AUDIT_EVENT_LIMIT,
                },
            )
            return [dict(row) for row in cursor.fetchall()]

    def execute(self, command: Command) -> dict[str, Any]:
        try:
            return self._execute(command)
        except (LibraryConflict, FileExistsError, ValueError) as error:
            raise Conflict(str(error)) from error
        except LibraryError as error:
            raise TeamError(str(error)) from error

    def _execute(self, command: Command) -> dict[str, Any]:
        command.validate()
        with (
            SQLite3DatabaseAPI(self.database) as db,
            durable_operation(self.database.parent, db) as journal,
        ):
            db._connect.execute(
                "UPDATE write_context SET request_id=:request_id",
                {"request_id": command.request_id},
            )
            receipt = named_query(
                db._connect,
                "SELECT fingerprint,result FROM catalog_requests WHERE request_id=:request_id",
                {"request_id": command.request_id},
            ).fetchone()
            if receipt is not None:
                if receipt["fingerprint"] != command.fingerprint():
                    raise Conflict("Request ID was already used with different content")
                return dict(json.loads(receipt["result"]))
            if command.operation in {
                "restore",
                "purge",
                "restore_history",
                "purge_history",
            }:
                assert command.asset_id is not None
                revision = named_query(
                    db._connect,
                    "SELECT revision FROM catalog_revisions WHERE asset_id=:asset_id",
                    {"asset_id": command.asset_id},
                ).fetchone()
                if (
                    revision is None
                    or revision["revision"] != command.expected_revision
                ):
                    raise Conflict("Asset changed; reload")
                action = (
                    "restore" if command.operation.startswith("restore") else "purge"
                )
                PersonalLifecycle(db._connect).change(
                    command.asset_id, action, command.values.get("history_id")
                )
                db._connect.execute(
                    "UPDATE catalog_revisions SET revision=revision+1 WHERE asset_id=:asset_id",
                    {"asset_id": command.asset_id},
                )
                result = (
                    {"id": command.asset_id, "deleted": True, "purged": True}
                    if action == "purge" and "history_id" not in command.values
                    else self._document(db, self._get(db, command.asset_id))
                )
                db._connect.execute(
                    "INSERT INTO catalog_requests (request_id,fingerprint,result) VALUES(:request_id,:value,:result)",
                    {
                        "request_id": command.request_id,
                        "value": command.fingerprint(),
                        "result": json.dumps(result),
                    },
                )
                return result
            if command.operation != "create":
                assert command.asset_id is not None
                self._get(db, command.asset_id)
                revision = named_query(
                    db._connect,
                    "SELECT revision FROM catalog_revisions WHERE asset_id=:asset_id",
                    {"asset_id": command.asset_id},
                ).fetchone()[0]
                if (
                    command.operation not in {"preference", "usage"}
                    and revision != command.expected_revision
                ):
                    raise Conflict(
                        "Asset changed since it was loaded; reload before saving"
                    )
            result = self._apply(db, journal, command)
            db._connect.execute(
                "INSERT INTO catalog_requests (request_id,fingerprint,result) VALUES(:request_id,:value,:result)",
                {
                    "request_id": command.request_id,
                    "value": command.fingerprint(),
                    "result": json.dumps(result),
                },
            )
            return result

    def _apply(
        self, db: SQLite3DatabaseAPI, journal: MoveJournal, command: Command
    ) -> dict[str, Any]:
        repository, values = self._repository(db), command.values
        asset_id = command.asset_id

        @contextmanager
        def shared_operation(
            directory: Path, db: TransactionalRepository | None = None
        ) -> Iterator[MoveJournal]:
            yield journal

        if command.operation in {"create", "version"}:
            current = self._get(db, asset_id) if asset_id is not None else None
            if (
                current is not None
                and db._connect.execute(
                    "SELECT 1 FROM hda_history WHERE hda_key_id=:asset_id AND version=:version",
                    {"asset_id": asset_id, "version": values["version"]},
                ).fetchone()
            ):
                raise Conflict("This version already exists, including Trash")
            name = values["name"] if current is None else current["hda_name"]
            category = values["category"] if current is None else current["hda_cate"]
            directory = (
                self.asset_root
                / category
                / (name if current is None else current["hda_name"])
                / command.request_id
            )
            directory.mkdir(parents=True, exist_ok=True)
            files = {
                key: self.download(parse_blob(value))
                for key, value in values["files"].items()
            }
            asset_path = directory / files["asset"].name
            shutil.copyfile(files["asset"], asset_path)
            thumbnail = (
                directory
                / "thumbnail"
                / (
                    files["thumbnail"].name
                    if "thumbnail" in files
                    else "unavailable.png"
                )
            )
            thumbnail.parent.mkdir(exist_ok=True)
            if "thumbnail" in files:
                shutil.copyfile(files["thumbnail"], thumbnail)
            else:
                thumbnail.touch()
            metadata = values.get("metadata", {})
            payload = RegistrationPayload(
                user=self.user,
                node_name=name,
                node_path=metadata.get("node_old_path", "/obj/" + name),
                version=values["version"],
                hda_dirpath=directory,
                hda_filename=asset_path.name,
                type_name=metadata.get("node_type_name", "unknown"),
                cate_name=category,
                def_desc=metadata.get("node_def_desc", ""),
                is_network=bool(metadata.get("is_network")),
                is_sub_network=bool(metadata.get("is_sub_network")),
                type_path_lst=tuple(
                    metadata.get("node_type_path_list")
                    or [category + "/" + metadata.get("node_type_name", "unknown")]
                ),
                cate_path_lst=tuple(
                    metadata.get("node_cate_path_list") or [category.title()]
                ),
                icon_path_lst=tuple(metadata.get("hda_icon") or ["SOP", "box"]),
                input_conn=(),
                output_conn=(),
                hou_version=metadata.get("hou_version", ""),
                hou_license=metadata.get("hda_license", ""),
                operating_system=metadata.get("operating_system", ""),
                hip_filename=metadata.get("hip_filename") or "unknown.hip",
                hip_dirpath=Path(metadata.get("hip_dirpath") or "."),
                sf=1,
                ef=1,
                fps=24,
                thumb_dirpath=thumbnail.parent,
                thumb_filename=thumbnail.name,
                registered_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            result = (
                repository.register_asset(payload)
                if asset_id is None
                else repository.add_version(asset_id, payload)
            )
            asset_id = result.asset.hda_id
            latest = db._connect.execute(
                "SELECT MAX(id) FROM hda_history WHERE hda_key_id=:asset_id",
                {"asset_id": asset_id},
            ).fetchone()[0]
            if latest is not None:
                PersonalLifecycle(db._connect).details(
                    latest,
                    {
                        key: values[key]
                        for key in ("description", "dependencies", "dependency_status")
                        if key in values
                    },
                )
            if "note" in values:
                repository.set_note(asset_id, values["note"])
            if "tags" in values:
                repository.set_tags(asset_id, values["tags"])
            if "video" in files:
                repository.set_video(
                    asset_id,
                    files["video"].parent,
                    files["video"].name,
                    values["version"],
                )
        else:
            assert asset_id is not None
            current = self._get(db, asset_id)
            if command.operation == "preference":
                PersonalLifecycle(db._connect).favorite(
                    asset_id, values["favorite"], command.expected_revision
                )
            elif command.operation == "usage":
                PersonalLifecycle(db._connect).record_use(asset_id, command.request_id)
            elif command.operation == "version_details":
                PersonalLifecycle(db._connect).details(values["history_id"], values)
            elif command.operation == "metadata":
                if "note" in values:
                    repository.set_note(asset_id, values["note"])
                if "tags" in values:
                    repository.set_tags(asset_id, values["tags"])
                if "favorite" in values and values["favorite"] != bool(
                    current["is_favorite_hda"]
                ):
                    repository.toggle_favorite(asset_id)
            elif command.operation == "rename":
                plan = build_rename_plan(
                    decode_record(AssetData, current),
                    values["name"],
                    self._names,
                    rename_video=repository.video_matches_version(
                        asset_id, current["hda_version"]
                    ),
                )
                rename_asset(
                    SQLiteRenameRepository(db), plan, operations=shared_operation
                )
            elif command.operation == "delete":
                asset_commands.delete_asset(db, asset_id)
                return {"id": asset_id, "deleted": True}
            elif command.operation == "delete_history":
                asset_commands.delete_history(db, asset_id, values["history_id"])
            elif command.operation == "media":
                file = self.download(parse_blob(values["file"]))
                if values["kind"] == "thumbnail":
                    repository.set_thumbnail(
                        asset_id, file.parent, file.name, current["hda_version"]
                    )
                else:
                    repository.set_video(
                        asset_id, file.parent, file.name, current["hda_version"]
                    )
        assert asset_id is not None
        return self._document(db, self._get(db, asset_id))
