"""Intelligent builder — adapts a BuildingSpec to the WorldContext.

The LLM/stub emits a baseline spec; this module post-processes it so the
structure fits naturally into the world instead of ignoring the environment:

  * orientation          — face the structure toward the player
  * foundation height     — sink deeper on soft/water-adjacent terrain
  * material palette      — swap to biome-appropriate materials
  * roof style            — flat in deserts, gabled in forests/snow, etc.
  * terrain adaptation    — note when the surface is uneven
  * clearance             — offset the build away from nearby buildings/trees
  * water avoidance       — raise foundation and choose erosion-resistant blocks
  * tree preservation     — bias orientation/offset to keep nearby trees intact

Every decision is appended to a human-readable ``decisions`` list so the Java
side can surface them in chat and the logs explain each adaptation.
"""
from __future__ import annotations

import logging

from models.building_spec import (
    BuildingSpec,
    MaterialPalette,
    RoofStyle,
)
from models.world_context import WorldContext

logger = logging.getLogger("buildermc.intelligent")


# Biome-appropriate fallback palettes — used when the context strongly suggests
# a material swap. Each entry mirrors MaterialPalette's required fields.
_BIOME_PALETTES: dict[str, MaterialPalette] = {
    "desert": MaterialPalette(
        name="desert",
        walls=["minecraft:sandstone"],
        floor=["minecraft:sandstone"],
        roof=["minecraft:sandstone_slab[type=top]"],
        foundation=["minecraft:sandstone"],
        detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
    ),
    "snowy": MaterialPalette(
        name="spruce-snow",
        walls=["minecraft:spruce_planks"],
        floor=["minecraft:spruce_planks"],
        roof=["minecraft:spruce_slab[type=top]"],
        foundation=["minecraft:cobblestone"],
        detail=["minecraft:glass_pane", "minecraft:spruce_door[half=lower]"],
    ),
    "water": MaterialPalette(
        name="watertight",
        walls=["minecraft:oak_planks"],
        floor=["minecraft:oak_planks"],
        roof=["minecraft:oak_slab[type=top]"],
        foundation=["minecraft:stone_bricks"],
        detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
    ),
    "nether": MaterialPalette(
        name="nether",
        walls=["minecraft:nether_bricks"],
        floor=["minecraft:nether_bricks"],
        roof=["minecraft:nether_brick_slab[type=top]"],
        foundation=["minecraft:netherrack"],
        detail=["minecraft:glass_pane", "minecraft:oak_door[half=lower]"],
    ),
}

# Thresholds for environment heuristics.
_BUILDING_DENSITY_THRESHOLD = 8
_TREE_DENSITY_THRESHOLD = 4
_WATER_PROXIMITY_THRESHOLD = 16


