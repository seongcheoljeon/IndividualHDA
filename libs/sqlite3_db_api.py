# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.27 21:35:47
# modified date:    
# description:      SQLite3 Database API

import sqlite3
import socket
import struct
import logging
import itertools
import collections
from imp import reload

import public

reload(public)

# third-pary modules
import pathlib2

from libs import log_handler
from model import sqlite3_db_schema

reload(log_handler)
reload(sqlite3_db_schema)


class SQLite3DatabaseAPI(object):
    def __init__(self, db_filepath=None):
        assert isinstance(db_filepath, pathlib2.Path)
        self.__db_filepath = db_filepath
        self.__connect = sqlite3.connect(self.__db_filepath.as_posix())
        self.__cursor = self.__connect.cursor()
        self.__cursor.execute('PRAGMA encoding = "UTF-8"')
        self.__cursor.execute('PRAGMA foreign_keys = ON')

    def __del__(self):
        self.__cursor.close()
        self.__connect.close()

    @property
    def db_filepath(self):
        return self.__db_filepath

    def create_tables(self):
        query = sqlite3_db_schema.db_schema()
        try:
            self.__cursor.executescript(query)
            self.__connect.commit()
            return True
        except sqlite3.Error as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='database table creation failed')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return False

    @staticmethod
    def inet_aton(ip_str=None):
        return struct.unpack('>L', socket.inet_aton(ip_str))[0]

    @staticmethod
    def inet_ntoa(packed_ip=None):
        return socket.inet_ntoa(struct.pack('>L', packed_ip))

    # ################ insert ################## #
    def insert_users(self, user_id=None, email=None):
        query = '''
        INSERT INTO users (user_id, email, join_datetime)
        VALUES (?, ?, (SELECT DATETIME('now', 'localtime')))
        '''
        try:
            dat = (user_id, email)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** users (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hda_category(self, category=None, user_id=None):
        query = '''
        INSERT INTO hda_category (category, user_id) 
            SELECT ?, ?
            WHERE NOT EXISTS (SELECT * FROM hda_category WHERE category = ? AND user_id = ?)
        '''
        try:
            dat = (category, user_id, category, user_id)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_category (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hda_key(self, name=None, category=None, user_id=None, ):
        query = '''INSERT INTO hda_key (name, category, user_id) VALUES (?, ?, ?)'''
        try:
            dat = (name, category, user_id)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_key (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hda_info(
            self, hda_key_id=None, version=None, is_favorite=False,
            load_count=0, filename=None, dirpath=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''
        INSERT INTO hda_info
            (hda_key_id, version, is_favorite, load_count, filename, dirpath,
            initial_registration_datetime, modified_registration_datetime)
        VALUES (?, ?, ?, ?, ?, ?, (SELECT DATETIME('now', 'localtime')), (SELECT DATETIME('now', 'localtime')))
        '''
        try:
            dat = (hda_key_id, version, is_favorite, load_count, filename, dirpath.as_posix())
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    @staticmethod
    def __make_icon_to_string(icon_lst=None):
        if not len(icon_lst):
            return None
        return ','.join(map(lambda x: x.strip(), icon_lst))

    @staticmethod
    def __make_tag_to_string(tag_lst=None):
        if not len(tag_lst):
            return None
        return '#'.join(map(lambda x: x.strip(), tag_lst))

    def insert_icon_info(self, hda_key_id=None, icon_lst=()):
        if not len(icon_lst):
            return None
        query = '''INSERT INTO icon_info (hda_key_id, icon) VALUES (?, ?)'''
        try:
            dat = (hda_key_id, SQLite3DatabaseAPI.__make_icon_to_string(icon_lst=icon_lst))
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** icon_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_tag_info(self, hda_key_id=None, tag_lst=None):
        if not len(tag_lst):
            return None
        query = '''INSERT INTO tag_info (hda_key_id, tag) VALUES (?, ?)'''
        try:
            dat = (hda_key_id, SQLite3DatabaseAPI.__make_tag_to_string(tag_lst=tag_lst))
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** tag_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hipfile_info(
            self, hda_key_id=None, filename=None, dirpath=None, houdini_version=None, hda_license=None,
            operating_system=None, sf=None, ef=None, fps=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''
        INSERT INTO hipfile_info
        (hda_key_id, filename, dirpath, houdini_version, hda_license, operating_system, sf, ef, fps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        try:
            dat = (hda_key_id, filename, dirpath.as_posix(),
                   houdini_version, hda_license, operating_system, sf, ef, fps)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hipfile_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_location_info(
            self, hda_key_id=None, country=None, timezone=None, region=None,
            city=None, ip=None, localx=None, localy=None, org=None, postal=None):
        query = '''
        INSERT INTO location_info
        (hda_key_id, country, timezone, region, city, ip, localx, localy, org, postal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        try:
            dat = (hda_key_id, country, timezone, region, city, SQLite3DatabaseAPI.inet_aton(ip_str=ip),
                   localx, localy, org, postal)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** location_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_info(
            self, hda_key_id=None, type_name=None, def_desc=None, is_net=None, is_sub_net=None, old_path=None):
        query = '''
        INSERT INTO houdini_node_info
            (hda_key_id, node_type_name, node_def_desc, is_network, is_sub_network, node_old_path)
        VALUES (?, ?, ?, ?, ?, ?)
        '''
        try:
            dat = (hda_key_id, type_name, def_desc, is_net, is_sub_net, old_path)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** node_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_category_path_info(self, info_id=None, node_category_lst=()):
        if not len(node_category_lst):
            return None
        join_str = ','.join(map(lambda x: x.strip(), node_category_lst))
        query = '''INSERT INTO houdini_node_category_path_info (info_id, node_category) VALUES (?, ?)'''
        try:
            dat = (info_id, join_str)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** node_category_path_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_type_path_info(self, info_id=None, node_type_lst=()):
        if not len(node_type_lst):
            return None
        join_str = ','.join(map(lambda x: x.strip(), node_type_lst))
        query = '''INSERT INTO houdini_node_type_path_info (info_id, node_type) VALUES (?, ?)'''
        try:
            dat = (info_id, join_str)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** node_type_path_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_input_connect_info(self, info_id=None, node_input_connect_lst=()):
        query = '''
        INSERT INTO houdini_node_input_connect_info
            (info_id, curt_node_input_idx, connect_node_name, connect_node_type, connect_output_idx)
        VALUES 
            (?, ?, ?, ?, ?)
        '''
        try:
            dat = tuple(map(lambda x: tuple([info_id] + x), node_input_connect_lst))
            cursor = self.__cursor.executemany(query, dat)
            self.__connect.commit()
            return cursor.rowcount
            # return True
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** node_input_connect_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_houdini_node_output_connect_info(self, info_id=None, node_output_connect_lst=()):
        query = '''
        INSERT INTO houdini_node_output_connect_info
            (info_id, curt_node_output_idx, connect_node_name, connect_node_type, connect_input_idx)
        VALUES 
            (?, ?, ?, ?, ?)
        '''
        try:
            dat = tuple(map(lambda x: tuple([info_id] + x), node_output_connect_lst))
            cursor = self.__cursor.executemany(query, dat)
            self.__connect.commit()
            return cursor.rowcount
            # return True
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** node_output_connect_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_video_info(self, hda_key_id=None, dirpath=None, filename=None, version=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''INSERT INTO video_info (hda_key_id, filename, dirpath, version) 
        VALUES (?, ?, ?, ?)'''
        try:
            dat = (hda_key_id, filename, dirpath.as_posix(), version)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** video_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_thumbnail_info(self, hda_key_id=None, dirpath=None, filename=None, version=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''INSERT INTO thumbnail_info (hda_key_id, filename, dirpath, version)
        VALUES (?, ?, ?, ?)'''
        try:
            dat = (hda_key_id, filename, dirpath.as_posix(), version)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** thumbnail_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_note_info(self, hda_key_id=None, note=None):
        query = '''INSERT INTO note_info (hda_key_id, note) VALUES (?, ?)'''
        try:
            dat = (hda_key_id, note)
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** note_info (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def insert_hda_node_location_record(
            self, hda_key_id=None, hip_filename=None, hip_dirpath=None, hda_filename=None, hda_dirpath=None,
            parent_node_path=None, node_type=None, node_cate=None, node_name=None, node_ver=None,
            hou_version=None, hou_license=None, operating_sys=None, sf=None, ef=None, fps=None):
        assert isinstance(hip_dirpath, pathlib2.Path)
        is_exist = self.is_exist_hda_node_loc_record(
            hda_key_id=hda_key_id, hip_filename=hip_filename, hip_dirpath=hip_dirpath,
            parent_node_path=parent_node_path, node_name=node_name, node_ver=node_ver)
        if is_exist:
            query = '''UPDATE hda_node_location_record SET mtime = (SELECT DATETIME('now', 'localtime')),
                houdini_version = '{0}', houdini_license = '{1}', operating_system = '{2}',
                sf = {3}, ef = {4}, fps = {5}
            WHERE hda_key_id = {6} AND hip_filename = '{7}' AND hip_dirpath = '{8}' 
                AND parent_node_path = '{9}' AND node_name = '{10}'
            '''.format(
                hou_version, hou_license, operating_sys, sf, ef, fps,
                hda_key_id, hip_filename, hip_dirpath.as_posix(), parent_node_path, node_name)
            try:
                cursor = self.__cursor.execute(query)
                self.__connect.commit()
                return cursor.rowcount
            except Exception as err:
                self.__connect.rollback()
                log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_node_location_record (update) ***')
                log_handler.LogHandler.log_msg(method=logging.error, msg=err)
                return None
        else:
            query = '''INSERT INTO hda_node_location_record 
            (hda_key_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
            parent_node_path, node_type, node_category, node_name, node_version, 
            houdini_version, houdini_license, operating_system, sf, ef, fps, ctime, mtime) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                (SELECT DATETIME('now', 'localtime')), (SELECT DATETIME('now', 'localtime')))'''
            try:
                dat = (hda_key_id, hip_filename, hip_dirpath.as_posix(), hda_filename, hda_dirpath.as_posix(),
                       parent_node_path, node_type, node_cate, node_name, node_ver,
                       hou_version, hou_license, operating_sys, sf, ef, fps)
                cursor = self.__cursor.execute(query, dat)
                self.__connect.commit()
                return cursor.rowcount
            except Exception as err:
                self.__connect.rollback()
                log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_node_location_record (insert) ***')
                log_handler.LogHandler.log_msg(method=logging.error, msg=err)
                return None

    def insert_hda_history(self, data=None):
        query = '''
        INSERT INTO hda_history
            (hda_key_id, comment, org_hda_name, version, hda_filename, hda_dirpath,
            registration_datetime, houdini_version, hip_filename, hip_dirpath, hda_license, operating_system,
            node_old_path, node_def_desc, node_type_name, node_category, userid, icon,
            thumb_filename, thumb_dirpath, video_filename, video_dirpath)
        VALUES (?, ?, ?, ?, ?, ?, 
            (SELECT DATETIME('now', 'localtime')), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        try:
            hist_key_lst = [
                public.Key.History.hda_id, public.Key.History.comment,
                public.Key.History.org_hda_name, public.Key.History.version, public.Key.History.ihda_filename,
                public.Key.History.ihda_dirpath, public.Key.History.reg_time, public.Key.History.hou_version,
                public.Key.History.hip_filename, public.Key.History.hip_dirpath, public.Key.History.hda_license,
                public.Key.History.os, public.Key.History.node_old_path, public.Key.History.node_def_desc,
                public.Key.History.node_type_name, public.Key.History.node_category, public.Key.History.userid,
                public.Key.History.icon, public.Key.History.thumb_filename, public.Key.History.thumb_dirpath,
                public.Key.History.video_filename, public.Key.History.video_dirpath]
            assert len(hist_key_lst) == len(data)
            hist_dat = collections.OrderedDict(itertools.izip(hist_key_lst, data))
            del hist_dat[public.Key.History.reg_time]
            hist_dat[public.Key.History.ihda_dirpath] = hist_dat[public.Key.History.ihda_dirpath].as_posix()
            hist_dat[public.Key.History.hip_dirpath] = hist_dat[public.Key.History.hip_dirpath].as_posix()
            if hist_dat.get(public.Key.History.thumb_dirpath) is not None:
                hist_dat[public.Key.History.thumb_dirpath] = hist_dat[public.Key.History.thumb_dirpath].as_posix()
            if hist_dat.get(public.Key.History.video_dirpath) is not None:
                hist_dat[public.Key.History.video_dirpath] = hist_dat[public.Key.History.video_dirpath].as_posix()
            hist_dat[public.Key.History.icon] = SQLite3DatabaseAPI.__make_icon_to_string(
                hist_dat[public.Key.History.icon])
            dat = tuple(hist_dat.values())
            cursor = self.__cursor.execute(query, dat)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_history (insert) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    # ################ update BEGIN ################## #
    def update_hda_info(self, hda_key_id=None, version=None, filename=None, dirpath=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''
        UPDATE hda_info SET version = '{ver}', filename = '{fname}', dirpath = '{dirpath}', 
        modified_registration_datetime = (SELECT DATETIME('now', 'localtime')) WHERE hda_key_id = {hda_key_id}
        '''.format(ver=version, fname=filename, dirpath=dirpath.as_posix(), hda_key_id=hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_info(self, hda_key_id=None, node_path=None):
        query = '''
        UPDATE houdini_node_info SET node_old_path = '{nodepath}' WHERE hda_key_id = {hda_key_id}
        '''.format(nodepath=node_path, hda_key_id=hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** houdini_node_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_hda_name(self, hda_key_id=None, name=None, filename=None, dirpath=None, node_old_path=None,
                        thumbnail_dirpath=None, thumbnail_filename=None, video_dirpath=None, video_filename=None):
        assert isinstance(dirpath, pathlib2.Path)
        query_hda_key = '''UPDATE hda_key SET name = '{0}' WHERE id = {1}'''.format(name, hda_key_id)
        query_hda_info = '''
        UPDATE hda_info SET filename = '{0}', dirpath = '{1}',
        modified_registration_datetime = (SELECT DATETIME('now', 'localtime')) WHERE hda_key_id = {2}
        '''.format(filename, dirpath.as_posix(), hda_key_id)
        query_hou_node_info = '''
        UPDATE houdini_node_info SET node_old_path = '{0}' WHERE hda_key_id = {1}
        '''.format(node_old_path, hda_key_id)
        query_thumb_info = None
        query_video_info = None
        if thumbnail_dirpath is not None:
            assert isinstance(thumbnail_dirpath, pathlib2.Path)
            query_thumb_info = '''
            UPDATE thumbnail_info SET dirpath = '{0}', filename = '{1}' WHERE hda_key_id = {2}
            '''.format(thumbnail_dirpath.as_posix(), thumbnail_filename, hda_key_id)
        if video_dirpath is not None:
            assert isinstance(video_dirpath, pathlib2.Path)
            query_video_info = '''
            UPDATE video_info SET dirpath = '{0}', filename = '{1}' WHERE hda_key_id = {2}
            '''.format(video_dirpath.as_posix(), video_filename, hda_key_id)
        try:
            res_cnt = 0
            cursor_hda_key = self.__cursor.execute(query_hda_key)
            cursor_hda_info = self.__cursor.execute(query_hda_info)
            cursor_hou_node_info = self.__cursor.execute(query_hou_node_info)
            rows_thumb_info = 0
            rows_video_info = 0
            if query_thumb_info is not None:
                cursor_thumb_info = self.__cursor.execute(query_thumb_info)
                rows_thumb_info = cursor_thumb_info.rowcount
            if query_video_info is not None:
                cursor_video_info = self.__cursor.execute(query_video_info)
                rows_video_info = cursor_video_info.rowcount
            self.__connect.commit()
            res_cnt += (cursor_hda_key.rowcount + cursor_hda_info.rowcount + cursor_hou_node_info.rowcount)
            res_cnt += (rows_thumb_info + rows_video_info)
            return res_cnt
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_name (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_hda_name_to_history(
            self, hda_key_id=None, hda_version=None, hda_filename=None, hda_dirpath=None,
            thumb_dirpath=None, thumb_filename=None, video_dirpath=None, video_filename=None):
        assert isinstance(hda_dirpath, pathlib2.Path)
        assert isinstance(thumb_dirpath, pathlib2.Path)
        if video_dirpath is not None:
            query_whole_dirpath = '''
            UPDATE hda_history SET hda_dirpath = '{0}', thumb_dirpath = '{1}',
            video_dirpath = 
            CASE 
                WHEN video_dirpath IS NOT NULL
                    THEN '{2}'
                ELSE video_dirpath
            END
            WHERE hda_key_id = {3}
            '''.format(hda_dirpath.as_posix(), thumb_dirpath.as_posix(), video_dirpath.as_posix(), hda_key_id)
            query_filename_by_ver = '''
            UPDATE hda_history SET hda_filename = '{0}', thumb_filename = '{1}',
            video_filename = 
            CASE 
                WHEN video_filename IS NOT NULL
                    THEN '{2}'
                ELSE video_filename
            END
            WHERE hda_key_id = {3} AND version = '{4}'
            '''.format(hda_filename, thumb_filename, video_filename, hda_key_id, hda_version)
        else:
            query_whole_dirpath = '''
            UPDATE hda_history SET hda_dirpath = '{0}', thumb_dirpath = '{1}' WHERE hda_key_id = {2}
            '''.format(hda_dirpath.as_posix(), thumb_dirpath.as_posix(), hda_key_id)
            query_filename_by_ver = '''
            UPDATE hda_history SET hda_filename = '{0}', thumb_filename = '{1}'
            WHERE hda_key_id = {2} AND version = '{3}'
            '''.format(hda_filename, thumb_filename, hda_key_id, hda_version)
        #
        # most_recent_hist_id = self.get_most_recent_ihda_history_id(
        #     hda_key_id=hda_key_id, hda_version=hda_version)
        # query_comment = '''
        # UPDATE hda_history SET comment = '{0}' WHERE id = {1}
        # '''.format('NAME (CHANGE)', most_recent_hist_id)
        #
        try:
            res_cnt = 0
            dirpath_cursor = self.__cursor.execute(query_whole_dirpath)
            filename_cursor = self.__cursor.execute(query_filename_by_ver)
            # comment_cursor = self.__cursor.execute(query_comment)
            self.__connect.commit()
            # res_cnt += (dirpath_cursor.rowcount + filename_cursor.rowcount + comment_cursor.rowcount)
            res_cnt += (dirpath_cursor.rowcount + filename_cursor.rowcount)
            return res_cnt
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_name_to_history (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_load_count(self, hda_key_id=None):
        query = '''
        UPDATE hda_info SET load_count = load_count + 1 WHERE hda_key_id = {0}
        '''.format(hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** load_count (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_hda_favorite(self, hda_key_id=None):
        query = '''
        UPDATE hda_info SET is_favorite = is_favorite <> 1 WHERE hda_key_id = {0}
        '''.format(hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_favorite (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_note_info(self, hda_key_id=None, note=''):
        query = '''
        UPDATE note_info SET note = '{note}' WHERE hda_key_id = {hda_key_id}
        '''.format(note=note, hda_key_id=hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** note_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_video_info(self, hda_key_id=None, filename=None, dirpath=None, version=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''UPDATE video_info SET filename = '{0}', dirpath = '{1}', version = '{2}'
        WHERE hda_key_id = {3}'''.format(
            filename, dirpath.as_posix(), version, hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** video_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_thumbnail_info(self, hda_key_id=None, filename=None, dirpath=None, version=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''UPDATE thumbnail_info SET filename = '{0}', dirpath = '{1}', version = '{2}'
        WHERE hda_key_id = {3}'''.format(
            filename, dirpath.as_posix(), version, hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** thumbnail_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_hipfile_info(
            self, hda_key_id=None, filename=None, dirpath=None, houdini_version=None,
            hda_license=None, operating_system=None, sf=None, ef=None, fps=None):
        assert isinstance(dirpath, pathlib2.Path)
        query = '''
        UPDATE hipfile_info SET filename = '{fname}', dirpath = '{dpath}', houdini_version = '{hver}',
            hda_license = '{lic}', operating_system = '{os}', sf = {sf}, ef = {ef}, fps = {fps}
        WHERE hda_key_id = {hkey}
        '''.format(
            fname=filename, dpath=dirpath.as_posix(), hver=houdini_version, lic=hda_license,
            os=operating_system, sf=sf, ef=ef, fps=fps, hkey=hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hipfile_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_location_info(
            self, hda_key_id=None, country=None, timezone=None, region=None, city=None, ip=None,
            localx=None, localy=None, org=None, postal=None):
        query = '''
        UPDATE location_info SET country = '{ctry}', timezone = '{tzone}', region = '{reg}',
            city = '{city}', ip = {ip}, localx = {x}, localy = {y}, org = '{org}', 
            postal = {postal} WHERE hda_key_id = {hkey}
        '''.format(
            ctry=country, tzone=timezone, reg=region, city=city, ip=SQLite3DatabaseAPI.inet_aton(ip),
            x=localx, y=localy, org=org, postal=postal, hkey=hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** location_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_icon_info(self, hda_key_id=None, icon_lst=()):
        if not len(icon_lst):
            return None
        icon_join_str = ','.join(map(lambda x: x.strip(), icon_lst))
        query = '''
        UPDATE icon_info SET icon = '{0}' WHERE hda_key_id = {1}
        '''.format(icon_join_str, hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** icon_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_tag_info(self, hda_key_id=None, tag_lst=()):
        if len(tag_lst):
            tag_join_str = '#'.join(map(lambda x: x.strip(), tag_lst))
        else:
            tag_join_str = ''
        query = '''
        UPDATE tag_info SET tag = '{0}' WHERE hda_key_id = {1}
        '''.format(tag_join_str, hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** tag_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_category_path_info(self, info_id=None, node_category_lst=()):
        if not len(node_category_lst):
            return None
        join_str = ','.join(map(lambda x: x.strip(), node_category_lst))
        query = '''
        UPDATE houdini_node_category_path_info SET node_category = '{0}' WHERE info_id = {1}
        '''.format(join_str, info_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='*** houdini_node_category_path_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_type_path_info(self, info_id=None, node_type_lst=()):
        if not len(node_type_lst):
            return None
        join_str = ','.join(map(lambda x: x.strip(), node_type_lst))
        query = '''
        UPDATE houdini_node_type_path_info SET node_type = '{0}' WHERE info_id = {1}
        '''.format(join_str, info_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='*** houdini_node_type_path_info (update) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def update_houdini_node_input_connect_info(self, info_id=None, node_input_connect_lst=()):
        _ = self.delete_houdini_node_input_connect_info(info_id=info_id)
        is_hou_node_input_connect_info = self.insert_houdini_node_input_connect_info(
            info_id=info_id, node_input_connect_lst=node_input_connect_lst)
        return is_hou_node_input_connect_info

    def update_houdini_node_output_connect_info(self, info_id=None, node_output_connect_lst=()):
        _ = self.delete_houdini_node_output_connect_info(info_id=info_id)
        is_hou_node_output_connect_info = self.insert_houdini_node_output_connect_info(
            info_id=info_id, node_output_connect_lst=node_output_connect_lst)
        return is_hou_node_output_connect_info
    # ################ update END #################### #

    # ################ delete BEGIN #################### #
    def delete_hda_category(self, category=None, user_id=None):
        cnt_hda_key_by_cate = self.get_count_hda_key(category=category, user_id=user_id)
        if cnt_hda_key_by_cate != 0:
            return 0
        query = '''
        DELETE FROM hda_category WHERE category = '{cate}' AND user_id = '{userid}'
        '''.format(cate=category, userid=user_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_category (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_hda_key(self, name=None, category=None, user_id=None):
        query = '''
        DELETE FROM hda_key WHERE name = '{name}' AND category = '{cate}' AND user_id = '{userid}'
        '''.format(name=name, cate=category, userid=user_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_key (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_hda_key_with_id(self, hda_key_id=None):
        query = 'DELETE FROM hda_key WHERE id = {0}'.format(hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_key (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_houdini_node_category_path_info(self, info_id=None):
        query = '''
        DELETE FROM houdini_node_category_path_info WHERE info_id = {0}
        '''.format(info_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='*** houdini_node_category_path_info (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_houdini_node_type_path_info(self, info_id=None):
        query = '''
        DELETE FROM houdini_node_type_path_info WHERE info_id = {0}
        '''.format(info_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='*** houdini_node_type_path_info (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_houdini_node_input_connect_info(self, info_id=None):
        query = '''
        DELETE FROM houdini_node_input_connect_info WHERE info_id = {0}
        '''.format(info_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='*** houdini_node_input_connect_info (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_houdini_node_output_connect_info(self, info_id=None):
        query = '''
        DELETE FROM houdini_node_output_connect_info WHERE info_id = {0}
        '''.format(info_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='*** houdini_node_output_connect_info (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_tag_info(self, hda_key_id=None):
        query = '''DELETE FROM tag_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** tag_info (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_icon_info(self, hda_key_id=None):
        query = '''DELETE FROM icon_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** icon_info (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_hda_history(self, hda_key_id=None, hist_id=None):
        if (hda_key_id is None) and (hist_id is None):
            query = '''DELETE FROM hda_history'''
        elif (hda_key_id is not None) and (hist_id is None):
            query = '''
            DELETE FROM hda_history WHERE hda_key_id = {0}
            '''.format(hda_key_id)
        elif (hda_key_id is None) and (hist_id is not None):
            query = '''
                DELETE FROM hda_history WHERE id = {0}
                '''.format(hist_id)
        else:
            query = '''
            DELETE FROM hda_history WHERE hda_key_id = {0} AND id = {1}
            '''.format(hda_key_id, hist_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_history (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_hda_record(self, hda_key_id=None, record_id=None):
        if (hda_key_id is None) and (record_id is None):
            query = '''DELETE FROM hda_node_location_record'''
        elif (hda_key_id is not None) and (record_id is None):
            query = '''
            DELETE FROM hda_node_location_record WHERE hda_key_id = {0}
            '''.format(hda_key_id)
        elif (hda_key_id is None) and (record_id is not None):
            query = '''
                DELETE FROM hda_node_location_record WHERE id = {0}
                '''.format(record_id)
        else:
            query = '''
            DELETE FROM hda_node_location_record WHERE hda_key_id = {0} AND id = {1}
            '''.format(hda_key_id, record_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_node_location_record (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    def delete_hda_note_history(self, hda_key_id=None):
        if hda_key_id is None:
            query = '''DELETE FROM hda_note_history'''
        else:
            query = '''DELETE FROM hda_note_history WHERE hda_key_id = {0}'''.format(hda_key_id)
        try:
            cursor = self.__cursor.execute(query)
            self.__connect.commit()
            return cursor.rowcount
        except Exception as err:
            self.__connect.rollback()
            log_handler.LogHandler.log_msg(method=logging.error, msg='*** hda_note_history (delete) ***')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            return None

    # ################ delete END ###################### #

    # ################ select BEGIN ################## #
    def is_exist_users_table(self):
        query = '''
        SELECT name FROM sqlite_master WHERE type='table' AND name='users'
        '''
        cursor = self.__cursor.execute(query)
        return cursor.fetchone() is not None

    def is_exist_user_id(self, user_id):
        query = '''SELECT COUNT(user_id) FROM users WHERE user_id = '{0}'
        '''.format(user_id)
        cursor = self.__cursor.execute(query)
        return bool(cursor.fetchone()[0])

    def is_exist_email(self, email):
        query = '''SELECT COUNT(email) FROM users WHERE email = '{0}'
        '''.format(email)
        cursor = self.__cursor.execute(query)
        return bool(cursor.fetchone()[0])

    def is_exist_tag(self, hda_key_id=None):
        query = '''SELECT hda_key_id FROM tag_info'''
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchall()
        if dat is not None:
            dat = map(lambda x: x[0], dat)
            return hda_key_id in dat
        return False

    def is_exist_note(self, hda_key_id=None):
        query = '''SELECT hda_key_id FROM note_info'''
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchall()
        if dat is not None:
            dat = map(lambda x: x[0], dat)
            return hda_key_id in dat
        return False

    def is_exist_hda_history(self, hda_key_id=None):
        if hda_key_id is None:
            query = '''SELECT COUNT(*) FROM hda_history'''
        else:
            query = '''SELECT COUNT(*) FROM hda_history WHERE hda_key_id = {0}
            '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_exist_hda_note_history(self, hda_key_id=None):
        if hda_key_id is None:
            query = '''SELECT COUNT(*) FROM hda_note_history'''
        else:
            query = '''SELECT COUNT(*) FROM hda_note_history WHERE hda_key_id = {0}
            '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_exist_hda_name(self, user_id=None, category=None, hda_name=None):
        query = '''
        SELECT COUNT(*) FROM hda_key WHERE user_id = '{0}' AND category = '{1}' AND name = '{2}'
        '''.format(user_id, category, hda_name)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_exist_hda_node_loc_file(self, hda_key_id=None, version=None, user_id=None):
        query = '''
        SELECT COUNT(*) FROM hda_history WHERE hda_key_id = {0} AND version = '{1}' AND userid = '{2}'
        '''.format(hda_key_id, version, user_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return bool(dat)

    def is_exist_hda_node_loc_record(self, hda_key_id=None, hip_filename=None, hip_dirpath=None,
                                     parent_node_path=None, node_name=None, node_ver=None):
        assert isinstance(hip_dirpath, pathlib2.Path)
        query = '''
        SELECT COUNT(*) FROM hda_node_location_record 
        WHERE hda_key_id = {0} AND hip_filename = '{1}' AND hip_dirpath = '{2}' AND parent_node_path = '{3}'
            AND node_name = '{4}' AND node_version = '{5}'
        '''.format(hda_key_id, hip_filename, hip_dirpath.as_posix(), parent_node_path, node_name, node_ver)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return bool(dat)

    # 마지막 버전인지
    def is_ihda_lastest_version(self, hda_key_id=None, version=None):
        query = '''SELECT COUNT(*) FROM hda_info WHERE hda_key_id = {0} AND version = '{1}'
        '''.format(hda_key_id, version)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return bool(dat)

    # 등록되어있는 히스토리중 최신 버전인지
    def is_most_recent_ihda_history(self, hda_key_id=None, hist_id=None):
        query = '''SELECT MAX(id) FROM hda_history WHERE hda_key_id = {0}
        '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat == hist_id

    # iHDA와 video파일이 같은 버전인지
    # 이 함수의 존재의미는 thumbnail과는 다르게 video는 공유하기 때문에 rename시 문제가 되어
    # 같은 버전의 비디오의 이름만 바꾸기 위함이다.
    def is_video_and_ihda_same_version(self, hda_key_id=None, version=None):
        query = '''
        SELECT COUNT(*) FROM video_info WHERE hda_key_id = {0} AND version = '{1}'
        '''.format(hda_key_id, version)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return bool(dat)

    # 등록되어있는 히스토리중 최신 버전인지
    def get_most_recent_ihda_history_id(self, hda_key_id=None, hda_version=None):
        query = '''SELECT MAX(id) FROM hda_history WHERE hda_key_id = {0} AND version = '{1}'
        '''.format(hda_key_id, hda_version)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def count_hda_history(self, hda_key_id=None):
        if hda_key_id is None:
            query = '''SELECT COUNT(*) FROM hda_history'''
        else:
            query = '''SELECT COUNT(*) FROM hda_history WHERE hda_key_id = {0}
            '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def count_hda_note_history(self, hda_key_id=None):
        if hda_key_id is None:
            query = '''SELECT COUNT(*) FROM hda_note_history'''
        else:
            query = '''SELECT COUNT(*) FROM hda_note_history WHERE hda_key_id = {0}
            '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def get_user_id(self):
        query = 'SELECT user_id FROM users'
        cursor = self.__cursor.execute(query)
        dat = list(map(lambda x: x[0], cursor.fetchall()))
        return dat

    def get_email(self, user_id=None):
        if user_id is None:
            query = 'SELECT email FROM users'
        else:
            query = '''SELECT email FROM users WHERE user_id = '{0}'
            '''.format(user_id)
        cursor = self.__cursor.execute(query)
        dat = list(map(lambda x: x[0], cursor.fetchall()))
        return dat

    def get_hda_category(self, user_id=None):
        query = '''
        SELECT category FROM hda_category WHERE user_id = '{userid}' ORDER BY category
        '''.format(userid=user_id)
        cursor = self.__cursor.execute(query)
        dat = list(map(lambda x: x[0], cursor.fetchall()))
        return dat

    def get_hda_key_id(self, category=None, name=None, user_id=None):
        query = 'SELECT id FROM hda_key'
        if user_id is not None:
            query = '''{0} WHERE user_id = '{1}'
            '''.format(query, user_id)
        if category is not None:
            query = ''' {0} AND category = '{1}'
            '''.format(query, category)
        if name is not None:
            query = ''' {0} AND name = '{1}'
            '''.format(query, name)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        return map(lambda x: x[0], fetch_dat)

    def get_hou_node_info_id(self, hda_key_id=None):
        query = '''SELECT id FROM houdini_node_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def get_hda_name(self, category=None, user_id=None, with_id=False):
        if category is None:
            if with_id:
                query = '''
                SELECT id, name FROM hda_key WHERE user_id = '{0}'
                '''.format(user_id)
            else:
                query = '''
                SELECT name FROM hda_key WHERE user_id = '{0}'
                '''.format(user_id)
        else:
            if with_id:
                query = '''
                SELECT id, name FROM hda_key WHERE category = '{0}' AND user_id = '{1}'
                '''.format(category, user_id)
            else:
                query = '''
                SELECT name FROM hda_key WHERE category = '{0}' AND user_id = '{1}'
                '''.format(category, user_id)
        query = '''{0} ORDER BY name'''.format(query)
        cursor = self.__cursor.execute(query)
        dat = map(lambda x: list(x), cursor.fetchall())
        return dat

    def get_all_hda_fileinfo(self, user_id=None):
        query = '''
        SELECT hinfo.hda_key_id, hinfo.dirpath, hinfo.filename, hkey.category FROM hda_info AS hinfo
        INNER JOIN hda_key AS hkey
        ON hinfo.hda_key_id = hkey.id
        WHERE hkey.user_id = '{0}'
        '''.format(user_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        return fetch_dat

    # 기존 노드를 업데이트할 때 원래의 정보를 가져오는 함수
    def get_update_before_data(self, hda_key_id=None):
        query = '''
        SELECT is_favorite, load_count, initial_registration_datetime,
            (SELECT tag_info.tag FROM tag_info WHERE tag_info.hda_key_id = {0}),
            (SELECT note_info.note FROM note_info WHERE note_info.hda_key_id = {1}),
            (SELECT video_info.dirpath FROM video_info WHERE video_info.hda_key_id = {2}),
            (SELECT video_info.filename FROM video_info WHERE video_info.hda_key_id = {3})
        FROM hda_info WHERE hda_key_id = {4}
        '''.format(hda_key_id, hda_key_id, hda_key_id, hda_key_id, hda_key_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        key_lst = [
            public.Key.is_favorite_hda, public.Key.hda_load_count, public.Key.hda_ctime,
            public.Key.hda_tags, public.Key.hda_note, public.Key.video_dirpath,
            public.Key.video_filename]
        data = dict(itertools.izip(key_lst, fetch_dat))
        # dirpath
        tags = data.get(public.Key.hda_tags)
        if tags is None:
            data[public.Key.hda_tags] = list()
        else:
            data[public.Key.hda_tags] = tags.split('#')
        video_dirpath = data.get(public.Key.video_dirpath)
        if video_dirpath is not None:
            data[public.Key.video_dirpath] = pathlib2.Path(video_dirpath)
        return data

    def get_hda_filepath(self, hda_key_id=None):
        query = 'SELECT dirpath, filename FROM hda_info WHERE hda_key_id = {0}'.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        if any(itertools.imap(lambda x: x is None, fetch_dat)):
            return None
        filepath = pathlib2.Path(fetch_dat[0]) / fetch_dat[1]
        return filepath

    def get_all_hda_record_fileinfo(self, hda_key_id=None, hip_filename=None, hip_dirpath=None, user_id=None):
        query = '''
        SELECT hrecord.id, hrecord.hip_dirpath, hrecord.hip_filename, hrecord.hda_dirpath, hrecord.hda_filename 
        FROM hda_node_location_record AS hrecord
        INNER JOIN hda_key AS hkey 
        ON hrecord.hda_key_id = hkey.id
        WHERE hkey.user_id = '{0}'
        '''.format(user_id)
        if hda_key_id is not None:
            query = '''{0} AND hda_key_id = {1}'''.format(query, hda_key_id)
        if (hip_filename is not None) and (hip_dirpath is not None):
            assert isinstance(hip_dirpath, pathlib2.Path)
            query = '''{0} AND hip_filename = '{1}' AND hip_dirpath = '{2}'
            '''.format(query, hip_filename, hip_dirpath.as_posix())
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        return fetch_dat

    def get_all_hda_history_fileinfo(self, user_id=None):
        query = '''
        SELECT id, hda_key_id, hda_dirpath, hda_filename FROM hda_history WHERE userid = '{0}'
        '''.format(user_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        return fetch_dat

    def get_hda_version(self, hda_key_id=None):
        query = '''SELECT version FROM hda_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def get_hda_node_type(self, hda_key_id=None):
        query = '''SELECT node_type_name FROM houdini_node_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def get_hist_hda_license(self, hda_key_id=None, version=None, user_id=None):
        query = '''
        SELECT hda_license FROM hda_history WHERE hda_key_id = {0} AND version = '{1}' AND userid = '{2}'
        '''.format(hda_key_id, version, user_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def get_count_hda_key(self, name=None, category=None, user_id=None):
        ele_dat = {'name': name, 'category': category, 'user_id': user_id}
        logic_lst = ['AND', 'AND']
        query = 'SELECT COUNT(ALL name) FROM hda_key'
        if (name is not None) or (category is not None) or (user_id is not None):
            query += ' WHERE'
            for val in ele_dat.itervalues():
                if val is None:
                    if len(logic_lst):
                        logic_lst.pop(0)
            for key, val in ele_dat.iteritems():
                if val is None:
                    continue
                if len(logic_lst):
                    logic = ' ' + logic_lst.pop(0)
                else:
                    logic = ''
                query += ''' {k} = '{v}'{logic}'''.format(k=key, v=val, logic=logic)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        return dat

    def get_icon_info_by_user(self, user_id=None):
        if user_id is None:
            query = '''
            SELECT hkey.id, (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id)
            FROM hda_key AS hkey
            '''
        else:
            query = '''
            SELECT hkey.id, (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id)
            FROM hda_key AS hkey WHERE user_id = '{0}'
            '''.format(user_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        dat = list()
        for row_val in sorted(fetch_dat, key=lambda x: x[0]):
            tmp_dat = list(row_val)
            tmp_dat[-1] = map(str, tmp_dat[-1].split(','))
            dat.append(tmp_dat)
        return dat

    def get_icon_info(self, hda_key_id=None, is_only_icon=False):
        if is_only_icon:
            query = '''SELECT icon FROM icon_info WHERE hda_key_id = {0}'''.format(hda_key_id)
            cursor = self.__cursor.execute(query)
            fetch_dat = cursor.fetchone()[0]
            dat = map(lambda x: x.strip(), fetch_dat.split(','))
        else:
            query = '''SELECT id, hda_key_id, icon FROM icon_info WHERE hda_key_id = {0}'''.format(hda_key_id)
            cursor = self.__cursor.execute(query)
            dat = list(cursor.fetchone())
            dat[2] = map(lambda x: x.strip(), dat[2].split(','))
        return dat

    def get_note_info(self, hda_key_id=None):
        query = '''SELECT note FROM note_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()
        if dat is None:
            return None
        return dat[0]

    def get_hipfile_info(self, hda_key_id=None):
        query = '''
        SELECT filename, dirpath, houdini_version, hda_license, operating_system, sf, ef, fps
        FROM hipfile_info WHERE hda_key_id = {0}
        '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = list(cursor.fetchone())
        dat[1] = pathlib2.Path(dat[1])
        return dat

    def get_location_info(self, hda_key_id=None):
        query = '''
        SELECT country, timezone, region, city, INET_NTOA(ip), localx, localy, org, postal
        FROM location_info WHERE hda_key_id = {0}
        '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()
        if dat is None:
            return None
        return list(dat)

    def get_houdini_node_input_connect_info(self, info_id=None):
        query = '''
        SELECT curt_node_input_idx, connect_node_name, connect_node_type, connect_output_idx
        FROM houdini_node_input_connect_info WHERE info_id = {0}
        '''.format(info_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return None
        return map(lambda x: list(x), dat)

    def get_houdini_node_output_connect_info(self, info_id=None):
        query = '''
        SELECT curt_node_output_idx, connect_node_name, connect_node_type, connect_input_idx
        FROM houdini_node_output_connect_info WHERE info_id = {0}
        '''.format(info_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return None
        return map(lambda x: list(x), dat)

    def get_houdini_node_category_path_info(self, info_id=None):
        query = '''
        SELECT node_category FROM houdini_node_category_path_info WHERE info_id = {0}
        '''.format(info_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        return map(lambda x: x.strip(), fetch_dat[0].split(','))

    def get_houdini_node_type_path_info(self, info_id=None):
        query = '''
        SELECT node_type FROM houdini_node_type_path_info WHERE info_id = {0}
        '''.format(info_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return None
        return map(lambda x: x.strip(), fetch_dat[0].split(','))

    def get_video_info(self, hda_key_id=None):
        query = '''SELECT dirpath, filename FROM video_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()
        if dat is None:
            return None
        dat = list(dat)
        dat[0] = pathlib2.Path(dat[0])
        return dat[0] / dat[1]

    def get_history_video_info(self, hda_key_id=None):
        query = '''
        SELECT dirpath, filename FROM video_info WHERE hda_key_id = {0}
        '''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        if fetch_dat is None:
            return None
        dat = list()
        for video_info in fetch_dat:
            dat.append(pathlib2.Path(video_info[0]) / video_info[1])
        return dat

    def get_thumbnail_info(self, hda_key_id=None):
        query = '''SELECT dirpath, filename FROM thumbnail_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()
        if dat is None:
            return None
        dat = list(dat)
        dat[0] = pathlib2.Path(dat[0])
        return dat[0] / dat[1]

    def get_tag_info(self, hda_key_id=None):
        query = '''SELECT tag FROM tag_info WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()
        if dat is None:
            return None
        dat = dat[0]
        if not len(dat):
            return None
        return map(lambda x: x.strip(), dat.split('#'))

    def get_thumbnail_by_hda_history(self, user_id=None):
        query = '''
        SELECT id, thumb_dirpath, thumb_filename FROM hda_history WHERE userid = '{0}' ORDER BY id
        '''.format(user_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        dat = list()
        key_lst = [public.Key.History.hist_id, public.Key.History.thumb_dirpath, public.Key.History.thumb_filename]
        for row_val in fetch_dat:
            tmp_dict = dict(itertools.izip(key_lst, row_val))
            tmp_dict[public.Key.History.thumb_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.History.thumb_dirpath))
            dat.append(tmp_dict)
        return dat

    def get_hda_node_location_record(self, hda_key_id=None, hip_filename=None, hip_dirpath=None):
        query = '''
        SELECT id, hda_key_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
            parent_node_path, node_type, node_category, node_name, node_version, 
            houdini_version, houdini_license, operating_system, sf, ef, fps, ctime, mtime
        FROM hda_node_location_record'''
        if hda_key_id is not None:
            query = '''{0} WHERE hda_key_id = {1}'''.format(query, hda_key_id)
        if (hip_filename is not None) and (hip_dirpath is not None):
            assert isinstance(hip_dirpath, pathlib2.Path)
            if hda_key_id is None:
                query = '''{0} WHERE hip_filename = '{1}' AND hip_dirpath = '{2}'
                '''.format(query, hip_filename, hip_dirpath.as_posix())
            else:
                query = '''{0} AND hip_filename = '{1}' AND hip_dirpath = '{2}'
                '''.format(query, hip_filename, hip_dirpath.as_posix())
        query = '''{0} ORDER BY hip_dirpath, hip_filename, parent_node_path, node_name, node_version'''.format(query)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return dict()
        key_lst = SQLite3DatabaseAPI.hda_record_key_lst()
        assert len(fetch_dat[0]) == len(key_lst)
        dat = dict()
        for row_val in fetch_dat:
            tmp_dict = dict(itertools.izip(key_lst, row_val))
            hip_dpath = tmp_dict.get(public.Key.Record.hip_dirpath)
            hip_fname = tmp_dict.get(public.Key.Record.hip_filename)
            hda_dpath = tmp_dict.get(public.Key.Record.hda_dirpath)
            hda_fname = tmp_dict.get(public.Key.Record.hda_filename)
            pnode_path = tmp_dict.get(public.Key.Record.parent_node_path)
            node_name = tmp_dict.get(public.Key.Record.node_name)
            node_ver = tmp_dict.get(public.Key.Record.node_ver)
            node_type = tmp_dict.get(public.Key.Record.node_type)
            node_cate = tmp_dict.get(public.Key.Record.node_cate)
            record_id = tmp_dict.get(public.Key.Record.record_id)
            hda_id = tmp_dict.get(public.Key.Record.hda_id)
            ctime = tmp_dict.get(public.Key.Record.ctime)
            mtime = tmp_dict.get(public.Key.Record.mtime)
            hou_version = tmp_dict.get(public.Key.Record.houdini_version)
            hou_license = tmp_dict.get(public.Key.Record.houdini_license)
            operating_system = tmp_dict.get(public.Key.Record.operating_system)
            sf = tmp_dict.get(public.Key.Record.sf)
            ef = tmp_dict.get(public.Key.Record.ef)
            fps = tmp_dict.get(public.Key.Record.fps)
            # 노드와 버전이 함께 보여지도록. 그리고 이래야 key data로 record데이터를 지울 때 명확하다.
            node_name_with_ver = '{0} (v{1})'.format(node_name, node_ver)
            if hip_dpath not in dat:
                dat[hip_dpath] = dict()
            if hip_fname not in dat[hip_dpath]:
                dat[hip_dpath][hip_fname] = dict()
            if pnode_path not in dat[hip_dpath][hip_fname]:
                dat[hip_dpath][hip_fname][pnode_path] = list()
            dat[hip_dpath][hip_fname][pnode_path].append(
                [record_id, hda_id, node_name_with_ver, node_type, node_cate, node_ver, ctime, mtime,
                 pathlib2.Path(hip_dpath), hip_fname, pathlib2.Path(hda_dpath), hda_fname,
                 hou_version, hou_license, operating_system, sf, ef, fps, node_name]
            )
        return dat

    @staticmethod
    def hda_record_key_lst():
        key_lst = [public.Key.Record.record_id, public.Key.Record.hda_id,
                   public.Key.Record.hip_filename, public.Key.Record.hip_dirpath,
                   public.Key.Record.hda_filename, public.Key.Record.hda_dirpath,
                   public.Key.Record.parent_node_path, public.Key.Record.node_type,
                   public.Key.Record.node_cate, public.Key.Record.node_name, public.Key.Record.node_ver,
                   public.Key.Record.houdini_version, public.Key.Record.houdini_license,
                   public.Key.Record.operating_system, public.Key.Record.sf, public.Key.Record.ef,
                   public.Key.Record.fps, public.Key.Record.ctime, public.Key.Record.mtime]
        return key_lst

    def get_only_detailview_record_data(self, record_id=None):
        query = '''
        SELECT id, hda_key_id, hip_filename, hip_dirpath, hda_filename, hda_dirpath,
            parent_node_path, node_type, node_category, node_name, node_version, 
            houdini_version, houdini_license, operating_system, sf, ef, fps, ctime, mtime,
            (SELECT thumb_dirpath FROM hda_history AS hhist
                WHERE hhist.hda_key_id = hrecord.hda_key_id AND hhist.version = hrecord.node_version),
            (SELECT thumb_filename FROM hda_history AS hhist
                WHERE hhist.hda_key_id = hrecord.hda_key_id AND hhist.version = hrecord.node_version)
        FROM hda_node_location_record AS hrecord 
        WHERE id = {0}'''.format(record_id)
        cursor = self.__cursor.execute(query)
        fetch_dat = cursor.fetchone()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return dict()
        key_lst = SQLite3DatabaseAPI.hda_record_key_lst()
        key_lst.append(public.Key.Record.thumb_dirpath)
        key_lst.append(public.Key.Record.thumb_filename)
        assert len(fetch_dat) == len(key_lst)
        dat = dict(itertools.izip(key_lst, fetch_dat))
        thumb_dirpath = dat.get(public.Key.Record.thumb_dirpath)
        if thumb_dirpath is not None:
            dat[public.Key.Record.thumb_dirpath] = pathlib2.Path(thumb_dirpath)
        return dat

    def get_hda_history(self, hda_key_id=None, user_id=None, search_date=None):
        if hda_key_id is not None:
            query = '''
            SELECT id, hda_key_id, comment, org_hda_name, version, hda_filename, hda_dirpath,
                registration_datetime, houdini_version, hip_filename, hip_dirpath, hda_license, 
                operating_system, node_old_path, node_def_desc, node_type_name, node_category, userid, icon,
                (SELECT tag FROM tag_info WHERE hda_key_id = hda_history.hda_key_id),
                thumb_filename, thumb_dirpath, video_filename, video_dirpath
            FROM hda_history WHERE hda_key_id = {0} AND userid = '{1}'
            '''.format(hda_key_id, user_id)
        else:
            query = '''
            SELECT id, hda_key_id, comment, org_hda_name, version, hda_filename, hda_dirpath,
                registration_datetime, houdini_version, hip_filename, hip_dirpath, hda_license, 
                operating_system, node_old_path, node_def_desc, node_type_name, node_category, userid, icon,
                (SELECT tag FROM tag_info WHERE hda_key_id = hda_history.hda_key_id),
                thumb_filename, thumb_dirpath, video_filename, video_dirpath
            FROM hda_history WHERE userid = '{0}'
            '''.format(user_id)
        if search_date is not None:
            query = '''{0} AND registration_datetime BETWEEN '{1}' AND '{2}'
            '''.format(query, *search_date)
        query = '''{0} ORDER BY id'''.format(query)
        cursor = self.__cursor.execute(query)
        key_lst = SQLite3DatabaseAPI.hda_history_key_lst()
        fetch_dat = cursor.fetchall()
        if (fetch_dat is None) or (not len(fetch_dat)):
            return list()
        dat = list()
        for row_val in fetch_dat:
            tmp_dict = dict(itertools.izip(key_lst, row_val))
            tags = tmp_dict.get(public.Key.History.tags)
            if tags is None:
                tmp_dict[public.Key.History.tags] = list()
            else:
                tmp_dict[public.Key.History.tags] = tags.split('#')
            tmp_dict[public.Key.History.icon] = tmp_dict.get(public.Key.History.icon).split(',')
            tmp_dict[public.Key.History.ihda_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.History.ihda_dirpath))
            tmp_dict[public.Key.History.hip_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.History.hip_dirpath))
            tmp_dict[public.Key.History.thumb_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.History.thumb_dirpath))
            if tmp_dict.get(public.Key.History.video_dirpath) is not None:
                tmp_dict[public.Key.History.video_dirpath] = pathlib2.Path(
                    tmp_dict.get(public.Key.History.video_dirpath))
            dat.append(tmp_dict)
        return dat

    @staticmethod
    def hda_history_key_lst():
        key_lst = [
            public.Key.History.hist_id,
            public.Key.History.hda_id,
            public.Key.History.comment,
            public.Key.History.org_hda_name,
            public.Key.History.version,
            public.Key.History.ihda_filename,
            public.Key.History.ihda_dirpath,
            public.Key.History.reg_time,
            public.Key.History.hou_version,
            public.Key.History.hip_filename,
            public.Key.History.hip_dirpath,
            public.Key.History.hda_license,
            public.Key.History.os,
            public.Key.History.node_old_path,
            public.Key.History.node_def_desc,
            public.Key.History.node_type_name,
            public.Key.History.node_category,
            public.Key.History.userid,
            public.Key.History.icon,
            public.Key.History.tags,
            public.Key.History.thumb_filename,
            public.Key.History.thumb_dirpath,
            public.Key.History.video_filename,
            public.Key.History.video_dirpath
        ]
        return key_lst

    def get_hda_history_columns(self):
        query = ''' SELECT * FROM hda_history'''
        cursor = self.__cursor.execute(query)
        columns = map(lambda x: x[0], cursor.description)
        return columns

    def get_hda_history_id(self, hda_key_id=None):
        if hda_key_id is None:
            query = '''SELECT id FROM hda_history'''
        else:
            query = '''SELECT id FROM hda_history WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return list()
        return map(lambda x: x[0], dat)

    def get_hda_note_history(self, hda_key_id=None, with_datetime=False):
        if with_datetime:
            query = '''
            SELECT registration_datetime, hda_version, note FROM hda_note_history 
            WHERE hda_key_id = {0}'''.format(hda_key_id)
        else:
            query = '''SELECT note FROM hda_note_history WHERE hda_key_id = {0}'''.format(hda_key_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchall()
        if (dat is None) or (not len(dat)):
            return None
        return dat

    # hda_Key_id, version 중 가장 최근의 video 히스토리 가져온다.
    def get_hda_history_video_most_recent_by_ver(self, hda_key_id=None, version=None):
        query_most_recent_id = '''
        SELECT MAX(id) FROM hda_history WHERE hda_key_id = {0} AND version = '{1}'
        '''.format(hda_key_id, version)
        cursor = self.__cursor.execute(query_most_recent_id)
        most_recent_id = cursor.fetchone()[0]
        if most_recent_id is None:
            return None
        query = '''SELECT video_dirpath, video_filename FROM hda_history 
        WHERE id = {0}'''.format(most_recent_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()
        if (dat is None) or (not len(dat)):
            return None
        if any(itertools.imap(lambda x: x is None, dat)):
            return None
        # dirpath
        dat = list(dat)
        dat[0] = pathlib2.Path(dat[0])
        return dat

    # hda_Key_id, version 중 가장 최근의 노트 히스토리 가져온다.
    def get_hda_note_history_most_recent_by_ver(self, hda_key_id=None, version=None):
        query_most_recent_id = '''
        SELECT MAX(id) FROM hda_note_history WHERE hda_key_id = {0} AND hda_version = '{1}'
        '''.format(hda_key_id, version)
        cursor = self.__cursor.execute(query_most_recent_id)
        most_recent_id = cursor.fetchone()[0]
        if most_recent_id is None:
            return None
        query = '''SELECT note FROM hda_note_history WHERE id = {0}'''.format(most_recent_id)
        cursor = self.__cursor.execute(query)
        dat = cursor.fetchone()[0]
        if (dat is None) or (not len(dat)):
            return None
        return dat.decode('utf8')

    # ihda data 정보
    def get_hda_data(self, category=None, user_id=None):
        if category == public.Type.root:
            category = None
        query = ''' 
SELECT hkey.id,
       hkey.name,
       hkey.category,
       hinfo.version,
       hinfo.filename,
       hinfo.dirpath,
       hinfo.is_favorite,
       hinfo.load_count,
       hinfo.initial_registration_datetime,
       hinfo.modified_registration_datetime,
       hipinfo.houdini_version,
       ninfo.node_type_name,
       ninfo.node_def_desc,
       ninfo.is_network,
       ninfo.is_sub_network,
       ninfo.node_old_path,
       hipinfo.hda_license,
       hipinfo.filename,
       hipinfo.dirpath,
       (SELECT filename FROM thumbnail_info WHERE thumbnail_info.hda_key_id = hkey.id),
       (SELECT dirpath FROM thumbnail_info WHERE thumbnail_info.hda_key_id = hkey.id),
       (SELECT filename FROM video_info WHERE video_info.hda_key_id = hkey.id),
       (SELECT dirpath FROM video_info WHERE video_info.hda_key_id = hkey.id),
       (SELECT note FROM note_info WHERE hda_key_id = hkey.id),
       (SELECT icon FROM icon_info WHERE hda_key_id = hkey.id),
       (SELECT tag FROM tag_info WHERE hda_key_id = hkey.id)
FROM hda_key AS hkey
         INNER JOIN hda_info AS hinfo
         INNER JOIN houdini_node_info AS ninfo
         INNER JOIN hipfile_info AS hipinfo
            ON hkey.id = hinfo.hda_key_id AND hkey.id = ninfo.hda_key_id AND hkey.id = hipinfo.hda_key_id
WHERE hkey.user_id = '{userid}'
        '''.format(userid=user_id)
        if category is not None:
            query = '''
            {0} AND hkey.category = '{1}'
            '''.format(query, category)
        query = '''{0} ORDER BY hkey.name'''.format(query)
        cursor = self.__cursor.execute(query)
        key_lst = SQLite3DatabaseAPI.hda_info_key_lst()
        fetch_dat = cursor.fetchall()
        if fetch_dat is None:
            return list()
        dat = list()
        for row_val in fetch_dat:
            tmp_dict = dict(itertools.izip(key_lst, row_val))
            tmp_dict[public.Key.hda_icon] = tmp_dict.get(public.Key.hda_icon).split(',')
            tags = tmp_dict.get(public.Key.hda_tags)
            if tags is None:
                tmp_dict[public.Key.hda_tags] = list()
            else:
                tmp_dict[public.Key.hda_tags] = tags.split('#')
            tmp_dict[public.Key.hda_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.hda_dirpath))
            tmp_dict[public.Key.hip_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.hip_dirpath))
            tmp_dict[public.Key.thumbnail_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.thumbnail_dirpath))
            if tmp_dict.get(public.Key.video_dirpath) is not None:
                tmp_dict[public.Key.video_dirpath] = pathlib2.Path(tmp_dict.get(public.Key.video_dirpath))
            dat.append(tmp_dict)
        return dat

    @staticmethod
    def hda_info_key_lst():
        key_lst = [
            public.Key.hda_id,
            public.Key.hda_name,
            public.Key.hda_cate,
            public.Key.hda_version,
            public.Key.hda_filename,
            public.Key.hda_dirpath,
            public.Key.is_favorite_hda,
            public.Key.hda_load_count,
            public.Key.hda_ctime,
            public.Key.hda_mtime,
            public.Key.hou_version,
            public.Key.node_type_name,
            public.Key.node_def_desc,
            public.Key.is_network,
            public.Key.is_sub_network,
            public.Key.node_old_path,
            public.Key.hda_license,
            public.Key.hip_filename,
            public.Key.hip_dirpath,
            public.Key.thumbnail_filename,
            public.Key.thumbnail_dirpath,
            public.Key.video_filename,
            public.Key.video_dirpath,
            public.Key.hda_note,
            # list
            public.Key.hda_icon,
            public.Key.hda_tags
        ]
        return key_lst

    @property
    def get_last_insert_id(self):
        return self.__cursor.lastrowid
        # self.__cursor.execute('''SELECT LAST_INSERT_ROWID()''')
        # return int(self.__cursor.fetchone()[0])
    # ################ select END #################### #


def check_db_server():
    return public.SQLite.db_filepath.exists()

