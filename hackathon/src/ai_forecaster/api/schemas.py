"""Pydantic request/response models for the API.

Named to match fields on the user-flow screens so a client developer can
look at a screen and immediately know which shapes to consume.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

Shift = Literal["Morning", "Afternoon", "Evening"]
Confidence = Literal["high", "medium", "low"]
Outcome = Literal["short", "met", "over"]


class ApiError(BaseModel):
    """Standard error body returned on 4xx/5xx."""

    error: str
    detail: str | None = None


# ---------------------------------------------------------------------------
# Screen 0 — Store profile
# ---------------------------------------------------------------------------


class Station(BaseModel):
    station_id: str
    station_name: str
    area: str
    positions: int
    base_staff_morning: int
    base_staff_afternoon: int
    base_staff_evening: int
    primary_channel: str
    channel_weight: float
    icon_emoji: str | None = None
    colour_hex: str | None = None


class Task(BaseModel):
    task_id: str
    task_name: str
    category: str
    area: str
    duration_min: int
    frequency_per_shift: int
    icon_emoji: str | None = None


class Store(BaseModel):
    store_id: str
    store_name: str
    city: str
    open_hour: int
    close_hour: int
    shifts_per_day: int
    base_staff_per_shift: int
    min_staff_per_shift: int
    max_staff_per_shift: int
    base_daily_orders: int | None = None


# ---------------------------------------------------------------------------
# Screen 1 — Crew
# ---------------------------------------------------------------------------


class Employee(BaseModel):
    employee_id: str
    employee_name: str
    store_id: str
    role: str
    contract_hours_per_week: int
    min_hours_per_week: int
    hourly_rate: float
    available_days: list[str]
    available_shifts: list[Shift]
    skills: list[str] = Field(default_factory=list, description="Certified station_ids")


class EmployeeCreate(BaseModel):
    employee_name: str
    role: str
    contract_hours_per_week: int = 40
    min_hours_per_week: int = 24
    hourly_rate: float = 18.0
    available_days: list[str] = Field(default_factory=lambda: ["Mon", "Tue", "Wed", "Thu", "Fri"])
    available_shifts: list[Shift] = Field(default_factory=lambda: ["Morning", "Afternoon"])
    skills: list[str] = Field(default_factory=list)


class EmployeePatch(BaseModel):
    employee_name: str | None = None
    role: str | None = None
    contract_hours_per_week: int | None = None
    min_hours_per_week: int | None = None
    hourly_rate: float | None = None
    available_days: list[str] | None = None
    available_shifts: list[Shift] | None = None
    skills: list[str] | None = None


# ---------------------------------------------------------------------------
# Screen 2 — External context + AI staffing suggestion
# ---------------------------------------------------------------------------


class ContextFactor(BaseModel):
    """One external-context badge on screen 2."""

    kind: Literal["weather", "event", "promo", "holiday", "day_of_week"]
    label: str
    icon: str
    probability: float | None = None
    impact_delivery: float = 0.0
    impact_dinein: float = 0.0
    impact_drivethrough: float = 0.0
    source: str  # "prediction_rule" | "ai_inference" | "calendar_check" | "forecast_feed"
    note: str
    time_window: str | None = None


class ContextResponse(BaseModel):
    store_id: str
    date: Date
    day_of_week: str
    factors: list[ContextFactor]
    # Aggregated multipliers (post-rule) that the forecast will use.
    channel_multipliers: dict[str, float]


class ReasonRow(BaseModel):
    """One row in the expandable "reason" panel on Screen 2."""

    icon: str
    label: str
    value: str


class RushHourInfo(BaseModel):
    """Rush-hour metadata for a shift cell."""

    is_rush: bool = False
    label: str | None = None
    window: str | None = None
    overlap_pct: float = 0.0
    staff_uplift: int = 0
    solutions: list[str] = Field(default_factory=list)


class StaffingCell(BaseModel):
    station_id: str
    station_name: str
    shift: Shift
    ai_recommended: int
    reason_short: str
    confidence: Confidence
    factors: list[str]
    rules_applied: list[str]
    channel_note: str
    crew_note: str
    reason_rows: list[ReasonRow]
    rush_hour: RushHourInfo = Field(default_factory=RushHourInfo)


class StaffingRequest(BaseModel):
    store_id: str
    date: Date
    # When True (default in tests), skip Chronos and use the rule-based
    # engine alone — no torch download required.
    demo_mode: bool = False
    model_config = ConfigDict(protected_namespaces=())


class StaffingResponse(BaseModel):
    store_id: str
    date: Date
    day_of_week: str
    generated_at: datetime
    model_used: str
    generation_ms: int
    context: ContextResponse
    cells: list[StaffingCell]

    def grid(self) -> dict[str, dict[str, StaffingCell]]:
        """Convenience: reshape into ``{station_id: {shift: cell}}``."""
        out: dict[str, dict[str, StaffingCell]] = {}
        for c in self.cells:
            out.setdefault(c.station_id, {})[c.shift] = c
        return out


# ---------------------------------------------------------------------------
# Screen 3 / 4 / 5 — Deployments
# ---------------------------------------------------------------------------


class AssignedCell(BaseModel):
    station_id: str
    shift: Shift
    ai_recommended: int
    assigned_employee_ids: list[str] = Field(default_factory=list)
    manager_note: str | None = None


class DeploymentCreate(BaseModel):
    store_id: str
    date: Date
    cells: list[AssignedCell]
    source_staffing_model: str | None = None


class Deployment(BaseModel):
    deployment_id: str
    store_id: str
    date: Date
    created_at: datetime
    updated_at: datetime
    cells: list[AssignedCell]
    source_staffing_model: str | None = None


class DeploymentPatch(BaseModel):
    cells: list[AssignedCell]


class DeploymentSummary(BaseModel):
    deployment_id: str
    store_id: str
    date: Date
    total_ai_recommended: int
    total_assigned: int
    gap: int
    coverage_pct: float
    shortages: list[AssignedCell]  # cells where assigned < ai_recommended
    overages: list[AssignedCell]
    est_wage_cost: float
    confidence_mix: dict[Confidence, int] = Field(default_factory=dict)


class ComparisonRow(BaseModel):
    station_id: str
    shift: Shift
    ai_recommended: int
    manager_assigned: int
    actual_staffed: int | None = None
    gap: int
    outcome: Outcome


class DeploymentComparison(BaseModel):
    deployment_id: str
    rows: list[ComparisonRow]


# ---------------------------------------------------------------------------
# Chat — AI assistant
# ---------------------------------------------------------------------------


class ChatMessageIn(BaseModel):
    """One message in the conversation history sent by the client."""

    role: Literal["user", "ai", "system"]
    content: str


class ChatAction(BaseModel):
    """A structured action the AI wants the manager to apply."""

    type: Literal["assign", "unassign", "swap"]
    employee_id: str
    employee_name: str | None = None
    station_id: str
    station_name: str | None = None
    shift: Shift
    reason: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessageIn] = Field(default_factory=list)
    store_id: str
    date: Date
    current_cells: list[AssignedCell] = Field(
        default_factory=list,
        description="Current deployment state from the UI so the AI knows what's assigned.",
    )


class ChatResponse(BaseModel):
    message: str
    actions: list[ChatAction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ops
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    uptime_seconds: float


class InfoResponse(BaseModel):
    name: str
    version: str
    default_model: str
    supported_modes: list[str]
    loaded_datasets: dict[str, int]
    notes: list[str]
