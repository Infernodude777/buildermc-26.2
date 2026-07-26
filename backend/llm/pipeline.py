"""The 3-stage AI generation pipeline.

Stage 1 — interpret the prompt.
Stage 2 — generate a building specification.
Stage 3 — generate concrete block placements.

Each stage's output is Pydantic-validated by the provider before it is returned,
and Stage 3 placements are bounds-checked against the Stage 2 spec here. Any
validation failure raises and the build service returns an error response.
"""
from __future__ import annotations

import logging

from config.settings import settings
from intelligent.builder import IntelligentBuilder
from models.building_spec import BlockPlacementList, BuildingSpec, Interpretation
from models.world_context import WorldContext

from .base import LanguageModelProvider, MalformedLLMOutputError
from .stub_provider import StubProvider

logger = logging.getLogger("buildermc.llm.pipeline")


class GenerationPipeline:
    """Runs the three stages against a provider and returns validated output."""

    def __init__(
        self,
        provider: LanguageModelProvider | None = None,
        intelligent: IntelligentBuilder | None = None,
    ) -> None:
        # Default to the stub provider so the pipeline is testable offline.
        self.provider = provider or StubProvider()
        self.intelligent = intelligent or IntelligentBuilder()

    async def run(
        self, prompt: str, context: WorldContext
    ) -> tuple[BuildingSpec, BlockPlacementList, list[str]]:
        logger.info("pipeline stage 1: interpret prompt=%r", prompt)
        try:
            interpretation: Interpretation = await self.provider.interpret(prompt, context)
        except MalformedLLMOutputError:
            raise
        except Exception as e:
            raise MalformedLLMOutputError(f"Stage 1 (interpret) failed: {e}") from e
        logger.info("pipeline stage 1 done: %s", interpretation)

        logger.info("pipeline stage 2: generate spec")
        try:
            spec: BuildingSpec = await self.provider.generate_spec(interpretation, context)
        except MalformedLLMOutputError:
            raise
        except Exception as e:
            raise MalformedLLMOutputError(f"Stage 2 (spec) failed: {e}") from e
        logger.info("pipeline stage 2 done: dims=%s palette=%s", spec.dimensions, spec.palette.name)

        logger.info("pipeline stage 2.5: adapt spec to world context")
        spec, decisions = self.intelligent.adapt(spec, context)
        logger.info("pipeline stage 2.5 done: %d decisions", len(decisions))

        logger.info("pipeline stage 3: generate placements")
        try:
            placements: BlockPlacementList = await self.provider.generate_placements(spec, context)
        except MalformedLLMOutputError:
            raise
        except Exception as e:
            raise MalformedLLMOutputError(f"Stage 3 (placements) failed: {e}") from e
        placements.validate_against(spec, settings.max_dimension)
        logger.info("pipeline stage 3 done: %d placements", len(placements.placements))

        return spec, placements, decisions
