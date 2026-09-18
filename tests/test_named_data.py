from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import pytest
from support.personal import payload

from libs.archive_policy import ArchiveLimits
from libs.archive_service import extract_archive
from libs.asset_contracts import HistoryData
from libs.browser_search import SearchPolicy
from libs.database.policy import SQLitePolicy
from libs.database.rows import history_record, named_query, require_fields
from libs.database.sqlite_repository import SqliteLibraryRepository
from libs.record_codec import decode_record, record_document
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from widgets.panel.policy import PanelPolicy


def test_named_read_preserves_connection_and_rejects_ambiguous_columns() -> None:
    with sqlite3.connect(":memory:") as connection:
        cursor = connection.cursor()
        row = named_query(
            connection, "SELECT 3 AS revision, 'artist' AS user_id"
        ).fetchone()
        assert row["user_id"] == "artist" and row["revision"] == 3
        assert connection.row_factory is None
        assert cursor.execute("SELECT 1, 2").fetchone() == (1, 2)
        with pytest.raises(ValueError, match="unique"):
            named_query(connection, "SELECT 1 AS id, 2 AS ID")
        with pytest.raises(KeyError):
            require_fields(dict(row), ("missing",))


def test_repository_results_survive_reordered_sql_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from libs.database import assets, history, nodes, records

    database = tmp_path / "ihda.db"
    with SQLite3DatabaseAPI(database):
        pass
    repository = SqliteLibraryRepository(database)
    repository.ensure_user("tester")
    result = repository.register_asset(payload(tmp_path, "한글"))
    expected_assets = repository.list_assets("tester")
    expected_history = repository.histories(None, "tester")

    def reordered(connection: Any, sql: str, parameters: Any = ()) -> Any:
        cursor = named_query(connection, sql, parameters)
        fields = [column[0] for column in cursor.description]
        cursor.close()
        projection = ",".join(
            '"' + name.replace('"', '""') + '"' for name in reversed(fields)
        )
        return named_query(connection, f"SELECT {projection} FROM ({sql})", parameters)

    for module in (assets, history, records, nodes):
        monkeypatch.setattr(module, "named_query", reordered)
    assert repository.list_assets("tester") == expected_assets
    assert repository.histories(None, "tester") == expected_history
    from libs.asset_contracts import NodeConnection

    with SQLite3DatabaseAPI(database) as db:
        identity = db.get_hou_node_info_id(result.asset.hda_id)
        connection = NodeConnection(
            port=2, node_name="upstream", node_type="box", peer_port=5
        )
        assert db.insert_houdini_node_input_connect_info(identity, (connection,)) == 1
        assert db.get_houdini_node_input_connect_info(identity) == (connection,)
    assert repository.node_connections(result.asset.hda_id).inputs == (connection,)
    with SQLite3DatabaseAPI(database) as db:
        assert (
            db.insert_hda_node_location_record(
                hda_key_id=result.asset.hda_id,
                hip_filename="scene.hip",
                hip_dirpath=tmp_path,
                hda_filename="한글.hda",
                hda_dirpath=tmp_path,
                parent_node_path="/obj",
                node_type="geo",
                node_cate="sop",
                node_name="한글",
                node_ver="1.0",
                hou_version="21",
                hou_license="commercial",
                operating_sys="linux",
                sf=1,
                ef=24,
                fps=24,
            )
            == 1
        )
        record = db.get_only_detailview_record_data(db.get_last_insert_id)
        assert record.node_name == "한글" and record.hip_dirpath == tmp_path
        assert (
            db.get_update_before_data(result.asset.hda_id).hda_ctime
            == expected_assets[0].hda_ctime
        )
        assert (
            db.get_hda_filepath(result.asset.hda_id)
            == expected_assets[0].hda_dirpath / expected_assets[0].hda_filename
        )
        assert (
            db.insert_hda_history(
                data=decode_record(
                    HistoryData,
                    dict(reversed(list(record_document(result.history).items()))),
                )
            )
            == 1
        )
        assert db.get_hda_history(user_id="tester")[-1].org_hda_name == "한글"
        db._connect.execute(
            "UPDATE hda_history SET video_dirpath=NULL,video_filename=NULL,icon=''"
        )
        db._connect.commit()
        converted = db.get_hda_history(user_id="tester")[0]
        assert converted.video_dirpath is None and converted.icon == ()


