"""Ops endpoints: /health + /api/v1/info."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from ..schemas import HealthResponse, InfoResponse
from ..state import AppState

router = APIRouter(tags=["ops"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@router.get("/health", response_model=HealthResponse)
def health(state: AppState = Depends(_state)) -> HealthResponse:
    return HealthResponse(
        version=state.version,
        uptime_seconds=round(time.time() - state.started_at, 2),
    )


@router.get("/api/v1/info", response_model=InfoResponse)
def info(state: AppState = Depends(_state)) -> InfoResponse:
    return InfoResponse(
        name="ai-forecaster",
        version=state.version,
        default_model=state.default_model,
        supported_modes=["demo/rules-only", "chronos-t5", "chronos-bolt"],
        loaded_datasets=state.data.row_counts(),
        notes=[
            "All mock data is loaded from examples/*.xlsx at boot.",
            "Deployments are stored in-memory — swap in Postgres for prod.",
            "Set demo_mode=true on /forecast/staffing to skip Chronos inference.",
        ],
    )
