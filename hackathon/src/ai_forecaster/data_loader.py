"""Load univariate / multivariate time-series data from Excel workbooks.

The loader is intentionally lenient:

* Accepts ``.xlsx`` (openpyxl) or legacy ``.xls`` (xlrd).
* Auto-detects the timestamp column (first column parseable as a datetime).
* If ``value_columns`` is omitted, every remaining numeric column becomes a
  separate :class:`TimeSeries`.
* Optionally resamples to a fixed frequency and forward-fills small gaps so
  the output is suitable for foundation models that assume regular spacing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass
class TimeSeries:
    """A single named univariate time-series with a DatetimeIndex."""

    name: str
    values: pd.Series  # index = DatetimeIndex, dtype = float
    freq: str | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.values.index, pd.DatetimeIndex):
            raise TypeError(f"TimeSeries '{self.name}' requires a DatetimeIndex.")
        self.values = self.values.astype(float)

    def __len__(self) -> int:
        return len(self.values)

    def to_array(self) -> np.ndarray:
        return self.values.to_numpy(dtype=np.float32)

    def tail(self, n: int) -> "TimeSeries":
        return TimeSeries(self.name, self.values.tail(n), self.freq, dict(self.metadata))


class ExcelTimeSeriesLoader:
    """Read time-series from an Excel workbook into :class:`TimeSeries` objects."""

    def __init__(
        self,
        path: str | Path,
        sheet_name: str | int | None = 0,
        timestamp_column: str | None = None,
        value_columns: Sequence[str] | None = None,
        freq: str | None = None,
        fillna: str | float | None = "ffill",
    ) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)

        self.sheet_name = sheet_name
        self.timestamp_column = timestamp_column
        self.value_columns = list(value_columns) if value_columns else None
        self.freq = freq
        self.fillna = fillna

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def load(self) -> list[TimeSeries]:
        """Return one :class:`TimeSeries` per numeric value column."""
        df = self._read_dataframe()
        ts_col = self._detect_timestamp_column(df)
        df = self._prepare_index(df, ts_col)

        value_cols = self.value_columns or self._detect_numeric_columns(df)
        if not value_cols:
            raise ValueError(
                f"No numeric value columns found in {self.path.name}. "
                "Pass `value_columns=` explicitly."
            )

        series_list: list[TimeSeries] = []
        for col in value_cols:
            if col not in df.columns:
                raise KeyError(f"Column '{col}' not found in workbook.")
            s = pd.to_numeric(df[col], errors="coerce")
            s = self._handle_missing(s)
            series_list.append(
                TimeSeries(
                    name=str(col),
                    values=s,
                    freq=self.freq or pd.infer_freq(s.index),
                    metadata={"source": str(self.path), "sheet": self.sheet_name},
                )
            )
        return series_list

    def load_one(self) -> TimeSeries:
        """Convenience helper when the workbook contains a single series."""
        series = self.load()
        if len(series) != 1:
            raise ValueError(
                f"Expected exactly 1 series but found {len(series)}. "
                "Use `load()` or pass `value_columns=` to disambiguate."
            )
        return series[0]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _read_dataframe(self) -> pd.DataFrame:
        engine = "openpyxl" if self.path.suffix.lower() == ".xlsx" else None
        return pd.read_excel(self.path, sheet_name=self.sheet_name, engine=engine)

    def _detect_timestamp_column(self, df: pd.DataFrame) -> str:
        if self.timestamp_column:
            if self.timestamp_column not in df.columns:
                raise KeyError(
                    f"timestamp_column='{self.timestamp_column}' not found. "
                    f"Available: {list(df.columns)}"
                )
            return self.timestamp_column

        for col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() >= max(2, int(0.8 * len(df))):
                return col
        raise ValueError(
            "Could not auto-detect a timestamp column. "
            "Pass `timestamp_column=` explicitly."
        )

    def _prepare_index(self, df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
        df = df.copy()
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
        df = df.dropna(subset=[ts_col]).sort_values(ts_col)
        df = df.set_index(ts_col)

        if self.freq:
            df = df.asfreq(self.freq)
        return df

    def _detect_numeric_columns(self, df: pd.DataFrame) -> list[str]:
        return [
            c for c in df.columns
            if pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))
            and pd.to_numeric(df[c], errors="coerce").notna().any()
        ]

    def _handle_missing(self, s: pd.Series) -> pd.Series:
        if self.fillna is None:
            return s.dropna()
        if isinstance(self.fillna, (int, float)):
            return s.fillna(float(self.fillna))
        if self.fillna == "ffill":
            return s.ffill().bfill()
        if self.fillna == "bfill":
            return s.bfill().ffill()
        if self.fillna == "interpolate":
            return s.interpolate(method="time").ffill().bfill()
        raise ValueError(f"Unknown fillna strategy: {self.fillna!r}")


def load_excel(path: str | Path, **kwargs) -> list[TimeSeries]:
    """Functional shortcut equivalent to ``ExcelTimeSeriesLoader(path, **kwargs).load()``."""
    return ExcelTimeSeriesLoader(path, **kwargs).load()


def iter_series(series: Iterable[TimeSeries]) -> Iterable[tuple[str, np.ndarray]]:
    """Yield ``(name, np.ndarray)`` pairs - handy when feeding batched models."""
    for s in series:
        yield s.name, s.to_array()
