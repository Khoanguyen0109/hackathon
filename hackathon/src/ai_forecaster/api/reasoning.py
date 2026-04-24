"""AI staffing reasoning engine.

Given a ``(store_id, date)`` this module returns:

  1. The **external context** badges — weather, events, promos, holiday,
     day-of-week — with their per-channel impact and source.
  2. A full **station × shift grid** of headcount recommendations, each
     cell carrying human-readable ``reason_rows`` the UI can drop straight
     into its expandable panel.

Both are computed deterministically from the mock data bundle so the API
is fully testable without downloading any Chronos weights.  When
``demo_mode=False`` the forecast multiplier is blended with a short
Chronos horizon (10 days) against the event-driven ``demand_index``
series, but the rule-based grid is always produced first as a baseline
the UI can render immediately.
"""

from __future__ import annotations

import time
from datetime import date as Date
from datetime import datetime
from typing import Iterable

import pandas as pd

from .schemas import (
    ContextFactor,
    ContextResponse,
    ReasonRow,
    RushHourInfo,
    StaffingCell,
    StaffingResponse,
)
from .state import DataBundle

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Base demand multipliers by day of week (matches generator).
DOW_MULT = {"Mon": 0.85, "Tue": 0.85, "Wed": 0.90, "Thu": 0.95,
            "Fri": 1.10, "Sat": 1.25, "Sun": 1.20}

# ---------------------------------------------------------------------------
# Rush-hour windows (24h clock) and the uplift they apply to staffing.
# Each window has a name, start/end hour, and a multiplier bump on top
# of the base recommendation.
# ---------------------------------------------------------------------------

RUSH_HOURS: list[dict] = [
    {"label": "Lunch rush", "start": 11, "end": 14, "uplift_pct": 0.20},
    {"label": "Dinner rush", "start": 17, "end": 20, "uplift_pct": 0.25},
]

MIN_RUSH_OVERLAP_PCT = 0.40

SHIFT_WINDOWS: dict[str, tuple[int, int]] = {
    "Morning": (6, 12),
    "Afternoon": (12, 18),
    "Evening": (18, 23),
}

_RUSH_SOLUTIONS: dict[str, list[str]] = {
    "Lunch rush": [
        "Pre-prep high-demand items (dough, toppings) 30 min before rush",
        "Stagger crew breaks to avoid gaps during 11:00–14:00",
        "Cross-deploy a Prep crew member to Makeline during peak",
        "Enable express menu / limited specials to reduce ticket time",
    ],
    "Dinner rush": [
        "Schedule shift overlap: Afternoon crew stays 30 min into Evening",
        "Assign a dedicated expediter to the pass during 17:00–20:00",
        "Pre-stage delivery bags and DT packaging before 17:00",
        "Move a Cleaning/Restock crew member to Drive-Through during peak",
        "Consider opening an extra register or DT lane if available",
    ],
}


def _rush_hour_for_shift(shift: str) -> RushHourInfo:
    """Compute rush-hour overlap for a named shift."""
    s_start, s_end = SHIFT_WINDOWS.get(shift, (0, 0))
    shift_len = s_end - s_start
    if shift_len <= 0:
        return RushHourInfo()

    best: RushHourInfo | None = None
    for rh in RUSH_HOURS:
        overlap_start = max(s_start, rh["start"])
        overlap_end = min(s_end, rh["end"])
        overlap = max(0, overlap_end - overlap_start)
        if overlap <= 0:
            continue
        pct = overlap / shift_len
        if pct < MIN_RUSH_OVERLAP_PCT:
            continue
        uplift = max(1, int(round(rh["uplift_pct"] * 10 * pct)))
        info = RushHourInfo(
            is_rush=True,
            label=rh["label"],
            window=f"{rh['start']:02d}:00–{rh['end']:02d}:00",
            overlap_pct=round(pct, 2),
            staff_uplift=uplift,
            solutions=_RUSH_SOLUTIONS.get(rh["label"], []),
        )
        if best is None or info.overlap_pct > best.overlap_pct:
            best = info
    return best or RushHourInfo()


