"""Measure bounded Explorer reads against full snapshots on synthetic libraries."""

from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.benchmark_library import seed, milliseconds
from libs.library_explorer import search_assets
from libs.sqlite3_db_api import SQLite3DatabaseAPI


def main() -> None:
    results = []
    for count in (10000, 50000):
        with tempfile.TemporaryDirectory(prefix="ihda-explorer-bench-") as directory:
            root = Path(directory)
            database = root / "ihda.db"
            with SQLite3DatabaseAPI(database) as db:
                seed(db, root, count)
                full = milliseconds(lambda: db.get_hda_data(user_id="bench"))
            results.append(
                {
                    "assets": count,
                    "full_snapshot_ms": full,
                    "first_200_ms": milliseconds(
                        lambda: search_assets(database, "bench", "")
                    ),
                    "filtered_200_ms": milliseconds(
                        lambda: search_assets(database, "bench", "Asset 00")
                    ),
                    "second_200_ms": milliseconds(
                        lambda: search_assets(database, "bench", "", offset=200)
                    ),
                }
            )
            print(json.dumps(results[-1]), flush=True)
    output = {
        "python": sys.version.split()[0],
        "measurement": "Median of 3 warm read calls, synthetic libraries, excludes UI rendering and initial panel load",
        "workloads": results,
    }
    Path("docs/explorer-benchmark.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
