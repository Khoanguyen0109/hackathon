"""Event-driven time-series construction.

The repo's "raw" Excel workbook
(``examples/simulated_event_data_and_rules.xlsx``) does not contain numeric
time series at all. Instead it provides:

* **Tab1_EventTable** — a long-format event log with columns
  ``store_id, date, time, event, event type``.
* **Tab2_PredictionRules** — for each ``(Event Type, Event)`` and ``Channel``
  (e.g. *Delivery* / *Dine-in*) it gives a multiplicative ``Delta`` to apply
  to that channel's baseline demand. ``Event = "Any"`` is a wildcard that
  matches every event of that type.

This module turns those two tabs into one numeric time-series per
``(store_id, channel)`` pair so they can be forecast with the rest of the
pipeline (Chronos / any other model).

The constructed series is::

    demand_index(store, channel, date) = 1.0 + Σ Δ over all rules
                                                that fire for that day

A value of ``1.00`` means "no impact"; ``1.05`` means "+5% expected lift",
``0.97`` means "-3% expected drop". Days with no events default to ``1.0``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .data_loader import TimeSeries


WILDCARD_EVENT = "Any"

DEFAULT_EVENT_SHEET = "Tab1_EventTable"
DEFAULT_RULES_SHEET = "Tab2_PredictionRules"

# Column names expected in the event sheet (case-insensitive lookup).
EVENT_COLS = {
    "store": "store_id",
    "date": "date",
    "event": "event",
    "event_type": "event type",
}

# Column names expected in the rules sheet (case-insensitive lookup).
RULES_COLS = {
    "event_type": "Event Type",
    "event": "Event",
    "channel": "Channel",
    "delta": "Delta",
}


@dataclass
class EventForecastInput:
    """Parsed event/rules workbook ready to be turned into time-series."""

    events: pd.DataFrame      # columns: store_id, date (datetime64[ns]), event, event_type
    rules: pd.DataFrame       # columns: event_type, event, channel, delta
    channels: list[str] = field(default_factory=list)
    stores: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_event_workbook(
    path: str | Path,
    event_sheet: str = DEFAULT_EVENT_SHEET,
    rules_sheet: str = DEFAULT_RULES_SHEET,
) -> EventForecastInput:
    """Read the event log + rules table from a workbook.

    The expected sheet/column names match
    ``examples/simulated_event_data_and_rules.xlsx`` but lookup is
    case-insensitive so small variations are tolerated.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    raw_events = pd.read_excel(path, sheet_name=event_sheet)
    raw_rules = pd.read_excel(path, sheet_name=rules_sheet)

    events = _normalise_events(raw_events)
    rules = _normalise_rules(raw_rules)

    channels = sorted(rules["channel"].unique())
    stores = sorted(events["store_id"].unique())

    return EventForecastInput(
        events=events, rules=rules, channels=channels, stores=stores
    )


def _normalise_events(df: pd.DataFrame) -> pd.DataFrame:
    cols = _ci_columns(df)
    out = pd.DataFrame(
        {
            "store_id": df[cols[EVENT_COLS["store"]]].astype(str),
            "date": pd.to_datetime(df[cols[EVENT_COLS["date"]]], errors="coerce"),
            "event": df[cols[EVENT_COLS["event"]]].astype(str),
            "event_type": df[cols[EVENT_COLS["event_type"]]].astype(str),
        }
    )
    out = out.dropna(subset=["date"]).reset_index(drop=True)
    return out


def _normalise_rules(df: pd.DataFrame) -> pd.DataFrame:
    cols = _ci_columns(df)
    out = pd.DataFrame(
        {
            "event_type": df[cols[RULES_COLS["event_type"]]].astype(str),
            "event": df[cols[RULES_COLS["event"]]].astype(str),
            "channel": df[cols[RULES_COLS["channel"]]].astype(str),
            "delta": pd.to_numeric(df[cols[RULES_COLS["delta"]]], errors="coerce").fillna(0.0),
        }
    )
    return out


def _ci_columns(df: pd.DataFrame) -> dict[str, str]:
    """Return a {lowercased: original} column map for lenient lookup."""
    mapping = {c.lower(): c for c in df.columns}
    # Validate up front — surface friendly errors before we go further.
    return _LooseColumnLookup(mapping)


class _LooseColumnLookup(dict):
    """Dict that accepts case-insensitive keys."""

    def __getitem__(self, key: str) -> str:
        if key in self:
            return super().__getitem__(key)
        lower = key.lower()
        if lower in self:
            return super().__getitem__(lower)
        raise KeyError(
            f"Required column {key!r} not found. Available: {list(self.values())}"
        )