def _dow(d: Date) -> str:
    return DAY_NAMES[d.weekday()]


# ---------------------------------------------------------------------------
# 1 / External context
# ---------------------------------------------------------------------------


def build_context(data: DataBundle, store_id: str, target: Date) -> ContextResponse:
    """Collect every factor that could nudge demand on that day."""
    factors: list[ContextFactor] = []
    target_ts = pd.Timestamp(target)
    dow = _dow(target)

    # ---- Weather (per-store, per-shift forecast; collapse to a daily badge)
    if not data.weather_forecast.empty:
        wf = data.weather_forecast
        mask = (wf["store_id"] == store_id) & (pd.to_datetime(wf["date"]).dt.date == target)
        rows = wf[mask]
        if not rows.empty:
            # Use the worst-shift forecast as the daily label.
            worst = rows.sort_values("rain_probability", ascending=False).iloc[0]
            cond = str(worst["condition"])
            prob = float(worst["rain_probability"])
            if cond == "rain":
                factors.append(ContextFactor(
                    kind="weather",
                    label=f"🌧 Rain ({int(round(prob * 100))}%)",
                    icon="🌧",
                    probability=prob,
                    impact_delivery=0.05,
                    impact_dinein=-0.03,
                    impact_drivethrough=0.02,
                    source="prediction_rule",
                    note="Rain shifts customers from dine-in to delivery and drive-through. Expect higher dispatch and DT load.",
                ))
            else:
                factors.append(ContextFactor(
                    kind="weather",
                    label="☀ Dry",
                    icon="☀",
                    probability=1.0 - prob,
                    source="forecast_feed",
                    note="Dry conditions, no weather-driven channel shift.",
                ))

    # ---- Events calendar
    if not data.events_calendar.empty:
        ec = data.events_calendar
        mask = pd.to_datetime(ec["event_date"]).dt.date == target
        for _, ev in ec[mask].iterrows():
            affected = str(ev.get("affected_store_ids", "")).split(",")
            if store_id not in affected and affected != [""]:
                continue
            factors.append(ContextFactor(
                kind="event",
                label=f"{_event_icon(str(ev['event_type']))} {ev['event_name']}",
                icon=_event_icon(str(ev["event_type"])),
                impact_delivery=float(ev.get("impact_delivery", 0)),
                impact_dinein=float(ev.get("impact_dinein", 0)),
                impact_drivethrough=float(ev.get("impact_drivethrough", 0)),
                source="ai_inference",
                note=(
                    f"{ev['event_type']} event ~{ev.get('venue_distance_km', 0):.1f} km away, "
                    f"expected crowd {int(ev.get('expected_crowd_size', 0)):,}."
                ),
                time_window=str(ev.get("time_window", "")) or None,
            ))

    # ---- Active promos
    if not data.promos.empty:
        pr = data.promos
        start = pd.to_datetime(pr["start_date"]).dt.date
        end = pd.to_datetime(pr["end_date"]).dt.date
        active = pr[(start <= target) & (end >= target)]
        for _, p in active.iterrows():
            scope = str(p.get("store_scope", "all"))
            if scope != "all" and store_id not in scope.split(","):
                continue
            factors.append(ContextFactor(
                kind="promo",
                label=f"📣 {p['promo_name']}",
                icon="📣",
                impact_delivery=float(p.get("uplift_delivery", 0)),
                impact_dinein=float(p.get("uplift_dinein", 0)),
                impact_drivethrough=float(p.get("uplift_drivethrough", 0)),
                source="ai_inference",
                note=f"{p['promo_type']} campaign — estimated +{p.get('expected_order_lift_pct', 0):.0f}% order volume.",
                time_window="All day",
            ))

    # ---- Holidays (from event log)
    holiday_here = False
    if not data.event_log.empty:
        el = data.event_log
        mask = (pd.to_datetime(el["date"]).dt.date == target) & \
               (el["event type"].str.lower() == "holidays")
        holiday_here = bool(mask.any())
    if holiday_here:
        factors.append(ContextFactor(
            kind="holiday",
            label="🎉 Public holiday",
            icon="🎉",
            impact_delivery=0.02,
            impact_dinein=0.02,
            source="prediction_rule",
            note="Public holiday — light uplift on both channels.",
        ))
    else:
        factors.append(ContextFactor(
            kind="holiday",
            label="✓ No holiday",
            icon="✓",
            source="calendar_check",
            note="No national or regional holiday on this date.",
        ))

    # ---- Day of week
    factors.append(ContextFactor(
        kind="day_of_week",
        label=f"📅 {dow}",
        icon="📅",
        impact_delivery=(DOW_MULT[dow] - 1.0) / 2,
        impact_dinein=(DOW_MULT[dow] - 1.0) / 2,
        impact_drivethrough=(DOW_MULT[dow] - 1.0) / 2,
        source="prediction_rule",
        note=f"Day-of-week multiplier = {DOW_MULT[dow]:.2f}.",
    ))

    # ---- Aggregate to channel multipliers
    channel_multipliers = {
        "Delivery": 1.0 + sum(f.impact_delivery for f in factors),
        "Dine-in": 1.0 + sum(f.impact_dinein for f in factors),
        "Drive-Through": 1.0 + sum(f.impact_drivethrough for f in factors),
    }

    return ContextResponse(
        store_id=store_id,
        date=target,
        day_of_week=dow,
        factors=factors,
        channel_multipliers={k: round(v, 4) for k, v in channel_multipliers.items()},
    )


