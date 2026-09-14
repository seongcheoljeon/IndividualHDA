"""Owned asynchronous processes with bounded output and cancellation."""

from __future__ import annotations

from PySide6 import QtCore


class ProcessJob(QtCore.QObject):
    finished = QtCore.Signal(int, str)

    def __init__(
        self,
        command: list[str] | tuple[str, ...],
        parent: QtCore.QObject | None = None,
        timeout_ms: int = 0,
    ) -> None:
        super().__init__(parent)
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.command = list(command)
        self.output = bytearray()
        self._done = False
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.cancel)
        self.timeout_ms = timeout_ms

    def start(self) -> None:
        self.process.start(self.command[0], self.command[1:])
        if self.timeout_ms:
            self.timer.start(self.timeout_ms)

    def _read(self) -> None:
        self.output.extend(bytes(self.process.readAllStandardOutput()))
        del self.output[:-1048576]

    def _error(self, error: QtCore.QProcess.ProcessError) -> None:
        if error == QtCore.QProcess.FailedToStart:
            self._complete(-1, self.process.errorString())

    def _finished(self, code: int, status: QtCore.QProcess.ExitStatus) -> None:
        self._read()
        self._complete(
            code if status == QtCore.QProcess.NormalExit else -1,
            self.output.decode("utf-8", errors="replace"),
        )

    def _complete(self, code: int, output: str) -> None:
        if self._done:
            return
        self._done = True
        self.timer.stop()
        self.finished.emit(code, output)

    def cancel(self) -> None:
        self.process.kill()

    def shutdown(self) -> None:
        self.timer.stop()
        if self.process.state() != QtCore.QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
