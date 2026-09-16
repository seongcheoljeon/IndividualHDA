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
        return self.catalog.execute(command)
