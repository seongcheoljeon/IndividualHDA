"""History date filtering policy; Qt date conversion belongs to the view."""

from __future__ import annotations

from datetime import date
from typing import Protocol


class HistoryView(Protocol):
    def show_history_dates(self, dates: list[str]) -> None: ...


class HistoryPresenter:
    def __init__(self, view: HistoryView) -> None:
        self._view = view

    def filter_dates(self, enabled: bool, start: date, end: date) -> None:
        """An inverted range is a typing slip: filter the sorted range."""
        if not enabled:
            self._view.show_history_dates([])
            return
        first, last = sorted((start, end))
        self._view.show_history_dates([first.isoformat(), last.isoformat()])
