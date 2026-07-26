"""Streaming progress routes (Server-Sent Events).

Future builds can take many seconds. ``POST /build/stream`` accepts the same
payload as ``POST /build`` but returns immediately and runs generation in a
background task. Clients connect to ``GET /build/stream/{job_id}`` to receive
progress events.

Note: this is a skeleton implementation. For real-time progress, the build
service would accept a progress callback and emit stage events; the job store
would be backed by Redis/RabbitMQ in a multi-process deployment.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from models.requests import BuildRequest
from models.responses import BuildResponse
from routes import deps
from services.build_service import BuildService

logger = logging.getLogger("buildermc.routes.stream")

router = APIRouter()

# In-memory job store. Replace with Redis/RabbitMQ for multi-process deployments.
_JOBS: dict[str, dict] = {}


@router.post("/build/stream")
async def start_streamed_build(
    request: BuildRequest,
    background_tasks: BackgroundTasks,
    demo: bool = False,
    service: BuildService = Depends(deps.get_build_service),
) -> dict[str, str]:
    """Kick off a streamed build and return a job id."""
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"status": "queued", "progress": 0.0, "result": None, "error": None}
    background_tasks.add_task(_run_build, job_id, request, demo, service)
    logger.info("stream build queued: job=%s prompt=%r demo=%s", job_id, request.prompt, demo)
    return {"job_id": job_id, "stream_url": f"/build/stream/{job_id}"}


@router.get("/build/stream/{job_id}")
async def stream_progress(job_id: str) -> StreamingResponse:
    """Server-Sent Events endpoint for build progress."""
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return StreamingResponse(
        _event_stream(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


async def _event_stream(job_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE data lines until the job completes or fails."""
    previous_progress = -1.0
    while True:
        job = _JOBS.get(job_id)
        if job is None:
            yield "event: error\ndata: job disappeared\n\n"
            break

        progress = job.get("progress", 0.0)
        if progress != previous_progress:
            previous_progress = progress
            yield f"event: progress\ndata: {progress}\n\n"

        status = job.get("status")
        if status == "done":
            result: BuildResponse = job["result"]
            yield f"event: done\ndata: {result.schematic}\n\n"
            break
        if status == "error":
            error = job.get("error", "unknown error")
            yield f"event: error\ndata: {error}\n\n"
            break

        await asyncio.sleep(0.5)


async def _run_build(job_id: str, request: BuildRequest, demo: bool, service: BuildService) -> None:
    """Run a build and update the in-memory job store."""
    def _set_progress(progress: float, status: str | None = None) -> None:
        if job_id in _JOBS:
            _JOBS[job_id]["progress"] = min(max(progress, 0.0), 1.0)
            if status:
                _JOBS[job_id]["status"] = status

    try:
        _set_progress(0.0, "starting")
        _set_progress(0.25, "interpreting")
        _set_progress(0.5, "generating")
        _set_progress(0.75, "writing")
        result = await service.build(request, use_demo=demo)
        _JOBS[job_id]["result"] = result
        _JOBS[job_id]["status"] = "done"
        _set_progress(1.0)
    except Exception as exc:
        logger.exception("streamed build failed: job=%s", job_id)
        _JOBS[job_id]["error"] = f"{type(exc).__name__}: {exc}"
        _JOBS[job_id]["status"] = "error"
