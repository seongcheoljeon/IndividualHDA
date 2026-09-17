"""Personal SQLite adapter. Storage operations share one transaction session."""

from libs.database.assets import AssetsOperations
from libs.database.catalog import CatalogOperations
from libs.database.history import HistoryOperations
from libs.database.nodes import NodesOperations
from libs.database.records import RecordsOperations
from libs.database.session import DatabaseSession
from libs.database.values import DatabaseValues


class SQLite3DatabaseAPI(
    HistoryOperations,
    RecordsOperations,
    NodesOperations,
    CatalogOperations,
    AssetsOperations,
    DatabaseValues,
    DatabaseSession,
):
    """Individual HDA library database."""

    def trash_asset(self, asset_id: int) -> None:
        from libs.database.lifecycle import PersonalLifecycle

        with self.transaction():
            PersonalLifecycle(self._connect).change(asset_id, "delete")

    def trash_history(self, asset_id: int, history_id: int) -> None:
        from libs.database.lifecycle import PersonalLifecycle
        from libs.repository import LibraryConflict

        try:
            with self.transaction():
                PersonalLifecycle(self._connect).change(asset_id, "delete", history_id)
        except LibraryConflict as error:
            raise ValueError(str(error)) from error
