"""GUI-owned debounce; pending callbacks disappear with their owner."""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore


class DebouncedText(QtCore.QObject):
    def __init__(
        self,
        callback: Callable[[str], None],
        parent: QtCore.QObject,
        delay: int = 200,
        immediate: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self.immediate = immediate
        self.callback = callback
        self.value = ""
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(delay)
        self.timer.timeout.connect(self._deliver)

    @QtCore.Slot(str)
    def submit(self, value: str) -> None:
        self.value = value
        if self.immediate is not None and self.immediate():
            self.timer.stop()
            self.callback(value)
        else:
            self.timer.start()

    def _deliver(self) -> None:
        self.callback(self.value)
