"""Explicit owners of session, panel lifetime and view references."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from libs.domain import LibraryContext
from libs.repository import LibraryRepository, LibraryUnavailable

if TYPE_CHECKING:
    from view.ihda_category_view import CategoryView
    from view.ihda_history_view import HistoryView
    from view.ihda_inside_view import InsideView
    from view.ihda_list_view import ListView
    from view.ihda_record_view import RecordView
    from view.ihda_table_view import TableView
    from widgets.panel.library_session import PanelLibrarySession


@dataclass(slots=True)
class PanelSessionState:
    user: str = ""
    context: LibraryContext | None = None
    repository: LibraryRepository | None = None
    actions: PanelLibrarySession = field(init=False)
    generation: int = 0

    def replace(
        self, context: LibraryContext | None, repository: LibraryRepository | None
    ) -> None:
        self.context, self.repository = context, repository
        self.generation += 1

    def require_repository(self) -> LibraryRepository:
        if self.repository is None:
            raise LibraryUnavailable("Select a library first")
        return self.repository

    def require_context(self) -> LibraryContext:
        if self.context is None:
            raise LibraryUnavailable("Select a personal library first")
        return self.context


@dataclass(slots=True)
class PanelStatus:
    closing: bool = False
    close_requested: bool = False
    host_destroying: bool = False
    ready: bool = False
    reset_settings: bool = False
    embedded: bool = False


class PanelViews:
    """Assigned by bootstrap before any feature is connected to UI signals."""

    category: CategoryView
    history: HistoryView
    inside: InsideView
    record: RecordView
    assets_list: ListView
    assets_table: TableView
