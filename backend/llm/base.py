"""Abstract LLM provider interface.

A provider implements the three stages of the generation pipeline. Each stage
returns a Pydantic model that the pipeline validates — providers are
responsible for parsing their model's raw JSON output and either returning a
validated model or raising :class:`MalformedLLMOutputError`.

This interface is async so providers can use real HTTP-based LLMs without
blocking the FastAPI event loop. The bundled stub is synchronous internally but
still awaited.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from models.building_spec import (
    BlockPlacementList,
    BuildingSpec,
    Interpretation,
)
from models.world_context import WorldContext


class MalformedLLMOutputError(RuntimeError):
    """Raised when an LLM emits JSON that fails Pydantic validation."""


class LanguageModelProvider(ABC):
    """A swappable AI backend behind the 3-stage pipeline."""

    @abstractmethod
    async def interpret(self, prompt: str, context: WorldContext) -> Interpretation:
        """Stage 1 — read the user's prompt into a structured interpretation."""

    @abstractmethod
    async def generate_spec(
        self, interpretation: Interpretation, context: WorldContext
    ) -> BuildingSpec:
        """Stage 2 — turn the interpretation into a full building specification."""

    @abstractmethod
    async def generate_placements(
        self, spec: BuildingSpec, context: WorldContext
    ) -> BlockPlacementList:
        """Stage 3 — turn the spec into concrete block placements."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release any resources held by this provider.

        Called by the build service after a per-request provider finishes.
        Providers that do not hold resources should implement this as a no-op.
        """
