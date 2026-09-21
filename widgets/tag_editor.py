"""Chip-style tag editor: committed tags as removable chips, a completer line below.

The widget owns a ``list[str]``; text only exists at its edges. ``setTags`` is the
programmatic path (selection changes) and is silent; ``setPlainText`` mirrors what
typing into the old QTextEdit did and therefore emits ``changed``.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore, QtGui, QtWidgets

from libs.tags import normalize_tags, tag_text

_COMMIT_KEYS = frozenset({",", " "})


class _ChipList(QtWidgets.QListWidget):
    """Wrapping chip row; Delete/Backspace ask the editor to drop the current chip."""

    removeRequested = QtCore.Signal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.setMovement(QtWidgets.QListView.Movement.Static)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setSpacing(2)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            row = self.currentRow()
            if row >= 0:
                self.removeRequested.emit(row)
                return
        super().keyPressEvent(event)


class _Chip(QtWidgets.QFrame):
    def __init__(
        self, tag: str, *, suggested: bool, removable: bool, parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self.setObjectName("chip__suggested" if suggested else "chip__tag")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 2, 0)
        layout.setSpacing(0)
        self.name = QtWidgets.QToolButton(self)
        self.name.setAutoRaise(True)
        self.name.setText(f"#{tag}")
        self.name.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        if suggested:
            font = self.name.font()
            font.setItalic(True)
            self.name.setFont(font)
            self.name.setToolTip("Suggested — click to add")
        else:
            self.name.setToolTip("Search this tag")
        layout.addWidget(self.name)
        self.remove = QtWidgets.QToolButton(self)
        self.remove.setAutoRaise(True)
        self.remove.setText("×")
        self.remove.setToolTip("Dismiss" if suggested else "Remove tag")
        self.remove.setVisible(removable)
        layout.addWidget(self.remove)


class TagEditor(QtWidgets.QWidget):
    changed = QtCore.Signal()
    tagClicked = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._tags: list[str] = []
        self._suggestions: list[str] = []
        self._read_only = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self._list = _ChipList(self)
        self._list.removeRequested.connect(self._remove_row)
        layout.addWidget(self._list, 1)
        self._line = QtWidgets.QLineEdit(self)
        self._line.setFrame(False)
        self._line.setClearButtonEnabled(True)
        self._model = QtCore.QStringListModel(self)
        completer = QtWidgets.QCompleter(self._model, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self._line.setCompleter(completer)
        self._line.returnPressed.connect(self.commit)
        self._line.textEdited.connect(self._text_edited)
        self._line.installEventFilter(self)
        layout.addWidget(self._line)
        self.setFocusProxy(self._line)

    # --- data -----------------------------------------------------------------

    def tags(self) -> list[str]:
        return list(self._tags)

    def setTags(self, tags: Sequence[str]) -> None:
        """Programmatic replacement; never reports as a user edit."""
        self._tags = normalize_tags(tags)
        self._suggestions = [tag for tag in self._suggestions if not self._has(tag)]
        self._rebuild()

    def setVocabulary(self, words: Sequence[str]) -> None:
        # Case-insensitive order, ties broken by spelling: set order is not stable.
        self._model.setStringList(sorted(set(words), key=lambda w: (w.casefold(), w)))

    def setSuggestions(self, words: Sequence[str]) -> None:
        self._suggestions = [tag for tag in normalize_tags(words) if not self._has(tag)]
        self._rebuild()

    def suggestions(self) -> list[str]:
        return list(self._suggestions)

    def setReadOnly(self, read_only: bool) -> None:
        self._read_only = read_only
        self._line.setReadOnly(read_only)
        self._rebuild()

    def isReadOnly(self) -> bool:
        return self._read_only

    def setPlaceholderText(self, text: str) -> None:
        self._line.setPlaceholderText(text)

    def setFont(self, font: QtGui.QFont) -> None:  # type: ignore[override]
        super().setFont(font)
        self._line.setFont(font)
        self._list.setFont(font)
        self._rebuild()

    def lineEdit(self) -> QtWidgets.QLineEdit:
        return self._line

    # QTextEdit-compatible surface for callers that still speak text.
    def toPlainText(self) -> str:
        return tag_text(self._tags)

    def setPlainText(self, text: str) -> None:
        """Behaves like typing: replaces the tags and reports a change."""
        self.setTags(normalize_tags(text))
        self.changed.emit()

    # --- editing --------------------------------------------------------------

    def commit(self) -> None:
        """Turn the pending line into chips."""
        if self._read_only:
            return
        added = [tag for tag in normalize_tags(self._line.text()) if not self._has(tag)]
        self._line.clear()
        if added:
            self._tags.extend(added)
            self._suggestions = [t for t in self._suggestions if not self._has(t)]
            self._rebuild()
            self.changed.emit()

    def _has(self, tag: str) -> bool:
        folded = tag.casefold()
        return any(existing.casefold() == folded for existing in self._tags)

    def _text_edited(self, text: str) -> None:
        if text and text[-1] in _COMMIT_KEYS:
            self.commit()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (
            watched is self._line
            and event.type() == QtCore.QEvent.Type.KeyPress
            and isinstance(event, QtGui.QKeyEvent)
            and event.key() == QtCore.Qt.Key.Key_Backspace
            and not self._line.text()
            and self._tags
            and not self._read_only
        ):
            self._remove_row(len(self._tags) - 1)
            return True
        return super().eventFilter(watched, event)

    def _remove_row(self, row: int) -> None:
        if self._read_only:
            return
        if 0 <= row < len(self._tags):
            del self._tags[row]
            self._rebuild()
            self.changed.emit()
        elif 0 <= (index := row - len(self._tags)) < len(self._suggestions):
            del self._suggestions[index]
            self._rebuild()

    def _accept(self, tag: str) -> None:
        if self._read_only or self._has(tag):
            return
        self._suggestions = [
            t for t in self._suggestions if t.casefold() != tag.casefold()
        ]
        self._tags.append(tag)
        self._rebuild()
        self.changed.emit()

    # --- rendering ------------------------------------------------------------

    def _rebuild(self) -> None:
        # clear() only schedules the item widgets for deletion; detach them now so
        # the chip set is exact right after the call (findChildren, sizes, tests).
        for row in range(self._list.count()):
            chip = self._list.itemWidget(self._list.item(row))
            if chip is not None:
                chip.setParent(None)
                chip.deleteLater()
        self._list.clear()
        for row, tag in enumerate(self._tags):
            chip = _Chip(
                tag, suggested=False, removable=not self._read_only, parent=self._list
            )
            chip.name.clicked.connect(lambda _=False, t=tag: self.tagClicked.emit(t))
            chip.remove.clicked.connect(lambda _=False, r=row: self._remove_row(r))
            self._add_chip(chip)
        for offset, tag in enumerate(self._suggestions):
            chip = _Chip(
                tag, suggested=True, removable=not self._read_only, parent=self._list
            )
            chip.name.clicked.connect(lambda _=False, t=tag: self._accept(t))
            chip.remove.clicked.connect(
                lambda _=False, r=len(self._tags) + offset: self._remove_row(r)
            )
            self._add_chip(chip)

    def _add_chip(self, chip: _Chip) -> None:
        item = QtWidgets.QListWidgetItem(self._list)
        item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        )
        item.setSizeHint(chip.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, chip)
