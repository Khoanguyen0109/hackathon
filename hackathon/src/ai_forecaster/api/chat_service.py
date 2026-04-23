"""AI chat service — Direct Context Injection with Ollama.

Builds a structured text context from the in-memory xlsx DataFrames,
sends it alongside the user's conversation to a local Ollama model,
and parses the response into a message + optional structured actions.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date as Date

import httpx
import pandas as pd

from .schemas import AssignedCell, ChatAction, ChatMessageIn, ChatResponse
from .state import DataBundle

logger = logging.getLogger(__name__)

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _dow(d: Date) -> str:
    return DAY_NAMES[d.weekday()]


# ---------------------------------------------------------------------------
# 1 / Build data context from DataFrames
# ---------------------------------------------------------------------------


def _df_to_table(df: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 40) -> str:
    """Convert a DataFrame slice to a compact text table."""
    if df.empty:
        return "(no data)"
    cols = columns or list(df.columns)
    cols = [c for c in cols if c in df.columns]
    subset = df[cols].head(max_rows)
    return subset.to_string(index=False)


def build_data_context(data: DataBundle, store_id: str, target: Date) -> str:
    """Extract and format relevant data slices for the LLM prompt."""
    dow = _dow(target)
    sections: list[str] = []

    # -- Available crew for this store
    if not data.employees.empty:
        emp = data.employees[data.employees["store_id"] == store_id].copy()
        if not emp.empty:
            emp_display = emp[["employee_id", "employee_name", "role", "hourly_rate",
                               "available_days", "available_shifts", "skills"]]
            sections.append(f"AVAILABLE CREW (store {store_id}):\n{_df_to_table(emp_display)}")
        else:
            sections.append(f"AVAILABLE CREW (store {store_id}): none found")

    # -- Stations
    if not data.stations.empty:
        st_cols = ["station_id", "station_name", "area", "positions",
                   "base_staff_morning", "base_staff_afternoon", "base_staff_evening",
                   "primary_channel", "channel_weight"]
        sections.append(f"STATIONS:\n{_df_to_table(data.stations, st_cols)}")

    # -- Past deployments (same day-of-week for this store, last 5)
    if not data.past_deployments.empty:
        pd_df = data.past_deployments
        mask = pd_df["store_id"] == store_id
        if "day_of_week" in pd_df.columns:
            mask = mask & (pd_df["day_of_week"] == dow)
        past = pd_df[mask].tail(5)
        if not past.empty:
            past_cols = [c for c in ["date", "shift", "station_id",
                                     "ai_recommended", "manager_assigned",
                                     "actual_staffed", "gap", "outcome",
                                     "demand_multiplier", "notes"] if c in past.columns]
            sections.append(f"PAST DEPLOYMENTS (same day-of-week, store {store_id}):\n{_df_to_table(past, past_cols)}")

    # -- Orders history (same day-of-week, last 5 per shift)
    if not data.orders_history.empty:
        oh = data.orders_history
        mask = oh["store_id"] == store_id
        if "day_of_week" in oh.columns:
            mask = mask & (oh["day_of_week"] == dow)
        recent = oh[mask].tail(15)
        if not recent.empty:
            oh_cols = [c for c in ["date", "shift", "channel", "order_count",
                                   "avg_order_size", "revenue"] if c in recent.columns]
            sections.append(f"ORDERS HISTORY (same day-of-week, store {store_id}):\n{_df_to_table(recent, oh_cols)}")

    # -- Weather for target date
    if not data.weather_forecast.empty:
        wf = data.weather_forecast
        mask = (wf["store_id"] == store_id) & (pd.to_datetime(wf["date"]).dt.date == target)
        weather = wf[mask]
        if not weather.empty:
            w_cols = [c for c in ["shift", "condition", "rain_probability",
                                  "temperature_c", "wind_kmh"] if c in weather.columns]
            sections.append(f"WEATHER FORECAST ({target}):\n{_df_to_table(weather, w_cols)}")

    # -- Events
    if not data.events_calendar.empty:
        ec = data.events_calendar
        mask = pd.to_datetime(ec["event_date"]).dt.date == target
        events = ec[mask]
        if not events.empty:
            e_cols = [c for c in ["event_name", "event_type", "time_window",
                                  "expected_crowd_size", "impact_delivery",
                                  "impact_dinein", "impact_drivethrough"] if c in events.columns]
            sections.append(f"EVENTS TODAY:\n{_df_to_table(events, e_cols)}")

    # -- Active promos
    if not data.promos.empty:
        pr = data.promos
        start = pd.to_datetime(pr["start_date"]).dt.date
        end = pd.to_datetime(pr["end_date"]).dt.date
        active = pr[(start <= target) & (end >= target)]
        if not active.empty:
            p_cols = [c for c in ["promo_name", "promo_type", "uplift_delivery",
                                  "uplift_dinein", "uplift_drivethrough",
                                  "expected_order_lift_pct"] if c in active.columns]
            sections.append(f"ACTIVE PROMOS:\n{_df_to_table(active, p_cols)}")

    return "\n\n".join(sections) if sections else "(no data available)"


# ---------------------------------------------------------------------------
# 2 / Build the system prompt
# ---------------------------------------------------------------------------

SYSTEM_TEMPLATE = """You are an AI staffing assistant for a pizza restaurant chain.
You help managers assign crew members to stations for each shift based on real data.

