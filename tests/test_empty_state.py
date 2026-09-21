"""The empty state follows its model and resizes with the viewport."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from widgets.empty_state import attach_empty_state


def test_empty_state_follows_the_model_and_the_viewport(app: Any) -> None:
    model = QtGui.QStandardItemModel()
    view = QtWidgets.QListView()
    view.setModel(model)
    view.resize(300, 200)
    state = attach_empty_state(view)
    clicked: list[str] = []
    state.set_content(
        "Nothing here", "Add something.", "Add", lambda: clicked.append("add")
    )
    assert state.isVisibleTo(view) and state.hint.text() == "Add something."
    state.action.click()
    assert clicked == ["add"]
    model.appendRow(QtGui.QStandardItem("row"))
    assert not state.isVisibleTo(view)
    model.removeRow(0)
    assert state.isVisibleTo(view)
    view.resize(500, 400)
    app.sendPostedEvents()
    assert state.size() == view.viewport().size()
    state.set_content("Title only")
    assert not state.hint.isVisibleTo(view) and not state.action.isVisibleTo(view)
    # A re-set content replaces the action instead of stacking callbacks.
    state.set_content("Again", action="Go", on_action=lambda: clicked.append("go"))
    state.action.click()
    assert clicked == ["add", "go"]
    view.close()
    view.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
