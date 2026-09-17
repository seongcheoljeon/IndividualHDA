"""Version links and tracking migration. Preserve ambiguous legacy records."""

from __future__ import annotations

import json
import sqlite3

from libs.database.tracking import local_tracking
from libs.database_v5 import NOW_SQL, UUID_SQL
from libs.version_tracking import schema_statements


def install(connection: sqlite3.Connection) -> None:
    for sql in schema_statements():
        connection.execute(sql)
    for column in (
        "library_uuid TEXT",
        "asset_uuid TEXT",
        "version_uuid TEXT",
        "link_status TEXT NOT NULL DEFAULT 'unresolved'",
    ):
        connection.execute(f"ALTER TABLE hda_node_location_record ADD COLUMN {column}")
    connection.execute(
        "CREATE INDEX idx_scene_record_version ON hda_node_location_record(version_uuid)"
    )
    tracking = local_tracking(connection)
    for _history_id, uuid, details in connection.execute(
        "SELECT history_id,uuid,details FROM version_identity"
    ).fetchall():
        tracking.replace_dependencies(uuid, json.loads(details).get("dependencies", []))
    connection.execute("""UPDATE hda_node_location_record SET library_uuid=(SELECT uuid FROM library_identity),
        asset_uuid=(SELECT uuid FROM asset_identity WHERE asset_id=hda_key_id)""")
    connection.execute("""UPDATE hda_node_location_record SET version_uuid=(SELECT v.uuid FROM version_identity v JOIN hda_history h ON h.id=v.history_id
        WHERE h.hda_key_id=hda_node_location_record.hda_key_id AND h.version=node_version AND h.hda_filename=hda_node_location_record.hda_filename
        AND h.hda_dirpath=hda_node_location_record.hda_dirpath),link_status='resolved'
        WHERE 1=(SELECT COUNT(*) FROM hda_history h WHERE h.hda_key_id=hda_node_location_record.hda_key_id AND h.version=node_version
        AND h.hda_filename=hda_node_location_record.hda_filename AND h.hda_dirpath=hda_node_location_record.hda_dirpath)""")
    connection.execute("DROP TRIGGER v5_version_identity")
    connection.execute(f"""CREATE TRIGGER v6_version_identity AFTER INSERT ON hda_history BEGIN
        INSERT INTO version_identity(history_id,uuid,created_at) VALUES(new.id,{UUID_SQL},{NOW_SQL});
        UPDATE asset_identity SET current_version_uuid=(SELECT uuid FROM version_identity WHERE history_id=new.id)
        WHERE asset_id=new.hda_key_id AND (current_version_uuid IS NULL OR NOT EXISTS(
            SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE v.uuid=current_version_uuid AND h.version=new.version))
        AND EXISTS(SELECT 1 FROM hda_info WHERE hda_key_id=new.hda_key_id AND version=new.version); END""")
    # Corrupt existing pointers are retained in a report, never guessed from a name.
    connection.execute("""INSERT INTO migration_reports SELECT 'Invalid current version cleared for asset ' || asset_id FROM asset_identity a
        WHERE current_version_uuid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE v.uuid=a.current_version_uuid AND h.hda_key_id=a.asset_id AND v.deleted_at IS NULL)""")
    connection.execute("""UPDATE asset_identity SET current_version_uuid=NULL WHERE current_version_uuid IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id WHERE v.uuid=asset_identity.current_version_uuid AND h.hda_key_id=asset_identity.asset_id AND v.deleted_at IS NULL)""")
    for action in ("INSERT", "UPDATE OF current_version_uuid"):
        connection.execute(f"""CREATE TRIGGER v6_current_{action.split()[0].lower()} BEFORE {action} ON asset_identity
        WHEN new.current_version_uuid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id
        WHERE v.uuid=new.current_version_uuid AND h.hda_key_id=new.asset_id AND v.deleted_at IS NULL)
        BEGIN SELECT RAISE(ABORT,'Current version must belong to this asset and be active'); END""")
    connection.execute("""CREATE TRIGGER v6_protect_current BEFORE UPDATE OF deleted_at ON version_identity WHEN new.deleted_at IS NOT NULL AND EXISTS(
        SELECT 1 FROM asset_identity WHERE current_version_uuid=new.uuid)
        BEGIN SELECT RAISE(ABORT,'Cannot trash current version'); END""")
    connection.execute("""CREATE TRIGGER v6_dependency_cleanup AFTER DELETE ON version_identity BEGIN
        DELETE FROM version_dependencies WHERE source_uuid=old.uuid; END""")

    connection.execute("""CREATE TRIGGER v6_clear_current AFTER DELETE ON version_identity BEGIN
        UPDATE asset_identity SET current_version_uuid=NULL WHERE current_version_uuid=old.uuid; END""")
    for action in (
        "INSERT",
        "UPDATE OF version_uuid,asset_uuid,library_uuid,hda_key_id",
    ):
        connection.execute(f"""CREATE TRIGGER v6_scene_{action.split()[0].lower()} BEFORE {action} ON hda_node_location_record
        WHEN new.version_uuid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM version_identity v JOIN hda_history h ON h.id=v.history_id
        JOIN asset_identity a ON a.asset_id=h.hda_key_id WHERE v.uuid=new.version_uuid AND a.uuid=new.asset_uuid
        AND a.asset_id=new.hda_key_id AND new.library_uuid=(SELECT uuid FROM library_identity))
        BEGIN SELECT RAISE(ABORT,'Scene version belongs to another asset or library'); END""")
