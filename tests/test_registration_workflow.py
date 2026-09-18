from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support.personal import payload

from libs.asset_lifecycle import LocalAssetLifecycle
from libs.asset_registration import RegistrationService
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.repository import LibraryError, RegistrationPayload
from libs.sqlite3_db_api import SQLite3DatabaseAPI


class Capture:
    def __init__(self, failure: str = "") -> None:
        self.failure = failure

    def asset(self, destination: Path) -> None:
        destination.write_bytes(b"captured asset")
        if self.failure == "asset":
            raise RuntimeError("asset capture failed")

    def thumbnail(self, destination: Path) -> None:
        if self.failure == "no viewport":
            return
        destination.write_bytes(b"captured thumbnail")
        if self.failure == "thumbnail":
            raise RuntimeError("thumbnail capture failed")


def setup(
    tmp_path: Path, version: str = "1.0"
) -> tuple[Any, RegistrationPayload, RegistrationService]:
    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    request = replace(
        payload(tmp_path, "Water", version),
        hda_filename=f"Water_{version}.hda",
        thumb_filename=f"Water_{version}.jpg",
    )
    return (
        repository,
        request,
        RegistrationService(LocalAssetLifecycle(repository, SimpleNamespace())),
    )


@pytest.mark.parametrize("failure", ["asset", "thumbnail"])
def test_capture_failure_leaves_no_final_files_and_can_retry(
    tmp_path: Path, failure: str
) -> None:
    repository, request, service = setup(tmp_path)
    with pytest.raises(RuntimeError, match="capture failed"):
        service.register(request, Capture(failure))
    assert not (request.hda_dirpath / request.hda_filename).exists()
    assert list(request.hda_dirpath.glob(".ihda-registration-*"))
    recovery = repository.registration_recovery()
    failed = next(job for job in recovery.jobs() if job["phase"] != "committed")
    recovery.discard(failed["id"])
    assert not list(request.hda_dirpath.glob(".ihda-registration-*"))
    assert repository.list_assets() == []
    result = service.register(request, Capture())
    assert result.asset.hda_version == "1.0"
    assert len(repository.histories(result.asset.hda_id, owner="tester")) == 1


@pytest.mark.parametrize("new_version", [False, True])
def test_database_failure_retains_attempt_files_and_retry_commits_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, new_version: bool
) -> None:
    repository, request, service = setup(tmp_path)
    asset_id = None
    if new_version:
        asset_id = service.register(request, Capture()).asset.hda_id
        request = replace(
            request,
            version="1.1",
            hda_filename="Water_1.1.hda",
            thumb_filename="Water_1.1.jpg",
        )
    operation_name = "_add_version" if new_version else "_register_asset"
    original = getattr(repository, operation_name)

    def fail(*args: Any) -> Any:
        raise LibraryError("injected database failure")

    monkeypatch.setattr(repository, operation_name, fail)
    with pytest.raises(LibraryError, match="injected"):
        service.register(request, Capture(), asset_id)
    assert (request.hda_dirpath / request.hda_filename).exists()
    assert (request.thumb_dirpath / request.thumb_filename).exists()
    assert (request.hda_dirpath / "Water.hda").read_bytes() == b"hda"
    if new_version:
        assert (request.hda_dirpath / "Water_1.0.hda").is_file()
        assert repository.list_assets()[0].hda_version == "1.0"
    monkeypatch.setattr(repository, operation_name, original)
    recovery = repository.registration_recovery()
    failed = next(job for job in recovery.jobs() if job["phase"] == "published")
    writer = LocalAssetLifecycle(repository, SimpleNamespace())
    result = recovery.retry(failed["id"], writer)
    assert recovery.retry(failed["id"], writer).history_id == result.history_id
    assert len(repository.histories(result.asset.hda_id, owner="tester")) == (
        2 if new_version else 1
    )
    with pytest.raises(LibraryError, match="already exists"):
        service.register(request, Capture(), asset_id)
    assert (
        request.hda_dirpath / request.hda_filename
    ).read_bytes() == b"captured asset"


