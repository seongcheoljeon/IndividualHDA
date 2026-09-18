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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {"tests", "benchmarks", ".venv", "__pycache__"}
GENERATED = ("_rc.py",)

# Modules allowed to import hou/hdefereval at runtime (the host boundary).
HOST_BOUNDARY = {"libs.host", "libs.houdini_api"}
# Debt: modules that still import hou directly. Target: empty.
HOU_IMPORTERS: set[str] = set()
# Debt: modules that reach the god module `public` instead of its real homes.
PUBLIC_IMPORTERS: set[str] = set()

# libs modules that legitimately wrap Qt; everything else under libs/ is domain.
QT_LIBS = {
    "libs.asset_search",
    "libs.background_job",
    "libs.data_stream",
    "libs.debounce",
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
# Debt: direct SQLite facade use left in panel mixins, per module. Target: empty.
LOCAL_DB_SITES: dict[str, int] = {}


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
    offenders = {
        m
        for m, imp in IMPORTS.items()
        if "main" in imp and m not in {"main", "tools.dev_app"}
    }
    assert not offenders, sorted(offenders)


def test_public_importers_only_shrink() -> None:
    now = {m for m, imp in IMPORTS.items() if "public" in imp}
    assert now <= PUBLIC_IMPORTERS, (
        f"import from libs.keys/libs.paths instead: {sorted(now - PUBLIC_IMPORTERS)}"
    )
    assert now == PUBLIC_IMPORTERS, (
        f"debt paid, update PUBLIC_IMPORTERS: {sorted(PUBLIC_IMPORTERS - now)}"
    )


def test_panel_features_are_composed_and_have_explicit_bindings() -> None:
    feature_count = 0
    for module, tree in MODULES.items():
        if not module.startswith("widgets.panel."):
            continue
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            assert not cls.name.endswith("Mixin"), module
            if cls.name.endswith("Bindings"):
                feature_count += 1
                fields = [node for node in cls.body if isinstance(node, ast.AnnAssign)]
                assert fields, module
                for field in fields:
                    assert ast.unparse(field.annotation) not in {
                        "Any",
                        "IndividualHDA",
                    }, module
                    assert ast.unparse(field.target) not in {"window", "panel"}, module
    assert feature_count >= 15
    panel = next(
        node
        for node in MODULES["main"].body
        if isinstance(node, ast.ClassDef) and node.name == "IndividualHDA"
    )
    assert [ast.unparse(base) for base in panel.bases] == [
        "QtWidgets.QMainWindow",
        "MainWindowLayout",
    ]


def test_maintained_modules_are_type_checked() -> None:
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    for override in config["tool"]["mypy"].get("overrides", []):
        if override.get("ignore_errors"):
            assert all(module.endswith("_rc") for module in override["module"])


def test_direct_facade_sites_only_shrink() -> None:
    sites = {}
    for name in MODULES:
        if name.startswith("widgets.panel."):
            path = ROOT / (name.replace(".", "/") + ".py")
            count = len(re.findall(r"_db_api_wrap\(", path.read_text(encoding="utf-8")))
            if count:
                sites[name] = count
    assert sites == LOCAL_DB_SITES, f"route through LibraryRepository: {sites}"


def test_team_workspace_contract_and_presenter_stay_independent() -> None:
    forbidden = {
        "PySide6",
        "hou",
        "sqlalchemy",
        "fastapi",
        "urllib",
        "requests",
        "httpx",
    }
    for module in (
        "libs.team.contracts",
        "widgets.team_library.presenter",
        "widgets.panel.selection_presenter",
        "widgets.panel.sync_presenter",
        "ihda_server.service",
    ):
        assert not IMPORTS[module] & forbidden, module
    for module, imports in IMPORTS.items():
        if module.startswith("libs.team.") or module.startswith(
            "widgets.team_library."
        ):
            assert not imports & {"ihda_server", "sqlalchemy", "fastapi", "psycopg"}, (
                module
            )


def test_panel_selection_fields_are_not_written_by_ui_adapters() -> None:
    """Use SelectionState methods so identity, version and path cannot diverge."""
    offenders = []
    for name, tree in MODULES.items():
        if not name.startswith("widgets."):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Attribute):
                    continue
                if any(
                    isinstance(part, ast.Attribute) and part.attr == "_selection"
                    for part in ast.walk(target.value)
                ):
                    offenders.append(f"{name}:{node.lineno}")
    assert not offenders, offenders


def test_named_boundaries_do_not_regress_to_row_lists_or_whole_windows() -> None:
    for filename in ("libs/row_contracts.py", "libs/scene_record_input.py"):
        assert not (ROOT / filename).exists()
    for filename in (
        "widgets/asset_browser/integration.py",
        "widgets/asset_details/integration.py",
        "widgets/team_library/integration.py",
        "widgets/panel/scene_usage.py",
    ):
        source = (ROOT / filename).read_text()
        assert "IndividualHDA" not in source and "from main import" not in source
        tree = ast.parse(source)
        assert not any(
            isinstance(node, ast.Attribute)
            and node.attr in {"window", "_window", "_services"}
            for node in ast.walk(tree)
        )
    for filename in (
        "libs/database/assets.py",
        "libs/database/history.py",
        "libs/database/nodes.py",
        "libs/database/records.py",
    ):
        tree = ast.parse((ROOT / filename).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not (
                    "?" in node.value
                    and re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", node.value)
                )
    for filename in (
        "model/ihda_table_model.py",
        "model/ihda_history_model.py",
        "model/ihda_record_model.py",
        "model/ihda_inside_model.py",
    ):
        source = (ROOT / filename).read_text()
        assert "self.__keys" not in source and "self.__headers" not in source


def test_scene_ui_does_not_open_storage_connections() -> None:
    tree = ast.parse((ROOT / "widgets/panel/scene_usage.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(
                ("libs.database", "libs.sqlite3_db_api")
            )


def test_qobject_panel_features_do_not_shadow_qt_api() -> None:
    """A method named like a QObject member hides Qt's own and breaks wiring.

    PanelAIActions.connect() shadowed QObject.connect, which PySide6 calls with
    four arguments to hook up a signal: the panel failed to start in Houdini.
    Houdini ships PySide6 6.5.3 while the tests run on 6.11.2, which tolerates
    the shadowing -- so only a static check catches this.
    """
    from PySide6 import QtCore

    reserved = {name for name in dir(QtCore.QObject) if not name.startswith("__")}
    offenders: dict[str, list[str]] = {}
    for module, tree in MODULES.items():
        if not module.startswith("widgets.panel."):
            continue
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            bases = {ast.unparse(base) for base in cls.bases}
            if not bases & {"QtCore.QObject", "QObject"}:
                continue
            clashes = sorted(
                node.name
                for node in cls.body
                if isinstance(node, ast.FunctionDef) and node.name in reserved
            )
            if clashes:
                offenders[f"{module}.{cls.name}"] = clashes
    assert not offenders, f"these hide Qt's own members: {offenders}"
