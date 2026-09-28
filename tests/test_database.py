from __future__ import annotations

import pathlib
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest

from libs.database.schema import SCHEMA_VERSION, install
from libs.sqlite3_db_api import SQLite3DatabaseAPI


@pytest.fixture
def db(tmp_path: pathlib.Path) -> Iterator[Any]:
    with SQLite3DatabaseAPI(tmp_path / "library.db") as api:
        yield api


def seed(db: Any, user: str = "O'한글", name: str = "Asset's 한글") -> Any:
    assert db.insert_users(user, user + "@example.com") == 1
    assert db.insert_hda_category("sop", user) == 1
    assert db.insert_hda_key(name, "sop", user) == 1
    return db.get_hda_key_id(category="sop", name=name, user_id=user)[0]


def test_quoted_data_and_tags(db: Any, tmp_path: pathlib.Path) -> None:
    key = seed(db)
    assert db.insert_hda_info(key, "1.0", filename="a's.hda", dirpath=tmp_path) == 1
    assert db.insert_note_info(key, "메모 ' SQL ; --") == 1
    assert db.get_note_info(key) == "메모 ' SQL ; --"
    assert db.update_note_info(key, "새 메모 ';") == 1
    assert db.get_hda_note_history_most_recent_by_ver(key, "1.0") == "새 메모 ';"
    assert db.insert_tag_info(key, ["한글", "quote'", "한글"]) == 1
    with sqlite3.connect(db.db_filepath) as connection:
        assert connection.execute(
            "SELECT tag FROM asset_tags ORDER BY tag"
        ).fetchall() == [("quote'",), ("한글",)]
    assert db.update_tag_info(key, ["changed"]) == 1
    with sqlite3.connect(db.db_filepath) as connection:
        assert connection.execute("SELECT tag FROM asset_tags").fetchall() == [
            ("changed",)
        ]
    assert db.get_count_hda_key(name="Asset's 한글") == 1
    assert db.get_count_hda_key(name="' OR 1=1 --") == 0


def test_normalize_tags_and_vocabulary(db: Any, tmp_path: pathlib.Path) -> None:
    from libs.database.values import normalize_tags

    assert normalize_tags("#smoke, Fire\nsmoke #SMOKE #  ") == ["smoke", "Fire"]
    assert normalize_tags(["a#b", " c ", "", "A"]) == ["a", "b", "c"]
    assert normalize_tags(None) == []
    key = seed(db)
    assert db.insert_hda_info(key, "1.0", filename="a.hda", dirpath=tmp_path) == 1
    assert db.insert_tag_info(key, ["물", "Smoke#fire", "smoke"]) == 1
    assert db.get_tag_info(key) == ["물", "Smoke", "fire"]
    assert db.distinct_tags() == ["fire", "Smoke", "물"]
    assert db.distinct_tags(user_id="nobody") == []


def test_transaction_rolls_back(db: Any) -> None:
    with pytest.raises(sqlite3.DatabaseError), db.transaction():
        seed(db)
        db.insert_hda_key("Asset's 한글", "sop", "O'한글")
    assert db.get_user_id() == []


def test_category_cleanup_is_scoped_to_user(db: Any) -> None:
    key = seed(db, "one", "asset")
    seed(db, "two", "asset")
    assert db.delete_hda_key_with_id(key) == 1
    assert db.get_hda_category("one") == []
    assert db.get_hda_category("two") == ["sop"]


