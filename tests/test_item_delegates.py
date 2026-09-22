"""Delegates draw from roles only and route the star click to one signal."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets
from test_models import asset

from model.ihda_list_model import ListModel
from widgets.item_delegates import CardDelegate, star_rect
from widgets.ui_tokens import FAVORITE_COLOR


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
    # A favorite's star is filled with the accent colour, not the theme highlight.
    assert favorite.pixelColor(star.center()).name().lower() == FAVORITE_COLOR.lower()
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


def test_category_counts_come_from_the_store_and_draw_as_a_badge(app: Any) -> None:
    from libs.asset_store import AssetStore
    from model.ihda_category_model import CategoryModel
    from widgets.item_delegates import CountBadgeDelegate

    store = AssetStore()
    store.reset(
        [
            replace(asset(1), hda_cate="sop"),
            replace(asset(2), hda_cate="sop"),
            replace(asset(3), hda_cate="obj"),
        ]
    )
    assert dict(store.category_counts) == {"sop": 2, "obj": 1}
    store.remove(0)
    assert dict(store.category_counts) == {"sop": 1, "obj": 1}  # invalidated on change
    model = CategoryModel(
        data={"sop": None, "obj": None, "vop": None},
        pixmap_cate_data={},
        font_size=10,
        font_style="Sans",
        icon_size=16,
        padding=2,
        counts=lambda: store.category_counts,
    )
    root = model.index(0, 0)
    counts = {
        model.index(row, 0, root).data(CategoryModel.category_role): model.index(
            row, 0, root
        ).data(CategoryModel.count_role)
        for row in range(model.rowCount(root))
    }
    assert counts == {"sop": 1, "obj": 1, "vop": 0}
    assert root.data(CategoryModel.count_role) is None  # the root is not a category
    delegate = CountBadgeDelegate(None, count_role=CategoryModel.count_role)
    rect = QtCore.QRect(0, 0, 160, 22)
    sop = next(
        model.index(row, 0, root)
        for row in range(model.rowCount(root))
        if model.index(row, 0, root).data(CategoryModel.category_role) == "sop"
    )
    vop = next(
        model.index(row, 0, root)
        for row in range(model.rowCount(root))
        if model.index(row, 0, root).data(CategoryModel.category_role) == "vop"
    )
    assert painted(render(delegate, option_for(rect), sop)) > 0
    assert (
        delegate.sizeHint(option_for(rect), sop).width()
        > delegate.sizeHint(option_for(rect), vop).width()
    )


def test_record_rows_draw_their_icon_unselected_and_badge_only_the_name(
    app: Any,
) -> None:
    from pathlib import Path

    from libs.scene_contracts import SceneRecord
    from model.ihda_record_model import RecordModel
    from widgets.item_delegates import CountBadgeDelegate

    red = QtGui.QPixmap(20, 20)
    red.fill(QtGui.QColor("#ff0000"))
    records = [
        SceneRecord(
            record_id=n,
            hda_id=n,
            hip_filename="shot.hip",
            hip_dirpath=Path("/hips"),
            parent_node_path="/obj/geo1",
            node_name=f"fx{n}",
            node_ver="1.0",
        )
        for n in (1, 2)
    ]
    model = RecordModel(data=records, pixmap_ihda_data={1: red, 2: red}, icon_size=20)
    delegate = CountBadgeDelegate(None, count_role=RecordModel.count_role)
    root = model.index(0, 0)
    folder = model.index(0, 0, root)
    network = model.index(0, 0, model.index(0, 0, folder))
    leaf = model.index(0, 0, network)
    rect = QtCore.QRect(0, 0, 200, 24)

    def red_pixels(image: QtGui.QImage) -> int:
        return sum(
            1
            for x in range(image.width())
            for y in range(image.height())
            if image.pixelColor(x, y).red() > 200
            and image.pixelColor(x, y).green() < 60
            and image.pixelColor(x, y).blue() < 60
        )

    # The icon is painted by the delegate itself, selected or not.
    assert red_pixels(render(delegate, option_for(rect), leaf)) >= 20 * 20 * 0.9
    assert red_pixels(render(delegate, option_for(rect, selected=True), leaf)) >= 360
    # The count badge belongs to the name column only.
    name_hint = delegate.sizeHint(option_for(rect), folder)
    other_hint = delegate.sizeHint(option_for(rect), folder.siblingAtColumn(1))
    assert name_hint.width() > other_hint.width()


def test_version_pills_are_accented_and_tables_drop_grid_and_row_numbers(
    app: Any,
) -> None:
    from libs.model_columns import AssetColumn
    from model.ihda_table_model import TableModel
    from view.ihda_history_view import HistoryView
    from view.ihda_table_view import TableView
    from widgets.item_delegates import RowDelegate
    from widgets.ui_tokens import VERSION_COLOR

    table = TableModel(items=[replace(asset(1), hda_version="1.0")])
    rows = RowDelegate(
        None,
        data_role=TableModel.data_role,
        name_column=AssetColumn.NAME,
        secondary_column=AssetColumn.DEFINITION,
        version_column=AssetColumn.VERSION,
    )
    rect = QtCore.QRect(0, 0, 76, 28)
    cell = render(rows, option_for(rect), table.index(0, AssetColumn.VERSION))
    colours = {
        cell.pixelColor(x, y).name().lower()
        for x in range(cell.width())
        for y in range(cell.height())
    }
    assert VERSION_COLOR.lower() in colours and "#ffffff" in colours
    for view in (TableView(), HistoryView()):
        assert view.verticalHeader().isHidden()
        assert not view.showGrid()
        assert view.alternatingRowColors()
        view.deleteLater()
