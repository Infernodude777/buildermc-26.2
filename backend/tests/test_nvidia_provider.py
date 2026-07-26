"""Tests for the NVIDIA NIM LLM provider — mocked, no real API calls.

The _FakeNvidiaProvider subclasses NvidiaNimProvider and overrides _chat to
return canned JSON strings, so we can test the parsing, validation, retry, and
malformed-output rejection logic without hitting the network.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from llm.base import MalformedLLMOutputError
from llm.nvidia_nim_provider import NvidiaNimProvider
from models.building_spec import (
    BlockPlacementList,
    BuildingSpec,
    Interpretation,
    StructureType,
)
from models.world_context import WorldContext


# ─── Canned LLM responses ────────────────────────────────────────────────────

_VALID_INTERPRET = {
    "type": "house",
    "style": "cottage",
    "description": "A small cottage house.",
    "keywords": ["house", "cottage", "small", "wooden"],
}

_VALID_SPEC = {
    "interpretation": _VALID_INTERPRET,
    "dimensions": [7, 5, 7],
    "palette": {
        "name": "oak-cobble",
        "walls": ["minecraft:oak_planks"],
        "floor": ["minecraft:oak_planks"],
        "roof": ["minecraft:oak_stairs[facing=east]"],
        "foundation": ["minecraft:cobblestone"],
        "detail": ["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
    },
    "roof_style": "gable",
    "orientation": "north",
    "foundation_height": 1,
    "features": ["door", "windows", "floor"],
}

_VALID_PLACEMENTS = {
    "placements": [
        {"x": 0, "y": 0, "z": 0, "block_state": "minecraft:cobblestone"},
        {"x": 1, "y": 0, "z": 0, "block_state": "minecraft:cobblestone"},
        {"x": 0, "y": 1, "z": 0, "block_state": "minecraft:oak_planks"},
        {"x": 1, "y": 1, "z": 0, "block_state": "minecraft:oak_planks"},
        {"x": 0, "y": 2, "z": 0, "block_state": "minecraft:oak_planks"},
    ]
}


class _FakeNvidiaProvider(NvidiaNimProvider):
    """Overrides _chat to return canned JSON — no network."""

    def __init__(self, responses: dict[str, str | list[str]]) -> None:
        super().__init__(
            api_key="fake-key", base_url="http://fake", model="fake-model",
        )
        self._responses = responses

    async def _chat(
        self, system: str, user: str, max_tokens: int | None = None,
    ) -> str:
        if "architecture interpreter" in system:
            key = "interpret"
        elif "building designer" in system:
            key = "spec"
        elif "block-placement generator" in system:
            key = "placements"
        else:
            key = "unknown"

        val = self._responses.get(key, "{}")
        if isinstance(val, list):
            return val.pop(0) if val else "{}"
        return val


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_nvidia_interpret_valid():
    """Stage 1: valid JSON -> Interpretation model."""
    provider = _FakeNvidiaProvider({"interpret": json.dumps(_VALID_INTERPRET)})
    result = asyncio.run(provider.interpret("a small house", WorldContext()))
    assert isinstance(result, Interpretation)
    assert result.type == StructureType.HOUSE
    assert result.style == "cottage"
    assert "house" in result.keywords


def test_nvidia_spec_valid():
    """Stage 2: valid JSON -> BuildingSpec model."""
    provider = _FakeNvidiaProvider({
        "interpret": json.dumps(_VALID_INTERPRET),
        "spec": json.dumps(_VALID_SPEC),
    })
    interp = Interpretation.model_validate(_VALID_INTERPRET)
    result = asyncio.run(provider.generate_spec(interp, WorldContext()))
    assert isinstance(result, BuildingSpec)
    assert result.width == 7
    assert result.height == 5
    assert result.depth == 7
    assert result.palette.walls == ["minecraft:oak_planks"]


def test_nvidia_placements_valid():
    """Stage 3: valid JSON -> BlockPlacementList, all in-bounds."""
    provider = _FakeNvidiaProvider({
        "placements": json.dumps(_VALID_PLACEMENTS),
    })
    spec = BuildingSpec.model_validate(_VALID_SPEC)
    result = asyncio.run(provider.generate_placements(spec, WorldContext()))
    assert isinstance(result, BlockPlacementList)
    assert len(result.placements) == 5
    result.validate_against(spec, max_dimension=64)


def test_nvidia_placements_rejected_on_invalid_json():
    """Stage 3: invalid LLM JSON is rejected rather than silently falling back."""
    provider = _FakeNvidiaProvider({
        "placements": ["NOT VALID JSON {{{", "ALSO NOT VALID"],
    })
    spec = BuildingSpec.model_validate(_VALID_SPEC)
    with pytest.raises(MalformedLLMOutputError):
        asyncio.run(provider.generate_placements(spec, WorldContext()))


def test_nvidia_malformed_interpret_raises():
    """Stage 1: invalid JSON even after retry -> raises."""
    provider = _FakeNvidiaProvider({
        "interpret": ["NOT VALID JSON {{{", "STILL NOT VALID"],
    })
    with pytest.raises(MalformedLLMOutputError):
        asyncio.run(provider.interpret("a house", WorldContext()))


def test_nvidia_fenced_json_parsed():
    """The _parse_json helper strips markdown code fences."""
    provider = _FakeNvidiaProvider({
        "interpret": "```json\n" + json.dumps(_VALID_INTERPRET) + "\n```",
    })
    result = asyncio.run(provider.interpret("a house", WorldContext()))
    assert result.type == StructureType.HOUSE
