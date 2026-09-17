"""Registration/rename/delete coordination with commit-before-display semantics."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TypeVar

from libs.asset_contracts import AssetData
from libs.asset_lifecycle import AssetLifecycleGateway, RenameResult
from libs.asset_registration import RegistrationCapture, RegistrationService
from libs.repository import RegistrationPayload, RegistrationResult

Result = TypeVar("Result")


class CommandView(Protocol):
    def show_command_error(self, message: str) -> None: ...


class AssetCommandPresenter:
    def __init__(
        self,
        view: CommandView,
        gateway: AssetLifecycleGateway,
        committed_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._committed_error = committed_error
        self._view = view
        self._gateway = gateway

    def _execute(
        self, operation: Callable[[], Result], committed: Callable[[Result], None]
    ) -> bool:
        try:
            result = operation()
        except Exception as error:
            self._view.show_command_error(str(error))
            return False
        # UI errors must not be misreported as rolled-back storage transactions.
        try:
            committed(result)
        except Exception as error:
            if self._committed_error is None:
                raise
            self._committed_error(error)
        return True

    def register(
        self,
        payload: RegistrationPayload,
        asset_id: int | None,
        committed: Callable[[RegistrationResult], None],
    ) -> bool:
        return self._execute(
            lambda: self._gateway.register(payload, asset_id), committed
        )

    def capture_and_register(
        self,
        service: RegistrationService,
        payload: RegistrationPayload,
        capture: RegistrationCapture,
        asset_id: int | None,
        committed: Callable[[RegistrationResult], None],
    ) -> bool:
        return self._execute(
            lambda: service.register(payload, capture, asset_id), committed
        )

    def rename(
        self, asset: AssetData, name: str, committed: Callable[[RenameResult], None]
    ) -> bool:
        return self._execute(lambda: self._gateway.rename(asset, name), committed)

    def delete(
        self, asset_id: int, directory: Path, committed: Callable[[None], None]
    ) -> bool:
        return self._execute(
            lambda: self._gateway.delete(asset_id, directory), committed
        )

    def delete_history(
        self,
        asset_id: int,
        history_id: int,
        files: Sequence[Path],
        committed: Callable[[None], None],
    ) -> bool:
        return self._execute(
            lambda: self._gateway.delete_history(asset_id, history_id, files), committed
        )