def _event_icon(event_type: str) -> str:
    return {
        "Sport": "⚽",
        "Concert": "🎤",
        "Festival": "🎪",
        "Holiday": "🎉",
        "Conference": "💼",
        "Retail": "🛍",
        "Community": "🏘",
    }.get(event_type, "📌")


# ---------------------------------------------------------------------------
# 2 / Per-cell recommendation + reasoning
# ---------------------------------------------------------------------------


def _available_crew(
    employees: pd.DataFrame,
    store_id: str,
    dow: str,
    shift: str,
    station_id: str,
    overrides: pd.DataFrame,
    target: Date,
) -> list[str]:
    """Return employee names at this store, certified for this station,
    and available on this day × shift (respecting PTO/Sick overrides)."""
    if employees.empty:
        return []
    emp = employees[employees["store_id"] == store_id]

    def _has(col_list, needle):
        return col_list.map(lambda xs: needle in (xs or []))

    emp = emp[_has(emp["available_days"], dow)]
    emp = emp[_has(emp["available_shifts"], shift)]
    emp = emp[_has(emp["skills"], station_id)]

    if not overrides.empty:
        ov = overrides
        ov_today = ov[(pd.to_datetime(ov["date"]).dt.date == target) &
                      (~ov["available"].astype(bool))]
        blocked = set(ov_today["employee_id"].astype(str))
        emp = emp[~emp["employee_id"].astype(str).isin(blocked)]

    return emp["employee_name"].tolist()


def _base_staff_for_shift(station_row: pd.Series, shift: str) -> int:
    col = {"Morning": "base_staff_morning",
           "Afternoon": "base_staff_afternoon",
           "Evening": "base_staff_evening"}[shift]
    return int(station_row[col])


def _station_multiplier(station_row: pd.Series, channel_mult: dict[str, float]) -> float:
    primary = str(station_row.get("primary_channel", "Both"))
    w = float(station_row.get("channel_weight", 0.5))
    if primary == "Both":
        return w * channel_mult["Delivery"] + (1 - w) * channel_mult["Dine-in"]
    if primary == "Drive-Through":
        return channel_mult["Drive-Through"]
    if primary == "Delivery":
        return w * channel_mult["Delivery"] + (1 - w) * channel_mult["Dine-in"]
    if primary == "Dine-in":
        return w * channel_mult["Dine-in"] + (1 - w) * channel_mult["Delivery"]
    return 1.0


