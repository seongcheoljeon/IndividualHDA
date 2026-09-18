"""Collection boundaries shared by pytest, local verification and CI."""

CORE = frozenset(
    {
        "test_ai_features.py",
        "test_annotations.py",
        "test_architecture.py",
        "test_database.py",
        "test_history_activity.py",
        "test_identity.py",
        "test_ollama.py",
        "test_path_updates.py",
        "test_scene_repository.py",
        "test_team_contracts.py",
        "test_record_boundaries.py",
    }
)
SERVER = frozenset({"test_team_library.py", "test_server_backup.py"})
POSTGRES = frozenset(
    {
        "test_team_library.py",
        "test_team_workspace.py",
        "test_main_team.py",
        "test_library_v2.py",
        "test_library_v2_migrations.py",
        "test_asset_copy.py",
        "test_server_backup.py",
        "test_core_refactoring.py",
        "test_version_tracking.py",
    }
)


def suite_for(filename: str) -> str:
    if filename in CORE:
        return "core"
    if filename in SERVER:
        return "server"
    return "qt"


def includes(suite: str, filename: str) -> bool:
    if suite == "all":
        return True
    if suite == "postgres":
        return filename in POSTGRES
    # Personal parametrizations of this shared contract require the Qt file lock.
    if suite == "qt" and filename == "test_team_library.py":
        return True
    return suite_for(filename) == suite
