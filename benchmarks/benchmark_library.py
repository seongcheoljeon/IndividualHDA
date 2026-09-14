"""Reproducible synthetic workload. Run from repository root with --counts 10000 50000."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets

from libs.asset_store import AssetStore
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from libs.thumbnail_cache import ThumbnailCache
from model.ihda_list_model import ListModel
from model.ihda_list_proxy_model import ListProxyModel


def milliseconds(operation: Callable[[], Any], repeat: int = 3) -> float:
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        operation()
        times.append((time.perf_counter() - start) * 1000)
    return round(statistics.median(times), 3)


def seed(db: SQLite3DatabaseAPI, root: Path, count: int) -> None:
    with db.transaction():
        db.insert_users("bench", "bench@example.com")
        db.insert_hda_category("sop", "bench")
        for key in range(1, count + 1):
            name = f"Asset {key:06d}"
            db.insert_hda_key(name, "sop", "bench")
            db.insert_hda_info(key, "1.0", filename="asset.ihda", dirpath=root)
            db.insert_icon_info(key, ["SOP", "box"])
            db.insert_hipfile_info(
                key, "scene.hip", root, "21.0", "commercial", "Linux", 1, 24, 24
            )
            db.insert_houdini_node_info(key, "box", "Box", False, False, "/obj/geo/box")
            db.insert_thumbnail_info(key, root, "thumb.png", "1.0")
            db.insert_tag_info(key, ["water", str(key % 10)])
            db.insert_hda_history(
                [
                    key,
                    "create",
                    name,
                    "1.0",
                    "asset.ihda",
                    root,
                    None,
                    "21.0",
                    "scene.hip",
                    root,
                    "commercial",
                    "Linux",
                    "/obj/geo/box",
                    "Box",
                    "box",
                    "sop",
                    "bench",
                    ["SOP", "box"],
                    "thumb.png",
                    root,
                    None,
                    None,
                ]
            )


def run(count: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ihda-benchmark-") as directory:
        root = Path(directory)
        image = QtGui.QImage(256, 256, QtGui.QImage.Format.Format_RGB32)
        image.fill(QtCore.Qt.GlobalColor.blue)
        image.save(str(root / "thumb.png"))
        with SQLite3DatabaseAPI(root / "ihda.db") as db:
            seed(db, root, count)
            results: dict[str, Any] = {"assets": count, "history": count}
            results["db_assets_ms"] = milliseconds(
                lambda: db.get_hda_data(user_id="bench")
            )
            results["db_history_ms"] = milliseconds(
                lambda: db.get_hda_history(user_id="bench")
            )
            rows = db.get_hda_data(user_id="bench")
        store = AssetStore()
        store.reset(rows)
        ids = [1 + (i * 997) % count for i in range(100)]

        def old_lookup() -> None:
            for key in ids:
                {item["hda_id"]: row for row, item in enumerate(rows)}.get(key)

        def new_lookup() -> None:
            for key in ids:
                store.id_rows.get(key)

        results["100_id_lookups_before_ms"] = milliseconds(old_lookup)
        results["100_id_lookups_after_ms"] = milliseconds(new_lookup)

        def old_thumbnails() -> None:
            pixmaps = {}
            for row in rows:
                path = row["thumbnail_dirpath"] / row["thumbnail_filename"]
                pixmaps[row["hda_id"]] = (
                    QtGui.QPixmap(str(path)) if path.exists() else QtGui.QPixmap()
                )

        cache = ThumbnailCache(QtGui.QPixmap(32, 32))

        def new_thumbnails() -> None:
            cache.clear()
            for row in rows:
                cache.set_path(
                    row["hda_id"], row["thumbnail_dirpath"] / row["thumbnail_filename"]
                )

        results["thumbnail_startup_before_ms"] = milliseconds(old_thumbnails)
        results["thumbnail_startup_after_ms"] = milliseconds(new_thumbnails)
        results["decoded_at_startup"] = cache.decoded_count
        model = ListModel(items=rows)
        proxy = ListProxyModel()
        proxy.setSourceModel(model)

        def filtering() -> None:
            proxy.setFilterRegularExpression("Asset 00[123]")
            proxy.rowCount()
            proxy.setFilterRegularExpression("")
            proxy.rowCount()

        def sorting() -> None:
            proxy.sort(0, QtCore.Qt.SortOrder.DescendingOrder)
            proxy.rowCount()
            proxy.sort(0, QtCore.Qt.SortOrder.AscendingOrder)
            proxy.rowCount()

        results["filter_and_clear_ms"] = milliseconds(filtering)
        results["sort_both_directions_ms"] = milliseconds(sorting)
        cache.shutdown()
        return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", nargs="+", type=int, default=[10000, 50000])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    results = {
        "python": sys.version.split()[0],
        "qt": QtCore.qVersion(),
        "workloads": [run(count) for count in args.counts],
    }
    output = json.dumps(results, indent=2)
    print(output)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
