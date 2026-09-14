from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

import public
from libs.ai_provider import AISettings
from libs.settings_store import apply_settings, load_json, save_json


def test_load_json_sets_aside_corrupt_files(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "prefs.json"
    assert load_json(path) == {}  # missing file
    path.write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        assert load_json(path) == {}
    assert not path.exists() and path.with_suffix(".corrupt").exists()
    assert "unreadable" in caplog.text
    path.write_text("[1, 2]", encoding="utf-8")
    assert load_json(path) == {} and path.with_suffix(".corrupt").exists()
    save_json(path, {"a": 1})
    assert load_json(path) == {"a": 1}


def test_apply_settings_isolates_each_key(caplog: pytest.LogCaptureFixture) -> None:
    applied: dict[str, Any] = {}

    def strict_int(value: Any) -> None:
        if not isinstance(value, int):
            raise TypeError("int required")
        applied["size"] = value

    table = [
        ("size", strict_int),
        ("name", lambda value: applied.__setitem__("name", value)),
        ("missing", lambda value: applied.__setitem__("missing", value)),
    ]
    with caplog.at_level(logging.WARNING):
        skipped = apply_settings({"size": "12", "name": "x"}, table)
    assert skipped == ["size", "missing"] and applied == {"name": "x"}
    assert "Ignoring setting size" in caplog.text


def test_preference_survives_bad_values_and_unknown_ai_keys(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from widgets.preference.preference import Preference

    prefs = tmp_path / "prefs.json"
    monkeypatch.setattr(public.Paths, "json_pref_filepath", prefs)
    keys = public.Name.PreferenceUI
    prefs.write_text(
        json.dumps(
            {
                keys.lineedit_data_dirpath: tmp_path.as_posix(),
                keys.spb_view_font_size: "twelve",  # wrong type: skipped, not fatal
                keys.spb_note_font_size: 17,  # later key still applied
                keys.ai: {"kind": "local", "model": "m", "future_field": 1},
            }
        ),
        encoding="utf-8",
    )
    preference = Preference()
    assert preference.data_dirpath == tmp_path
    assert preference.spinBox__note_font_size.value() == 17
    assert preference.ai_settings == AISettings(kind="local", model="m")
    preference.close()
