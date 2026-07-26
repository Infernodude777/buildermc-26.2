"""End-to-end test for the backend build pipeline (stub provider, no LLM).

Runs the full flow: BuildRequest -> BuildService -> SchematicWriter -> file on
disk. Verifies the response status, dimensions, and that the intelligent
builder produced a decision log.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from generator.demo_generator import generate_demo_structure
from intelligent.builder import IntelligentBuilder
from models.building_spec import BlockPlacementList
from models.requests import BuildRequest
from models.world_context import WorldContext
from llm.pipeline import GenerationPipeline
from llm.registry import create_provider_from_config
from llm.stub_provider import StubProvider


def _service(tmp_path: Path):
    # Lazy import so tests that don't write schematics can still collect/run
    # without mcschematic installed.
    from generator.schematic_writer import SchematicWriter
    from services.build_service import BuildService
    return BuildService(
        pipeline=GenerationPipeline(
            provider=StubProvider(), intelligent=IntelligentBuilder()
        ),
        writer=SchematicWriter(output_dir=tmp_path),
        intelligent=IntelligentBuilder(),
    )


def test_stub_pipeline_produces_schematic(tmp_path: Path):
    req = BuildRequest(prompt="a small wooden house", seed=42, world_context=WorldContext())
    resp = asyncio.run(_service(tmp_path).build(req, use_demo=False))

    assert resp.status == "success", resp.error
    assert resp.dimensions and len(resp.dimensions) == 3
    assert all(d > 0 for d in resp.dimensions)
    assert resp.decisions, "intelligent builder should emit at least one decision"
    assert (tmp_path / "latest.schem").exists(), "schematic file should be written"


def test_demo_generator_produces_schematic(tmp_path: Path):
    req = BuildRequest(prompt="house", seed=1, world_context=WorldContext())
    resp = asyncio.run(_service(tmp_path).build(req, use_demo=True))

    assert resp.status == "success", resp.error
    assert resp.dimensions == [7, 5, 7]
    assert (tmp_path / "latest.schem").exists()


def test_intelligent_builder_adapts_to_desert():
    spec, _ = generate_demo_structure(WorldContext(biome="minecraft:desert"))
    adapted, decisions = IntelligentBuilder().adapt(spec, WorldContext(biome="minecraft:desert"))
    assert any("palette" in d for d in decisions)
    assert "desert" in adapted.palette.name


def test_intelligent_builder_offsets_for_clearance_and_trees():
    ctx = WorldContext(biome="minecraft:forest", nearby_buildings=20, nearby_trees=12)
    spec, _ = generate_demo_structure(ctx)
    adapted, decisions = IntelligentBuilder().adapt(spec, ctx)
    assert adapted.offset_x >= 0 and adapted.offset_z >= 0
    assert adapted.offset_x != 0 or adapted.offset_z != 0
    assert adapted.width >= spec.width and adapted.depth >= spec.depth
    assert any("clearance" in d.lower() for d in decisions)
    assert any("tree" in d.lower() for d in decisions)
    assert any("offset" in d.lower() for d in decisions)


def test_invalid_prompt_rejected():
    with pytest.raises(Exception):
        BuildRequest(prompt="   ", seed=0)


def test_placements_bounds_validated():
    spec, placements = generate_demo_structure(WorldContext())
    # Should pass: placements are within the 7x5x7 demo bounds.
    placements.validate_against(spec, max_dimension=64)


def test_placements_out_of_bounds_rejected():
    from models.building_spec import BlockPlacement
    spec, _ = generate_demo_structure(WorldContext())
    bad = BlockPlacementList(placements=[BlockPlacement(x=100, y=0, z=0, block_state="minecraft:stone")])
    with pytest.raises(ValueError):
        bad.validate_against(spec, max_dimension=64)


def test_per_request_provider_override(tmp_path: Path, monkeypatch):
    """When provider_config is supplied, the backend should instantiate, use, and close a per-request provider."""
    from unittest.mock import AsyncMock

    from models.requests import ProviderConfig

    captured_provider = None
    closed = False

    class _TrackingProvider(StubProvider):
        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    def _fake_create_provider_from_config(config: ProviderConfig):
        nonlocal captured_provider
        captured_provider = config
        return _TrackingProvider()

    monkeypatch.setattr("services.build_service.create_provider_from_config", _fake_create_provider_from_config)

    req = BuildRequest(
        prompt="a small wooden house",
        seed=42,
        world_context=WorldContext(),
        provider_config=ProviderConfig(
            provider="openai",
            base_url="http://test-backend/",
            model_id="test-model",
            api_key="test-key",
        ),
    )
    resp = asyncio.run(_service(tmp_path).build(req, use_demo=False))

    assert resp.status == "success", resp.error
    assert captured_provider is not None
    assert captured_provider.base_url == "http://test-backend/"
    assert captured_provider.model_id == "test-model"
    assert captured_provider.api_key == "test-key"
    assert closed, "per-request provider should be closed after the build"


def test_no_provider_config_uses_default_provider(tmp_path: Path):
    """When provider_config is absent, the default provider in the pipeline is used."""
    req = BuildRequest(prompt="a small wooden house", seed=42, world_context=WorldContext())
    # GenerationPipeline was constructed with StubProvider; this should succeed.
    resp = asyncio.run(_service(tmp_path).build(req, use_demo=False))
    assert resp.status == "success", resp.error


def test_per_request_provider_rejects_unknown_provider():
    """An unknown provider type should raise a clear error."""
    from models.requests import ProviderConfig

    config = ProviderConfig(
        provider="unknown-provider",
        base_url="http://test-backend/",
        model_id="test-model",
        api_key="test-key",
    )
    with pytest.raises(ValueError, match="unknown-provider"):
        create_provider_from_config(config)


def test_build_request_with_provider_config_serializes_roundtrip():
    """Provider config should serialize/deserialize cleanly via Pydantic."""
    import json as _json

    from models.requests import ProviderConfig

    req = BuildRequest(
        prompt="a small wooden house",
        seed=42,
        world_context=WorldContext(),
        provider_config=ProviderConfig(
            provider="openai",
            base_url="http://test-backend/",
            model_id="test-model",
            api_key="test-key",
        ),
    )
    dumped = req.model_dump()
    serialized = _json.dumps(dumped)
    restored = BuildRequest.model_validate(_json.loads(serialized))

    assert restored.provider_config is not None
    assert restored.provider_config.provider == "openai"
    assert restored.provider_config.base_url == "http://test-backend/"
    assert restored.provider_config.model_id == "test-model"
    assert restored.provider_config.api_key == "test-key"
