"""AI suggestions for the selected asset. The AI only fills editors; saving stays
with the existing Save buttons, so nothing reaches the library without a click."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs import log_handler
from libs.ai_backends import format_timings
from libs.ai_features import Description, describe_asset
from libs.item_paths import item_path

if TYPE_CHECKING:
    from libs.task_controller import TaskController
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.notes import PanelNotes
    from widgets.panel.selection import PanelSelection
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState
    from widgets.preference.preference import Preference
    from widgets.team_library.integration import MainLibraryIntegration


@dataclass(frozen=True, slots=True)
class PanelAIActionsBindings:
    notes: PanelNotes
    preference: Preference
    selection: PanelSelection
    services: PanelServices
    session: PanelSessionState
    tasks: TaskController
    team: Callable[[], MainLibraryIntegration]
    ui: MainWindowLayout


class PanelAIActions:
    bindings: PanelAIActionsBindings

    def __init__(self) -> None:
        self.target_id: int | None = None
        self._provider: Any = None
        self._target_repository: object | None = None
        self._target_generation = -1

    def connect(self) -> None:
        self.bindings.ui.pushButton__ai_suggest = QtWidgets.QPushButton(
            "AI", self.bindings.ui.widget__tag_editor
        )
        self.bindings.ui.pushButton__ai_suggest.setToolTip(
            "Suggest a note and tags with the configured AI backend"
        )
        self.bindings.ui.pushButton__ai_suggest.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_new_releases_white.png"))
        )
        self.bindings.ui.pushButton__ai_suggest.setFlat(True)
        self.bindings.ui.pushButton__ai_suggest.setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor
        )
        self.bindings.ui.horizontalLayout__tag_actions.insertWidget(
            0, self.bindings.ui.pushButton__ai_suggest
        )
        self.bindings.ui.pushButton__ai_suggest.clicked.connect(self.suggest)
        self.bindings.tasks.result.connect(self.result)
        self.bindings.tasks.idle.connect(self.idle)

    def language(self) -> str:
        note = (
            self.bindings.selection.state.asset.require_data().hda_note
            if self.bindings.selection.state.asset.data
            else None
        )
        if note and note.strip():
            return "the language of the existing note"
        return QtCore.QLocale.system().name()[:2] or "en"

    @QtCore.Slot()
    def suggest(self) -> None:
        data = self.bindings.selection.state.asset.data
        settings = self.bindings.preference.ai_settings
        if data is None:
            log_handler.LogHandler.log_msg(
                method=logging.warning, msg="select an iHDA node first"
            )
            return
        if settings.kind == "none":
            log_handler.LogHandler.log_msg(
                method=logging.warning,
                msg="no AI backend configured (Tools > Local AI Models… or Preferences > AI)",
            )
            return
        if self.bindings.tasks.busy:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="AI is still working on the previous request"
            )
            return
        provider = self.bindings.services.ai(settings)
        self._provider = provider  # timings of the finished call are read from it
        asset = data
        thumbnail = item_path(data.thumbnail_dirpath, data.thumbnail_filename)
        vocabulary = (
            self.bindings.session.require_repository().distinct_tags(
                owner=self.bindings.session.user
            )
            if self.bindings.session.repository
            else []
        )
        language = self.language()
        self.target_id = data.hda_id
        self._target_repository = self.bindings.session.repository
        self._target_generation = self.bindings.session.generation
        self.bindings.ui.pushButton__ai_suggest.setEnabled(False)
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg=f"AI: suggesting note and tags for {asset.hda_name}…",
        )
        self.bindings.tasks.start(
            lambda: describe_asset(
                provider,
                asset,
                thumbnail=thumbnail,
                vocabulary=vocabulary,
                language=language,
            ),
            self.describe_done,
        )

    def describe_done(self, description: Description) -> None:
        if (
            self.bindings.selection.state.asset.id != self.target_id
            or self.bindings.session.repository is not self._target_repository
            or self.bindings.session.generation != self._target_generation
        ):
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="AI suggestion discarded: selection changed"
            )
            return
        if description.summary:
            self.bindings.ui.textEdit__note.setPlainText(description.summary)
        existing = self.bindings.notes._split_tag_string(
            tag_str=self.bindings.notes._hda_tags
        )
        merged = sorted(set(existing) | set(description.tags))
        self.bindings.ui.textEdit__tag.setPlainText(
            self.bindings.notes._set_tag_string(merged)
        )
        timings = format_timings(getattr(self._provider, "last_timings", None) or {})
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="AI suggestion filled the note and tag editors; press the save buttons"
            " to keep them" + (f" ({timings})" if timings else ""),
        )

    @QtCore.Slot(object, object)
    def result(self, value: Any, error: Any) -> None:
        if error is not None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg=f"AI request failed: {error}"
            )

    @QtCore.Slot()
    def idle(self) -> None:
        team = self.bindings.team()
        self.bindings.ui.pushButton__ai_suggest.setEnabled(
            team is None or not team.active or team.writable
        )
