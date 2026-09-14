from __future__ import annotations
from PySide6 import QtWidgets

from typing import Any, Callable

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.02.17 03:11:54
# modified date:
# description:

import logging

from PySide6 import QtGui, QtCore


class _LogRelay(QtCore.QObject):
    message = QtCore.Signal(str)

    def __init__(self, widget: QtWidgets.QWidget) -> None:
        super().__init__(widget)
        self.widget = widget
        self.message.connect(self.append, QtCore.Qt.QueuedConnection)

    @QtCore.Slot(str)
    def append(self, message: str) -> None:
        self.widget.append(message)
        self.widget.moveCursor(QtGui.QTextCursor.End)


class LogHandler(logging.Handler):
    def __init__(self, out_stream: Any = None) -> None:
        super(LogHandler, self).__init__()
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
    def log_msg(method: Callable[..., Any] | None = None, msg: str = "") -> None:
        if method is None:
            return
        if method.__name__ == "info":
            new_msg = "<font color=#dddddd>{msg}</font>".format(msg=msg)
        elif method.__name__ == "debug":
            new_msg = "<font color=#23bcde>{msg}</font>".format(msg=msg)
        elif method.__name__ == "warning":
            new_msg = "<font color=#cc9900>{msg}</font>".format(msg=msg)
        elif method.__name__ == "error":
            new_msg = "<font color=#e32474>{msg}</font>".format(msg=msg)
        elif method.__name__ == "critical":
            new_msg = "<font color=#ff0000>{msg}</font>".format(msg=msg)
        else:
            raise TypeError("[log method] unknown type")
        method(new_msg)


if __name__ == "__main__":
    pass
