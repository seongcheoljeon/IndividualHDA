"""Deterministic asset filenames without a Houdini host."""

from pathlib import Path


class Names:
    @staticmethod
    def make_hda_filename(name: str, version: str, with_suffix: bool = True) -> str:
        return f"{name}-{version}.hda"

    @staticmethod
    def make_thumbnail_filename(name: str, version: str) -> str:
        return f"{name}.png"

    @staticmethod
    def make_thumbnail_dirpath(directory: Path) -> Path:
        return directory / "thumbnail"

    @staticmethod
    def make_video_filename(name: str, version: str) -> str:
        return f"{name}.mp4"

    @staticmethod
    def make_video_dirpath(directory: Path) -> Path:
        return directory / "video"
