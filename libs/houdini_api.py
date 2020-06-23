#!/usr/bin/env python
# encoding=utf-8

# author            : SeongCheol Jeon
# email addr        : saelly55@gmail.com
# create date       : 2020.01.28 02:34
# modify date       :
# description       :

import re
import sys
import math
import shutil
import logging
from imp import reload

import pathlib2

import public
from libs import log_handler

IS_HOUDINI = False
try:
    import hou

    IS_HOUDINI = hou.isUIAvailable()
except ImportError:
    pass

reload(public)
reload(log_handler)

sys.setrecursionlimit(10000)


def _return_value_by_none(val):
    def _decorate(func):
        def _wrapper(*args, **kwargs):
            args_lst = filter(lambda x: not isinstance(x, HoudiniAPI), args)
            if args_lst[0] is None:
                return val
            return func(*args, **kwargs)

        return _wrapper

    return _decorate


# (2020.03.14): hda_dirpath 파라미터의 들어오는 값은 pathlib2.Path 객체이다.
class HoudiniAPI(object):
    # undo import group name
    __undo_name_import_ihda = 'import_individual_hda'

    def __init__(self, hda_version='1.0', node_path='/obj/geo1/box',
                 hda_dirpath='/2TB/library/individualHDA/scii/sop',):
        assert isinstance(hda_dirpath, pathlib2.Path)
        self.__hda_version = hda_version
        self.__node_path = node_path
        self.__node = hou.node(self.__node_path)
        if self.__node is None:
            log_handler.LogHandler.log_msg(method=logging.error, msg='node does not exist')
            return
        self.__hda_dirpath = hda_dirpath
        self.__hda_filename = None
        self.__hda_filepath = None

    @property
    def node(self):
        return self.__node

    @property
    def hda_version(self):
        return self.__hda_version

    @property
    def hda_dirpath(self):
        return self.__hda_dirpath

    @property
    def hda_filename(self):
        return self.__hda_filename

    @hda_filename.setter
    def hda_filename(self, val):
        self.__hda_filename = val

    @property
    def hda_filepath(self):
        return self.__hda_filepath

    @hda_filepath.setter
    def hda_filepath(self, val):
        self.__hda_filepath = val

    @staticmethod
    @_return_value_by_none(list())
    def __node_type_path_list(node):
        node_type_lst = list()
        node_type_lst.append(HoudiniAPI.node_type_name(node))
        return HoudiniAPI.__node_type_path_list(node.parent()) + node_type_lst

    @staticmethod
    @_return_value_by_none(list())
    def __node_category_path_list(node):
        node_category_lst = list()
        node_category_lst.append(HoudiniAPI.node_category_type_name(node))
        return HoudiniAPI.__node_category_path_list(node.parent()) + node_category_lst

    @staticmethod
    @_return_value_by_none(None)
    def node_type_name(node):
        return node.type().name()

    @staticmethod
    @_return_value_by_none(None)
    def __node_type_description(node):
        return node.type().description()

    @staticmethod
    @_return_value_by_none(None)
    def node_category_type_name(node):
        # 원래 대문자로 나오지만, 소문자로 바꿈.
        return node.type().category().typeName().lower()

    @staticmethod
    @_return_value_by_none(None)
    def node_icon_path_lst(node):
        try:
            if public.Name.company_initial in HoudiniAPI.node_definition_description(node).lower():
                return [public.Name.company_icon_dirname, public.Name.company_log_icon_filename]
            icon = node.type().definition().icon().strip()
            if icon == '':
                icon = node.type().icon().strip()
        except AttributeError as err:
            icon = node.type().icon().strip()
        icon_lst = icon.split('_', 1)
        find_idx = icon_lst[1].find('-')
        if find_idx >= 0:
            icon_lst[1] = icon_lst[1][:find_idx]
        return icon_lst

    @staticmethod
    @_return_value_by_none(None)
    def node_definition_description(node):
        node_type = node.type()
        try:
            return node_type.definition().description()
        except AttributeError as err:
            return node_type.description()

    @staticmethod
    @_return_value_by_none(None)
    def __is_network_node(node):
        return node.isNetwork()

    @staticmethod
    @_return_value_by_none(None)
    def __is_sub_network_node(node):
        return node.isSubNetwork()

    @staticmethod
    def __set_node_general_connections(connections=None, target_node=None):
        if connections is None:
            return
        for connect in connections:
            input_idx = connect.inputItemOutputIndex()
            input_node = connect.inputNode()
            cur_idx = connect.inputIndex()
            cur_node = connect.outputNode()
            if target_node is not None:
                cur_node = target_node
            cur_node.setInput(cur_idx, input_node, input_idx)

    @staticmethod
    def __get_node_input_connections_lst(node):
        conn_lst = list()
        for connect in node.inputConnections():
            conn_node = connect.inputNode()
            if conn_node is None:
                continue
            conn_idx = connect.inputItemOutputIndex()
            cur_idx = connect.inputIndex()
            conn_lst.append([cur_idx, conn_node.name(), conn_node.type().name(), conn_idx])
        return conn_lst

    @staticmethod
    def __get_node_output_connections_lst(node):
        conn_lst = list()
        for connect in node.outputConnections():
            conn_node = connect.outputNode()
            if conn_node is None:
                continue
            cur_idx = connect.inputItemOutputIndex()
            conn_idx = connect.inputIndex()
            conn_lst.append([cur_idx, conn_node.name(), conn_node.type().name(), conn_idx])
        return conn_lst

    @staticmethod
    def set_node_input_connections(node=None, connection_lst=None):
        if connection_lst is None:
            return
        if not len(connection_lst):
            return
        child_type_dict = HoudiniAPI.__get_child_type_by_name_dict(node)
        child_node_name_lst = child_type_dict.keys()
        with hou.undos.group(HoudiniAPI.__undo_name_import_ihda):
            for conn_info in connection_lst:
                node_idx, conn_node_name, conn_node_type, conn_node_idx = conn_info
                if conn_node_name in child_node_name_lst:
                    if conn_node_type == child_type_dict.get(conn_node_name):
                        conn_node = hou.node(node.parent().path() + public.Paths.houdini_path_sep + conn_node_name)
                        node.setInput(int(node_idx), conn_node, int(conn_node_idx))

    @staticmethod
    def set_node_output_connections(node=None, connection_lst=None):
        if connection_lst is None:
            return
        if not len(connection_lst):
            return
        child_type_dict = HoudiniAPI.__get_child_type_by_name_dict(node)
        child_node_name_lst = child_type_dict.keys()
        with hou.undos.group(HoudiniAPI.__undo_name_import_ihda):
            for conn_info in connection_lst:
                node_idx, conn_node_name, conn_node_type, conn_node_idx = conn_info
                if conn_node_name in child_node_name_lst:
                    if conn_node_type == child_type_dict.get(conn_node_name):
                        conn_node = hou.node(node.parent().path() + public.Paths.houdini_path_sep + conn_node_name)
                        conn_node.setInput(int(conn_node_idx), node, int(node_idx))

    @staticmethod
    def __get_child_type_by_name_dict(node):
        parent_node = node.parent()
        d = dict()
        for child in parent_node.children():
            d[child.name()] = child.type().name()
        return d

    @staticmethod
    def __get_between_node_length(node1, node2):
        sub = node1.position() - node2.position()
        return math.sqrt(math.pow(sub.x(), 2) + math.pow(sub.y(), 2))

    def get_individual_hda_data(self):
        self.hda_filename = HoudiniAPI.make_hda_filename(
            name=self.node.name(), version=self.hda_version, with_suffix=True)
        self.hda_filepath = self.hda_dirpath / self.hda_filename
        return self.__info_dict_individual_node(node=self.node)

    @staticmethod
    def make_hda_filename(name=None, version=None, with_suffix=True):
        if with_suffix:
            _ext = public.Extensions.ihda_file
            return '{0}_{1}_v{2}{3}'.format(public.Name.hda_prefix_str, name, version, _ext)
        return '{0}_{1}_v{2}'.format(public.Name.hda_prefix_str, name, version)

    @staticmethod
    def make_thumbnail_filename(name=None, version=None):
        return '{0}_{1}_thumb_v{2}{3}'.format(public.Name.hda_prefix_str, name, version, public.Extensions.image)

    @staticmethod
    def make_thumbnail_dirpath(hda_dirpath=None):
        assert isinstance(hda_dirpath, pathlib2.Path)
        return hda_dirpath / public.Name.thumbnail_dirname

    @staticmethod
    def make_preview_filename(name=None, version=None):
        return '{0}_{1}_v{2}.$F4{3}'.format(public.Name.hda_prefix_str, name, version, public.Extensions.image)

    @staticmethod
    def make_preview_dirpath(hda_dirpath=None, version=None):
        assert isinstance(hda_dirpath, pathlib2.Path)
        return hda_dirpath / public.Name.preview_dirname / version

    @staticmethod
    def make_video_filename(name=None, version=None):
        return '{0}_{1}_v{2}{3}'.format(public.Name.hda_prefix_str, name, version, public.Extensions.video)

    @staticmethod
    def make_video_dirpath(hda_dirpath=None):
        assert isinstance(hda_dirpath, pathlib2.Path)
        return hda_dirpath / public.Name.video_dirname

    @staticmethod
    def is_root_network(node=None):
        return bool(HoudiniAPI.node_type_name(node) == public.Type.root)

    @staticmethod
    def __is_shop_network(node=None):
        return bool(HoudiniAPI.node_category_type_name(node) == public.Type.shop)

    @staticmethod
    def __is_vop_network(node=None):
        return bool(HoudiniAPI.node_category_type_name(node) == public.Type.vop)

    @staticmethod
    def is_subnet_nodetype(node=None):
        return bool(HoudiniAPI.node_type_name(node) == public.Type.subnet_node)

    @staticmethod
    def is_valid_node(node=None):
        if HoudiniAPI.__is_shop_network(node=node):
            if HoudiniAPI.__is_sub_network_node(node):
                log_handler.LogHandler.log_msg(
                    method=logging.error, msg='subnet node is not supported in the SHOP network')
                return False
        if HoudiniAPI.__is_vop_network(node=node):
            node_descript = HoudiniAPI.node_definition_description(node)
            node_type = HoudiniAPI.node_type_name(node)
            is_descript = node_descript in public.InvalidNode.node_descript_list
            is_type = node_type in public.InvalidNode.node_type_list
            if is_descript or is_type:
                log_handler.LogHandler.log_msg(
                    method=logging.error,
                    msg='node "{0}" cannot be registered because it is of type "{1}"'.format(
                        node.name(), node_descript))
                return False
        if hasattr(node, 'inputs'):
            if len(node.inputs()) >= 5:
                log_handler.LogHandler.log_msg(
                    method=logging.error, msg='"{0}" nodes have more than five inputs'.format(node.name()))
                return False
        return True

    @staticmethod
    def is_valid_node_name(node=None, verbose=True):
        """
        노드 이름이 유효한 이름인지
        :param node: Houdini Node Instance
        :param verbose: Display Error Message
        :return: Bool
        """
        node_name = node.name()
        node_type = HoudiniAPI.node_type_name(node)
        if node_type.find(':') >= 0:
            node_type = node_type.split(':')[0].strip()
        if node_name == node_type:
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.error, msg='the name "{0}" is the same as the current node type'.format(node_name))
            return False
        wrong_name = '{0}1'.format(node_type)
        if node_name == wrong_name:
            if verbose:
                log_handler.LogHandler.log_msg(
                    method=logging.error, msg='"{0}" is a name that can cause errors in Houdini'.format(node_name))
            return False
        return True

    @staticmethod
    def create_hda_file(node=None, hda_dirpath=None, hda_filename=None, hda_version=None):
        assert isinstance(hda_dirpath, pathlib2.Path)
        hda_filepath = hda_dirpath / hda_filename
        tmp_filepath = public.Paths.tmp_dirpath / hda_filename
        # 같은 경로의 같은 이름으로 저장하지 않도록
        if hda_filepath.exists():
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='iHDA file already exists ({0})'.format(hda_filepath))
            return False
        # temp에 파일이 존재한다면 삭제
        if tmp_filepath.exists():
            tmp_filepath.unlink()
        node_name = node.name()
        with hou.undos.disabler():
            # copy node
            copy_node = hou.copyNodesTo((node,), node.parent())[0]
            node.setName('__org__', unique_name=True)
            copy_node.setName(node_name, unique_name=True)
            try:
                if HoudiniAPI.__is_shop_network(node=node):
                    subnet = copy_node
                else:
                    subnet = copy_node.parent().collapseIntoSubnet((copy_node,))
                subnet.setName('__hull__', unique_name=True)
                if not subnet.canCreateDigitalAsset():
                    node.setName(node_name, unique_name=True)
                    if subnet is not None:
                        subnet.destroy()
                    log_handler.LogHandler.log_msg(
                        method=logging.error, msg='type of node that cannot be created with an iHDA node')
                    return False
                if subnet is None:
                    return False
                hda = subnet.createDigitalAsset(
                    name=node_name, description=node_name.replace('_', ' ').strip().title(),
                    hda_file_name=tmp_filepath.as_posix(), version=hda_version,
                    ignore_external_references=True, create_backup=False)
                if hda is None:
                    if copy_node is not None:
                        copy_node.destroy()
                    if subnet is not None:
                        subnet.destroy()
                    node.setName(node_name, unique_name=True)
                    if tmp_filepath.exists():
                        tmp_filepath.unlink()
                    return False
                is_done = HoudiniAPI.__set_hda_options(hda=hda)
                if not is_done:
                    node.setName(node_name, unique_name=True)
                    if tmp_filepath.exists():
                        tmp_filepath.unlink()
                    return False
                node.setName(node_name, unique_name=True)
                HoudiniAPI.__delete_dir(dirpath=tmp_filepath.parent.joinpath('backup'))
                # pathlib2의 rename함수를 이용할 경우, linux에서 "OSError: [Errno 18] Invalid cross-device link 에러 발생
                # 그래서 shutil의 move함수로 대체하였다.
                # tmp_filepath.rename(hda_filepath)
                shutil.move(tmp_filepath.as_posix(), hda_filepath.as_posix())
                return True
            except hou.Error as err:
                log_handler.LogHandler.log_msg(method=logging.error, msg=err)
                log_handler.LogHandler.log_msg(
                    method=logging.error, msg='failed to register "{0}" node'.format(node_name))
                try:
                    if subnet is not None:
                        subnet.destroy()
                    if hda is not None:
                        hda.destroy()
                except UnboundLocalError as err_bound:
                    node.setName(node_name, unique_name=True)
                    HoudiniAPI.clean_hda_library(hda_base_dirpath=tmp_filepath.parent)
                    HoudiniAPI.delete_hda_file(hda_path=tmp_filepath)
                    return False
                node.setName(node_name, unique_name=True)
                HoudiniAPI.clean_hda_library(hda_base_dirpath=tmp_filepath.parent)
                HoudiniAPI.delete_hda_file(hda_path=tmp_filepath)
                return False

    @staticmethod
    def __set_hda_options(hda=None):
        definition = hda.type().definition()
        if definition is None:
            hda.destroy()
            hou.hda.uninstallFile('Embedded')
            return False
        hda_filepath = definition.libraryFilePath()
        options = definition.options()
        options.setUnlockNewInstances(True)
        options.setSaveSpareParms(True)
        options.setSaveInitialParmsAndContents(True)
        definition.setOptions(options)
        definition.save(hda_filepath, template_node=hda, options=options, create_backup=False)
        definition.updateFromNode(hda)
        hda.destroy()
        hou.hda.uninstallFile(hda_filepath)
        hou.hda.uninstallFile('Embedded')
        return True

    @staticmethod
    def create_thumbnail(output_filepath=None):
        assert isinstance(output_filepath, pathlib2.Path)
        frame = hou.frame()
        return HoudiniAPI.__flipbook(
            filepath=output_filepath, frame_range=(frame, frame), resolution=public.Value.thumbnail_resolution)

    @staticmethod
    def create_preview(
            output_filepath=None, frame_info=(), resolution=(),
            is_beautypass_only=False, is_init_sim=False, is_motionblur=False, is_crop_out_mask=True):
        assert isinstance(output_filepath, pathlib2.Path)
        org_frinfo = HoudiniAPI.frame_info()
        hou.setFps(frame_info[2])
        HoudiniAPI.__set_frame_range_for_scene(sf=frame_info[0], ef=frame_info[1], fps=frame_info[2])
        is_done = HoudiniAPI.__flipbook(
            filepath=output_filepath, frame_range=(frame_info[0], frame_info[1]), resolution=resolution,
            is_beautypass_only=is_beautypass_only, is_init_sim=is_init_sim,
            is_motionblur=is_motionblur, is_crop_out_mask=is_crop_out_mask)
        hou.setFps(org_frinfo[2])
        HoudiniAPI.__set_frame_range_for_scene(sf=org_frinfo[0], ef=org_frinfo[1], fps=org_frinfo[2])
        return is_done

    @staticmethod
    def __flipbook(
            filepath=None, frame_range=(), resolution=(), is_beautypass_only=False, is_init_sim=False,
            is_motionblur=False, is_crop_out_mask=False):
        assert isinstance(filepath, pathlib2.Path)
        assert isinstance(frame_range, tuple) or isinstance(frame_range, list)
        curt_desktop = hou.ui.curDesktop()
        scene_viewer = curt_desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if not scene_viewer:
            log_handler.LogHandler.log_msg(
                method=logging.error, msg='could not find scene viewer pane tab, please create it and try again')
            return False
        viewports_persp = [vp for vp in scene_viewer.viewports() if vp.type() == hou.geometryViewportType.Perspective]
        # perpective 뷰 포트를 찾을 수 없다면
        if not len(viewports_persp):
            # log_handler.LogHandler.log_msg(method=logging.warning, msg='could not find the "Perspective" viewport')
            viewport = scene_viewer.viewports()[-1]
        # perpective 뷰 포트가 존재한다면
        else:
            # perspective 뷰 포트중 하나만 취한다.
            viewport = viewports_persp[-1]
        log_handler.LogHandler.log_msg(
            method=logging.info, msg='currently active viewport is {0}'.format(viewport.name()))
        # viewport의 카메라들
        # print viewport.camera()
        #
        # pane = scene_viewer.pane()
        # 원래의 pane 상태 (확장되었는지)
        # is_max_pane = pane.isMaximized()
        # get the display settings
        # settings = scene_viewer.curViewport().settings()
        # get the GeometryViewportDisplaySet for obejcts
        # dp_set = settings.displaySet(hou.displaySetType.SceneObject)
        # 원래의 display mode 저장
        # original_display_mode = dp_set.shadedMode()
        # display mode를 smooth wire모드로 변경
        # dp_set.setShadedMode(hou.glShadingType.SmoothWire)
        # pane 확장이 안되어있다면 pane 확장
        # if not is_max_pane:
        #     pane.setIsMaximized(True)
        #
        flipbook_options = scene_viewer.flipbookSettings().stash()
        # 뷰티패스를 true로 하면, 핸드, 그리드, 가이드, 뷰포트 배경 이미지 등이 렌더 되지 않는다.
        flipbook_options.outputToMPlay(False)
        flipbook_options.beautyPassOnly(is_beautypass_only)
        # 뷰포트의 모든 것을 렌더한다. 이것을 활성화하면 썸네일 만들 때, 200x200가 되지 않아 주석처리함.
        # flipbook_options.renderAllViewports(not is_beautypass_only)
        flipbook_options.initializeSimulations(is_init_sim)
        flipbook_options.useMotionBlur(is_motionblur)
        flipbook_options.cropOutMaskOverlay(is_crop_out_mask)
        flipbook_options.frameRange(frame_range)
        flipbook_options.frameIncrement(1)
        flipbook_options.antialias(hou.flipbookAntialias.UseViewportSetting)
        flipbook_options.useResolution(True)
        flipbook_options.resolution(resolution)
        flipbook_options.output(filepath.as_posix())
        scene_viewer.flipbook(scene_viewer.curViewport(), flipbook_options)
        # 원래의 display mode로 되돌리기
        # dp_set.setShadedMode(original_display_mode)
        # 원래의 pane 확장 되돌리기
        # pane.setIsMaximized(is_max_pane)
        return True

    @staticmethod
    def __set_frame_range_for_scene(sf=1001, ef=1240, fps=24):
        frange_expr = 'tset `({0}-1)/{1}` `{2}/{3}`'.format(sf, fps, ef, fps)
        hou.hscript(frange_expr)
        hou.playbar.setPlaybackRange(sf, ef)
        hou.setFrame(int(sf))

    @staticmethod
    def frame_info():
        sf = int(hou.hscriptExpression('$RFSTART'))
        ef = int(hou.hscriptExpression('$RFEND'))
        fps = int(hou.hscriptExpression('$FPS'))
        return [sf, ef, fps]

    # 현재 후디니가 상업용 라이센스인지
    @staticmethod
    def is_houdini_commercial_license():
        return HoudiniAPI.commercial_license() == HoudiniAPI.current_houdini_license()

    @staticmethod
    def commercial_license():
        return hou.licenseCategoryType.Commercial.name()

    @staticmethod
    def current_houdini_license():
        if IS_HOUDINI:
            return hou.licenseCategory().name()
        return 'unknown'

    @staticmethod
    def current_houdini_version():
        return hou.applicationVersionString()

    @staticmethod
    def __current_houdini_version_major():
        return hou.applicationVersion()[0]

    @staticmethod
    def is_valid_houdini_major_version(major_version):
        if HoudiniAPI.__current_houdini_version_major() == major_version:
            return True
        return False

    @staticmethod
    def current_hipfile():
        return pathlib2.Path(hou.hipFile.path())

    @staticmethod
    def delete_hda_file(hda_path=None):
        assert isinstance(hda_path, pathlib2.Path)
        if hda_path.exists() and hda_path.is_file():
            hda_path.unlink()

    @staticmethod
    def __delete_dir(dirpath=None):
        assert isinstance(dirpath, pathlib2.Path)
        if dirpath.exists() and dirpath.is_dir():
            shutil.rmtree(dirpath.as_posix())

    def __info_dict_individual_node(self, node=None):
        d = dict()
        # houdini node instance
        d[public.Key.node] = node
        # houdini hda version
        d[public.Key.hda_version] = self.hda_version
        # hda dirpath
        d[public.Key.hda_dirpath] = self.hda_dirpath
        # hda file name
        d[public.Key.hda_filename] = self.hda_filename
        # node type path list
        d[public.Key.node_type_path_list] = HoudiniAPI.__node_type_path_list(node)
        # node category path list
        d[public.Key.node_cate_path_list] = HoudiniAPI.__node_category_path_list(node)
        # node type name
        d[public.Key.node_type_name] = HoudiniAPI.node_type_name(node)
        # node category type name
        d[public.Key.node_cate_name] = HoudiniAPI.node_category_type_name(node)
        # node definition description
        d[public.Key.node_def_desc] = HoudiniAPI.node_definition_description(node)
        # node icon path list
        d[public.Key.node_icon_path_list] = HoudiniAPI.node_icon_path_lst(node)
        # node is network
        d[public.Key.is_network] = HoudiniAPI.__is_network_node(node)
        # node is sub network
        d[public.Key.is_sub_network] = HoudiniAPI.__is_sub_network_node(node)
        # node input connections
        d[public.Key.node_input_connections] = HoudiniAPI.__get_node_input_connections_lst(node)
        # node output connections
        d[public.Key.node_output_connections] = HoudiniAPI.__get_node_output_connections_lst(node)
        return d

    @staticmethod
    def __hide_parms(node=None):
        group = node.parmTemplateGroup()
        for parm in group.entries():
            group.hideFolder(parm.label(), True)
        node.setParmTemplateGroup(group)

    @staticmethod
    def clean_hda_library(hda_base_dirpath=None):
        assert isinstance(hda_base_dirpath, pathlib2.Path)
        for hda_filepath in hou.hda.loadedFiles():
            if re.search(r'{0}'.format(hda_base_dirpath.as_posix()), hda_filepath):
                num = len(hou.hda.definitionsInFile(hda_filepath)[0].nodeType().instances())
                if num == 0:
                    hou.hda.uninstallFile(hda_filepath)
        hou.hda.uninstallFile('Embedded')

    # (2020.04.17): 원래는 ihda directory에 ihda 파일을 다이렉트로 불러왔지만 temp 디렉토리를 한번 거치고 불러오는
    # 것으로 바꿨다.
    # 즉, 안전성 및 암호화를 위하여 temp 디렉토리에 ihda data를 복사하고 그 파일을 Houdini에서 불러온다.
    @staticmethod
    def import_individual_hda_into_houdini(
            node_filepath=None, parent_node=None, position=None, node_name=None, node_type_name=None):
        assert isinstance(node_filepath, pathlib2.Path)
        #
        tmp_filepath = public.Paths.tmp_dirpath / node_filepath.name
        dec_filepath = public.Paths.tmp_dirpath / node_filepath.with_suffix(public.Extensions.ihda_file).name
        if tmp_filepath.exists():
            tmp_filepath.unlink()
        if dec_filepath.exists():
            dec_filepath.unlink()
        shutil.copyfile(node_filepath.as_posix(), tmp_filepath.as_posix())
        tmp_filepath.rename(dec_filepath)
        hou.hda.installFile(dec_filepath.as_posix(), change_oplibraries_file=False, force_use_assets=False)
        definition = hou.hda.definitionsInFile(dec_filepath.as_posix())[0]
        hda_name = definition.nodeTypeName()
        # hda_type = definition.nodeTypeCategory().typeName().lower()
        try:
            with hou.undos.group(HoudiniAPI.__undo_name_import_ihda):
                hda_node = parent_node.createNode(hda_name)
                if HoudiniAPI.__is_shop_network(node=hda_node):
                    node = hda_node.changeNodeType(
                        node_type_name, keep_name=True, keep_parms=True, keep_network_contents=True,
                        force_change_on_node_type_match=False)
                else:
                    if hasattr(hda_node, 'extractAndDelete'):
                        node = hda_node.extractAndDelete()[0]
                    else:
                        node = hda_node
                if node_name != node.name():
                    node.setName(node_name, unique_name=True)
                hou.hda.uninstallFile(dec_filepath.as_posix())
                hou.hda.uninstallFile('Embedded')
                node.setUserData('nodeshape', 'cloud')
                # node.setColor(hou.Color(0.85, 0.4, 0.05))
                node.setColor(hou.Color(0.24, 0.12, 0.85))
                node.setPosition(position)
                if dec_filepath.exists():
                    dec_filepath.unlink()
                return node
        except hou.Error as err:
            for child in parent_node.children():
                if child.type().name() == hda_name:
                    child.destroy()
            hou.hda.uninstallFile(dec_filepath.as_posix())
            hou.hda.uninstallFile('Embedded')
            log_handler.LogHandler.log_msg(method=logging.error, msg=err)
            if dec_filepath.exists():
                dec_filepath.unlink()
            return None

    # (2020.05.24): is_unpack_subnet 추가했다. unpack하지 않은 서브넷은 자식노드들까지 코멘트 들어가지 않도록
    @staticmethod
    def set_node_comment(node=None, contents='', show_comments=False, is_unpack_subnet=False):
        if not len(contents):
            return
        with hou.undos.disabler():
            if hasattr(node, 'setComment') and hasattr(node, 'setGenericFlag'):
                node.setComment(contents)
                node.setGenericFlag(hou.nodeFlag.DisplayComment, show_comments)
            if HoudiniAPI.is_subnet_nodetype(node=node) and is_unpack_subnet:
                for child in node.children():
                    if hasattr(child, 'setComment') and hasattr(child, 'setGenericFlag'):
                        child.setComment(contents)
                        child.setGenericFlag(hou.nodeFlag.DisplayComment, show_comments)

    @staticmethod
    def create_sticky_note(node=None, contents=''):
        if not len(contents):
            return None
        with hou.undos.disabler():
            sticky = node.createStickyNote(public.Name.hda_prefix_str)
            sticky.setText(contents)
            sticky.setTextSize(0.35)
            sticky.setTextColor(hou.Color(0.85, 0.85, 0.85))
            # sticky.resize(sticky.size())
            sticky.setColor(hou.Color(0.1, 0.8, 0.45))
            sticky.setDrawBackground(False)
            return sticky

    @staticmethod
    def items_position(items=()):
        pos = hou.Vector2(0, 0)
        num = 0
        for item in items:
            if isinstance(item, hou.SubnetIndirectInput):
                continue
            pos += item.position()
            num += 1
        pos /= num
        return pos + hou.Vector2(-5, 0)

    @staticmethod
    def create_network_box(node=None, comment='', items=()):
        with hou.undos.disabler():
            if len(items):
                net_box = node.createNetworkBox()
                for item in items:
                    if isinstance(item, hou.SubnetIndirectInput):
                        continue
                    net_box.addItem(item)
            else:
                items = node.allItems()
                net_box = node.createNetworkBox()
                for item in items:
                    if isinstance(item, hou.SubnetIndirectInput):
                        continue
                    net_box.addItem(item)
            net_box.setColor(hou.Color(0.3, 0.3, 0.3))
            net_box.fitAroundContents()
            padding = hou.Vector2(1, 1)
            bbox = hou.BoundingRect(
                net_box.position()[0] - padding[0],
                net_box.position()[1] - padding[1],
                net_box.position()[0] + net_box.size()[0] + padding[0],
                net_box.position()[1] + net_box.size()[1] + padding[1])
            net_box.setBounds(bbox)
            net_box.setComment(comment)
            return net_box

    @staticmethod
    def current_network_editor_type_name(network_editor=None, not_have_null_node_context_lst=None):
        if network_editor is None:
            return None
        if isinstance(network_editor, hou.PythonPanel):
            return None
        try:
            net_pwd = network_editor.pwd()
        except AttributeError:
            return None
        net_cur_node = network_editor.currentNode()
        if net_pwd.path() == net_cur_node.path():
            if net_pwd.path() not in not_have_null_node_context_lst:
                with hou.undos.disabler():
                    cur_node = net_pwd.createNode('null', '__tmp__')
                    net_category = HoudiniAPI.node_category_type_name(cur_node)
                    cur_node.destroy()
            else:
                if net_pwd.path() == '/shop':
                    with hou.undos.disabler():
                        cur_node = net_pwd.createNode('properties', '__tmp__')
                        net_category = HoudiniAPI.node_category_type_name(cur_node)
                        cur_node.destroy()
                else:
                    net_category = HoudiniAPI.node_category_type_name(net_pwd)
        else:
            net_category = HoudiniAPI.node_category_type_name(net_cur_node)
        return net_category

    @staticmethod
    def slot_confirm_primary_network_editor():
        network_editor = HoudiniAPI.find_network_editor()
        network_editor.flashMessage(
            public.Paths.icons_hda_default_filepath.as_posix(), 'this is the main network', 1)

    @staticmethod
    def find_network_editor():
        for pane_tab in hou.ui.currentPaneTabs():
            if hou.paneTabType.NetworkEditor != pane_tab.type():
                continue
            try:
                node = pane_tab.currentNode()
                if node.isSelected():
                    return pane_tab
            except AttributeError:
                pass
        return hou.ui.curDesktop().paneTabOfType(hou.paneTabType.NetworkEditor)

    @staticmethod
    def find_network_editor_by_cursor():
        desk = hou.ui.curDesktop()
        cur_pane_tab = desk.paneTabUnderCursor()
        try:
            if hou.paneTabType.NetworkEditor != cur_pane_tab.type():
                return None
        except AttributeError:
            return None
        return cur_pane_tab

    @staticmethod
    def get_cursor_pos(network_editor=None):
        if network_editor is None:
            return None
        return network_editor.cursorPosition()

    @staticmethod
    def get_selected_nodes():
        nodes = hou.selectedNodes()
        if len(nodes):
            return nodes
        return None

    @staticmethod
    def get_node_comment(node=None):
        if node is None:
            return None
        if not hasattr(node, 'comment'):
            return None
        comment = node.comment()
        if (not len(comment)) or (comment is None):
            return None
        return comment.strip()

    @staticmethod
    def all_clear_selected(node=None):
        node.setSelected(False, clear_all_selected=True)

    @staticmethod
    def __is_exist_ihda_node(parent_node=None):
        is_found = False
        try:
            leaves = parent_node.children()
        except hou.Error:
            if parent_node is None:
                return False
            hda_info = HoudiniAPI.get_hda_info_by_selection_node(node=parent_node)
            if hda_info is not None:
                return True
            return False
        if len(leaves) == 0:
            hda_info = HoudiniAPI.get_hda_info_by_selection_node(node=parent_node)
            if hda_info is not None:
                return True
        else:
            for child_node in leaves:
                hda_info = HoudiniAPI.get_hda_info_by_selection_node(node=child_node)
                if hda_info is not None:
                    return True
                is_found |= HoudiniAPI.__is_exist_ihda_node(parent_node=child_node)
        return is_found

    @staticmethod
    def get_ihda_node_instance_data(parent_node=None):
        node_data = dict()
        for child_node in parent_node.children():
            hda_info = HoudiniAPI.get_hda_info_by_selection_node(node=child_node)
            is_exist = HoudiniAPI.__is_exist_ihda_node(parent_node=child_node)
            if not is_exist and hda_info is None:
                continue
            node_data[child_node] = dict()
            if hasattr(child_node, 'isLockedHDA'):
                if child_node.isLockedHDA():
                    continue
            result = HoudiniAPI.get_ihda_node_instance_data(parent_node=child_node)
            if len(result):
                node_data[child_node].update(result)
        return node_data

    @staticmethod
    def get_ihda_node_instance_nested_list(parent_node=None):
        node_data = list()
        for child_node in parent_node.children():
            hda_info = HoudiniAPI.get_hda_info_by_selection_node(node=child_node)
            is_exist = HoudiniAPI.__is_exist_ihda_node(parent_node=child_node)
            if not is_exist and hda_info is None:
                continue
            node_data.append(child_node)
            if hasattr(child_node, 'isLockedHDA'):
                if child_node.isLockedHDA():
                    continue
            result = HoudiniAPI.get_ihda_node_instance_nested_list(parent_node=child_node)
            if len(result):
                node_data.append(result)
        return node_data

    @staticmethod
    def get_hda_info_by_selection_node(node=None):
        comment = HoudiniAPI.get_node_comment(node=node)
        if comment is None:
            return None
        regex_is_valid = re.compile(r'{0}'.format(public.Key.Comment.ihda_id))
        search_comment = regex_is_valid.search(comment)
        if search_comment is None:
            return None
        hda_info_lst = []
        for info in comment.split('\n'):
            hda_info_lst.append(map(lambda x: x.strip(), info.split(':')))
        hda_info_dat = dict(hda_info_lst)
        hda_info_dat[public.Key.Comment.ihda_id] = int(hda_info_dat.get(public.Key.Comment.ihda_id))
        return hda_info_dat

    @staticmethod
    def go_to_node(node=None):
        if node is None:
            return
        node.setSelected(True, clear_all_selected=True)
        network_editor = HoudiniAPI.find_network_editor()
        network_editor.setIsCurrentTab()
        network_editor.setPwd(node.parent())
        network_editor.homeToSelection()

    @staticmethod
    def get_node_datetime(node=None):
        return node.creationTime(), node.modificationTime()

