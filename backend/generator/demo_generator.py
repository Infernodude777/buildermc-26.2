"""Standalone demo generator (no LLM).

Produces a small fixed house as a (BuildingSpec, BlockPlacementList) pair so the
full pipeline (request → schematic → response) can be exercised end-to-end
without invoking the AI stages. This is what Prompt 3 asks for: a demonstration
structure that tests the entire pipeline before the LLM is wired in.
"""
from __future__ import annotations

import logging

from models.building_spec import (
    BlockPlacement,
    BlockPlacementList,
    BuildingSpec,
    Interpretation,
    MaterialPalette,
    RoofStyle,
    StructureType,
)
from models.world_context import WorldContext

logger = logging.getLogger("buildermc.generator.demo")


def generate_demo_structure(context: WorldContext | None = None) -> tuple[BuildingSpec, BlockPlacementList]:
    """Return a deterministic small house spec + placements."""
    context = context or WorldContext()

    w, h, d = 7, 5, 7
    palette = MaterialPalette(
        name="oak-cobble",
        walls=["minecraft:oak_planks"],
        floor=["minecraft:oak_planks"],
        roof=["minecraft:oak_stairs[facing=east]"],
        foundation=["minecraft:cobblestone"],
        detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
    )
    spec = BuildingSpec(
        interpretation=Interpretation(
            type=StructureType.HOUSE,
            style="demo",
            description="A small demo house for pipeline testing.",
        ),
        dimensions=[w, h, d],
        palette=palette,
        roof_style=RoofStyle.GABLE,
        orientation=context.player_facing if context.player_facing in ("north", "south", "east", "west") else "north",
        foundation_height=1,
        features=["door", "windows", "floor"],
    )

    placements: list[BlockPlacement] = []
    wall, floor, roof, foundation = palette.walls[0], palette.floor[0], palette.roof[0], palette.foundation[0]
    glass = palette.detail[0]

    for x in range(w):
        for z in range(d):
            placements.append(BlockPlacement(x=x, y=0, z=z, block_state=foundation))
            placements.append(BlockPlacement(x=x, y=1, z=z, block_state=floor))

    door_x, door_z = w // 2, 0
    for y in range(2, h):
        for x in range(w):
            for z in (0, d - 1):
                if not (x == door_x and z == door_z and y in (2, 3)):
                    placements.append(BlockPlacement(x=x, y=y, z=z, block_state=wall))
        for z in range(d):
            for x in (0, w - 1):
                placements.append(BlockPlacement(x=x, y=y, z=z, block_state=wall))

    for y in [v for v in (3, 4) if v < h - 1]:
        for x in (w // 4, (3 * w) // 4):
            if 0 < x < w - 1:
                placements.append(BlockPlacement(x=x, y=y, z=0, block_state=glass))
                placements.append(BlockPlacement(x=x, y=y, z=d - 1, block_state=glass))

    for x in range(w):
        for z in range(d):
            placements.append(BlockPlacement(x=x, y=h - 1, z=z, block_state=roof))

    logger.info("demo structure: %d blocks for %dx%dx%d", len(placements), w, h, d)
    return spec, BlockPlacementList(placements=placements)
