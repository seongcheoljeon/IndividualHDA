"""Backward-compatible database entry point.

Domain operations share one connection and transaction through DatabaseSession.
Existing callers retain their method signatures, return values and context manager.
"""

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
