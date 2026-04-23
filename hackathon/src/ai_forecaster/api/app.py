"""FastAPI application factory.

Usage:

    from ai_forecaster.api import create_app
    app = create_app()

Run with uvicorn:

    uvicorn ai_forecaster.api:create_app --factory --reload --port 8000

Or via the CLI:

    ai-forecast serve --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import chat, context, crew, deployments, forecast, ops, stores
from .state import AppState

logger = logging.getLogger(__name__)


def create_app(examples_dir: str | Path | None = None) -> FastAPI:
    """Build the FastAPI application.

    Parameters
    ----------
    examples_dir:
        Where to load mock Excel data from. Defaults to ``examples/``
        alongside the package.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Loading mock data bundle...")
        app.state.app_state = AppState.bootstrap(examples_dir=examples_dir)
        counts = app.state.app_state.data.row_counts()
        logger.info("Loaded datasets: %s", counts)
        yield
        logger.info("Shutting down API.")

    app = FastAPI(
        title="AI Deployment Chart API",
        summary="Forecast-driven shift staffing, mirrors the ByteCoach Manager user flow.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ops.router)
    app.include_router(stores.router)
    app.include_router(crew.router)
    app.include_router(context.router)
    app.include_router(forecast.router)
    app.include_router(deployments.router)
    app.include_router(chat.router)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "name": "ai-forecaster",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
        }

    return app
