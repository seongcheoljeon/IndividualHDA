#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.05.14 01:55
# modify date       :
# description       :

import datetime
from imp import reload
from operator import itemgetter
from bisect import bisect_right
from itertools import izip

from PySide2 import QtGui, QtCore

try:
    import hou
except ImportError as err:
    pass

import public

reload(public)

import pathlib2

from libs import houdini_api

reload(houdini_api)


class Node(QtCore.QObject):
    def __init__(self, node_name=None, node_depth=None, parent=None):
        super(Node, self).__init__()
        self.__name = node_name
        self.__depth = node_depth
        self._parent = parent
        self._children = list()
        self.setParent(parent)

    def name(self):
        return self.__name

    def depth(self):
        return self.__depth

    def parent(self):
        return self._parent

    def child(self, row):
        return self._children[row]

    def insert_child(self, position, child):
        if position < 0 or position > len(self._children):
            return False
        self._children.insert(position, child)
        child._parent = self
        return True

    def setParent(self, parent):
        if parent is not None:
            self._parent = parent
            self._parent.append_child(self)
        else:
            self._parent = None

    def append_child(self, child):
        self._children.append(child)

    def child_at_row(self, row):
        return self._children[row]

    def row_of_child(self, child):
        for idx, item in enumerate(self._children):
            if child == item:
                return idx
        return -1

    def remove_child(self, row):
        value = self._children[row]
        self._children.remove(value)
        return True

    def __len__(self):
        return len(self._children)


class NodeData(Node):
    def __init__(
            self, node_name=None, node_type=None, icon=None, icon_cate=None, category=None, node_depth=None,
            version=None, hda_id=None, node_descript=None, created_time=None, modified_time=None,
            hda_org_name=None, node_path=None, parent=None):
        super(NodeData, self).__init__(node_name=node_name, node_depth=node_depth, parent=parent)
        self.__node_type = node_type
        self.__node_descript = node_descript
        self.__node_path = node_path
        self.__icon = icon
        self.__icon_cate = icon_cate
        self.__category = category
        self.__version = version
        self.__hda_id = hda_id
        self.__created_time = created_time
        self.__modified_time = modified_time
        self.__hda_org_name = hda_org_name

    def node_type(self):
        return self.__node_type

    def node_descript(self):
        return self.__node_descript

    def node_path(self):
        return self.__node_path

    def icon(self):
        return self.__icon if self.__icon is not None else None

    def icon_cate(self):
        return self.__icon_cate if self.__icon_cate is not None else None

    def category(self):
        return self.__category

    def version(self):
        return self.__version

    def hda_id(self):
        return self.__hda_id

    def created_time(self):
        return self.__created_time

    def modified_time(self):
        return self.__modified_time

    def hda_org_name(self):
        return self.__hda_org_name


