"""Screen 0 — Store profile: /stores, /stations, /tasks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas import Station, Store, Task
from ..state import AppState

router = APIRouter(tags=["stores"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@router.get("/api/v1/stations", response_model=list[Station])
def list_stations(state: AppState = Depends(_state)) -> list[Station]:
    return [Station(**row) for row in state.data.stations.to_dict(orient="records")]


@router.get("/api/v1/tasks", response_model=list[Task])
def list_tasks(state: AppState = Depends(_state)) -> list[Task]:
    return [Task(**row) for row in state.data.tasks.to_dict(orient="records")]


@router.get("/api/v1/stores", response_model=list[Store])
def list_stores(state: AppState = Depends(_state)) -> list[Store]:
    rows = state.data.stores.to_dict(orient="records")
    return [Store(**row) for row in rows]


@router.get("/api/v1/stores/{store_id}", response_model=Store)
def get_store(store_id: str, state: AppState = Depends(_state)) -> Store:
    df = state.data.stores
    row = df[df["store_id"] == store_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"store_id={store_id} not found")
    return Store(**row.iloc[0].to_dict())
