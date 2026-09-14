from __future__ import annotations

from typing import Any
import pathlib
import threading

import pytest

import public
from libs.ai_provider import KINDS, AISettings, NullProvider, Prompt, make_provider
from libs.settings_store import save_json
from libs.task_controller import TaskController
from widgets.panel.services import PanelServices


def test_provider_dispatch_by_kind() -> None:
    from libs.ai_backends import OllamaProvider

    for kind in KINDS:
        provider = PanelServices().ai(AISettings(kind=kind, model="m"))
        if kind == "local":
            assert isinstance(provider, OllamaProvider)
        else:  # cloud backends arrive in a later phase
            assert isinstance(provider, NullProvider)
            assert provider.complete(Prompt("describe", images=(b"png",))) == ""
    assert make_provider(AISettings()).complete(Prompt("x")) == ""


def test_ai_call_runs_off_gui_thread_and_delivers_once(app: Any) -> None:
    from PySide6.QtCore import QThread

    seen: list[Any] = []
    results: list[str] = []

    class Recording:
        def complete(self, prompt: Prompt) -> str:
            seen.append(QThread.currentThread())
            return prompt.text.upper()

    provider = Recording()
    controller = TaskController()
    assert controller.start(lambda: provider.complete(Prompt("hda")), results.append)
    job = controller.file_job
    assert job is not None
    job.wait()
    for _ in range(50):
        app.processEvents()
        if results:
            break
    assert results == ["HDA"]
    assert seen and seen[0] is not app.thread()
    assert not controller.busy
    controller.deleteLater()


def test_ai_controller_does_not_share_archive_busy_gate(app: Any) -> None:
    release = threading.Event()
    archive, ai = TaskController(), TaskController()
    assert archive.start(release.wait, lambda _: None)
    try:
        assert archive.busy
        assert ai.start(lambda: "", lambda _: None)
    finally:
        release.set()
        archive.drain()
        ai.drain()
        app.processEvents()
    archive.deleteLater()
    ai.deleteLater()


def test_preference_ai_settings_roundtrip(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from widgets.preference.preference import Preference

    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    wanted = AISettings("local", "http://localhost:11434", "llama3", "")
    preference = Preference()
    preference.data_dirpath = str(tmp_path)
    preference.ai_settings = wanted
    assert preference.ai_settings == wanted
    preference._Preference__pref_settings.save_cfg_dict_to_file()
    preference.close()
    reloaded = Preference()
    assert reloaded.ai_settings == wanted
    reloaded.close()


def test_preference_without_ai_key_loads_defaults(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from widgets.preference.preference import Preference

    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    save_json(
        tmp_path / "prefs.json",
        {
            public.Name.PreferenceUI.lineedit_data_dirpath: tmp_path.as_posix(),
            public.Name.PreferenceUI.lineedit_ffmpeg_dirpath: "",
        },
    )
    preference = Preference()
    assert preference.ai_settings == AISettings()
    assert preference.data_dirpath == tmp_path
    preference.close()


def test_preference_ai_fields_follow_backend(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from libs.ai_provider import FIELDS
    from widgets.preference.preference import Preference

    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    preference = Preference()
    edits = {
        "endpoint": preference.lineEdit__ai_endpoint,
        "model": preference.lineEdit__ai_model,
        "api_key_env": preference.lineEdit__ai_api_key_env,
    }
    preference.lineEdit__ai_model.setText("kept")
    for kind in KINDS:
        preference.ai_settings = AISettings(kind=kind, model="kept")
        assert {n for n, e in edits.items() if e.isEnabled()} == set(FIELDS[kind]), kind
    assert preference.lineEdit__ai_model.text() == "kept"
    assert preference.lineEdit__ai_api_key_env.placeholderText() == "OPENAI_API_KEY"
    preference.close()
