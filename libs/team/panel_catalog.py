"""Read model preparation for the main panel, performed entirely in its worker."""

from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Any

from libs.search_limits import TEAM_PAGE_DEFAULT
from libs.team.client import HttpCatalog
from libs.team.contracts import Blob, Command, Page, Unavailable


class PanelCatalog:
    def __init__(
        self, backend: HttpCatalog, *, page_size: int = TEAM_PAGE_DEFAULT
    ) -> None:
        from libs.search_limits import TEAM_PAGE_MAX

        if type(page_size) is not int or not 1 <= page_size <= TEAM_PAGE_MAX:
            raise ValueError("Invalid team page size")
        self.page_size = page_size
        self.backend = backend
        self.cancel = Event()

    @property
    def namespace(self) -> str:
        return self.backend.namespace

    def list_assets(
        self, query: str = "", offset: int = 0, limit: int = TEAM_PAGE_DEFAULT
    ) -> Page:
        # The existing models own filtering, sorting and category navigation.
        # Fetch metadata in bounded pages; HDA/video files remain on demand.
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            if self.cancel.is_set():
                raise Unavailable("Library loading stopped")
            page = self.backend.list_assets(query, offset, self.page_size)
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

    def tracking_supported(self) -> bool:
        return self.backend.tracking_supported()

    def tracking_read(
        self,
        kind: str,
        asset_uuid: str,
        version_uuid: str | None = None,
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> list[dict[str, Any]]:
        return self.backend.tracking_read(kind, asset_uuid, version_uuid, offset, limit)

    def tracking_execute(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.backend.tracking_execute(body)
