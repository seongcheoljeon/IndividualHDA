"""Qt task adapter for transport-independent presenters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.task_controller import TaskController


class WorkspaceTaskExecutor:
    def __init__(self, tasks: TaskController) -> None:
        self.tasks = tasks
        self._finished: Callable[[Any, Exception | None], None] | None = None
        tasks.result.connect(self._result)

    def submit(
        self,
        operation: Callable[[], Any],
        finished: Callable[[Any, Exception | None], None],
    ) -> bool:
        if self.tasks.busy:
            return False
        self._finished = finished
        try:
            return self.tasks.start(operation, lambda _: None)
        except Exception:
            self._finished = None
            raise

    def _result(self, result: Any, error: Exception | None) -> None:
        finished, self._finished = self._finished, None
        if finished is not None:
            finished(result, error)
