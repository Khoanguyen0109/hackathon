"""Plot forecasts (history + median + uncertainty band)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt

from .forecaster import ForecastResult


def plot_forecast(
    result: ForecastResult,
    ax: plt.Axes | None = None,
    show_history: bool = True,
    title: str | None = None,
) -> plt.Axes:
    """Plot a single :class:`ForecastResult` (history + median + 80% band)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))

    if show_history:
        ax.plot(result.history.index, result.history.values, label="history", color="#1f77b4")

    ax.plot(
        result.forecast_index, result.median.values,
        label="median forecast", color="#d62728",
    )

    qs = sorted(result.quantiles.keys())
    if len(qs) >= 2:
        lo, hi = qs[0], qs[-1]
        ax.fill_between(
            result.forecast_index,
            result.quantiles[lo].values,
            result.quantiles[hi].values,
            alpha=0.25,
            color="#d62728",
            label=f"{int(lo * 100)}–{int(hi * 100)}% interval",
        )

    ax.set_title(title or f"Forecast — {result.series_name}")
    ax.set_xlabel("time")
    ax.set_ylabel("value")
    ax.legend(loc="best")
    ax.grid(alpha=0.3)
    return ax


def plot_results(
    results: Sequence[ForecastResult],
    out_dir: str | Path | None = None,
    show: bool = False,
) -> list[Path]:
    """Plot every forecast and (optionally) save each as a PNG.

    Returns the list of files written (empty if ``out_dir`` is None).
    """
    written: list[Path] = []
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    for r in results:
        fig, ax = plt.subplots(figsize=(10, 4))
        plot_forecast(r, ax=ax)
        fig.tight_layout()

        if out_dir is not None:
            from .forecaster import _safe_sheet_name  # reuse sanitiser
            file = out_dir / f"forecast_{_safe_sheet_name(r.series_name)}.png"
            fig.savefig(file, dpi=120)
            written.append(file)

        if show:
            plt.show()
        plt.close(fig)

    return written
