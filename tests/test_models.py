from __future__ import annotations

import pathlib
from typing import Any

from PySide6 import QtCore, QtGui, QtTest

import public
from libs.asset_contracts import AssetData
from libs.drag_payload import decode_payload
from libs.record_codec import decode_record
from model.ihda_list_model import ListModel
from model.ihda_list_proxy_model import ListProxyModel
from model.ihda_table_model import TableModel


def asset(tmp_path: pathlib.Path) -> AssetData:
    (tmp_path / "asset.hda").touch()
    return decode_record(
        AssetData,
        {
            public.Key.hda_id: 1,
            public.Key.hda_name: "Water 한글",
            public.Key.hda_dirpath: tmp_path,
            public.Key.hda_filename: "asset.hda",
            public.Key.hda_cate: "sop",
            public.Key.hda_version: "1.0",
            public.Key.is_favorite_hda: False,
            public.Key.hda_tags: ["물"],
            public.Key.node_type_name: "geo",
            public.Key.node_def_desc: "Geometry",
            public.Key.hda_load_count: 0,
            public.Key.hda_ctime: "2020-01-01 00:00:00",
            public.Key.hda_mtime: "2020-01-01 00:00:00",
            public.Key.hou_version: "21.0",
            public.Key.hda_license: "commercial",
            public.Key.thumbnail_dirpath: tmp_path,
            public.Key.thumbnail_filename: "thumb.jpg",
        },
    )


def test_shared_model_notifications_and_drag(app: Any, tmp_path: pathlib.Path) -> None:
    from widgets.panel.model_binding import PanelModelBinding

    owner = PanelModelBinding()
    rows = owner.assets.rows
    kwargs = {
        "items": rows,
        "pixmap_ihda_data": {1: QtGui.QPixmap(32, 32)},
        "pixmap_thumb_data": {},
        "font_size": 11,
        "font_style": "Sans",
        "icon_size": 38,
        "thumb_size": 76,
    }
    first = ListModel(padding=20, **kwargs)
    second = TableModel(**kwargs)
    owner.list_model = first
    owner.table_model = second
    messages = []
    previous = QtCore.qInstallMessageHandler(
        lambda kind, context, msg: messages.append(msg)
    )
    try:
        _testers = [  # must stay alive while testing
            QtTest.QAbstractItemModelTester(
                model, QtTest.QAbstractItemModelTester.Warning
            )
            for model in (first, second)
        ]
        owner._insert_ihda_data_model(asset(tmp_path))
        assert first.rowCount() == second.rowCount() == 1
        payload = first.mimeData([first.index(0, 0)]).data(public.Type.mime_type)
        assert decode_payload(payload)[public.Key.hda_dirpath] == tmp_path
        for model in (first, second):
            for role in (
                QtCore.Qt.DecorationRole,
                QtCore.Qt.FontRole,
                QtCore.Qt.SizeHintRole,
            ):
                model.data(model.index(0, 0), role)
        owner._remove_hda_data(0)
        assert first.rowCount() == second.rowCount() == 0
        assert not any("FAIL!" in message for message in messages), messages
    finally:
        QtCore.qInstallMessageHandler(previous)


def test_tag_filter(app: Any, tmp_path: pathlib.Path) -> None:
    model = ListModel(items=[asset(tmp_path)])
    proxy = ListProxyModel(search_target_idx=1)
    proxy.setSourceModel(model)
    proxy.setFilterRegularExpression("물")
    assert proxy.rowCount() == 1
    proxy.setFilterRegularExpression("absent")
    assert proxy.rowCount() == 0
    proxy.set_id_filter(frozenset({1}))
    assert proxy.rowCount() == 1  # id filter wins over the regex
    proxy.set_id_filter(frozenset())
    assert proxy.rowCount() == 0
    proxy.set_id_filter(None)
    proxy.set_search_field("Name")
    proxy.setFilterRegularExpression("Water")
    assert proxy.rowCount() == 1


def test_scene_rename_retains_historical_filenames(
    app: Any, tmp_path: pathlib.Path
) -> None:
    from libs.scene_contracts import SceneRecord
    from model.ihda_record_model import RecordModel

    records = tuple(
        SceneRecord(
            record_id=index,
            hda_id=7,
            node_name="Old",
            node_ver=version,
            hda_dirpath=tmp_path / "Old",
            hda_filename=filename,
            hip_dirpath=tmp_path,
            hip_filename="scene.hip",
            parent_node_path="/obj",
        )
        for index, version, filename in ((1, "1.0", "v1.hda"), (2, "2.0", "v2.hda"))
    )
    model = RecordModel(data=records)
    model.rename_record_item(
        hda_id=7,
        new_name="New",
        hda_dirpath=tmp_path / "New",
        hda_version="2.0",
        hda_filename="New_2.0.hda",
    )
    model.reload()
    changed = {record.record_id: record for record in model.record_data}
    assert changed[1].hda_filename == "v1.hda"
    assert changed[2].hda_filename == "New_2.0.hda"
    assert all(
        record.hda_dirpath == tmp_path / "New" and record.node_name == "New"
        for record in changed.values()
    )
    assert records[0].node_name == "Old"
