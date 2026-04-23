"""Screen 2 — AI staffing suggestion grid.

``POST /api/v1/forecast/staffing`` with ``{store_id, date, demo_mode}``
returns the full station × shift grid with per-cell reasoning.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..reasoning import generate_staffing
from ..schemas import StaffingRequest, StaffingResponse
from ..state import AppState

router = APIRouter(tags=["forecast"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/api/v1/forecast/staffing", response_model=StaffingResponse)
def forecast_staffing(body: StaffingRequest,
                      state: AppState = Depends(_state)) -> StaffingResponse:
    try:
        return generate_staffing(
            state.data,
            store_id=body.store_id,
            target=body.date,
            demo_mode=body.demo_mode,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
