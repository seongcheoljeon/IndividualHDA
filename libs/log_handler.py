from __future__ import annotations

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.02.17 03:11:54
# modified date:
# description:
import html
import logging
import logging.handlers
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

_FILE_HANDLER_MARK = "_ihda_file_handler"
_TAGS = re.compile(r"<[^>]+>")
# Level colours belong to the view, which knows the palette it draws on: the old
# near-white info colour was invisible whenever the host theme was light. INFO
# carries no colour at all, so most lines simply use the pane's text colour.
_DARK_LEVELS = {
    logging.DEBUG: "#5bc8e8",
    logging.WARNING: "#e0a33a",
    logging.ERROR: "#ff6b6b",
    logging.CRITICAL: "#ff3b3b",
}
_LIGHT_LEVELS = {
    logging.DEBUG: "#0b6e8a",
    logging.WARNING: "#8a6100",
    logging.ERROR: "#c0392b",
    logging.CRITICAL: "#a01010",
}


def level_html(message: str, level: int, palette: QtGui.QPalette) -> str:
    """``message`` as rich text for a log pane with this palette."""
    dark = palette.base().color().lightness() < 128
    colour = (_DARK_LEVELS if dark else _LIGHT_LEVELS).get(level)
    text = html.escape(message)
    if level >= logging.CRITICAL:
        text = f"<b>{text}</b>"
    return text if colour is None else f'<span style="color:{colour}">{text}</span>'


class _PlainFormatter(logging.Formatter):
    """Panel messages carry <font> markup; the file gets plain text."""

    def format(self, record: logging.LogRecord) -> str:
        return _TAGS.sub("", super().format(record))


def install_file_logging(directory: Path) -> Path:
    """Rotating file log shared by every panel in the process; idempotent.

    INFO by default, DEBUG when IHDA_DEBUG is set. Handlers filter by level, so the
    root logger stays at DEBUG for the panel widget handler.
    """
    root = logging.getLogger()
    for handler in root.handlers:
        if getattr(handler, _FILE_HANDLER_MARK, False):
            return Path(handler.baseFilename)  # type: ignore[attr-defined]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "ihda.log"
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        _PlainFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler.setLevel(logging.DEBUG if os.environ.get("IHDA_DEBUG") else logging.INFO)
    setattr(handler, _FILE_HANDLER_MARK, True)
    root.addHandler(handler)
    if root.level == logging.NOTSET or root.level > logging.DEBUG:
        root.setLevel(logging.DEBUG)
    return path


def uninstall_file_logging() -> None:
    """Close the process-wide file handler so its directory can be removed.

    Windows refuses to delete an open log file; callers that remove the
    configuration directory (reset app properties, host smoke test) run this first.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _FILE_HANDLER_MARK, False):
            root.removeHandler(handler)
            handler.close()


class _LogRelay(QtCore.QObject):
    message = QtCore.Signal(str, int)

    def __init__(self, widget: QtWidgets.QTextEdit) -> None:
        super().__init__(widget)
        self.widget = widget
        self.message.connect(self.append, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(str, int)
    def append(self, message: str, level: int) -> None:
        # On the GUI thread: the palette is read now, so a theme switch applies
        # to the lines written after it.
        self.widget.append(level_html(message, level, self.widget.palette()))
        self.widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)


def log_elapsed(label: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Log how long the wrapped call took, at info level, in the panel log."""

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                LogHandler.log_msg(
                    method=logging.info,
                    msg=f"( {label} ) elapsed time: {int(elapsed // 60)}m {int(elapsed % 60)}s",
                )

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorate


class LogHandler(logging.Handler):
    def __init__(self, out_stream: Any = None) -> None:
        super().__init__()
        # log text msg format
        self.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] : %(message)s")
        )
        logging.getLogger().addHandler(self)
        # logging level
        logging.getLogger().setLevel(logging.DEBUG)
        self.__out_stream = out_stream
        self._relay = _LogRelay(out_stream) if out_stream is not None else None

    def emit(self, record: Any) -> None:
        if self._relay is not None:
            try:
                self._relay.message.emit(self.format(record), record.levelno)
            except RuntimeError:
                self.close()

    def close(self) -> None:
        logging.getLogger().removeHandler(self)
        self._relay = None
        super().close()

    @staticmethod
    def log_msg(method: Callable[..., Any] | None = None, msg: object = "") -> None:
        if method is None:
            return
        if method.__name__ not in {"info", "debug", "warning", "error", "critical"}:
            raise TypeError("[log method] unknown type")
        method(msg)


if __name__ == "__main__":
    pass
