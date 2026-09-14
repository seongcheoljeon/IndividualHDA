"""Repository-backed asset search off the GUI thread; stale results are dropped."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6 import QtCore

from libs.background_job import BackgroundJob

SearchOperation = Callable[[str, threading.Event], list[int]]


class AssetSearch(QtCore.QObject):
    """One search at a time wins: every submit supersedes the previous one.

    ``rewrite`` (optional) transforms the text inside the worker before searching;
    the AI natural-language search plugs in there without touching the panel.
    """

    results = QtCore.Signal(object)  # frozenset[int]
    failed = QtCore.Signal(object)  # Exception

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        rewrite: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.rewrite = rewrite
        self._generation = 0
        self._cancel: threading.Event | None = None
        self._jobs: list[BackgroundJob] = []

    def submit(self, text: str, search: SearchOperation) -> None:
        self.cancel()
        self._generation += 1
        generation = self._generation
        cancel = threading.Event()
        self._cancel = cancel
        rewrite = self.rewrite

        def run() -> frozenset[int]:
            query = rewrite(text) if rewrite is not None else text
            return frozenset(search(query, cancel))

        job = BackgroundJob(run, self)
        job.result.connect(lambda value, error: self._deliver(generation, value, error))
        # Qt deletes the thread object once it has finished; we only drop our ref.
        job.finished.connect(job.deleteLater)
        job.finished.connect(lambda: self._forget(job))
        self._jobs.append(job)
        job.start()

    def cancel(self) -> None:
        if self._cancel is not None:
            self._cancel.set()
        self._generation += 1

    @property
    def busy(self) -> bool:
        return any(job.isRunning() for job in self._jobs)

    def drain(self) -> None:
        self.cancel()
        for job in list(self._jobs):
            job.wait()

    def _deliver(self, generation: int, value: object, error: object) -> None:
        if generation != self._generation:
            return  # superseded or cancelled
        if error is not None:
            self.failed.emit(error)
        else:
            self.results.emit(value)

    def _forget(self, job: BackgroundJob) -> None:
        if job in self._jobs:
            self._jobs.remove(job)
