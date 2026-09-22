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
