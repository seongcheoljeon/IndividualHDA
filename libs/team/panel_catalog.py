"""Read model preparation for the main panel, performed entirely in its worker."""

from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Any

from libs.team.client import HttpCatalog
from libs.team.contracts import Blob, Command, Page, Unavailable


class PanelCatalog:
    def __init__(self, backend: HttpCatalog) -> None:
        self.backend = backend
        self.cancel = Event()

    @property
    def namespace(self) -> str:
        return self.backend.namespace

    def list_assets(self, query: str = "", offset: int = 0, limit: int = 100) -> Page:
        # The existing models own filtering, sorting and category navigation.
        # Fetch metadata in bounded pages; HDA/video files remain on demand.
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            if self.cancel.is_set():
                raise Unavailable("Library loading stopped")
            page = self.backend.list_assets(query, offset, 200)
            rows.extend(page.items)
            offset += len(page.items)
            if offset >= page.total or not page.items:
                return Page(rows, page.total, 0, max(1, len(rows)), page.revision)

    def get_asset(self, asset_id: int) -> dict[str, Any]:
        return self.backend.get_asset(asset_id)

    def histories(self, asset_id: int) -> list[dict[str, Any]]:
        return self.backend.histories(asset_id)

    def execute(self, command: Command) -> dict[str, Any]:
        return self.backend.execute(command)

    def file_status(self, asset_id: int) -> list[dict[str, Any]]:
        return self.backend.file_status(asset_id)

    def trash(self) -> list[dict[str, Any]]:
        return self.backend.trash()

    def events(self, asset_uuid: str) -> list[dict[str, Any]]:
        return self.backend.events(asset_uuid)

    def upload(self, path: Path) -> Blob:
        return self.backend.upload(path)

    def download(self, blob: Blob) -> Path:
        if self.cancel.is_set():
            raise Unavailable("Library loading stopped")
        return self.backend.download(blob)
