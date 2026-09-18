"""HDA files and previews: creating, naming, importing and flipbooking.

Only libs.houdini_api and this package import hou.
"""

from __future__ import annotations

import contextlib
import logging
import pathlib
import shutil
import tempfile
from contextlib import suppress
from typing import Any

from libs import keys, log_handler, paths
from libs.houdini import nodes, session

with suppress(ImportError):
    import hou

try:
    import hdefereval
except ImportError:  # not hosted by Houdini
    hdefereval = None


def hda_definitions_in_file(path: pathlib.Path) -> Any:
    return hou.hda.definitionsInFile(str(path))


def hda_expand_to_directory(path: pathlib.Path, destination: pathlib.Path) -> None:
    hou.hda.expandToDirectory(str(path), str(destination))


def make_hda_filename(
    name: str | None = None, version: str | None = None, with_suffix: bool = True
) -> str:
    if with_suffix:
        _ext = keys.Extensions.ihda_file
        return f"{keys.Name.hda_prefix_str}_{name}_v{version}{_ext}"
    return f"{keys.Name.hda_prefix_str}_{name}_v{version}"


def make_thumbnail_filename(name: str | None = None, version: str | None = None) -> str:
    return f"{keys.Name.hda_prefix_str}_{name}_thumb_v{version}{keys.Extensions.image}"


def make_thumbnail_dirpath(hda_dirpath: pathlib.Path | None = None) -> pathlib.Path:
    assert isinstance(hda_dirpath, pathlib.Path)
    return hda_dirpath / keys.Name.thumbnail_dirname


def make_preview_filename(name: str | None = None, version: str | None = None) -> str:
    return f"{keys.Name.hda_prefix_str}_{name}_v{version}.$F4{keys.Extensions.image}"


def make_preview_dirpath(
    hda_dirpath: pathlib.Path | None = None, version: str | None = None
) -> pathlib.Path:
    if version is None:
        raise ValueError("A version is required")
    assert isinstance(hda_dirpath, pathlib.Path)
    return hda_dirpath / keys.Name.preview_dirname / version


def make_video_filename(name: str | None = None, version: str | None = None) -> str:
    return f"{keys.Name.hda_prefix_str}_{name}_v{version}{keys.Extensions.video}"


def make_video_dirpath(hda_dirpath: pathlib.Path | None = None) -> pathlib.Path:
    assert isinstance(hda_dirpath, pathlib.Path)
    return hda_dirpath / keys.Name.video_dirname


def create_hda_file(
    node: hou.Node | None = None,
    hda_dirpath: pathlib.Path | None = None,
    hda_filename: str | None = None,
    hda_version: str | None = None,
) -> bool:
    if node is None or hda_filename is None:
        return False
    assert isinstance(hda_dirpath, pathlib.Path)
    hda_filepath = hda_dirpath / hda_filename
    if hda_filepath.exists():
        logging.error("iHDA file already exists: %s", hda_filepath)
        return False
    hda_dirpath.mkdir(parents=True, exist_ok=True)
    node_name = node.name()
    # Stage on the destination filesystem; never delete shared temp/backup folders.
    with tempfile.TemporaryDirectory(prefix=".ihda-build-", dir=hda_dirpath) as staging:
        tmp_filepath = pathlib.Path(staging) / hda_filename
        copied = subnet = hda = None
        with hou.undos.disabler():
            try:
                copied = hou.copyNodesTo((node,), node.parent())[0]
                node.setName("__org__", unique_name=True)
                copied.setName(node_name, unique_name=True)
                subnet = (
                    copied
                    if nodes._is_shop_network(node=node)
                    else copied.parent().collapseIntoSubnet((copied,))
                )
                subnet.setName("__hull__", unique_name=True)
                if not subnet.canCreateDigitalAsset():
                    return False
                hda = subnet.createDigitalAsset(
                    name=node_name,
                    description=node_name.replace("_", " ").strip().title(),
                    hda_file_name=tmp_filepath.as_posix(),
                    version=hda_version,
                    ignore_external_references=True,
                    create_backup=False,
                )
                if hda is None or not _set_hda_options(hda=hda):
                    return False
                tmp_filepath.replace(hda_filepath)
                return True
            except (hou.Error, OSError) as error:
                logging.error("Failed to register %s: %s", node_name, error)
                return False
            finally:
                for temporary_node in (hda, subnet, copied):
                    if temporary_node is not None:
                        with contextlib.suppress(hou.ObjectWasDeleted):
                            temporary_node.destroy()
                node.setName(node_name, unique_name=True)
                if tmp_filepath.as_posix() in hou.hda.loadedFiles():
                    hou.hda.uninstallFile(tmp_filepath.as_posix())


