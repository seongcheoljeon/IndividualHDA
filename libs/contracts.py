"""Small structural contracts for domain/application code; no Qt or HOM imports."""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol


class TransactionalRepository(Protocol):
    @property
    def db_filepath(self) -> Path: ...
    @property
    def in_transaction(self) -> bool: ...
    def transaction(self) -> AbstractContextManager[object]: ...
    def record_operation_commit(self, operation_id: str) -> None: ...


class AssetDeletionRepository(TransactionalRepository, Protocol):
    def delete_hda_key_with_id(self, hda_key_id: int | None = None) -> int | None: ...


class HistoryDeletionRepository(TransactionalRepository, Protocol):
    def is_library_file_referenced(
        self, path: Path, excluding_history_id: int
    ) -> bool: ...
    def is_most_recent_ihda_history(
        self, hda_key_id: int | None = None, hist_id: int | None = None
    ) -> bool: ...
    def delete_hda_history(
        self, hda_key_id: int | None = None, hist_id: int | None = None
    ) -> int | None: ...


class FileMoves(Protocol):
    def move(self, source: Path, destination: Path) -> None: ...


class OperationFactory(Protocol):
    def __call__(
        self, directory: Path, db: TransactionalRepository | None = None
    ) -> AbstractContextManager[FileMoves]: ...


class RowNotifications(Protocol):
    def begin_reset(self) -> None: ...
    def end_reset(self) -> None: ...
    def begin_insert(self, row: int) -> None: ...
    def end_insert(self) -> None: ...
    def begin_remove(self, row: int) -> None: ...
    def end_remove(self) -> None: ...
    def changed(self, row: int) -> None: ...


class SilentRows:
    """Domain storage can be used without a GUI observer."""

    def begin_reset(self) -> None:
        pass

    def end_reset(self) -> None:
        pass

    def begin_insert(self, row: int) -> None:
        pass

    def end_insert(self) -> None:
        pass

    def begin_remove(self, row: int) -> None:
        pass

    def end_remove(self) -> None:
        pass

    def changed(self, row: int) -> None:
        pass
