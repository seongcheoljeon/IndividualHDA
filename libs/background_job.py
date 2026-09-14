"""Owned file/CPU workers. Never pass Qt widgets, HOM objects or DB connections."""

from __future__ import annotations

from typing import Any, Callable
from PySide6 import QtCore


class BackgroundJob(QtCore.QThread):
    result = QtCore.Signal(object, object)

    def __init__(
        self, operation: Callable[[], Any], parent: QtCore.QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.operation: Callable[[], Any] | None = operation
        # Read only after wait(); the host's destroy hook cannot wait for queued
        # UI delivery once it is about to delete the panel.
        self.outcome: tuple[Any, Exception | None] = (None, None)
        app = QtCore.QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown)

    @QtCore.Slot()
    def _shutdown(self) -> None:
        # File writes finish before Qt destroys the worker at application exit.
        self.wait()

    def run(self) -> None:
        try:
            operation = self.operation
            if operation is None:
                raise RuntimeError("A background operation can only run once")
            result = operation()
        except Exception as error:
            self.outcome = (None, error)
            self.result.emit(None, error)
        else:
            self.outcome = (result, None)
            self.result.emit(result, None)
        finally:
            self.operation = None
