"""End-to-end demo on ``simulated_event_data_and_rules.xlsx``.

The workbook contains:

* ``Tab1_EventTable``     — long-format event log per store / day.
* ``Tab2_PredictionRules`` — multiplicative ``Delta`` per (event, channel).

This script:

1. Joins both tabs into one daily ``demand_index`` time-series per
   ``(store_id, channel)``.
2. Forecasts each series 30 days into the future with Hugging Face Chronos.
3. Saves an Excel workbook (one sheet per series + a ``_summary`` sheet) and
   PNG plots.

Run::

    python examples/forecast_events_example.py
"""

from __future__ import annotations

from pathlib import Path

from ai_forecaster import (
    ChronosForecastModel,
    Forecaster,
    build_demand_index_series,
    filter_series,
    load_event_workbook,
)
from ai_forecaster.visualization import plot_results

HERE = Path(__file__).resolve().parent
INPUT = HERE / "simulated_event_data_and_rules.xlsx"
OUT_XLSX = HERE / "outputs" / "event_forecast.xlsx"
PLOT_DIR = HERE / "outputs" / "event_plots"

# Forecasting knobs
HORIZON_DAYS = 30
MODEL_NAME = "amazon/chronos-t5-small"
# Limit the demo to a few stores so first run is quick. Set to None for all.
STORES_TO_USE = ["S0001", "S0002", "S0003"]


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(f"Workbook not found: {INPUT}")

    print(f"Reading {INPUT.name} ...")
    data = load_event_workbook(INPUT)
    print(
        f"  stores={len(data.stores)} channels={len(data.channels)} "
        f"rules={len(data.rules)} events={len(data.events)} "
        f"({data.events['date'].min().date()} → {data.events['date'].max().date()})"
    )

    series = build_demand_index_series(data)
    series = filter_series(series, stores=STORES_TO_USE)
    print(f"  built {len(series)} (store, channel) series")

    print(f"\nLoading {MODEL_NAME} (first run downloads ~200 MB) ...")
    model = ChronosForecastModel(model_name=MODEL_NAME)
    forecaster = Forecaster(model=model, num_samples=50)

    print(f"Forecasting {HORIZON_DAYS} days ahead for {len(series)} series ...")
    results = forecaster.forecast_many(series, horizon=HORIZON_DAYS)

    forecaster.to_excel(results, out_path=OUT_XLSX)
    plot_results(results, out_dir=PLOT_DIR)

    print(f"\nForecast workbook: {OUT_XLSX}")
    print(f"Plots:             {PLOT_DIR}")
    print("\nPer-series summary:")
    for r in results:
        print(
            f"  {r.series_name:>20s}  "
            f"history={len(r.history):>3d}  "
            f"mean={r.mean.mean():.4f}  "
            f"median={r.median.mean():.4f}"
        )


if __name__ == "__main__":
    main()
