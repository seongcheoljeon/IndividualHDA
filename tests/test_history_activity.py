"""Audit events become non-version history rows; personal and team shapes."""

from __future__ import annotations

import json
from datetime import datetime

from libs import keys
from libs.asset_contracts import HistoryData
from libs.history_activity import (
    activity_rows,
    changes,
    merge_history_rows,
    rename_names,
    video_action,
)

TEAM_RENAME = {
    "operation": "rename",
    "changes": {"name": {"before": "fire_presets1", "after": "preset_tmp"}},
}
PERSONAL_RENAME = {
    "operation": "hda_key.update",
    "changes": json.dumps(
        {
            "before": {"name": "fire_presets1", "category": "sop"},
            "after": {"name": "preset_tmp", "category": "sop"},
        }
    ),
}
PERSONAL_CATEGORY_ONLY = {
    "operation": "hda_key.update",
    "changes": json.dumps(
        {
            "before": {"name": "a", "category": "sop"},
            "after": {"name": "a", "category": "obj"},
        }
    ),
}
TEAM_VIDEO_INSERT = {
    "operation": "media",
    "changes": {
        "files": {"before": {"asset": "x"}, "after": {"asset": "x", "video": "v1"}}
    },
}
TEAM_VIDEO_UPDATE = {
    "operation": "media",
    "changes": {
        "files": {
            "before": {"asset": "x", "video": "v1"},
            "after": {"asset": "x", "video": "v2"},
        }
    },
}
TEAM_THUMBNAIL = {
    "operation": "media",
    "changes": {
        "files": {"before": {"asset": "x"}, "after": {"asset": "x", "thumbnail": "t"}}
    },
}


def test_changes_accepts_json_text_dicts_and_garbage() -> None:
    assert changes({"changes": '{"a": 1}'}) == {"a": 1}
    assert changes({"changes": {"a": 1}}) == {"a": 1}
    assert changes({"changes": "not json"}) == {}
    assert changes({"changes": "[1]"}) == {}
    assert changes({}) == {}


def test_rename_names_reads_both_libraries_and_ignores_category_edits() -> None:
    assert rename_names(TEAM_RENAME) == ("fire_presets1", "preset_tmp")
    assert rename_names(PERSONAL_RENAME) == ("fire_presets1", "preset_tmp")
    assert rename_names(PERSONAL_CATEGORY_ONLY) is None
    assert rename_names({"operation": "metadata", "changes": {"tags": {}}}) is None


def test_video_action_tells_attach_from_replace() -> None:
    assert video_action({"operation": "video_info.insert"}) == "insert"
    assert video_action({"operation": "video_info.update"}) == "update"
    assert video_action(TEAM_VIDEO_INSERT) == "insert"
    assert video_action(TEAM_VIDEO_UPDATE) == "update"
    assert video_action(TEAM_THUMBNAIL) is None
    assert video_action(TEAM_RENAME) is None


def test_activity_rows_are_local_time_non_version_rows() -> None:
    stamp = "2026-09-17T05:57:11.123Z"
    rows = activity_rows(
        [
            {
                **PERSONAL_RENAME,
                "occurred_at": stamp,
                "actor": "tester",
                "hda_id": 3,
                "org_hda_name": "preset_tmp",
                "node_category": "sop",
            },
            {
                "operation": "video_info.insert",
                "changes": "{}",
                "occurred_at": "2026-09-17T06:00:00+00:00",
                "actor": "tester",
                "hda_id": 3,
            },
        ],
        remote=True,
        library_id="team-1",
    )
    assert [row.comment for row in rows] == [
        "NAME (CHANGE) fire_presets1 → preset_tmp",
        "VIDEO (INSERT)",
    ]
    assert [row.kind for row in rows] == ["rename", "video"]
    expected = datetime.fromisoformat(stamp).astimezone()
    assert rows[0].reg_time == expected.strftime(keys.Value.datetime_fmt_str)
    for row in rows:
        assert not row.is_version and row.hist_id == 0 and row.version == ""
        assert row.ihda_dirpath is None and row.thumb_filename is None
        assert row.remote and row.library_id == "team-1"
        assert row.hda_id == 3 and row.userid == "tester"


def test_activity_rows_drop_the_video_move_that_accompanies_a_rename() -> None:
    shared = {"occurred_at": "2026-09-17T05:57:11Z", "actor": "tester", "hda_id": 1}
    rows = activity_rows(
        [
            {**PERSONAL_RENAME, **shared, "request_id": "req-1"},
            {
                "operation": "video_info.update",
                "changes": "{}",
                **shared,
                "request_id": "req-1",
            },
            {
                "operation": "video_info.update",
                "changes": "{}",
                **shared,
                "request_id": "req-2",
            },
            {**PERSONAL_CATEGORY_ONLY, **shared, "request_id": "req-3"},
        ]
    )
    assert [row.comment for row in rows] == [
        "NAME (CHANGE) fire_presets1 → preset_tmp",
        "VIDEO (UPDATE)",
    ]


def test_merge_interleaves_by_time_and_keeps_versions_first_on_ties() -> None:
    def row(kind: str, when: str, hist_id: int = 0) -> HistoryData:
        return HistoryData(
            kind=kind,
            hist_id=hist_id,
            hda_id=1,
            org_hda_name="a",
            version="",
            reg_time=when,
        )

    versions = [
        row("version", "2026-01-01 10:00:00", 1),
        row("version", "2026-01-03 10:00:00", 2),
    ]
    activity = [
        row("rename", "2026-01-02 10:00:00"),
        row("video", "2026-01-03 10:00:00"),
    ]
    merged = merge_history_rows(versions, activity)
    assert [(r.kind, r.hist_id) for r in merged] == [
        ("version", 1),
        ("rename", 0),
        ("version", 2),
        ("video", 0),
    ]


def test_history_rows_are_versions_unless_marked() -> None:
    assert HistoryData(hda_id=1, org_hda_name="a", version="1.0").is_version
    assert activity_rows([]) == []
