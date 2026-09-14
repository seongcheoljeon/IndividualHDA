from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from libs.ai_features import (
    Description,
    build_describe_prompt,
    describe_asset,
    parse_describe,
    structure_from_asset,
)
from libs.ai_provider import Prompt

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16


def test_prompt_contains_metadata_but_never_paths() -> None:
    asset: dict[str, Any] = {
        "hda_name": "smoke_source",
        "hda_cate": "sop",
        "node_type_name": "pyrosource",
        "node_def_desc": "Pyro Source",
        "hda_dirpath": Path("/secret/library/user"),
        "hip_dirpath": Path("/secret/shots"),
        "node_input_connections": [(0, "a", "b", 0)],
        "children": {"attribwrangle": 2, "scatter": 1},
        "parameters": ["Density", "Temperature"],
    }
    prompt = build_describe_prompt(
        "smoke_source",
        structure_from_asset(asset),
        existing_tags=["fx"],
        vocabulary=["smoke", "물"],
        language="ko",
        image=PNG,
    )
    text = prompt.text
    for expected in (
        "smoke_source",
        "pyrosource",
        "Pyro Source",
        "attribwrangle: 2",
        "Density",
        "fx",
        "물",
        "'ko'",
        "inputs: 1",
    ):
        assert expected in text
    for forbidden in ("secret", "shots", "user"):
        assert forbidden not in text
    assert prompt.images == (PNG,) and "json" in prompt.system
    assert "thumbnail" in text and "Existing note" not in text


@pytest.mark.parametrize(
    "answer",
    [
        '```json\n{"summary": "Makes smoke.", "tags": ["Smoke", "fx source", "smoke"]}\n```',
        'Sure! Here you go:\n{"summary": "Makes smoke.", "tags": "smoke, fx_source #Smoke"}\nHope it helps.',
        '{"summary": " Makes smoke. ", "tags": ["smoke", "fx_source"]}',
    ],
)
def test_parse_describe_is_tolerant(answer: str) -> None:
    assert parse_describe(answer) == Description("Makes smoke.", ("smoke", "fx_source"))


def test_parse_describe_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_describe("I cannot help with that.")
    with pytest.raises(ValueError):
        parse_describe("[1, 2, 3]")


def test_describe_asset_round_trip(tmp_path: Path) -> None:
    thumb = tmp_path / "t.png"
    thumb.write_bytes(PNG)
    seen: list[Prompt] = []

    class Fake:
        def complete(self, prompt: Prompt) -> str:
            seen.append(prompt)
            return '{"summary": "Scatters points.", "tags": ["points", "scatter"]}'

    asset: dict[str, Any] = {
        "hda_name": "scatter_pts",
        "hda_cate": "sop",
        "hda_note": "기존 노트",
        "hda_tags": ["점"],
    }
    result = describe_asset(
        Fake(), asset, thumbnail=thumb, vocabulary=["점", "smoke"], language="ko"
    )
    assert result == Description("Scatters points.", ("points", "scatter"))
    assert (
        seen[0].images == (PNG,)
        and "기존 노트" in seen[0].text
        and "점" in seen[0].text
    )
    (tmp_path / "big.png").write_bytes(PNG + b"0" * (3 * 1024 * 1024))
    describe_asset(Fake(), asset, thumbnail=tmp_path / "big.png")
    assert seen[1].images == ()  # oversized thumbnails are skipped, not sent
