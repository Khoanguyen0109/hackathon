"""Tests for the Forecaster orchestration layer using a mock model.

These avoid downloading the real Hugging Face checkpoint so the suite can
run on CI in seconds.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_forecaster.data_loader import TimeSeries
from ai_forecaster.forecaster import Forecaster
from ai_forecaster.model import ModelPrediction


class FakeModel:
    """Stand-in for ChronosForecastModel — returns deterministic numbers."""

    def predict(self, history, horizon, num_samples=10, quantile_levels=(0.1, 0.5, 0.9), **kw):
        rng = np.random.default_rng(0)
        samples = rng.normal(loc=float(np.asarray(history)[-1]), scale=1.0,
                             size=(num_samples, horizon)).astype(np.float32)
        return ModelPrediction(
            quantiles={float(q): np.quantile(samples, q, axis=0) for q in quantile_levels},
            mean=samples.mean(axis=0),
            median=np.quantile(samples, 0.5, axis=0),
            samples=None,
        )

    def predict_batch(self, histories, horizon, **kw):
        return [self.predict(h, horizon, **kw) for h in histories]


@pytest.fixture
def daily_series() -> TimeSeries:
    idx = pd.date_range("2024-01-01", periods=50, freq="D")
    return TimeSeries(name="sales", values=pd.Series(np.arange(50, dtype=float), index=idx), freq="D")


def test_forecast_series_shape(daily_series: TimeSeries) -> None:
    f = Forecaster(model=FakeModel(), num_samples=20)
    result = f.forecast_series(daily_series, horizon=7)

    assert result.series_name == "sales"
    assert len(result.forecast_index) == 7
    assert result.forecast_index[0] == pd.Timestamp("2024-02-20")
    assert set(result.quantiles) == {0.1, 0.5, 0.9}
    assert result.mean.shape == (7,)


def test_forecast_excel_export(daily_series: TimeSeries, tmp_path: Path) -> None:
    f = Forecaster(model=FakeModel(), num_samples=10)
    result = f.forecast_series(daily_series, horizon=5)
    out = f.to_excel([result], tmp_path / "fc.xlsx")
    assert out.exists()

    written = pd.read_excel(out, sheet_name="sales", index_col=0)
    assert "mean" in written.columns
    assert "median" in written.columns
    assert any(c.startswith("q") for c in written.columns)


def test_combined_dataframe_contains_history(daily_series: TimeSeries) -> None:
    f = Forecaster(model=FakeModel(), num_samples=10)
    result = f.forecast_series(daily_series, horizon=3)
    df = result.combined_dataframe()
    assert df["actual"].notna().sum() == 50
    assert df["mean"].notna().sum() == 3
