from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtCore, QtTest

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
        delete_model=lambda endpoint, model: installed.remove(model),
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
    marks = {
        dialog.tree.topLevelItem(row).text(0): dialog.tree.topLevelItem(row).text(1)
        for row in range(dialog.tree.topLevelItemCount())
    }
    assert marks["qwen3-vl:4b"] == "\u2713" and marks["gemma4:12b"] == ""
    assert dialog.download_button.text() == "Download"
    assert dialog.download_button.isDefault() and not dialog.use_button.isDefault()

    dialog.download()
    wait_tasks(app, dialog)  # pull
    wait_tasks(app, dialog)  # follow-up refresh
    assert dialog.progress_bar.value() == 100 and dialog.installed_list.count() == 2
    assert dialog.status.text() == "Download complete"
    assert dialog.use_button.isEnabled()
    # Installed now: the pull button turns into an update check and Enter applies.
    assert dialog.download_button.text() == "Update"
    assert dialog.use_button.isDefault() and not dialog.download_button.isDefault()

    def pull_up_to_date(
        endpoint: str, model: str, *, progress: Any, cancel: threading.Event
    ) -> bool:
        progress("pulling manifest", 0, 0)
        progress("pulling 1278394b6936", 7_600_000_000, 7_600_000_000)  # present
        progress("success", 0, 0)
        return True

    client.pull = pull_up_to_date
    dialog.download()
    assert dialog.status.text() == "Checking gemma4:12b for updates…"
    wait_tasks(app, dialog)
    wait_tasks(app, dialog)
    assert dialog.status.text() == "gemma4:12b is up to date"
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


def test_remove_installed_model_asks_first_then_refreshes(app: Any) -> None:
    installed = ["qwen3-vl:4b", "gemma4:12b"]
    dialog = LocalModelsDialog(client=fake_client("0.12.1", installed, 12.0))
    wait_tasks(app, dialog)
    assert not dialog.remove_button.isEnabled()
    dialog.installed_list.setCurrentRow(1)  # gemma4:12b (sorted by the client)
    assert dialog.remove_button.isEnabled()
    asked: list[str] = []
    dialog.confirm_remove = lambda model: asked.append(model) or False  # type: ignore[method-assign]
    dialog.remove_selected()
    assert asked == ["gemma4:12b"] and not dialog.tasks.busy
    dialog.confirm_remove = lambda model: True  # type: ignore[method-assign]
    dialog.remove_selected()
    wait_tasks(app, dialog)  # delete
    wait_tasks(app, dialog)  # refresh
    assert dialog.status.text() == "Removed gemma4:12b"
    assert dialog.installed_list.count() == 1 and installed == ["qwen3-vl:4b"]
    dialog.close()


def test_progress_survives_byte_counts_beyond_32_bits(app: Any) -> None:
    dialog = LocalModelsDialog(client=fake_client("0.12.1", [], None))
    wait_tasks(app, dialog)
    dialog.progress.emit("pulling abc", 1_200_000_000, 7_298_896_370)
    app.processEvents()
    assert dialog.progress_bar.value() == 16
    assert "1.1 GB / 6.8 GB" in dialog.status.text()
    dialog.close()


@pytest.mark.parametrize("operation", ["remove", "download"])
@pytest.mark.parametrize("close_before_idle", [False, True])
def test_followup_refresh_waits_for_controller_idle(
    app: Any, operation: str, close_before_idle: bool
) -> None:
    """Deliver completion before the worker stops, even across an event-loop turn."""
    client = fake_client("0.12.1", ["qwen3-vl:4b"], 12.0)
    probes: list[str] = []
    original_probe = client.installed_models

    def installed_models(endpoint: str) -> Any:
        probes.append(endpoint)
        return original_probe(endpoint)

    client.installed_models = installed_models
    dialog = LocalModelsDialog(client=client)
    wait_tasks(app, dialog)
    before = len(probes)
    started, release = threading.Event(), threading.Event()

    def worker() -> None:
        started.set()
        release.wait(3)

    try:
        assert dialog.tasks.start(worker, lambda result: None)
        assert started.wait(2)
        if operation == "remove":
            dialog._removed("qwen3-vl:4b")
        else:
            dialog._pull_transferred = True
            dialog._pulled(True)
        completion_status = dialog.status.text()
        if close_before_idle:
            dialog.reject()
        app.processEvents()  # a zero-delay refresh used to run too early here
        assert dialog.tasks.busy
        assert len(probes) == before
        assert dialog.status.text() == completion_status
        release.set()
        wait_tasks(app, dialog)
        assert len(probes) == before + (0 if close_before_idle else 1)
        assert dialog.status.text() == completion_status
    finally:
        release.set()
        dialog.shutdown()


def test_installed_model_can_be_applied_over_the_recommendation(app: Any) -> None:
    """Picking from the installed list must win over the auto-selected catalog row.

    A refresh preselects the recommended catalog model, and selected_model() reads
    the catalog before the installed list, so clicking an installed model left
    "Use as AI backend" disabled whenever the recommendation was not installed.
    """
    dialog = LocalModelsDialog(client=fake_client("0.12.1", ["qwen3-vl:4b"], 12.0))
    wait_tasks(app, dialog)
    recommended = dialog.selected_model()
    assert recommended and recommended != "qwen3-vl:4b", (
        "this test needs a recommendation that is not the installed model"
    )
    assert not dialog.use_button.isEnabled()

    dialog.installed_list.setCurrentRow(0)
    assert dialog.selected_model() == "qwen3-vl:4b"
    assert dialog.use_button.isEnabled()

    chosen: list[Any] = []
    dialog.settingsChosen.connect(chosen.append)
    dialog.use_selected()
    assert [settings.model for settings in chosen] == ["qwen3-vl:4b"]

    # And back: the catalog must win again when it is the one clicked.
    item = dialog.tree.topLevelItem(0)
    assert item is not None
    dialog.tree.setCurrentItem(item)
    assert dialog.selected_model() == item.data(0, QtCore.Qt.ItemDataRole.UserRole)
    dialog.close()
