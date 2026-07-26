"""Build service — orchestrates the backend's generation flow.

Flow:
  1. (optional) run the 3-stage LLM pipeline → (BuildingSpec, BlockPlacementList)
     — or use the demo generator when ``use_demo=True`` (no LLM, Prompt 3)
  2. adapt the spec to the world context via :class:`IntelligentBuilder`
  3. write the schematic via :class:`SchematicWriter`
  4. return a :class:`BuildResponse` with the schematic path, dimensions, and
     the intelligent builder's decision log

All stages are async-friendly and log every step.
"""
from __future__ import annotations

import logging

from config.settings import settings
from generator.demo_generator import generate_demo_structure
from generator.schematic_writer import SchematicWriter
from intelligent.builder import IntelligentBuilder
from llm.pipeline import GenerationPipeline
from models.requests import BuildRequest
from models.responses import BlockPlacementEntry, BuildResponse

logger = logging.getLogger("buildermc.services.build")


class BuildService:
    """Coordinates the pipeline, intelligent adaptation, and schematic writing."""

    def __init__(
        self,
        pipeline: GenerationPipeline,
        writer: SchematicWriter,
        intelligent: IntelligentBuilder,
    ) -> None:
        self.pipeline = pipeline
        self.writer = writer
        self.intelligent = intelligent

    async def build(self, request: BuildRequest, use_demo: bool = False) -> BuildResponse:
        logger.info(
            "build start: prompt=%r seed=%d demo=%s context=%s",
            request.prompt, request.seed, use_demo, request.world_context.biome,
        )
        try:
            if use_demo:
                logger.info("using demo generator (no LLM)")
                spec, placements = generate_demo_structure(request.world_context)
                # Apply the same intelligent adaptation to the demo path.
                spec, decisions = self.intelligent.adapt(spec, request.world_context)
            else:
                spec, placements, decisions = await self.pipeline.run(
                    request.prompt, request.world_context
                )

            # Apply any world-context-driven horizontal offset (clearance / tree
            # preservation) before writing the schematic.
            if spec.offset_x or spec.offset_z:
                placements.apply_offset(spec.offset_x, spec.offset_z)

            # Validate placements against the (possibly adapted) spec bounds.
            placements.validate_against(spec, max_dimension=settings.max_dimension)

            path = self.writer.write(spec, placements)

            placement_entries = [
                BlockPlacementEntry(x=p.x, y=p.y, z=p.z, block_state=p.block_state)
                for p in placements.placements
            ]

            logger.info(
                "build success: schematic=%s blocks=%d decisions=%d",
                path, len(placement_entries), len(decisions),
            )
            return BuildResponse(
                status="success",
                schematic=str(path).replace("\\", "/"),
                dimensions=[spec.width, spec.height, spec.depth],
                placements=placement_entries,
                decisions=decisions,
            )
        except Exception as e:
            logger.exception("build failed")
            return BuildResponse.failure(f"{type(e).__name__}: {e}")