def test_legacy_history_input_is_validated_and_ui_does_not_mutate_it(
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace
    from unittest.mock import Mock

    from widgets.panel.model_binding import PanelModelBinding

    row = HistoryData(hda_id=7, comment="memo", org_hda_name="asset", version="")
    feature = PanelModelBinding()
    feature.history_model = Mock()
    feature.history_proxy_model = SimpleNamespace(rowCount=lambda: 1)
    feature.bindings = SimpleNamespace(ui=SimpleNamespace(label__hist_cnt=Mock()))
    feature.insert_ihda_history_data_model(data=row, hist_id=9, tags=["물"])
    assert row.hist_id == 0 and row.tags == ()
    appended = feature.history_model.append_item.call_args.args[0]
    assert appended.hist_id == 9 and appended.tags == ("물",)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sync_interval_ms": 0},
        {"warn_node_batch": 31},
        {"sync_interval_ms": 2**31},
    ],
)
def test_panel_policy_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        PanelPolicy(**kwargs)


def test_sqlite_timeout_policy_is_applied(tmp_path: Path) -> None:
    with SQLite3DatabaseAPI(
        tmp_path / "ihda.db", policy=SQLitePolicy(busy_timeout_ms=123)
    ) as db:
        assert db._connect.execute("PRAGMA busy_timeout").fetchone()[0] == 123
    for kwargs in (
        {"connect_timeout_seconds": float("nan")},
        {"busy_timeout_ms": -1},
        {"connect_timeout_seconds": True},
    ):
        with pytest.raises(ValueError):
            SQLitePolicy(**kwargs)


def test_optional_history_values_are_normalized_without_mutating_input() -> None:
    raw = {
        "hda_id": 1,
        "org_hda_name": "asset",
        "version": "1.0",
        "ihda_dirpath": "한글/asset",
        "hip_dirpath": None,
        "thumb_dirpath": None,
        "video_dirpath": None,
        "icon": None,
        "tags": None,
    }
    result = history_record(raw)
    assert result.ihda_dirpath == Path("한글/asset")
    assert result.thumb_dirpath is None and result.icon == result.tags == ()
    assert raw["ihda_dirpath"] == "한글/asset"


@pytest.mark.parametrize(
    "kwargs", [{"delay_ms": True}, {"immediate_rows": -1}, {"delay_ms": 2**31}]
)
def test_search_policy_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        SearchPolicy(**kwargs)


@pytest.mark.parametrize(
    "limits", [ArchiveLimits(expanded_bytes=2), ArchiveLimits(entries=1)]
)
def test_injected_archive_limits_reject_oversized_input(
    tmp_path: Path, limits: ArchiveLimits
) -> None:
    archive = tmp_path / "files.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("one", b"123")
        output.writestr("two", b"456")
    with pytest.raises(ValueError, match="supported library size"):
        extract_archive(archive, tmp_path / "stage", limits=limits)


def test_panel_uses_policy_and_page_identity(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6 import QtWidgets

    from main import IndividualHDA
    from widgets.panel.services import PanelServices
    from widgets.web_view.web_view import WebView

    monkeypatch.setattr(WebView, "_WebView__set_init_load", lambda self: None)
    panel = IndividualHDA(
        services=PanelServices(
            policy=PanelPolicy(
                sync_interval_ms=1234,
                search=SearchPolicy(delay_ms=321),
                maximum_node_batch=20,
            )
        )
    )
    try:
        assert panel._library_sync.timer.interval() == 1234
        assert panel._browser.debounce.timer.interval() == 321
        assert panel._history_search_debounce.timer.interval() == 321
        assert panel._MAX_NUM_OF_NODE_REGIST == 20
        panel.stackedWidget__whole.insertWidget(0, QtWidgets.QWidget(panel))
        panel.selection._slot_select_view(inst=panel.actionVideo_Player)
        assert panel.stackedWidget__whole.currentWidget() is panel.page__video_player
        panel.selection._slot_select_view(index=panel._hist_view_idx)
        assert panel.stackedWidget__whole.currentWidget() is panel.page__history
        assert panel.actionHistory.isChecked()
    finally:
        panel.close()
