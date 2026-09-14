"""Architecture rules the code base must keep as it grows.

Two kinds of checks:
- layering (hard rules): the domain layer has no Qt/HOM, only the host boundary
  imports ``hou``, nothing imports ``main``.
- ratchets: sets that may only shrink. Removing an entry is a deliberate edit
  here; adding one fails the build. Update the constant when you pay the debt.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {"tests", "benchmarks", ".venv", "__pycache__"}
GENERATED = ("_ui.py", "_rc.py")

# Modules allowed to import hou/hdefereval at runtime (the host boundary).
HOST_BOUNDARY = {"libs.host", "libs.houdini_api"}
# Debt: modules that still import hou directly. Target: empty.
HOU_IMPORTERS: set[str] = set()
# Debt: modules that reach the god module `public` instead of its real homes.
PUBLIC_IMPORTERS = {
    "libs.houdini_api",
    "libs.ihda_icons",
    "libs.ihda_system",
    "main",
    "model.ihda_category_model",
    "model.ihda_history_model",
    "model.ihda_inside_model",
    "model.ihda_list_model",
    "model.ihda_record_model",
    "model.ihda_table_model",
    "ui_settings",
    "view.ihda_history_view",
    "view.ihda_inside_view",
    "view.ihda_list_view",
    "view.ihda_record_view",
    "view.ihda_table_view",
    "widgets.detail_view.detail_view",
    "widgets.make_video_info.make_video_info",
    "widgets.panel.ai_actions",
    "widgets.panel.asset_management",
    "widgets.panel.asset_registration",
    "widgets.panel.bootstrap",
    "widgets.panel.context_menus",
    "widgets.panel.host_callbacks",
    "widgets.panel.houdini_actions",
    "widgets.panel.library_queries",
    "widgets.panel.media_actions",
    "widgets.panel.model_binding",
    "widgets.panel.notes",
    "widgets.panel.presentation",
    "widgets.panel.selection",
    "widgets.preference.preference",
    "widgets.preference.preference_ui_settings",
    "widgets.video_player.video_player",
    "widgets.video_player.video_ui_settings",
    "widgets.web_view.web_ui_settings",
    "widgets.web_view.web_view",
}
# libs modules that legitimately wrap Qt; everything else under libs/ is domain.
QT_LIBS = {
    "libs.asset_search",
    "libs.background_job",
    "libs.data_stream",
    "libs.debounce",
    "libs.drag_payload",
    "libs.dragdrop_overlay",
    "libs.ihda_icons",
    "libs.loading_indicator",
    "libs.log_handler",
    "libs.media_playlist",
    "libs.note_syntax",
    "libs.operation_journal",
    "libs.process_job",
    "libs.qt_helpers",
    "libs.task_controller",
    "libs.thumbnail_cache",
    "libs.version_compare",
}
# Debt: panel attributes written by more than one mixin (main.py initialises them).
SHARED_PANEL_STATE = {
    "_ihda_list_model",
    "_ihda_list_proxy_model",
    "_ihda_table_model",
    "_ihda_table_proxy_model",
    "_library",
    "_repository",
    "_selection",
}
# Debt: direct SQLite facade use left in panel mixins, per module. Target: empty.
LOCAL_DB_SITES = {
    "widgets.panel.asset_management": 8,
    "widgets.panel.asset_registration": 1,
    "widgets.panel.bootstrap": 1,
    "widgets.panel.context_menus": 7,
    "widgets.panel.houdini_actions": 1,
    "widgets.panel.media_actions": 1,
    "widgets.panel.notes": 1,
    "widgets.panel.selection": 2,
}


def production_modules() -> dict[str, ast.Module]:
    result = {}
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_PARTS for part in path.parts) or path.name.endswith(
            GENERATED
        ):
            continue
        name = ".".join(path.with_suffix("").relative_to(ROOT).parts)
        result[name] = ast.parse(path.read_text(encoding="utf-8"))
    return result


def runtime_imports(tree: ast.AST) -> set[str]:
    """Top-level package names imported at runtime; TYPE_CHECKING blocks excluded."""
    names: set[str] = set()

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if (
                isinstance(child, ast.If)
                and isinstance(child.test, ast.Name)
                and child.test.id == "TYPE_CHECKING"
            ):
                for other in child.orelse:
                    visit(other)
                continue
            if isinstance(child, ast.Import):
                names.update(alias.name.split(".")[0] for alias in child.names)
            elif isinstance(child, ast.ImportFrom) and child.module:
                names.add(child.module.split(".")[0])
            visit(child)

    visit(tree)
    return names


MODULES = production_modules()
IMPORTS = {name: runtime_imports(tree) for name, tree in MODULES.items()}


def test_only_the_host_boundary_imports_hou() -> None:
    offenders = {m for m, imp in IMPORTS.items() if imp & {"hou", "hdefereval"}}
    offenders -= HOST_BOUNDARY
    assert offenders == HOU_IMPORTERS, (
        "hou importers changed; route HOM calls through libs.houdini_api "
        f"(new: {sorted(offenders - HOU_IMPORTERS)}, paid: {sorted(HOU_IMPORTERS - offenders)})"
    )


def test_domain_libs_have_no_qt() -> None:
    libs = {m for m in MODULES if m.startswith("libs.")}
    offenders = {m for m in libs - QT_LIBS - HOST_BOUNDARY if "PySide6" in IMPORTS[m]}
    assert not offenders, f"domain modules must not import Qt: {sorted(offenders)}"
    qt_now = {m for m in libs if "PySide6" in IMPORTS[m]}
    assert qt_now <= QT_LIBS, f"new Qt use in libs: {sorted(qt_now - QT_LIBS)}"


def test_nothing_imports_main() -> None:
    offenders = {m for m, imp in IMPORTS.items() if "main" in imp and m != "main"}
    assert not offenders, sorted(offenders)


def test_public_importers_only_shrink() -> None:
    now = {m for m, imp in IMPORTS.items() if "public" in imp}
    assert now <= PUBLIC_IMPORTERS, (
        f"import from libs.keys/libs.paths instead: {sorted(now - PUBLIC_IMPORTERS)}"
    )
    assert now == PUBLIC_IMPORTERS, (
        f"debt paid, update PUBLIC_IMPORTERS: {sorted(PUBLIC_IMPORTERS - now)}"
    )


def test_shared_panel_state_only_shrinks() -> None:
    writers: dict[str, set[str]] = defaultdict(set)
    for name, tree in MODULES.items():
        if not name.startswith("widgets.panel."):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    for sub in ast.walk(target):
                        if (
                            isinstance(sub, ast.Attribute)
                            and isinstance(sub.value, ast.Name)
                            and sub.value.id == "self"
                            and sub.attr.startswith("_")
                        ):
                            writers[sub.attr].add(name)
    shared = {attr for attr, owners in writers.items() if len(owners) > 1}
    assert shared == SHARED_PANEL_STATE, (
        f"new multi-writer attributes: {sorted(shared - SHARED_PANEL_STATE)}; "
        f"paid: {sorted(SHARED_PANEL_STATE - shared)}"
    )


def test_direct_facade_sites_only_shrink() -> None:
    sites = {}
    for name in MODULES:
        if (
            name.startswith("widgets.panel.")
            and name != "widgets.panel.library_queries"
        ):
            path = ROOT / (name.replace(".", "/") + ".py")
            count = len(re.findall(r"_db_api_wrap\(", path.read_text(encoding="utf-8")))
            if count:
                sites[name] = count
    assert sites == LOCAL_DB_SITES, f"route through LibraryRepository: {sites}"
