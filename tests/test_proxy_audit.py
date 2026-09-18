"""Regression cases from the model/proxy/theme audit."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from libs.asset_contracts import AssetData
from libs.record_codec import decode_record
from model.ihda_category_proxy_model import CategoryProxyModel
from model.ihda_history_model import HistoryModel
from model.ihda_history_proxy_model import HistoryProxyModel
from model.ihda_inside_model import InsideModel
from model.ihda_inside_proxy_model import InsideProxyModel
from model.ihda_list_proxy_model import ListProxyModel
from model.ihda_record_model import RecordModel
from model.ihda_record_proxy_model import RecordProxyModel
from model.ihda_table_proxy_model import TableProxyModel


@pytest.mark.parametrize(
    "proxy_type", [ListProxyModel, TableProxyModel, HistoryProxyModel]
)
def test_flat_proxy_null_values_and_combined_filters(
    app: Any, proxy_type: type
) -> None:
    proxy = proxy_type(search_target_idx=1)
    source = QtGui.QStandardItemModel()
    rows = []
    for name, tags in [("Alpha", None), ("Beta", ["water", None])]:
        item = QtGui.QStandardItem(name)
        item.setData(tags, proxy.tag_role)
        item.setData(None, proxy.type_role)
        if proxy.favorite_role is not None:
            item.setData(name == "Beta", proxy.favorite_role)
            item.setData("sop", proxy.cate_role)
        source.appendRow(
            [QtGui.QStandardItem("id"), item] if proxy.name_column else item
        )
        rows.append(item)
    proxy.setSourceModel(source)
    proxy.setFilterRegularExpression("water")
    assert proxy.rowCount() == 1
    proxy.set_search_target_idx(2)
    assert proxy.rowCount() == 0
    proxy.set_search_target_idx(0)
    proxy.setFilterRegularExpression("beta")
    proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
    assert proxy.rowCount() == 1
    source_index = rows[1].index()
    assert proxy.mapToSource(proxy.mapFromSource(source_index)) == source_index
    if proxy.favorite_role is not None:
        proxy.is_favorite_nodes = True
        rows[1].setData(False, proxy.favorite_role)
        assert proxy.rowCount() == 0


def test_history_dates_include_whole_last_day(app: Any) -> None:
    proxy = HistoryProxyModel()
    source = QtGui.QStandardItemModel()
    for stamp in [
        None,
        "2026-09-10 23:59:59",
        "2026-09-11 00:00:00",
        "2026-09-11 23:59:59",
        "2026-09-12 00:00:00",
    ]:
        item = QtGui.QStandardItem("asset")
        item.setData(stamp, HistoryModel.datetime_role)
        source.appendRow([QtGui.QStandardItem(), item])
    proxy.setSourceModel(source)
    proxy.set_datetime(["2026-09-11", "2026-09-11"])
    assert proxy.rowCount() == 2
    proxy.set_datetime(None)
    assert proxy.rowCount() == 5
    with pytest.raises(ValueError):
        proxy.set_datetime(["2026-09-12", "2026-09-11"])


@pytest.mark.parametrize("proxy_type", [RecordProxyModel, InsideProxyModel])
def test_tree_constraints_apply_to_same_node_and_count_all_roots(
    app: Any, proxy_type: type
) -> None:
    role = (
        RecordModel.hda_id_role
        if proxy_type is RecordProxyModel
        else InsideModel.hda_id_role
    )
    source = QtGui.QStandardItemModel()
    for group_name in ["group A", "group B"]:
        group = QtGui.QStandardItem(group_name)
        for name, key, file in [
            ("water", 1, Path("/a.hip")),
            ("fire", 2, Path("/b.hip")),
        ]:
            item = QtGui.QStandardItem(name)
            item.setData(key, role)
            if proxy_type is RecordProxyModel:
                item.setData(file, RecordModel.hip_filepath_role)
                item.setData(True, RecordModel.is_record_type_role)
            group.appendRow(item)
        source.appendRow(group)
    proxy = proxy_type()
    proxy.setSourceModel(source)
    assert proxy.get_row_count() == 4
    proxy.set_filter_attribute(hda_id=1)
    proxy.setFilterRegularExpression("fire")
    assert proxy.rowCount() == 0
    proxy.setFilterRegularExpression("group")
    assert proxy.get_row_count() == 2
    if proxy_type is RecordProxyModel:
        proxy.set_filter_attribute(hda_id=1, hip_filepath=Path("/b.hip"))
        assert proxy.rowCount() == 0
    proxy.set_filter_attribute(hda_id=-1)
    assert proxy.get_row_count() == 4
    source.removeRow(1)
    assert proxy.get_row_count() == 2


def test_category_descendant_and_ancestor_search(app: Any) -> None:
    source = QtGui.QStandardItemModel()
    root = QtGui.QStandardItem("root")
    group = QtGui.QStandardItem("sop")
    group.appendRow(QtGui.QStandardItem("water"))
    group.appendRow(QtGui.QStandardItem("fire"))
    root.appendRow(group)
    source.appendRow(root)
    proxy = CategoryProxyModel()
    proxy.setSourceModel(source)
    proxy.setFilterRegularExpression("water")
    assert proxy.rowCount(proxy.index(0, 0, proxy.index(0, 0))) == 1
    proxy.setFilterRegularExpression("sop")
    assert proxy.rowCount(proxy.index(0, 0, proxy.index(0, 0))) == 2


def test_dark_resources_and_host_theme_roundtrip(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import public
    import ui_settings
    from libs.qt_helpers import dark_stylesheet

    sheet = dark_stylesheet()
    urls = re.findall(r"url\([\s\"\']*(:/[^)\s\"\']+)", sheet)
    assert urls
    assert all(QtCore.QFile.exists(url) for url in urls)
    window = QtWidgets.QWidget()
    window.actionDefault = QtGui.QAction(window)
    window.actionDefault.setCheckable(True)
    window.actionDark_blue = QtGui.QAction(window)
    window.actionDark_blue.setCheckable(True)
    settings = ui_settings.UISettings(window)
    from libs import host, houdini_api

    monkeypatch.setattr(host, "IS_HOUDINI", True)
    monkeypatch.setattr(houdini_api, "IS_HOUDINI", True)
    monkeypatch.setattr(
        houdini_api,
        "hou",
        SimpleNamespace(
            qt=SimpleNamespace(styleSheet=lambda: "QWidget { color: #abcdef; }")
        ),
        raising=False,
    )
    original = app.styleSheet()
    for _ in range(2):
        settings.set_theme(public.Name.darkblue_theme)
        assert window.styleSheet() == sheet and window.property("houdiniStyle") is False
        settings.set_theme(public.Name.default_theme)
        assert "#abcdef" in window.styleSheet() and "QToolBar" in window.styleSheet()
        assert window.property("houdiniStyle") is True
    assert app.styleSheet() == original
    window.close()


def test_tree_model_mutation_notifications(app: Any) -> None:
    from model.ihda_category_model import CategoryModel

    model = CategoryModel(
        data={"a": None, "b": None, "c": None},
        pixmap_cate_data={},
        font_size=10,
        font_style="Sans",
        icon_size=16,
        padding=2,
    )
    messages: list[str] = []
    previous = QtCore.qInstallMessageHandler(
        lambda kind, context, text: messages.append(text)
    )
    try:
        _tester = QtTest.QAbstractItemModelTester(  # must stay alive while testing
            model, QtTest.QAbstractItemModelTester.Warning
        )
        root = model.index(0, 0)
        assert model.rowCount(root) == 3
        assert not model.insertRows(0, 1, root)
        assert not model.removeRows(-1, 1, root)
        assert not model.removeRows(0, 4, root)
        assert model.removeRows(0, 2, root)
        assert model.rowCount(root) == 1
        model.delete_node(model.index(0, 0, root))
        assert model.rowCount(root) == 0
        assert not any("FAIL!" in message for message in messages), messages
    finally:
        QtCore.qInstallMessageHandler(previous)


@pytest.mark.parametrize(
    "kind", ["category", "record", "inside", "list", "table", "history"]
)
def test_every_source_model_and_proxy_obeys_qt_contract(app: Any, kind: str) -> None:
    from importlib import import_module

    source_class = getattr(
        import_module(f"model.ihda_{kind}_model"), kind.title() + "Model"
    )
    proxy_class = getattr(
        import_module(f"model.ihda_{kind}_proxy_model"), kind.title() + "ProxyModel"
    )
    source = source_class()
    proxy = proxy_class()
    proxy.setSourceModel(source)
    messages: list[str] = []
    previous = QtCore.qInstallMessageHandler(
        lambda level, context, text: messages.append(text)
    )
    try:
        _testers = [  # must stay alive while testing
            QtTest.QAbstractItemModelTester(
                model, QtTest.QAbstractItemModelTester.Warning
            )
            for model in (source, proxy)
        ]
        proxy.setFilterRegularExpression("absent")
        proxy.setFilterRegularExpression("")
        proxy.sort(0, QtCore.Qt.DescendingOrder)
        source.clear_item()
        assert not any("FAIL!" in message for message in messages), messages
    finally:
        QtCore.qInstallMessageHandler(previous)


def test_sorted_filtered_selection_maps_source_id(app: Any, tmp_path: Path) -> None:
    import public
    from model.ihda_list_model import ListModel
    from widgets.panel.library_queries import PanelLibraryQueries

    items = [
        decode_record(AssetData, {public.Key.hda_id: 10, public.Key.hda_name: "Zulu"}),
        decode_record(AssetData, {public.Key.hda_id: 20, public.Key.hda_name: "Alpha"}),
    ]
    model = ListModel(items=items)
    proxy = ListProxyModel()
    proxy.setSourceModel(model)
    proxy.sort(0)
    owner = SimpleNamespace(
        bindings=SimpleNamespace(
            management=SimpleNamespace(_get_hda_id_row_map=lambda: {10: 0, 20: 1})
        )
    )
    index = PanelLibraryQueries._find_hda_id_by_model_item(owner, proxy, 10)
    assert index.data(ListModel.id_role) == 10 and index.row() == 1
    proxy.setFilterRegularExpression("Alpha")
    assert PanelLibraryQueries._find_hda_id_by_model_item(owner, proxy, 10) is None


def test_source_change_rechecks_active_filter(app: Any) -> None:
    import public
    from model.ihda_list_model import ListModel
    from model.ihda_table_model import TableModel
    from widgets.panel.model_binding import PanelModelBinding

    rows = [
        decode_record(
            AssetData,
            {public.Key.hda_id: 1, public.Key.hda_name: "Old", public.Key.hda_tags: []},
        )
    ]
    first, second = ListModel(items=rows), TableModel(items=rows)
    proxies = [ListProxyModel(), TableProxyModel()]
    for proxy, source in zip(proxies, (first, second), strict=False):
        proxy.setSourceModel(source)
        proxy.setFilterRegularExpression("New")
        assert proxy.rowCount() == 0
    from libs.asset_store import AssetStore

    store = AssetStore()
    store.reset(rows)
    store.rows = rows
    owner = SimpleNamespace(assets=store, list_model=first, table_model=second)
    PanelModelBinding._update_item_row_data(owner, 0, replace(rows[0], hda_name="New"))
    assert all(proxy.rowCount() == 1 for proxy in proxies)


def test_multi_delete_keeps_ids_after_proxy_reorders(app: Any, tmp_path: Path) -> None:
    import public
    from model.ihda_list_model import ListModel
    from widgets.panel.asset_management import PanelAssetManagement

    rows = [
        decode_record(
            AssetData,
            {
                public.Key.hda_id: key,
                public.Key.hda_name: name,
                public.Key.hda_dirpath: tmp_path,
                public.Key.hda_cate: "sop",
            },
        )
        for key, name in [(1, "Zulu"), (2, "Alpha"), (3, "Beta")]
    ]
    source = ListModel(items=rows)
    proxy = ListProxyModel()
    proxy.setSourceModel(source)
    proxy.sort(0)
    selected = [proxy.index(0, 0), proxy.index(2, 0)]
    deleted: list[int] = []

    def remove(**values: Any) -> None:
        deleted.append(values["hda_id"])
        current_row = next(
            row for row, item in enumerate(rows) if item.hda_id == values["hda_id"]
        )
        source.remove_item(current_row)

    owner = SimpleNamespace(
        bindings=SimpleNamespace(
            team=lambda: None,
            video_player=SimpleNamespace(player_stop=lambda: None),
            presentation=SimpleNamespace(_is_icon_mode=True),
            models=SimpleNamespace(
                assets=SimpleNamespace(
                    id_rows={item.hda_id: row for row, item in enumerate(rows)}
                ),
                history_model=SimpleNamespace(
                    get_hist_data_by_hkey_id_from_model=lambda **kw: []
                ),
                record_proxy_model=SimpleNamespace(get_row_count=lambda: 0),
            ),
            selection=SimpleNamespace(
                _initialize_current_attribs=lambda: None,
                _initialize_hist_current_attribs=lambda: None,
            ),
            notes=SimpleNamespace(
                _clear_parms=lambda: None, _clear_hist_parms=lambda: None
            ),
            ui=SimpleNamespace(
                label__loc_record_count=SimpleNamespace(setText=lambda text: None)
            ),
        ),
        _get_hda_id_row_map=lambda: {item.hda_id: row for row, item in enumerate(rows)},
        _delete_ihda_item=remove,
    )
    PanelAssetManagement._remove_hda_item(owner, selected)
    assert deleted == [2, 1]
    assert [item.hda_id for item in rows] == [3]


def test_activity_rows_are_readable_but_inert(app: Any) -> None:
    from libs.asset_contracts import HistoryData

    version = HistoryData(
        hist_id=7,
        hda_id=1,
        org_hda_name="Water",
        version="1.0",
        ihda_dirpath=Path("/missing"),
        ihda_filename="Water.hda",
        reg_time="2026-09-17 10:00:00",
    )
    activity = HistoryData(
        kind="rename",
        hda_id=1,
        org_hda_name="Ocean",
        version="",
        comment="NAME (CHANGE) Water → Ocean",
        reg_time="2026-09-17 11:00:00",
    )
    model = HistoryModel(items=[version, activity])
    proxy = HistoryProxyModel()
    proxy.setSourceModel(model)

    index = model.index(1, 0)
    assert not index.flags() & QtCore.Qt.ItemFlag.ItemIsDragEnabled
    assert index.flags() & QtCore.Qt.ItemFlag.ItemIsSelectable
    font = index.data(QtCore.Qt.ItemDataRole.FontRole)
    assert font.italic() and not font.strikeOut()
    assert index.data(QtCore.Qt.ItemDataRole.DisplayRole) == ""  # no history id
    assert index.data(QtCore.Qt.ItemDataRole.DecorationRole) is None
    assert model.index(1, 4).data(QtCore.Qt.ItemDataRole.DisplayRole) == (
        "NAME (CHANGE) Water → Ocean"
    )
    # The version row keeps its missing-file strike-out and its identity lookup.
    assert model.index(0, 0).data(QtCore.Qt.ItemDataRole.FontRole).strikeOut()
    assert model.get_history_id_from_model(1, "1.0") == 7
    assert model.get_history_id_from_model(1, "") is None
    proxy.set_datetime(["2026-09-17", "2026-09-17"])
    assert proxy.rowCount() == 2
