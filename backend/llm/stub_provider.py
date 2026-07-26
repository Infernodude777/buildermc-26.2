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

    async def aclose(self) -> None:
        """No resources to release."""
        return None

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
            StructureType.HOUSE: (9, 7, 9),
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
                roof=["minecraft:spruce_stairs[facing=north]"],
                foundation=["minecraft:cobblestone"],
                detail=["minecraft:glass_pane", "minecraft:spruce_door[half=lower]"],
            )
            roof_style = RoofStyle.GABLE
        elif context.is_water_biome() or context.nearby_water:
            palette = MaterialPalette(
                name="watertight",
                walls=["minecraft:oak_planks"],
                floor=["minecraft:oak_planks"],
                roof=["minecraft:oak_stairs[facing=north]"],
                foundation=["minecraft:stone_bricks"],
                detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
            )
            roof_style = RoofStyle.HIP
        else:
            palette = MaterialPalette(
                name="oak-cobble",
                walls=["minecraft:oak_planks"],
                floor=["minecraft:oak_planks"],
                roof=["minecraft:oak_stairs[facing=north]"],
                foundation=["minecraft:cobblestone"],
                detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
            )
            roof_style = RoofStyle.GABLE

        orientation = context.player_facing if context.player_facing in ("north", "south", "east", "west") else "north"
        foundation_height = 2 if context.is_water_biome() or context.nearby_water else 1

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
            features=["door", "windows", "floor", "lighting"],
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
        door_lower = "minecraft:oak_door[half=lower,hinge=left,facing=south]"
        door_upper = "minecraft:oak_door[half=upper,hinge=left,facing=south]"
        if spec.palette.detail and len(spec.palette.detail) > 1:
            door_lower = spec.palette.detail[1]

        fh = max(1, spec.foundation_height)

        # Foundation layers (y=0..fh-1).
        for y in range(fh):
            for x in range(w):
                for z in range(d):
                    placements.append(BlockPlacement(x=x, y=y, z=z, block_state=foundation))

        # Floor layer (y=fh).
        for x in range(w):
            for z in range(d):
                placements.append(BlockPlacement(x=x, y=fh, z=z, block_state=floor))

        # Walls (y=fh+1..h-2) — hollow shell with a door on the front wall.
        door_x = w // 2
        door_z = 0
        for y in range(fh + 1, h - 1):
            for x in range(w):
                for z in (0, d - 1):
                    if not (z == door_z and x == door_x and y in (fh + 1, fh + 2)):
                        placements.append(BlockPlacement(x=x, y=y, z=z, block_state=wall))
            for z in range(d):
                for x in (0, w - 1):
                    placements.append(BlockPlacement(x=x, y=y, z=z, block_state=wall))

        # Actually place the door (lower + upper halves).
        if fh + 2 < h:
            placements.append(BlockPlacement(x=door_x, y=fh + 1, z=door_z, block_state=door_lower))
            placements.append(BlockPlacement(x=door_x, y=fh + 2, z=door_z, block_state=door_upper))

        # Windows on the long walls.
        for y in [v for v in (fh + 2, fh + 3) if v < h - 1]:
            for x in (w // 4, (3 * w) // 4):
                if 0 < x < w - 1:
                    placements.append(BlockPlacement(x=x, y=y, z=0, block_state=glass))
                    placements.append(BlockPlacement(x=x, y=y, z=d - 1, block_state=glass))

        # Roof according to style.
        roof = _build_roof(spec, wall, roof_block)
        placements.extend(roof)

        # Interior lighting — torches on the floor and one central ceiling light.
        torch = "minecraft:wall_torch[facing=south]"
        placements.append(BlockPlacement(x=w // 2, y=fh + 1, z=d // 2, block_state="minecraft:torch"))
        if w > 3 and d > 3:
            placements.append(BlockPlacement(x=1, y=fh + 1, z=1, block_state=torch))
            placements.append(BlockPlacement(x=w - 2, y=fh + 1, z=1, block_state=torch))
            placements.append(BlockPlacement(x=1, y=fh + 1, z=d - 2, block_state=torch))
            placements.append(BlockPlacement(x=w - 2, y=fh + 1, z=d - 2, block_state=torch))

        # Apply orientation rotation around the schematic origin.
        placements = _rotate_to_orientation(placements, w, d, spec.orientation)

        logger.info("generate_placements: %d blocks for %dx%dx%d", len(placements), w, h, d)
        return BlockPlacementList(placements=placements)


def _build_roof(spec: BuildingSpec, wall_block: str, roof_block: str) -> list[BlockPlacement]:
    """Generate roof placements for the supported roof styles."""
    w, h, d = spec.width, spec.height, spec.depth
    placements: list[BlockPlacement] = []
    style = spec.roof_style

    if style == RoofStyle.FLAT:
        for x in range(w):
            for z in range(d):
                placements.append(BlockPlacement(x=x, y=h - 1, z=z, block_state=roof_block))
        return placements

    if style in (RoofStyle.GABLE, RoofStyle.SLOPED):
        # Gable roof running along the X axis (ridge at z = d//2).
        for z in range(d):
            distance = abs(z - (d - 1) // 2)
            y = h - 1 - distance
            if y >= 0:
                for x in range(w):
                    placements.append(BlockPlacement(x=x, y=y, z=z, block_state=roof_block))
                # Fill walls under the gable.
                for fill_y in range(y + 1, h - 1):
                    for x in (0, w - 1):
                        placements.append(BlockPlacement(x=x, y=fill_y, z=z, block_state=wall_block))
        return placements

    if style == RoofStyle.HIP:
        # Hip roof: step in from all four sides.
        max_step = min((d - 1) // 2, (w - 1) // 2, h - 1)
        for step in range(max_step + 1):
            y = h - 1 - step
            for x in range(step, w - step):
                for z in range(step, d - step):
                    placements.append(BlockPlacement(x=x, y=y, z=z, block_state=roof_block))
        return placements

    if style == RoofStyle.DOME:
        # Simple stepped dome approximation.
        cx, cz = (w - 1) / 2.0, (d - 1) / 2.0
        radius = min(w, d) / 2.0
        for x in range(w):
            for z in range(d):
                dist = max(abs(x - cx), abs(z - cz))
                steps = int(dist / radius * (h - 1))
                y = h - 1 - min(steps, h - 1)
                placements.append(BlockPlacement(x=x, y=y, z=z, block_state=roof_block))
        return placements

    # Fallback: flat roof.
    for x in range(w):
        for z in range(d):
            placements.append(BlockPlacement(x=x, y=h - 1, z=z, block_state=roof_block))
    return placements


def _rotate_to_orientation(placements: list[BlockPlacement], w: int, d: int, orientation: str) -> list[BlockPlacement]:
    """Rotate placements so the door/front faces the player orientation."""
    # Front wall is currently at z=0 (south-facing door). Map orientation to
    # the number of 90-degree clockwise rotations needed around the Y axis.
    rotations = {"south": 0, "west": 1, "north": 2, "east": 3}
    n = rotations.get(orientation, 0)

    for _ in range(n):
        new_placements = []
        for p in placements:
            # 90-degree clockwise rotation about the Y axis: (x, z) -> (z, w-1-x)
            # where w is the current width. After rotation the new width/depth swap.
            new_x = p.z
            new_z = w - 1 - p.x
            new_placements.append(BlockPlacement(x=new_x, y=p.y, z=new_z, block_state=p.block_state))
        placements = new_placements
        w, d = d, w
    return placements
