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


def test_houdini_node_text_drops_are_accepted_while_moving_and_delivered(
    app: Any,
) -> None:
    """Registering nodes is a drop of their paths as text from the network editor."""
    from view.ihda_list_view import ListView

    view = ListView()
    view.setModel(Model())
    view.resize(300, 300)
    view.show()
    app.processEvents()
    dropped: list[Any] = []
    view.signal.signal_object.connect(dropped.append)
    mime = QtCore.QMimeData()
    mime.setText("/obj/geo1 /obj/geo2")
    pos = QtCore.QPointF(50, 50)
    actions = QtCore.Qt.DropAction.CopyAction | QtCore.Qt.DropAction.MoveAction
    buttons, mods = (
        QtCore.Qt.MouseButton.MiddleButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    viewport = view.viewport()
    enter = QtGui.QDragEnterEvent(pos.toPoint(), actions, mime, buttons, mods)
    QtWidgets.QApplication.sendEvent(viewport, enter)
    assert enter.isAccepted()
    move = QtGui.QDragMoveEvent(pos.toPoint(), actions, mime, buttons, mods)
    QtWidgets.QApplication.sendEvent(viewport, move)
    assert move.isAccepted()  # the base class would have asked the model and refused
    drop = QtGui.QDropEvent(pos, actions, mime, buttons, mods)
    QtWidgets.QApplication.sendEvent(viewport, drop)
    assert dropped == [["/obj/geo1", "/obj/geo2"]]
    view.close()


def test_hovering_does_not_change_the_selection(app: Any) -> None:
    """Selection follows clicks, keys and drags; moving the mouse only styles."""
    from view.ihda_list_view import ListView

    model = Model()
    for name in ("a", "b", "c"):
        model.appendRow(QtGui.QStandardItem(name))
    view = ListView()
    view.setModel(model)
    view.resize(300, 300)
    view.show()
    app.processEvents()
    view.setCurrentIndex(model.index(0, 0))
    over_b = view.visualRect(model.index(1, 0)).center()
    none = QtCore.Qt.MouseButton.NoButton
    QtWidgets.QApplication.sendEvent(
        view.viewport(), mouse(QtCore.QEvent.Type.MouseMove, over_b, none, none)
    )
    view.entered.emit(model.index(1, 0))  # what mouse tracking reports
    assert view.currentIndex().row() == 0
    left = QtCore.Qt.MouseButton.LeftButton
    QtWidgets.QApplication.sendEvent(
        view.viewport(), mouse(QtCore.QEvent.Type.MouseButtonPress, over_b, left, left)
    )
    assert view.currentIndex().row() == 1
    view.close()


def test_record_view_drags_only_concrete_records(app: Any, monkeypatch: Any) -> None:
    from pathlib import Path

    from libs.scene_contracts import SceneRecord
    from model.ihda_record_model import RecordModel
    from view.ihda_record_view import RecordView

    monkeypatch.setattr(
        QtGui.QDrag, "exec", lambda self, *a, **k: QtCore.Qt.DropAction.IgnoreAction
    )
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
    model = RecordModel(data=records)
    view = RecordView()
    view.setModel(model)
    view.resize(400, 300)
    view.expandAll()
    view.show()
    app.processEvents()
    # root > folder > hip > network > records
    root = model.index(0, 0)
    folder = model.index(0, 0, root)
    hip = model.index(0, 0, folder)
    network = model.index(0, 0, hip)
    assert folder.data(RecordModel.count_role) == 2  # badge counts the records
    assert hip.data(RecordModel.count_role) == 2
    assert model.index(0, 0, network).data(RecordModel.count_role) is None
    assert "/hips" in folder.data(QtCore.Qt.ItemDataRole.ToolTipRole)
    assert "/obj/geo1" in model.index(0, 0, network).data(
        QtCore.Qt.ItemDataRole.ToolTipRole
    )
    drops: list[Any] = []
    view.signal.mouse_signal_object.connect(drops.append)
    view.selectionModel().select(
        hip,
        QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
        | QtCore.QItemSelectionModel.SelectionFlag.Rows,
    )
    assert view.drag_indexes() == []  # a HIP row is not draggable
    for row in range(2):
        view.selectionModel().select(
            model.index(row, 0, network),
            QtCore.QItemSelectionModel.SelectionFlag.Select
            | QtCore.QItemSelectionModel.SelectionFlag.Rows,
        )
    view.selectionModel().select(
        hip,
        QtCore.QItemSelectionModel.SelectionFlag.Deselect
        | QtCore.QItemSelectionModel.SelectionFlag.Rows,
    )
    assert len(view.drag_indexes()) == 2
    start = view.visualRect(model.index(0, 0, network)).center()
    left = QtCore.Qt.MouseButton.LeftButton
    viewport = view.viewport()
    QtWidgets.QApplication.sendEvent(
        viewport, mouse(QtCore.QEvent.Type.MouseButtonPress, start, left, left)
    )
    for row in range(2):  # the press re-selected one row; select both again
        view.selectionModel().select(
            model.index(row, 0, network),
            QtCore.QItemSelectionModel.SelectionFlag.Select
            | QtCore.QItemSelectionModel.SelectionFlag.Rows,
        )
    far = start + QtCore.QPoint(QtWidgets.QApplication.startDragDistance() + 5, 0)
    QtWidgets.QApplication.sendEvent(
        viewport, mouse(QtCore.QEvent.Type.MouseMove, far, left, left)
    )
    assert len(drops) == 1 and len(drops[0][1]) == 2  # one payload per record
    view.close()
