"""The iHDA node scan: tolerant comments, plain scan data, a Houdini-free model."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore

from libs import keys
from libs.houdini.nodes import get_hda_info_by_selection_node, parse_ihda_comment
from libs.scene_scan import IhdaMark, ScannedNode, count_marks, marked_nodes


class FakeNode:
    def __init__(self, comment: str) -> None:
        self._comment = comment

    def comment(self) -> str:
        return self._comment


def test_comment_parser_reads_the_three_keys_and_ignores_everything_else() -> None:
    clean = "iHDA Name: Water\niHDA Version: 1.0\niHDA ID: 7"
    assert parse_ihda_comment(clean) == {
        "iHDA Name": "Water",
        "iHDA Version": "1.0",
        "iHDA ID": 7,
    }
    # A user's notes: extra colons, blank lines, unknown keys, trailing spaces.
    edited = (
        "todo: check 10:30 with Kim\n\n"
        "iHDA Name: Water \n iHDA Version: 1.0\niHDA ID: 7 \n"
        "URL: http://example.com/a:b\niHDA ID: 99"
    )
    assert parse_ihda_comment(edited) == {
        "iHDA Name": "Water",
        "iHDA Version": "1.0",
        "iHDA ID": 7,  # the first ID wins; later duplicates are ignored
    }
    assert parse_ihda_comment("") is None and parse_ihda_comment(None) is None
    assert parse_ihda_comment("just a note") is None
    assert parse_ihda_comment("iHDA Name: x\niHDA Version: 1") is None  # no ID
    assert parse_ihda_comment("iHDA ID: seven") is None  # not a number
    assert parse_ihda_comment("iHDA ID: 3") == {
        "iHDA Name": "",
        "iHDA Version": "",
        "iHDA ID": 3,
    }
    assert get_hda_info_by_selection_node(FakeNode(edited))["iHDA ID"] == 7
    assert get_hda_info_by_selection_node(FakeNode("   ")) is None
    assert get_hda_info_by_selection_node(None) is None


def scene() -> tuple[ScannedNode, ...]:
    fire = ScannedNode(
        "/obj/geo1/fire",
        "fire",
        "subnet",
        "sop",
        "Fire",
        ("SOP", "subnet"),
        "2026-09-01 10:00:00",
        "2026-09-02 11:00:00",
        IhdaMark(3, "fire_presets", "2.0"),
    )
    smoke = ScannedNode(
        "/obj/geo1/smoke",
        "smoke",
        "subnet",
        "sop",
        "Smoke",
        ("SOP", "subnet"),
        "",
        "",
        IhdaMark(5, "smoke", "1.0"),
    )
    geo = ScannedNode(
        "/obj/geo1",
        "geo1",
        "geo",
        "obj",
        "Geometry",
        ("OBJ", "geo"),
        "",
        "",
        None,
        (fire, smoke),
    )
    obj = ScannedNode(
        "/obj", "obj", "obj", keys.Type.manager, "", (), "", "", None, (geo,)
    )
    return (obj,)


def test_scan_data_counts_and_lists_marks() -> None:
    nodes = scene()
    assert count_marks(nodes) == 2
    assert [n.path for n in marked_nodes(nodes)] == [
        "/obj/geo1/fire",
        "/obj/geo1/smoke",
    ]
    assert count_marks(()) == 0


def test_inside_model_mirrors_the_scan_without_houdini(app: Any) -> None:
    from model.ihda_inside_model import InsideModel
    from model.ihda_inside_proxy_model import InsideProxyModel

    model = InsideModel(pixmap_cate_data={}, pixmap_ihda_data={}, inst_ihda_icon=None)
    assert model.rowCount(model.index(0, 0)) == 0  # empty until a scan arrives
    model.make_node_tree(scene())
    root = model.index(0, 0)
    obj = model.index(0, 0, root)
    assert obj.data() == "obj" and obj.data(InsideModel.node_type_role) == "manager"
    geo = model.index(0, 0, obj)
    assert geo.data() == "geo1" and geo.data(InsideModel.depth_role) == 2
    assert geo.data(QtCore.Qt.ItemDataRole.ToolTipRole) == "/obj/geo1"
    fire = model.index(0, 0, geo)
    assert fire.data() == "fire (v2.0)"
    assert fire.data(InsideModel.node_type_role) == keys.Type.ihda
    assert fire.data(InsideModel.hda_id_role) == 3
    assert fire.data(InsideModel.hda_org_name_role) == "fire_presets"
    assert fire.data(InsideModel.node_path_role) == "/obj/geo1/fire"
    assert model.index(0, 5, obj).data() == ""  # geo1: no created time -> blank
    assert model.index(0, 5, geo).data() == "2026-09-01 10:00:00"  # fire
    assert fire.data(QtCore.Qt.ItemDataRole.DecorationRole) is not None  # generic icon
    assert model.get_ihda_node_list() == [
        ["fire_presets", 3, "/obj/geo1/fire"],
        ["smoke", 5, "/obj/geo1/smoke"],
    ]
    proxy = InsideProxyModel()
    proxy.setSourceModel(model)
    assert proxy.get_row_count() == 2
    proxy.setFilterRegularExpression("smoke")
    assert proxy.get_row_count() == 1
    proxy.setFilterRegularExpression("obj/geo1/fire")  # paths match too
    assert proxy.get_row_count() == 1
    proxy.setFilterRegularExpression("")
    proxy.set_filter_attribute(hda_id=5)
    assert proxy.get_row_count() == 1
    model.clear_item()
    assert model.rowCount(model.index(0, 0)) == 0
