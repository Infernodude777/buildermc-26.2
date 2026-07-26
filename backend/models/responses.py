"""Outbound response models for the /build endpoint."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BlockPlacementEntry(BaseModel):
    """A single block placement in schematic-local coordinates.

    Mirrors ``BlockPlacement`` but lives in the response package so the mod can
    place blocks without parsing the ``.schem`` file itself.
    """

    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    z: int = Field(..., ge=0)
    block_state: str = Field(..., min_length=1)


class BuildResponse(BaseModel):
    """Successful (or explicit-failure) response from ``POST /build``."""

    status: Literal["success", "error"] = "success"
    schematic: str = Field(default="", description="Path to the generated .schem file.")
    dimensions: list[int] = Field(default_factory=list, description="[x, y, z] size of the schematic.")
    placements: list[BlockPlacementEntry] = Field(
        default_factory=list,
        description="Raw block placements for the mod to paste into the world.",
    )
    decisions: list[str] = Field(
        default_factory=list,
        description="Human-readable design decisions logged by the intelligent builder.",
    )
    error: str | None = Field(default=None, description="Present only when status == 'error'.")

    @classmethod
    def failure(cls, message: str) -> "BuildResponse":
        return cls(status="error", error=message)
