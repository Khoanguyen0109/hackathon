"""High-level orchestration: Excel in → forecasts out."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from .data_loader import ExcelTimeSeriesLoader, TimeSeries
from .model import ChronosForecastModel, DEFAULT_QUANTILES, ModelPrediction


@dataclass
class ForecastResult:
    """Forecast output for a single series."""

    series_name: str
    history: pd.Series                       # original observations
    forecast_index: pd.DatetimeIndex         # future timestamps
    mean: pd.Series
    median: pd.Series
    quantiles: dict[float, pd.Series] = field(default_factory=dict)
    samples: np.ndarray | None = None        # (num_samples, horizon)

    def as_dataframe(self) -> pd.DataFrame:
        """Wide DataFrame with mean/median + quantile columns."""
        data = {"mean": self.mean, "median": self.median}
        for q, s in self.quantiles.items():
            data[f"q{int(q * 100):02d}"] = s
        return pd.DataFrame(data)

    def combined_dataframe(self) -> pd.DataFrame:
        """History + forecast, useful for plotting / exporting."""
        hist = self.history.to_frame(name="actual")
        fc = self.as_dataframe()
        fc.insert(0, "actual", np.nan)
        return pd.concat([hist.assign(**{c: np.nan for c in fc.columns if c != "actual"}), fc])


class Forecaster:
    """End-to-end forecaster: load → predict → export."""

    def __init__(
        self,
        model: ChronosForecastModel | None = None,
        quantile_levels: Sequence[float] = DEFAULT_QUANTILES,
        num_samples: int = 100,
    ) -> None:
        self.model = model or ChronosForecastModel()
        self.quantile_levels = list(quantile_levels)
        self.num_samples = num_samples

    # ------------------------------------------------------------------ #
    # Forecasting
    # ------------------------------------------------------------------ #
    def forecast_series(self, ts: TimeSeries, horizon: int) -> ForecastResult:
        prediction = self.model.predict(
            history=ts.to_array(),
            horizon=horizon,
            num_samples=self.num_samples,
            quantile_levels=self.quantile_levels,
        )
        return self._build_result(ts, horizon, prediction)

    def forecast_many(
        self, series: Sequence[TimeSeries], horizon: int
    ) -> list[ForecastResult]:
        predictions = self.model.predict_batch(
            histories=[s.to_array() for s in series],
            horizon=horizon,
            num_samples=self.num_samples,
            quantile_levels=self.quantile_levels,
        )
        return [self._build_result(s, horizon, p) for s, p in zip(series, predictions)]

    def forecast_excel(
        self,
        path: str | Path,
        horizon: int,
        sheet_name: str | int | None = 0,
        timestamp_column: str | None = None,
        value_columns: Sequence[str] | None = None,
        freq: str | None = None,
        fillna: str | float | None = "ffill",
    ) -> list[ForecastResult]:
        """Convenience: load an Excel file and forecast every series in it."""
        loader = ExcelTimeSeriesLoader(
            path=path,
            sheet_name=sheet_name,
            timestamp_column=timestamp_column,
            value_columns=value_columns,
            freq=freq,
            fillna=fillna,
        )
        series = loader.load()
        return self.forecast_many(series, horizon=horizon)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def to_excel(
        self,
        results: Sequence[ForecastResult],
        out_path: str | Path,
        include_history: bool = True,
    ) -> Path:
        """Write all forecasts to a single workbook, one sheet per series."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            summary_rows = []
            for r in results:
                df = r.combined_dataframe() if include_history else r.as_dataframe()
                df.index.name = "timestamp"
                sheet = _safe_sheet_name(r.series_name)
                df.to_excel(writer, sheet_name=sheet)

                summary_rows.append(
                    {
                        "series": r.series_name,
                        "horizon": len(r.forecast_index),
                        "forecast_start": r.forecast_index[0],
                        "forecast_end": r.forecast_index[-1],
                        "mean_forecast": float(r.mean.mean()),
                        "median_forecast": float(r.median.mean()),
                    }
                )
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="_summary", index=False)
        return out_path

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _build_result(
        self, ts: TimeSeries, horizon: int, prediction: ModelPrediction
    ) -> ForecastResult:
        future_index = _future_index(ts.values.index, horizon, ts.freq)
        return ForecastResult(
            series_name=ts.name,
            history=ts.values.copy(),
            forecast_index=future_index,
            mean=pd.Series(prediction.mean, index=future_index, name="mean"),
            median=pd.Series(prediction.median, index=future_index, name="median"),
            quantiles={
                q: pd.Series(v, index=future_index, name=f"q{int(q * 100):02d}")
                for q, v in prediction.quantiles.items()
            },
            samples=prediction.samples,
        )


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def _future_index(
    history_index: pd.DatetimeIndex, horizon: int, freq: str | None
) -> pd.DatetimeIndex:
    inferred = freq or pd.infer_freq(history_index)
    if inferred is None:
        # Fall back to median spacing (works for any roughly-regular series).
        diffs = history_index.to_series().diff().dropna()
        if diffs.empty:
            raise ValueError("Cannot infer frequency from a single-point history.")
        step = diffs.median()
        start = history_index[-1] + step
        return pd.DatetimeIndex([start + i * step for i in range(horizon)])
    return pd.date_range(
        start=history_index[-1], periods=horizon + 1, freq=inferred
    )[1:]


def _safe_sheet_name(name: str) -> str:
    bad = set('[]:*?/\\')
    cleaned = "".join("_" if c in bad else c for c in name)
    return cleaned[:31] or "series"
