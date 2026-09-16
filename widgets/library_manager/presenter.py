"""Explorer paging and stale-result handling without Qt or database access."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageRequest:
    generation: int
    offset: int
    append: bool


class LibraryManagerPresenter:
    def __init__(self) -> None:
        self._generation = 0
        self._offset = 0

    def invalidate(self) -> None:
        self._generation += 1
        self._offset = 0

    def request(self, more: bool) -> PageRequest:
        return PageRequest(self._generation, self._offset if more else 0, more)

    def receive(self, request: PageRequest, count: int) -> str | None:
        if request.generation != self._generation:
            return None
        self._offset = request.offset + count
        suffix = " · end of results" if count < 200 else " · load next page for more"
        return f"{self._offset} assets loaded" + suffix
