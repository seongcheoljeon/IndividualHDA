"""Node icons come from Houdini, never from a file the panel has to find."""

from __future__ import annotations

import logging
from typing import Any

import pytest

import icons_rc  # noqa: F401 (the bundled fallbacks live in this resource)
from libs import ihda_icons, keys
from libs.ihda_icons import IHDAIcons


def test_icons_resolve_through_the_host_and_start_quietly(
    app: Any, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Startup used to log an error for $HH/help/icons.zip, gone since Houdini 19."""
    with caplog.at_level(logging.DEBUG):
        icons = IHDAIcons()
    assert caplog.records == []

    # Outside Houdini the host has no icon to give, so a bundled one stands in.
    blank = icons.get_houdini_icon(["SOP", "box"])
    assert not blank.isNull()
    assert not icons.get_category_icon("sop").isNull()
    assert not icons.get_houdini_icon(None).isNull()
    assert not icons.get_houdini_icon([keys.Type.chop, "wave"]).isNull()

    asked: list[str] = []

    def host_icon(name: str, size: int = 128) -> Any:
        asked.append(name)
        return None

    monkeypatch.setattr(ihda_icons.HoudiniAPI, "host_icon", host_icon)
    icons.make_pixmap_cate_data(cate_lst=["SOP"])
    icons.add_pixmap_cate_data("obj")
    icons.add_pixmap_ihda_data(hkey_id=1, icon_lst=["SOP", "box"])
    assert asked == ["NETWORKS_root", "NETWORKS_sop", "NETWORKS_obj", "SOP_box"]
    assert set(icons.pixmap_cate_data) == {"root", "sop", "obj"}
    assert 1 in icons.pixmap_ihda_data
    icons.shutdown()
