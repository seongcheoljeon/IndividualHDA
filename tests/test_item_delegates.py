"""Delegates draw from roles only and route the star click to one signal."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets
from test_models import asset

from model.ihda_list_model import ListModel
from widgets.item_delegates import CardDelegate, star_rect


def option_for(
    rect: QtCore.QRect, *, hover: bool = False, selected: bool = False
) -> Any:
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = rect
    option.state = QtWidgets.QStyle.StateFlag.State_Enabled
    if hover:
        option.state |= QtWidgets.QStyle.StateFlag.State_MouseOver
    if selected:
        option.state |= QtWidgets.QStyle.StateFlag.State_Selected
    return option


def render(delegate: Any, option: Any, index: QtCore.QModelIndex) -> QtGui.QImage:
    image = QtGui.QImage(option.rect.size(), QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    delegate.paint(painter, option, index)
    painter.end()
    return image


def painted(image: QtGui.QImage) -> int:
    return sum(
        1
        for y in range(0, image.height(), 4)
        for x in range(0, image.width(), 4)
        if image.pixelColor(x, y).alpha()
    )


def test_card_paints_from_roles_and_toggles_the_star(
    app: Any, monkeypatch: Any
) -> None:
    rows = [
        replace(asset(1), hda_version="1.0", is_favorite_hda=True),
        replace(asset(2, available=False), hda_version="2.0"),
    ]
    model = ListModel(items=rows)
    delegate = CardDelegate(
        None,
        data_role=ListModel.data_role,
        favorite_role=ListModel.favorite_role,
        version_role=ListModel.version_role,
    )
    rect = QtCore.QRect(0, 0, 120, 120)
    # Painting must not consult the filesystem (same rule as the models).
    import pathlib

    monkeypatch.setattr(
        pathlib.Path, "exists", lambda self: (_ for _ in ()).throw(OSError)
    )
    favorite = render(delegate, option_for(rect), model.index(0, 0))
    plain = render(delegate, option_for(rect), model.index(1, 0))
    hovered = render(delegate, option_for(rect, hover=True), model.index(1, 0))
    assert painted(favorite) > 0 and painted(plain) > 0
    # The star only appears on hover for a non-favorite; on a favorite always.
    star = star_rect(rect)
    assert any(
        favorite.pixelColor(x, y).alpha()
        for x in range(star.left(), star.right())
        for y in range(star.top(), star.bottom())
    )
    assert not any(
        plain.pixelColor(x, y).alpha()
        for x in range(star.left(), star.right())
        for y in range(star.top(), star.bottom())
    )
    assert painted(hovered) > painted(plain)
    assert delegate.sizeHint(option_for(rect), model.index(0, 0)) == model.index(
        0, 0
    ).data(QtCore.Qt.ItemDataRole.SizeHintRole)
    toggled: list[int] = []
    delegate.favoriteToggled.connect(lambda index: toggled.append(index.row()))

    def release(pos: QtCore.QPoint) -> QtGui.QMouseEvent:
        return QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QPointF(pos),
            QtCore.QPointF(pos),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )

    assert delegate.editorEvent(
        release(star.center()), model, option_for(rect), model.index(1, 0)
    )
    assert not delegate.editorEvent(
        release(QtCore.QPoint(10, 100)), model, option_for(rect), model.index(1, 0)
    )
    assert toggled == [1]


def test_row_delegate_paints_versions_activity_and_the_star(app: Any) -> None:
    from test_models import history

    from libs.asset_contracts import HistoryData
    from libs.model_columns import AssetColumn, HistoryColumn
    from model.ihda_history_model import HistoryModel
    from model.ihda_table_model import TableModel
    from widgets.item_delegates import RowDelegate, two_line_row_height

    table = TableModel(
        items=[
            replace(
                asset(1), hda_version="1.0", node_def_desc="Box", is_favorite_hda=True
            )
        ]
    )
    rows = RowDelegate(
        None,
        data_role=TableModel.data_role,
        name_column=AssetColumn.NAME,
        secondary_column=AssetColumn.DEFINITION,
        version_column=AssetColumn.VERSION,
        favorite_column=AssetColumn.FAVORITE,
        favorite_role=TableModel.favorite_role,
    )
    rect = QtCore.QRect(0, 0, 220, two_line_row_height(QtGui.QFont()))
    for column in (
        AssetColumn.NAME,
        AssetColumn.VERSION,
        AssetColumn.FAVORITE,
        AssetColumn.CREATED,
    ):
        assert painted(render(rows, option_for(rect), table.index(0, column))) >= 0
    toggled: list[tuple[int, int]] = []
    rows.favoriteToggled.connect(
        lambda index: toggled.append((index.row(), index.column()))
    )
    click = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease,
        QtCore.QPointF(rect.center()),
        QtCore.QPointF(rect.center()),
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rows.editorEvent(
        click, table, option_for(rect), table.index(0, AssetColumn.FAVORITE)
    )
    assert not rows.editorEvent(
        click, table, option_for(rect), table.index(0, AssetColumn.NAME)
    )
    assert toggled == [(0, int(AssetColumn.FAVORITE))]

    activity = HistoryData(
        kind="rename", hist_id=0, hda_id=1, org_hda_name="a", version=""
    )
    model = HistoryModel(items=[history(1), activity])
    hist_rows = RowDelegate(
        None,
        data_role=HistoryModel.data_role,
        name_column=HistoryColumn.NAME,
        secondary_column=HistoryColumn.DEFINITION,
        version_column=HistoryColumn.VERSION,
    )
    version_cell = render(
        hist_rows, option_for(rect), model.index(0, HistoryColumn.NAME)
    )
    activity_cell = render(
        hist_rows, option_for(rect), model.index(1, HistoryColumn.NAME)
    )
    assert painted(version_cell) > 0 and painted(activity_cell) > 0
    # Only the version row carries a thumbnail; the activity row starts with a dot.
    assert activity_cell.pixelColor(7, rect.center().y()).alpha() > 0
