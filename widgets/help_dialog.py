"""Help: what the panel does and which key or gesture does it.

The old Help was a message box with two video links. This lists the gestures
and shortcuts the panel actually binds (see widgets/panel/shortcuts.py) next to
a short tour of the tabs, and links to the documentation for the rest.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from widgets.about_dialog import ISSUES_URL, REPOSITORY_URL

DOCS_URL = REPOSITORY_URL + "#readme"
TEAM_DOCS_URL = REPOSITORY_URL + "/blob/master/docs/TEAM_LIBRARY.md"
TOOLS_DOCS_URL = REPOSITORY_URL + "/blob/master/docs/LIBRARY_TOOLS.md"

# The same key objects widgets/panel/shortcuts.py binds, so the dialog shows
# what each platform really uses and a test keeps the two from drifting apart.
Key = QtGui.QKeySequence.StandardKey | QtCore.Qt.Key
SHORTCUTS: tuple[tuple[Key, str], ...] = (
    (QtGui.QKeySequence.StandardKey.Save, "Save the note and tags of the asset"),
    (QtGui.QKeySequence.StandardKey.Find, "Jump to the search box"),
    (QtCore.Qt.Key.Key_Escape, "Clear the search box"),
    (QtCore.Qt.Key.Key_Return, "Import the selected asset into the current network"),
    (QtCore.Qt.Key.Key_Delete, "Move the selected assets to the Trash (with Undo)"),
    (QtGui.QKeySequence.StandardKey.Refresh, "Reload the library from disk"),
)


def shortcut_rows() -> tuple[tuple[str, str], ...]:
    """The key names this platform shows, next to what the key does."""
    return tuple(
        (
            QtGui.QKeySequence(key).toString(
                QtGui.QKeySequence.SequenceFormat.NativeText
            ),
            description,
        )
        for key, description in SHORTCUTS
    )


GESTURES: tuple[tuple[str, str], ...] = (
    ("Middle-drag a node", "Drop a Houdini node on the panel to register it"),
    ("Drag an asset out", "Drop it in a Network Editor to import it"),
    ("Double-click", "Play the asset's preview video"),
    ("Click the star", "Add or remove a favorite"),
    ("Right-click", "Versions, thumbnails, videos, rename, delete"),
)

TABS: tuple[tuple[str, str], ...] = (
    ("Assets", "Browse by category, search by name, tag or node type, edit notes."),
    ("Versions", "Every registered version with its comment; restore or compare."),
    ("Records", "Where assets were imported, per HIP file."),
    ("Find", "iHDA nodes inside the scene that is open now."),
    ("Web", "Houdini help and the web, inside the panel."),
)

FIRST_RUN = (
    "Choose the folder that holds <b>ihda.db</b> in Preferences, or an empty "
    "folder for a new library, then reopen the panel. Point Preferences at "
    "FFmpeg for thumbnails and preview videos."
)


def _section(title: str, rows: tuple[tuple[str, str], ...]) -> QtWidgets.QGroupBox:
    box = QtWidgets.QGroupBox(title)
    form = QtWidgets.QFormLayout(box)
    form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(4)
    for name, description in rows:
        key = QtWidgets.QLabel(name, box)
        key_font = QtGui.QFont(key.font())
        key_font.setBold(True)
        key.setFont(key_font)
        text = QtWidgets.QLabel(description, box)
        text.setWordWrap(True)
        form.addRow(key, text)
    return box


class HelpDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        *,
        open_url: Callable[[str], object],
    ) -> None:
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setObjectName("Dialog__help")
        self.setWindowTitle("Individual HDA Help")
        self.resize(560, 540)
        self._open_url = open_url
        layout = QtWidgets.QVBoxLayout(self)

        self.label__intro = QtWidgets.QLabel(FIRST_RUN, self)
        self.label__intro.setWordWrap(True)
        layout.addWidget(self.label__intro)

        self.scrollArea__help = QtWidgets.QScrollArea(self)
        self.scrollArea__help.setObjectName("scrollArea__help")
        self.scrollArea__help.setWidgetResizable(True)
        self.scrollArea__help.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        content = QtWidgets.QWidget(self.scrollArea__help)
        sections = QtWidgets.QVBoxLayout(content)
        sections.setContentsMargins(0, 0, 0, 0)
        for title, rows in (
            ("Gestures", GESTURES),
            ("Keyboard", shortcut_rows()),
            ("Tabs", TABS),
        ):
            sections.addWidget(_section(title, rows))
        sections.addStretch(1)
        self.scrollArea__help.setWidget(content)
        layout.addWidget(self.scrollArea__help, 1)

        self.label__keys_note = QtWidgets.QLabel(
            "Keys work while the focus is in the panel, so Houdini keeps its own.",
            self,
        )
        self.label__keys_note.setWordWrap(True)
        self.label__keys_note.setStyleSheet("color: palette(mid);")
        layout.addWidget(self.label__keys_note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close, self
        )
        for attr, text, url, tip in (
            ("pushButton__docs", "Documentation", DOCS_URL, "README on GitHub"),
            ("pushButton__team", "Team library", TEAM_DOCS_URL, "Set up a team server"),
            (
                "pushButton__tools",
                "Library tools",
                TOOLS_DOCS_URL,
                "Health, backups, repair",
            ),
            ("pushButton__ask", "Ask a question", ISSUES_URL, "Open the issue tracker"),
        ):
            button = QtWidgets.QPushButton(text, self)
            button.setObjectName(attr)
            button.setToolTip(tip)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, u=url: self._open_url(u))
            setattr(self, attr, button)
            buttons.addButton(button, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
