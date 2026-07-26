"""Deterministic stub LLM provider.

No network, no API key. It reads the prompt for keywords and emits valid
Pydantic-validated output, so the entire pipeline (prompt → spec → placements
→ schematic) is testable end-to-end without an LLM. This is what the backend
uses by default.
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

from .base import LanguageModelProvider

logger = logging.getLogger("buildermc.llm.stub")


class StubProvider(LanguageModelProvider):
    """Keyword-driven deterministic provider for offline testing."""

    async def interpret(self, prompt: str, context: WorldContext) -> Interpretation:
        p = prompt.lower()
        if "house" in p or "home" in p or "cottage" in p or "hut" in p:
            stype = StructureType.HOUSE
            style = "cottage" if "cottage" in p else "simple"
        elif "tower" in p:
            stype = StructureType.TOWER
            style = "stone"
        elif "fort" in p or "castle" in p:
            stype = StructureType.FORT
            style = "medieval"
        elif "bridge" in p:
            stype = StructureType.BRIDGE
            style = "wooden"
        elif "garden" in p:
            stype = StructureType.GARDEN
            style = "natural"
        elif "sculpture" in p or "statue" in p:
            stype = StructureType.SCULPTURE
            style = "artistic"
        else:
            stype = StructureType.OTHER
            style = "simple"

        keywords = [w for w in p.split() if len(w) > 3][:10]
        logger.info("interpret: type=%s style=%s keywords=%s", stype.value, style, keywords)
        return Interpretation(
            type=stype,
            style=style,
            description=f"A {style} {stype.value} matching '{prompt}'.",
            keywords=keywords,
        )

    async def generate_spec(
        self, interpretation: Interpretation, context: WorldContext
    ) -> BuildingSpec:
        # Size scales with structure type.
        sizes = {
            StructureType.HOUSE: (9, 6, 9),
            StructureType.TOWER: (5, 12, 5),
            StructureType.FORT: (15, 8, 15),
            StructureType.BRIDGE: (3, 3, 16),
            StructureType.GARDEN: (11, 4, 11),
            StructureType.SCULPTURE: (5, 6, 5),
            StructureType.OTHER: (7, 5, 7),
        }
        w, h, d = sizes.get(interpretation.type, (7, 5, 7))

        # Palette adapts to biome for a natural look.
        if context.is_desert_biome():
            palette = MaterialPalette(
                name="desert",
                walls=["minecraft:sandstone"],
                floor=["minecraft:sandstone"],
                roof=["minecraft:sandstone_slab[type=top]"],
                foundation=["minecraft:sandstone"],
                detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
            )
            roof_style = RoofStyle.FLAT
        elif context.is_snowy_biome():
            palette = MaterialPalette(
                name="spruce-snow",
                walls=["minecraft:spruce_planks"],
                floor=["minecraft:spruce_planks"],
                roof=["minecraft:spruce_slab[type=top]"],
                foundation=["minecraft:cobblestone"],
                detail=["minecraft:glass_pane", "minecraft:spruce_door[half=lower]"],
            )
            roof_style = RoofStyle.GABLE
        elif context.is_water_biome() or context.nearby_water:
            palette = MaterialPalette(
                name="watertight",
                walls=["minecraft:oak_planks"],
                floor=["minecraft:oak_planks"],
                roof=["minecraft:oak_slab[type=top]"],
                foundation=["minecraft:stone_bricks"],
                detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
            )
            roof_style = RoofStyle.GABLE
        else:
            palette = MaterialPalette(
                name="oak-cobble",
                walls=["minecraft:oak_planks"],
                floor=["minecraft:oak_planks"],
                roof=["minecraft:oak_stairs[facing=east]"],
                foundation=["minecraft:cobblestone"],
                detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
            )
            roof_style = RoofStyle.GABLE

        orientation = context.player_facing if context.player_facing in ("north", "south", "east", "west") else "north"
        foundation_height = 1 if context.is_water_biome() or context.nearby_water else 1

        logger.info(
            "generate_spec: dims=%dx%dx%d palette=%s roof=%s orientation=%s",
            w, h, d, palette.name, roof_style.value, orientation,
        )
        return BuildingSpec(
            interpretation=interpretation,
            dimensions=[w, h, d],
            palette=palette,
            roof_style=roof_style,
            orientation=orientation,
            foundation_height=foundation_height,
            features=["door", "windows", "floor"],
        )

    async def generate_placements(
        self, spec: BuildingSpec, context: WorldContext
    ) -> BlockPlacementList:
        placements: list[BlockPlacement] = []
        w, h, d = spec.width, spec.height, spec.depth
        wall = spec.palette.walls[0]
        floor = spec.palette.floor[0]
        roof_block = spec.palette.roof[0]
        foundation = spec.palette.foundation[0]
        glass = spec.palette.detail[0] if spec.palette.detail else "minecraft:glass_pane"

        # Foundation layer (y=0) — solid.
        for x in range(w):
            for z in range(d):
                placements.append(BlockPlacement(x=x, y=0, z=z, block_state=foundation))

        # Floor layer (y=1).
        for x in range(w):
            for z in range(d):
                placements.append(BlockPlacement(x=x, y=1, z=z, block_state=floor))

        # Walls (y=2..h-1) — hollow shell with a door on the facing side.
        door_z = 0  # door on the north wall (z=0)
        door_x = w // 2
        for y in range(2, h):
            for x in range(w):
                for z in (0, d - 1):
                    if not (z == door_z and x == door_x and y in (2, 3)):
                        placements.append(BlockPlacement(x=x, y=y, z=z, block_state=wall))
            for z in range(d):
                for x in (0, w - 1):
                    placements.append(BlockPlacement(x=x, y=y, z=z, block_state=wall))

        # Windows on the long walls — only on rows that exist below the roof.
        for y in [v for v in (3, 4) if v < h - 1]:
            for x in (w // 4, (3 * w) // 4):
                if 0 < x < w - 1:
                    placements.append(BlockPlacement(x=x, y=y, z=0, block_state=glass))
                    placements.append(BlockPlacement(x=x, y=y, z=d - 1, block_state=glass))

        # Roof (y=h-1, the top layer) — flat cap of roof block.
        for x in range(w):
            for z in range(d):
                placements.append(BlockPlacement(x=x, y=h - 1, z=z, block_state=roof_block))

        logger.info("generate_placements: %d blocks for %dx%dx%d", len(placements), w, h, d)
        return BlockPlacementList(placements=placements)
