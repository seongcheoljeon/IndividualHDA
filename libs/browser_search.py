"""Transport-independent search boundary for the desktop asset browser.

IDs filter the existing in-memory store in this first migration. A server-backed
paged browser will need a separate result-page contract, not an ID-per-row RPC.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Protocol

from libs.runtime_settings import DEFAULT_RUNTIME
from libs.search_limits import SEARCH_RESULT_LIMIT


@dataclass(frozen=True, slots=True)
class SearchPolicy:
    delay_ms: int = DEFAULT_RUNTIME.search_delay_ms
    immediate_rows: int = 1000

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or not 0 < value <= 2_147_483_647
            for value in (self.delay_ms, self.immediate_rows)
        ):
            raise ValueError("Search limits must be positive Qt-compatible integers")


@dataclass(frozen=True, slots=True)
class SearchRequest:
    text: str = ""
    field: str = "Name"
    case_sensitive: bool = False


class AssetSearchGateway(Protocol):
    def search(self, request: SearchRequest, cancel: Event) -> list[int]: ...


class SearchRepository(Protocol):
    def search_asset_ids(
        self,
        query: str,
        *,
        field: str = "All",
        case_sensitive: bool = False,
        limit: int = SEARCH_RESULT_LIMIT,
        cancel: Event | None = None,
    ) -> list[int]: ...


class RepositoryAssetSearch:
    """Local adapter; connections and query syntax remain repository concerns."""

    def __init__(self, repository: SearchRepository) -> None:
        self._repository = repository

    def search(self, request: SearchRequest, cancel: Event) -> list[int]:
        return self._repository.search_asset_ids(
            request.text,
            field=request.field,
            case_sensitive=request.case_sensitive,
            cancel=cancel,
        )