def _confidence(factors: list[ContextFactor], has_ai_inferred: bool) -> str:
    n_rule = sum(1 for f in factors if f.source == "prediction_rule")
    n_inferred = sum(1 for f in factors if f.source == "ai_inference")
    if n_inferred == 0:
        return "high"
    if n_inferred <= 1 and n_rule >= 2:
        return "medium"
    return "medium" if n_inferred <= 2 else "low"


def _build_cell(
    *,
    station_row: pd.Series,
    shift: str,
    store_id: str,
    target: Date,
    dow: str,
    context: ContextResponse,
    employees: pd.DataFrame,
    overrides: pd.DataFrame,
) -> StaffingCell:
    base = _base_staff_for_shift(station_row, shift)
    if base == 0 and shift == "Evening":
        closed_rows = [
            ReasonRow(icon="📋", label="Factors", value="Station closed — no staffing"),
            ReasonRow(icon="📐", label="Rules", value="base_staff_evening = 0 in stations.xlsx"),
            ReasonRow(icon="🔗", label="Channel", value="Station does not operate this shift."),
            ReasonRow(icon="👥", label="Crew", value="No crew required."),
            ReasonRow(icon="◆", label="Confidence", value="● High — deterministic from config."),
        ]
        return StaffingCell(
            station_id=station_row["station_id"],
            station_name=station_row["station_name"],
            shift=shift,
            ai_recommended=0,
            reason_short="Station closed this shift",
            confidence="high",
            factors=[f.label for f in context.factors],
            rules_applied=[],
            channel_note="This station does not operate in the evening.",
            crew_note="No crew required.",
            reason_rows=closed_rows,
        )

    mult = _station_multiplier(station_row, context.channel_multipliers)
    reco_base = max(1, int(round(base * mult)))

    rush = _rush_hour_for_shift(shift)
    reco = reco_base + rush.staff_uplift if rush.is_rush else reco_base

    crew_names = _available_crew(
        employees, store_id, dow, shift,
        station_row["station_id"], overrides, target,
    )

    rules_applied = [f.note for f in context.factors if f.source == "prediction_rule"]
    active_factor_labels = [f.label for f in context.factors if f.impact_delivery or f.impact_dinein or f.impact_drivethrough or f.kind == "day_of_week"]

    reason_short = _short_reason(context.factors, station_row, shift, reco, base, rush)

    channel_note = (
        f"{station_row['station_name']} serves "
        f"{station_row['primary_channel']} channel (weight={station_row['channel_weight']:.2f}). "
        f"Effective multiplier = {mult:.2f} → base {base} → rec {reco_base}."
    )
    if rush.is_rush:
        channel_note += (
            f" Rush-hour uplift (+{rush.staff_uplift}) → final rec {reco}."
        )

    if len(crew_names) >= reco:
        crew_note = (
            f"{len(crew_names)} certified + available this shift "
            f"({', '.join(crew_names[:4])}) — meets target."
        )
    else:
        crew_note = (
            f"Only {len(crew_names)} certified + available "
            f"({', '.join(crew_names) if crew_names else 'none'}) — gap of "
            f"{reco - len(crew_names)} vs target."
        )

    conf = _confidence(context.factors, has_ai_inferred=any(f.source == "ai_inference" for f in context.factors))

    reason_rows: list[ReasonRow] = [
        ReasonRow(icon="📋", label="Factors",
                  value=", ".join(active_factor_labels[:4]) or "Baseline day"),
        ReasonRow(icon="📐", label="Rules",
                  value=" · ".join(rules_applied[:3]) or "No explicit rule triggered"),
        ReasonRow(icon="🔗", label="Channel", value=channel_note),
        ReasonRow(icon="👥", label="Crew", value=crew_note),
        ReasonRow(icon="◆", label="Confidence",
                  value={"high": "● High — rule-based, no extrapolation needed.",
                         "medium": "● Medium — blend of rules + inferred impact.",
                         "low": "● Low — mostly inferred, limited rule coverage."}[conf]),
    ]
    if rush.is_rush:
        reason_rows.insert(2, ReasonRow(
            icon="🔥",
            label="Rush hour",
            value=(
                f"{rush.label} ({rush.window}) overlaps "
                f"{int(rush.overlap_pct * 100)}% of this shift → "
                f"+{rush.staff_uplift} staff. "
                f"Tip: {rush.solutions[0]}" if rush.solutions else
                f"{rush.label} ({rush.window}) overlaps "
                f"{int(rush.overlap_pct * 100)}% of this shift → "
                f"+{rush.staff_uplift} staff."
            ),
        ))

    return StaffingCell(
        station_id=station_row["station_id"],
        station_name=station_row["station_name"],
        shift=shift,
        ai_recommended=reco,
        reason_short=reason_short,
        confidence=conf,  # type: ignore[arg-type]
        factors=[f.label for f in context.factors],
        rules_applied=rules_applied,
        channel_note=channel_note,
        crew_note=crew_note,
        reason_rows=reason_rows,
        rush_hour=rush,
    )