def test_publication_race_preserves_competing_file(tmp_path: Path) -> None:
    repository, request, service = setup(tmp_path)

    class RacingCapture(Capture):
        def thumbnail(self, destination: Path) -> None:
            super().thumbnail(destination)
            (request.thumb_dirpath / request.thumb_filename).write_bytes(
                b"other writer"
            )

    from libs.repository import LibraryConflict

    with pytest.raises(LibraryConflict, match="ownership"):
        service.register(request, RacingCapture())
    assert (request.hda_dirpath / request.hda_filename).exists()
    assert (
        request.thumb_dirpath / request.thumb_filename
    ).read_bytes() == b"other writer"
    assert not repository.list_assets()


def test_optional_thumbnail_and_postcommit_error_preserve_registered_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, request, service = setup(tmp_path)
    original = repository._register_asset

    def committed_but_failed(request: RegistrationPayload) -> Any:
        original(request)
        raise LibraryError("postcommit error")

    monkeypatch.setattr(repository, "_register_asset", committed_but_failed)
    with pytest.raises(LibraryError, match="postcommit"):
        service.register(request, Capture("no viewport"))
    assert len(repository.list_assets()) == 1
    assert (request.hda_dirpath / request.hda_filename).is_file()
    assert not (request.thumb_dirpath / request.thumb_filename).exists()


def test_cleanup_verification_failure_preserves_original_error_and_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, request, service = setup(tmp_path)

    def fail(*args: Any) -> Any:
        raise LibraryError("original failure")

    def unavailable(*args: Any) -> Any:
        raise OSError("cannot inspect references")

    monkeypatch.setattr(repository, "_register_asset", fail)
    monkeypatch.setattr(repository, "_session", unavailable)
    with pytest.raises(LibraryError, match="original failure"):
        service.register(request, Capture())
    assert (request.hda_dirpath / request.hda_filename).is_file()


def test_display_and_render_flags_restore_after_registration_error() -> None:
    from widgets.panel.asset_registration import PanelAssetRegistration

    state = {"display": True, "render": False}
    node = SimpleNamespace(
        isDisplayFlagSet=lambda: state["display"],
        isRenderFlagSet=lambda: state["render"],
        setDisplayFlag=lambda value: state.update(display=value),
        setRenderFlag=lambda value: state.update(render=value),
    )

    def fail(node: Any) -> bool:
        state.update(display=False, render=True)
        raise RuntimeError("capture failed")

    with pytest.raises(RuntimeError):
        PanelAssetRegistration._node_declare(
            SimpleNamespace(_declare_registration=fail), node
        )
    assert state == {"display": True, "render": False}


def test_overlay_closes_after_batch_error() -> None:
    from widgets.panel.asset_registration import PanelAssetRegistration

    closed: list[bool] = []

    def fail(*args: Any) -> None:
        raise RuntimeError("batch error")

    owner = SimpleNamespace(
        _register_dropped_nodes=fail,
        bindings=SimpleNamespace(
            presentation=SimpleNamespace(
                dragdrop_overlay_close=lambda: closed.append(True)
            )
        ),
    )
    with pytest.raises(RuntimeError):
        PanelAssetRegistration._make_houdini_node_to_ihda_node(owner, [], 0)
    assert closed == [True]


