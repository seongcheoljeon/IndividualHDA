"""One shape for the questions the panel has to ask.

"Yes" and "No" say nothing about what is about to happen, so the accepting
button carries the verb, the safe answer is the default for anything
destructive, and the explanation sits under the question instead of behind a
"Show Details" button. The standard Yes/No roles are kept underneath so the
buttons still land where each platform puts them.
"""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

Button = QtWidgets.QMessageBox.StandardButton


def confirm(
    parent: QtWidgets.QWidget | None,
    *,
    title: str,
    question: str,
    detail: str = "",
    accept: str = "OK",
    destructive: bool = False,
    font: QtGui.QFont | None = None,
) -> bool:
    """Ask, and answer True only if the person chose ``accept``."""
    box = QtWidgets.QMessageBox(parent)
    if font is not None:
        box.setFont(font)
    box.setWindowTitle(title)
    box.setIcon(
        QtWidgets.QMessageBox.Icon.Warning
        if destructive
        else QtWidgets.QMessageBox.Icon.Question
    )
    box.setText(question)
    if detail:
        box.setInformativeText(detail)
    box.setStandardButtons(Button.Yes | Button.No)
    yes, no = box.button(Button.Yes), box.button(Button.No)
    if yes is not None:
        yes.setText(accept)
    if no is not None:
        no.setText("Cancel")
    box.setDefaultButton(Button.No if destructive else Button.Yes)
    return box.exec() == Button.Yes
