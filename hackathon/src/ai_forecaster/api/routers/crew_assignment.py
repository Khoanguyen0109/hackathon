"""AI crew auto-assignment endpoint.

``POST /api/v1/forecast/crew-assignment`` takes the staffing grid and
returns employee assignments with per-cell reasoning from Ollama.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..crew_assignment_service import assign_crew
from ..schemas import CrewAssignmentRequest, CrewAssignmentResponse
from ..state import AppState

router = APIRouter(tags=["forecast"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/api/v1/forecast/crew-assignment", response_model=CrewAssignmentResponse)
async def crew_assignment(body: CrewAssignmentRequest,
                          state: AppState = Depends(_state)) -> CrewAssignmentResponse:
    try:
        return await assign_crew(
            state.data,
            store_id=body.store_id,
            target=body.date,
            staffing_cells=body.staffing_cells,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