@pytest.mark.parametrize("new_version", [False, True])
def test_history_insert_failure_rolls_back_database_and_allows_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, new_version: bool
) -> None:
    repository, request, service = setup(tmp_path)
    asset_id = None
    if new_version:
        asset_id = service.register(request, Capture()).asset.hda_id
        request = replace(
            request,
            version="1.1",
            hda_filename="Water_1.1.hda",
            thumb_filename="Water_1.1.jpg",
        )
    with monkeypatch.context() as patch:
        patch.setattr(
            SQLite3DatabaseAPI, "insert_hda_history", lambda *args, **kwargs: None
        )
        with pytest.raises(LibraryError):
            service.register(request, Capture(), asset_id)
    assert (request.hda_dirpath / request.hda_filename).exists()
    assets = repository.list_assets()
    assert len(assets) == int(new_version)
    if assets:
        assert assets[0].hda_version == "1.0"
        assert len(repository.histories(asset_id, owner="tester")) == 1
    recovery = repository.registration_recovery()
    failed = next(job for job in recovery.jobs() if job["phase"] == "published")
    writer = LocalAssetLifecycle(repository, SimpleNamespace())
    result = recovery.retry(failed["id"], writer)
    assert recovery.retry(failed["id"], writer).history_id == result.history_id
    assert len(repository.histories(result.asset.hda_id, owner="tester")) == (
        2 if new_version else 1
    )


def test_committed_display_failure_does_not_repeat_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs import houdini_api
    from widgets.asset_lifecycle.presenter import AssetCommandPresenter
    from widgets.panel.asset_registration import PanelAssetRegistration

    repository, request, service = setup(tmp_path)
    gateway = LocalAssetLifecycle(repository, SimpleNamespace())
    errors: list[str] = []
    reloaded: list[bool] = []
    owner = SimpleNamespace(
        _repository=repository,
        _services=SimpleNamespace(
            lifecycle=lambda *args: gateway,
            names=None,
            registration=lambda writer: service,
            host_capture=None,
        ),
        show_command_error=errors.append,
        reload_library=lambda: reloaded.append(True),
    )
    owner.bindings = SimpleNamespace(
        session=SimpleNamespace(
            repository=repository, require_repository=lambda: repository
        ),
        services=owner._services,
        management=owner,
        reload_library=owner.reload_library,
    )
    owner._asset_commands = lambda: AssetCommandPresenter(owner, gateway)
    monkeypatch.setattr(houdini_api.HoudiniAPI, "find_node", lambda path: object())
    monkeypatch.setattr(
        "widgets.panel.asset_registration.HoudiniRegistrationCapture",
        lambda *args: Capture(),
    )

    def broken_display(result: Any) -> None:
        raise RuntimeError("model unavailable")

    assert PanelAssetRegistration._register_captured_asset(
        owner, request, None, broken_display
    )
    assert len(repository.list_assets()) == 1
    assert reloaded == [True] and "Asset saved" in errors[0]


def test_registration_job_insert_survives_added_database_column(tmp_path: Path) -> None:
    import sqlite3

    repository, request, service = setup(tmp_path)
    with sqlite3.connect(repository.db_filepath) as database:
        database.execute(
            "ALTER TABLE registration_jobs ADD COLUMN extension TEXT DEFAULT 'kept'"
        )
    result = service.register(request, Capture())
    assert result.asset.hda_name == "Water"
    with sqlite3.connect(repository.db_filepath) as database:
        assert (
            database.execute("SELECT extension FROM registration_jobs").fetchone()[0]
            == "kept"
        )


def test_staged_capture_paths_keep_the_destination_suffix(tmp_path: Path) -> None:
    """Houdini's flipbook picks its image format from the suffix.

    Staging the thumbnail as a bare "thumbnail" made the host write nothing, so
    registration committed without one and only a manual update produced a file.
    """
    _, request, service = setup(tmp_path)
    staged: list[Path] = []

    class Recorder(Capture):
        def asset(self, destination: Path) -> None:
            staged.append(destination)
            super().asset(destination)

        def thumbnail(self, destination: Path) -> None:
            staged.append(destination)
            super().thumbnail(destination)

    service.register(request, Recorder())
    assert [path.name for path in staged] == [
        request.hda_filename,
        request.thumb_filename,
    ]
    assert (request.thumb_dirpath / request.thumb_filename).is_file()
