"""Conflict review: my draft against the latest saved note and tags, as a diff."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from html import escape

from PySide6 import QtCore, QtWidgets

from libs.text_diff import line_ops, render_html, tag_diff

Draft = tuple[str, Sequence[str]]  # note, tags


class ComparisonDialog(QtWidgets.QDialog):
    textEdit__left: QtWidgets.QTextEdit
    textEdit__right: QtWidgets.QTextEdit

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        asset_name: str,
        mine: Draft,
        theirs: Draft,
        *,
        on_keep_mine: Callable[[], None],
        on_take_theirs: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review changes — " + asset_name)
        self.resize(760, 420)
        self._on_keep_mine, self._on_take_theirs = on_keep_mine, on_take_theirs
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                "Someone saved this asset after you started editing. Changed lines"
                " are highlighted; nothing is written until you choose."
            )
        )
        columns = QtWidgets.QHBoxLayout()
        ops = line_ops(mine[0], theirs[0])
        palette = self.palette()
        highlight = palette.highlight().color()
        removed = (
            f"rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 60)"
        )
        added = "rgba(80, 170, 90, 70)"
        for title, side, colour in (
            ("Your edits", "left", removed),
            ("Latest saved", "right", added),
        ):
            group = QtWidgets.QGroupBox(title)
            group_layout = QtWidgets.QVBoxLayout(group)
            editor = QtWidgets.QTextEdit(group)
            editor.setObjectName(f"textEdit__{side}")
            editor.setReadOnly(True)
            editor.setHtml(render_html(ops, side, changed=colour))
            setattr(self, f"textEdit__{side}", editor)
            group_layout.addWidget(editor)
            columns.addWidget(group)
        layout.addLayout(columns)
        only_mine, only_theirs, _ = tag_diff(mine[1], theirs[1])
        parts = [f"+{escape(tag)}" for tag in only_mine] + [
            f"−{escape(tag)}" for tag in only_theirs
        ]
        self.label__tags = QtWidgets.QLabel(
            "Tags: " + (" ".join(parts) if parts else "no difference"), self
        )
        self.label__tags.setObjectName("label__tags")
        self.label__tags.setToolTip("+ only in your draft · − only in the saved asset")
        layout.addWidget(self.label__tags)
        buttons = QtWidgets.QDialogButtonBox(self)
        self.pushButton__keep_mine = buttons.addButton(
            "Keep mine (save over)", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        self.pushButton__take_theirs = buttons.addButton(
            "Take theirs", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        buttons.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        self.pushButton__keep_mine.clicked.connect(self._keep_mine)
        self.pushButton__take_theirs.clicked.connect(self._take_theirs)
        layout.addWidget(buttons)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

    def _keep_mine(self) -> None:
        self.accept()
        self._on_keep_mine()

    def _take_theirs(self) -> None:
        self.accept()
        self._on_take_theirs()
