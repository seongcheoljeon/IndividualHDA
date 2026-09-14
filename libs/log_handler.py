from __future__ import annotations

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.02.17 03:11:54
# modified date:
# description:
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


class _LogRelay(QtCore.QObject):
    message = QtCore.Signal(str)

    def __init__(self, widget: QtWidgets.QTextEdit) -> None:
        super().__init__(widget)
        self.widget = widget
        self.message.connect(self.append, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(str)
    def append(self, message: str) -> None:
        self.widget.append(message)
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
                self._relay.message.emit(self.format(record))
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
        if method.__name__ == "info":
            new_msg = f"<font color=#dddddd>{msg}</font>"
        elif method.__name__ == "debug":
            new_msg = f"<font color=#23bcde>{msg}</font>"
        elif method.__name__ == "warning":
            new_msg = f"<font color=#cc9900>{msg}</font>"
        elif method.__name__ == "error":
            new_msg = f"<font color=#e32474>{msg}</font>"
        elif method.__name__ == "critical":
            new_msg = f"<font color=#ff0000>{msg}</font>"
        else:
            raise TypeError("[log method] unknown type")
        method(new_msg)


if __name__ == "__main__":
    pass
