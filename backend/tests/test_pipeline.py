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
