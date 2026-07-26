"""Inbound request models for the /build endpoint."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .world_context import WorldContext


class ProviderConfig(BaseModel):
    """AI provider configuration forwarded by the mod's ``/api`` command."""

    model_config = ConfigDict(extra="forbid")

    base_url: str = Field(..., min_length=1, description="OpenAI-compatible API base URL.")
    model_id: str = Field(..., min_length=1, description="Model identifier to use.")
    api_key: str = Field(..., min_length=1, description="API key for the provider.")
    provider: str = Field(default="openai", min_length=1, description="Provider type (e.g. openai, anthropic, local).")


class BuildRequest(BaseModel):
    """Body of ``POST /build``.

    ``world_context`` is optional so the endpoint still works for raw API
    testing without a running mod; the intelligent builder treats a missing
    context as a neutral plains-like default.

    ``provider_config`` is optional; when present it overrides the server's
    default LLM provider for this request, allowing the mod to switch
    providers at runtime via the ``/api`` command.
    """

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1, max_length=2000, description="Natural-language build request.")
    seed: int = Field(default=0, ge=0, description="World seed (used for deterministic variants).")
    world_context: WorldContext = Field(default_factory=WorldContext)
    provider_config: ProviderConfig | None = Field(default=None, description="Optional LLM provider override.")

    @model_validator(mode="after")
    def _strip_prompt(self) -> "BuildRequest":
        self.prompt = self.prompt.strip()
        if not self.prompt:
            raise ValueError("prompt must not be empty")
        return self
