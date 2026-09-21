"""Toasts: non-modal, at most three, an optional action, gone on their own."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtTest, QtWidgets

from widgets import toast as toast_module
from widgets.toast import ToastStack


def wait_until(app: Any, condition: Any, tries: int = 300) -> None:
    for _ in range(tries):
        app.processEvents()
        if condition():
            return
        QtTest.QTest.qWait(10)
    raise AssertionError("Condition not met in time")


def test_stack_keeps_three_and_runs_the_action(app: Any) -> None:
    parent = QtWidgets.QWidget()
    parent.resize(800, 600)
    stack = ToastStack(parent)
    assert not stack.isVisibleTo(parent)
    for n in range(4):
        stack.push(f"message {n}")
    assert [t.message.text() for t in stack.toasts()] == [
        "message 1",
        "message 2",
        "message 3",
    ]
    assert stack.isVisibleTo(parent) and stack.width() <= 480
    done: list[str] = []
    toast = stack.push(
        "moved to Trash", action="Undo", on_action=lambda: done.append("undo")
    )
    assert toast.action is not None and toast.action.text() == "Undo"
    toast.action.click()
    assert done == ["undo"] and toast not in stack.toasts()
    assert len(stack.toasts()) == 2  # the fourth push had dropped "message 1"
    stack.toasts()[0].close_button.click()
    assert len(stack.toasts()) == 1
    stack.reposition(QtCore.QSize(300, 200))
    assert stack.width() == 300 - 32 and stack.geometry().bottom() < 200


def test_toast_hides_itself_after_the_timeout(app: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(toast_module, "TIMEOUT_MS", 30)
    parent = QtWidgets.QWidget()
    parent.resize(400, 300)
    stack = ToastStack(parent)
    stack.push("gone soon")
    wait_until(app, lambda: not stack.toasts())
    assert not stack.isVisibleTo(parent)
    parent.deleteLater()
