"""Preference validation with injected local path/executable checks."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class PreferenceView(Protocol):
    def show_preference_error(self, message: str) -> None: ...


class PreferencePresenter:
    def __init__(
        self, view: PreferenceView, is_directory: Callable[[Path], bool] = Path.is_dir
    ) -> None:
        self._view = view
        self._is_directory = is_directory

    def validate(self, directory: str) -> bool:
        if not directory.strip():
            self._view.show_preference_error(
                "Please specify the folder where the data is stored"
            )
            return False
        if not self._is_directory(Path(directory.strip())):
            self._view.show_preference_error("Directory does not exist")
            return False
        return True
