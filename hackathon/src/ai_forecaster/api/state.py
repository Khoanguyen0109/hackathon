"""Application state: mock-data cache + in-memory deployment store.

For the demo/hackathon all reference data (stations, stores, employees,
events, promos, weather, ...) is loaded from the Excel workbooks in
``examples/``. Deployments created via ``POST /api/v1/deployments``
live in an in-memory dict — in production you'd swap this for Postgres.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:  # avoid importing heavy deps at module load
    from .schemas import Deployment

logger = logging.getLogger(__name__)


DEFAULT_EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"


@dataclass
class DataBundle:
    """All Excel workbooks parsed once at startup."""

    stations: pd.DataFrame
    channel_mapping: pd.DataFrame
    stores: pd.DataFrame
    employees: pd.DataFrame
    tasks: pd.DataFrame
    orders_history: pd.DataFrame
    promos: pd.DataFrame
    events_calendar: pd.DataFrame
    past_deployments: pd.DataFrame
    weather_forecast: pd.DataFrame
    overrides: pd.DataFrame
    event_rules: pd.DataFrame   # Tab2_PredictionRules
    event_log: pd.DataFrame     # Tab1_EventTable

    loaded_at: datetime = field(default_factory=datetime.utcnow)

    def row_counts(self) -> dict[str, int]:
        return {
            "stations": len(self.stations),
            "stores": len(self.stores),
            "employees": len(self.employees),
            "tasks": len(self.tasks),
            "orders_history": len(self.orders_history),
            "promos": len(self.promos),
            "events_calendar": len(self.events_calendar),
            "past_deployments": len(self.past_deployments),
            "weather_forecast": len(self.weather_forecast),
            "crew_availability_overrides": len(self.overrides),
            "event_rules": len(self.event_rules),
            "event_log": len(self.event_log),
        }


def _read(path: Path, sheet: str | None = None) -> pd.DataFrame:
    if not path.exists():
        logger.warning("expected workbook %s not found — returning empty DataFrame", path)
        return pd.DataFrame()
    if sheet is None:
        return pd.read_excel(path)
    return pd.read_excel(path, sheet_name=sheet)


def load_data_bundle(examples_dir: Path | str | None = None) -> DataBundle:
    """Load every mock workbook in ``examples/`` into memory."""
    d = Path(examples_dir) if examples_dir else DEFAULT_EXAMPLES_DIR

    event_wb = d / "simulated_event_data_and_rules.xlsx"

    def _csv_list(col: pd.Series) -> pd.Series:
        return col.fillna("").astype(str).map(lambda s: [t for t in s.split(",") if t])

    employees = _read(d / "employees.xlsx")
    if not employees.empty:
        for c in ("available_days", "available_shifts", "skills"):
            if c in employees.columns:
                employees[c] = _csv_list(employees[c])

    return DataBundle(
        stations=_read(d / "stations.xlsx", sheet="Stations"),
        channel_mapping=_read(d / "stations.xlsx", sheet="ChannelMapping"),
        stores=_read(d / "stores.xlsx"),
        employees=employees,
        tasks=_read(d / "tasks.xlsx"),
        orders_history=_read(d / "orders_history.xlsx"),
        promos=_read(d / "promos.xlsx"),
        events_calendar=_read(d / "events_calendar.xlsx"),
        past_deployments=_read(d / "past_deployments.xlsx"),
        weather_forecast=_read(d / "weather_forecast.xlsx"),
        overrides=_read(d / "crew_availability_overrides.xlsx"),
        event_rules=_read(event_wb, sheet="Tab2_PredictionRules") if event_wb.exists() else pd.DataFrame(),
        event_log=_read(event_wb, sheet="Tab1_EventTable") if event_wb.exists() else pd.DataFrame(),
    )


class DeploymentStore:
    """Thread-safe in-memory store for saved deployments.

    Key = ``deployment_id``. All reads/writes are protected by a single
    RLock — adequate for demo traffic, swap to Postgres for production.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rows: dict[str, "Deployment"] = {}

    def list(self, store_id: str | None = None) -> list["Deployment"]:
        with self._lock:
            rows = list(self._rows.values())
        if store_id:
            rows = [r for r in rows if r.store_id == store_id]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows

    def get(self, deployment_id: str) -> "Deployment | None":
        with self._lock:
            return self._rows.get(deployment_id)

    def put(self, deployment: "Deployment") -> None:
        with self._lock:
            self._rows[deployment.deployment_id] = deployment

    def delete(self, deployment_id: str) -> bool:
        with self._lock:
            return self._rows.pop(deployment_id, None) is not None

    @staticmethod
    def new_id() -> str:
        return f"DPL_{uuid.uuid4().hex[:10]}"


@dataclass
class AppState:
    """The singleton we attach to ``app.state`` and return from a dep."""

    data: DataBundle
    deployments: DeploymentStore
    started_at: float = field(default_factory=time.time)
    version: str = "0.1.0"
    default_model: str = "amazon/chronos-bolt-base"

    @classmethod
    def bootstrap(cls, examples_dir: Path | str | None = None) -> "AppState":
        data = load_data_bundle(examples_dir)
        return cls(data=data, deployments=DeploymentStore())
