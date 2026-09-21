"""Personal and team adapters behind the panel's library port."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from widgets.panel.library_port import PersonalLibrary, TeamLibrary


def test_personal_library_leaves_forwarded_requests_to_the_panel(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    library = PersonalLibrary(
        database=lambda: None,
        writer=lambda: None,
        reload=lambda: calls.append("reload"),
        paths_changed=lambda: calls.append("paths"),
    )
    assert library.writable and library.owner and not library.busy
    assert library.supports_scene_records
    assert not library.register_nodes([]) and not library.import_drop(None)
    assert not library.remove_selected() and not library.play_video()
    assert not library.import_selected()
    assert not library.attach("video") and not library.context_menu(None)
    # Without a database file there is nothing to recover or manage.
    assert library.registration_recovery() is None
    assert library.management_gateway() is None
    assert library.copy_source(1) is None
    library.metadata_changed()
    library.metadata_dialog_closed()
    library.refresh()
    assert calls == ["paths", "reload", "reload"]


def test_team_library_forwards_requests_and_reports_the_role() -> None:
    calls: list[tuple[str, Any]] = []
    actions = SimpleNamespace(
        register_nodes=lambda nodes: calls.append(("register", nodes)),
        import_drop=lambda data: calls.append(("drop", data)),
        remove=lambda: calls.append(("remove", None)),
        context_menu=lambda point: calls.append(("menu", point)),
        history_menu=lambda point: calls.append(("history", point)),
        attach=lambda kind: calls.append(("attach", kind)),
        play_video=lambda: calls.append(("play", None)),
    )
    presenter = SimpleNamespace(refresh=lambda: calls.append(("refresh", None)))
    team = SimpleNamespace(
        writable=False,
        busy=True,
        project={"role": "owner"},
        presenter=presenter,
        actions=actions,
        show_status=lambda text: calls.append(("status", text)),
        download=lambda: calls.append(("download", None)),
    )
    library = TeamLibrary(team)  # type: ignore[arg-type]
    assert not library.writable and library.owner and library.busy
    assert not library.supports_scene_records
    assert library.copy_source(1) is None
    assert library.register_nodes(["n"]) and library.import_drop("d")
    assert library.remove_selected() and library.attach("thumbnail")
    assert (
        library.context_menu("p") and library.history_menu("h") and library.play_video()
    )
    library.metadata_changed()
    library.metadata_dialog_closed()
    assert calls == [
        ("register", ["n"]),
        ("drop", "d"),
        ("remove", None),
        ("attach", "thumbnail"),
        ("menu", "p"),
        ("history", "h"),
        ("play", None),
        ("refresh", None),
        ("status", ""),
    ]
    assert library.import_selected() and calls[-1] == ("download", None)
