"""World context received from the Fabric mod.

The model is deliberately permissive (``extra="allow"``) so the Java mod can
add new context fields in future versions without breaking an older backend.
The backend reads only the fields it understands and ignores the rest.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorldContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    biome: str = Field(default="minecraft:plains", description="Biome registry id at the player.")
    terrain_height: int = Field(default=64, ge=-64, le=320, description="Surface Y at the player.")
    surface_block: str = Field(default="minecraft:grass_block", description="Top surface block id.")
    nearby_trees: int = Field(default=0, ge=0, description="Tree-log cells nearby.")
    nearby_water: bool = Field(default=False, description="Water found within the build radius.")
    nearby_buildings: int = Field(default=0, ge=0, description="Plank cells nearby (existing builds).")
    nearby_entities: list[str] = Field(default_factory=list, description="Distinct entity type ids nearby.")
    player_position: list[int] = Field(default=[0, 64, 0], min_length=3, max_length=3)
    player_facing: str = Field(default="north", description="Player horizontal facing direction.")
    build_radius: int = Field(default=16, ge=1, le=128, description="Radius scanned around the player.")

    def is_water_biome(self) -> bool:
        return any(tag in self.biome for tag in ("ocean", "river", "beach", "swamp"))

    def is_desert_biome(self) -> bool:
        return "desert" in self.biome

    def is_snowy_biome(self) -> bool:
        return any(tag in self.biome for tag in ("snow", "icy", "frozen"))

    def is_forest_biome(self) -> bool:
        return "forest" in self.biome

    def extras(self) -> dict[str, Any]:
        """Return any fields the model didn't explicitly declare (forward-compat payload)."""
        return {k: v for k, v in self.model_dump().items() if k not in self.model_fields}
