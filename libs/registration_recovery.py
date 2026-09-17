"""Durable local capture/publication with transaction-coupled registration receipts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from libs.asset_contracts import AssetData, HistoryData
from libs.file_integrity import measure_file
from libs.legacy_documents import (
    fingerprint_connections,
    receipt_connections_v1,
    receipt_history_v1,
    receipt_owner_v1,
)
from libs.library_metadata import new_identity, utc_now
from libs.record_codec import decode_record, record_document
from libs.repository import LibraryConflict, RegistrationPayload, RegistrationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class CaptureFile:
    source: Path
    destination: Path
    capture: Callable[[Path], None]
    required: bool = False


def payload_document(
    payload: RegistrationPayload, asset_id: int | None
) -> dict[str, Any]:
    return {
        "format_version": 2,
        "payload": record_document(payload),
        "asset_id": asset_id,
    }


def fingerprint(payload: RegistrationPayload, asset_id: int | None) -> str:
    document = payload_document(payload, asset_id)
    document.pop("format_version")
    document["payload"].pop("operation_id", None)
    for field in ("input_conn", "output_conn"):
        document["payload"][field] = fingerprint_connections(document["payload"][field])
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()


def decode_payload(document: dict[str, Any]) -> RegistrationPayload:
    version = document.get("format_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported registration job version")
    values = dict(document["payload"])
    if version == 1:
        for field in ("input_conn", "output_conn"):
            values[field] = receipt_connections_v1(values[field])
    return decode_record(RegistrationPayload, values)


def _job_document(text: str) -> dict[str, Any]:
    document = json.loads(text)
    if not isinstance(document, dict):
        raise ValueError("Invalid registration job")
    version = document.get("format_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported registration job version")
    if version == 1:
        for field in ("input_conn", "output_conn"):
            document["payload"][field] = receipt_connections_v1(
                document["payload"][field]
            )
        for file in document.get("files", ()):
            file["owner"] = receipt_owner_v1(file["owner"])
        document["format_version"] = 2
    return document


def encode_result(result: RegistrationResult) -> str:
    return json.dumps(
        {"format_version": 2, **record_document(result)}, ensure_ascii=False
    )


def decode_result(text: str) -> RegistrationResult:
    values = json.loads(text)
    if not isinstance(values, dict):
        raise ValueError("Invalid registration receipt")
    version = values.get("format_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported registration receipt version")
    history = (
        receipt_history_v1(values["history"]) if version == 1 else values["history"]
    )
    if type(values.get("history_id")) is not int or not isinstance(
        values.get("thumb_filepath"), str
    ):
        raise ValueError("Invalid registration receipt identity/path")
    asset = dict(values["asset"])
    if version == 1:
        for field in ("is_favorite_hda", "is_network", "is_sub_network"):
            if field in asset and type(asset[field]) is int and asset[field] in (0, 1):
                asset[field] = bool(asset[field])
    return RegistrationResult(
        asset=decode_record(AssetData, asset),
        history=decode_record(HistoryData, history),
        history_id=values["history_id"],
        thumb_filepath=Path(values["thumb_filepath"]),
    )


class RegistrationRecovery:
    def __init__(self, database: Path) -> None:
        self.database = database

    def jobs(self) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.database)) as db:
            db.row_factory = sqlite3.Row
            jobs = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM registration_jobs ORDER BY created_at DESC"
                )
            ]
            for job in jobs:
                payload = _job_document(job["document"])["payload"]
                job.update(name=payload["node_name"], version=payload["version"])
            return jobs

    def load(self, identity: str) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.database)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM registration_jobs WHERE id=:identity",
                {"identity": identity},
            ).fetchone()
            return dict(row) if row else None

    def save(
        self,
        identity: str,
        phase: str,
        document: dict[str, Any],
        error: str | None = None,
    ) -> None:
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute(
                "UPDATE registration_jobs SET phase=:phase,document=:document,error=:error,updated_at=:utc_now WHERE id=:identity AND phase!='committed'",
                {
                    "phase": phase,
                    "document": json.dumps(document),
                    "error": error,
                    "utc_now": utc_now(),
                    "identity": identity,
                },
            )

    def run(
        self,
        payload: RegistrationPayload,
        capture: Any,
        writer: Any,
        asset_id: int | None,
    ) -> RegistrationResult:
        from libs.operation_journal import operation_lock

        identity = payload.operation_id or new_identity()
        from uuid import UUID

        UUID(identity)
        payload = replace(payload, operation_id=identity)
        with operation_lock(self.database.parent):
            job = self.load(identity)
            if job and job["fingerprint"] != fingerprint(payload, asset_id):
                raise LibraryConflict("Registration ID belongs to different content")
            if job and job["phase"] == "committed":
                return decode_result(job["result"])
            if job and job["phase"] == "discarded":
                raise LibraryConflict("Registration was discarded; start a new request")
            document = (
                _job_document(job["document"])
                if job
                else payload_document(payload, asset_id)
            )
            if not job:
                document.update(
                    database=str(self.database.resolve()),
                    stage=str(payload.hda_dirpath / (".ihda-registration-" + identity)),
                    files=[],
                )
                with closing(sqlite3.connect(self.database)) as db, db:
                    db.execute(
                        "INSERT INTO registration_jobs (id,fingerprint,phase,document,result,error,created_at,updated_at) VALUES(:identity,:payload, 'prepared',:document,NULL,NULL,:utc_now,:utc_now)",
                        {
                            "identity": identity,
                            "payload": fingerprint(payload, asset_id),
                            "document": json.dumps(document),
                            "utc_now": utc_now(),
                        },
                    )
            if document.get("database") != str(self.database.resolve()):
                raise ValueError(
                    "Registration belongs to the original library location; files preserved for review"
                )
            try:
                self._capture(payload, capture, document, identity)
                self._publish(document, identity)
                result = writer.register(payload, asset_id)
                receipt = self.load(identity)
                if not receipt or receipt["phase"] != "committed":
                    raise RuntimeError(
                        "Registration completed without a durable receipt"
                    )
                shutil.rmtree(document["stage"], ignore_errors=True)
                return result
            except Exception as error:
                current = self.load(identity)
                if current and current["phase"] != "committed":
                    self.save(identity, current["phase"], document, str(error))
                raise

    def _capture(
        self,
        payload: RegistrationPayload,
        capture: Any,
        document: dict[str, Any],
        identity: str,
    ) -> None:
        if document["files"]:
            for item in document["files"]:
                content = measure_file(Path(item["source"]))
                if content.digest != item["digest"] or content.size != item["size"]:
                    raise ValueError("Staged registration file changed")
            return
        for filename in (payload.hda_filename, payload.thumb_filename):
            if Path(filename).name != filename or filename in {"", ".", ".."}:
                raise ValueError("Registration filenames must be plain filenames")
        if capture is None:
            raise ValueError(
                "Capture was interrupted; recapture the Houdini node in a new request"
            )
        stage = Path(document["stage"])
        files = (
            CaptureFile(
                source=stage / "asset",
                destination=payload.hda_dirpath / payload.hda_filename,
                capture=capture.asset,
                required=True,
            ),
            CaptureFile(
                source=stage / "thumbnail",
                destination=payload.thumb_dirpath / payload.thumb_filename,
                capture=capture.thumbnail,
            ),
        )
        if len({file.destination for file in files}) != len(files) or any(
            file.destination.exists() or file.destination.is_symlink() for file in files
        ):
            raise LibraryConflict("Registration destination already exists")
        stage.mkdir(parents=True, exist_ok=True)
        for file in files:
            file.capture(file.source)
        for file in files:
            source, destination = file.source, file.destination
            if file.required and (not source.is_file() or not source.stat().st_size):
                raise ValueError("Capture did not create an asset")
            if source.is_file():
                with source.open("rb") as stream:
                    os.fsync(stream.fileno())
                content = measure_file(source)
                document["files"].append(
                    {
                        "source": str(source),
                        "destination": str(destination),
                        "digest": content.digest,
                        "size": content.size,
                        "owner": None,
                    }
                )
        from libs.operation_journal import sync_directory

        sync_directory(stage)
        self.save(identity, "captured", document)

    def _publish(self, document: dict[str, Any], identity: str) -> None:
        for item in document["files"]:
            destination = Path(item["destination"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                info = destination.stat()
                if (
                    item["owner"] != {"device": info.st_dev, "inode": info.st_ino}
                    or destination.is_symlink()
                ):
                    raise LibraryConflict(
                        "Destination ownership is uncertain; retained for review"
                    )
                if measure_file(destination).digest == item["digest"]:
                    continue
                destination.unlink()
            self.save(identity, "captured", document)
            with destination.open("xb") as output:
                info = os.fstat(output.fileno())
                item["owner"] = {"device": info.st_dev, "inode": info.st_ino}
                self.save(identity, "captured", document)
                with Path(item["source"]).open("rb") as source:
                    shutil.copyfileobj(source, output)
                output.flush()
                os.fsync(output.fileno())
        from libs.operation_journal import sync_directory

        for item in document["files"]:
            sync_directory(Path(item["destination"]).parent)
        self.save(identity, "published", document)

    def retry(self, identity: str, writer: Any) -> RegistrationResult:
        job = self.load(identity)
        if job is None:
            raise ValueError("Registration job no longer exists")
        document = _job_document(job["document"])
        return self.run(decode_payload(document), None, writer, document["asset_id"])

    def discard(self, identity: str) -> None:
        from libs.library_maintenance import references
        from libs.operation_journal import operation_lock

        with (
            operation_lock(self.database.parent),
            closing(sqlite3.connect(self.database)) as db,
        ):
            job = self.load(identity)
            if job is None or job["phase"] == "committed":
                raise ValueError("A committed registration cannot be discarded")
            document = _job_document(job["document"])
            if document.get("database") != str(self.database.resolve()):
                raise ValueError(
                    "Registration belongs to the original library location; files preserved for review"
                )
            registered = {ref.path.resolve() for ref in references(db)}
            for item in document["files"]:
                path = Path(item["destination"])
                if path.is_symlink():
                    raise ValueError(
                        "File ownership is uncertain; symbolic link preserved"
                    )
                if not path.exists():
                    continue
                info = path.stat()
                if (
                    path.resolve() in registered
                    or item["owner"] != {"device": info.st_dev, "inode": info.st_ino}
                    or path.is_symlink()
                ):
                    raise ValueError(
                        "File ownership or references prevent cleanup; files retained"
                    )
            for item in document["files"]:
                Path(item["destination"]).unlink(missing_ok=True)
            shutil.rmtree(document["stage"], ignore_errors=True)
            self.save(identity, "discarded", document)
