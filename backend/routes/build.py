"""POST /build route + GET /health.

Keeps the route thin: parse + validate the request (Pydantic does this), call
the build service, return the response. The ``?demo=true`` query switches to
the no-LLM demo generator so the whole pipeline can be smoke-tested without an
LLM provider configured.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from models.requests import BuildRequest
from models.responses import BuildResponse
from services.build_service import BuildService

from . import deps

logger = logging.getLogger("buildermc.routes.build")

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — used by the mod to verify the backend is up."""
    return {"status": "ok"}


@router.post("/build", response_model=BuildResponse)
async def build(
    request: BuildRequest,
    demo: bool = Query(default=False, description="Use the no-LLM demo generator."),
    service: BuildService = Depends(deps.get_build_service),
) -> BuildResponse:
    """Generate a structure from a prompt and (optional) world context."""
    logger.info("POST /build prompt=%r demo=%s", request.prompt, demo)
    return await service.build(request, use_demo=demo)
