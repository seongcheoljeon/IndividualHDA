"""Replaying file moves against stored rows needs no Qt and no database."""

from __future__ import annotations

from pathlib import Path

from libs.asset_contracts import HistoryData
from libs.path_updates import PathMove, relocate_history, relocated_path


def test_relocate_history_moves_every_file_pair_and_rechecks_availability(
    tmp_path: Path,
) -> None:
    old, new = tmp_path / "Old", tmp_path / "New"
    (new / "thumbnail").mkdir(parents=True)
    (new / "v1.hda").write_text("hda", encoding="utf-8")
    moves = (PathMove(source=old, target=new),)
    item = HistoryData(
        hist_id=1,
        hda_id=1,
        org_hda_name="Old",
        version="1.0",
        ihda_dirpath=old,
        ihda_filename="v1.hda",
        thumb_dirpath=old / "thumbnail",
        thumb_filename="v1.png",
        video_dirpath=None,
        video_filename=None,
        available=False,
    )
    moved = relocate_history(item, moves)
    assert moved.ihda_dirpath == new and moved.ihda_filename == "v1.hda"
    assert moved.thumb_dirpath == new / "thumbnail" and moved.thumb_filename == "v1.png"
    assert moved.video_dirpath is None  # untouched pairs stay untouched
    assert moved.available  # the file exists at the new place
    assert (
        relocated_path(tmp_path / "elsewhere" / "x", moves)
        == tmp_path / "elsewhere" / "x"
    )
