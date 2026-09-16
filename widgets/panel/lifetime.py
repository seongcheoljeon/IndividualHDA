"""Ordered, retryable ownership of panel resources; no Qt dependency."""

from __future__ import annotations

from collections.abc import Callable


class PanelLifetime:
    def __init__(self) -> None:
        self._resources: dict[str, tuple[int, Callable[[], object]]] = {}

    def add(self, name: str, close: Callable[[], object], order: int) -> None:
        if name in self._resources:
            raise ValueError(f"Resource already owned: {name}")
        self._resources[name] = order, close

    def close(self) -> list[tuple[str, Exception]]:
        errors = []
        for name, (_, close) in sorted(
            self._resources.items(), key=lambda item: item[1][0]
        ):
            try:
                close()
            except Exception as error:
                errors.append((name, error))
                break  # Do not destroy dependent views while an earlier worker is live.
            else:
                del self._resources[name]
        return errors
