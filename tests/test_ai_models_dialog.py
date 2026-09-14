from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtTest

from libs import ollama
from libs.ai_provider import AISettings
from widgets.ai_models.dialog import LocalModelsDialog


def wait_tasks(app: Any, dialog: Any) -> None:
    for _ in range(500):
        app.processEvents()
        if not dialog.tasks.busy:
            app.processEvents()
            return
        QtTest.QTest.qWait(10)
    raise AssertionError("Worker did not finish")


def fake_client(version: str | None, installed: list[str], vram: float | None) -> Any:
    def pull(
        endpoint: str, model: str, *, progress: Any, cancel: threading.Event
    ) -> bool:
        for done in (0, 50, 100):
            if cancel.is_set():
                return False
            progress("pulling", done, 100)
        progress("success", 0, 0)
        installed.append(model)
        return True

    return SimpleNamespace(
        DEFAULT_ENDPOINT=ollama.DEFAULT_ENDPOINT,
        DOWNLOAD_PAGE=ollama.DOWNLOAD_PAGE,
        RECOMMENDED=ollama.RECOMMENDED,
        endpoint_url=ollama.endpoint_url,
        choose_recommended=ollama.choose_recommended,
        install_hint=lambda: "winget install Ollama.Ollama",
        version=lambda endpoint: version,
        installed_models=lambda endpoint: [
            ollama.InstalledModel(name, 6_000_000_000) for name in installed
        ],
        detect_vram_gb=lambda: vram,
        pull=pull,
    )


def test_missing_server_shows_install_guidance(app: Any) -> None:
    dialog = LocalModelsDialog(client=fake_client(None, [], None))
    wait_tasks(app, dialog)
    assert dialog.install_box.isVisibleTo(dialog)
    assert "Not running" in dialog.server_status.text()
    assert not dialog.download_button.isEnabled() and not dialog.use_button.isEnabled()
    dialog.close()


def test_download_recommended_then_use(app: Any) -> None:
    installed = ["qwen3-vl:4b"]
    client = fake_client("0.12.1", installed, 12.0)
    chosen: list[AISettings] = []
    dialog = LocalModelsDialog("http://localhost:11434/", client=client)
    dialog.settingsChosen.connect(chosen.append)
    wait_tasks(app, dialog)
    assert "Ollama 0.12.1" in dialog.server_status.text()
    assert dialog.installed_list.count() == 1
    assert "GPU memory: 12" in dialog.vram_label.text()
    assert dialog.selected_model() == "gemma4:12b"  # preselected by VRAM
    assert dialog.download_button.isEnabled() and not dialog.use_button.isEnabled()

    dialog.download()
    wait_tasks(app, dialog)  # pull
    wait_tasks(app, dialog)  # follow-up refresh
    assert dialog.progress_bar.value() == 100 and dialog.installed_list.count() == 2
    assert dialog.use_button.isEnabled()
    dialog.use_selected()
    assert chosen == [
        AISettings(kind="local", endpoint="http://localhost:11434", model="gemma4:12b")
    ]

    dialog.custom.setText("qwen3-vl")  # bare names resolve to :latest, not installed
    assert not dialog.use_button.isEnabled()
    dialog.custom.setText("qwen3-vl:4b")
    assert dialog.use_button.isEnabled()
    dialog.close()


def test_close_during_download_cancels_and_finishes(app: Any) -> None:
    gate = threading.Event()
    seen_cancel: list[bool] = []

    def slow_pull(
        endpoint: str, model: str, *, progress: Any, cancel: threading.Event
    ) -> bool:
        gate.wait(2)
        seen_cancel.append(cancel.is_set())
        return not cancel.is_set()

    client = fake_client("0.12.1", ["qwen3-vl:8b"], None)
    client.pull = slow_pull
    dialog = LocalModelsDialog(client=client)
    wait_tasks(app, dialog)
    dialog.download()
    assert dialog.tasks.busy
    dialog.close()
    assert dialog.tasks.busy and dialog.cancel.is_set()
    gate.set()
    wait_tasks(app, dialog)
    assert seen_cancel == [True] and "cancelled" in dialog.status.text()


def test_preference_button_applies_settings_without_saving(
    app: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    import public
    from widgets.preference.preference import Preference

    monkeypatch.setattr(public.Paths, "json_pref_filepath", tmp_path / "prefs.json")
    monkeypatch.setattr(ollama, "version", lambda endpoint: "0.12.1")
    monkeypatch.setattr(
        ollama,
        "installed_models",
        lambda endpoint: [ollama.InstalledModel("gemma4:12b", 1)],
    )
    monkeypatch.setattr(ollama, "detect_vram_gb", lambda: 16.0)
    preference = Preference()
    preference.open_local_models()
    dialog = preference._Preference__local_models
    wait_tasks(app, dialog)
    dialog.use_selected()
    assert preference.ai_settings == AISettings(
        kind="local", endpoint="http://localhost:11434", model="gemma4:12b"
    )
    assert not (tmp_path / "prefs.json").exists()
    preference.shutdown()
    app.processEvents()
    preference.close()
