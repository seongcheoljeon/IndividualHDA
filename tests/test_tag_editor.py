"""Chip tag editor: list in, list out; typing commits, selection does not edit."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtTest, QtWidgets


def editor(app: Any) -> Any:
    from widgets.tag_editor import TagEditor

    widget = TagEditor()
    widget.resize(300, 120)
    changes: list[int] = []
    widget.changed.connect(lambda: changes.append(1))
    widget.changes = changes  # type: ignore[attr-defined]
    return widget


def test_typing_commits_on_enter_comma_and_space(app: Any) -> None:
    widget = editor(app)
    line = widget.lineEdit()
    QtTest.QTest.keyClicks(line, "water")
    QtTest.QTest.keyClick(line, QtCore.Qt.Key.Key_Return)
    QtTest.QTest.keyClicks(line, "fire,")
    QtTest.QTest.keyClicks(line, "smoke ")
    assert widget.tags() == ["water", "fire", "smoke"]
    assert line.text() == "" and len(widget.changes) == 3


def test_duplicates_are_dropped_case_insensitively(app: Any) -> None:
    widget = editor(app)
    widget.setTags(["Water"])
    widget.lineEdit().setText("water, 한글")
    widget.commit()
    assert widget.tags() == ["Water", "한글"]


def test_set_tags_is_silent_and_set_plain_text_is_an_edit(app: Any) -> None:
    widget = editor(app)
    widget.setTags(["a", "b"])
    assert widget.tags() == ["a", "b"] and not widget.changes
    widget.setPlainText("#x #X #y")
    assert widget.tags() == ["x", "y"] and widget.changes == [1]
    assert widget.toPlainText() == "#x #y"


def test_backspace_on_empty_line_pops_the_last_chip(app: Any) -> None:
    widget = editor(app)
    widget.setTags(["a", "b"])
    QtTest.QTest.keyClick(widget.lineEdit(), QtCore.Qt.Key.Key_Backspace)
    assert widget.tags() == ["a"] and widget.changes == [1]
    widget.lineEdit().setText("typed")
    QtTest.QTest.keyClick(widget.lineEdit(), QtCore.Qt.Key.Key_Backspace)
    assert widget.tags() == ["a"]  # backspace edits the text, not the chips


def test_chip_buttons_search_remove_and_accept(app: Any) -> None:
    widget = editor(app)
    widget.setTags(["water"])
    widget.setSuggestions(["Water", "fire", "smoke"])
    assert widget.suggestions() == ["fire", "smoke"]  # existing tags never suggested
    clicked: list[str] = []
    widget.tagClicked.connect(clicked.append)
    chips = widget.findChildren(QtWidgets.QFrame, "chip__tag")
    suggested = widget.findChildren(QtWidgets.QFrame, "chip__suggested")
    assert len(chips) == 1 and len(suggested) == 2
    chips[0].name.click()
    assert clicked == ["water"]
    suggested[0].name.click()  # accept "fire"
    assert widget.tags() == ["water", "fire"] and widget.suggestions() == ["smoke"]
    widget.findChildren(QtWidgets.QFrame, "chip__suggested")[0].remove.click()
    assert widget.suggestions() == [] and widget.changes == [1]
    widget.findChildren(QtWidgets.QFrame, "chip__tag")[0].remove.click()
    assert widget.tags() == ["fire"] and widget.changes == [1, 1]


def test_vocabulary_feeds_the_completer_and_read_only_blocks_edits(app: Any) -> None:
    widget = editor(app)
    widget.setVocabulary(["smoke", "Fire", "water", "fire"])
    model = widget.lineEdit().completer().model()
    assert [model.index(i, 0).data() for i in range(model.rowCount())] == [
        "Fire",
        "fire",
        "smoke",
        "water",
    ]
    widget.setTags(["a"])
    widget.setReadOnly(True)
    widget.lineEdit().setText("b")
    widget.commit()
    QtTest.QTest.keyClick(widget.lineEdit(), QtCore.Qt.Key.Key_Backspace)
    assert widget.tags() == ["a"] and widget.isReadOnly()
    assert not widget.findChildren(QtWidgets.QFrame, "chip__tag")[0].remove.isVisibleTo(
        widget
    )