# --------------------------------------------------------------------------- #
# Core: events + rules -> per-(store, channel, date) delta sum
# --------------------------------------------------------------------------- #
def compute_daily_deltas(data: EventForecastInput) -> pd.DataFrame:
    """Return a tidy DataFrame: store_id, date, channel, delta_sum.

    For every (store, date) we look up every rule that *matches* the events
    happening that day. ``Event = "Any"`` rules match every event of the
    same ``Event Type`` and are added once per matching event.
    """
    events = data.events.copy()
    rules = data.rules.copy()

    # Specific (event_type, event) rules — exact match.
    specific = rules[rules["event"] != WILDCARD_EVENT].copy()
    # Wildcard rules — match every event of the given event_type.
    wildcard = rules[rules["event"] == WILDCARD_EVENT].drop(columns=["event"]).copy()

    matched_specific = events.merge(
        specific, on=["event_type", "event"], how="inner"
    )
    matched_wildcard = events.merge(
        wildcard, on=["event_type"], how="inner"
    )

    matched = pd.concat([matched_specific, matched_wildcard], ignore_index=True, sort=False)

    if matched.empty:
        # Still produce zero-impact rows for every (store, date, channel).
        all_dates = pd.date_range(events["date"].min(), events["date"].max(), freq="D")
        idx = pd.MultiIndex.from_product(
            [data.stores, all_dates, data.channels],
            names=["store_id", "date", "channel"],
        )
        return pd.DataFrame(index=idx).reset_index().assign(delta_sum=0.0)

    grouped = (
        matched.groupby(["store_id", "date", "channel"], as_index=False)["delta"]
        .sum()
        .rename(columns={"delta": "delta_sum"})
    )
    return grouped


def build_demand_index_series(
    data: EventForecastInput,
    baseline: float = 1.0,
    fillna: float = 1.0,
) -> list[TimeSeries]:
    """Construct one daily :class:`TimeSeries` per (store_id, channel).

    Parameters
    ----------
    data:
        Output of :func:`load_event_workbook`.
    baseline:
        Value added to the summed ``Delta`` (default ``1.0``, so the series
        is interpretable as a multiplicative demand index).
    fillna:
        Value used for days that contain no events (default ``1.0`` =
        baseline / "no impact").
    """
    deltas = compute_daily_deltas(data)
    if deltas.empty:
        return []

    full_dates = pd.date_range(deltas["date"].min(), deltas["date"].max(), freq="D")

    series: list[TimeSeries] = []
    for store in data.stores:
        for channel in data.channels:
            sub = deltas[(deltas["store_id"] == store) & (deltas["channel"] == channel)]
            s = (
                sub.set_index("date")["delta_sum"]
                .reindex(full_dates, fill_value=0.0)
                .add(baseline)
            )
            s.index.name = "date"
            s.name = f"{store}|{channel}"
            # If the user wants a different "missing day" value, apply it.
            if fillna != baseline:
                s = s.where(sub.set_index("date")["delta_sum"].reindex(full_dates).notna(), fillna)
            series.append(
                TimeSeries(
                    name=s.name,
                    values=s.astype(float),
                    freq="D",
                    metadata={"store_id": store, "channel": channel},
                )
            )
    return series


# --------------------------------------------------------------------------- #
# Convenience: load + build in one call
# --------------------------------------------------------------------------- #
def load_event_series(
    path: str | Path,
    event_sheet: str = DEFAULT_EVENT_SHEET,
    rules_sheet: str = DEFAULT_RULES_SHEET,
    baseline: float = 1.0,
    fillna: float = 1.0,
) -> list[TimeSeries]:
    """One-shot helper used by the CLI / examples."""
    data = load_event_workbook(path, event_sheet=event_sheet, rules_sheet=rules_sheet)
    return build_demand_index_series(data, baseline=baseline, fillna=fillna)


def filter_series(
    series: Iterable[TimeSeries],
    stores: Iterable[str] | None = None,
    channels: Iterable[str] | None = None,
) -> list[TimeSeries]:
    """Subset the constructed series by store/channel."""
    stores_set = set(stores) if stores else None
    channels_set = set(channels) if channels else None
    out: list[TimeSeries] = []
    for s in series:
        meta = s.metadata
        if stores_set and meta.get("store_id") not in stores_set:
            continue
        if channels_set and meta.get("channel") not in channels_set:
            continue
        out.append(s)
    return out


def summarise_input(data: EventForecastInput) -> dict:
    """Small dict useful for CLI status output / debugging."""
    return {
        "stores": len(data.stores),
        "channels": len(data.channels),
        "rules": len(data.rules),
        "events": len(data.events),
        "date_min": data.events["date"].min(),
        "date_max": data.events["date"].max(),
    }


# --------------------------------------------------------------------------- #
# numpy is imported for type completeness in case downstream callers expect it
# (no direct usage above; kept for future numeric helpers).
# --------------------------------------------------------------------------- #
_ = np
