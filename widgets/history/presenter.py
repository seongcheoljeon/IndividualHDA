"""History date filtering policy; Qt date conversion belongs to the view."""

from __future__ import annotations

from datetime import date
from typing import Protocol


class HistoryView(Protocol):
    def show_history_dates(self, dates: list[str]) -> None: ...
    def show_history_error(self, message: str) -> None: ...


class HistoryPresenter:
    def __init__(self, view: HistoryView) -> None:
        self._view = view

    def filter_dates(self, enabled: bool, start: date, end: date) -> None:
        if enabled and start > end:
            self._view.show_history_error(
                "Search start date must not be after the end date."
            )
            return
        self._view.show_history_dates(
            [start.isoformat(), end.isoformat()] if enabled else []
        )
