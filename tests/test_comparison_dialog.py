"""The conflict dialog routes each button to one callback and closes."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore


def test_buttons_call_back_and_the_tag_line_lists_the_difference(app: Any) -> None:
    from widgets.team_library.comparison_dialog import ComparisonDialog

    calls: list[str] = []
    dialog = ComparisonDialog(
        None,
        "Water",
        ("mine\nshared", ["a", "Mine"]),
        ("theirs\nshared", ["A", "theirs"]),
        on_keep_mine=lambda: calls.append("keep"),
        on_take_theirs=lambda: calls.append("take"),
    )
    assert dialog.windowTitle().startswith("Review changes")
    assert dialog.label__tags.text() == "Tags: +Mine −theirs"
    assert dialog.textEdit__left.toPlainText().splitlines() == ["mine", "shared"]
    dialog.pushButton__take_theirs.click()
    assert calls == ["take"] and dialog.result() == 1
    second = ComparisonDialog(
        None,
        "Water",
        ("same", []),
        ("same", []),
        on_keep_mine=lambda: calls.append("keep"),
        on_take_theirs=lambda: calls.append("take"),
    )
    assert second.label__tags.text() == "Tags: no difference"
    assert "background-color:" not in second.textEdit__left.toHtml()
    second.pushButton__keep_mine.click()
    assert calls == ["take", "keep"]
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
