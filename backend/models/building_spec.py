"""Structured LLM output schemas for the 3-stage generation pipeline.

The LLM NEVER emits Python code — only JSON that validates against these
Pydantic models. Each stage has its own model so we can validate and reject
malformed output at each step instead of after a single huge response.

Stage 1 — Interpretation:   what the user asked for (type, style, intent)
Stage 2 — BuildingSpec:      dimensions, palette, features, orientation
Stage 3 — BlockPlacement[]:  concrete block-state strings at coordinates
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─── Stage 1: prompt interpretation ──────────────────────────────────────────


class StructureType(str, Enum):
    HOUSE = "house"
    TOWER = "tower"
    FORT = "fort"
    BRIDGE = "bridge"
    GARDEN = "garden"
    SCULPTURE = "sculpture"
    OTHER = "other"


class Interpretation(BaseModel):
    """Stage 1 — the LLM's reading of the user's prompt."""

    model_config = ConfigDict(extra="forbid")

    type: StructureType
    style: str = Field(default="simple", max_length=64, description="e.g. 'medieval', 'modern', 'cottage'.")
    description: str = Field(default="", max_length=500, description="One-line restatement of intent.")
    keywords: list[str] = Field(default_factory=list, max_length=20)


# ─── Stage 2: building specification ─────────────────────────────────────────


class RoofStyle(str, Enum):
    FLAT = "flat"
    GABLE = "gable"
    HIP = "hip"
    DOME = "dome"
    SLOPED = "sloped"


class MaterialPalette(BaseModel):
    """A named palette of block-state strings used by the structure."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="oak", max_length=64)
    walls: list[str] = Field(default_factory=list, min_length=1, max_length=16,
                             description="Block-state strings for walls.")
    floor: list[str] = Field(default_factory=list, min_length=1, max_length=16)
    roof: list[str] = Field(default_factory=list, min_length=1, max_length=16)
    foundation: list[str] = Field(default_factory=list, min_length=1, max_length=16)
    detail: list[str] = Field(default_factory=list, max_length=16,
                              description="Trim/door/glass/accent blocks.")

    @field_validator("walls", "floor", "roof", "foundation", "detail")
    @classmethod
    def _validate_block_states(cls, v: list[str]) -> list[str]:
        for bs in v:
            if not isinstance(bs, str) or not bs.startswith("minecraft:"):
                raise ValueError(f"Block state must start with 'minecraft:': {bs!r}")
        return v


class BuildingSpec(BaseModel):
    """Stage 2 — the full design before any block is placed."""

    model_config = ConfigDict(extra="forbid")

    interpretation: Interpretation = Field(default_factory=Interpretation)
    dimensions: list[int] = Field(..., min_length=3, max_length=3,
                                  description="[width, height, depth].")
    palette: MaterialPalette
    roof_style: RoofStyle = RoofStyle.GABLE
    orientation: Literal["north", "south", "east", "west"] = "north"
    foundation_height: int = Field(default=1, ge=0, le=8,
                                   description="Blocks sunk below surface for stability.")
    # World-context-driven offsets so the structure avoids trees/buildings.
    offset_x: int = Field(default=0, ge=-32, le=32,
                          description="Horizontal X offset from the anchor to avoid obstacles.")
    offset_z: int = Field(default=0, ge=-32, le=32,
                          description="Horizontal Z offset from the anchor to avoid obstacles.")
    features: list[str] = Field(default_factory=list, max_length=32,
                                description="Named features: 'door', 'windows', 'chimney', …")

    @field_validator("dimensions")
    @classmethod
    def _validate_dimensions(cls, v: list[int]) -> list[int]:
        if any(d < 1 for d in v):
            raise ValueError("dimensions must all be >= 1")
        return v

    @model_validator(mode="after")
    def _validate_palette_nonempty(self) -> "BuildingSpec":
        for field_name in ("walls", "floor", "roof", "foundation"):
            block_list = getattr(self.palette, field_name)
            if not block_list:
                raise ValueError(f"palette.{field_name} must not be empty")
        return self

    @property
    def width(self) -> int:
        return self.dimensions[0]

    @property
    def height(self) -> int:
        return self.dimensions[1]

    @property
    def depth(self) -> int:
        return self.dimensions[2]


# ─── Stage 3: block placements ───────────────────────────────────────────────


class BlockPlacement(BaseModel):
    """A single block placement inside the schematic's local coordinate space.

    Coordinates are non-negative and bounded by the parent BuildingSpec
    dimensions (checked by ``BlockPlacementList``).
    """

    model_config = ConfigDict(extra="forbid")

    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    z: int = Field(..., ge=0)
    block_state: str = Field(..., min_length=1, max_length=128)

    @field_validator("block_state")
    @classmethod
    def _validate_block_state(cls, v: str) -> str:
        if not v.startswith("minecraft:"):
            raise ValueError(f"block_state must start with 'minecraft:': {v!r}")
        return v


class BlockPlacementList(BaseModel):
    """Stage 3 — the complete set of placements, bounds-checked against a spec."""

    model_config = ConfigDict(extra="forbid")

    placements: list[BlockPlacement] = Field(default_factory=list, max_length=200_000)

    def validate_against(self, spec: BuildingSpec, max_dimension: int) -> None:
        """Raises ValueError if any placement is outside the spec bounds."""
        if any(d > max_dimension for d in spec.dimensions):
            raise ValueError(f"dimensions exceed max_dimension={max_dimension}")
        for p in self.placements:
            if p.x >= spec.width or p.y >= spec.height or p.z >= spec.depth:
                raise ValueError(
                    f"placement ({p.x},{p.y},{p.z}) out of bounds for "
                    f"dimensions {spec.dimensions}"
                )

    def apply_offset(self, offset_x: int, offset_z: int) -> None:
        """Shift all placements by the given horizontal offset.

        Used when the intelligent builder decides to move the structure away
        from nearby trees or existing buildings.
        """
        if offset_x == 0 and offset_z == 0:
            return
        for p in self.placements:
            p.x += offset_x
            p.z += offset_z
