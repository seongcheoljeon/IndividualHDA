"""GUI-thread ownership and exactly-once completion of background file work."""

from __future__ import annotations
from collections.abc import Callable
from typing import Any
import logging
from PySide6.QtCore import QObject, QCoreApplication, Signal, Slot
from libs.background_job import BackgroundJob
from libs.process_job import ProcessJob


class TaskController(QObject):
    result = Signal(object, object)
    idle = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        file_factory: Callable[
            [Callable[[], Any], QObject | None], BackgroundJob
        ] = BackgroundJob,
        process_factory: Callable[[list[str], QObject | None], ProcessJob] = ProcessJob,
    ) -> None:
        super().__init__(parent)
        self._file_job: BackgroundJob | None = None
        self._video_job: ProcessJob | None = None
        self._completion: Callable[[Any], None] | None = None
        self._delivered = False
        self._file_factory = file_factory
        self._process_factory = process_factory

    @property
    def file_job(self) -> BackgroundJob | None:
        return self._file_job

    @property
    def video_job(self) -> ProcessJob | None:
        return self._video_job

    def start_process(
        self, command: list[str], completion: Callable[[int, str], None]
    ) -> bool:
        if self.busy:
            return False
        if not command:
            raise ValueError("Process command must not be empty")
        job = self._process_factory(command, self)
        self._video_job = job

        def finished(code: int, diagnostic: str) -> None:
            if self._video_job is None or self._video_job is not job:
                return
            try:
                completion(code, diagnostic)
            except Exception:
                logging.exception("Process completion callback failed")
            finally:
                job.deleteLater()
                self._video_job = None
                self.idle.emit()

        job.finished.connect(finished)
        try:
            job.start()
        except Exception:
            self._video_job = None
            job.deleteLater()
            raise
        return True

    def shutdown_process(self) -> None:
        if self._video_job is not None:
            self._video_job.shutdown()

    @property
    def busy(self) -> bool:
        return self.file_job is not None or self.video_job is not None

    def start(
        self, operation: Callable[[], Any], completion: Callable[[Any], None]
    ) -> bool:
        if self.busy:
            return False
        job = self._file_factory(operation, QCoreApplication.instance())
        self._file_job = job
        self._completion = completion
        self._delivered = False
        job.result.connect(self._receive)
        job.finished.connect(self._finish)
        try:
            job.start()
        except Exception:
            self._file_job = None
            self._completion = None
            self._delivered = True
            job.deleteLater()
            raise
        return True

    @Slot(object, object)
    def _receive(self, value: Any, error: Exception | None) -> None:
        if self._delivered:
            return
        self._delivered = True
        completion, self._completion = self._completion, None
        self.result.emit(value, error)
        if error is None and completion is not None:
            try:
                completion(value)
            except Exception:
                logging.exception("Background completion callback failed")

    @Slot()
    def _finish(self) -> None:
        job = self.file_job
        if job is None:
            return
        try:
            self._receive(*job.outcome)
        finally:
            self._file_job = None
            self._completion = None
            job.deleteLater()
            self.idle.emit()

    def drain(self) -> None:
        """Houdini onDestroyInterface cannot defer widget destruction."""
        job = self.file_job
        if job is not None:
            job.result.disconnect(self._receive)
            job.finished.disconnect(self._finish)
            job.wait()
            self._finish()
