from __future__ import annotations


# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.14 18:18:59
# modified date:
# description:      SQLite3 Database Schema


def db_schema() -> str:
    """Base tables and triggers; use migrate() to create a complete versioned DB.

    Versioned indexes and normalized tags are installed by
    libs.database_migrations. Executing this SQL alone does not upgrade a library.
    """
    tables_schema = """
CREATE TABLE IF NOT EXISTS operation_commits
(
    operation_id TEXT NOT NULL PRIMARY KEY CHECK(length(operation_id) > 0),
    committed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users
(
    user_id       TEXT NOT NULL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    join_datetime TEXT     NOT NULL
);

CREATE TABLE IF NOT EXISTS hda_category
(
    category TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    PRIMARY KEY (category, user_id),
    CONSTRAINT FK_hda_category_users_user_id FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hda_key
(
    id       INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    UNIQUE (name, category, user_id),
    CONSTRAINT FK_hda_key_hda_category FOREIGN KEY (category, user_id)
        REFERENCES hda_category (category, user_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hda_history
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
);

CREATE TABLE IF NOT EXISTS hda_node_location_record
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
    CONSTRAINT FK_hda_node_location_record_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hda_note_history
(
    id                    INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id            INTEGER      NOT NULL,
    note                  TEXT         NOT NULL,
    registration_datetime TEXT     NOT NULL,
    hda_version           TEXT NOT NULL,
    CONSTRAINT FK_hda_note_history_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hda_info
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
);

CREATE TABLE IF NOT EXISTS hipfile_info
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
);

CREATE TABLE IF NOT EXISTS houdini_node_info
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
);

CREATE TABLE IF NOT EXISTS houdini_node_category_path_info
(
    id            INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id       INTEGER      NOT NULL,
    node_category TEXT NOT NULL,
    CONSTRAINT FK_houdini_node_category_path_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_type_path_info
(
    id        INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id   INTEGER      NOT NULL,
    node_type TEXT NOT NULL,
    CONSTRAINT FK_houdini_node_type_path_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_input_connect_info
(
    id                  INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id             INTEGER      NOT NULL,
    curt_node_input_idx INTEGER      NOT NULL CHECK(typeof(curt_node_input_idx) = 'integer' AND curt_node_input_idx >= 0),
    connect_node_name   TEXT NOT NULL,
    connect_node_type   TEXT NOT NULL,
    connect_output_idx  INTEGER      NOT NULL CHECK(typeof(connect_output_idx) = 'integer' AND connect_output_idx >= 0),
    CONSTRAINT FK_houdini_node_input_connect_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_output_connect_info
(
    id                   INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id              INTEGER      NOT NULL,
    curt_node_output_idx INTEGER      NOT NULL CHECK(typeof(curt_node_output_idx) = 'integer' AND curt_node_output_idx >= 0),
    connect_node_name    TEXT NOT NULL,
    connect_node_type    TEXT NOT NULL,
    connect_input_idx    INTEGER      NOT NULL CHECK(typeof(connect_input_idx) = 'integer' AND connect_input_idx >= 0),
    CONSTRAINT FK_houdini_node_output_connect_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS icon_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    icon       TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_icon_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tag_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    tag        TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_tag_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS note_info
(
    id         INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER NOT NULL,
    note       TEXT    NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_note_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS thumbnail_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    filename   TEXT NOT NULL,
    dirpath    TEXT NOT NULL,
    version    TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_thumbnail_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS video_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    filename   TEXT NOT NULL,
    dirpath    TEXT NOT NULL,
    version    TEXT NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_video_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS insert_trg_hda_note_history
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
END;

CREATE TRIGGER IF NOT EXISTS update_trg_hda_note_history
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
END;

CREATE TRIGGER IF NOT EXISTS update_trg_hda_node_location_record
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
END;

    """
    return tables_schema + category_cleanup_trigger()


def category_cleanup_trigger() -> str:
    """Shared by base schema creation and upgrades of existing databases."""
    return """
CREATE TRIGGER IF NOT EXISTS delete_trg_unused_hda_category
    AFTER DELETE ON hda_key
    FOR EACH ROW
BEGIN
    DELETE FROM hda_category
    WHERE category = old.category AND user_id = old.user_id
      AND NOT EXISTS (
          SELECT 1 FROM hda_key
          WHERE category = old.category AND user_id = old.user_id
      );
END;
"""
