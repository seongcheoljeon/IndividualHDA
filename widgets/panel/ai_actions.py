"""AI suggestions for the selected asset. The AI only fills editors; saving stays
with the existing Save buttons, so nothing reaches the library without a click."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from libs import log_handler
from libs.ai_backends import format_timings
from libs.ai_features import Description, describe_asset
from libs.item_paths import item_path
from widgets.ui_tokens import TOOLBAR_ICON_SIZE

if TYPE_CHECKING:
    from libs.task_controller import TaskController
    from widgets.panel.layout import MainWindowLayout
    from widgets.panel.library_port import LibraryPort
    from widgets.panel.ports import NotesPort, SelectionPort
    from widgets.panel.services import PanelServices
    from widgets.panel.state import PanelSessionState
    from widgets.preference.preference import Preference


@dataclass(frozen=True, slots=True)
class PanelAIActionsBindings:
    notes: NotesPort
    preference: Preference
    selection: SelectionPort
    services: PanelServices
    session: PanelSessionState
    tasks: TaskController
    library: Callable[[], LibraryPort]
    ui: MainWindowLayout


class _Cancelled(Exception):
    """Raised on the worker thread to abort a streaming AI request.

    Must derive from Exception, not BaseException: BackgroundJob.run catches
    Exception and routes it to the result channel, which is how the GUI learns
    the request stopped. concurrent.futures.CancelledError would escape.
    """


class PanelAIActions(QtCore.QObject):
    bindings: PanelAIActionsBindings

    # Running token count. `object`, not `int`: a Qt int argument is 32-bit.
    progress = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.target_id: int | None = None
        self._provider: Any = None
        self._target_repository: object | None = None
        self._target_generation = -1
        self._cancel = threading.Event()
        self._started = 0.0

    def setup_ai_actions(self) -> None:
        # Not named connect(): this class is a QObject and QObject.connect is
        # what PySide6 calls, with four arguments, to wire up a signal.
        self.bindings.ui.pushButton__ai_suggest = QtWidgets.QPushButton(
            "AI", self.bindings.ui.widget__tag_editor
        )
        self.bindings.ui.pushButton__ai_suggest.setToolTip(
            "Suggest a note and tags with the configured AI backend"
        )
        self.bindings.ui.pushButton__ai_suggest.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/network_intelligence.png"))
        )
        # Without this the button falls back to the style's smaller default and
        # looks undersized beside its siblings in the tag action row.
        self.bindings.ui.pushButton__ai_suggest.setIconSize(
            QtCore.QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE)
        )
        self.bindings.ui.pushButton__ai_suggest.setFlat(True)
        self.bindings.ui.pushButton__ai_suggest.setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor
        )
        self.bindings.ui.horizontalLayout__tag_actions.insertWidget(
            0, self.bindings.ui.pushButton__ai_suggest
        )
        self.bindings.ui.pushButton__ai_suggest.clicked.connect(self.suggest)
        ui = self.bindings.ui
        ui.pushButton__ai_cancel = QtWidgets.QPushButton(
            "Cancel", ui.widget__tag_editor
        )
        ui.pushButton__ai_cancel.setObjectName("pushButton__ai_cancel")
        ui.pushButton__ai_cancel.setFlat(True)
        ui.pushButton__ai_cancel.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        ui.pushButton__ai_cancel.setVisible(False)
        ui.pushButton__ai_cancel.clicked.connect(self.cancel)
        ui.label__ai_status = QtWidgets.QLabel("", ui.widget__tag_editor)
        ui.label__ai_status.setObjectName("label__ai_status")
        ui.label__ai_status.setVisible(False)
        # Left of the expanding spacer, so a long line grows into the free middle
        # instead of pushing the save button.
        ui.horizontalLayout__tag_actions.insertWidget(1, ui.pushButton__ai_cancel)
        ui.horizontalLayout__tag_actions.insertWidget(2, ui.label__ai_status)
        self.progress.connect(self._show_progress)
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
        self._cancel = threading.Event()
        token = self._cancel
        self._started = time.monotonic()

        def tick(count: int) -> None:
            # Worker thread. Signal.emit is thread-safe and delivers queued.
            # ponytail: cancel lands on the next stream event; nothing arrives
            # while the model loads into VRAM.
            if token.is_set():
                raise _Cancelled
            self.progress.emit(count)

        self._show_progress(0)
        self.bindings.ui.label__ai_status.setVisible(True)
        self.bindings.ui.pushButton__ai_cancel.setVisible(True)
        self.bindings.ui.pushButton__ai_cancel.setEnabled(True)
        self.bindings.tasks.start(
            lambda: describe_asset(
                provider,
                asset,
                thumbnail=thumbnail,
                vocabulary=vocabulary,
                language=language,
                progress=tick,
            ),
            self.describe_done,
        )

    def describe_done(self, description: Description) -> None:
        if self._cancel.is_set():
            return
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
        existing = self.bindings.notes.split_tag_string(
            tag_str=self.bindings.notes.hda_tags
        )
        merged = sorted(set(existing) | set(description.tags))
        self.bindings.ui.textEdit__tag.setPlainText(
            self.bindings.notes.set_tag_string(merged)
        )
        timings = format_timings(getattr(self._provider, "last_timings", None) or {})
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="AI suggestion filled the note and tag editors; press the save buttons"
            " to keep them" + (f" ({timings})" if timings else ""),
        )

    @QtCore.Slot(object)
    def _show_progress(self, count: Any) -> None:
        elapsed = time.monotonic() - self._started
        self.bindings.ui.label__ai_status.setText(
            f"AI thinking… {count} tokens, {elapsed:.1f}s" if count else "AI thinking…"
        )

    @QtCore.Slot()
    def cancel(self) -> None:
        self._cancel.set()
        self.bindings.ui.pushButton__ai_cancel.setEnabled(False)
        self.bindings.ui.label__ai_status.setText("Cancelling…")

    @QtCore.Slot(object, object)
    def result(self, value: Any, error: Any) -> None:
        # A cancel arrives through the error channel; it is not a failure.
        if isinstance(error, _Cancelled):
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="AI suggestion cancelled"
            )
            return
        if error is not None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg=f"AI request failed: {error}"
            )

    @QtCore.Slot()
    def idle(self) -> None:
        self.bindings.ui.label__ai_status.setText("")
        self.bindings.ui.label__ai_status.setVisible(False)
        self.bindings.ui.pushButton__ai_cancel.setVisible(False)
        self.bindings.ui.pushButton__ai_suggest.setEnabled(
            self.bindings.library().writable
        )