class InsideModel(QtCore.QAbstractItemModel):
    hda_id_role = QtCore.Qt.UserRole
    hda_org_name_role = QtCore.Qt.UserRole + 1
    node_path_role = QtCore.Qt.UserRole + 2
    name_role = QtCore.Qt.UserRole + 3
    depth_role = QtCore.Qt.UserRole + 4
    node_type_role = QtCore.Qt.UserRole + 5
    version_role = QtCore.Qt.UserRole + 6

    def __init__(self, data=None, pixmap_cate_data=None, pixmap_ihda_data=None, inst_ihda_icon=None,
                 font_size=None, font_style=None, icon_size=None, padding=None, parent=None):
        super(InsideModel, self).__init__(parent)
        self.__data = self.__default_data
        self.__update_data(data=data)
        self.__pixmap_cate_data = pixmap_cate_data
        self.__pixmap_ihda_data = pixmap_ihda_data
        self.__inst_ihda_icon = inst_ihda_icon
        self.__font_size = font_size
        self.__font_style = font_style
        self.__icon_size = icon_size
        self.__padding = padding
        self.__root = None
        self.__generic_pixmap = QtGui.QPixmap(':/main/icons/generic.png')
        self.__headers = ('Name', 'Type', 'Category', 'Version', 'Descript', 'Created', 'Modified')
        self.__init_set_data()

    def __init_set_data(self):
        self.__root = NodeData(node_name=public.Type.root, node_depth=0, parent=None)
        root_pixmap = self.__pixmap_cate_data.get(public.Type.root)

        if self.__data is not None:
            for root_key, root_val in sorted(self.__data.iteritems(), key=itemgetter(0)):
                parent_node = NodeData(
                    node_name=root_key, node_type=public.Type.root, node_depth=0,
                    icon=root_pixmap, parent=self.__root)
                self.set_treemodel_data(data=root_val, root_type=root_key, depth=1, parent=parent_node)

    #               0           1       2           3           4       5       6          7            8
    # LIST DATA: [inside_id, hda_id, node_name, node_type, node_cate, ctime, mtime, hip_dirpath, hip_filename,
    #          9            10
    #    hda_dirpath, hda_filename
    # ]
    def set_treemodel_data(self, data=None, root_type=None, depth=1, parent=None):
        if isinstance(data, dict):
            for key, val in data.iteritems():
                node_name = key.name()
                node_path = key.path()
                node_cate = houdini_api.HoudiniAPI.node_category_type_name(key)
                hda_info = houdini_api.HoudiniAPI.get_hda_info_by_selection_node(node=key)
                node_descript = houdini_api.HoudiniAPI.node_definition_description(key)
                created_time, modified_time = houdini_api.HoudiniAPI.get_node_datetime(key)
                created_time = created_time.strftime(public.Value.datetime_fmt_str)
                modified_time = modified_time.strftime(public.Value.datetime_fmt_str)
                if hda_info is not None:
                    hda_id = hda_info.get(public.Key.Comment.ihda_id)
                    hda_ver = hda_info.get(public.Key.Comment.ihda_version)
                    hda_org_name = hda_info.get(public.Key.Comment.ihda_name)
                    node_name = '{0} (v{1})'.format(node_name, hda_ver)
                    node_type = public.Type.ihda
                    icon = self.__pixmap_ihda_data.get(hda_id)
                    if icon is None:
                        icon = self.__inst_ihda_icon.get_houdini_icon(
                            icon_lst=houdini_api.HoudiniAPI.node_icon_path_lst(key))
                    # pixmap 공유 데이터 변수에 존재하지 않는다면 직접 가공해서 넣어준다.
                    icon_cate = self.__pixmap_cate_data.get(node_cate)
                    if icon_cate is None:
                        icon_cate = self.__inst_ihda_icon.get_category_icon(category=node_cate)
                else:
                    hda_id = None
                    hda_ver = None
                    hda_org_name = None
                    if node_cate == public.Type.manager:
                        node_type = 'manager'
                        icon_cate = self.__generic_pixmap
                    else:
                        node_type = houdini_api.HoudiniAPI.node_type_name(key)
                        # pixmap 공유 데이터 변수에 존재하지 않는다면 직접 가공해서 넣어준다.
                        icon_cate = self.__pixmap_cate_data.get(node_cate)
                        if icon_cate is None:
                            icon_cate = self.__inst_ihda_icon.get_category_icon(category=node_cate)
                    icon_lst = houdini_api.HoudiniAPI.node_icon_path_lst(key)
                    icon = self.__pixmap_cate_data.get(icon_lst[1])
                    if icon is None:
                        icon = self.__inst_ihda_icon.get_houdini_icon(icon_lst=icon_lst)
                node = NodeData(node_name=node_name, node_type=node_type, icon=icon, icon_cate=icon_cate,
                                node_depth=depth, category=node_cate, node_descript=node_descript,
                                version=hda_ver, hda_id=hda_id, node_path=node_path,
                                created_time=created_time, modified_time=modified_time,
                                hda_org_name=hda_org_name, parent=parent)
                self.set_treemodel_data(data=val, root_type=root_type, depth=depth+1, parent=node)
        elif isinstance(data, list):
            if not len(data):
                return
            for val in sorted(data, key=itemgetter(2)):
                node = NodeData(node_name=val, node_type=public.Type.ihda, category='', parent=parent)
        else:
            pass

    def reload_inside_model(self):
        self.beginResetModel()
        self.__init_set_data()
        self.endResetModel()

    @property
    def inside_data(self):
        return self.__data

    @inside_data.setter
    def inside_data(self, val):
        self.__update_data(val)

    @property
    def __default_data(self):
        return {public.Type.root: {}}

    def __update_data(self, data=None):
        assert isinstance(data, dict)
        if (data is None) or (not len(data)):
            return
        self.__data.get(public.Type.root).update(data)

    def insert_inside_data(self, data=None):
        self.__insert_item_to_inside_data(data=self.__data, insert_data=data)

    def __insert_item_to_inside_data(self, data=None, insert_data=None):
        if isinstance(insert_data, dict):
            for key, val in insert_data.iteritems():
                get_data = data.get(key)
                if get_data is None:
                    data.update(insert_data)
                else:
                    if isinstance(get_data, list):
                        if len(get_data):
                            val = val[0]
                            filtering_data = filter(lambda x: (x[1] == val[1]) and (x[5] == val[5]), get_data)
                            if len(filtering_data):
                                # 만약 같은 version이 이미 존재한다면
                                # filtering data unpack
                                filtering_data = filtering_data[0]
                                filtering_data[2] = val[2]
                                filtering_data[7] = val[7]
                                # index 12~18
                                filtering_data[12:18+1] = val[12:18+1]
                            else:
                                # node 이름으로 정렬하여 삽입
                                node_name_keys = map(lambda x: x[2], get_data)
                                node_name = val[2]
                                insert_idx = bisect_right(node_name_keys, node_name)
                                get_data.insert(insert_idx, val)
                        else:
                            get_data.append(val[0])
                    else:
                        self.__insert_item_to_inside_data(data=get_data, insert_data=val)

    def __one_dimension_keys_array_to_data(self, key_lst=None, add_item=None, depth=0):
        if isinstance(key_lst, list):
            try:
                key = key_lst[depth]
                if isinstance(key, dict):
                    return key
                val = [self.__one_dimension_keys_array_to_data(key_lst=key_lst, add_item=add_item, depth=depth+1)]
                if val[0] is None:
                    if add_item is not None:
                        if isinstance(add_item, list):
                            val = [add_item]
                        else:
                            val = [[add_item]]
                    else:
                        val = [None]
                return dict(izip([key], val))
            except IndexError as err:
                pass

    def make_node_tree(self, node_data=None):
        self.beginResetModel()
        self.__data = self.__default_data
        self.inside_data = node_data
        self.__init_set_data()
        self.endResetModel()

    # build context 에서 선택한 아이템을 삭제할 때 호출하는 함수.
    # bhild context에서 제공하는 index로 삭제하려는 무한루프에 빠지면서 오류난다.
    # 그래서 선택한 노드를 재귀적으로 돌려 찾은 index로 삭제하는 방식으로 돌아간다.
    def remove_selected_inside_data(self, index=None):
        plst = self.__get_all_inside_parent_by_index(index)
        remove_key_data = self.__one_dimension_keys_array_to_data(key_lst=plst)
        get_data = self.__get_inside_data_from_key_data(data=self.__data, key_data=remove_key_data)
        inside_id_list = self.__find_inside_id_from_selected_inside_data(data=get_data)
        # 데이터 삭제
        self.__remove_item_from_inside_data(data=self.__data, remove_key_data=remove_key_data)
        remove_find_item = self.__find_selected_inside_data(
            index=self.index(0, 0, QtCore.QModelIndex()), key_data=remove_key_data.get(public.Type.root),
            find_item=(index.data(QtCore.Qt.DisplayRole),))
        for rm_item in sorted(remove_find_item, key=itemgetter(0), reverse=True):
            item_row, pindex = rm_item
            self.removeRow(item_row, pindex)
        return inside_id_list

    # 유효한 데이터가 남아 있지 않은 껍데기 뿐인 inside 데이터/모델 삭제하는 함수
    def remove_invalid_hull_inside_item_model(self):
        # 데이터를 삭제하고 빈 껍데기만 남은 데이터가 있다면 삭제하는 함수
        invalid_data_list = self.__find_invalid_hull_inside_item_model(index=self.index(0, 0, QtCore.QModelIndex()))
        if len(invalid_data_list):
            for invalid_data in sorted(invalid_data_list, key=itemgetter(0), reverse=True):
                item_row, pindex, key_data = invalid_data
                self.removeRow(item_row, pindex)
                remove_key_data = self.__one_dimension_keys_array_to_data(key_lst=key_data)
                self.__remove_item_from_inside_data(data=self.__data, remove_key_data=remove_key_data)

    # 인자로 들어 온 key_data로 inside data가져오는 함수
    def __get_inside_data_from_key_data(self, data=None, key_data=None):
        if key_data is None:
            return data
        if isinstance(key_data, dict):
            for key, val in key_data.iteritems():
                if val is None:
                    if isinstance(data, list):
                        return filter(lambda x: x[2] == key, data)
                get_data = data.get(key)
                return self.__get_inside_data_from_key_data(data=get_data, key_data=val)

    # 선택한 부모에 존재하는 모든 inside data의 id를 찾아 반환하는 함수
    # 이렇게 찾은 id를 DB에서 제거하기 위함.
    def __find_inside_id_from_selected_inside_data(self, data=None):
        inside_id_lst = list()
        if isinstance(data, list):
            return map(lambda x: x[0], data)
        if isinstance(data, dict):
            for key, val in data.iteritems():
                if isinstance(val, dict):
                    inside_id_lst += self.__find_inside_id_from_selected_inside_data(data=val)
                else:
                    inside_id_lst += map(lambda x: x[0], val)
        return inside_id_lst

    # hda_id를 가진 노드의 [[이름/hda_id/노드경로],]를 반환하는 함수
    def get_ihda_node_list(self):
        root_index = self.index(0, 0, QtCore.QModelIndex())
        tmp_id_lst = list()
        return self.__find_inside_ihda_node(index=root_index, tmp_id_lst=tmp_id_lst)

    # tmp_id_lst는 데이터가 중복 저장되는 것을 방지하는 위한 임시 변수이다.
    def __find_inside_ihda_node(self, index=None, tmp_id_lst=None):
        find_lst = list()
        for row in range(0, self.rowCount(index)):
            child_index = self.index(row, 0, index)
            hda_id = child_index.data(InsideModel.hda_id_role)
            if hda_id is not None:
                if hda_id not in tmp_id_lst:
                    hda_org_name = child_index.data(InsideModel.hda_org_name_role)
                    node_path = child_index.data(InsideModel.node_path_role)
                    find_lst.append([hda_org_name, hda_id, node_path])
                    tmp_id_lst.append(hda_id)
            find_lst += self.__find_inside_ihda_node(index=child_index, tmp_id_lst=tmp_id_lst)
        return find_lst

    # key_date를 기준으로 아이템을 찾아들어가서 find_item을 찾고 리스트 반환
    def __find_selected_inside_data(self, index=None, key_data=None, find_item=None):
        find_lst = list()
        for row in range(0, self.rowCount(index)):
            child_index = self.index(row, 0, index)
            key = child_index.data(QtCore.Qt.DisplayRole)
            get_data = key_data.get(key)
            if get_data is None:
                if key in find_item:
                    find_lst.append([child_index.row(), index])
            else:
                find_lst += self.__find_selected_inside_data(
                    index=child_index, key_data=get_data, find_item=find_item)
        return find_lst

    # 유효하지 않는 데이터를 반환하는 함수. 껍데기만 존재하는 데이터
    # 이 함수로 반환된 데이터를 삭제한다. 선택하여 삭제하는 함수를 쓰면, 유효한 데이터가 하나도 존재 하지 않을 때
    # 그 껍데기를 삭제하는 용도이다.
    def __find_invalid_hull_inside_item_model(self, index=None):
        find_invalid_lst = list()
        for row in range(0, self.rowCount(index)):
            child_index = self.index(row, 0, index)
            is_invalid_data = self.__is_exist_invalid_inside_data(index=child_index)
            if is_invalid_data:
                pkey_list = self.__get_all_inside_parent_by_index(child_index)
                find_invalid_lst.append([row, index, pkey_list])
                continue
            find_invalid_lst += self.__find_invalid_hull_inside_item_model(index=child_index)
        return find_invalid_lst

    # 유효하지 않는 데이터가 존재하는지 확인하는 함수. 존재하지 않는다면 껍데기만 있는 데이터라 그 껍데기를 지우도록 확인한다.
    # 즉, 유효한 데이터가 존재하지 않는 최상위 부모를 찾는다.
    def __is_exist_invalid_inside_data(self, index=None):
        is_found = True
        if self.rowCount(index) == 0:
            return index.data(InsideModel.inside_id_role) is None
        else:
            for row in range(0, self.rowCount(index)):
                child_index = self.index(row, 0, index)
                is_found &= self.__is_exist_invalid_inside_data(index=child_index)
        return is_found

    def __remove_item_from_inside_data(self, data=None, remove_key_data=None):
        if isinstance(data, dict) and isinstance(remove_key_data, dict):
            remove_data_key = remove_key_data.keys()[0]
            remove_data_val = remove_key_data.get(remove_data_key)
            if remove_data_val is not None:
                self.__remove_item_from_inside_data(
                    data=data.get(remove_data_key), remove_key_data=remove_data_val)
            else:
                try:
                    del data[remove_data_key]
                except KeyError as err:
                    pass
        else:
            if isinstance(data, list):
                if isinstance(remove_key_data, dict):
                    rkey = remove_key_data.keys()[0]
                # inside data 이름만 가져옴
                inside_name_lst = map(lambda x: x[2], data)
                # 삭제하려는 key가 이름 리스트에 존재한다면
                if rkey in inside_name_lst:
                    rindex = inside_name_lst.index(rkey)
                    del data[rindex]

    # 인자로 들어온 index의 부모들 이름을 구하는 함수. inside data를 현재는 이름을 가져오지만 차후에는 inside_id로
    # 변환해 이것으로 지워야 정확함. 현재 노드 이름과 버전이 공존하여 이것을 기반으로 삭제한다. 이름과 버전은 unique하기 때문.
    # ex) ['root', 'c:/users/scii', aaa.hip', '/obj/cam', 'bakeoedtest']
    def __get_all_inside_parent_by_index(self, index):
        plist = list()
        if not index.isValid():
            return list()
        plist.append(index.data(QtCore.Qt.DisplayRole))
        return self.__get_all_inside_parent_by_index(index.parent()) + plist

    # 모델 데이터와 inside 데이터를 제거하는 함수
    def remove_invalid_inside_data(self):
        invalid_data = self.__find_invalid_inside_data()
        if invalid_data is None:
            return
        model_lst, pkey_lst = invalid_data
        # remove model data
        # 같은 부모 밑에 존재하는 데이터는 row가 가장 큰 것부터 삭제해야 한다. 그래야 indexError가 발생하지 않는다.
        # 작은 row부터 삭제를 진행하면 row가 바뀌어 버려서 잘못된 연산이 될 수 있다.
        for child_row, parent_index in sorted(model_lst, key=itemgetter(0), reverse=True):
            self.removeRow(child_row, parent_index)
        # remove inside data
        for pkey in pkey_lst:
            remove_key_data = self.__one_dimension_keys_array_to_data(key_lst=pkey)
            self.__remove_item_from_inside_data(data=self.__data, remove_key_data=remove_key_data)

    # 유효하지 않는 레코드 데이터, 모델 데이터 취합하는 함수의 랩퍼 함수
    def __find_invalid_inside_data(self):
        find_model_lst = list()
        parent_key_lst = list()
        self.__find_invalid_item_from_inside_data(
            index=self.index(0, 0, QtCore.QModelIndex()),
            collect_model_lst=find_model_lst, collect_pkey_lst=parent_key_lst)
        if not len(find_model_lst):
            return None
        return [find_model_lst, parent_key_lst]

    # 유효하지 않는 레코드 데이터를 재귀적으로 찾는 함수
    def __find_invalid_item_from_inside_data(
            self, index=None, collect_model_lst=None, collect_pkey_lst=None):
        for row in range(0, self.rowCount(index)):
            child_index = self.index(row, 0, index)
            is_can_remove = self.__is_can_remove_data(parent=child_index)
            if is_can_remove:
                pkey_list = self.__get_all_inside_parent_by_index(child_index)
                collect_pkey_lst.append(pkey_list)
                # [삭제할 row, 부모 인덱스]
                collect_model_lst.append([row, index])
                continue
            self.__find_invalid_item_from_inside_data(
                child_index, collect_model_lst=collect_model_lst, collect_pkey_lst=collect_pkey_lst)

    # 해당 부모를 지워도 되는지 확인하는 함수. 자식 중 하나라도 유효한 데이터가 있다면 부모를 지울 수 없다.
    def __is_can_remove_data(self, parent=None):
        flag_lst = list()
        if self.rowCount(parent) == 0:
            hda_filepath = parent.data(InsideModel.hda_filepath_role)
            if hda_filepath is not None:
                if hda_filepath.exists():
                    return False
                else:
                    return True
        else:
            for row in range(0, self.rowCount(parent)):
                child = self.index(row, 0, parent)
                hip_hipfile = child.data(InsideModel.hip_filepath_role)
                if hip_hipfile.exists():
                    flag_lst.append(self.__is_can_remove_data(parent=child))
                else:
                    flag_lst.append(True)
        return all(flag_lst)

    # hda_id와 같은 inside data 삭제 함수
    # iHDA 삭제 시, inside 데이터 삭제되도록 DB에서 Constraint 걸어 놓아서 여기서만 삭제하면 된다.
    # 해당 hda_id를 가진 자식의 부모가 자식이 하나라면 가장 끝 부모를 삭제해야하기 때문에 is_find_parent를 True로 주었다.
    def remove_inside_item_by_hda_id(self, hda_id=None):
        find_model_lst = list()
        parent_key_lst = list()
        self.__find_item_from_inside_data(
            index=self.index(0, 0, QtCore.QModelIndex()),
            collect_model_lst=find_model_lst, collect_pkey_lst=parent_key_lst,
            hda_id=hda_id, is_find_parent=True)
        if not len(find_model_lst):
            return None
        for child_row, parent_index in sorted(find_model_lst, key=itemgetter(0), reverse=True):
            self.removeRow(child_row, parent_index)
        for pkey in parent_key_lst:
            remove_key_data = self.__one_dimension_keys_array_to_data(key_lst=pkey)
            self.__remove_item_from_inside_data(data=self.__data, remove_key_data=remove_key_data)

    # inside data 이름 변경 함수 (iHDA 파일 경로도 변경해야 함)
    # iHDA 이름 변경 시, inside 데이터도 함께 변경되어야 한다. DB는 트리거로 자동화 시켜 놓았다.
    # 정확하게 해당 데이터를 찾아가야해서 is_find_parent를 False로 주었다.
    def rename_inside_item(
            self, hda_id=None, new_name=None, hda_dirpath=None, hda_version=None):
        find_model_lst = list()
        parent_key_lst = list()
        self.__find_item_from_inside_data(
            index=self.index(0, 0, QtCore.QModelIndex()),
            collect_model_lst=find_model_lst, collect_pkey_lst=parent_key_lst,
            hda_id=hda_id, is_find_parent=False)
        if not len(find_model_lst):
            return None
        collect_update_key_data = dict()
        for pkey in parent_key_lst:
            # 찾은 정확한 데이터의 바로 위의 부모에서 list 데이터를 for문으로 돌리려고 아래의 명령을 추가했다.
            del pkey[-1]
            update_data = self.__one_dimension_keys_array_to_data(key_lst=pkey)
            self.__collect_inside_data(data=collect_update_key_data, insert_data=update_data)
        self.__rename_inside_data(
            data=self.__data, update_key_data=collect_update_key_data,
            update_data=[hda_id, new_name, hda_dirpath, hda_version])

    # 여러 개의 inside data (중첩 된 딕셔너리&리스트 데이터)를 하나의 데이터로 만드는 함수
    def __collect_inside_data(self, data=None, insert_data=None):
        if isinstance(insert_data, dict):
            if not len(data):
                data.update(insert_data)
                return
            for key, val in insert_data.iteritems():
                get_data = data.get(key)
                if get_data is None:
                    data.update(insert_data)
                else:
                    if isinstance(get_data, list):
                        pass
                    else:
                        self.__collect_inside_data(data=get_data, insert_data=val)

    def __rename_inside_data(self, data=None, update_key_data=None, update_data=None):
        if isinstance(update_key_data, dict):
            for key, val in update_key_data.iteritems():
                get_data = data.get(key)
                if isinstance(get_data, list):
                    hda_id, new_name, hda_dirpath, hda_version = update_data
                    for row in range(len(get_data)):
                        # hda_id가 같은 지
                        if get_data[row][1] == hda_id:
                            hda_ver = get_data[row][5]
                            new_name_with_ver = '{0} (v{1})'.format(new_name, hda_ver)
                            # 새로운 이름으로 변경
                            get_data[row][2] = new_name_with_ver
                            # 오리지날 이름도 새로운 이름으로 변경
                            get_data[row][18] = new_name
                            # hda dirpath 변경
                            get_data[row][10] = hda_dirpath
                            # hda filename 변경
                            # 파일 이름은 버전이 같은 것만 변경 해야 함.
                            if get_data[row][5] == hda_version:
                                hda_filename = houdini_api.HoudiniAPI.make_hda_filename(
                                    name=new_name, version=hda_version, is_encrypt_ihda=True)
                                get_data[row][11] = hda_filename
                else:
                    self.__rename_inside_data(data=get_data, update_key_data=val, update_data=update_data)

    def __find_item_from_inside_data(
            self, index=None, collect_model_lst=None, collect_pkey_lst=None,
            hda_id=None, is_find_parent=False):
        for row in range(0, self.rowCount(index)):
            child_index = self.index(row, 0, index)
            is_found_data = self.__is_exist_hda_id(
                hda_id=hda_id, parent=child_index, is_find_parent=is_find_parent)
            if is_found_data:
                pkey_list = self.__get_all_inside_parent_by_index(child_index)
                collect_pkey_lst.append(pkey_list)
                # [row, 부모 인덱스]
                collect_model_lst.append([row, index])
                continue
            self.__find_item_from_inside_data(
                child_index, collect_model_lst=collect_model_lst, collect_pkey_lst=collect_pkey_lst,
                hda_id=hda_id, is_find_parent=is_find_parent)

    # 인자로 들어온 hda_id를 가진 자식들이 존재하는지
    def __is_exist_hda_id(self, hda_id=None, is_find_parent=False, parent=None):
        """
        인자로 들어온 hda_id를 가진 부모/데이터가 존재하는 지 확인하는 함수
        :param hda_id: 검색 대상의 iHDA ID
        :param is_find_parent: 정확한 데이터를 찾을 것인지 혹은 찾는 데이터를 하나 밖에 가지고 있지 않는 부모를 찾을 것인지
                True -> 찾은 hda_id의 부모를 반환한다. 그 부모는 찾는 데이터를 단 하나만 가지고 있다.
                    불필요하게 껍데기만 존재하는 데이터를 방지하고자 할 때 True로 주면 된다.
                False -> hda_id를 가진 데이터를 정확하게 찾을 때 False를 주면 된다.
        :param parent: model index
        :return: 찾은 데이터 리스트를 반환
        """
        is_found = is_find_parent
        if self.rowCount(parent) == 0:
            return parent.data(InsideModel.hda_id_role) == hda_id
        else:
            for row in range(0, self.rowCount(parent)):
                child_index = self.index(row, 0, parent)
                if child_index.data(InsideModel.hda_id_role) == hda_id:
                    is_found &= True
                is_found &= self.__is_exist_hda_id(
                    hda_id=hda_id, is_find_parent=is_find_parent, parent=child_index)
        return is_found

    def add_item(self, data=None):
        assert isinstance(data, dict)
        self.__update_data(data=data)

    def remove_item(self, category=None):
        del self.__data.get(public.Type.root)[category]

    def set_icon_size(self, val):
        self.beginResetModel()
        self.__icon_size = val
        self.endResetModel()

    def set_font(self, style=None, size=None):
        self.beginResetModel()
        self.__font_style = style.decode('utf8')
        self.__font_size = size
        self.endResetModel()

    def set_padding(self, val):
        self.beginResetModel()
        self.__padding = val
        self.endResetModel()

    def clear_item(self):
        self.beginResetModel()
        self.__data = self.__default_data
        self.__init_set_data()
        self.endResetModel()

    def flags(self, index=QtCore.QModelIndex()):
        flags = super(InsideModel, self).flags(index)
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        # if index.isValid():
        #     flags |= QtCore.Qt.ItemIsSelectable
        #     flags |= QtCore.Qt.ItemIsEnabled
        #     flags |= QtCore.Qt.ItemIsDragEnabled
        #     flags |= QtCore.Qt.ItemIsDropEnabled
        # else:
        #     flags |= QtCore.Qt.ItemIsDropEnabled
        # return flags

    @property
    def headers_count(self):
        return len(self.__headers)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.__headers)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.__headers[section]
        elif role == QtCore.Qt.DecorationRole:
            return None
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            # font.setFamily(self.__font_style)
            font.setPointSize(public.UISetting.view_font_size)
            return font
        elif role == QtCore.Qt.TextAlignmentRole:
            return int(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        return None

    def node_from_index(self, index):
        return index.internalPointer() if index.isValid() else self.__root

    def insertRow(self, row, parent=QtCore.QModelIndex()):
        return self.insertRows(row, 1, parent)

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        node = self.node_from_index(parent)
        self.beginInsertRows(parent, row, (row + (count - 1)))
        self.endInsertRows()
        return True

    def delete_node(self, index):
        node = self.node_from_index(index)
        parent = self.parent(index)
        position = node.row_of_child(parent)
        self.removeRows(position, 1, parent)

    def removeRow(self, row, parent=QtCore.QModelIndex()):
        return self.removeRows(row, 1, parent)

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        node = self.node_from_index(parent)
        node.remove_child(row)
        self.endRemoveRows()
        return True

    def index(self, row, column, parent=QtCore.QModelIndex()):
        node = self.node_from_index(parent)
        return self.createIndex(row, column, node.child_at_row(row))

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = self.node_from_index(index)
        column = index.column()
        if role == QtCore.Qt.TextAlignmentRole:
            if column > 2:
                return int(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            return int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        elif role == QtCore.Qt.DisplayRole:
            disp_lst = (
                node.name(), node.node_type(), node.category(), node.version(), node.node_descript(),
                node.created_time(), node.modified_time()
            )
            return disp_lst[column]
        elif role == QtCore.Qt.ToolTipRole:
            if column == 0:
                return node.name()
            return None
        elif role == QtCore.Qt.DecorationRole:
            if column == 0:
                if node.icon() is None:
                    return None
                if node.node_type() == public.Type.ihda:
                    return node.icon().scaled(
                        QtCore.QSize(self.__icon_size, self.__icon_size), QtCore.Qt.KeepAspectRatio)
                return node.icon().scaled(
                    QtCore.QSize(self.__icon_size * 0.8, self.__icon_size * 0.8), QtCore.Qt.KeepAspectRatio)
            elif column == 2:
                if node.icon_cate() is None:
                    return None
                return node.icon_cate().scaled(
                    QtCore.QSize(self.__icon_size * 0.8, self.__icon_size * 0.8), QtCore.Qt.KeepAspectRatio)
            elif column in [5, 6]:
                if (node.created_time() is None) or (node.modified_time() is None):
                    return None
                else:
                    pixmap = QtGui.QPixmap(':/main/icons/ic_query_builder_white.png')
                return pixmap.scaled(
                    QtCore.QSize(self.__icon_size * 0.7, self.__icon_size * 0.7), QtCore.Qt.KeepAspectRatio)
            return None
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setFamily(self.__font_style)
            font.setPointSize(self.__font_size)
            return font
        elif role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(self.__icon_size, self.__icon_size + self.__padding)
        elif role == QtCore.Qt.BackgroundColorRole:
            return None
        # UserRole
        elif role == InsideModel.hda_id_role:
            return node.hda_id()
        elif role == InsideModel.hda_org_name_role:
            return node.hda_org_name()
        elif role == InsideModel.node_path_role:
            return node.node_path()
        elif role == InsideModel.name_role:
            return node.name()
        elif role == InsideModel.depth_role:
            return node.depth()
        elif role == InsideModel.node_type_role:
            return node.node_type()
        elif role == InsideModel.version_role:
            return node.version()

    # def setData(self, index, value, role=QtCore.Qt.DisplayRole):
    #     if not index.isValid():
    #         return False
    #     node = self.node_from_index(index)
    #     if role == QtCore.Qt.DisplayRole:
    #         node.name = value
    #         self.emit(QtCore.SIGNAL('dataChanged(QModelIndex, QModelIndex)', index, index))
    #         return True
    #     return False

    def rowCount(self, parent=QtCore.QModelIndex()):
        node = self.node_from_index(parent)
        if node is None:
            return 0
        return len(node)

    def parent(self, index=QtCore.QModelIndex()):
        if not index.isValid():
            return QtCore.QModelIndex()
        node = self.node_from_index(index)
        if node is None:
            return QtCore.QModelIndex()
        parent = node.parent()
        if parent is None:
            return QtCore.QModelIndex()
        grand_parent = parent.parent()
        if grand_parent is None:
            return QtCore.QModelIndex()
        row = grand_parent.row_of_child(parent)
        assert row != -1
        return self.createIndex(row, 0, parent)

    def mimeTypes(self):
        return [public.Type.mime_type]

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def mimeData(self, indexes):
        if not len(indexes):
            return False
        mime_data = super(InsideModel, self).mimeData(indexes)
        # 원래 2번째 컬럼만 선택되어지는데 간혹가다가 모든 컬럼이 indexes로 들어올 때가 있어서 명시해주었다.
        if len(indexes) > 1:
            indexes = [indexes[public.Value.drag_column_inside_view]]
        for index in indexes:
            if index.isValid():
                data = str(self.data(index, role=InsideModel.inside_data_role))
                mime_data.setData(public.Type.mime_type, QtCore.QByteArray(data))
        return mime_data

    def dropMimeData(self, mime_data, action, row, column, parent):
        return True
