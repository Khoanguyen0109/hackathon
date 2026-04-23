"""Tests for the Excel loader (do not require the model)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_forecaster.data_loader import ExcelTimeSeriesLoader, TimeSeries


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    dates = pd.date_range("2024-01-01", periods=20, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "sales": np.linspace(10, 30, 20),
            "visitors": np.arange(100, 120),
            "label": ["x"] * 20,
        }
    )
    path = tmp_path / "data.xlsx"
    df.to_excel(path, index=False)
    return path


def test_auto_detects_timestamp_and_numeric_columns(sample_xlsx: Path) -> None:
    series = ExcelTimeSeriesLoader(sample_xlsx).load()
    names = sorted(s.name for s in series)
    assert names == ["sales", "visitors"]
    for s in series:
        assert isinstance(s, TimeSeries)
        assert isinstance(s.values.index, pd.DatetimeIndex)
        assert len(s) == 20


def test_explicit_columns(sample_xlsx: Path) -> None:
    series = ExcelTimeSeriesLoader(
        sample_xlsx, timestamp_column="date", value_columns=["sales"]
    ).load()
    assert len(series) == 1
    assert series[0].name == "sales"


def test_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        ExcelTimeSeriesLoader("/tmp/does_not_exist.xlsx")


def test_to_array_dtype(sample_xlsx: Path) -> None:
    s = ExcelTimeSeriesLoader(sample_xlsx, value_columns=["sales"]).load_one()
    arr = s.to_array()
    assert arr.dtype == np.float32
    assert arr.shape == (20,)
