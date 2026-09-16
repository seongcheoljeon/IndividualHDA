"""Additive personal schema. Triggers cover the legacy facade's write paths too."""

from __future__ import annotations

import sqlite3

from libs.library_metadata import new_identity

UUID_SQL = "(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-a' || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6))))"
NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


def install(connection: sqlite3.Connection) -> None:
    statements = [
        "CREATE TABLE write_context (singleton INTEGER PRIMARY KEY CHECK(singleton=1), request_id TEXT, maintenance INTEGER NOT NULL DEFAULT 0)",
        "CREATE TABLE migration_reports (message TEXT NOT NULL)",
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
    ]
    for statement in statements:
        connection.execute(statement)
    connection.execute("INSERT INTO write_context(singleton,request_id) VALUES(1,NULL)")
    connection.execute("INSERT INTO library_identity VALUES(1,?)", (new_identity(),))
    for (asset_id,) in connection.execute("SELECT id FROM hda_key").fetchall():
        connection.execute(
            "INSERT INTO asset_identity(asset_id,uuid,created_at) VALUES(?,?,NULL)",
            (asset_id, new_identity()),
        )
    for (history_id,) in connection.execute("SELECT id FROM hda_history").fetchall():
        connection.execute(
            "INSERT INTO version_identity(history_id,uuid,created_at) VALUES(?,?,NULL)",
            (history_id, new_identity()),
        )
    connection.execute("""UPDATE asset_identity SET current_version_uuid=(
        SELECT v.uuid FROM version_identity v JOIN hda_history h ON h.id=v.history_id
        JOIN hda_info i ON i.hda_key_id=h.hda_key_id
        WHERE h.hda_key_id=asset_identity.asset_id AND h.version=i.version ORDER BY h.id DESC LIMIT 1)""")
    connection.execute("""INSERT INTO asset_user_preferences(asset_id,user_id,favorite,use_count)
        SELECT k.id,k.user_id,i.is_favorite,i.load_count FROM hda_key k JOIN hda_info i ON i.hda_key_id=k.id""")
    for kind, directory, filename in (
        ("asset", "hda_dirpath", "hda_filename"),
        ("thumbnail", "thumb_dirpath", "thumb_filename"),
        ("video", "video_dirpath", "video_filename"),
    ):
        connection.execute(
            f"""INSERT INTO version_files(history_id,kind,directory,filename,registered_at)
            SELECT id,?,{directory},{filename},registration_datetime FROM hda_history
            WHERE {directory} IS NOT NULL AND {filename} IS NOT NULL""",
            (kind,),
        )
        for action in ("INSERT", "UPDATE"):
            condition = (
                ""
                if action == "INSERT"
                else f"WHEN old.{directory} IS NOT new.{directory} OR old.{filename} IS NOT new.{filename}"
            )
            connection.execute(f"""CREATE TRIGGER v5_files_{kind}_{action.lower()} AFTER {action} ON hda_history {condition} BEGIN
                DELETE FROM version_files WHERE history_id=new.id AND kind='{kind}' AND (new.{directory} IS NULL OR new.{filename} IS NULL);
                INSERT INTO version_files(history_id,kind,directory,filename,registered_at)
                SELECT new.id,'{kind}',new.{directory},new.{filename},{NOW_SQL}
                WHERE new.{directory} IS NOT NULL AND new.{filename} IS NOT NULL
                ON CONFLICT(history_id,kind) DO UPDATE SET directory=excluded.directory,filename=excluded.filename;
            END""")
    connection.execute(f"""CREATE TRIGGER v5_asset_identity AFTER INSERT ON hda_key BEGIN
        INSERT INTO asset_identity(asset_id,uuid,created_at) VALUES(new.id,{UUID_SQL},{NOW_SQL}); END""")
    connection.execute(f"""CREATE TRIGGER v5_version_identity AFTER INSERT ON hda_history BEGIN
        INSERT INTO version_identity(history_id,uuid,created_at) VALUES(new.id,{UUID_SQL},{NOW_SQL});
        UPDATE asset_identity SET current_version_uuid=(SELECT uuid FROM version_identity WHERE history_id=new.id)
        WHERE asset_id=new.hda_key_id AND EXISTS(SELECT 1 FROM hda_info WHERE hda_key_id=new.hda_key_id AND version=new.version);
        END""")
    # Legacy fields are compatibility projections. All public setting writes use the preferences table.
    for action in ("INSERT", "UPDATE OF is_favorite,load_count"):
        name = action.split()[0].lower()
        connection.execute(f"""CREATE TRIGGER v5_preferences_{name} AFTER {action} ON hda_info BEGIN
            INSERT INTO asset_user_preferences(asset_id,user_id,favorite,use_count)
            SELECT new.hda_key_id,user_id,new.is_favorite,new.load_count FROM hda_key WHERE id=new.hda_key_id
            ON CONFLICT(asset_id,user_id) DO UPDATE SET favorite=excluded.favorite,use_count=excluded.use_count;
        END""")
    for table, key, fields in (
        ("hda_key", "id", ("name", "category")),
        ("hda_info", "hda_key_id", ("version", "filename", "dirpath")),
        ("note_info", "hda_key_id", ("note",)),
        ("tag_info", "hda_key_id", ("tag",)),
        (
            "hda_history",
            "hda_key_id",
            ("version", "comment", "hda_filename", "hda_dirpath"),
        ),
        ("thumbnail_info", "hda_key_id", ("filename", "dirpath")),
        ("video_info", "hda_key_id", ("filename", "dirpath")),
    ):
        for action in ("INSERT", "UPDATE"):
            old_json = (
                "'{}'"
                if action == "INSERT"
                else "json_object("
                + ",".join(f"'{field}',old.{field}" for field in fields)
                + ")"
            )
            new_json = (
                "json_object("
                + ",".join(f"'{field}',new.{field}" for field in fields)
                + ")"
            )
            when = (
                ""
                if action == "INSERT"
                else "WHEN "
                + " OR ".join(f"old.{field} IS NOT new.{field}" for field in fields)
            )
            # Creation of hda_key identity occurs in another trigger: resolve UUID at the identity trigger below.
            if table == "hda_key" and action == "INSERT":
                continue
            connection.execute(f"""CREATE TRIGGER v5_audit_{table}_{action.lower()} AFTER {action} ON {table} {when} BEGIN
                INSERT INTO audit_events(id,asset_uuid,actor,occurred_at,request_id,operation,changes)
                SELECT {UUID_SQL},uuid,(SELECT user_id FROM hda_key WHERE id=new.{key}),{NOW_SQL},COALESCE((SELECT request_id FROM write_context),{UUID_SQL}),
                '{table}.{action.lower()}',json_object('before',json({old_json}),'after',json({new_json}))
                FROM asset_identity WHERE asset_id=new.{key}; END""")
    connection.execute(f"""CREATE TRIGGER v5_audit_create AFTER INSERT ON asset_identity BEGIN
        INSERT INTO audit_events(id,asset_uuid,actor,occurred_at,request_id,operation,changes)
        SELECT {UUID_SQL},new.uuid,user_id,{NOW_SQL},COALESCE((SELECT request_id FROM write_context),{UUID_SQL}),'create',json_object('name',name) FROM hda_key WHERE id=new.asset_id; END""")

    connection.execute("""INSERT INTO migration_reports SELECT 'Asset ' || asset_id || ': no matching historical version; original data retained'
        FROM asset_identity WHERE current_version_uuid IS NULL""")
    connection.execute("""INSERT INTO migration_reports SELECT 'Asset ' || hda_key_id || ': duplicate version label ' || version || '; history IDs retained'
        FROM hda_history GROUP BY hda_key_id,version HAVING COUNT(*)>1""")
    connection.execute(
        "INSERT INTO migration_reports VALUES('Legacy timestamps retain their original values; timezone is unknown')"
    )

    for table in (
        "hda_info",
        "note_info",
        "tag_info",
        "thumbnail_info",
        "video_info",
        "hipfile_info",
        "houdini_node_info",
        "hda_history",
    ):
        for event in ("INSERT", "UPDATE"):
            connection.execute(f"""CREATE TRIGGER v5_reject_deleted_{table}_{event} BEFORE {event} ON {table}
                WHEN (SELECT maintenance FROM write_context)=0 AND EXISTS(SELECT 1 FROM asset_identity WHERE asset_id=new.hda_key_id AND deleted_at IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'Asset is in the trash'); END""")

    connection.execute("""CREATE TRIGGER v5_audit_time AFTER INSERT ON audit_events BEGIN
        UPDATE asset_identity SET updated_at=new.occurred_at WHERE uuid=new.asset_uuid; END""")
    # Updating preview metadata changes only the matching current version snapshot.
    for table, prefix, kind in (
        ("thumbnail_info", "thumb", "thumbnail"),
        ("video_info", "video", "video"),
    ):
        for event in ("INSERT", "UPDATE"):
            connection.execute(f"""CREATE TRIGGER v5_snapshot_{table}_{event} AFTER {event} ON {table} BEGIN
                UPDATE hda_history SET {prefix}_dirpath=new.dirpath,{prefix}_filename=new.filename
                WHERE id=(SELECT v.history_id FROM version_identity v JOIN asset_identity a ON a.current_version_uuid=v.uuid
                          WHERE a.asset_id=new.hda_key_id) AND version=new.version;
                UPDATE version_files SET digest=NULL,size=NULL,status='unverified',checked_at=NULL
                WHERE kind='{kind}' AND history_id=(SELECT v.history_id FROM version_identity v JOIN asset_identity a ON a.current_version_uuid=v.uuid
                          JOIN hda_history h ON h.id=v.history_id WHERE a.asset_id=new.hda_key_id AND h.version=new.version);
            END""")
