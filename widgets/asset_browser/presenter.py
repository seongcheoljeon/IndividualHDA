"""Search presentation without Qt, SQL, filesystem or main-window dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from threading import Event
from typing import Protocol

from libs.browser_search import AssetSearchGateway, SearchRequest


class BrowserView(Protocol):
    def show_busy(self, busy: bool) -> None: ...
    def show_error(self, message: str) -> None: ...
    def show_results(self, ids: frozenset[int]) -> None: ...
    def filter_text(self, request: SearchRequest) -> None: ...
    def show_library_available(self, available: bool) -> None: ...


class SearchExecutor(Protocol):
    """Deliver only current results; callbacks are connected at composition time."""

    def submit(self, text: str, search: Callable[[str, Event], list[int]]) -> None: ...
    def cancel(self) -> None: ...
    def drain(self) -> None: ...


class AssetBrowserPresenter:
    def __init__(
        self,
        browser_view: BrowserView,
        search_executor: SearchExecutor,
        search_gateway: AssetSearchGateway | None = None,
    ) -> None:
        self._browser_view = browser_view
        self._search_executor = search_executor
        self._search_gateway = search_gateway
        self._search_request = SearchRequest()
        self._is_closed = False

    def invalidate(self) -> None:
        """Invalidate on input change, before the debounce interval elapses."""
        self._search_executor.cancel()
        self._browser_view.show_busy(False)

    def change_gateway(self, search_gateway: AssetSearchGateway | None) -> None:
        self.invalidate()
        self._search_gateway = search_gateway
        self._browser_view.show_library_available(search_gateway is not None)

    def search(self, request: SearchRequest) -> None:
        if self._is_closed:
            return
        self.invalidate()
        self._search_request = replace(request, text=request.text.strip())
        self._browser_view.show_error("")
        search_gateway = self._search_gateway
        if not self._search_request.text or search_gateway is None:
            self._browser_view.filter_text(self._search_request)
            return
        search_request = self._search_request
        self._browser_view.show_busy(True)
        self._search_executor.submit(
            search_request.text,
            lambda text, cancel: search_gateway.search(
                replace(search_request, text=text), cancel
            ),
        )

    def results(self, ids: frozenset[int]) -> None:
        if not self._is_closed:
            self._browser_view.show_busy(False)
            self._browser_view.show_results(ids)

    def failed(self, error: Exception) -> None:
        if not self._is_closed:
            self._browser_view.show_busy(False)
            self._browser_view.show_error(f"search failed: {error}")

    def close(self) -> None:
        self._is_closed = True
        self.invalidate()
        self._search_executor.drain()