class IntelligentBuilder:
    """Post-processes a spec against world context, returning (spec, decisions)."""

    def adapt(self, spec: BuildingSpec, context: WorldContext) -> tuple[BuildingSpec, list[str]]:
        decisions: list[str] = []

        # ── Orientation: align with the player's facing ─────────────────
        facing = context.player_facing.lower()
        if facing in ("north", "south", "east", "west") and facing != spec.orientation:
            spec = spec.model_copy(update={"orientation": facing})
            decisions.append(f"orientation: aligned to player facing '{facing}'")
        else:
            decisions.append(f"orientation: kept {spec.orientation} (player facing {context.player_facing})")

        # ── Foundation height: deeper on water/soft terrain ─────────────
        new_foundation = spec.foundation_height
        if context.is_water_biome() or context.nearby_water:
            new_foundation = max(new_foundation, 2)
            decisions.append(
                f"foundation: raised to {new_foundation} blocks — water nearby requires deeper footing"
            )
        elif context.is_desert_biome():
            new_foundation = max(new_foundation, 2)
            decisions.append(
                f"foundation: sunk {new_foundation} blocks — sand shifts, needs firmer footing"
            )
        elif context.surface_block and "sand" in context.surface_block:
            new_foundation = max(new_foundation, 2)
            decisions.append(
                f"foundation: sunk {new_foundation} blocks — soft surface {context.surface_block!r}"
            )
        else:
            decisions.append(f"foundation: kept {spec.foundation_height} blocks (stable surface)")

        if new_foundation != spec.foundation_height:
            spec = spec.model_copy(update={"foundation_height": new_foundation})

        # ── Palette: swap to biome-appropriate materials ────────────────
        new_palette = self._biome_palette(context)
        if new_palette is not None and new_palette.name != spec.palette.name:
            spec = spec.model_copy(update={"palette": new_palette})
            decisions.append(
                f"palette: swapped to '{new_palette.name}' for biome {context.biome!r}"
            )
        else:
            decisions.append(f"palette: kept '{spec.palette.name}' (biome-appropriate)")

        # ── Roof style: climate-driven ─────────────────────────────────
        wanted_roof = self._climate_roof(context)
        if wanted_roof != spec.roof_style:
            spec = spec.model_copy(update={"roof_style": wanted_roof})
            decisions.append(f"roof: changed to {wanted_roof.value} for {context.biome!r}")
        else:
            decisions.append(f"roof: kept {spec.roof_style.value}")

        # ── Terrain adaptation ────────────────────────────────────────
        if abs(context.terrain_height - 64) > 8:
            decisions.append(
                f"terrain: surface height {context.terrain_height} is far from sea level — "
                "the builder should add a leveling pad before placing blocks"
            )
        else:
            decisions.append(f"terrain: surface height {context.terrain_height} is near sea level — no leveling needed")

        # ── Clearance from existing structures ──────────────────────────
        # Offsets are kept non-negative so block coordinates stay >= 0.
        offset_x, offset_z = 0, 0
        if context.nearby_buildings > _BUILDING_DENSITY_THRESHOLD:
            # Shift south/east to move away from detected plank concentration.
            offset_x += 3
            offset_z += 3
            decisions.append(
                f"clearance: {context.nearby_buildings} plank cells nearby — shifting build "
                f"+{offset_x}X, +{offset_z}Z to avoid existing structures"
            )
        else:
            decisions.append("clearance: no dense existing builds nearby")

        # ── Water avoidance ────────────────────────────────────────────
        if context.nearby_water and not context.is_water_biome():
            decisions.append(
                "water: nearby water detected — foundation uses erosion-resistant stone"
            )
        elif context.is_water_biome():
            decisions.append(
                "water: water biome — using watertight palette and raised foundation"
            )
        else:
            decisions.append("water: no water nearby")

        # ── Tree preservation ──────────────────────────────────────────
        if context.nearby_trees > _TREE_DENSITY_THRESHOLD:
            # Offset slightly to reduce tree removal while keeping the build close.
            offset_x += 2
            offset_z += 2
            decisions.append(
                f"trees: {context.nearby_trees} tree cells nearby — offsetting +2X, +2Z "
                "to preserve as many trees as possible"
            )
        else:
            decisions.append("trees: sparse or no trees nearby — no preservation offset needed")

        if offset_x != 0 or offset_z != 0:
            # Expand dimensions so the placement generator has room for the offset.
            new_width = spec.width + abs(offset_x)
            new_depth = spec.depth + abs(offset_z)
            spec = spec.model_copy(
                update={
                    "offset_x": offset_x,
                    "offset_z": offset_z,
                    "dimensions": [new_width, spec.height, new_depth],
                }
            )
            decisions.append(
                f"offset: shifting build by ({offset_x}, {offset_z}); "
                f"expanded footprint to {spec.width}x{spec.depth}"
            )

        logger.info("adapted spec: %d decisions", len(decisions))
        for d in decisions:
            logger.info("  decision: %s", d)
        return spec, decisions

    @staticmethod
    def _biome_palette(context: WorldContext) -> MaterialPalette | None:
        if context.is_desert_biome():
            return _BIOME_PALETTES["desert"]
        if context.is_snowy_biome():
            return _BIOME_PALETTES["snowy"]
        if context.is_water_biome() or context.nearby_water:
            return _BIOME_PALETTES["water"]
        if "nether" in context.biome or "soul" in context.biome:
            return _BIOME_PALETTES["nether"]
        return None

    @staticmethod
    def _climate_roof(context: WorldContext) -> RoofStyle:
        if context.is_desert_biome():
            return RoofStyle.FLAT
        if context.is_snowy_biome():
            return RoofStyle.GABLE
        if context.is_water_biome() or context.nearby_water:
            return RoofStyle.HIP
        if context.is_forest_biome():
            return RoofStyle.GABLE
        return RoofStyle.GABLE
