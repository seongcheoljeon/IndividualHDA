from __future__ import annotations

import pathlib
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest

from libs.database_migrations import SCHEMA_VERSION, migrate
from libs.sqlite3_db_api import SQLite3DatabaseAPI
from model.sqlite3_db_schema import db_schema


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


def test_legacy_upgrade_backs_up_and_preserves_rows(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(db_schema())
        connection.execute(
            "INSERT INTO users VALUES ('artist','a@example.com','2020-01-01')"
        )
        connection.commit()
        migrate(connection, path)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute("SELECT user_id FROM users").fetchone()[0] == "artist"
        migrate(connection, path)
    backups = list(tmp_path.glob("*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 0


def test_failed_migration_restores_original(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "orphan.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(db_schema())
        connection.execute("INSERT INTO hda_key VALUES (1,'bad','sop','missing')")
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError):
            migrate(connection, path)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='asset_tags'"
            ).fetchone()
            is None
        )
        assert connection.execute("SELECT name FROM hda_key").fetchone()[0] == "bad"


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


def test_base_schema_category_cleanup_scopes_owner() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(db_schema())
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


def test_v2_upgrade_repairs_derived_tags_and_installs_indexes(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "v2.db"
    with SQLite3DatabaseAPI(path) as db:
        key = seed(db)
        db.insert_tag_info(key, ["valid"])
        with db.transaction():
            db.record_operation_commit("preserved")
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO asset_tags VALUES (?, 'stale')", (key,))
        connection.execute("DROP INDEX idx_history_asset_latest")
        connection.execute("DROP INDEX idx_hda_history_video_filename_reference")
        connection.execute("DROP TRIGGER sync_tags_update")
        connection.execute("""CREATE TRIGGER sync_tags_update AFTER UPDATE ON tag_info
            BEGIN SELECT 1; END""")
        # Build a genuine pre-v5 database rather than only downgrading its version marker.
        for (name,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND (name LIKE 'v5_%' OR name LIKE 'v6_%')"
        ).fetchall():
            connection.execute(f'DROP TRIGGER "{name}"')
        for table in (
            "version_dependencies",
            "version_checks",
            "scene_usages",
            "tracking_requests",
            "registration_jobs",
            "version_files",
            "asset_user_preferences",
            "version_identity",
            "asset_identity",
            "audit_events",
            "usage_requests",
            "library_identity",
            "file_cleanup",
            "write_context",
            "migration_reports",
        ):
            connection.execute(f'DROP TABLE "{table}"')
        connection.execute("DROP INDEX idx_scene_record_version")
        for column in ("library_uuid", "asset_uuid", "version_uuid", "link_status"):
            connection.execute(
                f"ALTER TABLE hda_node_location_record DROP COLUMN {column}"
            )
        connection.execute("PRAGMA user_version=2")
        connection.commit()
        migrate(connection, path)
        assert connection.execute("SELECT tag FROM asset_tags").fetchall() == [
            ("valid",)
        ]
        assert connection.execute(
            "SELECT operation_id FROM operation_commits"
        ).fetchall() == [("preserved",)]
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
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
    backups = list(tmp_path.glob("v2.db.pre-v4-*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 2
        assert backup.execute("SELECT tag FROM asset_tags ORDER BY tag").fetchall() == [
            ("stale",),
            ("valid",),
        ]
