"""Media metadata commit policy; capture/encoding and Qt models are adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class MediaRequest:
    asset_id: int
    version: str
    directory: Path
    filename: str


class MediaGateway(Protocol):
    def set_thumbnail(
        self, asset_id: int, directory: Path, filename: str, version: str
    ) -> bool: ...
    def set_video(
        self, asset_id: int, directory: Path, filename: str, version: str
    ) -> str: ...


class MediaView(Protocol):
    def show_media_error(self, message: str) -> None: ...


class AssetMediaPresenter:
    def __init__(self, view: MediaView, gateway: MediaGateway) -> None:
        self._view = view
        self._gateway = gateway

    def thumbnail(
        self, request: MediaRequest, committed: Callable[[bool], None]
    ) -> bool:
        try:
            updated = self._gateway.set_thumbnail(
                request.asset_id, request.directory, request.filename, request.version
            )
        except Exception as error:
            self._view.show_media_error(str(error))
            return False
        committed(updated)
        return True

    def video(self, request: MediaRequest, committed: Callable[[str], None]) -> bool:
        try:
            kind = self._gateway.set_video(
                request.asset_id, request.directory, request.filename, request.version
            )
        except Exception as error:
            self._view.show_media_error(str(error))
            return False
        committed(kind)
        return True