def _set_hda_options(hda: hou.Node | None = None) -> bool:
    if hda is None:
        return False
    definition = hda.type().definition()
    if definition is None:
        hda.destroy()
        return False
    hda_filepath = definition.libraryFilePath()
    options = definition.options()
    options.setUnlockNewInstances(True)
    options.setSaveSpareParms(True)
    options.setSaveInitialParmsAndContents(True)
    definition.setOptions(options)
    definition.save(
        hda_filepath, template_node=hda, options=options, create_backup=False
    )
    definition.updateFromNode(hda)
    hda.destroy()
    hou.hda.uninstallFile(hda_filepath)
    return True


def create_thumbnail(output_filepath: pathlib.Path | None = None) -> bool:
    assert isinstance(output_filepath, pathlib.Path)
    frame = hou.frame()
    return _flipbook(
        filepath=output_filepath,
        frame_range=(frame, frame),
        resolution=keys.Value.thumbnail_resolution,
    )


def _flipbook(
    filepath: pathlib.Path | None = None,
    frame_range: tuple[float, float] | None = None,
    resolution: tuple[int, int] | list[int] | None = None,
    is_beautypass_only: bool = False,
    is_init_sim: bool = False,
    is_motionblur: bool = False,
    is_crop_out_mask: bool = False,
) -> bool:
    assert isinstance(filepath, pathlib.Path)
    assert isinstance(frame_range, (tuple, list))
    curt_desktop = hou.ui.curDesktop()
    scene_viewer = curt_desktop.paneTabOfType(hou.paneTabType.SceneViewer)
    if not scene_viewer:
        log_handler.LogHandler.log_msg(
            method=logging.error,
            msg="could not find scene viewer pane tab, please create it and try again",
        )
        return False
    viewports_persp = [
        vp
        for vp in scene_viewer.viewports()
        if vp.type() == hou.geometryViewportType.Perspective
    ]
    # perpective 뷰 포트를 찾을 수 없다면
    if not len(viewports_persp):
        # log_handler.LogHandler.log_msg(method=logging.warning, msg='could not find the "Perspective" viewport')
        viewport = scene_viewer.viewports()[-1]
    # perpective 뷰 포트가 존재한다면
    else:
        # perspective 뷰 포트중 하나만 취한다.
        viewport = viewports_persp[-1]
    log_handler.LogHandler.log_msg(
        method=logging.info,
        msg=f"currently active viewport is {viewport.name()}",
    )
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


def create_preview(
    output_filepath: pathlib.Path | None = None,
    frame_info: tuple[float, float, float] | list[float] | None = None,
    resolution: tuple[int, int] | list[int] | None = None,
    is_beautypass_only: bool = False,
    is_init_sim: bool = False,
    is_motionblur: bool = False,
    is_crop_out_mask: bool = True,
) -> bool:
    if frame_info is None or len(frame_info) != 3 or resolution is None:
        raise ValueError("Frame start, end, FPS and resolution are required")
    assert isinstance(output_filepath, pathlib.Path)
    original_fps = hou.fps()
    original_frame = hou.frame()
    original_global_range = tuple(hou.playbar.frameRange())
    original_playback_range = tuple(hou.playbar.playbackRange())
    try:
        hou.setFps(frame_info[2])
        session._set_frame_range_for_scene(
            sf=frame_info[0], ef=frame_info[1], fps=frame_info[2]
        )
        return _flipbook(
            filepath=output_filepath,
            frame_range=(frame_info[0], frame_info[1]),
            resolution=resolution,
            is_beautypass_only=is_beautypass_only,
            is_init_sim=is_init_sim,
            is_motionblur=is_motionblur,
            is_crop_out_mask=is_crop_out_mask,
        )
    finally:
        hou.setFps(original_fps)
        hou.playbar.setFrameRange(*original_global_range)
        hou.playbar.setPlaybackRange(*original_playback_range)
        hou.setFrame(original_frame)


def _delete_dir(dirpath: pathlib.Path | None = None) -> None:
    assert isinstance(dirpath, pathlib.Path)
    if dirpath.exists() and dirpath.is_dir():
        shutil.rmtree(dirpath.as_posix())


def clean_hda_library(hda_base_dirpath: pathlib.Path | None = None) -> None:
    assert isinstance(hda_base_dirpath, pathlib.Path)
    root = hda_base_dirpath.resolve()
    for hda_filepath in hou.hda.loadedFiles():
        if hda_filepath == "Embedded":
            continue
        if pathlib.Path(hda_filepath).resolve().is_relative_to(root):
            definitions = hou.hda.definitionsInFile(hda_filepath)
            if definitions and not any(
                definition.nodeType().instances() for definition in definitions
            ):
                hou.hda.uninstallFile(hda_filepath)


