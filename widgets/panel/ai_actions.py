"""AI suggestions for the selected asset. The AI only fills editors; saving stays
with the existing Save buttons, so nothing reaches the library without a click."""

from __future__ import annotations

import logging
import pathlib
from typing import Any, cast

from PySide6 import QtCore, QtGui, QtWidgets

from libs import log_handler
from libs.ai_backends import format_timings
from libs.ai_features import Description, describe_asset
from libs.domain import AssetData
from libs.keys import Key


class PanelAIActions:
    def __init__(self, window: Any) -> None:
        self.window = window
        self.target_id: int | None = None
        self._provider: Any = None

    def connect(self) -> None:
        window = self.window
        window.pushButton__ai_suggest = QtWidgets.QPushButton(
            "AI", window.widget__tag_editor
        )
        window.pushButton__ai_suggest.setToolTip(
            "Suggest a note and tags with the configured AI backend"
        )
        window.pushButton__ai_suggest.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_new_releases_white.png"))
        )
        window.pushButton__ai_suggest.setFlat(True)
        window.pushButton__ai_suggest.setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor
        )
        window.horizontalLayout__tag_actions.insertWidget(
            0, window.pushButton__ai_suggest
        )
        window.pushButton__ai_suggest.clicked.connect(self.suggest)
        window._ai_tasks.result.connect(self.result)
        window._ai_tasks.idle.connect(self.idle)

    def language(self) -> str:
        window = self.window
        note = (
            window._selection.asset.data.get(Key.hda_note)
            if window._selection.asset.data
            else None
        )
        if note and note.strip():
            return "the language of the existing note"
        return QtCore.QLocale.system().name()[:2] or "en"

    @QtCore.Slot()
    def suggest(self) -> None:
        window = self.window
        data = window._selection.asset.data
        settings = window._preference.ai_settings
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
        if window._ai_tasks.busy:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="AI is still working on the previous request"
            )
            return
        provider = window._services.ai(settings)
        self._provider = provider  # timings of the finished call are read from it
        asset = cast(AssetData, dict(data))
        thumbnail: pathlib.Path | None = None
        if data.get(Key.thumbnail_dirpath) and data.get(Key.thumbnail_filename):
            thumbnail = (
                pathlib.Path(data[Key.thumbnail_dirpath]) / data[Key.thumbnail_filename]
            )
        vocabulary = (
            window._repository.distinct_tags(owner=window._user)
            if window._repository
            else []
        )
        language = self.language()
        self.target_id = data.get(Key.hda_id)
        window.pushButton__ai_suggest.setEnabled(False)
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg=f"AI: suggesting note and tags for {asset.get('hda_name')}…",
        )
        window._ai_tasks.start(
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
        window = self.window
        if window._selection.asset.id != self.target_id:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="AI suggestion discarded: selection changed"
            )
            return
        if description.summary:
            window.textEdit__note.setPlainText(description.summary)
        existing = window._split_tag_string(tag_str=window._hda_tags)
        merged = sorted(set(existing) | set(description.tags))
        window.textEdit__tag.setPlainText(window._set_tag_string(merged))
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
        window = self.window
        team = getattr(window, "_team_library", None)
        window.pushButton__ai_suggest.setEnabled(
            team is None or not team.active or team.writable
        )