{data_context}

{assignment_context}

RULES FOR YOUR RESPONSES:
- Always ground your answers in the data above.
- When suggesting assignments, consider: employee skills (must match station_id), availability (available_days and available_shifts), hourly rate (prefer lower cost when skills match), and past deployment outcomes.
- If you recommend assignment changes, include a JSON block with actions.
- Format the JSON block exactly like this (inside triple backticks with json tag):
```json
[{{"type": "assign", "employee_id": "EMP_01", "employee_name": "John", "station_id": "ST_OVEN", "station_name": "Oven", "shift": "Morning", "reason": "Certified for Oven, available Morning, lowest hourly rate among qualified crew"}}]
```
- Valid action types: "assign", "unassign"
- Shifts must be exactly: "Morning", "Afternoon", or "Evening"
- Keep explanations concise but data-driven.
- If you don't have enough data to answer, say so honestly."""


def build_system_prompt(data_context: str, current_cells: list[AssignedCell]) -> str:
    """Assemble the full system prompt with data + current assignment state."""
    if current_cells:
        lines = ["CURRENT ASSIGNMENTS:"]
        for cell in current_cells:
            assigned = ", ".join(cell.assigned_employee_ids) if cell.assigned_employee_ids else "none"
            lines.append(
                f"  {cell.station_id} / {cell.shift}: "
                f"AI rec={cell.ai_recommended}, assigned=[{assigned}]"
            )
        assignment_context = "\n".join(lines)
    else:
        assignment_context = "CURRENT ASSIGNMENTS: No assignments made yet."

    return SYSTEM_TEMPLATE.format(
        data_context=data_context,
        assignment_context=assignment_context,
    )


# ---------------------------------------------------------------------------
# 3 / Call Ollama
# ---------------------------------------------------------------------------


async def call_ollama(
    system_prompt: str,
    conversation: list[ChatMessageIn],
    user_message: str,
) -> str:
    """Send messages to Ollama and return the assistant's reply text."""
    messages = [{"role": "system", "content": system_prompt}]

    for msg in conversation:
        role = "assistant" if msg.role == "ai" else msg.role
        if role == "system":
            continue
        messages.append({"role": role, "content": msg.content})

    messages.append({"role": "user", "content": user_message})

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
# 4 / Parse response into message + actions
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```json\s*\n?(.*?)```", re.DOTALL)


def parse_response(raw: str) -> ChatResponse:
    """Split the LLM output into a display message and structured actions."""
    actions: list[ChatAction] = []

    json_match = _JSON_BLOCK_RE.search(raw)
    if json_match:
        try:
            raw_actions = json.loads(json_match.group(1).strip())
            if isinstance(raw_actions, list):
                for item in raw_actions:
                    try:
                        actions.append(ChatAction(**item))
                    except Exception:
                        logger.warning("Skipping malformed action: %s", item)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON actions from LLM response")

    display = _JSON_BLOCK_RE.sub("", raw).strip()
    if not display:
        if actions:
            display = "Here are my suggested assignments based on crew skills, availability, and past performance:"
        else:
            display = raw

    return ChatResponse(message=display, actions=actions)
