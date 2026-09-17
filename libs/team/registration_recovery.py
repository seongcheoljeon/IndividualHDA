"""Resume captured Team registrations and uploads using the existing command receipt."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from libs.file_integrity import measure_file
from libs.library_metadata import new_identity
from libs.operation_journal import operation_lock
from libs.settings_store import save_json
from libs.team.contracts import Command, TeamError


class TeamRegistrationRecovery:
    def __init__(self, root: Path, namespace: str) -> None:
        self.root, self.namespace = root, namespace
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, identity: str) -> Path:
        from uuid import UUID

        UUID(identity)
        return self.root / (identity + ".json")

    def load(self, identity: str) -> dict[str, Any]:
        value = json.loads(self._path(identity).read_text(encoding="utf-8"))
        if value["namespace"] != self.namespace:
            raise TeamError("Registration belongs to a different account or library")
        return dict(value)

    def jobs(self) -> list[dict[str, Any]]:
        rows = []
        for path in self.root.glob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            if value["namespace"] == self.namespace:
                request = value.get("request", {})
                metadata = value.get("metadata", {})
                value.update(
                    name=request.get("name")
                    or metadata.get("hda_name")
                    or value.get("node_path", "Captured asset"),
                    version=request.get("version") or metadata.get("hda_version", ""),
                )
                rows.append(value)
        return rows

    def save(self, job: dict[str, Any]) -> None:
        save_json(self._path(job["id"]), job)
        from libs.operation_journal import sync_directory

        sync_directory(self.root)

    def begin_capture(self, node_path: str) -> tuple[str, Path]:
        identity = new_identity()
        stage = self.root / identity
        self.save(
            {
                "id": identity,
                "namespace": self.namespace,
                "phase": "prepared",
                "stage": str(stage),
                "node_path": node_path,
                "error": None,
            }
        )
        stage.mkdir()
        return identity, stage

    def captured(
        self,
        identity: str,
        path: Path,
        metadata: dict[str, Any],
        thumbnail: Path | None,
    ) -> None:
        job = self.load(identity)
        from libs.operation_journal import sync_tree

        sync_tree(Path(job["stage"]))
        job.update(
            phase="captured",
            path=str(path),
            metadata=metadata,
            thumbnail=str(thumbnail) if thumbnail else None,
        )
        self.save(job)

    def prepare(
        self,
        path: Path,
        name: str,
        category: str,
        version: str,
        metadata: dict[str, Any],
        thumbnail: Path | None,
        asset: dict[str, Any] | None,
        description: str,
        identity: str | None = None,
    ) -> str:
        identity = identity or new_identity()
        job: dict[str, Any] = (
            self.load(identity)
            if self._path(identity).exists()
            else {
                "id": identity,
                "namespace": self.namespace,
                "phase": "captured",
                "stage": None,
            }
        )
        if job.get("request"):
            raise TeamError(
                "This capture already has a registration request; use Recovery to retry"
            )
        files = {}
        for kind, value in (("asset", path), ("thumbnail", thumbnail)):
            if value is not None:
                files[kind] = {"path": str(value), **asdict(measure_file(value))}
        job.update(
            request={
                "name": name,
                "category": category,
                "version": version,
                "metadata": metadata,
                "asset": asset,
                "description": description,
            },
            files=files,
            error=None,
        )
        self.save(job)
        return identity

    def retry(self, identity: str, backend: Any, pending: Any) -> dict[str, Any]:
        with operation_lock(self.root):
            job = self.load(identity)
            if job["phase"] == "committed":
                return dict(job["result"])
            if job["phase"] == "discarded":
                raise TeamError("Registration has been discarded")
            try:
                current = pending.load()
                if current and current.request_id != identity:
                    raise TeamError("Resolve the other pending request first")
                if not job.get("command"):
                    if not job.get("request"):
                        # Completed capture before presenter was reached can resume as a new asset.
                        metadata = job.get("metadata")
                        if not metadata:
                            raise TeamError(
                                "Capture was interrupted; recapture the Houdini node"
                            )
                        self.prepare(
                            Path(job["path"]),
                            metadata["hda_name"],
                            metadata["hda_cate"],
                            metadata["hda_version"],
                            metadata,
                            Path(job["thumbnail"]) if job.get("thumbnail") else None,
                            None,
                            "",
                            identity,
                        )
                        job = self.load(identity)
                    files = {}
                    for kind, item in job["files"].items():
                        path = Path(item["path"])
                        content = measure_file(path)
                        if (
                            content.digest != item["digest"]
                            or content.size != item["size"]
                        ):
                            raise TeamError(
                                "Registration file changed; start a new request"
                            )
                        files[kind] = asdict(backend.upload(path))
                    request = job["request"]
                    asset = request["asset"]
                    values = {
                        "version": request["version"],
                        "description": request["description"],
                        "metadata": request["metadata"],
                        "files": files,
                    }
                    if asset is None:
                        values.update(
                            name=request["name"], category=request["category"]
                        )
                    command = Command(
                        "version" if asset else "create",
                        request_id=identity,
                        asset_id=asset["id"] if asset else None,
                        expected_revision=asset["revision"] if asset else None,
                        values=values,
                    )
                    command.validate()
                    job.update(command=asdict(command), phase="published")
                    self.save(job)
                command = Command(**job["command"])
                if current is None:
                    pending.save(command)
                result = backend.execute(command)
                job.update(result=result, phase="committed", error=None)
                self.save(job)
                pending.clear(identity)
                if job.get("stage"):
                    shutil.rmtree(job["stage"], ignore_errors=True)
                return dict(result)
            except Exception as error:
                job["error"] = str(error)
                self.save(job)
                raise

    def discard(self, identity: str) -> None:
        with operation_lock(self.root):
            job = self.load(identity)
            if job.get("command") or job["phase"] == "committed":
                raise TeamError(
                    "Submitted registrations must be resolved by Retry before cleanup"
                )
            if job.get("stage"):
                stage = Path(job["stage"])
                if stage != self.root / identity:
                    raise TeamError("Unexpected capture directory; preserved")
                shutil.rmtree(stage, ignore_errors=True)
            job.update(phase="discarded")
            self.save(job)
