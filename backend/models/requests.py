"""Inbound request models for the /build endpoint."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .world_context import WorldContext


class BuildRequest(BaseModel):
    """Body of ``POST /build``.

    ``world_context`` is optional so the endpoint still works for raw API
    testing without a running mod; the intelligent builder treats a missing
    context as a neutral plains-like default.
    """

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1, max_length=2000, description="Natural-language build request.")
    seed: int = Field(default=0, ge=0, description="World seed (used for deterministic variants).")
    world_context: WorldContext = Field(default_factory=WorldContext)

    @model_validator(mode="after")
    def _strip_prompt(self) -> "BuildRequest":
        self.prompt = self.prompt.strip()
        if not self.prompt:
            raise ValueError("prompt must not be empty")
        return self
