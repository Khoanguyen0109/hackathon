"""End-to-end orchestration: events.xlsx + Chronos → demand → optimal shifts.

This is the glue that takes:

* the **event log + rules** workbook (e.g. ``simulated_event_data_and_rules.xlsx``),
* a **stores** workbook,
* an **employees** workbook,

runs the Chronos foundation model to forecast a daily ``demand_index``
per ``(store, channel)``, averages the channels into one demand signal per
``(store, day)``, and feeds it into the OR-Tools ``ShiftScheduler`` to
produce an optimal weekly roster.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from .event_pipeline import build_demand_index_series, load_event_workbook
from .scheduler import ScheduleResult, SchedulerConfig, ShiftScheduler


@dataclass
class SchedulingPipelineResult:
    schedule: ScheduleResult
    demand: pd.DataFrame                # store_id, date, demand_index
    forecast_window: tuple[pd.Timestamp, pd.Timestamp]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def build_demand_frame_from_events(
    events_path: str | Path,
    start_date: str | pd.Timestamp | None = None,
    horizon_days: int = 7,
    forecaster=None,                       # optional ai_forecaster.Forecaster
    forecast_horizon: int = 30,
) -> pd.DataFrame:
    """Return a ``store_id, date, demand_index`` frame for ``horizon_days``.

    * If the requested window is already covered by the event log, deltas are
      taken straight from the rules join (no model needed → fast & exact).
    * Otherwise the Chronos forecaster is invoked to extend each
      ``(store, channel)`` series and the future portion is averaged across
      channels.
    """
    data = load_event_workbook(events_path)
    series_list = build_demand_index_series(data)

    # Wide frame: index = date, columns = "<store>|<channel>"
    wide = pd.concat({s.name: s.values for s in series_list}, axis=1)
    history_end = wide.index.max()

    if start_date is None:
        start_date = history_end + pd.Timedelta(days=1)
    start_date = pd.Timestamp(start_date)
    end_date = start_date + pd.Timedelta(days=horizon_days - 1)

    # Extend with Chronos if the requested window goes beyond the history.
    if end_date > history_end and forecaster is not None:
        results = forecaster.forecast_many(series_list, horizon=forecast_horizon)
        future_cols = {r.series_name: r.median for r in results}
        future_df = pd.concat(future_cols, axis=1)
        wide = pd.concat([wide, future_df]).sort_index()
        wide = wide[~wide.index.duplicated(keep="first")]
    elif end_date > history_end:
        # No forecaster supplied — clamp to history end.
        end_date = history_end

    window = wide.loc[start_date:end_date]
    if window.empty:
        raise ValueError(
            f"No demand data in window {start_date.date()} → {end_date.date()}. "
            "Pass a forecaster or pick dates inside the event log."
        )

    # Average the per-channel demand into a single signal per (store, day).
    long = window.stack().rename("demand_index").reset_index()
    long.columns = ["date", "series", "demand_index"]
    long[["store_id", "channel"]] = long["series"].str.split("|", n=1, expand=True)
    out = (
        long.groupby(["store_id", "date"], as_index=False)["demand_index"].mean()
    )
    return out


def optimise_shifts(
    events_path: str | Path,
    stores_path: str | Path,
    employees_path: str | Path,
    start_date: str | pd.Timestamp | None = None,
    horizon_days: int = 7,
    config: SchedulerConfig | None = None,
    forecaster=None,
    stores_to_use: Sequence[str] | None = None,
) -> SchedulingPipelineResult:
    """Top-level convenience: read all three files, return optimal schedule."""
    stores = pd.read_excel(stores_path)
    employees = pd.read_excel(employees_path)

    if stores_to_use:
        stores = stores[stores["store_id"].isin(stores_to_use)].reset_index(drop=True)
        employees = employees[employees["store_id"].isin(stores_to_use)].reset_index(drop=True)

    demand = build_demand_frame_from_events(
        events_path,
        start_date=start_date,
        horizon_days=horizon_days,
        forecaster=forecaster,
    )
    if stores_to_use:
        demand = demand[demand["store_id"].isin(stores_to_use)].reset_index(drop=True)

    scheduler = ShiftScheduler(config=config)
    schedule = scheduler.solve(stores=stores, employees=employees, demand=demand)

    return SchedulingPipelineResult(
        schedule=schedule,
        demand=demand,
        forecast_window=(demand["date"].min(), demand["date"].max()),
    )


# --------------------------------------------------------------------------- #
# Excel export
# --------------------------------------------------------------------------- #
def write_schedule_excel(result: SchedulingPipelineResult, out_path: str | Path) -> Path:
    """Write the schedule + coverage + employee summary to a single workbook."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sched = result.schedule

    # Pretty wide pivot: rows = (store, date, shift), cols = employee assigned.
    if not sched.assignments.empty:
        wide = (
            sched.assignments
            .assign(slot=lambda d: d["date"].dt.strftime("%Y-%m-%d") + " " + d["shift"])
            .groupby(["store_id", "slot"])["employee_name"]
            .agg(lambda s: ", ".join(sorted(s)))
            .unstack("slot")
            .fillna("")
            .sort_index()
        )
    else:
        wide = pd.DataFrame()

    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        sched.assignments.to_excel(w, sheet_name="assignments", index=False)
        sched.coverage.to_excel(w, sheet_name="coverage", index=False)
        sched.employee_summary.to_excel(w, sheet_name="employee_summary", index=False)
        if not wide.empty:
            wide.to_excel(w, sheet_name="schedule_wide")
        result.demand.to_excel(w, sheet_name="demand", index=False)

        meta = pd.DataFrame(
            {
                "key": [
                    "solver_status",
                    "objective_value (currency)",
                    "shortfall_total",
                    "below_min_total",
                    "horizon_start",
                    "horizon_end",
                    "n_assignments",
                    "n_employees_used",
                ],
                "value": [
                    sched.solver_status,
                    f"{sched.objective_value:.2f}",
                    int(sched.coverage["shortfall"].sum()) if not sched.coverage.empty else 0,
                    int(sched.employee_summary["below_min"].sum())
                        if not sched.employee_summary.empty else 0,
                    str(result.forecast_window[0].date()),
                    str(result.forecast_window[1].date()),
                    len(sched.assignments),
                    sched.assignments["employee_id"].nunique() if not sched.assignments.empty else 0,
                ],
            }
        )
        meta.to_excel(w, sheet_name="_summary", index=False)

    return out_path