def import_individual_hda_into_houdini(
    node_filepath: pathlib.Path | None = None,
    parent_node: hou.Node | None = None,
    position: hou.Vector2 | None = None,
    node_name: str | None = None,
    node_type_name: str | None = None,
) -> hou.Node | None:
    if parent_node is None:
        raise ValueError("A parent node is required")
    assert isinstance(node_filepath, pathlib.Path)
    with tempfile.TemporaryDirectory(
        prefix="ihda-import-", dir=paths.Paths.tmp_dirpath
    ) as staging:
        staged = pathlib.Path(staging) / node_filepath.name
        shutil.copyfile(node_filepath, staged)
        hda_node = node = None
        try:
            hou.hda.installFile(
                str(staged), change_oplibraries_file=False, force_use_assets=False
            )
            definitions = hou.hda.definitionsInFile(str(staged))
            if not definitions:
                raise ValueError("File contains no HDA definition")
            with hou.undos.group(session.UNDO_NAME_IMPORT_IHDA):
                hda_node = parent_node.createNode(definitions[0].nodeTypeName())
                if nodes._is_shop_network(node=hda_node):
                    node = hda_node.changeNodeType(
                        node_type_name,
                        keep_name=True,
                        keep_parms=True,
                        keep_network_contents=True,
                        force_change_on_node_type_match=False,
                    )
                else:
                    extracted = hda_node.extractAndDelete()
                    node = next(
                        (
                            item
                            for item in extracted
                            if item.type().name() == node_type_name
                        ),
                        extracted[0],
                    )
                    # Houdini 21 creates output connectors for the wrapper asset.
                    # They must not leak into the artist's parent network.
                    for item in extracted:
                        if item != node and item.type().name() == "output":
                            item.destroy()
                if node_name != node.name():
                    node.setName(node_name, unique_name=True)
                node.setUserData("nodeshape", "cloud")
                node.setColor(hou.Color(0.24, 0.12, 0.85))
                node.setPosition(position)
                return node
        except (hou.Error, OSError, ValueError) as error:
            for created in (node, hda_node):
                if created is not None:
                    with contextlib.suppress(hou.ObjectWasDeleted):
                        created.destroy()
            logging.error("Could not import asset: %s", error)
            return None
        finally:
            if (
                str(staged) in hou.hda.loadedFiles()
                or staged.as_posix() in hou.hda.loadedFiles()
            ):
                hou.hda.uninstallFile(str(staged))


def _is_exist_ihda_node(parent_node: hou.Node | None = None) -> bool:
    if parent_node is None:
        return False
    is_found = False
    try:
        leaves = parent_node.children()
    except hou.Error:
        if parent_node is None:
            return False
        hda_info = nodes.get_hda_info_by_selection_node(node=parent_node)
        return hda_info is not None
    if len(leaves) == 0:
        hda_info = nodes.get_hda_info_by_selection_node(node=parent_node)
        if hda_info is not None:
            return True
    else:
        for child_node in leaves:
            hda_info = nodes.get_hda_info_by_selection_node(node=child_node)
            if hda_info is not None:
                return True
            is_found |= _is_exist_ihda_node(parent_node=child_node)
    return is_found


def get_ihda_node_instance_data(
    parent_node: hou.Node | None = None,
) -> dict[str, Any]:
    if parent_node is None:
        return {}
    node_data: dict[str, Any] = {}
    for child_node in parent_node.children():
        hda_info = nodes.get_hda_info_by_selection_node(node=child_node)
        is_exist = _is_exist_ihda_node(parent_node=child_node)
        if not is_exist and hda_info is None:
            continue
        node_data[child_node] = {}
        if hasattr(child_node, "isLockedHDA"):
            if child_node.isLockedHDA():
                continue
        result = get_ihda_node_instance_data(parent_node=child_node)
        if len(result):
            node_data[child_node].update(result)
    return node_data


def get_ihda_node_instance_nested_list(
    parent_node: hou.Node | None = None,
) -> list[Any]:
    if parent_node is None:
        return []
    node_data = []
    for child_node in parent_node.children():
        hda_info = nodes.get_hda_info_by_selection_node(node=child_node)
        is_exist = _is_exist_ihda_node(parent_node=child_node)
        if not is_exist and hda_info is None:
            continue
        node_data.append(child_node)
        if hasattr(child_node, "isLockedHDA"):
            if child_node.isLockedHDA():
                continue
        result = get_ihda_node_instance_nested_list(parent_node=child_node)
        if len(result):
            node_data.append(result)
    return node_data
