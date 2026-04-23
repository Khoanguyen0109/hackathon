"""Screens 3 / 4 / 5 — save, retrieve, summarise deployments.

Deployments are the result of a manager accepting/overriding the AI
suggestion grid and assigning specific crew members to each cell.

Data lives in ``state.deployments`` (in-memory). Swap to a real database
for production.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ..schemas import (
    ComparisonRow,
    Deployment,
    DeploymentComparison,
    DeploymentCreate,
    DeploymentPatch,
    DeploymentSummary,
)
from ..state import AppState

router = APIRouter(tags=["deployments"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/api/v1/deployments",
             response_model=Deployment, status_code=status.HTTP_201_CREATED)
def create_deployment(body: DeploymentCreate,
                      state: AppState = Depends(_state)) -> Deployment:
    if state.data.stores[state.data.stores["store_id"] == body.store_id].empty:
        raise HTTPException(404, f"store_id={body.store_id} not found")
    now = datetime.utcnow()
    dep = Deployment(
        deployment_id=state.deployments.new_id(),
        store_id=body.store_id,
        date=body.date,
        created_at=now,
        updated_at=now,
        cells=body.cells,
        source_staffing_model=body.source_staffing_model,
    )
    state.deployments.put(dep)
    return dep


@router.get("/api/v1/deployments", response_model=list[Deployment])
def list_deployments(store_id: str | None = Query(None),
                     state: AppState = Depends(_state)) -> list[Deployment]:
    return state.deployments.list(store_id=store_id)


@router.get("/api/v1/deployments/{deployment_id}", response_model=Deployment)
def get_deployment(deployment_id: str, state: AppState = Depends(_state)) -> Deployment:
    dep = state.deployments.get(deployment_id)
    if not dep:
        raise HTTPException(404, f"deployment_id={deployment_id} not found")
    return dep


@router.patch("/api/v1/deployments/{deployment_id}", response_model=Deployment)
def patch_deployment(deployment_id: str, body: DeploymentPatch,
                     state: AppState = Depends(_state)) -> Deployment:
    dep = state.deployments.get(deployment_id)
    if not dep:
        raise HTTPException(404, f"deployment_id={deployment_id} not found")
    updated = Deployment(
        **{**dep.model_dump(), "cells": body.cells, "updated_at": datetime.utcnow()},
    )
    state.deployments.put(updated)
    return updated


@router.delete("/api/v1/deployments/{deployment_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_deployment(deployment_id: str, state: AppState = Depends(_state)) -> None:
    if not state.deployments.delete(deployment_id):
        raise HTTPException(404, f"deployment_id={deployment_id} not found")


@router.get("/api/v1/deployments/{deployment_id}/summary",
            response_model=DeploymentSummary)
def summarise_deployment(deployment_id: str,
                         state: AppState = Depends(_state)) -> DeploymentSummary:
    dep = state.deployments.get(deployment_id)
    if not dep:
        raise HTTPException(404, f"deployment_id={deployment_id} not found")

    total_ai = sum(c.ai_recommended for c in dep.cells)
    total_asg = sum(len(c.assigned_employee_ids) for c in dep.cells)
    gap = total_asg - total_ai
    coverage = (total_asg / total_ai) if total_ai else 1.0
    shortages = [c for c in dep.cells
                 if len(c.assigned_employee_ids) < c.ai_recommended]
    overages = [c for c in dep.cells
                if len(c.assigned_employee_ids) > c.ai_recommended]

    # Wage-cost estimate uses ~6h/shift × store employees' mean rate.
    employees = state.data.employees
    emp_rate = {
        str(r["employee_id"]): float(r["hourly_rate"])
        for r in employees.to_dict(orient="records")
    } if not employees.empty else {}
    cost = 0.0
    for c in dep.cells:
        for eid in c.assigned_employee_ids:
            cost += 6.0 * emp_rate.get(eid, 20.0)

    return DeploymentSummary(
        deployment_id=dep.deployment_id,
        store_id=dep.store_id,
        date=dep.date,
        total_ai_recommended=total_ai,
        total_assigned=total_asg,
        gap=gap,
        coverage_pct=round(coverage * 100, 1),
        shortages=shortages,
        overages=overages,
        est_wage_cost=round(cost, 2),
    )


@router.get("/api/v1/deployments/{deployment_id}/comparison",
            response_model=DeploymentComparison)
def compare_deployment(deployment_id: str,
                       state: AppState = Depends(_state)) -> DeploymentComparison:
    """Compare saved deployment vs past_deployments.xlsx actuals (if any)."""
    dep = state.deployments.get(deployment_id)
    if not dep:
        raise HTTPException(404, f"deployment_id={deployment_id} not found")

    past = state.data.past_deployments
    rows: list[ComparisonRow] = []
    for c in dep.cells:
        manager = len(c.assigned_employee_ids)
        actual = None
        if not past.empty:
            import pandas as pd
            mask = (
                (past["store_id"] == dep.store_id)
                & (pd.to_datetime(past["date"]).dt.date == dep.date)
                & (past["shift"] == c.shift)
                & (past["station_id"] == c.station_id)
            )
            match = past[mask]
            if not match.empty:
                actual = int(match.iloc[0]["actual_staffed"])

        gap = manager - c.ai_recommended
        outcome = "short" if gap <= -1 else "over" if gap >= 1 else "met"
        rows.append(ComparisonRow(
            station_id=c.station_id, shift=c.shift,
            ai_recommended=c.ai_recommended,
            manager_assigned=manager,
            actual_staffed=actual,
            gap=gap, outcome=outcome,
        ))
    return DeploymentComparison(deployment_id=deployment_id, rows=rows)
