"""Generate the full mock Excel dataset used by the AI deployment chart.

This orchestrator produces every workbook the forecasting + scheduling +
explanation pipeline needs, with **cross-referenced IDs** so a given
``store_id``/``employee_id``/``station_id`` means the same thing in every
file.

Priorities (P0 → P2) match the UI user-flow breakdown:

P0 — Minimum viable deployment chart
    stations.xlsx              (station catalogue + channel mapping sheet)
    stores.xlsx                (regenerated, compatible schema)
    employees.xlsx             (now with a ``skills`` column)
    tasks.xlsx                 (rotational tasks — Cleaning / Restocking / Prep)
    orders_history.xlsx        (90 days × stores × shifts × channels)

P1 — Richer demand signal + explainability
    promos.xlsx                (campaigns with per-channel uplift)
    events_calendar.xlsx       (external events with crowd + distance + window)
    past_deployments.xlsx      (AI vs manager gap for "reasoning" panel)

P2 — Edge cases + roster disruption
    weather_forecast.xlsx      (per store × date × shift, synced with event log)
    crew_availability_overrides.xlsx  (PTO / Sick / Training)

All files land in ``examples/`` next to this script. Re-running is safe —
every file is overwritten deterministically (fixed seed per generator).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent

# ----------------------------------------------------------------------
# Master catalogues (single source of truth across every workbook below)
# ----------------------------------------------------------------------

ALL_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ALL_SHIFTS = ["Morning", "Afternoon", "Evening"]
CHANNELS = ["Delivery", "Dine-in", "Drive-Through"]
CITIES = ["Hanoi", "Saigon", "Da Nang", "Hai Phong", "Can Tho"]
ROLES = ["Manager", "Cashier", "Cook", "Server", "Cleaner"]

FIRST_NAMES = [
    "An", "Binh", "Cuong", "Dung", "Duc", "Hai", "Hanh", "Hung", "Khanh", "Lan",
    "Linh", "Long", "Mai", "Minh", "Nam", "Ngoc", "Phong", "Quan", "Quynh", "Tam",
    "Thanh", "Thao", "Thu", "Trang", "Trung", "Tuan", "Van", "Vinh", "Xuan", "Yen",
]
LAST_NAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Vo", "Dang", "Bui", "Do"]

# (station_id, name, area, positions, base_staff[M,A,E], primary_channel, channel_weight, emoji, colour_hex)
STATION_CATALOG: list[tuple] = [
    ("ST_GRILL", "Grill",         "Kitchen", 2, [2, 3, 2], "Both",          0.50, "🔥", "#FAEEDA"),
    ("ST_FRYER", "Fryer",         "Kitchen", 2, [1, 2, 2], "Both",          0.50, "🍟", "#FAECE7"),
    ("ST_DT",    "Drive-Through", "Front",   3, [2, 3, 3], "Drive-Through", 1.00, "🪟", "#EAF3DE"),
    ("ST_FC",    "Front Counter", "Front",   2, [2, 2, 1], "Dine-in",       0.70, "🏷", "#E6F1FB"),
    ("ST_ASM",   "Assembly",      "Kitchen", 2, [1, 2, 2], "Delivery",      0.80, "📦", "#EEEDFE"),
    ("ST_PREP",  "Prep",          "Kitchen", 1, [1, 1, 0], "Both",          0.20, "🥗", "#E1F5EE"),
]

# Which stations an employee can work, derived from their role.
ROLE_SKILLS: dict[str, list[str]] = {
    "Manager": ["ST_GRILL", "ST_FRYER", "ST_DT", "ST_FC", "ST_ASM", "ST_PREP"],
    "Cook":    ["ST_GRILL", "ST_FRYER", "ST_PREP"],
    "Server":  ["ST_DT", "ST_FC", "ST_ASM"],
    "Cashier": ["ST_FC", "ST_DT"],
    "Cleaner": ["ST_PREP", "ST_ASM"],
}

# Day-of-week demand multipliers for orders / deployments.
DOW_MULT = {"Mon": 0.85, "Tue": 0.85, "Wed": 0.90, "Thu": 0.95, "Fri": 1.10, "Sat": 1.25, "Sun": 1.20}

# Shift-of-day split of total daily orders.
SHIFT_SPLIT = {"Morning": 0.20, "Afternoon": 0.40, "Evening": 0.40}

# Channel mix when a store serves all three.
CHANNEL_SPLIT = {"Delivery": 0.35, "Dine-in": 0.45, "Drive-Through": 0.20}

# Date windows
HISTORY_START = date(2025, 10, 1)
HISTORY_END = date(2025, 12, 31)
EVENT_START = date(2026, 1, 1)   # matches simulated_event_data_and_rules.xlsx
EVENT_END = date(2026, 12, 31)


def _dates(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _dow(d: date) -> str:
    return ALL_DAYS[d.weekday()]


# ----------------------------------------------------------------------
# P0 — stations.xlsx (+ channel mapping sheet)
# ----------------------------------------------------------------------

def gen_stations() -> dict[str, pd.DataFrame]:
    rows = []
    channel_rows = []
    for sid, name, area, positions, base, primary, weight, emoji, colour in STATION_CATALOG:
        rows.append({
            "station_id": sid,
            "station_name": name,
            "area": area,
            "positions": positions,
            "base_staff_morning":   base[0],
            "base_staff_afternoon": base[1],
            "base_staff_evening":   base[2],
            "primary_channel": primary,
            "channel_weight": weight,
            "icon_emoji": emoji,
            "colour_hex": colour,
        })
        if primary == "Both":
            channel_rows.append({"station_id": sid, "channel": "Delivery",      "weight": weight})
            channel_rows.append({"station_id": sid, "channel": "Dine-in",       "weight": 1 - weight})
        elif primary == "Drive-Through":
            channel_rows.append({"station_id": sid, "channel": "Drive-Through", "weight": 1.0})
        elif primary == "Dine-in":
            channel_rows.append({"station_id": sid, "channel": "Dine-in",       "weight": weight})
            channel_rows.append({"station_id": sid, "channel": "Delivery",      "weight": 1 - weight})
        elif primary == "Delivery":
            channel_rows.append({"station_id": sid, "channel": "Delivery",      "weight": weight})
            channel_rows.append({"station_id": sid, "channel": "Dine-in",       "weight": 1 - weight})
    return {
        "Stations": pd.DataFrame(rows),
        "ChannelMapping": pd.DataFrame(channel_rows),
    }


# ----------------------------------------------------------------------
# P0 — stores.xlsx (schema-compatible with existing scheduler pipeline)
# ----------------------------------------------------------------------

def gen_stores(n_stores: int = 15, seed: int = 7) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for i in range(1, n_stores + 1):
        shifts = rng.choice([2, 3])
        open_hour = rng.choice([7, 8, 9])
        close_hour = open_hour + (8 if shifts == 2 else 14)
        baseline = rng.choice([3, 4, 4, 5, 6])
        # Daily baseline orders for this store (used by orders_history).
        base_daily_orders = rng.choice([600, 800, 900, 1100, 1300, 1400])
        rows.append({
            "store_id": f"S{i:04d}",
            "store_name": f"Store {i:02d}",
            "city": rng.choice(CITIES),
            "open_hour": open_hour,
            "close_hour": close_hour,
            "shifts_per_day": shifts,
            "base_staff_per_shift": baseline,
            "min_staff_per_shift": max(2, baseline - 2),
            "max_staff_per_shift": baseline + 3,
            "base_daily_orders": base_daily_orders,
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# P0 — employees.xlsx (with skills column)
# ----------------------------------------------------------------------

def gen_employees(stores: pd.DataFrame, per_store: int = 12, seed: int = 11) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    rows = []
    emp_id = 1
    for _, store in stores.iterrows():
        n_emp = per_store + int(np_rng.integers(-2, 3))
        shifts_per_day = int(store["shifts_per_day"])
        n_managers = max(2, -(-7 * shifts_per_day // 3))
        roles = ["Manager"] * n_managers + [
            rng.choice(ROLES[1:]) for _ in range(max(0, n_emp - n_managers))
        ]
        rng.shuffle(roles)

        store_shifts = ALL_SHIFTS[: shifts_per_day]

        for role in roles:
            full_time = rng.random() < 0.55
            contract = 40 if full_time else rng.choice([16, 20, 24, 28, 32])
            min_hours = max(8, contract - rng.choice([8, 12, 16]))
            n_days = rng.choice([5, 6]) if full_time else rng.choice([3, 4])
            avail_days = sorted(rng.sample(ALL_DAYS, n_days), key=ALL_DAYS.index)
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

            # Skills: start from role baseline, then drop some at random
            # (some crew members are only certified on a subset of their role).
            baseline_skills = list(ROLE_SKILLS[role])
            if role != "Manager" and len(baseline_skills) > 1 and rng.random() < 0.5:
                keep = rng.randint(1, len(baseline_skills))
                skills = sorted(rng.sample(baseline_skills, keep), key=baseline_skills.index)
            else:
                skills = baseline_skills

            name = f"{rng.choice(LAST_NAMES)} {rng.choice(FIRST_NAMES)}"
            rows.append({
                "employee_id": f"E{emp_id:05d}",
                "employee_name": name,
                "store_id": store["store_id"],
                "role": role,
                "contract_hours_per_week": int(contract),
                "min_hours_per_week": int(min_hours),
                "hourly_rate": round(rate, 2),
                "available_days": ",".join(avail_days),
                "available_shifts": ",".join(avail_shifts),
                "skills": ",".join(skills),
            })
            emp_id += 1
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# P0 — tasks.xlsx
# ----------------------------------------------------------------------

def gen_tasks() -> pd.DataFrame:
    return pd.DataFrame([
        {"task_id": "TK_CLEAN",   "task_name": "Cleaning",   "category": "Rotational", "area": "All",     "duration_min": 20, "frequency_per_shift": 2, "icon_emoji": "🧹"},
        {"task_id": "TK_RESTOCK", "task_name": "Restocking", "category": "Rotational", "area": "Kitchen", "duration_min": 15, "frequency_per_shift": 3, "icon_emoji": "🗄"},
        {"task_id": "TK_PREP",    "task_name": "Prep",       "category": "Kitchen",    "area": "Kitchen", "duration_min": 45, "frequency_per_shift": 1, "icon_emoji": "🥗"},
    ])


# ----------------------------------------------------------------------
# P0 — orders_history.xlsx
# ----------------------------------------------------------------------

def gen_orders_history(
    stores: pd.DataFrame,
    weather_lookup: dict[date, str] | None = None,
    seed: int = 23,
) -> pd.DataFrame:
    """Daily order counts for (store, shift, channel), Oct-Dec 2025."""
    rng = np.random.default_rng(seed)
    rows = []
    for _, store in stores.iterrows():
        shifts_per_day = int(store["shifts_per_day"])
        store_shifts = ALL_SHIFTS[:shifts_per_day]
        base_daily = float(store["base_daily_orders"])
        for d in _dates(HISTORY_START, HISTORY_END):
            dow_mult = DOW_MULT[_dow(d)]
            weather = (weather_lookup or {}).get(d, "dry")
            for shift in store_shifts:
                shift_frac = SHIFT_SPLIT[shift]
                # Rescale if the store only runs 2 shifts (Morning+Afternoon).
                if shifts_per_day == 2:
                    shift_frac = {"Morning": 0.35, "Afternoon": 0.65}[shift]
                for channel, ch_frac in CHANNEL_SPLIT.items():
                    weather_mult = {
                        "Delivery":      1.05 if weather == "rain" else 1.00,
                        "Dine-in":       0.92 if weather == "rain" else 1.00,
                        "Drive-Through": 0.95 if weather == "rain" else 1.00,
                    }[channel]
                    noise = float(rng.normal(1.0, 0.08))
                    order_count = max(
                        1,
                        int(round(base_daily * dow_mult * shift_frac * ch_frac * weather_mult * noise)),
                    )
                    avg_order_size = round(float(rng.normal(8.5, 1.2)), 2)
                    avg_order_size = max(3.0, avg_order_size)
                    revenue = round(order_count * avg_order_size, 2)
                    rows.append({
                        "date": d,
                        "store_id": store["store_id"],
                        "day_of_week": _dow(d),
                        "shift": shift,
                        "channel": channel,
                        "order_count": order_count,
                        "avg_order_size": avg_order_size,
                        "revenue": revenue,
                        "weather_observed": weather,
                    })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# P1 — promos.xlsx
# ----------------------------------------------------------------------

def gen_promos(stores: pd.DataFrame, seed: int = 31) -> pd.DataFrame:
    rng = random.Random(seed)
    campaigns = [
        ("PRM_BOGO_BURGER",  "Burger BOGO",         "BOGO",     ["ST_GRILL", "ST_ASM"],                 (0.18, 0.08, 0.04)),
        ("PRM_FRY_COMBO",    "Fries Combo Deal",    "Combo",    ["ST_FRYER", "ST_FC"],                  (0.06, 0.12, 0.05)),
        ("PRM_DT_HAPPY",     "Drive-Thru Happy Hr", "Discount", ["ST_DT", "ST_ASM"],                    (0.03, 0.02, 0.22)),
        ("PRM_DLV_20OFF",    "Delivery 20% Off",    "Discount", ["ST_ASM", "ST_GRILL"],                 (0.25, 0.02, 0.01)),
        ("PRM_FAMILY_PACK",  "Family Pack Bundle",  "Combo",    ["ST_GRILL", "ST_FRYER", "ST_ASM"],     (0.12, 0.14, 0.08)),
        ("PRM_WEEKEND_2X",   "Weekend 2x Points",   "Loyalty",  ["ST_FC", "ST_DT"],                     (0.05, 0.08, 0.07)),
        ("PRM_NEWYEAR_GIFT", "NY Gift Combo",       "Combo",    ["ST_GRILL", "ST_ASM", "ST_FC"],        (0.10, 0.16, 0.10)),
    ]
    store_ids = stores["store_id"].tolist()
    rows = []
    for pid, name, ptype, stations, (uplift_del, uplift_din, uplift_dt) in campaigns:
        # Some promos are national, some regional.
        scope = "all" if rng.random() < 0.6 else ",".join(rng.sample(store_ids, k=rng.randint(3, 8)))
        # Anchor date somewhere in 2025-10 .. 2026-06
        anchor = HISTORY_START + timedelta(days=rng.randint(0, 270))
        duration = rng.choice([3, 5, 7, 10, 14])
        rows.append({
            "promo_id": pid,
            "promo_name": name,
            "promo_type": ptype,
            "start_date": anchor,
            "end_date": anchor + timedelta(days=duration - 1),
            "duration_days": duration,
            "affected_stations": ",".join(stations),
            "store_scope": scope,
            "uplift_delivery": round(uplift_del + rng.uniform(-0.02, 0.02), 3),
            "uplift_dinein":   round(uplift_din + rng.uniform(-0.02, 0.02), 3),
            "uplift_drivethrough": round(uplift_dt + rng.uniform(-0.02, 0.02), 3),
            "expected_order_lift_pct": round((uplift_del + uplift_din + uplift_dt) * 100, 1),
            "notes": f"{ptype} campaign targeting {name.lower()}",
        })
    return pd.DataFrame(rows).sort_values("start_date").reset_index(drop=True)


# ----------------------------------------------------------------------
# P1 — events_calendar.xlsx (extended external events)
# ----------------------------------------------------------------------

def gen_events_calendar(stores: pd.DataFrame, seed: int = 37) -> pd.DataFrame:
    rng = random.Random(seed)
    catalogue = [
        # (name, type, typical_crowd_range, distance_range_km, channel_bias_dict, time_window)
        ("Football Derby",       "Sport",    (15_000, 45_000), (1.0, 6.0), {"Delivery": 0.18, "Dine-in": -0.08, "Drive-Through": 0.10}, "19:00-22:00"),
        ("Rock Concert",         "Concert",  (8_000,  25_000), (0.5, 4.0), {"Delivery": 0.10, "Dine-in":  0.05, "Drive-Through": 0.15}, "20:00-23:30"),
        ("Food Festival",        "Festival", (5_000,  20_000), (0.3, 2.5), {"Delivery": -0.05, "Dine-in":-0.12, "Drive-Through":-0.08}, "10:00-22:00"),
        ("Lunar New Year",       "Holiday",  (0, 0),           (0.0, 0.0), {"Delivery": 0.08, "Dine-in":  0.15, "Drive-Through": 0.05}, "All day"),
        ("National Day",         "Holiday",  (0, 0),           (0.0, 0.0), {"Delivery": 0.05, "Dine-in":  0.12, "Drive-Through": 0.08}, "All day"),
        ("Marathon",             "Sport",    (3_000,  10_000), (0.2, 3.0), {"Delivery":-0.05, "Dine-in":  0.10, "Drive-Through":-0.10}, "05:00-11:00"),
        ("Tech Conference",      "Conference",(2_000, 8_000),  (0.5, 5.0), {"Delivery": 0.20, "Dine-in":  0.08, "Drive-Through": 0.05}, "08:00-18:00"),
        ("Shopping Sale Weekend","Retail",   (10_000, 30_000), (0.3, 3.0), {"Delivery":-0.05, "Dine-in":  0.18, "Drive-Through": 0.10}, "All day"),
        ("Basketball Playoff",   "Sport",    (5_000, 15_000),  (1.0, 6.0), {"Delivery": 0.22, "Dine-in": -0.05, "Drive-Through": 0.05}, "19:30-22:00"),
        ("Music Awards",         "Concert",  (3_000, 12_000),  (1.0, 5.0), {"Delivery": 0.12, "Dine-in":  0.03, "Drive-Through": 0.10}, "19:00-23:00"),
        ("City Parade",          "Festival", (20_000, 60_000), (0.1, 2.0), {"Delivery":-0.08, "Dine-in": -0.15, "Drive-Through":-0.20}, "14:00-18:00"),
        ("Graduation Ceremony",  "Community",(500, 3_000),     (0.5, 4.0), {"Delivery": 0.02, "Dine-in":  0.25, "Drive-Through": 0.05}, "10:00-16:00"),
    ]
    store_ids = stores["store_id"].tolist()
    rows = []
    eid = 1
    for name, etype, crowd_range, dist_range, bias, window in catalogue:
        # Each template spawns 1-3 concrete instances across 2026.
        occurrences = rng.randint(1, 3) if etype not in {"Holiday"} else 1
        for _ in range(occurrences):
            event_date = EVENT_START + timedelta(days=rng.randint(0, (EVENT_END - EVENT_START).days))
            # Pick affected stores: 30-70% of all stores.
            affected = rng.sample(store_ids, k=rng.randint(max(3, len(store_ids) // 3), int(len(store_ids) * 0.7)))
            crowd = 0 if crowd_range == (0, 0) else rng.randint(*crowd_range)
            dist = 0.0 if dist_range == (0.0, 0.0) else round(rng.uniform(*dist_range), 2)
            start_time, end_time = (window.split("-") + ["", ""])[:2] if "-" in window else (window, window)
            rows.append({
                "event_id": f"EV{eid:04d}",
                "event_date": event_date,
                "event_name": name,
                "event_type": etype,
                "start_time": start_time,
                "end_time": end_time,
                "time_window": window,
                "venue_distance_km": dist,
                "expected_crowd_size": crowd,
                "affected_store_ids": ",".join(sorted(affected)),
                "impact_delivery":      bias["Delivery"],
                "impact_dinein":        bias["Dine-in"],
                "impact_drivethrough":  bias["Drive-Through"],
                "confidence": rng.choice(["high", "high", "medium", "medium", "low"]),
                "source": rng.choice(["city-events-api", "manual-entry", "partner-feed"]),
            })
            eid += 1
    return pd.DataFrame(rows).sort_values("event_date").reset_index(drop=True)


# ----------------------------------------------------------------------
# P1 — past_deployments.xlsx  (AI vs manager gap — powers "reasoning" panel)
# ----------------------------------------------------------------------

def gen_past_deployments(
    stores: pd.DataFrame,
    stations: pd.DataFrame,
    orders_history: pd.DataFrame,
    seed: int = 43,
) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    station_rows = stations.set_index("station_id").to_dict("index")
    base_staff_map = {
        "Morning":   "base_staff_morning",
        "Afternoon": "base_staff_afternoon",
        "Evening":   "base_staff_evening",
    }
    # Daily demand multiplier derived from orders_history (per store, date).
    daily = (
        orders_history.groupby(["store_id", "date"])["order_count"].sum().reset_index(name="daily")
    )
    store_baseline = daily.groupby("store_id")["daily"].median().to_dict()
    daily["mult"] = daily.apply(lambda r: r["daily"] / store_baseline[r["store_id"]], axis=1)
    mult_lookup = daily.set_index(["store_id", "date"])["mult"].to_dict()

    rows = []
    did = 1
    for _, store in stores.iterrows():
        shifts_per_day = int(store["shifts_per_day"])
        store_shifts = ALL_SHIFTS[:shifts_per_day]
        for d in _dates(HISTORY_START + timedelta(days=30), HISTORY_END):
            demand_mult = mult_lookup.get((store["store_id"], pd.Timestamp(d)), 1.0)
            for shift in store_shifts:
                for sid, srow in station_rows.items():
                    if shift == "Evening" and srow["base_staff_evening"] == 0:
                        continue
                    base = int(srow[base_staff_map[shift]])
                    ai_reco = max(1, int(round(base * demand_mult)))
                    bias = rng.choices([-2, -1, -1, 0, 0, 0, 0, 1], k=1)[0]
                    manager = max(1, ai_reco + bias)
                    actual = max(1, manager + rng.choice([-1, 0, 0, 0, 0, 1]))
                    gap = manager - ai_reco
                    if gap <= -1:
                        outcome = "short"
                    elif gap >= 1:
                        outcome = "over"
                    else:
                        outcome = "met"
                    rows.append({
                        "deployment_id": f"DEP{did:07d}",
                        "date": d,
                        "day_of_week": _dow(d),
                        "store_id": store["store_id"],
                        "shift": shift,
                        "station_id": sid,
                        "station_name": srow["station_name"],
                        "ai_recommended": ai_reco,
                        "manager_assigned": manager,
                        "actual_staffed": actual,
                        "gap": gap,
                        "outcome": outcome,
                        "demand_multiplier": round(demand_mult, 3),
                        "notes": rng.choice([
                            "", "", "", "Late swap", "Sick call-out", "Walk-in hire", "Training day",
                        ]),
                    })
                    did += 1
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# P2 — weather_forecast.xlsx
# ----------------------------------------------------------------------

def gen_weather_forecast(stores: pd.DataFrame, event_workbook_path: Path, seed: int = 53) -> pd.DataFrame:
    """Per-store, per-shift weather forecast for 2026.

    Synced with ``simulated_event_data_and_rules.xlsx`` so that days marked
    ``rain`` there have high rain_probability here (the AI explanation panel
    can then say "forecast: 85% rain" and still line up with the event log).
    """
    rng = random.Random(seed)

    try:
        ev = pd.read_excel(event_workbook_path, sheet_name="Tab1_EventTable")
    except Exception:
        ev = pd.DataFrame(columns=["store_id", "date", "event", "event type"])
    weather_map: dict[tuple[str, date], str] = {}
    if not ev.empty:
        mask = ev["event type"].astype(str).str.lower() == "weather"
        weather_ev = ev[mask].copy()
        weather_ev["date"] = pd.to_datetime(weather_ev["date"]).dt.date
        for _, row in weather_ev.iterrows():
            weather_map[(str(row["store_id"]), row["date"])] = str(row["event"]).lower()

    rows = []
    for _, store in stores.iterrows():
        shifts_per_day = int(store["shifts_per_day"])
        store_shifts = ALL_SHIFTS[:shifts_per_day]
        for d in _dates(EVENT_START, EVENT_END):
            observed = weather_map.get((store["store_id"], d))
            if observed is None:
                # Global daily weather fallback (use S0001 as proxy)
                observed = weather_map.get(("S0001", d), "dry")
            is_rain = observed == "rain"
            base_temp = {
                1: 18, 2: 20, 3: 23, 4: 27, 5: 30, 6: 31,
                7: 32, 8: 32, 9: 29, 10: 26, 11: 22, 12: 19,
            }[d.month]
            for shift in store_shifts:
                shift_temp_bias = {"Morning": -3, "Afternoon": 2, "Evening": 0}[shift]
                temp_c = round(base_temp + shift_temp_bias + rng.uniform(-2, 2), 1)
                if is_rain:
                    condition = "rain"
                    rain_prob = round(rng.uniform(0.70, 0.95), 2)
                    intensity = rng.choice(["light", "moderate", "moderate", "heavy"])
                    wind = round(rng.uniform(8, 25), 1)
                else:
                    condition = "dry"
                    rain_prob = round(rng.uniform(0.00, 0.20), 2)
                    intensity = "none"
                    wind = round(rng.uniform(2, 12), 1)
                severity = (
                    "severe" if intensity == "heavy"
                    else "moderate" if intensity == "moderate"
                    else "mild" if intensity == "light"
                    else "clear"
                )
                rows.append({
                    "store_id": store["store_id"],
                    "date": d,
                    "shift": shift,
                    "condition": condition,
                    "rain_probability": rain_prob,
                    "intensity": intensity,
                    "temp_c": temp_c,
                    "wind_kmh": wind,
                    "severity": severity,
                })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# P2 — crew_availability_overrides.xlsx
# ----------------------------------------------------------------------

def gen_availability_overrides(employees: pd.DataFrame, seed: int = 61) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    oid = 1
    start = HISTORY_START
    end = EVENT_START + timedelta(days=90)  # overrides span into Q1 2026
    total_days = (end - start).days
    for _, emp in employees.iterrows():
        # Each employee gets ~4-12 override days across the ~8-month window.
        n = rng.randint(4, 12)
        picks = rng.sample(range(total_days), k=min(n, total_days))
        for offset in picks:
            d = start + timedelta(days=offset)
            status = rng.choices(
                ["PTO", "Sick", "Training", "Personal", "Swap"],
                weights=[0.30, 0.25, 0.15, 0.20, 0.10],
                k=1,
            )[0]
            note = {
                "PTO": "Pre-approved vacation",
                "Sick": "Same-day call-out",
                "Training": "Corporate training",
                "Personal": "Personal day",
                "Swap": "Shift swap with colleague",
            }[status]
            rows.append({
                "override_id": f"OV{oid:06d}",
                "employee_id": emp["employee_id"],
                "store_id": emp["store_id"],
                "date": d,
                "status": status,
                "available": status == "Swap",  # swap = still works, just different day
                "note": note,
                "created_at": datetime.combine(d - timedelta(days=rng.randint(0, 14)), datetime.min.time()),
            })
            oid += 1
    return pd.DataFrame(rows).sort_values(["date", "employee_id"]).reset_index(drop=True)


# ----------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------

@dataclass
class GenReport:
    files: list[tuple[str, int, int]]  # (filename, row count or total, col count)

    def print(self) -> None:
        print("\n=== Mock dataset generated ===")
        print(f"{'File':<42} {'Rows':>10} {'Cols':>6}")
        print("-" * 62)
        for fn, rows, cols in self.files:
            print(f"{fn:<42} {rows:>10,} {cols:>6}")


def _weather_lookup_for_history(event_workbook_path: Path) -> dict[date, str]:
    """Extract a simple (date -> weather) map for historical orders_history.

    The event workbook only covers 2026, so for Oct–Dec 2025 we just
    synthesise a realistic rainy-season pattern deterministically.
    """
    rng = random.Random(97)
    lookup: dict[date, str] = {}
    for d in _dates(HISTORY_START, HISTORY_END):
        # Oct = end of rainy season in VN → ~35% rain; Nov ~20%; Dec ~10%.
        rain_prob = {10: 0.35, 11: 0.20, 12: 0.10}[d.month]
        lookup[d] = "rain" if rng.random() < rain_prob else "dry"
    return lookup


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    event_wb = OUT_DIR / "simulated_event_data_and_rules.xlsx"
    report: list[tuple[str, int, int]] = []

    # ---- P0 ----
    stations_sheets = gen_stations()
    with pd.ExcelWriter(OUT_DIR / "stations.xlsx") as w:
        for name, df in stations_sheets.items():
            df.to_excel(w, sheet_name=name, index=False)
    total = sum(len(df) for df in stations_sheets.values())
    cols = max(len(df.columns) for df in stations_sheets.values())
    report.append(("stations.xlsx", total, cols))

    stores = gen_stores()
    stores.to_excel(OUT_DIR / "stores.xlsx", index=False)
    report.append(("stores.xlsx", len(stores), len(stores.columns)))

    employees = gen_employees(stores)
    employees.to_excel(OUT_DIR / "employees.xlsx", index=False)
    report.append(("employees.xlsx", len(employees), len(employees.columns)))

    tasks = gen_tasks()
    tasks.to_excel(OUT_DIR / "tasks.xlsx", index=False)
    report.append(("tasks.xlsx", len(tasks), len(tasks.columns)))

    weather_hist = _weather_lookup_for_history(event_wb)
    orders = gen_orders_history(stores, weather_lookup=weather_hist)
    orders.to_excel(OUT_DIR / "orders_history.xlsx", index=False)
    report.append(("orders_history.xlsx", len(orders), len(orders.columns)))

    # ---- P1 ----
    promos = gen_promos(stores)
    promos.to_excel(OUT_DIR / "promos.xlsx", index=False)
    report.append(("promos.xlsx", len(promos), len(promos.columns)))

    events_cal = gen_events_calendar(stores)
    events_cal.to_excel(OUT_DIR / "events_calendar.xlsx", index=False)
    report.append(("events_calendar.xlsx", len(events_cal), len(events_cal.columns)))

    deployments = gen_past_deployments(stores, stations_sheets["Stations"], orders)
    deployments.to_excel(OUT_DIR / "past_deployments.xlsx", index=False)
    report.append(("past_deployments.xlsx", len(deployments), len(deployments.columns)))

    # ---- P2 ----
    weather = gen_weather_forecast(stores, event_wb)
    weather.to_excel(OUT_DIR / "weather_forecast.xlsx", index=False)
    report.append(("weather_forecast.xlsx", len(weather), len(weather.columns)))

    overrides = gen_availability_overrides(employees)
    overrides.to_excel(OUT_DIR / "crew_availability_overrides.xlsx", index=False)
    report.append(("crew_availability_overrides.xlsx", len(overrides), len(overrides.columns)))

    GenReport(files=report).print()

    print("\nCross-reference summary")
    print(f"  stations      : {len(stations_sheets['Stations'])} station_ids")
    print(f"  stores        : {len(stores)} store_ids ({stores['store_id'].min()} .. {stores['store_id'].max()})")
    print(f"  employees     : {len(employees)} employee_ids (across {employees['store_id'].nunique()} stores)")
    print(f"  orders history: {orders['date'].min()} -> {orders['date'].max()}")
    print(f"  weather       : {weather['date'].min()} -> {weather['date'].max()}")
    print(f"  promos        : {promos['start_date'].min()} -> {promos['end_date'].max()}")


if __name__ == "__main__":
    main()
