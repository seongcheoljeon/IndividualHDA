"""About: what this is, which version runs where, and where to go from here.

Replaces the QMessageBox whose detail pane opened on a green gradient: a header
with the logo, a small facts table you can copy for a bug report, link buttons
and the licence text in a collapsible pane.
"""

from __future__ import annotations

import platform
from collections.abc import Callable, Sequence
from pathlib import Path
from urllib.parse import urlencode

from PySide6 import QtCore, QtGui, QtWidgets

from libs import platform_info
from libs.app_metadata import (
    DISPLAY_VERSION,
    MINIMUM_HOUDINI_MAJOR,
    SPONSORS_URL,
    SUPPORT_URL,
)
from libs.ui_icons import Icon
from widgets.layout_helpers import copy_to_clipboard

REPOSITORY_URL = "https://github.com/seongcheoljeon/IndividualHDA"
ISSUES_URL = REPOSITORY_URL + "/issues"


def new_issue_url(kind: str, facts: str = "") -> str:
    """A prefilled issue: the reporter writes what happened, not their setup."""
    heading = "Bug report" if kind == "bug" else "Feedback"
    if not facts:
        return ISSUES_URL + "/new"
    body = f"## What happened\n\n\n## Environment\n\n```\n{facts}\n```\n"
    query = urlencode({"title": f"[{heading}] ", "body": body})
    return f"{ISSUES_URL}/new?{query}"


YOUTUBE_URL = "https://youtube.com/@seongcheoljeon5785"
LICENSE_PANE_WIDTH = 640  # the licence files are hard-wrapped at 80 columns
LICENSE_PATH = Path(__file__).resolve().parent.parent / "LICENSE"
THIRD_PARTY_PATH = LICENSE_PATH.with_name("THIRD_PARTY_LICENSES.txt")


def environment_facts(
    houdini_version: str | None, config_dir: Path | None
) -> list[tuple[str, str]]:
    """Name/value pairs shown in the dialog and copied for bug reports."""
    facts = [
        ("Version", DISPLAY_VERSION),
        ("Houdini", houdini_version or f"not running (needs {MINIMUM_HOUDINI_MAJOR}+)"),
        ("Qt", QtCore.qVersion()),
        ("Python", platform.python_version()),
        ("System", f"{platform_info.platform_system().title()} {platform.release()}"),
    ]
    if config_dir is not None:
        facts.append(("Settings", str(config_dir)))
    return facts


def facts_text(facts: Sequence[tuple[str, str]]) -> str:
    return "\n".join(f"{name}: {value}" for name, value in facts)


def license_text() -> str:
    parts = []
    for path in (LICENSE_PATH, THIRD_PARTY_PATH):
        try:
            parts.append(path.read_text(encoding="utf-8").strip())
        except OSError:
            continue
    return "\n\n\n".join(parts) or "MIT License — see LICENSE in the repository."


class AboutDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        *,
        houdini_version: str | None,
        config_dir: Path | None,
        open_url: Callable[[str], object],
        open_folder: Callable[[Path], object],
    ) -> None:
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setObjectName("Dialog__about")
        self.setWindowTitle("About Individual HDA")
        self.setMinimumWidth(460)
        self._open_url = open_url
        self._facts = environment_facts(houdini_version, config_dir)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(14)
        self.label__logo = QtWidgets.QLabel(self)
        self.label__logo.setPixmap(QtGui.QPixmap(Icon.VIEWPORT_LOGO_TRANS))
        self.label__logo.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        header.addWidget(self.label__logo, 0)
        titles = QtWidgets.QVBoxLayout()
        titles.setSpacing(2)
        self.label__title = QtWidgets.QLabel("Individual HDA", self)
        self.label__title.setObjectName("label__title")
        title_font = QtGui.QFont(self.font())
        title_font.setPointSize(title_font.pointSize() + 6)
        title_font.setBold(True)
        self.label__title.setFont(title_font)
        titles.addWidget(self.label__title)
        self.label__tagline = QtWidgets.QLabel(
            "A personal and team library for Houdini digital assets.", self
        )
        self.label__tagline.setWordWrap(True)
        titles.addWidget(self.label__tagline)
        self.label__version = QtWidgets.QLabel(
            f"{DISPLAY_VERSION} · MIT License · © 2020 Seongcheol Jeon", self
        )
        self.label__version.setObjectName("label__version")
        self.label__version.setStyleSheet("color: palette(mid);")
        titles.addWidget(self.label__version)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        self.groupBox__environment = QtWidgets.QGroupBox("Environment", self)
        facts = QtWidgets.QFormLayout(self.groupBox__environment)
        facts.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        facts.setHorizontalSpacing(16)
        for name, value in self._facts:
            label = QtWidgets.QLabel(value, self.groupBox__environment)
            label.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            if name == "Settings" and config_dir is not None:
                label.setObjectName("label__settings_folder")
                label.setText(f'<a href="folder">{value}</a>')
                label.setTextInteractionFlags(
                    QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
                )
                label.setToolTip("Open the settings folder")
                label.linkActivated.connect(
                    lambda _=None, folder=config_dir: open_folder(folder)
                )
            facts.addRow(f"{name}:", label)
        layout.addWidget(self.groupBox__environment)

        links = QtWidgets.QHBoxLayout()
        links.setSpacing(8)
        self.pushButton__copy_info = QtWidgets.QPushButton("Copy info", self)
        self.pushButton__copy_info.setObjectName("pushButton__copy_info")
        self.pushButton__copy_info.setToolTip(
            "Copy the environment facts for a bug report"
        )
        self.pushButton__copy_info.clicked.connect(self._copy_info)
        links.addWidget(self.pushButton__copy_info)
        links.addStretch(1)
        for attr, text, url, tip in (
            ("pushButton__repository", "GitHub", REPOSITORY_URL, "Source and releases"),
            (
                "pushButton__issues",
                "Report an issue",
                ISSUES_URL,
                "Open the issue tracker",
            ),
            ("pushButton__youtube", "YouTube", YOUTUBE_URL, "Tutorial videos"),
        ):
            button = QtWidgets.QPushButton(text, self)
            button.setObjectName(attr)
            button.setToolTip(tip)
            button.setFlat(True)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, u=url: self._open_url(u))
            setattr(self, attr, button)
            links.addWidget(button)
        layout.addLayout(links)

        support = QtWidgets.QHBoxLayout()
        support.setSpacing(8)
        self.label__support = QtWidgets.QLabel("If this app saves you time:", self)
        support.addWidget(self.label__support)
        support.addStretch(1)
        self.pushButton__book = QtWidgets.QPushButton("Buy me a book", self)
        self.pushButton__book.setObjectName("pushButton__book")
        self.pushButton__book.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.pushButton__book.setStyleSheet(
            "QPushButton {background: #ff5f5f; color: white; border: none;"
            " border-radius: 6px; padding: 6px 12px; font-weight: bold;}"
            " QPushButton:hover {background: #ff7a7a;}"
        )
        self.pushButton__book.clicked.connect(lambda: self._open_url(SUPPORT_URL))
        support.addWidget(self.pushButton__book)
        self.pushButton__sponsor = QtWidgets.QPushButton("Sponsor on GitHub", self)
        self.pushButton__sponsor.setObjectName("pushButton__sponsor")
        self.pushButton__sponsor.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.pushButton__sponsor.setStyleSheet(
            "QPushButton {background: #ea4aaa; color: white; border: none;"
            " border-radius: 6px; padding: 6px 12px; font-weight: bold;}"
            " QPushButton:hover {background: #f06cbc;}"
        )
        self.pushButton__sponsor.clicked.connect(lambda: self._open_url(SPONSORS_URL))
        support.addWidget(self.pushButton__sponsor)
        layout.addLayout(support)

        self.toolButton__license = QtWidgets.QToolButton(self)
        self.toolButton__license.setObjectName("toolButton__license")
        self.toolButton__license.setText("Licenses")
        self.toolButton__license.setCheckable(True)
        self.toolButton__license.setAutoRaise(True)
        self.toolButton__license.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.toolButton__license.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self.toolButton__license.toggled.connect(self._toggle_license)
        layout.addWidget(self.toolButton__license)
        self.plainTextEdit__license = QtWidgets.QPlainTextEdit(self)
        self.plainTextEdit__license.setObjectName("plainTextEdit__license")
        self.plainTextEdit__license.setReadOnly(True)
        self.plainTextEdit__license.setPlainText(license_text())
        self.plainTextEdit__license.setMinimumHeight(180)
        # The licence files are hard-wrapped already; re-wrapping them looks ragged.
        self.plainTextEdit__license.setLineWrapMode(
            QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.plainTextEdit__license.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        )
        self.plainTextEdit__license.hide()
        layout.addWidget(self.plainTextEdit__license, 1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close, self
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _toggle_license(self, shown: bool) -> None:
        self.toolButton__license.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if shown else QtCore.Qt.ArrowType.RightArrow
        )
        self.plainTextEdit__license.setVisible(shown)
        self.adjustSize()
        if shown:
            # Wide enough for the licence's own 80-column lines, no side scrolling.
            self.resize(max(self.width(), LICENSE_PANE_WIDTH), self.height())

    def _copy_info(self) -> None:
        copy_to_clipboard(facts_text(self._facts))
        self.pushButton__copy_info.setText("Copied")
        QtCore.QTimer.singleShot(
            1500, lambda: self.pushButton__copy_info.setText("Copy info")
        )
