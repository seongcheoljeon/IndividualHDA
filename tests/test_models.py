"""Item models are pure views: no I/O and no mutation while painting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore

from libs.asset_contracts import AssetData, HistoryData
from model.ihda_history_model import HistoryModel
from model.ihda_list_model import ListModel
from model.ihda_table_model import TableModel


def asset(n: int, available: bool = True) -> AssetData:
    return AssetData(
        hda_id=n,
        hda_name=f"a{n}",
        hda_dirpath=Path("/nowhere"),
        hda_filename=f"a{n}.hda",
        available=available,
    )


def history(n: int, available: bool = True) -> HistoryData:
    return HistoryData(
        hist_id=n,
        hda_id=1,
        org_hda_name="a",
        version=f"{n}.0",
        ihda_dirpath=Path("/nowhere"),
        ihda_filename="a.hda",
        available=available,
    )


@pytest.mark.parametrize(
    ("model_type", "make"),
    [(ListModel, asset), (TableModel, asset), (HistoryModel, history)],
)
def test_data_and_flags_never_touch_the_filesystem_or_the_rows(
    app: Any, monkeypatch: pytest.MonkeyPatch, model_type: Any, make: Any
) -> None:
    def boom(self: Path) -> bool:
        raise AssertionError("stat() during paint")

    monkeypatch.setattr(Path, "exists", boom)
    model = model_type(items=[make(1), make(2, available=False)])
    index = model.index(1, 0)
    first = index.data(model_type.data_role)
    for role in (
        QtCore.Qt.ItemDataRole.DisplayRole,
        QtCore.Qt.ItemDataRole.FontRole,
        QtCore.Qt.ItemDataRole.DecorationRole,
    ):
        index.data(role)
    index.flags()
    # The same object comes back: data() no longer rebuilds the row.
    assert index.data(model_type.data_role) is first
    assert index.data(QtCore.Qt.ItemDataRole.FontRole).strikeOut()
    assert not model.index(0, 0).data(QtCore.Qt.ItemDataRole.FontRole).strikeOut()
    assert not index.flags() & QtCore.Qt.ItemFlag.ItemIsDragEnabled


@pytest.mark.parametrize(
    ("model_type", "make"),
    [(ListModel, asset), (TableModel, asset), (HistoryModel, history)],
)
def test_item_row_follows_row_operations(app: Any, model_type: Any, make: Any) -> None:
    model = model_type(items=[make(1), make(2), make(3)])
    assert [
        model.index(r, 0).data(model_type.data_role).item_row for r in range(3)
    ] == [0, 1, 2]
    model.remove_item(0)
    assert [
        model.index(r, 0).data(model_type.data_role).item_row for r in range(2)
    ] == [0, 1]
    model.append_item(make(4))
    assert model.index(2, 0).data(model_type.data_role).item_row == 2
    model.reload([make(9)]) if hasattr(model, "reload") else model.add_items([make(9)])
    assert model.index(0, 0).data(model_type.data_role).item_row == 0
