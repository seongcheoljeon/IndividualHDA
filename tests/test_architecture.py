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
        "libs/database/media.py",
        "libs/database/metadata.py",
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


# --- ratchets added by the SOLID/SQL audit -----------------------------------
# Debt: raw reads of hda_key/hda_history without a live-row filter
# (rows.LIVE_ASSET_IDS / LIVE_HISTORY_IDS or an explicit deleted_at test),
# per module. Per-id lookups of a known-live asset are tolerated here; list
# reads must filter. Target: only the per-id ones.
SOFT_DELETE_UNFILTERED: dict[str, int] = {
    "libs/database/assets.py": 2,
    "libs/database/catalog.py": 3,
    "libs/database/history.py": 11,
    "libs/database/lifecycle.py": 3,
    "libs/database/metadata.py": 2,
    "libs/database/records.py": 2,
    "libs/database/sqlite_repository.py": 1,
}
# Debt: features reaching into another feature's underscore members through
# their bindings (self.bindings.x._y) or the team integration (self.library._y).
# Target: empty, once the bindings are typed as ports.
CROSS_FEATURE_PRIVATE: dict[str, int] = {}
# Debt: imports inside function bodies in libs/ and ihda_server/ (most hide an
# import cycle). Target: only the ones that defer optional dependencies.
LAZY_IMPORT_SITES: dict[str, int] = {
    "ihda_server.backup_cli": 4,
    "ihda_server.backup_files": 1,
    "ihda_server.backup_postgres": 2,
    "ihda_server.catalog": 2,
    "ihda_server.cli": 6,
    "ihda_server.database": 2,
    "ihda_server.migrations": 2,
    "ihda_server.queries": 1,
    "ihda_server.storage_lock": 2,
    "ihda_server.tracking": 1,
    "libs.ai_provider": 1,
    "libs.data_stream": 2,
    "libs.database.assets": 3,
    "libs.database.lifecycle": 1,
    "libs.database.session": 1,
    "libs.database.sqlite_repository": 5,
    "libs.database.tracking": 3,
    "libs.library_backups": 3,
    "libs.library_management": 5,
    "libs.operation_journal": 1,
    "libs.qt_helpers": 1,
    "libs.registration_recovery": 7,
    "libs.settings_store": 1,
    "libs.sqlite3_db_api": 3,
    "libs.team.client": 1,
    "libs.team.contracts": 2,
    "libs.team.copy_contract": 1,
    "libs.team.copy_destination": 2,
    "libs.team.copy_source": 1,
    "libs.team.panel_catalog": 1,
    "libs.team.pending": 3,
    "libs.team.registration_recovery": 3,
    "libs.version_compare": 2,
}
# Debt: LibraryRepository size and its methods without a production caller.
REPOSITORY_METHODS = 44
DEAD_REPOSITORY_METHODS: set[str] = set()
# Personal features branch on the team integration being active only in the
# composition root, which picks the LibraryPort adapter.
TEAM_ACTIVE_BRANCHES = 1


def _sql_reads_without_live_filter(tree: ast.AST) -> int:
    def raw(sql: str, formatted: list[str]) -> bool:
        return bool(
            re.search(r"\bSELECT\b", sql)
            and re.search(r"\b(FROM|JOIN)\s+hda_(key|history)\b", sql)
            and "deleted_at" not in sql
            and not any(name.startswith("LIVE_") for name in formatted)
        )

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            count += raw(node.value, [])
        elif isinstance(node, ast.JoinedStr):
            text = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
            names = [
                getattr(v.value, "id", "")
                for v in node.values
                if isinstance(v, ast.FormattedValue)
            ]
            count += raw(text, names)
    return count


def test_soft_delete_filter_sites_only_shrink() -> None:
    now = {}
    for path in sorted((ROOT / "libs" / "database").glob("*.py")):
        count = _sql_reads_without_live_filter(
            ast.parse(path.read_text(encoding="utf-8"))
        )
        if count:
            now[path.relative_to(ROOT).as_posix()] = count
    assert now == SOFT_DELETE_UNFILTERED, (
        "reads of hda_key/hda_history must apply rows.LIVE_ASSET_IDS / "
        f"LIVE_HISTORY_IDS (or update the constant when debt is paid): {now}"
    )


def test_cross_feature_private_access_only_shrinks() -> None:
    now = {}
    for folder in ("widgets/panel", "widgets/team_library"):
        for path in sorted((ROOT / folder).glob("*.py")):
            source = path.read_text(encoding="utf-8")
            count = len(re.findall(r"self\.bindings\.\w+(?:\(\))?\._\w+", source))
            count += len(re.findall(r"self\.library\._\w+", source))
            if count:
                now[".".join(path.with_suffix("").relative_to(ROOT).parts)] = count
    assert now == CROSS_FEATURE_PRIVATE, (
        f"expose the member on a port instead of reaching for _name: {now}"
    )


def test_lazy_import_sites_only_shrink() -> None:
    now = {}
    for module, tree in MODULES.items():
        if not module.startswith(("libs.", "ihda_server.")):
            continue
        count = 0
        for function in ast.walk(tree):
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                count += sum(
                    isinstance(node, (ast.Import, ast.ImportFrom))
                    for node in ast.walk(function)
                )
        if count:
            now[module] = count
    assert now == LAZY_IMPORT_SITES, (
        f"a function-level import usually hides a cycle; break it instead: {now}"
    )


def test_repository_protocol_only_shrinks_and_is_used() -> None:
    classes = {
        node.name: node
        for node in MODULES["libs.repository"].body
        if isinstance(node, ast.ClassDef)
    }
    protocol = classes["LibraryRepository"]
    roles = [protocol] + [
        classes[ast.unparse(base)]
        for base in protocol.bases
        if ast.unparse(base) in classes
    ]
    methods = {
        node.name
        for role in roles
        for node in role.body
        if isinstance(node, ast.FunctionDef)
    }
    assert len(methods) == REPOSITORY_METHODS, (
        f"LibraryRepository has {len(methods)} methods; split roles, do not grow it"
    )
    used = set()
    for module, tree in MODULES.items():
        if module in {"libs.repository", "libs.database.sqlite_repository"}:
            continue
        used.update(
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        )
    dead = methods - used
    assert dead == DEAD_REPOSITORY_METHODS, (
        f"repository methods without a production caller changed: {sorted(dead)}"
    )


def test_team_active_branches_only_shrink() -> None:
    now = sum(
        len(re.findall(r"team(?:\(\))?\.active", path.read_text(encoding="utf-8")))
        for path in (ROOT / "widgets" / "panel").glob("*.py")
    )
    assert now == TEAM_ACTIVE_BRANCHES, (
        "personal features should depend on a library port, not on team.active "
        f"(now {now})"
    )


def test_catalog_methods_cannot_bypass_project_authorization() -> None:
    """Only ihda_server.access touches the engine; reads and writes go through it."""
    for module in ("ihda_server.catalog", "ihda_server.queries"):
        for node in ast.walk(MODULES[module]):
            assert not (isinstance(node, ast.Attribute) and node.attr == "_engine"), (
                f"{module} reaches the engine directly; use reading()/writing()"
            )
