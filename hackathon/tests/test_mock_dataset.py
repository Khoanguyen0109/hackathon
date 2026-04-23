"""Cross-reference integrity tests for the mock dataset generators.

We call the cheap generators directly (stations / stores / employees /
tasks / promos / events) and verify the ID universes line up. The
expensive generators (orders_history, past_deployments, weather,
overrides) are smoke-tested with a 1-store subset so the full run is not
required in CI.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
GEN_PATH = HERE.parent / "examples" / "generate_full_mock_dataset.py"


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("_mock_gen", GEN_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_mock_gen"] = module
    spec.loader.exec_module(module)
    return module


# ---------- P0 ----------

def test_stations_schema_and_ids(gen):
    sheets = gen.gen_stations()
    stations = sheets["Stations"]
    channels = sheets["ChannelMapping"]
    assert set(["station_id", "station_name", "area", "positions",
                "base_staff_morning", "base_staff_afternoon", "base_staff_evening",
                "primary_channel", "channel_weight"]).issubset(stations.columns)
    assert stations["station_id"].is_unique
    # Channel mapping must only reference real stations.
    assert set(channels["station_id"]).issubset(set(stations["station_id"]))
    # Every station appears in at least one channel row.
    assert set(stations["station_id"]) == set(channels["station_id"])


def test_employees_skills_reference_real_stations(gen):
    stations = gen.gen_stations()["Stations"]
    stores = gen.gen_stores(n_stores=3)
    employees = gen.gen_employees(stores, per_store=6)
    valid = set(stations["station_id"])

    assert set(employees["store_id"]).issubset(set(stores["store_id"]))
    assert employees["employee_id"].is_unique

    for skill_csv in employees["skills"]:
        tokens = [t for t in str(skill_csv).split(",") if t]
        assert tokens, "every employee must have at least one skill"
        assert set(tokens).issubset(valid), f"unknown station in skills: {tokens}"


def test_every_store_has_a_manager(gen):
    stores = gen.gen_stores(n_stores=3)
    employees = gen.gen_employees(stores, per_store=6)
    managers = employees[employees["role"] == "Manager"]
    for sid in stores["store_id"]:
        assert len(managers[managers["store_id"] == sid]) >= 2, f"store {sid} has <2 managers"


def test_orders_history_smoke(gen):
    stores = gen.gen_stores(n_stores=1)
    orders = gen.gen_orders_history(stores, weather_lookup={})
    # 92 days (Oct-Dec 2025) × 2-3 shifts × 3 channels
    assert set(orders.columns) >= {"date", "store_id", "shift", "channel",
                                   "order_count", "avg_order_size", "revenue"}
    assert (orders["order_count"] > 0).all()
    assert len(orders) > 0
    assert set(orders["channel"]).issubset({"Delivery", "Dine-in", "Drive-Through"})
    assert (orders["store_id"] == stores["store_id"].iloc[0]).all()


# ---------- P1 ----------

def test_promos_reference_real_stations_and_stores(gen):
    stations = gen.gen_stations()["Stations"]
    stores = gen.gen_stores(n_stores=5)
    promos = gen.gen_promos(stores)
    valid_stations = set(stations["station_id"])
    valid_stores = set(stores["store_id"])

    assert promos["promo_id"].is_unique
    for stations_csv in promos["affected_stations"]:
        tokens = [t for t in str(stations_csv).split(",") if t]
        assert set(tokens).issubset(valid_stations)
    for scope in promos["store_scope"]:
        if scope != "all":
            tokens = [t for t in str(scope).split(",") if t]
            assert set(tokens).issubset(valid_stores)
    # Dates are chronologically valid.
    assert (promos["end_date"] >= promos["start_date"]).all()


def test_events_calendar_references_real_stores(gen):
    stores = gen.gen_stores(n_stores=5)
    events = gen.gen_events_calendar(stores)
    valid = set(stores["store_id"])
    assert events["event_id"].is_unique
    for csv in events["affected_store_ids"]:
        tokens = [t for t in str(csv).split(",") if t]
        assert set(tokens).issubset(valid)
    # Impact values are bounded multipliers.
    for col in ("impact_delivery", "impact_dinein", "impact_drivethrough"):
        assert events[col].between(-1, 1).all()


def test_past_deployments_cross_refs(gen):
    stations = gen.gen_stations()["Stations"]
    stores = gen.gen_stores(n_stores=1)
    orders = gen.gen_orders_history(stores, weather_lookup={})
    deploys = gen.gen_past_deployments(stores, stations, orders)

    assert set(deploys["store_id"]).issubset(set(stores["store_id"]))
    assert set(deploys["station_id"]).issubset(set(stations["station_id"]))
    assert set(deploys["outcome"]).issubset({"short", "met", "over"})
    assert (deploys["ai_recommended"] >= 1).all()
    assert (deploys["manager_assigned"] >= 1).all()


# ---------- P2 ----------

def test_weather_forecast_covers_every_day(gen, tmp_path):
    stores = gen.gen_stores(n_stores=1)
    # Point at the real event workbook so the "rain" days line up.
    event_wb = GEN_PATH.parent / "simulated_event_data_and_rules.xlsx"
    w = gen.gen_weather_forecast(stores, event_wb)
    # 365 days × shifts_per_day rows for one store.
    shifts_per_day = int(stores["shifts_per_day"].iloc[0])
    assert len(w) == 365 * shifts_per_day
    assert set(w["condition"]).issubset({"dry", "rain"})
    assert w["rain_probability"].between(0, 1).all()
    assert (w["temp_c"] > 0).all() and (w["temp_c"] < 50).all()


def test_availability_overrides_cross_refs(gen):
    stores = gen.gen_stores(n_stores=1)
    employees = gen.gen_employees(stores, per_store=5)
    overrides = gen.gen_availability_overrides(employees)

    assert set(overrides["employee_id"]).issubset(set(employees["employee_id"]))
    assert set(overrides["store_id"]).issubset(set(stores["store_id"]))
    assert set(overrides["status"]).issubset({"PTO", "Sick", "Training", "Personal", "Swap"})
    assert overrides["override_id"].is_unique
