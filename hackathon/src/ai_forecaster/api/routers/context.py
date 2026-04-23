"""Screen 2 — External factors for the selected date.

``GET /api/v1/context?store_id=S0001&date=2026-04-26`` returns every
factor badge the UI shows above the "Generate staffing suggestion"
button, plus the aggregated channel multipliers the forecast will use.
"""

from __future__ import annotations

from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..reasoning import build_context
from ..schemas import ContextResponse
from ..state import AppState

router = APIRouter(tags=["context"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@router.get("/api/v1/context", response_model=ContextResponse)
def get_context(
    store_id: str = Query(..., description="Store whose location governs weather/events."),
    date: Date = Query(..., description="Target date (YYYY-MM-DD)."),
    state: AppState = Depends(_state),
) -> ContextResponse:
    if state.data.stores[state.data.stores["store_id"] == store_id].empty:
        raise HTTPException(404, f"store_id={store_id} not found")
    return build_context(state.data, store_id, date)
