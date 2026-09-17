"""Run with Houdini 21+ hython; creates only a fresh in-memory scene and temp files."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ihda-host-smoke-") as directory:
        directory = Path(directory)
        os.environ["IHDA_CONFIG_DIR"] = str(directory / "config")
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6 import QtCore, QtWidgets

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        from libs.drag_payload import decode_payload, encode_payload
        from libs.houdini_api import HoudiniAPI
        from libs.qt_helpers import wildcard_expression
        from libs.sqlite3_db_api import SQLite3DatabaseAPI

        assert (
            wildcard_expression("asset*", QtCore.Qt.CaseInsensitive)
            .match("Asset 한글")
            .hasMatch()
        )
        assert decode_payload(encode_payload({"path": directory}))["path"] == directory
        assets = directory / "asset's 한글"
        assets.mkdir()
        geo = hou.node("/obj").createNode("geo", "ihda_smoke_container")
        box = geo.createNode("box", "ihda_smoke_box")
        original_path = box.path()
        assert HoudiniAPI.create_hda_file(box, assets, "smoke.ihda", "1.0")
        assert (assets / "smoke.ihda").is_file()
        assert box.path() == original_path
        assert len(geo.children()) == 1
        definitions = hou.hda.definitionsInFile(str(assets / "smoke.ihda"))
        assert definitions
        imported = HoudiniAPI.import_individual_hda_into_houdini(
            assets / "smoke.ihda", geo, hou.Vector2(2, 0), "ihda_imported_box", "box"
        )
        assert imported is not None and imported.type().name() == "box"
        print(
            "After import:",
            box.path(),
            original_path,
            [(n.name(), n.type().name()) for n in geo.children()],
            flush=True,
        )
        assert box.path() == original_path and len(geo.children()) == 2
        assert HoudiniAPI.node_type_name(node=box) == "box"
        print("HDA export/import and original node preservation: PASS", flush=True)
        from libs.version_compare import compare_expanded, expand_asset

        box.parm("sizex").set(2.0)
        assert HoudiniAPI.create_hda_file(box, assets, "smoke-v2.ihda", "2.0")
        before_files = set(hou.hda.loadedFiles())
        before_nodes = tuple(geo.children())
        left = directory / "compare-left"
        right = directory / "compare-right"
        left_parameters = expand_asset(assets / "smoke.ihda", left)
        right_parameters = expand_asset(assets / "smoke-v2.ihda", right)
        comparison = compare_expanded(
            left,
            right,
            {"version": "1.0"},
            {"version": "2.0"},
            left_parameters,
            right_parameters,
        )
        assert "Changed:" in comparison and "version:" in comparison
        assert (
            set(hou.hda.loadedFiles()) == before_files
            and tuple(geo.children()) == before_nodes
        )
        print("SideFX version comparison without scene changes: PASS", flush=True)

        with SQLite3DatabaseAPI(directory / "ihda.db") as db:
            assert db.insert_users("anonymous", "anonymous@example.com") == 1
            assert db.insert_hda_category("sop", "anonymous") == 1
            assert db.insert_hda_key("asset's 한글", "sop", "anonymous") == 1
            assert db.get_hda_key_id(name="asset's 한글") == [1]
        print("SQLite and Unicode paths: PASS", flush=True)
        from libs.database_migrations import SCHEMA_VERSION, migrate

        legacy_path = directory / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                (Path(__file__).parent / "fixtures/schema_legacy.sql").read_text(
                    encoding="utf-8"
                )
            )
            connection.execute("INSERT INTO users VALUES ('keep','email','2020-01-01')")
            connection.execute("INSERT INTO hda_category VALUES ('sop','keep')")
            connection.execute("INSERT INTO hda_key VALUES (1,'box','sop','keep')")
            connection.execute(
                "INSERT INTO hipfile_info VALUES (1,1,'test.hip','/tmp','21','commercial','Windows',-1.5,100.25,23.976)"
            )
            connection.commit()
            migrate(connection, legacy_path)
            assert (
                connection.execute("PRAGMA user_version").fetchone()[0]
                == SCHEMA_VERSION
            )
            assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert not connection.execute("PRAGMA foreign_key_check").fetchall()
            assert connection.execute(
                "SELECT sf,ef,fps FROM hipfile_info"
            ).fetchone() == (-1.5, 100.25, 23.976)
            try:
                connection.execute("UPDATE hipfile_info SET fps=0")
            except sqlite3.IntegrityError:
                connection.rollback()
            else:
                raise AssertionError("Invalid FPS was accepted")
        print("Legacy schema migration and numeric constraints: PASS", flush=True)

        from widgets.web_view.web_view import WebView

        WebView._WebView__set_init_load = lambda self: self.lineEdit__address.setText(
            "about:blank"
        )
        from main import IndividualHDA

        panel = IndividualHDA()
        import public

        panel.presentation._set_theme(public.Name.darkblue_theme)
        assert panel.styleSheet()
        panel.presentation._set_theme(public.Name.default_theme)
        from widgets.library_manager.dialog import LibraryManager

        manager = LibraryManager(
            directory / "ihda.db", assets, "anonymous", parent=panel
        )
        assert manager.tabs.count() == 6
        manager.show()
        app.processEvents()
        manager.shutdown()
        print("Library Manager six-tab lifecycle: PASS", flush=True)

        assert HoudiniAPI.items_position(()) == hou.Vector2(-5, 0)
        panel.close()
        app.processEvents()
        print("Panel construction and shutdown: PASS", flush=True)
        geo.destroy()
        from libs.log_handler import uninstall_file_logging

        uninstall_file_logging()  # Windows cannot delete an open ihda.log
        print(
            "Houdini",
            hou.applicationVersionString(),
            "Qt",
            QtCore.qVersion(),
            "PASS",
            flush=True,
        )


if __name__ == "__main__":
    main()
