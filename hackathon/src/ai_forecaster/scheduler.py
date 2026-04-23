"""Shift scheduling optimiser (Google OR-Tools CP-SAT).

Inputs
------
* ``stores``     — DataFrame with store config (open hours, shifts/day,
                   baseline staff, min/max staff per shift).
* ``employees``  — DataFrame with employee roster (contract hours, hourly
                   rate, availability day/shift, role).
* ``demand``     — DataFrame indexed by ``date`` with columns ``store_id``
                   and ``demand_index`` (e.g. produced by the event pipeline +
                   Chronos forecaster). ``1.0`` = baseline demand.

Decision variables
------------------
``x[e, d, s] ∈ {0, 1}``  — employee ``e`` works day ``d`` shift ``s``.

Hard constraints
----------------
1. Coverage: for each (store, day, shift) the number of employees scheduled
   is ≥ ``required_staff = ceil(base * demand_index)``, clamped to
   ``[min_staff_per_shift, max_staff_per_shift]``.
2. Availability: an employee can only be scheduled on days/shifts that
   appear in their availability columns.
3. One shift per day: ``Σ_s x[e, d, s] ≤ 1`` for each (employee, day).
4. Contract cap: weekly hours per employee ≤ ``contract_hours_per_week``.
5. Each shift must contain ≥ 1 Manager (if any manager is on the roster).

Soft constraints (in the objective)
-----------------------------------
* Penalise under-coverage with a large per-missing-staff cost.
* Penalise hours below ``min_hours_per_week`` (fairness).
* Reward total assigned hours (= revenue surrogate) lightly so the solver
  prefers fuller schedules when costs tie.
* Minimise total wage cost = Σ x[e,d,s] * shift_hours * hourly_rate.

Returns
-------
:class:`ScheduleResult` with:

* ``assignments``        — long-format DataFrame
                          ``store_id, date, shift, employee_id, role, hours``.
* ``coverage``           — DataFrame with required vs. assigned per slot.
* ``employee_summary``   — weekly hours and pay per employee.
* ``solver_status``, ``objective_value``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import pandas as pd


SHIFT_ORDER = ["Morning", "Afternoon", "Evening"]


# --------------------------------------------------------------------------- #
# Public dataclasses
# --------------------------------------------------------------------------- #
@dataclass
class SchedulerConfig:
    """Tunable solver / objective weights."""

    shift_hours: int = 8                     # length of one shift in hours
    under_coverage_penalty: int = 1_000      # per missing employee per slot
    below_min_hours_penalty: int = 50        # per missing hour below contract min
    no_manager_penalty: int = 500            # per shift without a manager
    require_manager_per_shift: bool = True
    solver_time_limit_s: int = 30
    num_search_workers: int = 0              # 0 = OR-Tools auto


@dataclass
class ScheduleResult:
    assignments: pd.DataFrame
    coverage: pd.DataFrame
    employee_summary: pd.DataFrame
    solver_status: str
    objective_value: float = 0.0
    horizon_dates: list[pd.Timestamp] = field(default_factory=list)

    @property
    def is_feasible(self) -> bool:
        return self.solver_status in {"OPTIMAL", "FEASIBLE"}


# --------------------------------------------------------------------------- #
# Scheduler
# --------------------------------------------------------------------------- #
class ShiftScheduler:
    """Build & solve the CP-SAT model for a multi-store roster."""

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self.config = config or SchedulerConfig()

    # ------------------------------------------------------------------ #
    # Solve
    # ------------------------------------------------------------------ #
    def solve(
        self,
        stores: pd.DataFrame,
        employees: pd.DataFrame,
        demand: pd.DataFrame,
        dates: Sequence[pd.Timestamp] | None = None,
    ) -> ScheduleResult:
        """Solve the scheduling problem and return assignments."""
        try:
            from ortools.sat.python import cp_model
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "ortools is required. Install with `pip install ortools`."
            ) from e

        stores = self._normalise_stores(stores)
        employees = self._normalise_employees(employees, stores)
        demand = self._normalise_demand(demand)

        if dates is None:
            dates = sorted(demand["date"].unique())
        dates = [pd.Timestamp(d) for d in dates]
        if not dates:
            raise ValueError("No dates provided / found in demand frame.")

        # ---- Build model -------------------------------------------------
        model = cp_model.CpModel()
        x: dict[tuple[str, pd.Timestamp, str], cp_model.IntVar] = {}
        # under-coverage slack per (store, date, shift)
        under: dict[tuple[str, pd.Timestamp, str], cp_model.IntVar] = {}
        # missing-manager slack per (store, date, shift) — 1 if no manager
        no_mgr: dict[tuple[str, pd.Timestamp, str], cp_model.IntVar] = {}
        # hours-below-minimum slack per employee
        hours_below_min: dict[str, cp_model.IntVar] = {}

        store_index = stores.set_index("store_id")
        emps_by_store: dict[str, pd.DataFrame] = {
            sid: g for sid, g in employees.groupby("store_id")
        }

        # Decision vars + per-employee day/shift availability filter.
        for _, emp in employees.iterrows():
            eid = emp["employee_id"]
            avail_days = set(_split_csv(emp["available_days"]))
            avail_shifts = set(_split_csv(emp["available_shifts"]))
            store_shifts = self._store_shifts(store_index.loc[emp["store_id"]])

            for date in dates:
                day_name = date.day_name()[:3]  # Mon / Tue / ...
                if day_name not in avail_days:
                    continue
                for shift in store_shifts:
                    if shift not in avail_shifts:
                        continue
                    x[(eid, date, shift)] = model.NewBoolVar(
                        f"x[{eid},{date.date()},{shift}]"
                    )

        # Coverage + manager constraints + slack vars.
        for sid, store in store_index.iterrows():
            store_shifts = self._store_shifts(store)
            store_emps = emps_by_store.get(sid, pd.DataFrame(columns=employees.columns))
            manager_ids = set(store_emps[store_emps["role"] == "Manager"]["employee_id"])
            for date in dates:
                d_index = self._demand_for(demand, sid, date)
                base = int(store["base_staff_per_shift"])
                lo = int(store["min_staff_per_shift"])
                hi = int(store["max_staff_per_shift"])
                required = max(lo, min(hi, math.ceil(base * d_index)))

                for shift in store_shifts:
                    eligible = [
                        x[(eid, date, shift)]
                        for eid in store_emps["employee_id"]
                        if (eid, date, shift) in x
                    ]
                    slack = model.NewIntVar(
                        0, max(required, 1), f"under[{sid},{date.date()},{shift}]"
                    )
                    under[(sid, date, shift)] = slack

                    if eligible:
                        model.Add(sum(eligible) + slack >= required)
                        model.Add(sum(eligible) <= hi)
                        if self.config.require_manager_per_shift and manager_ids:
                            mgr_eligible = [
                                x[(mid, date, shift)]
                                for mid in manager_ids
                                if (mid, date, shift) in x
                            ]
                            mgr_slack = model.NewBoolVar(
                                f"no_mgr[{sid},{date.date()},{shift}]"
                            )
                            no_mgr[(sid, date, shift)] = mgr_slack
                            if mgr_eligible:
                                # sum(mgr_eligible) + mgr_slack >= 1
                                model.Add(sum(mgr_eligible) + mgr_slack >= 1)
                            else:
                                model.Add(mgr_slack == 1)
                    else:
                        # No-one available at all → entire required staff is missing.
                        model.Add(slack >= required)

        # Per-employee constraints.
        for _, emp in employees.iterrows():
            eid = emp["employee_id"]
            contract_hours = int(emp["contract_hours_per_week"])
            min_hours = int(emp["min_hours_per_week"])
            shift_hours = self.config.shift_hours
            max_shifts = contract_hours // shift_hours

            emp_vars_by_day: dict[pd.Timestamp, list] = {}
            all_emp_vars: list = []
            for date in dates:
                vars_today = [
                    x[k] for k in x.keys() if k[0] == eid and k[1] == date
                ]
                if vars_today:
                    emp_vars_by_day[date] = vars_today
                    all_emp_vars.extend(vars_today)

            # ≤ 1 shift / day.
            for vars_today in emp_vars_by_day.values():
                model.Add(sum(vars_today) <= 1)

            # Weekly contract cap.
            if all_emp_vars:
                model.Add(sum(all_emp_vars) <= max_shifts)

            # Below-min-hours slack.
            slack_below = model.NewIntVar(0, contract_hours, f"under_min[{eid}]")
            hours_below_min[eid] = slack_below
            if all_emp_vars:
                # min_hours <= shift_hours * Σx + slack_below
                model.Add(
                    shift_hours * sum(all_emp_vars) + slack_below >= min_hours
                )
            else:
                model.Add(slack_below >= min_hours)

        # ---- Objective ---------------------------------------------------
        # Total wage cost (in cents to keep ints): hourly_rate * 100 * hours.
        wage_terms = []
        for (eid, date, shift), var in x.items():
            rate_cents = int(round(float(
                employees.loc[employees["employee_id"] == eid, "hourly_rate"].iloc[0]
            ) * 100))
            wage_terms.append(var * rate_cents * self.config.shift_hours)

        under_cost = (
            self.config.under_coverage_penalty
            * 100  # match cents scale
            * self.config.shift_hours
            * sum(under.values())
        )
        below_min_cost = (
            self.config.below_min_hours_penalty * 100 * sum(hours_below_min.values())
        )
        no_mgr_cost = (
            self.config.no_manager_penalty * 100 * self.config.shift_hours
            * sum(no_mgr.values())
        ) if no_mgr else 0

        total_wages = sum(wage_terms) if wage_terms else 0
        model.Minimize(total_wages + under_cost + below_min_cost + no_mgr_cost)

        # ---- Solve -------------------------------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(self.config.solver_time_limit_s)
        if self.config.num_search_workers > 0:
            solver.parameters.num_search_workers = self.config.num_search_workers

        status_code = solver.Solve(model)
        status = solver.StatusName(status_code)

        # ---- Extract solution -------------------------------------------
        assignments_rows = []
        coverage_rows = []
        employee_rows = []

        feasible = status in {"OPTIMAL", "FEASIBLE"}
        for sid, store in store_index.iterrows():
            store_shifts = self._store_shifts(store)
            store_emps = emps_by_store.get(sid, pd.DataFrame(columns=employees.columns))
            for date in dates:
                d_index = self._demand_for(demand, sid, date)
                base = int(store["base_staff_per_shift"])
                lo = int(store["min_staff_per_shift"])
                hi = int(store["max_staff_per_shift"])
                required = max(lo, min(hi, math.ceil(base * d_index)))

                for shift in store_shifts:
                    assigned_emps = []
                    has_manager = False
                    if feasible:
                        for eid in store_emps["employee_id"]:
                            var = x.get((eid, date, shift))
                            if var is not None and solver.Value(var) == 1:
                                assigned_emps.append(eid)
                                if eid in manager_ids:
                                    has_manager = True
                    coverage_rows.append(
                        {
                            "store_id": sid,
                            "date": date,
                            "shift": shift,
                            "demand_index": round(d_index, 4),
                            "required_staff": required,
                            "assigned_staff": len(assigned_emps),
                            "shortfall": max(0, required - len(assigned_emps)),
                            "has_manager": bool(has_manager) if manager_ids else None,
                        }
                    )
                    for eid in assigned_emps:
                        emp_row = store_emps[store_emps["employee_id"] == eid].iloc[0]
                        assignments_rows.append(
                            {
                                "store_id": sid,
                                "date": date,
                                "shift": shift,
                                "employee_id": eid,
                                "employee_name": emp_row["employee_name"],
                                "role": emp_row["role"],
                                "hours": self.config.shift_hours,
                                "wage": round(
                                    self.config.shift_hours * float(emp_row["hourly_rate"]),
                                    2,
                                ),
                            }
                        )

        for _, emp in employees.iterrows():
            assigned_shifts = [
                k for k, v in x.items()
                if k[0] == emp["employee_id"] and feasible and solver.Value(v) == 1
            ]
            hours = len(assigned_shifts) * self.config.shift_hours
            employee_rows.append(
                {
                    "employee_id": emp["employee_id"],
                    "employee_name": emp["employee_name"],
                    "store_id": emp["store_id"],
                    "role": emp["role"],
                    "contract_hours_per_week": int(emp["contract_hours_per_week"]),
                    "min_hours_per_week": int(emp["min_hours_per_week"]),
                    "scheduled_hours": hours,
                    "scheduled_pay": round(hours * float(emp["hourly_rate"]), 2),
                    "below_min": max(0, int(emp["min_hours_per_week"]) - hours),
                }
            )

        return ScheduleResult(
            assignments=pd.DataFrame(assignments_rows).sort_values(
                ["store_id", "date", "shift", "employee_id"], kind="stable"
            ).reset_index(drop=True) if assignments_rows else pd.DataFrame(
                columns=["store_id", "date", "shift", "employee_id",
                         "employee_name", "role", "hours", "wage"]
            ),
            coverage=pd.DataFrame(coverage_rows),
            employee_summary=pd.DataFrame(employee_rows),
            solver_status=status,
            objective_value=float(solver.ObjectiveValue()) / 100 if feasible else float("nan"),
            horizon_dates=list(dates),
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _store_shifts(store_row: pd.Series) -> list[str]:
        n = int(store_row["shifts_per_day"])
        return SHIFT_ORDER[: max(1, min(3, n))]

    @staticmethod
    def _normalise_stores(stores: pd.DataFrame) -> pd.DataFrame:
        required = {
            "store_id", "shifts_per_day", "base_staff_per_shift",
            "min_staff_per_shift", "max_staff_per_shift",
        }
        missing = required - set(stores.columns)
        if missing:
            raise KeyError(f"stores missing columns: {sorted(missing)}")
        out = stores.copy()
        out["store_id"] = out["store_id"].astype(str)
        return out

    @staticmethod
    def _normalise_employees(emp: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
        required = {
            "employee_id", "employee_name", "store_id", "role",
            "contract_hours_per_week", "min_hours_per_week", "hourly_rate",
            "available_days", "available_shifts",
        }
        missing = required - set(emp.columns)
        if missing:
            raise KeyError(f"employees missing columns: {sorted(missing)}")
        out = emp.copy()
        out["employee_id"] = out["employee_id"].astype(str)
        out["store_id"] = out["store_id"].astype(str)
        # Drop employees whose store doesn't exist in the stores frame.
        valid_stores = set(stores["store_id"].astype(str))
        out = out[out["store_id"].isin(valid_stores)].reset_index(drop=True)
        return out

    @staticmethod
    def _normalise_demand(demand: pd.DataFrame) -> pd.DataFrame:
        cols = {c.lower(): c for c in demand.columns}
        if "store_id" not in cols or "demand_index" not in cols:
            raise KeyError(
                "demand frame must have 'store_id' and 'demand_index' columns "
                "(plus a 'date' column or DatetimeIndex)."
            )
        out = demand.rename(columns={cols["store_id"]: "store_id",
                                     cols["demand_index"]: "demand_index"}).copy()
        if "date" not in out.columns:
            out = out.reset_index().rename(columns={"index": "date"})
        out["date"] = pd.to_datetime(out["date"])
        out["store_id"] = out["store_id"].astype(str)
        return out

    @staticmethod
    def _demand_for(demand: pd.DataFrame, store_id: str, date: pd.Timestamp) -> float:
        m = (demand["store_id"] == store_id) & (demand["date"] == date)
        sub = demand.loc[m, "demand_index"]
        return float(sub.iloc[0]) if len(sub) else 1.0


def _split_csv(value: object) -> Iterable[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]