def test_other_schema_is_backed_up_and_rebuilt(tmp_path: pathlib.Path) -> None:
    """No in-place upgrade: the old file is kept as a backup, the library starts empty."""
    path = tmp_path / "library.db"
    with SQLite3DatabaseAPI(path) as db:
        seed(db, "artist")
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=3")
    with SQLite3DatabaseAPI(path) as db:
        assert db.get_user_id() == []
        assert db.is_exist_user_id("artist") is False
    backups = list(tmp_path.glob(f"library.db.pre-v{SCHEMA_VERSION}-*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 3
        assert backup.execute("SELECT user_id FROM users").fetchone() == ("artist",)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    # Opening again touches nothing.
    with SQLite3DatabaseAPI(path):
        pass
    assert len(list(tmp_path.glob("*.bak"))) == 1


def test_unversioned_file_with_tables_is_rebuilt_too(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO users VALUES ('artist')")
    with SQLite3DatabaseAPI(path) as db:
        assert db.get_user_id() == []
    assert len(list(tmp_path.glob("old.db.pre-v*.bak"))) == 1


def test_media_audit_events_name_their_version(db: Any, tmp_path: pathlib.Path) -> None:
    import json

    key = seed(db)
    assert db.insert_video_info(
        hda_key_id=key, dirpath=tmp_path, filename="v.mp4", version="1.0"
    )
    (changes,) = db._connect.execute(
        "SELECT changes FROM audit_events WHERE operation='video_info.insert'"
    ).fetchone()
    assert json.loads(changes)["after"]["version"] == "1.0"


def test_newer_schema_rejected(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 999")
    with pytest.raises(RuntimeError):
        SQLite3DatabaseAPI(path)


def test_transaction_spans_catalog_assets_nodes_and_history(
    db: Any, tmp_path: pathlib.Path
) -> None:
    """Split query modules must still use one atomic connection."""
    key = seed(db)
    with pytest.raises(RuntimeError, match="abort"), db.transaction():
        db.insert_hda_info(key, "1.0", filename="box.hda", dirpath=tmp_path)
        db.insert_houdini_node_info(key, "box", "Box", False, False, "/obj/geo/box")
        db.insert_note_info(key, "original")
        db.update_note_info(key, "updated")
        assert db.get_hda_node_type(key) == "box"
        assert db.get_hda_note_history_most_recent_by_ver(key, "1.0") == "updated"
        raise RuntimeError("abort")
    assert db.get_hda_key_id(name="Asset's 한글") == [key]
    with sqlite3.connect(db.db_filepath) as connection:
        for table in ("hda_info", "houdini_node_info", "note_info", "hda_note_history"):
            assert (
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            )


def test_category_cleanup_scopes_owner() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        install(connection)
        for user in ("one", "two"):
            connection.execute(
                "INSERT INTO users VALUES (?, ?, '2026-01-01')", (user, user)
            )
            connection.execute("INSERT INTO hda_category VALUES ('sop', ?)", (user,))
            connection.execute(
                "INSERT INTO hda_key(name, category, user_id) VALUES ('asset', 'sop', ?)",
                (user,),
            )
        connection.execute("DELETE FROM hda_key WHERE user_id='one'")
        assert connection.execute("SELECT user_id FROM hda_category").fetchall() == [
            ("two",)
        ]


def test_tag_owner_change_removes_previous_normalized_tags(db: Any) -> None:
    first = seed(db, "one", "asset")
    second = seed(db, "two", "asset")
    db.insert_tag_info(first, ["old"])
    with sqlite3.connect(db.db_filepath) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            "UPDATE tag_info SET hda_key_id=?, tag='new#한글' WHERE hda_key_id=?",
            (second, first),
        )
        assert connection.execute(
            "SELECT hda_key_id, tag FROM asset_tags ORDER BY tag"
        ).fetchall() == [(second, "new"), (second, "한글")]
        connection.execute("UPDATE hda_key SET id=100 WHERE id=?", (second,))
        assert connection.execute(
            "SELECT DISTINCT hda_key_id FROM asset_tags"
        ).fetchall() == [(100,)]
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()


def test_tags_are_normalized_and_lookups_use_the_indexes(db: Any) -> None:
    key = seed(db)
    db.insert_tag_info(key, ["valid"])
    with sqlite3.connect(db.db_filepath) as connection:
        assert connection.execute("SELECT tag FROM asset_tags").fetchall() == [
            ("valid",)
        ]
        connection.execute("UPDATE tag_info SET tag='changed'")
        assert connection.execute("SELECT tag FROM asset_tags").fetchall() == [
            ("changed",)
        ]
        latest_plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT MAX(id) FROM hda_history WHERE hda_key_id=?",
            (key,),
        ).fetchall()
        assert any("idx_history_asset_latest" in row[3] for row in latest_plan)
        reference_plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT video_dirpath FROM hda_history WHERE video_filename=? COLLATE NOCASE AND id != ?",
            ("video.mp4", 1),
        ).fetchall()
        assert any(
            "idx_hda_history_video_filename_reference" in row[3]
            for row in reference_plan
        )


def populated(db: Any, tmp_path: pathlib.Path) -> int:
    key = seed(db, "owner", "asset")
    assert db.insert_hda_info(key, "1.0", filename="asset.hda", dirpath=tmp_path) == 1
    assert (
        db.insert_hipfile_info(
            key,
            filename="scene.hip",
            dirpath=tmp_path,
            houdini_version="21",
            hda_license="commercial",
            operating_system="Linux",
            sf=-1.5,
            ef=100.25,
            fps=23.976,
        )
        == 1
    )
    assert db.insert_houdini_node_info(key, "box", "Box", False, False, "/obj/box")
    return key


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE hda_info SET load_count='bad'",
        "UPDATE hda_info SET load_count=1.5",
        "UPDATE hda_info SET load_count=-1",
        "UPDATE hda_info SET is_favorite=2",
        "UPDATE houdini_node_info SET is_network='true'",
        "UPDATE houdini_node_info SET is_sub_network=-1",
        "UPDATE hipfile_info SET fps=0",
        "UPDATE hipfile_info SET fps='bad'",
        "UPDATE hipfile_info SET fps=1e999",
        "UPDATE hipfile_info SET sf='bad'",
        "INSERT INTO houdini_node_input_connect_info VALUES (1,1,-1,'node','box',0)",
        "INSERT INTO houdini_node_output_connect_info VALUES (1,1,0,'node','box',0.5)",
    ],
)
def test_constraints_reject_invalid_writes(
    db: Any, tmp_path: pathlib.Path, mutation: str
) -> None:
    populated(db, tmp_path)
    with sqlite3.connect(db.db_filepath) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(mutation)


@pytest.mark.parametrize("identifier", [None, ""])
def test_operation_markers_require_nonempty_ids(
    db: Any, identifier: str | None
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db._connect.execute(
            "INSERT INTO operation_commits(operation_id) VALUES (?)", (identifier,)
        )
    db._connect.rollback()


def test_history_video_path_requires_both_components(
    db: Any, tmp_path: pathlib.Path
) -> None:
    key = populated(db, tmp_path)
    with sqlite3.connect(db.db_filepath) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        fields = {
            row[1]: "snapshot"
            for row in connection.execute("PRAGMA table_info(hda_history)")
        }
        fields.update(id=1, hda_key_id=key, video_filename=None, video_dirpath=None)
        columns = ",".join(fields)
        placeholders = ",".join("?" for _ in fields)
        connection.execute(
            f"INSERT INTO hda_history({columns}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE hda_history SET video_filename='only_filename.mp4'"
            )
        connection.rollback()
        connection.execute(
            "UPDATE hda_history SET video_filename='video.mp4', video_dirpath='/video'"
        )
        connection.commit()
