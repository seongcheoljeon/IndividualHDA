"""The personal library's SQLite schema, complete and in one place.

Every table, index, trigger and seed row the application relies on is created
here, in ``install``. ``SCHEMA_VERSION`` is stamped into ``PRAGMA user_version``
and compared on every open: a file at another version is never upgraded in
place. ``ensure_schema`` backs it up next to itself and starts fresh. So a
schema change is a change in this module plus a higher ``SCHEMA_VERSION``, and
nothing else; the library files on disk are untouched either way.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from libs.database.backup import backup_database
from libs.library_metadata import file_stamp, new_identity

SCHEMA_VERSION = 8

UUID_SQL = "(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-a' || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6))))"
# The clock of every audit and file-reference row; PersonalLifecycle uses it too.
NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"

# --- the library: users, assets, versions and what Houdini told us ------------

BASE_TABLES = (
    """CREATE TABLE operation_commits
(
    operation_id TEXT NOT NULL PRIMARY KEY CHECK(length(operation_id) > 0),
    committed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);""",
    """CREATE TABLE users
(
    user_id       TEXT NOT NULL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    join_datetime TEXT     NOT NULL
);""",
    """CREATE TABLE hda_category
(
    category TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    PRIMARY KEY (category, user_id),
    CONSTRAINT FK_hda_category_users_user_id FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE hda_key
(
    id       INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    UNIQUE (name, category, user_id),
    CONSTRAINT FK_hda_key_hda_category FOREIGN KEY (category, user_id)
        REFERENCES hda_category (category, user_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE hda_history
(
    id                    INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id            INTEGER      NOT NULL,
    comment               TEXT         NOT NULL,
    org_hda_name          TEXT NOT NULL,
    version               TEXT NOT NULL,
    hda_filename          TEXT NOT NULL,
    hda_dirpath           TEXT NOT NULL,
    registration_datetime TEXT     NOT NULL,
    houdini_version       TEXT NOT NULL,
    hip_filename          TEXT NOT NULL,
    hip_dirpath           TEXT NOT NULL,
    hda_license           TEXT NOT NULL,
    operating_system      TEXT NOT NULL,
    node_old_path         TEXT NOT NULL,
    node_def_desc         TEXT NOT NULL,
    node_type_name        TEXT NOT NULL,
    node_category         TEXT NOT NULL,
    userid                TEXT NOT NULL,
    icon                  TEXT NOT NULL,
    thumb_filename        TEXT NOT NULL,
    thumb_dirpath         TEXT NOT NULL,
    video_filename        TEXT DEFAULT NULL,
    video_dirpath         TEXT DEFAULT NULL,
    CHECK ((video_filename IS NULL) = (video_dirpath IS NULL)),
    CONSTRAINT FK_hda_history_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id)
        ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE hda_node_location_record
(
    id               INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id       INTEGER      NOT NULL,
    hip_filename     TEXT NOT NULL,
    hip_dirpath      TEXT NOT NULL,
    hda_filename     TEXT NOT NULL,
    hda_dirpath      TEXT NOT NULL,
    parent_node_path TEXT NOT NULL,
    node_type        TEXT NOT NULL,
    node_category    TEXT NOT NULL,
    node_name        TEXT NOT NULL,
    node_version     TEXT NOT NULL,
    houdini_version  TEXT NOT NULL,
    houdini_license  TEXT NOT NULL,
    operating_system TEXT NOT NULL,
    sf               REAL      NOT NULL CHECK(typeof(sf) = 'real' AND abs(sf) <= 1.7976931348623157e308),
    ef               REAL      NOT NULL CHECK(typeof(ef) = 'real' AND abs(ef) <= 1.7976931348623157e308),
    fps              REAL      NOT NULL CHECK(typeof(fps) = 'real' AND abs(fps) <= 1.7976931348623157e308 AND fps > 0),
    ctime            TEXT     NOT NULL,
    mtime            TEXT     NOT NULL,
    library_uuid     TEXT,
    asset_uuid       TEXT,
    version_uuid     TEXT,
    link_status      TEXT     NOT NULL DEFAULT 'unresolved',
    CONSTRAINT FK_hda_node_location_record_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE hda_note_history
(
    id                    INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id            INTEGER      NOT NULL,
    note                  TEXT         NOT NULL,
    registration_datetime TEXT     NOT NULL,
    hda_version           TEXT NOT NULL,
    CONSTRAINT FK_hda_note_history_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE hda_info
(
    id                             INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id                     INTEGER      NOT NULL,
    version                        TEXT NOT NULL,
    is_favorite                    INTEGER      NOT NULL DEFAULT 0 CHECK(typeof(is_favorite) = 'integer' AND is_favorite IN (0, 1)),
    load_count                     INTEGER      NOT NULL CHECK(typeof(load_count) = 'integer' AND load_count >= 0),
    filename                       TEXT NOT NULL,
    dirpath                        TEXT NOT NULL,
    initial_registration_datetime  TEXT     NOT NULL,
    modified_registration_datetime TEXT     NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_hda_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE hipfile_info
(
    id               INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id       INTEGER      NOT NULL,
    filename         TEXT NOT NULL,
    dirpath          TEXT NOT NULL,
    houdini_version  TEXT NOT NULL,
    hda_license      TEXT NOT NULL,
    operating_system TEXT NOT NULL,
    sf               REAL      NOT NULL CHECK(typeof(sf) = 'real' AND abs(sf) <= 1.7976931348623157e308),
    ef               REAL      NOT NULL CHECK(typeof(ef) = 'real' AND abs(ef) <= 1.7976931348623157e308),
    fps              REAL      NOT NULL CHECK(typeof(fps) = 'real' AND abs(fps) <= 1.7976931348623157e308 AND fps > 0),
    UNIQUE (hda_key_id),
    CONSTRAINT FK_hipfile_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE houdini_node_info
(
    id             INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id     INTEGER      NOT NULL,
    node_type_name TEXT NOT NULL,
    node_def_desc  TEXT NOT NULL,
    is_network     INTEGER      NOT NULL CHECK(typeof(is_network) = 'integer' AND is_network IN (0, 1)),
    is_sub_network INTEGER      NOT NULL CHECK(typeof(is_sub_network) = 'integer' AND is_sub_network IN (0, 1)),
    node_old_path  TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_houdini_node_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE houdini_node_category_path_info
(
    id            INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id       INTEGER      NOT NULL,
    node_category TEXT NOT NULL,
    CONSTRAINT FK_houdini_node_category_path_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE houdini_node_type_path_info
(
    id        INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id   INTEGER      NOT NULL,
    node_type TEXT NOT NULL,
    CONSTRAINT FK_houdini_node_type_path_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE houdini_node_input_connect_info
(
    id                  INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id             INTEGER      NOT NULL,
    curt_node_input_idx INTEGER      NOT NULL CHECK(typeof(curt_node_input_idx) = 'integer' AND curt_node_input_idx >= 0),
    connect_node_name   TEXT NOT NULL,
    connect_node_type   TEXT NOT NULL,
    connect_output_idx  INTEGER      NOT NULL CHECK(typeof(connect_output_idx) = 'integer' AND connect_output_idx >= 0),
    CONSTRAINT FK_houdini_node_input_connect_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE houdini_node_output_connect_info
(
    id                   INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id              INTEGER      NOT NULL,
    curt_node_output_idx INTEGER      NOT NULL CHECK(typeof(curt_node_output_idx) = 'integer' AND curt_node_output_idx >= 0),
    connect_node_name    TEXT NOT NULL,
    connect_node_type    TEXT NOT NULL,
    connect_input_idx    INTEGER      NOT NULL CHECK(typeof(connect_input_idx) = 'integer' AND connect_input_idx >= 0),
    CONSTRAINT FK_houdini_node_output_connect_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE icon_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    icon       TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_icon_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE tag_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    tag        TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_tag_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE note_info
(
    id         INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER NOT NULL,
    note       TEXT    NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_note_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE thumbnail_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    filename   TEXT NOT NULL,
    dirpath    TEXT NOT NULL,
    version    TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_thumbnail_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TABLE video_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    filename   TEXT NOT NULL,
    dirpath    TEXT NOT NULL,
    version    TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_video_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);""",
    """CREATE TRIGGER insert_trg_hda_note_history
    AFTER
        INSERT
    ON note_info
    FOR EACH ROW
BEGIN
    INSERT INTO hda_note_history
        (hda_key_id, note, registration_datetime, hda_version)
    VALUES (
        new.hda_key_id,
        (SELECT note FROM note_info WHERE note_info.hda_key_id = new.hda_key_id),
        (SELECT DATETIME('now', 'localtime')),
        (SELECT version FROM hda_info WHERE hda_info.hda_key_id = new.hda_key_id)
    );
END;""",
    """CREATE TRIGGER update_trg_hda_note_history
    AFTER
        UPDATE
    ON note_info
    FOR EACH ROW
BEGIN
    INSERT INTO hda_note_history
        (hda_key_id, note, registration_datetime, hda_version)
    VALUES (
        new.hda_key_id,
        (SELECT note FROM note_info WHERE note_info.hda_key_id = new.hda_key_id),
        (SELECT DATETIME('now', 'localtime')),
        (SELECT version FROM hda_info WHERE hda_info.hda_key_id = new.hda_key_id)
    );
END;""",
    """CREATE TRIGGER update_trg_hda_node_location_record
    AFTER
        UPDATE
    ON hda_info
    FOR EACH ROW
BEGIN
    UPDATE hda_node_location_record SET
        hda_dirpath = new.dirpath,
        node_name = (SELECT hda_key.name FROM hda_key WHERE hda_node_location_record.hda_key_id = hda_key.id)
    WHERE hda_key_id = new.hda_key_id;
    UPDATE hda_node_location_record SET hda_filename = new.filename
    WHERE hda_key_id = new.hda_key_id AND node_version = new.version;
END;""",
    """CREATE TRIGGER delete_trg_unused_hda_category
    AFTER DELETE ON hda_key
    FOR EACH ROW
BEGIN
    DELETE FROM hda_category
    WHERE category = old.category AND user_id = old.user_id
      AND NOT EXISTS (
          SELECT 1 FROM hda_key
          WHERE category = old.category AND user_id = old.user_id
      );
END;""",
)

LOOKUP_INDEXES = {
    "hda_key": "user_id, category",
    "hda_history": "hda_key_id, version, id",
    "hda_note_history": "hda_key_id, hda_version, id",
    "hda_node_location_record": "hda_key_id, hip_dirpath, hip_filename",
    "houdini_node_category_path_info": "info_id",
    "houdini_node_type_path_info": "info_id",
    "houdini_node_input_connect_info": "info_id",
    "houdini_node_output_connect_info": "info_id",
}
# Reference lookups (which rows point at this file?) are case-insensitive.
REFERENCE_INDEXES = {
    "hda_info": ("filename",),
    "thumbnail_info": ("filename",),
    "video_info": ("filename",),
    "hda_history": ("hda_filename", "thumb_filename", "video_filename"),
}
# tag_info keeps the legacy '#'-joined text; asset_tags is its indexed, per-tag
# projection, maintained by triggers for every writer.
TAG_SPLIT = """INSERT OR IGNORE INTO asset_tags(hda_key_id, tag)
    WITH RECURSIVE split(id, tag, rest) AS (
        SELECT hda_key_id, '', tag || '#' FROM tag_info {where}
        UNION ALL SELECT id, substr(rest, 1, instr(rest, '#') - 1),
            substr(rest, instr(rest, '#') + 1) FROM split WHERE rest <> ''
    ) SELECT id, trim(tag) FROM split WHERE trim(tag) <> '';"""

# --- identity, lifecycle, audit and file references ---------------------------

STATE_TABLES = (
    "CREATE TABLE write_context (singleton INTEGER PRIMARY KEY CHECK(singleton=1), request_id TEXT, maintenance INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE library_identity (singleton INTEGER PRIMARY KEY CHECK(singleton=1), uuid TEXT NOT NULL UNIQUE)",
    """CREATE TABLE asset_identity (
        asset_id INTEGER PRIMARY KEY REFERENCES hda_key(id) ON UPDATE CASCADE ON DELETE CASCADE,
        uuid TEXT NOT NULL UNIQUE, current_version_uuid TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT,
        deleted_at TEXT, deleted_by TEXT, provenance TEXT NOT NULL DEFAULT '{}')""",
    """CREATE TABLE version_identity (
        history_id INTEGER PRIMARY KEY REFERENCES hda_history(id) ON UPDATE CASCADE ON DELETE CASCADE,
        uuid TEXT NOT NULL UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, deleted_by TEXT,
        details TEXT NOT NULL DEFAULT '{"metadata_schema":1,"dependencies":[],"dependency_status":"unknown","compatibility_status":"unverified"}')""",
    """CREATE TABLE asset_user_preferences (
        asset_id INTEGER NOT NULL REFERENCES hda_key(id) ON UPDATE CASCADE ON DELETE CASCADE,
        user_id TEXT NOT NULL REFERENCES users(user_id) ON UPDATE CASCADE,
        favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1)),
        use_count INTEGER NOT NULL DEFAULT 0 CHECK(use_count>=0),
        last_used_at TEXT, revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
        PRIMARY KEY(asset_id,user_id))""",
    """CREATE TABLE audit_events (
        id TEXT PRIMARY KEY, asset_uuid TEXT, version_uuid TEXT, actor TEXT,
        occurred_at TEXT NOT NULL, request_id TEXT, operation TEXT NOT NULL, changes TEXT NOT NULL)""",
    "CREATE INDEX idx_audit_asset ON audit_events(asset_uuid,occurred_at)",
    "CREATE TABLE usage_requests (request_id TEXT PRIMARY KEY, asset_uuid TEXT NOT NULL, user_id TEXT NOT NULL)",
    """CREATE TABLE version_files (
        history_id INTEGER NOT NULL REFERENCES hda_history(id) ON UPDATE CASCADE ON DELETE CASCADE,
        kind TEXT NOT NULL, directory TEXT NOT NULL, filename TEXT NOT NULL,
        digest TEXT, size INTEGER CHECK(size>=0), registered_at TEXT,
        checked_at TEXT, status TEXT NOT NULL DEFAULT 'unverified', PRIMARY KEY(history_id,kind))""",
    "CREATE TABLE file_cleanup (path TEXT PRIMARY KEY, error TEXT)",
    "CREATE INDEX idx_version_files_reference ON version_files(directory,filename)",
)

# --- version tracking: dependencies, checks, scene usage, registration jobs --

TRACKING_TABLES = (
    """CREATE TABLE version_dependencies (scope_id TEXT NOT NULL, source_uuid TEXT NOT NULL,
    ordinal INTEGER NOT NULL, target_scope TEXT, target_asset TEXT, target_version TEXT,
    kind TEXT NOT NULL, target TEXT NOT NULL, version TEXT NOT NULL, required INTEGER NOT NULL CHECK(required IN (0,1)),
    source TEXT NOT NULL, PRIMARY KEY(scope_id,source_uuid,ordinal))""",
    "CREATE INDEX idx_dependency_target ON version_dependencies(target_scope,target_asset,target_version)",
    """CREATE TABLE version_checks (scope_id TEXT NOT NULL, id TEXT NOT NULL, version_uuid TEXT NOT NULL,
    asset_uuid TEXT NOT NULL, actor TEXT NOT NULL, checked_at TEXT NOT NULL, created_at TEXT NOT NULL,
    document TEXT NOT NULL, PRIMARY KEY(scope_id,id))""",
    "CREATE INDEX idx_checks_version ON version_checks(scope_id,version_uuid,created_at,id)",
    """CREATE TABLE scene_usages (scope_id TEXT NOT NULL,id TEXT NOT NULL,actor TEXT NOT NULL,
    client_id TEXT NOT NULL,scene_key TEXT NOT NULL,node_path TEXT NOT NULL,asset_uuid TEXT NOT NULL,
    version_uuid TEXT NOT NULL,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,document TEXT NOT NULL,
    PRIMARY KEY(scope_id,id),UNIQUE(scope_id,actor,client_id,scene_key,node_path,version_uuid))""",
    "CREATE INDEX idx_scene_version ON scene_usages(scope_id,asset_uuid,version_uuid,last_seen,id)",
    """CREATE TABLE tracking_requests (scope_id TEXT NOT NULL,actor TEXT NOT NULL,id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(scope_id,actor,id))""",
    """CREATE TABLE registration_jobs (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
    phase TEXT NOT NULL, document TEXT NOT NULL, result TEXT, error TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    "CREATE INDEX idx_scene_record_version ON hda_node_location_record(version_uuid)",
)

# Which tables write an audit_events row, keyed by the column that names the
# asset, with the fields whose change is worth a row.
AUDITED_TABLES = (
    ("hda_key", "id", ("name", "category")),
    ("hda_info", "hda_key_id", ("version", "filename", "dirpath")),
    ("note_info", "hda_key_id", ("note",)),
    ("tag_info", "hda_key_id", ("tag",)),
    (
        "hda_history",
        "hda_key_id",
        ("version", "comment", "hda_filename", "hda_dirpath"),
    ),
    ("thumbnail_info", "hda_key_id", ("filename", "dirpath", "version")),
    ("video_info", "hda_key_id", ("filename", "dirpath", "version")),
)
# Writes to these are refused while the asset is in the trash.
TRASH_GUARDED_TABLES = (
    "hda_info",
    "note_info",
    "tag_info",
    "thumbnail_info",
    "video_info",
    "hipfile_info",
    "houdini_node_info",
    "hda_history",
)


def audit_trigger_sql(
    name: str, table: str, key: str, fields: tuple[str, ...], action: str
) -> str:
    """CREATE TRIGGER that writes an audit_events row after INSERT/UPDATE.

    An UPDATE fires only when one of ``fields`` changed; ``changes`` carries the
    before/after values of those fields.
    """
    old_json = (
        "'{}'"
        if action == "INSERT"
        else "json_object(" + ",".join(f"'{f}',old.{f}" for f in fields) + ")"
    )
    new_json = "json_object(" + ",".join(f"'{f}',new.{f}" for f in fields) + ")"
    when = (
        ""
        if action == "INSERT"
        else "WHEN " + " OR ".join(f"old.{f} IS NOT new.{f}" for f in fields)
    )
    return f"""CREATE TRIGGER {name} AFTER {action} ON {table} {when} BEGIN
        INSERT INTO audit_events(id,asset_uuid,actor,occurred_at,request_id,operation,changes)
        SELECT {UUID_SQL},uuid,(SELECT user_id FROM hda_key WHERE id=new.{key}),{NOW_SQL},COALESCE((SELECT request_id FROM write_context),{UUID_SQL}),
        '{table}.{action.lower()}',json_object('before',json({old_json}),'after',json({new_json}))
        FROM asset_identity WHERE asset_id=new.{key}; END"""


def _index_statements() -> list[str]:
    statements = [
        f"CREATE INDEX idx_{table}_lookup ON {table} ({columns})"
        for table, columns in LOOKUP_INDEXES.items()
    ]
    statements += [
        "CREATE INDEX idx_history_user_date ON hda_history(userid, registration_datetime)",
        "CREATE INDEX idx_history_asset_latest ON hda_history(hda_key_id, id)",
        """CREATE TABLE asset_tags (
            hda_key_id INTEGER NOT NULL REFERENCES hda_key(id) ON UPDATE CASCADE ON DELETE CASCADE,
            tag TEXT NOT NULL CHECK(length(tag) > 0), PRIMARY KEY(hda_key_id, tag))""",
        "CREATE INDEX idx_asset_tags_text ON asset_tags(tag COLLATE NOCASE, hda_key_id)",
    ]
    for table, columns in REFERENCE_INDEXES.items():
        for column in columns:
            statements.append(
                f"CREATE INDEX idx_{table}_{column}_reference ON {table}({column} COLLATE NOCASE)"
            )
    return statements


def _trigger_statements() -> list[str]:
    statements = []
    for action in ("INSERT", "UPDATE"):
        previous = "old.hda_key_id, " if action == "UPDATE" else ""
        statements.append(f"""CREATE TRIGGER sync_tags_{action.lower()}
            AFTER {action} ON tag_info BEGIN
            DELETE FROM asset_tags WHERE hda_key_id IN ({previous}new.hda_key_id);
            {TAG_SPLIT.format(where="WHERE hda_key_id = new.hda_key_id")}
            END""")
    statements.append("""CREATE TRIGGER sync_tags_delete AFTER DELETE ON tag_info
        BEGIN DELETE FROM asset_tags WHERE hda_key_id = old.hda_key_id; END""")
    # version_files mirrors the three files a history row names.
    for kind, directory, filename in (
        ("asset", "hda_dirpath", "hda_filename"),
        ("thumbnail", "thumb_dirpath", "thumb_filename"),
        ("video", "video_dirpath", "video_filename"),
    ):
        for action in ("INSERT", "UPDATE"):
            condition = (
                ""
                if action == "INSERT"
                else f"WHEN old.{directory} IS NOT new.{directory} OR old.{filename} IS NOT new.{filename}"
            )
            statements.append(f"""CREATE TRIGGER files_{kind}_{action.lower()} AFTER {action} ON hda_history {condition} BEGIN
                DELETE FROM version_files WHERE history_id=new.id AND kind='{kind}' AND (new.{directory} IS NULL OR new.{filename} IS NULL);
                INSERT INTO version_files(history_id,kind,directory,filename,registered_at)
                SELECT new.id,'{kind}',new.{directory},new.{filename},{NOW_SQL}
                WHERE new.{directory} IS NOT NULL AND new.{filename} IS NOT NULL
                ON CONFLICT(history_id,kind) DO UPDATE SET directory=excluded.directory,filename=excluded.filename;
            END""")
    # Every asset and every version gets a UUID; a new version becomes current
    # unless the current one already carries that version label.
    statements.append(f"""CREATE TRIGGER asset_identity_insert AFTER INSERT ON hda_key BEGIN
        INSERT INTO asset_identity(asset_id,uuid,created_at) VALUES(new.id,{UUID_SQL},{NOW_SQL}); END""")
    statements.append(f"""CREATE TRIGGER version_identity_insert AFTER INSERT ON hda_history BEGIN
        INSERT INTO version_identity(history_id,uuid,created_at) VALUES(new.id,{UUID_SQL},{NOW_SQL});
        UPDATE asset_identity SET current_version_uuid=(SELECT uuid FROM version_identity WHERE history_id=new.id)
        WHERE asset_id=new.hda_key_id AND (current_version_uuid IS NULL OR NOT EXISTS(
            SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE v.uuid=current_version_uuid AND h.version=new.version))
        AND EXISTS(SELECT 1 FROM hda_info WHERE hda_key_id=new.hda_key_id AND version=new.version); END""")
    # hda_info.is_favorite/load_count are legacy projections of the preferences.
    for action in ("INSERT", "UPDATE OF is_favorite,load_count"):
        name = action.split()[0].lower()
        statements.append(f"""CREATE TRIGGER preferences_{name} AFTER {action} ON hda_info BEGIN
            INSERT INTO asset_user_preferences(asset_id,user_id,favorite,use_count)
            SELECT new.hda_key_id,user_id,new.is_favorite,new.load_count FROM hda_key WHERE id=new.hda_key_id
            ON CONFLICT(asset_id,user_id) DO UPDATE SET favorite=excluded.favorite,use_count=excluded.use_count;
        END""")
    for table, key, fields in AUDITED_TABLES:
        for action in ("INSERT", "UPDATE"):
            # An asset's creation is the identity trigger's event below.
            if table == "hda_key" and action == "INSERT":
                continue
            statements.append(
                audit_trigger_sql(
                    f"audit_{table}_{action.lower()}", table, key, fields, action
                )
            )
    statements.append(f"""CREATE TRIGGER audit_create AFTER INSERT ON asset_identity BEGIN
        INSERT INTO audit_events(id,asset_uuid,actor,occurred_at,request_id,operation,changes)
        SELECT {UUID_SQL},new.uuid,user_id,{NOW_SQL},COALESCE((SELECT request_id FROM write_context),{UUID_SQL}),'create',json_object('name',name) FROM hda_key WHERE id=new.asset_id; END""")
    for table in TRASH_GUARDED_TABLES:
        for event in ("INSERT", "UPDATE"):
            statements.append(f"""CREATE TRIGGER reject_deleted_{table}_{event.lower()} BEFORE {event} ON {table}
                WHEN (SELECT maintenance FROM write_context)=0 AND EXISTS(SELECT 1 FROM asset_identity WHERE asset_id=new.hda_key_id AND deleted_at IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'Asset is in the trash'); END""")
    statements.append("""CREATE TRIGGER audit_time AFTER INSERT ON audit_events BEGIN
        UPDATE asset_identity SET updated_at=new.occurred_at WHERE uuid=new.asset_uuid; END""")
    # A preview written for the current version is copied onto that version's
    # history row, and the file reference goes back to unverified.
    for table, prefix, kind in (
        ("thumbnail_info", "thumb", "thumbnail"),
        ("video_info", "video", "video"),
    ):
        for event in ("INSERT", "UPDATE"):
            statements.append(f"""CREATE TRIGGER snapshot_{table}_{event.lower()} AFTER {event} ON {table} BEGIN
                UPDATE hda_history SET {prefix}_dirpath=new.dirpath,{prefix}_filename=new.filename
                WHERE id=(SELECT v.history_id FROM version_identity v JOIN asset_identity a ON a.current_version_uuid=v.uuid
                          WHERE a.asset_id=new.hda_key_id) AND version=new.version;
                UPDATE version_files SET digest=NULL,size=NULL,status='unverified',checked_at=NULL
                WHERE kind='{kind}' AND history_id=(SELECT v.history_id FROM version_identity v JOIN asset_identity a ON a.current_version_uuid=v.uuid
                          JOIN hda_history h ON h.id=v.history_id WHERE a.asset_id=new.hda_key_id AND h.version=new.version);
            END""")
    # The current version must be one of the asset's own, active versions.
    for action in ("INSERT", "UPDATE OF current_version_uuid"):
        statements.append(f"""CREATE TRIGGER current_{action.split()[0].lower()} BEFORE {action} ON asset_identity
        WHEN new.current_version_uuid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id
        WHERE v.uuid=new.current_version_uuid AND h.hda_key_id=new.asset_id AND v.deleted_at IS NULL)
        BEGIN SELECT RAISE(ABORT,'Current version must belong to this asset and be active'); END""")
    statements.append("""CREATE TRIGGER protect_current BEFORE UPDATE OF deleted_at ON version_identity WHEN new.deleted_at IS NOT NULL AND EXISTS(
        SELECT 1 FROM asset_identity WHERE current_version_uuid=new.uuid)
        BEGIN SELECT RAISE(ABORT,'Cannot trash current version'); END""")
    statements.append("""CREATE TRIGGER dependency_cleanup AFTER DELETE ON version_identity BEGIN
        DELETE FROM version_dependencies WHERE source_uuid=old.uuid; END""")
    statements.append("""CREATE TRIGGER clear_current AFTER DELETE ON version_identity BEGIN
        UPDATE asset_identity SET current_version_uuid=NULL WHERE current_version_uuid=old.uuid; END""")
    # A scene record may only link a version of its own asset in this library.
    for action in (
        "INSERT",
        "UPDATE OF version_uuid,asset_uuid,library_uuid,hda_key_id",
    ):
        statements.append(f"""CREATE TRIGGER scene_{action.split()[0].lower()} BEFORE {action} ON hda_node_location_record
        WHEN new.version_uuid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id
        JOIN asset_identity a ON a.asset_id=h.hda_key_id WHERE v.uuid=new.version_uuid AND a.uuid=new.asset_uuid
        AND a.asset_id=new.hda_key_id AND new.library_uuid=(SELECT uuid FROM library_identity))
        BEGIN SELECT RAISE(ABORT,'Scene version belongs to another asset or library'); END""")
    return statements


def statements() -> list[str]:
    """Every DDL statement of the schema, in creation order."""
    return [
        *BASE_TABLES,
        *_index_statements(),
        *STATE_TABLES,
        *TRACKING_TABLES,
        *_trigger_statements(),
    ]


def install(connection: sqlite3.Connection) -> None:
    """Create the schema and its seed rows on an empty database."""
    for sql in statements():
        connection.execute(sql)
    connection.execute("INSERT INTO write_context(singleton,request_id) VALUES(1,NULL)")
    connection.execute(
        "INSERT INTO library_identity (singleton,uuid) VALUES(1,:new_identity)",
        {"new_identity": new_identity()},
    )


def schema_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _has_objects(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
        ).fetchone()
        is not None
    )


def _drop_everything(connection: sqlite3.Connection) -> None:
    objects = connection.execute(
        """SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'
           AND type IN ('trigger','view','table')
           ORDER BY CASE type WHEN 'trigger' THEN 0 WHEN 'view' THEN 1 ELSE 2 END"""
    ).fetchall()
    for kind, name in objects:
        connection.execute(f'DROP {kind.upper()} IF EXISTS "{name}"')


def ensure_schema(connection: sqlite3.Connection, filepath: str | Path) -> None:
    """Make ``connection`` a database at ``SCHEMA_VERSION``.

    An empty file gets the schema. A file at another version is backed up next
    to itself as ``<name>.pre-v<N>-<stamp>.bak`` and emptied, then gets the
    schema: there is no in-place upgrade. A file from a newer build is refused,
    since this build cannot know what it holds.
    """
    version = schema_version(connection)
    if version == SCHEMA_VERSION:
        return
    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema {version} is newer than supported {SCHEMA_VERSION}"
        )
    if connection.in_transaction:
        raise sqlite3.ProgrammingError(
            "Schema setup requires a connection without an active transaction"
        )
    filepath = Path(filepath)
    rebuild = _has_objects(connection)
    if rebuild:
        backup_database(
            connection,
            filepath.with_name(
                f"{filepath.name}.pre-v{SCHEMA_VERSION}-{file_stamp()}.bak"
            ),
        )
    foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        if rebuild:
            _drop_everything(connection)
        install(connection)
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.execute(f"PRAGMA foreign_keys={foreign_keys}")
