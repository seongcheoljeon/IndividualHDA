"""Shared fixtures without importing test modules."""

from __future__ import annotations

from pathlib import Path

from libs.repository import RegistrationPayload


def payload(root: Path, name: str, version: str = "1.0") -> RegistrationPayload:
    directory = root / "sop" / name
    (directory / "thumbnail").mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.hda").write_bytes(b"hda")
    (directory / "thumbnail" / "t.jpg").write_bytes(b"jpg")
    return RegistrationPayload(
        user="tester",
        node_name=name,
        node_path=f"/obj/{name}",
        version=version,
        hda_dirpath=directory,
        hda_filename=f"{name}.hda",
        type_name="box",
        cate_name="sop",
        def_desc="Box",
        is_network=False,
        is_sub_network=False,
        type_path_lst=("Sop/box",),
        cate_path_lst=("Sop",),
        icon_path_lst=(
            "SOP",
            "box",
        ),
        input_conn=(),
        output_conn=(),
        hou_version="21.0",
        hou_license="commercial",
        operating_system="Linux",
        hip_filename="scene.hip",
        hip_dirpath=root,
        sf=1,
        ef=24,
        fps=24.0,
        thumb_dirpath=directory / "thumbnail",
        thumb_filename="t.jpg",
        registered_at="2026-09-14 12:00:00",
    )
