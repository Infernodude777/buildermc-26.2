"""FastAPI application entrypoint.

Run with:
    uvicorn server:app --reload --port 8000
or:
    python server.py
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config.settings import settings
from routes.build import router as build_router
from routes.stream import router as stream_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
logger = logging.getLogger("buildermc.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "builderMC backend starting | host=%s port=%s provider=%s out=%s",
        settings.host, settings.port, settings.llm_provider, settings.output_dir,
    )
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("builderMC backend shutting down.")


app = FastAPI(
    title="builderMC backend",
    description="AI-powered Minecraft structure generator — receives prompts + world context, returns .schem files.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(build_router)
app.include_router(stream_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "builderMC backend", "status": "running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
