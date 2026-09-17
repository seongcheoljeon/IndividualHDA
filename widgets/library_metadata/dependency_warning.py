"""One concise warning shared by personal, team and trash commands."""

from pathlib import Path
from typing import Any

from PySide6 import QtWidgets


def dependency_message(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    names = [
        f"{row['source_version']['name']} ({row['source_version']['version']})"
        for row in rows[:8]
    ]
    suffix = "\nMore references are listed in Version details." if len(rows) > 8 else ""
    return (
        "\n\nReferenced by:\n"
        + "\n".join(names)
        + suffix
        + "\nThese references may stop working. You can still continue."
    )


def confirm_local_dependencies(
    window: QtWidgets.QWidget, item: dict[str, Any], *, database: Path | None
) -> bool:
    from libs.library_management import LocalManagement

    if database is None:
        return True
    rows = LocalManagement(database).dependents(item)
    return (
        not rows
        or QtWidgets.QMessageBox.question(
            window,
            "Dependent assets",
            "Continue moving this item to Trash?" + dependency_message(rows),
        )
        == QtWidgets.QMessageBox.StandardButton.Yes
    )
