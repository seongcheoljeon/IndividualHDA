"""Read-only personal snapshots. Upload paths stay in the local resume journal."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Event
from typing import Any, Protocol

from libs.file_integrity import measure_file
from libs.library_maintenance import check_cancel, read_database
from libs.team.contracts import Command, TeamError


def file_reference(path: Path, cancel: Event | None = None) -> dict[str, Any]:
    content = measure_file(path, lambda: check_cancel(cancel))
    return {"digest": content.digest, "size": content.size, "filename": path.name}


class CopySource(Protocol):
    def identity(self) -> dict[str, str]: ...
    def preview(
        self,
        *,
        all_versions: bool = True,
        previews: bool = True,
        cancel: Event | None = None,
    ) -> dict[str, Any]: ...


class PersonalCopySource:
    def __init__(self, database: Path, asset_id: int) -> None:
        self.database, self.asset_id = database, asset_id

    def identity(self) -> dict[str, str]:
        with read_database(self.database, None) as connection:
            row = connection.execute(
                "SELECT uuid FROM asset_identity WHERE asset_id=? AND deleted_at IS NULL",
                (self.asset_id,),
            ).fetchone()
            if row is None:
                raise TeamError("The personal asset is no longer available")
            return {
                "library_uuid": connection.execute(
                    "SELECT uuid FROM library_identity"
                ).fetchone()[0],
                "asset_uuid": row[0],
            }

    def preview(
        self,
        *,
        all_versions: bool = True,
        previews: bool = True,
        cancel: Event | None = None,
    ) -> dict[str, Any]:
        with read_database(self.database, cancel) as connection:
            asset = connection.execute(
                """SELECT k.name,k.category,a.uuid,a.current_version_uuid,
                COALESCE(n.note,'') AS note FROM hda_key k JOIN asset_identity a ON a.asset_id=k.id
                LEFT JOIN note_info n ON n.hda_key_id=k.id WHERE k.id=? AND a.deleted_at IS NULL""",
                (self.asset_id,),
            ).fetchone()
            if asset is None:
                raise TeamError("The personal asset is no longer available")
            origin = {
                "library_uuid": connection.execute(
                    "SELECT uuid FROM library_identity"
                ).fetchone()[0],
                "asset_uuid": asset["uuid"],
            }
            tags = [
                row[0]
                for row in connection.execute(
                    "SELECT tag FROM asset_tags WHERE hda_key_id=? ORDER BY tag",
                    (self.asset_id,),
                )
            ]
            histories = [
                dict(row)
                for row in connection.execute(
                    """SELECT h.*,v.uuid,v.details,
                COALESCE((SELECT n.note FROM hda_note_history n WHERE n.hda_key_id=h.hda_key_id
                  AND n.hda_version=h.version AND n.registration_datetime<=h.registration_datetime
                  ORDER BY n.registration_datetime DESC,n.id DESC LIMIT 1),'') AS version_note
                FROM hda_history h JOIN version_identity v ON v.history_id=h.id
                WHERE h.hda_key_id=? AND v.deleted_at IS NULL ORDER BY h.id""",
                    (self.asset_id,),
                )
            ]
            current = next(
                (
                    row
                    for row in histories
                    if row["uuid"] == asset["current_version_uuid"]
                ),
                None,
            )
            if current is None:
                raise TeamError(
                    "Current version has no matching history. Repair the personal library first."
                )
            histories = (
                [row for row in histories if row is not current] + [current]
                if all_versions
                else [current]
            )
            values = {
                "name": asset["name"],
                "category": asset["category"],
                "note": asset["note"],
                "tags": tags,
                "origin": origin,
                "versions": [],
            }
        paths: dict[str, list[str]] = {}
        warnings, labels = [], set()
        versions = []
        for row in histories:
            check_cancel(cancel)
            files = {}
            for kind, directory, filename in (
                ("asset", "hda_dirpath", "hda_filename"),
                ("thumbnail", "thumb_dirpath", "thumb_filename"),
                ("video", "video_dirpath", "video_filename"),
            ):
                if kind != "asset" and (not previews or not row[filename]):
                    continue
                path = Path(row[directory] or "") / (row[filename] or "")
                if not path.is_file():
                    if kind == "asset":
                        raise TeamError(
                            f"Missing HDA for version {row['version']}: {path}"
                        )
                    warnings.append(
                        f"Version {row['version']}: missing {kind}; omitted."
                    )
                    continue
                blob = file_reference(path, cancel)
                files[kind] = blob
                paths.setdefault(blob["digest"], []).append(str(path.resolve()))
            label, suffix = row["version"], 2
            while label in labels:
                label = f"{row['version'][:70]}-{suffix}"
                suffix += 1
            if label != row["version"]:
                warnings.append(
                    f"Repeated version {row['version']} will be copied as {label}."
                )
            labels.add(label)
            details = json.loads(row["details"])
            metadata = {
                key: row[source]
                for key, source in {
                    "hou_version": "houdini_version",
                    "hda_license": "hda_license",
                    "operating_system": "operating_system",
                    "node_old_path": "node_old_path",
                    "node_type_name": "node_type_name",
                    "node_def_desc": "node_def_desc",
                    "hip_filename": "hip_filename",
                    "hip_dirpath": "hip_dirpath",
                }.items()
            }
            metadata["hda_icon"] = (row["icon"] or "").split(",")
            versions.append(
                {
                    "origin": {
                        "version_uuid": row["uuid"],
                        "version": row["version"],
                        "created_at": row["registration_datetime"],
                        "created_by": row["userid"],
                    },
                    "values": {
                        "version": label,
                        "files": files,
                        "metadata": metadata,
                        "note": row["version_note"],
                        **{
                            key: details[key]
                            for key in (
                                "description",
                                "dependencies",
                                "dependency_status",
                            )
                            if key in details
                        },
                    },
                }
            )
        values["versions"] = versions
        Command("copy_asset", values=values).validate()
        return {
            "values": values,
            "paths": paths,
            "warnings": warnings,
            "options": {"all_versions": all_versions, "previews": previews},
        }
