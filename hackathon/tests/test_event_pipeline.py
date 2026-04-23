"""Tests for the event-driven pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_forecaster.event_pipeline import (
    DEFAULT_EVENT_SHEET,
    DEFAULT_RULES_SHEET,
    build_demand_index_series,
    compute_daily_deltas,
    filter_series,
    load_event_workbook,
)


@pytest.fixture
def sample_workbook(tmp_path: Path) -> Path:
    events = pd.DataFrame(
        [
            # Day 1: weekday, dry. No active rules. -> delta 0.
            {"store_id": "S1", "date": "2026-01-01", "time": "06:00:00", "event": "dry", "event type": "Weather"},
            # Day 2: rain (Delivery +0.05, Dine-in -0.03)
            {"store_id": "S1", "date": "2026-01-02", "time": "06:00:00", "event": "rain", "event type": "Weather"},
            # Day 3: rain + Saturday (rain + weekend rules stack)
            {"store_id": "S1", "date": "2026-01-03", "time": "06:00:00", "event": "rain", "event type": "Weather"},
            {"store_id": "S1", "date": "2026-01-03", "time": "00:00:00", "event": "Saturday", "event type": "Weekends"},
            # Day 4: a holiday (wildcard "Any" -> +0.02 both channels)
            {"store_id": "S1", "date": "2026-01-04", "time": "00:00:00", "event": "Christmas", "event type": "Holidays"},
            # Independent store has only a Sunday on day 5 (weekends rule).
            {"store_id": "S2", "date": "2026-01-05", "time": "00:00:00", "event": "Sunday", "event type": "Weekends"},
        ]
    )
    rules = pd.DataFrame(
        [
            {"Event Type": "Weather",  "Event": "rain",     "Channel": "Delivery", "Direction": "Increase",  "Delta":  0.05},
            {"Event Type": "Weather",  "Event": "rain",     "Channel": "Dine-in",  "Direction": "Decrease",  "Delta": -0.03},
            {"Event Type": "Weather",  "Event": "dry",      "Channel": "Delivery", "Direction": "No change", "Delta":  0.00},
            {"Event Type": "Weather",  "Event": "dry",      "Channel": "Dine-in",  "Direction": "No change", "Delta":  0.00},
            {"Event Type": "Weekends", "Event": "Saturday", "Channel": "Delivery", "Direction": "Increase",  "Delta":  0.06},
            {"Event Type": "Weekends", "Event": "Saturday", "Channel": "Dine-in",  "Direction": "Increase",  "Delta":  0.06},
            {"Event Type": "Weekends", "Event": "Sunday",   "Channel": "Delivery", "Direction": "Increase",  "Delta":  0.06},
            {"Event Type": "Weekends", "Event": "Sunday",   "Channel": "Dine-in",  "Direction": "Increase",  "Delta":  0.06},
            {"Event Type": "Holidays", "Event": "Any",      "Channel": "Delivery", "Direction": "Increase",  "Delta":  0.02},
            {"Event Type": "Holidays", "Event": "Any",      "Channel": "Dine-in",  "Direction": "Increase",  "Delta":  0.02},
        ]
    )

    path = tmp_path / "wb.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        events.to_excel(w, sheet_name=DEFAULT_EVENT_SHEET, index=False)
        rules.to_excel(w, sheet_name=DEFAULT_RULES_SHEET, index=False)
    return path


def test_load_event_workbook(sample_workbook: Path) -> None:
    data = load_event_workbook(sample_workbook)
    assert sorted(data.stores) == ["S1", "S2"]
    assert sorted(data.channels) == ["Delivery", "Dine-in"]
    assert len(data.rules) == 10
    assert len(data.events) == 6


def test_compute_daily_deltas_specific_and_wildcard(sample_workbook: Path) -> None:
    data = load_event_workbook(sample_workbook)
    deltas = compute_daily_deltas(data)

    def get(store: str, date: str, channel: str) -> float:
        sub = deltas[
            (deltas["store_id"] == store)
            & (deltas["date"] == pd.Timestamp(date))
            & (deltas["channel"] == channel)
        ]
        return 0.0 if sub.empty else float(sub["delta_sum"].iloc[0])

    # Day 2: only rain.
    assert get("S1", "2026-01-02", "Delivery") == pytest.approx(0.05)
    assert get("S1", "2026-01-02", "Dine-in") == pytest.approx(-0.03)

    # Day 3: rain + Saturday should stack.
    assert get("S1", "2026-01-03", "Delivery") == pytest.approx(0.05 + 0.06)
    assert get("S1", "2026-01-03", "Dine-in") == pytest.approx(-0.03 + 0.06)

    # Day 4: holiday wildcard fires for both channels.
    assert get("S1", "2026-01-04", "Delivery") == pytest.approx(0.02)
    assert get("S1", "2026-01-04", "Dine-in") == pytest.approx(0.02)

    # Day 5: only S2 has a Sunday event.
    assert get("S2", "2026-01-05", "Delivery") == pytest.approx(0.06)
    assert get("S1", "2026-01-05", "Delivery") == 0.0  # no event for S1


def test_build_demand_index_series_shape_and_baseline(sample_workbook: Path) -> None:
    data = load_event_workbook(sample_workbook)
    series = build_demand_index_series(data)

    # 2 stores * 2 channels = 4 series
    assert len(series) == 4
    names = sorted(s.name for s in series)
    assert names == ["S1|Delivery", "S1|Dine-in", "S2|Delivery", "S2|Dine-in"]

    # Each series should span every day from the earliest to latest event.
    for s in series:
        assert s.values.index.min() == pd.Timestamp("2026-01-01")
        assert s.values.index.max() == pd.Timestamp("2026-01-05")
        assert len(s) == 5
        assert s.freq == "D"

    s1_del = next(s for s in series if s.name == "S1|Delivery").values
    expected = pd.Series(
        {
            pd.Timestamp("2026-01-01"): 1.0,           # dry, no impact
            pd.Timestamp("2026-01-02"): 1.0 + 0.05,    # rain
            pd.Timestamp("2026-01-03"): 1.0 + 0.05 + 0.06,  # rain + Saturday
            pd.Timestamp("2026-01-04"): 1.0 + 0.02,    # holiday
            pd.Timestamp("2026-01-05"): 1.0,           # quiet day
        }
    )
    np.testing.assert_allclose(s1_del.values, expected.values)


def test_filter_series(sample_workbook: Path) -> None:
    data = load_event_workbook(sample_workbook)
    series = build_demand_index_series(data)

    only_s1 = filter_series(series, stores=["S1"])
    assert {s.metadata["store_id"] for s in only_s1} == {"S1"}

    only_delivery = filter_series(series, channels=["Delivery"])
    assert {s.metadata["channel"] for s in only_delivery} == {"Delivery"}
