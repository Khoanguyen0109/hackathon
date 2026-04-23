"""ai_forecaster — Excel-driven time-series forecasting with Hugging Face models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .data_loader import ExcelTimeSeriesLoader, TimeSeries
from .event_pipeline import (
    EventForecastInput,
    build_demand_index_series,
    compute_daily_deltas,
    filter_series,
    load_event_series,
    load_event_workbook,
)
from .scheduler import ScheduleResult, SchedulerConfig, ShiftScheduler
from .scheduling_pipeline import (
    SchedulingPipelineResult,
    build_demand_frame_from_events,
    optimise_shifts,
    write_schedule_excel,
)

# `model` and `forecaster` import torch / chronos which are heavy. Expose them
# lazily so lightweight users (just data loading or event aggregation) don't
# pay the import cost — and so tests for the non-ML modules don't require
# torch to be installed.
if TYPE_CHECKING:  # pragma: no cover
    from .forecaster import Forecaster, ForecastResult
    from .model import ChronosForecastModel


def __getattr__(name: str):
    if name in {"ChronosForecastModel"}:
        from .model import ChronosForecastModel

        return ChronosForecastModel
    if name in {"Forecaster", "ForecastResult"}:
        from . import forecaster as _f

        return getattr(_f, name)
    raise AttributeError(f"module 'ai_forecaster' has no attribute {name!r}")


__all__ = [
    "ExcelTimeSeriesLoader",
    "TimeSeries",
    "ChronosForecastModel",
    "Forecaster",
    "ForecastResult",
    "EventForecastInput",
    "build_demand_index_series",
    "compute_daily_deltas",
    "filter_series",
    "load_event_series",
    "load_event_workbook",
    "ShiftScheduler",
    "SchedulerConfig",
    "ScheduleResult",
    "SchedulingPipelineResult",
    "build_demand_frame_from_events",
    "optimise_shifts",
    "write_schedule_excel",
]

__version__ = "0.1.0"
