"""Scene-record cleanup commits before display and preserves failed records."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from PySide6 import QtCore, QtWidgets
from test_mutation_workflow import mutation_panel as mutation_panel

from libs.scene_record_cleanup import SceneRecordCleanup, SceneRecordFiles, file_exists
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def test_cleanup_preserves_inaccessible_records_and_deduplicates_deletion(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "present.hda"
    existing.write_text("unchanged")
    missing = tmp_path / "missing.hip"
    inaccessible = tmp_path / "restricted.hda"
    delete = Mock(side_effect=lambda identity: identity != 3)
    repository = SimpleNamespace(
        scene_record_files=lambda user: [
            SceneRecordFiles(1, missing, missing),
            SceneRecordFiles(2, missing, inaccessible),
            SceneRecordFiles(3, existing, missing),
            SceneRecordFiles(4, existing, existing),
        ],
        delete_scene_record=delete,
    )

    def exists(path: Path) -> bool:
        if path == inaccessible:
            raise PermissionError("restricted")
        return file_exists(path)

    result = SceneRecordCleanup(repository, exists).cleanup("tester")
    assert result.deleted == (1,)
    assert {identity for identity, _ in result.failed} == {2, 3}
    assert [call.args[0] for call in delete.call_args_list] == [1, 3]
    assert existing.read_text() == "unchanged"
    assert not missing.exists()


def seed_records(panel: Any, tmp_path: Path) -> list[int]:
    asset = panel.session.repository.list_assets()[0]
    with SQLite3DatabaseAPI(panel.queries._db_filepath) as db:
        for index in range(3):
            hip = tmp_path / f"scene{index}.hip"
            hip.write_text("scene")
            db.insert_hda_node_location_record(
                hda_key_id=asset.hda_id,
                hip_filename=hip.name,
                hip_dirpath=tmp_path,
                hda_filename=asset.hda_filename,
                hda_dirpath=asset.hda_dirpath,
                parent_node_path="/obj",
                node_type="box",
                node_cate="sop",
                node_name="same-name",
                node_ver=asset.hda_version,
                hou_version="21",
                hou_license="commercial",
                operating_sys="Linux",
                sf=1,
                ef=24,
                fps=24,
            )
        tree = db.get_hda_node_location_record()
    panel.models.record_model.replace_record_data(tree)
    panel.views.record.expandAll()
    return [
        record.record_id
        for record in panel.session.repository.scene_record_files(panel.session.user)
    ]


def test_filtered_parent_selection_keeps_failed_database_record(
    mutation_panel: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = mutation_panel
    identities = seed_records(panel, tmp_path)
    model, proxy = panel.models.record_model, panel.models.record_proxy_model
    assert len(identities) == 3
    before = model.record_data
    proxy.setFilterRegularExpression("same-name")
    proxy.sort(0, QtCore.Qt.SortOrder.DescendingOrder)
    root = proxy.index(0, 0)
    assert set(model.selected_record_ids(root)) == set(identities)
    assert model.record_data == before
    original = panel.session.repository.delete_scene_record

    def delete(identity: int) -> bool:
        if identity == identities[1]:
            raise RuntimeError("database locked")
        return original(identity)

    monkeypatch.setattr(panel.session.repository, "delete_scene_record", delete)
    errors: list[str] = []
    monkeypatch.setattr(panel.management, "show_command_error", errors.append)
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "exec",
        lambda self: QtWidgets.QMessageBox.StandardButton.No,
    )
    panel.management._remove_selected_record_item(root)
    assert len(panel.session.repository.scene_record_files(panel.session.user)) == 3
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "exec",
        lambda self: QtWidgets.QMessageBox.StandardButton.Yes,
    )
    panel.management._remove_selected_record_item(root)
    assert [
        r.record_id
        for r in panel.session.repository.scene_record_files(panel.session.user)
    ] == [identities[1]]
    assert model.selected_record_ids(model.index(0, 0)) == (identities[1],)
    assert "database locked" in errors[-1]
    assert len(list(tmp_path.glob("scene*.hip"))) == 3


def test_committed_delete_reloads_after_display_failure(
    mutation_panel: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = mutation_panel
    identities = seed_records(panel, tmp_path)
    model = panel.models.record_model
    result = SceneRecordCleanup(panel.session.repository).delete(
        [identities[0], identities[0]]
    )
    monkeypatch.setattr(
        model, "remove_record_ids", Mock(side_effect=RuntimeError("view failed"))
    )
    errors: list[str] = []
    monkeypatch.setattr(panel.management, "show_command_error", errors.append)
    panel.management._apply_scene_record_cleanup(result)
    assert set(model.selected_record_ids(model.index(0, 0))) == set(identities[1:])
    assert "Records were deleted" in errors[0]
    assert len(panel.session.repository.scene_record_files(panel.session.user)) == 2


def test_confirmation_uses_ids_captured_before_a_model_reset(
    mutation_panel: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = mutation_panel
    identities = seed_records(panel, tmp_path)
    model, proxy = panel.models.record_model, panel.models.record_proxy_model
    wanted = identities[0]

    def find(parent: QtCore.QModelIndex) -> QtCore.QModelIndex:
        for row in range(proxy.rowCount(parent)):
            index = proxy.index(row, 0, parent)
            if index.data(model.record_id_role) == wanted:
                return index
            child = find(index)
            if child.isValid():
                return child
        return QtCore.QModelIndex()

    index = find(QtCore.QModelIndex())
    assert index.isValid()

    def confirm(dialog: Any) -> Any:
        # A nested event loop can process a model reset before confirmation returns.
        model.remove_record_ids((wanted,))
        return QtWidgets.QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", confirm)
    panel.management._remove_selected_record_item(index)
    assert {
        r.record_id
        for r in panel.session.repository.scene_record_files(panel.session.user)
    } == set(identities[1:])
