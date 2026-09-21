"""Asset views start a drag with the left or middle button, once past the threshold."""

from __future__ import annotations

from typing import Any

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from libs import keys


class Model(QtGui.QStandardItemModel):
    def mimeData(self, indexes: Any) -> QtCore.QMimeData:
        mime = QtCore.QMimeData()
        mime.setData(
            keys.Type.mime_type, QtCore.QByteArray(b"row%d" % indexes[0].row())
        )
        return mime


def mouse(
    kind: QtCore.QEvent.Type, pos: QtCore.QPoint, button: Any, buttons: Any
) -> Any:
    return QtGui.QMouseEvent(
        kind,
        QtCore.QPointF(pos),
        QtCore.QPointF(pos),
        button,
        buttons,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )


@pytest.mark.parametrize(
    "button",
    [QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.MiddleButton],
)
def test_drag_starts_past_the_threshold_and_reports_the_drop(
    app: Any, monkeypatch: pytest.MonkeyPatch, button: Any
) -> None:
    from view.ihda_list_view import ListView

    monkeypatch.setattr(
        QtGui.QDrag, "exec", lambda self, *a, **k: QtCore.Qt.DropAction.IgnoreAction
    )
    model = Model()
    for name in ("a", "b"):
        model.appendRow(QtGui.QStandardItem(name))
    view = ListView()
    view.setModel(model)
    view.resize(300, 300)
    view.show()
    app.processEvents()
    drops: list[Any] = []
    view.signal.mouse_signal_object.connect(drops.append)
    index = model.index(1, 0)
    start = view.visualRect(index).center()
    viewport = view.viewport()
    QtWidgets.QApplication.sendEvent(
        viewport, mouse(QtCore.QEvent.Type.MouseButtonPress, start, button, button)
    )
    assert view.currentIndex() == index or button == QtCore.Qt.MouseButton.MiddleButton
    view.setCurrentIndex(index)
    near = start + QtCore.QPoint(1, 1)
    QtWidgets.QApplication.sendEvent(
        viewport, mouse(QtCore.QEvent.Type.MouseMove, near, button, button)
    )
    assert drops == []  # below the start-drag distance nothing happens
    far = start + QtCore.QPoint(QtWidgets.QApplication.startDragDistance() + 5, 0)
    QtWidgets.QApplication.sendEvent(
        viewport, mouse(QtCore.QEvent.Type.MouseMove, far, button, button)
    )
    assert drops == [[QtCore.Qt.DropAction.IgnoreAction, [b"row1"]]]
    QtWidgets.QApplication.sendEvent(
        viewport, mouse(QtCore.QEvent.Type.MouseMove, far, button, button)
    )
    assert len(drops) == 1  # one drag per press
    view.close()


def test_press_on_empty_space_does_not_drag(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from view.ihda_table_view import TableView

    monkeypatch.setattr(
        QtGui.QDrag, "exec", lambda self, *a, **k: QtCore.Qt.DropAction.IgnoreAction
    )
    model = Model()
    model.appendRow([QtGui.QStandardItem("a"), QtGui.QStandardItem("1.0")])
    view = TableView()
    view.setModel(model)
    view.resize(300, 300)
    view.show()
    app.processEvents()
    drops: list[Any] = []
    view.signal.mouse_signal_object.connect(drops.append)
    view.selectRow(0)
    empty = QtCore.QPoint(150, 280)
    left = QtCore.Qt.MouseButton.LeftButton
    viewport = view.viewport()
    QtWidgets.QApplication.sendEvent(
        viewport, mouse(QtCore.QEvent.Type.MouseButtonPress, empty, left, left)
    )
    QtWidgets.QApplication.sendEvent(
        viewport,
        mouse(QtCore.QEvent.Type.MouseMove, empty + QtCore.QPoint(60, 0), left, left),
    )
    assert drops == []
    assert [i.row() for i in view.drag_indexes()] == [0]  # one payload per row
    view.close()
