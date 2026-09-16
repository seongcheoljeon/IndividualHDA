"""Reload lifecycle and stale-result policy; no Qt or concrete repository imports."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class SyncView(Protocol):
    def sync_allowed(self) -> bool: ...
    def sync_context(self) -> tuple[object, int]: ...
    def read_snapshot(self) -> Callable[[], tuple[Any, ...]] | None: ...
    def show_snapshot(self, snapshot: tuple[Any, ...]) -> None: ...
    def show_sync_error(self, message: str) -> None: ...


class SyncExecutor(Protocol):
    def submit(
        self,
        operation: Callable[[], Any],
        finished: Callable[[Any, Exception | None], None],
    ) -> bool: ...


class LibrarySyncPresenter:
    def __init__(
        self, view: SyncView, executor: SyncExecutor, revision: int = 0
    ) -> None:
        self._view = view
        self._executor = executor
        self.known_revision = revision
        self.pending = False
        self._closed = False

    def revision_polled(self, revision: int) -> None:
        if not self._closed and revision != self.known_revision:
            self.pending = True

    def idle(self) -> None:
        if self.pending:
            self.refresh()

    def refresh(self) -> None:
        if self._closed:
            return
        if not self._view.sync_allowed():
            self.pending = True
            return
        operation = self._view.read_snapshot()
        if operation is None:
            self.pending = False
            return
        repository, write_generation = self._view.sync_context()

        def finished(snapshot: Any, error: Exception | None) -> None:
            if self._closed:
                return
            current_repository, current_generation = self._view.sync_context()
            if repository is not current_repository:
                return
            if error is not None:
                self.pending = False
                self._view.show_sync_error(str(error))
            elif write_generation != current_generation:
                # Retry after the save completes; never install pre-save metadata.
                self.pending = True
            else:
                self.accept(snapshot)
                self._view.show_snapshot(snapshot)

        self.pending = False
        try:
            if not self._executor.submit(operation, finished):
                self.pending = True
        except Exception as error:
            finished(None, error)

    def accept(self, snapshot: tuple[Any, ...]) -> None:
        self.pending = False
        self.known_revision = snapshot[0]

    def close(self) -> None:
        self._closed = True
        self.pending = False
