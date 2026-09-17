"""Disposable, clearly identified data for the standalone development window."""

from __future__ import annotations

from pathlib import Path

from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.repository import RegistrationPayload
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def create_sample_library(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=False)
    database = root / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("developer")
    for name, category in (
        ("SampleWater", "sop"),
        ("SampleRock", "sop"),
        ("SampleLight", "obj"),
    ):
        directory = root / category / name
        directory.mkdir(parents=True)
        (directory / (name + ".hda")).write_text(
            "Development sample; not a Houdini asset.\n", encoding="utf-8"
        )
        payload = RegistrationPayload(
            user="developer",
            node_name=name,
            node_path="/obj/" + name,
            version="1.0",
            hda_dirpath=directory,
            hda_filename=name + ".hda",
            type_name="sample",
            cate_name=category,
            def_desc="Development sample",
            is_network=False,
            is_sub_network=False,
            type_path_lst=("Sop/box",),
            cate_path_lst=("Sop",),
            icon_path_lst=(
                "SOP",
                "box",
            ),
            input_conn=(),
            output_conn=(),
            hou_version="21.0",
            hou_license="commercial",
            operating_system="Development",
            hip_filename="sample.hip",
            hip_dirpath=root,
            sf=1,
            ef=24,
            fps=24.0,
            thumb_dirpath=directory,
            thumb_filename="preview.png",
            registered_at="2026-01-01 00:00:00",
        )
        result = repository.register_asset(payload)
        repository.set_note(
            result.asset.hda_id, "Disposable sample for UI development."
        )
        repository.set_tags(result.asset.hda_id, ["sample", category])
    return database
