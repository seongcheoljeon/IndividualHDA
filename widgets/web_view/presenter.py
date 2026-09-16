"""Web zoom policy in logical units; apply host display scaling only once."""

from __future__ import annotations

from typing import Protocol


class WebZoomView(Protocol):
    def show_zoom(self, factor: float) -> None: ...


class WebPresenter:
    def __init__(self, view: WebZoomView, scale: float = 1.0) -> None:
        self._view = view
        self._scale = scale

    def zoom(self, physical_factor: float, multiplier: float) -> None:
        logical_factor = physical_factor / self._scale * multiplier
        self._view.show_zoom(min(5.0, max(0.25, logical_factor)) * self._scale)

    def reset_zoom(self) -> None:
        self._view.show_zoom(self._scale)
