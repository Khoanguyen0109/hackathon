"""Screen 1 — Crew setup: /stores/{id}/crew CRUD."""

from __future__ import annotations

import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..schemas import Employee, EmployeeCreate, EmployeePatch
from ..state import AppState

router = APIRouter(tags=["crew"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


def _row_to_employee(row: dict) -> Employee:
    return Employee(**{
        **row,
        "available_days": row.get("available_days") or [],
        "available_shifts": row.get("available_shifts") or [],
        "skills": row.get("skills") or [],
    })


@router.get("/api/v1/stores/{store_id}/crew", response_model=list[Employee])
def list_crew(store_id: str, state: AppState = Depends(_state)) -> list[Employee]:
    df = state.data.employees
    if df.empty:
        return []
    subset = df[df["store_id"] == store_id]
    return [_row_to_employee(r) for r in subset.to_dict(orient="records")]


@router.post("/api/v1/stores/{store_id}/crew",
             response_model=Employee, status_code=status.HTTP_201_CREATED)
def create_crew(store_id: str, body: EmployeeCreate,
                state: AppState = Depends(_state)) -> Employee:
    if state.data.stores[state.data.stores["store_id"] == store_id].empty:
        raise HTTPException(404, f"store_id={store_id} not found")

    emp_id = f"E{uuid.uuid4().hex[:6].upper()}"
    row = {
        "employee_id": emp_id,
        "employee_name": body.employee_name,
        "store_id": store_id,
        "role": body.role,
        "contract_hours_per_week": body.contract_hours_per_week,
        "min_hours_per_week": body.min_hours_per_week,
        "hourly_rate": body.hourly_rate,
        "available_days": body.available_days,
        "available_shifts": body.available_shifts,
        "skills": body.skills,
    }
    state.data.employees = pd.concat(
        [state.data.employees, pd.DataFrame([row])], ignore_index=True,
    )
    return _row_to_employee(row)


@router.patch("/api/v1/crew/{employee_id}", response_model=Employee)
def patch_crew(employee_id: str, body: EmployeePatch,
               state: AppState = Depends(_state)) -> Employee:
    df = state.data.employees
    idx = df.index[df["employee_id"] == employee_id]
    if len(idx) == 0:
        raise HTTPException(404, f"employee_id={employee_id} not found")
    i = idx[0]
    patch = body.model_dump(exclude_unset=True)
    for k, v in patch.items():
        df.at[i, k] = v
    state.data.employees = df
    return _row_to_employee(df.loc[i].to_dict())


@router.delete("/api/v1/crew/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crew(employee_id: str, state: AppState = Depends(_state)) -> None:
    df = state.data.employees
    if df[df["employee_id"] == employee_id].empty:
        raise HTTPException(404, f"employee_id={employee_id} not found")
    state.data.employees = df[df["employee_id"] != employee_id].reset_index(drop=True)
