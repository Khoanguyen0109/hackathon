"""Generate realistic mock data for stores and their employees.

Outputs (next to this script)::

    examples/stores.xlsx
    examples/employees.xlsx

Schemas
-------
stores.xlsx — one row per store, columns:

    store_id, store_name, city, open_hour, close_hour,
    shifts_per_day,             # 2 or 3 (Morning/Afternoon[/Evening])
    base_staff_per_shift,       # baseline headcount per shift on a normal day
    min_staff_per_shift,        # hard lower bound (safety / cover lone work)
    max_staff_per_shift         # hard upper bound (capacity)

employees.xlsx — one row per employee, columns:

    employee_id, employee_name, store_id, role,
    contract_hours_per_week,    # max hours
    min_hours_per_week,         # soft minimum (fairness)
    hourly_rate,                # used in the cost objective
    available_days,             # comma list e.g. "Mon,Tue,Wed,Thu,Fri"
    available_shifts            # comma list of {Morning, Afternoon, Evening}

The mock data is intentionally a bit messy (varying contract hours, partial
availability, mixed roles) so the OR-Tools scheduler has something
non-trivial to solve.
"""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

OUT_STORES = Path(__file__).resolve().parent / "stores.xlsx"
OUT_EMPLOYEES = Path(__file__).resolve().parent / "employees.xlsx"

ALL_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ALL_SHIFTS = ["Morning", "Afternoon", "Evening"]
ROLES = ["Manager", "Cashier", "Cook", "Server", "Cleaner"]
CITIES = ["Hanoi", "Saigon", "Da Nang", "Hai Phong", "Can Tho"]
FIRST_NAMES = [
    "An", "Binh", "Cuong", "Dung", "Duc", "Hai", "Hanh", "Hung", "Khanh", "Lan",
    "Linh", "Long", "Mai", "Minh", "Nam", "Ngoc", "Phong", "Quan", "Quynh", "Tam",
    "Thanh", "Thao", "Thu", "Trang", "Trung", "Tuan", "Van", "Vinh", "Xuan", "Yen",
]
LAST_NAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Vo", "Dang", "Bui", "Do"]


def gen_stores(n_stores: int = 15, seed: int = 7) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for i in range(1, n_stores + 1):
        shifts = rng.choice([2, 3])  # 2 = M+A, 3 = M+A+E
        open_hour = rng.choice([7, 8, 9])
        close_hour = open_hour + (8 if shifts == 2 else 14)
        baseline = rng.choice([3, 4, 4, 5, 6])
        rows.append(
            {
                "store_id": f"S{i:04d}",
                "store_name": f"Store {i:02d}",
                "city": rng.choice(CITIES),
                "open_hour": open_hour,
                "close_hour": close_hour,
                "shifts_per_day": shifts,
                "base_staff_per_shift": baseline,
                "min_staff_per_shift": max(2, baseline - 2),
                "max_staff_per_shift": baseline + 3,
            }
        )
    return pd.DataFrame(rows)


def gen_employees(stores: pd.DataFrame, per_store: int = 12, seed: int = 11) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    rows = []
    emp_id = 1
    for _, store in stores.iterrows():
        # Each store gets roughly `per_store` employees with a small jitter.
        n_emp = per_store + int(np_rng.integers(-2, 3))
        shifts_per_day = int(store["shifts_per_day"])
        # Heuristic: enough managers so that one is available for every shift
        # in the week despite contract caps and 1-shift-per-day rule. With a
        # 40h contract a manager can cover ~5 shifts/week, so we need
        # ceil(7 * shifts_per_day / 4) — leave headroom by using /3.
        n_managers = max(2, -(-7 * shifts_per_day // 3))
        roles = ["Manager"] * n_managers + [
            rng.choice(ROLES[1:]) for _ in range(max(0, n_emp - n_managers))
        ]
        rng.shuffle(roles)

        store_shifts = ALL_SHIFTS[: int(store["shifts_per_day"])]

        for role in roles:
            full_time = rng.random() < 0.55
            contract = 40 if full_time else rng.choice([16, 20, 24, 28, 32])
            min_hours = max(8, contract - rng.choice([8, 12, 16]))
            # Availability: full-timers usually 5-6 days, part-timers 3-4.
            n_days = rng.choice([5, 6]) if full_time else rng.choice([3, 4])
            avail_days = sorted(
                rng.sample(ALL_DAYS, n_days),
                key=ALL_DAYS.index,
            )
            # Most people prefer one or two shift bands.
            n_shifts = rng.choice([1, 2, len(store_shifts)])
            avail_shifts = sorted(
                rng.sample(store_shifts, min(n_shifts, len(store_shifts))),
                key=ALL_SHIFTS.index,
            )
            rate = {
                "Manager": rng.uniform(35, 55),
                "Cashier": rng.uniform(15, 22),
                "Cook":    rng.uniform(20, 30),
                "Server":  rng.uniform(15, 22),
                "Cleaner": rng.uniform(13, 18),
            }[role]
            name = f"{rng.choice(LAST_NAMES)} {rng.choice(FIRST_NAMES)}"
            rows.append(
                {
                    "employee_id": f"E{emp_id:05d}",
                    "employee_name": name,
                    "store_id": store["store_id"],
                    "role": role,
                    "contract_hours_per_week": int(contract),
                    "min_hours_per_week": int(min_hours),
                    "hourly_rate": round(rate, 2),
                    "available_days": ",".join(avail_days),
                    "available_shifts": ",".join(avail_shifts),
                }
            )
            emp_id += 1
    return pd.DataFrame(rows)


def main() -> None:
    stores = gen_stores()
    employees = gen_employees(stores)

    OUT_STORES.parent.mkdir(parents=True, exist_ok=True)
    stores.to_excel(OUT_STORES, index=False)
    employees.to_excel(OUT_EMPLOYEES, index=False)

    print(f"Wrote {OUT_STORES}      ({len(stores)} stores)")
    print(f"Wrote {OUT_EMPLOYEES}   ({len(employees)} employees)")
    print("\nEmployees per store:")
    print(employees.groupby("store_id").size().to_string())


if __name__ == "__main__":
    main()
