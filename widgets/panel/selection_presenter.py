"""Selection restoration policy independent of views and storage implementations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from libs.domain import AssetData, HistoryData, SelectionState


class SelectionView(Protocol):
    def show_asset_selection(self) -> None: ...
    def show_history_selection(self) -> None: ...
    def refresh_selection_dependents(self) -> None: ...


class PanelSelectionPresenter:
    def __init__(self, state: SelectionState, view: SelectionView) -> None:
        self.state = state
        self._view = view

    def select_asset(
        self, data: AssetData | None, row: int | None, field: str | None
    ) -> None:
        self.state.select_asset(data, row, field)
        self._view.show_asset_selection()
        self._view.refresh_selection_dependents()

    def select_history(
        self, data: HistoryData | None, row: int | None, field: str | None
    ) -> None:
        self.state.select_history(data, row, field)
        self._view.show_history_selection()
        self._view.refresh_selection_dependents()

    def restore(
        self, assets: Sequence[AssetData], histories: Sequence[HistoryData]
    ) -> None:
        """Rebuild every derived field by identity, never by the old row number."""
        asset_id, history_id = self.state.asset.id, self.state.history.hist_id
        asset_field, history_field = self.state.asset.field, self.state.history.field
        self.state.clear_asset()
        self.state.clear_history()
        for row, asset in enumerate(assets):
            if asset["hda_id"] == asset_id:
                self.state.select_asset(asset, row, asset_field)
                break
        for row, history in enumerate(histories):
            if history["hist_id"] == history_id:
                self.state.select_history(history, row, history_field)
                break
