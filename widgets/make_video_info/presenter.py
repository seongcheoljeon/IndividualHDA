"""Video capture settings validation."""

from __future__ import annotations

import math
from typing import Protocol


class VideoInfoView(Protocol):
    def show_video_settings_error(self, message: str) -> None: ...


class VideoInfoPresenter:
    def __init__(self, view: VideoInfoView) -> None:
        self._view = view

    def validate(self, start: int, end: int, fps: float) -> bool:
        if end < start:
            self._view.show_video_settings_error(
                "End frame must not be before start frame."
            )
            return False
        if not math.isfinite(fps) or fps <= 0:
            self._view.show_video_settings_error(
                "Frame rate must be greater than zero."
            )
            return False
        return True
