# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.04.14 18:18:59
# modified date:    
# description:      SQLite3 Database Schema


def db_schema():
    tables_schema = '''
CREATE TABLE IF NOT EXISTS users
(
    user_id       VARCHAR(50) NOT NULL UNIQUE PRIMARY KEY,
    email         VARCHAR(150) NOT NULL UNIQUE,
    join_datetime DATETIME     NOT NULL
);

CREATE TABLE IF NOT EXISTS hda_category
(
    category VARCHAR(100) NOT NULL,
    user_id  VARCHAR(50) NOT NULL,
    PRIMARY KEY (category, user_id),
    UNIQUE (category, user_id),
    CONSTRAINT FK_hda_category_users_user_id FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE ON DELETE CASCADE 
);

CREATE TABLE IF NOT EXISTS hda_key
(
    id       INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    name     VARCHAR(255) NOT NULL,
    category VARCHAR(255) NOT NULL,
    user_id  VARCHAR(50) NOT NULL,
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
    org_hda_name          VARCHAR(255) NOT NULL,
    version               VARCHAR(255) NOT NULL,
    hda_filename          VARCHAR(255) NOT NULL,
    hda_dirpath           VARCHAR(255) NOT NULL,
    registration_datetime DATETIME     NOT NULL,
    houdini_version       VARCHAR(100) NOT NULL,
    hip_filename          VARCHAR(255) NOT NULL,
    hip_dirpath           VARCHAR(255) NOT NULL,
    hda_license           VARCHAR(100) NOT NULL,
    operating_system      VARCHAR(100) NOT NULL,
    node_old_path         VARCHAR(255) NOT NULL,
    node_def_desc         VARCHAR(255) NOT NULL,
    node_type_name        VARCHAR(255) NOT NULL,
    node_category         VARCHAR(255) NOT NULL,
    userid                VARCHAR(50) NOT NULL,
    icon                  VARCHAR(255) NOT NULL,
    thumb_filename        VARCHAR(255) NOT NULL,
    thumb_dirpath         VARCHAR(255) NOT NULL,
    video_filename        VARCHAR(255) DEFAULT NULL,
    video_dirpath         VARCHAR(255) DEFAULT NULL,
    UNIQUE (id, hda_key_id),
    CONSTRAINT FK_hda_history_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hda_node_location_record
(
    id               INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id       INTEGER      NOT NULL,
    hip_filename     VARCHAR(255) NOT NULL,
    hip_dirpath      VARCHAR(255) NOT NULL,
    hda_filename     VARCHAR(255) NOT NULL,
    hda_dirpath      VARCHAR(255) NOT NULL,
    parent_node_path VARCHAR(255) NOT NULL,
    node_type        VARCHAR(255) NOT NULL,
    node_category    VARCHAR(255) NOT NULL,
    node_name        VARCHAR(255) NOT NULL, 
    node_version     VARCHAR(255) NOT NULL,
    houdini_version  VARCHAR(100) NOT NULL,
    houdini_license  VARCHAR(100) NOT NULL,
    operating_system VARCHAR(100) NOT NULL,
    sf               INTEGER      NOT NULL,
    ef               INTEGER      NOT NULL,
    fps              INTEGER      NOT NULL,
    ctime            DATETIME     NOT NULL,
    mtime            DATETIME     NOT NULL,
    UNIQUE (id, hda_key_id),
    CONSTRAINT FK_hda_node_location_record_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hda_note_history
(
    id                    INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id            INTEGER      NOT NULL,
    note                  TEXT         NOT NULL,
    registration_datetime DATETIME     NOT NULL,
    hda_version           VARCHAR(255) NOT NULL,
    UNIQUE (id, hda_key_id),
    CONSTRAINT FK_hda_note_history_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hda_info
(
    id                             INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id                     INTEGER      NOT NULL,
    version                        VARCHAR(255) NOT NULL,
    is_favorite                    INTEGER      NOT NULL DEFAULT 0,
    load_count                     INTEGER      NOT NULL,
    filename                       VARCHAR(255) NOT NULL,
    dirpath                        VARCHAR(255) NOT NULL,
    initial_registration_datetime  DATETIME     NOT NULL,
    modified_registration_datetime DATETIME     NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_hda_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hipfile_info
(
    id               INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id       INTEGER      NOT NULL,
    filename         VARCHAR(255) NOT NULL,
    dirpath          VARCHAR(255) NOT NULL,
    houdini_version  VARCHAR(100) NOT NULL,
    hda_license      VARCHAR(100) NOT NULL,
    operating_system VARCHAR(100) NOT NULL,
    sf               INTEGER      NOT NULL,
    ef               INTEGER      NOT NULL,
    fps              INTEGER      NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_hipfile_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_info
(
    id             INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id     INTEGER      NOT NULL,
    node_type_name VARCHAR(255) NOT NULL,
    node_def_desc  VARCHAR(255) NOT NULL,
    is_network     INTEGER      NOT NULL,
    is_sub_network INTEGER      NOT NULL,
    node_old_path  VARCHAR(255) NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_houdini_node_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_category_path_info
(
    id            INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id       INTEGER      NOT NULL,
    node_category VARCHAR(255) NOT NULL,
    UNIQUE (id, info_id),
    CONSTRAINT FK_houdini_node_category_path_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_type_path_info
(
    id        INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id   INTEGER      NOT NULL,
    node_type VARCHAR(255) NOT NULL,
    UNIQUE (id, info_id),
    CONSTRAINT FK_houdini_node_type_path_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_input_connect_info
(
    id                  INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id             INTEGER      NOT NULL,
    curt_node_input_idx INTEGER      NOT NULL,
    connect_node_name   VARCHAR(255) NOT NULL,
    connect_node_type   VARCHAR(255) NOT NULL,
    connect_output_idx  INTEGER      NOT NULL,
    UNIQUE (id, info_id),
    CONSTRAINT FK_houdini_node_input_connect_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS houdini_node_output_connect_info
(
    id                   INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    info_id              INTEGER      NOT NULL,
    curt_node_output_idx INTEGER      NOT NULL,
    connect_node_name    VARCHAR(255) NOT NULL,
    connect_node_type    VARCHAR(255) NOT NULL,
    connect_input_idx    INTEGER      NOT NULL,
    UNIQUE (id, info_id),
    CONSTRAINT FK_houdini_node_output_connect_info_hou_node_info_id FOREIGN KEY (info_id)
        REFERENCES houdini_node_info (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS icon_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    icon       VARCHAR(255) NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_icon_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tag_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    tag        VARCHAR(255) NOT NULL,
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
    filename   VARCHAR(255) NOT NULL,
    dirpath    VARCHAR(255) NOT NULL,
    version    VARCHAR(255) NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_thumbnail_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS video_info
(
    id         INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
    hda_key_id INTEGER      NOT NULL,
    filename   VARCHAR(255) NOT NULL,
    dirpath    VARCHAR(255) NOT NULL,
    version    VARCHAR(255) NOT NULL,
    UNIQUE (hda_key_id),
    CONSTRAINT FK_video_info_hda_key_id FOREIGN KEY (hda_key_id)
        REFERENCES hda_key (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS delete_trg_unused_hda_category
    AFTER
        DELETE
    ON hda_key
    FOR EACH ROW
BEGIN
    DELETE
    FROM hda_category
    WHERE hda_category.category = old.category
      AND (SELECT COUNT(*) FROM hda_key WHERE hda_key.category = old.category) = 0;
END;

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

    '''
    return tables_schema
