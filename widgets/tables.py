"""The look the panel's tables settled on, for the dialogs to share.

Grid lines and a row-number column make a table read like a spreadsheet. The
asset and history views dropped both; anything that shows rows in a dialog
should match, so this is the one place that decides it.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

View = QtWidgets.QAbstractItemView


def configure_table(
    table: QtWidgets.QTableWidget | QtWidgets.QTableView,
    *,
    rows_selectable: bool = True,
    single_selection: bool = True,
    stretch_column: int | None = None,
) -> None:
    """No grid, no row numbers, banded rows, a quiet left-aligned header."""
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    table.setEditTriggers(View.EditTrigger.NoEditTriggers)
    if rows_selectable:
        table.setSelectionBehavior(View.SelectionBehavior.SelectRows)
    if single_selection:
        table.setSelectionMode(View.SelectionMode.SingleSelection)
    vertical = table.verticalHeader()
    if vertical is not None:
        vertical.hide()
    header = table.horizontalHeader()
    if header is not None:
        header.setHighlightSections(False)
        header.setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(36)
        if stretch_column is not None:
            header.setSectionResizeMode(
                stretch_column, QtWidgets.QHeaderView.ResizeMode.Stretch
            )
