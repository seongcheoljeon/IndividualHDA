"""AI suggestions for the selected asset. The AI only fills editors; saving stays
with the existing Save buttons, so nothing reaches the library without a click."""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

import public
from libs import log_handler
from libs.ai_features import Description, describe_asset


class AIActionsMixin:
    def _init_ai_actions(self) -> None:
        self.pushButton__ai_suggest = QtWidgets.QPushButton("AI", self.layoutWidget5)
        self.pushButton__ai_suggest.setToolTip(
            "Suggest a note and tags with the configured AI backend"
        )
        self.pushButton__ai_suggest.setIcon(
            QtGui.QIcon(QtGui.QPixmap(":/main/icons/ic_new_releases_white.png"))
        )
        self.pushButton__ai_suggest.setFlat(True)
        self.pushButton__ai_suggest.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.horizontalLayout_6.insertWidget(0, self.pushButton__ai_suggest)
        self.pushButton__ai_suggest.clicked.connect(self._slot_ai_suggest)
        self._ai_tasks.result.connect(self._ai_result)
        self._ai_tasks.idle.connect(self._ai_idle)
        self._ai_target_id: int | None = None

    def _ai_language(self) -> str:
        note = (
            self._selection.asset.data.get(public.Key.hda_note)
            if self._selection.asset.data
            else None
        )
        if note and note.strip():
            return "the language of the existing note"
        return QtCore.QLocale.system().name()[:2] or "en"

    @QtCore.Slot()
    def _slot_ai_suggest(self) -> None:
        data = self._selection.asset.data
        settings = self._preference.ai_settings
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
        if self._ai_tasks.busy:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="AI is still working on the previous request"
            )
            return
        provider = self._services.ai(settings)
        asset = dict(data)
        thumbnail: pathlib.Path | None = None
        if data.get(public.Key.thumbnail_dirpath) and data.get(
            public.Key.thumbnail_filename
        ):
            thumbnail = (
                pathlib.Path(data[public.Key.thumbnail_dirpath])
                / data[public.Key.thumbnail_filename]
            )
        vocabulary = (
            self._repository.distinct_tags(owner=self._user) if self._repository else []
        )
        language = self._ai_language()
        self._ai_target_id = data.get(public.Key.hda_id)
        self.pushButton__ai_suggest.setEnabled(False)
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg=f"AI: suggesting note and tags for {asset.get('hda_name')}…",
        )
        self._ai_tasks.start(
            lambda: describe_asset(
                provider,
                asset,
                thumbnail=thumbnail,
                vocabulary=vocabulary,
                language=language,
            ),
            self._ai_describe_done,
        )

    def _ai_describe_done(self, description: Description) -> None:
        if self._selection.asset.id != self._ai_target_id:
            log_handler.LogHandler.log_msg(
                method=logging.info, msg="AI suggestion discarded: selection changed"
            )
            return
        if description.summary:
            self.textEdit__note.setPlainText(description.summary)
        existing = self._split_tag_string(tag_str=self._hda_tags)
        merged = sorted(set(existing) | set(description.tags))
        self.textEdit__tag.setPlainText(self._set_tag_string(merged))
        log_handler.LogHandler.log_msg(
            method=logging.info,
            msg="AI suggestion filled the note and tag editors; press the save buttons to keep them",
        )

    @QtCore.Slot(object, object)
    def _ai_result(self, value: Any, error: Any) -> None:
        if error is not None:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg=f"AI request failed: {error}"
            )

    @QtCore.Slot()
    def _ai_idle(self) -> None:
        self.pushButton__ai_suggest.setEnabled(True)
