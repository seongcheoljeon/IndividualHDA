"""HTTP adapter for a validated copy destination."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from libs.team.client import HttpCatalog
from libs.team.contracts import (
    API_PREFIX,
    API_VERSION,
    Blob,
    Command,
    Forbidden,
    NotFound,
    TeamError,
)


class HttpCopyDestination:
    def __init__(self, catalog: HttpCatalog) -> None:
        self.catalog = catalog
        health = catalog.transport.request("GET", "/health")
        if health.get("api_version") != API_VERSION or "asset_copy" not in health.get(
            "capabilities", []
        ):
            raise TeamError("Update the team server to support asset copying")
        self.tracking_supported = "version_tracking" in health.get("capabilities", [])
        user = catalog.transport.request("GET", API_PREFIX + "/me")
        project = next(
            (item for item in user["projects"] if item["id"] == catalog.project_id),
            None,
        )
        if project is None or project["role"] == "viewer":
            raise Forbidden(
                "Copying requires editor or owner access to the destination"
            )
        self.identity = json.dumps(
            [
                getattr(catalog.transport, "url", catalog.namespace),
                catalog.project_id,
                user["user_id"],
            ]
        )
        self._base = f"{API_PREFIX}/projects/{catalog.project_id}"

    def check(self, values: dict[str, Any]) -> dict[str, Any]:
        if not self.tracking_supported and any(
            version.get("checks")
            or any(
                dependency.get("version_uuid") or dependency.get("asset_uuid")
                for dependency in version["values"].get("dependencies", [])
            )
            for version in values["versions"]
        ):
            raise TeamError(
                "Update the team server to preserve version tracking during copying"
            )
        return dict(
            self.catalog.transport.request(
                "GET",
                self._base
                + "/copy-check?"
                + urlencode(
                    {
                        "name": values["name"],
                        "category": values["category"],
                        **values["origin"],
                    }
                ),
            )
        )

    def has_blob(self, blob: dict[str, Any]) -> bool:
        try:
            info = self.catalog.transport.request(
                "GET", self._base + "/blobs/" + blob["digest"] + "/info"
            )
            return bool(info["size"] == blob["size"])
        except NotFound:
            return False

    def upload(self, path: Path) -> Blob:
        return self.catalog.upload(path)

    def execute(self, command: Command) -> dict[str, Any]:
        if not self.tracking_supported and command.operation == "copy_asset":
            from copy import deepcopy
            from dataclasses import replace

            values = deepcopy(command.values)
            for version in values["versions"]:
                if version.pop("checks", []):
                    raise TeamError("Update the team server to preserve copied checks")
                for dependency in version["values"].get("dependencies", []):
                    if dependency.get("asset_uuid") or dependency.get("version_uuid"):
                        raise TeamError(
                            "Update the team server to preserve dependency identities"
                        )
                    for key in (
                        "library_uuid",
                        "asset_uuid",
                        "version_uuid",
                        "resolution",
                    ):
                        dependency.pop(key, None)
            command = replace(command, values=values)
        return self.catalog.execute(command)
