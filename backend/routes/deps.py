"""FastAPI dependency providers — singletons wired once per process.

Using ``Depends(get_build_service)`` keeps the route handler pure and makes the
collaborators swappable for tests (override the dependency in the app).
"""
from __future__ import annotations

from functools import lru_cache

from config.settings import settings
from generator.schematic_writer import SchematicWriter
from intelligent.builder import IntelligentBuilder
from llm import get_provider
from llm.pipeline import GenerationPipeline
from services.build_service import BuildService


@lru_cache
def get_pipeline() -> GenerationPipeline:
    return GenerationPipeline(provider=get_provider(settings.llm_provider))


@lru_cache
def get_writer() -> SchematicWriter:
    return SchematicWriter(output_dir=settings.output_dir)


@lru_cache
def get_intelligent() -> IntelligentBuilder:
    return IntelligentBuilder()


@lru_cache
def get_build_service() -> BuildService:
    return BuildService(
        pipeline=get_pipeline(),
        writer=get_writer(),
        intelligent=get_intelligent(),
    )
