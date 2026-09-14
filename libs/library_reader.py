"""Read snapshots through a narrow repository port with deterministic cleanup."""

from __future__ import annotations
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Protocol
from libs.domain import AssetData, HistoryData


class LibraryReadRepository(Protocol):
    def get_hda_data(
        self, category: str | None = None, user_id: str | None = None
    ) -> list[AssetData]: ...
    def get_hda_history(
        self,
        hda_key_id: int | None = None,
        user_id: str | None = None,
        search_date: object = None,
    ) -> list[HistoryData]: ...
    def close(self) -> None: ...


class LibraryReader:
    def __init__(
        self, open_repository: Callable[[Path], LibraryReadRepository]
    ) -> None:
        self._open_repository = open_repository

    def assets(
        self, path: Path | None, user: str | None, category: str | None = None
    ) -> list[AssetData]:
        if path is None or not path.is_file():
            return []
        with closing(self._open_repository(path)) as repository:
            return repository.get_hda_data(category=category, user_id=user)

    def history(
        self,
        path: Path | None,
        user: str | None,
        asset_id: int | None = None,
        search_date: object = None,
    ) -> list[HistoryData]:
        if path is None or not path.is_file():
            return []
        with closing(self._open_repository(path)) as repository:
            return repository.get_hda_history(
                hda_key_id=asset_id, user_id=user, search_date=search_date
            )
