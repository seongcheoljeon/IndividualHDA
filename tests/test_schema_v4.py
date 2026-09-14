from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from libs.database_migrations import migrate, SCHEMA_VERSION


@pytest.fixture
def legacy(tmp_path: Path) -> tuple[sqlite3.Connection, Path]:
    path = tmp_path / "library.db"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        (Path(__file__).parent / "fixtures/schema_legacy.sql").read_text()
    )
    connection.execute("INSERT INTO users VALUES ('owner','email','2020-01-01')")
    connection.execute("INSERT INTO hda_category VALUES ('sop','owner')")
    connection.execute("INSERT INTO hda_key VALUES (1,'asset','sop','owner')")
    connection.execute("""INSERT INTO hda_info VALUES
        (1,1,'1.0',0,0,'asset.hda','/assets','2020-01-01','2020-01-01')""")
    connection.execute("""INSERT INTO hipfile_info VALUES
        (1,1,'scene.hip','/scene','21','commercial','Linux',-1.5,100.25,23.976)""")
    connection.execute(
        "INSERT INTO houdini_node_info VALUES (1,1,'box','Box',0,0,'/obj/box')"
    )
    connection.execute("INSERT INTO note_info VALUES (1,1,'note')")
    connection.execute("PRAGMA user_version=3")
    connection.commit()
    return connection, path


def test_rebuild_preserves_data_sequences_and_custom_objects(
    legacy: tuple[sqlite3.Connection, Path],
) -> None:
    connection, path = legacy
    with connection:
        connection.execute("INSERT INTO hda_key VALUES (900,'deleted','sop','owner')")
        connection.execute("DELETE FROM hda_key WHERE id=900")
        connection.execute("CREATE TABLE custom_audit (name TEXT)")
        connection.execute("CREATE VIEW custom_assets AS SELECT id,name FROM hda_key")
        connection.execute("CREATE VIEW nested_assets AS SELECT * FROM custom_assets")
        connection.execute("CREATE INDEX custom_name_idx ON hda_key(name)")
        connection.execute("""CREATE TRIGGER custom_insert AFTER INSERT ON hda_key
            BEGIN INSERT INTO custom_audit VALUES (new.name); END""")
    before = connection.execute("SELECT * FROM hda_note_history").fetchall()
    migrate(connection, path)
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert connection.execute("SELECT * FROM hda_note_history").fetchall() == before
    assert connection.execute("SELECT sf,ef,fps FROM hipfile_info").fetchone() == (
        -1.5,
        100.25,
        23.976,
    )
    assert connection.execute("SELECT * FROM nested_assets").fetchall() == [
        (1, "asset")
    ]
    assert connection.execute("SELECT * FROM custom_audit").fetchall() == []
    connection.execute(
        "INSERT INTO hda_key(name,category,user_id) VALUES ('next','sop','owner')"
    )
    assert (
        connection.execute("SELECT id FROM hda_key WHERE name='next'").fetchone()[0]
        == 901
    )
    assert connection.execute("SELECT * FROM custom_audit").fetchall() == [("next",)]
    for table in ("hda_history", "hda_note_history", "houdini_node_input_connect_info"):
        assert not any(
            row[3] == "u" for row in connection.execute(f"PRAGMA index_list({table})")
        )
    connection.rollback()
    migrate(connection, path)
    assert len(list(path.parent.glob("*.bak"))) == 1
    connection.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE hda_info SET load_count='garbage'",
        "UPDATE hipfile_info SET fps=0",
        "ALTER TABLE video_info ADD COLUMN custom_data TEXT",
    ],
)
def test_invalid_legacy_data_or_columns_roll_back_entire_upgrade(
    legacy: tuple[sqlite3.Connection, Path], mutation: str
) -> None:
    connection, path = legacy
    connection.execute(mutation)
    connection.commit()
    before = list(connection.iterdump())
    with pytest.raises(sqlite3.DatabaseError):
        migrate(connection, path)
    assert list(connection.iterdump()) == before
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert len(list(path.parent.glob("*.pre-v4-*.bak"))) == 1
    connection.close()


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
    legacy: tuple[sqlite3.Connection, Path], mutation: str
) -> None:
    connection, path = legacy
    migrate(connection, path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(mutation)
    connection.rollback()
    assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    connection.close()


def test_migration_rejects_active_transaction_without_committing(
    legacy: tuple[sqlite3.Connection, Path],
) -> None:
    connection, path = legacy
    connection.execute("UPDATE hda_key SET name='pending'")
    with pytest.raises(sqlite3.ProgrammingError, match="active transaction"):
        migrate(connection, path)
    assert connection.in_transaction
    connection.rollback()
    assert connection.execute("SELECT name FROM hda_key").fetchone()[0] == "asset"
    assert not list(path.parent.glob("*.bak"))
    connection.close()


@pytest.mark.parametrize("identifier", [None, ""])
def test_operation_markers_require_nonempty_ids(
    legacy: tuple[sqlite3.Connection, Path], identifier: str | None
) -> None:
    connection, path = legacy
    migrate(connection, path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO operation_commits(operation_id) VALUES (?)", (identifier,)
        )
    connection.rollback()
    connection.close()


def test_history_video_path_requires_both_components(
    legacy: tuple[sqlite3.Connection, Path],
) -> None:
    connection, path = legacy
    migrate(connection, path)
    fields = {
        row[1]: "snapshot"
        for row in connection.execute("PRAGMA table_info(hda_history)")
    }
    fields.update(id=1, hda_key_id=1, video_filename=None, video_dirpath=None)
    columns = ",".join(fields)
    placeholders = ",".join("?" for _ in fields)
    connection.execute(
        f"INSERT INTO hda_history({columns}) VALUES ({placeholders})",
        tuple(fields.values()),
    )
    connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("UPDATE hda_history SET video_filename='only_filename.mp4'")
    connection.rollback()
    connection.execute(
        "UPDATE hda_history SET video_filename='video.mp4', video_dirpath='/video'"
    )
    connection.commit()
    connection.close()
