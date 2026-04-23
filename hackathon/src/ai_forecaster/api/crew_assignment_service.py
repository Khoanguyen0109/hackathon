"""AI crew auto-assignment service — Ollama-backed with rules fallback.

Given a staffing grid (list of StaffingCell from the forecast), assigns
specific employees to each station×shift slot.  Calls Ollama for
intelligent assignment with reasoning; falls back to a deterministic
skill-match + lowest-rate heuristic when the LLM is unreachable.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import date as Date

import httpx
import pandas as pd

from .reasoning import build_context
from .schemas import (
    CrewAssignmentCell,
    CrewAssignmentResponse,
    StaffingCell,
)
from .state import DataBundle

logger = logging.getLogger(__name__)

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_JSON_BLOCK_RE = re.compile(r"```json\s*\n?(.*?)```", re.DOTALL)

SHIFT_ORDER = {"Morning": 0, "Afternoon": 1, "Evening": 2}


def _dow(d: Date) -> str:
    return DAY_NAMES[d.weekday()]


# ---------------------------------------------------------------------------
# Employee filtering (mirrors reasoning._available_crew)
# ---------------------------------------------------------------------------


def _available_crew_df(
    employees: pd.DataFrame,
    store_id: str,
    dow: str,
    overrides: pd.DataFrame,
    target: Date,
) -> pd.DataFrame:
    """Return a DataFrame of employees available at this store on the target day."""
    if employees.empty:
        return employees
    emp = employees[employees["store_id"] == store_id].copy()

    def _has(col, needle):
        return col.map(lambda xs: needle in (xs or []))

    emp = emp[_has(emp["available_days"], dow)]

    if not overrides.empty:
        ov_today = overrides[
            (pd.to_datetime(overrides["date"]).dt.date == target)
            & (~overrides["available"].astype(bool))
        ]
        blocked = set(ov_today["employee_id"].astype(str))
        emp = emp[~emp["employee_id"].astype(str).isin(blocked)]

    return emp


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_assignment_prompt(
    staffing_cells: list[StaffingCell],
    employees: pd.DataFrame,
    store_id: str,
    target: Date,
    overrides: pd.DataFrame,
    context_factors: list[str],
) -> str:
    """Build the system prompt for the Ollama crew-assignment call."""
    lines: list[str] = []

    lines.append("You are an AI crew-assignment engine for a pizza restaurant.")
    lines.append("")
    lines.append("STATIONS NEEDING CREW:")
    lines.append(f"{'station_id':<16} {'station_name':<20} {'shift':<12} {'ai_recommended'}")
    for cell in staffing_cells:
        lines.append(f"{cell.station_id:<16} {cell.station_name:<20} {cell.shift:<12} {cell.ai_recommended}")

    lines.append("")
    lines.append("AVAILABLE EMPLOYEES:")
    if employees.empty:
        lines.append("(none)")
    else:
        lines.append(
            f"{'employee_id':<14} {'employee_name':<20} {'skills':<30} "
            f"{'available_shifts':<30} {'hourly_rate'}"
        )
        for _, row in employees.iterrows():
            skills = ",".join(row["skills"]) if isinstance(row["skills"], list) else str(row["skills"])
            shifts = ",".join(row["available_shifts"]) if isinstance(row["available_shifts"], list) else str(row["available_shifts"])
            lines.append(
                f"{str(row['employee_id']):<14} {str(row['employee_name']):<20} "
                f"{skills:<30} {shifts:<30} {row['hourly_rate']}"
            )

    if context_factors:
        lines.append("")
        lines.append("CONTEXT: " + "; ".join(context_factors))

    lines.append("")
    lines.append("RULES:")
    lines.append("- Assign each employee to AT MOST ONE shift (no double-booking).")
    lines.append("- Only assign to stations they are certified for (skills contains station_id).")
    lines.append("- Only assign to shifts they are available for (available_shifts).")
    lines.append("- When qualifications are equal, prefer lower hourly_rate.")
    lines.append("- Return a JSON array inside ```json fences with this structure:")
    lines.append('  [{"station_id": "...", "shift": "...", "assigned_employee_ids": [...], "reasoning": "..."}]')
    lines.append("- Include ALL station/shift cells in the output, even if no employees can be assigned (empty list).")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Ollama call
# ---------------------------------------------------------------------------


async def call_ollama_assignment(system_prompt: str, store_id: str, target: Date) -> str:
    """Call Ollama with the assignment prompt and return the raw response."""
    dow = _dow(target)
    user_message = f"Please assign crew for {dow} {target} at store {store_id}."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        resp = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        resp.raise_for_status()
        body = resp.json()

    return body.get("message", {}).get("content", "")


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_assignment_response(
    raw: str,
    staffing_cells: list[StaffingCell],
) -> tuple[list[CrewAssignmentCell], str]:
    """Parse the LLM output into CrewAssignmentCell list and a summary string."""
    cells: list[CrewAssignmentCell] = []

    json_match = _JSON_BLOCK_RE.search(raw)
    if json_match:
        try:
            raw_items = json.loads(json_match.group(1).strip())
            if isinstance(raw_items, list):
                for item in raw_items:
                    try:
                        cells.append(CrewAssignmentCell(
                            station_id=item["station_id"],
                            shift=item["shift"],
                            ai_recommended=_find_ai_rec(item["station_id"], item["shift"], staffing_cells),
                            assigned_employee_ids=item.get("assigned_employee_ids", []),
                            reasoning=item.get("reasoning", ""),
                        ))
                    except Exception:
                        logger.warning("Skipping malformed assignment item: %s", item)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from crew-assignment LLM response")

    summary = _JSON_BLOCK_RE.sub("", raw).strip()
    return cells, summary


def _find_ai_rec(station_id: str, shift: str, staffing_cells: list[StaffingCell]) -> int:
    for cell in staffing_cells:
        if cell.station_id == station_id and cell.shift == shift:
            return cell.ai_recommended
    return 0


# ---------------------------------------------------------------------------
# Validation / deduplication
# ---------------------------------------------------------------------------


def validate_assignments(cells: list[CrewAssignmentCell]) -> list[CrewAssignmentCell]:
    """Ensure no employee_id appears in more than one cell (keep first)."""
    seen: set[str] = set()
    cleaned: list[CrewAssignmentCell] = []

    for cell in cells:
        unique_ids: list[str] = []
        for eid in cell.assigned_employee_ids:
            if eid not in seen:
                seen.add(eid)
                unique_ids.append(eid)
        cleaned.append(cell.model_copy(update={"assigned_employee_ids": unique_ids}))

    return cleaned


# ---------------------------------------------------------------------------
# Fallback (rules-based, no LLM)
# ---------------------------------------------------------------------------


def fallback_assignment(
    staffing_cells: list[StaffingCell],
    employees: pd.DataFrame,
    overrides: pd.DataFrame,
    target: Date,
    store_id: str,
) -> list[CrewAssignmentCell]:
    """Deterministic assignment: skill match + availability + lowest hourly rate."""
    dow = _dow(target)
    assigned_ids: set[str] = set()
    results: list[CrewAssignmentCell] = []

    sorted_cells = sorted(staffing_cells, key=lambda c: SHIFT_ORDER.get(c.shift, 99))

    for cell in sorted_cells:
        if employees.empty:
            results.append(CrewAssignmentCell(
                station_id=cell.station_id,
                shift=cell.shift,
                ai_recommended=cell.ai_recommended,
                assigned_employee_ids=[],
                reasoning="Fallback: no employee data available",
            ))
            continue

        emp = employees[employees["store_id"] == store_id].copy()

        def _has(col, needle):
            return col.map(lambda xs: needle in (xs or []))

        emp = emp[_has(emp["available_days"], dow)]
        emp = emp[_has(emp["available_shifts"], cell.shift)]
        emp = emp[_has(emp["skills"], cell.station_id)]

        if not overrides.empty:
            ov_today = overrides[
                (pd.to_datetime(overrides["date"]).dt.date == target)
                & (~overrides["available"].astype(bool))
            ]
            blocked = set(ov_today["employee_id"].astype(str))
            emp = emp[~emp["employee_id"].astype(str).isin(blocked)]

        emp = emp[~emp["employee_id"].astype(str).isin(assigned_ids)]
        emp = emp.sort_values("hourly_rate", ascending=True)

        chosen = emp.head(cell.ai_recommended)
        chosen_ids = chosen["employee_id"].astype(str).tolist()
        assigned_ids.update(chosen_ids)

        results.append(CrewAssignmentCell(
            station_id=cell.station_id,
            shift=cell.shift,
            ai_recommended=cell.ai_recommended,
            assigned_employee_ids=chosen_ids,
            reasoning="Fallback: assigned by skill match + lowest hourly rate",
        ))

    return results


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def assign_crew(
    data: DataBundle,
    store_id: str,
    target: Date,
    staffing_cells: list[StaffingCell],
) -> CrewAssignmentResponse:
    """Assign employees to staffing cells using Ollama (with rules fallback)."""
    started = time.perf_counter()
    dow = _dow(target)

    available = _available_crew_df(
        data.employees, store_id, dow, data.overrides, target,
    )

    context = build_context(data, store_id, target)
    context_factors = [f.label for f in context.factors]

    try:
        prompt = build_assignment_prompt(
            staffing_cells, available, store_id, target, data.overrides, context_factors,
        )
        raw = await call_ollama_assignment(prompt, store_id, target)
        cells, summary = parse_assignment_response(raw, staffing_cells)

        if not cells:
            logger.warning("Ollama returned no parseable cells — falling back to rules")
            raise ValueError("empty LLM response")

        cells = validate_assignments(cells)
        model_used = OLLAMA_MODEL

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, ValueError) as exc:
        logger.warning("Ollama crew-assignment failed (%s) — using fallback", exc)
        cells = fallback_assignment(
            staffing_cells, data.employees, data.overrides, target, store_id,
        )
        summary = "Assigned using rules-based fallback (Ollama unavailable)."
        model_used = "rules-fallback"

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return CrewAssignmentResponse(
        cells=cells,
        model_used=model_used,
        generation_ms=elapsed_ms,
        summary=summary,
    )
