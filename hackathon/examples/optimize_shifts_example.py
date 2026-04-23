"""End-to-end demo: events + rules + stores + employees → optimal shift roster.

Designed to run on Apple Silicon (Mac M1/M2/M3 with ≥16 GB RAM):

* Forecasting:  ``amazon/chronos-bolt-base`` on the ``mps`` device.
* Optimisation: Google OR-Tools CP-SAT (CPU, native ARM64).

Run::

    python examples/generate_store_employee_data.py
    python examples/optimize_shifts_example.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_forecaster import (
    ChronosForecastModel,
    Forecaster,
    SchedulerConfig,
    optimise_shifts,
    write_schedule_excel,
)

HERE = Path(__file__).resolve().parent
EVENTS = HERE / "simulated_event_data_and_rules.xlsx"
STORES = HERE / "stores.xlsx"
EMPLOYEES = HERE / "employees.xlsx"
OUT = HERE / "outputs" / "shift_schedule.xlsx"

# Mac M1 32GB recommended config: Chronos-Bolt on MPS for fast forecasting.
MODEL_NAME = "amazon/chronos-bolt-base"
DEVICE = "mps"

# Schedule the first week of February 2026 (covered by the event log,
# so no extrapolation is required).
START_DATE = "2026-02-02"
HORIZON_DAYS = 7
STORES_TO_USE = ["S0001", "S0002", "S0003"]   # subset to keep the demo quick


def main() -> None:
    for p in (EVENTS, STORES, EMPLOYEES):
        if not p.exists():
            raise SystemExit(
                f"Missing input: {p}\n"
                "Generate mock store/employee data first:\n"
                "    python examples/generate_store_employee_data.py"
            )

    print(f"Loading forecast model {MODEL_NAME} on {DEVICE} ...")
    model = ChronosForecastModel(model_name=MODEL_NAME, device=DEVICE)
    forecaster = Forecaster(model=model, num_samples=50)

    config = SchedulerConfig(
        shift_hours=8,
        solver_time_limit_s=20,
        require_manager_per_shift=True,
    )

    print(
        f"Optimising shifts for {len(STORES_TO_USE)} stores · "
        f"{HORIZON_DAYS} days from {START_DATE} ..."
    )
    result = optimise_shifts(
        events_path=EVENTS,
        stores_path=STORES,
        employees_path=EMPLOYEES,
        start_date=START_DATE,
        horizon_days=HORIZON_DAYS,
        config=config,
        forecaster=forecaster,
        stores_to_use=STORES_TO_USE,
    )

    sched = result.schedule
    print(f"\nSolver status      : {sched.solver_status}")
    print(f"Total wage cost    : {sched.objective_value:,.2f}")
    print(f"Total assignments  : {len(sched.assignments)}")
    print(f"Employees used     : "
          f"{sched.assignments['employee_id'].nunique() if not sched.assignments.empty else 0}")
    print(f"Coverage shortfall : {int(sched.coverage['shortfall'].sum())} slots")
    print(f"Below-min hours    : {int(sched.employee_summary['below_min'].sum())} h")

    out = write_schedule_excel(result, OUT)
    print(f"\nWritten: {out}")

    # Show first few assignments inline.
    print("\nFirst 10 assignments:")
    with pd.option_context("display.max_rows", 10, "display.width", 120):
        print(sched.assignments.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
