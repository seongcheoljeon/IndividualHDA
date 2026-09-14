from __future__ import annotations

import pathlib
from types import SimpleNamespace
from typing import Any

import pytest

from libs import houdini_api


def test_preview_restores_timeline_after_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    state = {"fps": 23.976, "frame": 31.5, "global": (1, 240), "playback": (20, 100)}
    playbar = SimpleNamespace(
        frameRange=lambda: state["global"],
        playbackRange=lambda: state["playback"],
        setFrameRange=lambda a, b: state.update({"global": (a, b)}),
        setPlaybackRange=lambda a, b: state.update({"playback": (a, b)}),
    )
    hou = SimpleNamespace(
        fps=lambda: state["fps"],
        frame=lambda: state["frame"],
        playbar=playbar,
        setFps=lambda value: state.update(fps=value),
        setFrame=lambda value: state.update(frame=value),
    )
    monkeypatch.setattr(houdini_api, "hou", hou, raising=False)

    def fail(**kwargs: Any) -> None:
        raise RuntimeError("viewport error")

    monkeypatch.setattr(houdini_api.HoudiniAPI, "_HoudiniAPI__flipbook", fail)
    with pytest.raises(RuntimeError):
        houdini_api.HoudiniAPI.create_preview(
            tmp_path / "test.jpg", [1001, 1010, 30], [400, 400]
        )
    assert state == {
        "fps": 23.976,
        "frame": 31.5,
        "global": (1, 240),
        "playback": (20, 100),
    }


def test_houdini_deferred_callback_ignores_destroyed_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from widgets.panel import host_callbacks

    queued: list = []
    calls: list[str] = []
    from libs import houdini_api

    monkeypatch.setattr(
        houdini_api,
        "hdefereval",
        SimpleNamespace(executeDeferred=queued.append),
        raising=False,
    )
    panel = SimpleNamespace(_closing=False, _host_destroying=False)
    host_callbacks.HostCallbacksMixin._wrapper_execute_deferred(
        panel, lambda: calls.append("called")
    )
    assert calls == []
    queued.pop()()
    assert calls == ["called"]
    host_callbacks.HostCallbacksMixin._wrapper_execute_deferred(
        panel, lambda: calls.append("late")
    )
    panel._host_destroying = True
    queued.pop()()
    assert calls == ["called"]


def test_network_category_lookup_does_not_mutate_scene(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_hou = SimpleNamespace(
        PythonPanel=type("PythonPanel", (), {}),
        ObjectWasDeleted=LookupError,
        OperationFailed=RuntimeError,
    )
    monkeypatch.setattr(houdini_api, "hou", fake_hou, raising=False)
    # No createNode/currentNode API is provided: lookup needs only the native category.
    network = SimpleNamespace(
        childTypeCategory=lambda: SimpleNamespace(typeName=lambda: "Sop")
    )
    editor = SimpleNamespace(pwd=lambda: network)
    assert houdini_api.HoudiniAPI.current_network_editor_type_name(editor) == "sop"
    assert houdini_api.HoudiniAPI.current_network_editor_type_name(None) is None