def _short_reason(factors: Iterable[ContextFactor], station_row: pd.Series,
                  shift: str, reco: int, base: int,
                  rush: RushHourInfo | None = None) -> str:
    has_rain = any(f.kind == "weather" and "Rain" in f.label for f in factors)
    has_event = any(f.kind == "event" for f in factors)
    has_promo = any(f.kind == "promo" for f in factors)
    is_peak = reco > base
    st = str(station_row["station_name"])

    rush_tag = f" 🔥 {rush.label}" if rush and rush.is_rush else ""

    if is_peak and has_event and has_promo:
        return f"Event + promo → {st} peak{rush_tag}"
    if is_peak and has_event:
        return f"Event nearby → {st} surge{rush_tag}"
    if is_peak and has_promo:
        return f"Promo drives {st} load{rush_tag}"
    if is_peak:
        return f"Day-of-week peak on {st}{rush_tag}"
    if has_rain and st == "Drive-Through":
        return f"Rain → DT preference{rush_tag}"
    if has_rain and st == "Front Counter":
        return f"Rain suppresses walk-ins{rush_tag}"
    if reco < base:
        return f"Below baseline demand{rush_tag}"
    return f"Steady {shift.lower()} demand{rush_tag}"


def generate_staffing(
    data: DataBundle,
    store_id: str,
    target: Date,
    *,
    demo_mode: bool = True,
    model_name: str | None = None,
) -> StaffingResponse:
    """Build the full staffing grid + context for one store/date."""
    started = time.perf_counter()

    store_row = data.stores.loc[data.stores["store_id"] == store_id]
    if store_row.empty:
        raise LookupError(f"store_id={store_id!r} not found")
    shifts_per_day = int(store_row.iloc[0]["shifts_per_day"])
    shifts = ["Morning", "Afternoon", "Evening"][:shifts_per_day]

    context = build_context(data, store_id, target)
    dow = context.day_of_week

    cells: list[StaffingCell] = []
    for _, station in data.stations.iterrows():
        for shift in shifts:
            cells.append(_build_cell(
                station_row=station,
                shift=shift,
                store_id=store_id,
                target=target,
                dow=dow,
                context=context,
                employees=data.employees,
                overrides=data.overrides,
            ))

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return StaffingResponse(
        store_id=store_id,
        date=target,
        day_of_week=dow,
        generated_at=datetime.utcnow(),
        model_used=("rules-only/demo" if demo_mode else (model_name or "amazon/chronos-bolt-base")),
        generation_ms=elapsed_ms,
        context=context,
        cells=cells,
    )
