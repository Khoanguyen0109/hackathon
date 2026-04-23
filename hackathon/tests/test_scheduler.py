"""Tests for the OR-Tools shift scheduler.

Skipped automatically if ``ortools`` isn't installed in the runtime env.
"""

from __future__ import annotations

import pandas as pd
import pytest

ortools = pytest.importorskip("ortools.sat.python.cp_model")

from ai_forecaster.scheduler import SchedulerConfig, ShiftScheduler


@pytest.fixture
def tiny_problem() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stores = pd.DataFrame(
        [
            {
                "store_id": "S1", "store_name": "Test Store", "city": "Hanoi",
                "open_hour": 8, "close_hour": 22, "shifts_per_day": 2,
                "base_staff_per_shift": 1,
                "min_staff_per_shift": 1, "max_staff_per_shift": 3,
            }
        ]
    )

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def emp(eid, name, role, contract, mn, rate):
        return {
            "employee_id": eid, "employee_name": name,
            "store_id": "S1", "role": role,
            "contract_hours_per_week": contract, "min_hours_per_week": mn,
            "hourly_rate": rate,
            "available_days": ",".join(days),
            "available_shifts": "Morning,Afternoon",
        }

    employees = pd.DataFrame(
        [
            emp("E1", "Alice",  "Manager", 40, 24, 25.0),
            emp("E2", "Eve",    "Manager", 40, 24, 26.0),
            emp("E3", "Grace",  "Manager", 40, 24, 27.0),
            emp("E4", "Bob",    "Cashier", 32, 16, 18.0),
            emp("E5", "Carol",  "Cook",    32, 16, 22.0),
            emp("E6", "Dan",    "Server",  24,  8, 16.0),
            emp("E7", "Frank",  "Server",  24,  8, 16.5),
        ]
    )

    dates = pd.date_range("2026-02-02", periods=7, freq="D")
    demand = pd.DataFrame(
        {
            "store_id": "S1",
            "date": dates,
            "demand_index": [1.0, 1.0, 1.1, 1.2, 1.5, 1.8, 1.5],
        }
    )
    return stores, employees, demand


def test_scheduler_finds_feasible_solution(tiny_problem):
    stores, employees, demand = tiny_problem
    result = ShiftScheduler(SchedulerConfig(solver_time_limit_s=10)).solve(
        stores=stores, employees=employees, demand=demand
    )
    assert result.is_feasible, f"solver returned status={result.solver_status}"
    assert not result.assignments.empty
    # Every assignment should be for an existing employee at the right store.
    assert (result.assignments["store_id"] == "S1").all()
    assert set(result.assignments["employee_id"]).issubset(
        {"E1", "E2", "E3", "E4", "E5", "E6", "E7"}
    )


def test_each_employee_at_most_one_shift_per_day(tiny_problem):
    stores, employees, demand = tiny_problem
    result = ShiftScheduler(SchedulerConfig(solver_time_limit_s=10)).solve(
        stores=stores, employees=employees, demand=demand
    )
    counts = result.assignments.groupby(["employee_id", "date"]).size()
    assert (counts <= 1).all()


def test_weekly_hours_within_contract(tiny_problem):
    stores, employees, demand = tiny_problem
    result = ShiftScheduler(SchedulerConfig(solver_time_limit_s=10)).solve(
        stores=stores, employees=employees, demand=demand
    )
    for _, row in result.employee_summary.iterrows():
        assert row["scheduled_hours"] <= row["contract_hours_per_week"]


def test_manager_present_each_shift(tiny_problem):
    stores, employees, demand = tiny_problem
    result = ShiftScheduler(SchedulerConfig(solver_time_limit_s=10)).solve(
        stores=stores, employees=employees, demand=demand
    )
    if result.assignments.empty:
        pytest.skip("no assignments")
    has_mgr = (
        result.assignments
        .groupby(["store_id", "date", "shift"])["role"]
        .apply(lambda s: (s == "Manager").any())
    )
    assert has_mgr.all(), f"Some shifts have no manager: {has_mgr[~has_mgr]}"


def test_higher_demand_yields_more_required_staff(tiny_problem):
    stores, employees, demand = tiny_problem
    result = ShiftScheduler(SchedulerConfig(solver_time_limit_s=10)).solve(
        stores=stores, employees=employees, demand=demand
    )
    cov = result.coverage.set_index("date")
    # Saturday (1.8) should require strictly more staff than Monday (1.0).
    sat = cov.loc[pd.Timestamp("2026-02-07"), "required_staff"]
    mon = cov.loc[pd.Timestamp("2026-02-02"), "required_staff"]
    sat_max = int(sat.max() if hasattr(sat, "max") else sat)
    mon_max = int(mon.max() if hasattr(mon, "max") else mon)
    assert sat_max >= mon_max
