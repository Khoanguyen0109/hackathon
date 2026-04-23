"""FastAPI integration tests — exercise every screen of the user flow.

These run entirely in-process with ``TestClient`` (no real server, no
Chronos weights). The API uses ``demo_mode=True`` so torch is never
imported.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Require the mock dataset to be present; most tests need it.
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from ai_forecaster.api import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Ops
# ---------------------------------------------------------------------------


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_info_lists_all_datasets(client):
    r = client.get("/api/v1/info")
    assert r.status_code == 200
    counts = r.json()["loaded_datasets"]
    for required in ("stations", "stores", "employees", "orders_history",
                     "promos", "events_calendar", "past_deployments",
                     "weather_forecast", "crew_availability_overrides",
                     "event_rules", "event_log"):
        assert required in counts and counts[required] > 0, required


# ---------------------------------------------------------------------------
# Screen 0: Store profile
# ---------------------------------------------------------------------------


def test_list_stations(client):
    r = client.get("/api/v1/stations")
    assert r.status_code == 200
    stations = r.json()
    assert len(stations) == 6
    ids = {s["station_id"] for s in stations}
    assert {"ST_GRILL", "ST_FRYER", "ST_DT", "ST_FC", "ST_ASM", "ST_PREP"} == ids


def test_list_and_get_store(client):
    r = client.get("/api/v1/stores")
    assert r.status_code == 200 and len(r.json()) == 15

    r = client.get("/api/v1/stores/S0001")
    assert r.status_code == 200
    assert r.json()["store_id"] == "S0001"

    r = client.get("/api/v1/stores/NOPE")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Screen 1: Crew setup
# ---------------------------------------------------------------------------


def test_crew_crud_flow(client):
    r = client.get("/api/v1/stores/S0001/crew")
    assert r.status_code == 200
    initial = r.json()
    assert len(initial) > 0
    first = initial[0]
    assert "skills" in first and isinstance(first["skills"], list)

    created = client.post(
        "/api/v1/stores/S0001/crew",
        json={"employee_name": "Test Candidate", "role": "Cook",
              "skills": ["ST_GRILL", "ST_FRYER"]},
    )
    assert created.status_code == 201
    eid = created.json()["employee_id"]

    patched = client.patch(
        f"/api/v1/crew/{eid}",
        json={"role": "Manager", "skills": ["ST_GRILL", "ST_FC", "ST_PREP"]},
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "Manager"
    assert "ST_FC" in patched.json()["skills"]

    deleted = client.delete(f"/api/v1/crew/{eid}")
    assert deleted.status_code == 204

    still_there = client.patch(f"/api/v1/crew/{eid}", json={"role": "Cook"})
    assert still_there.status_code == 404


# ---------------------------------------------------------------------------
# Screen 2: Context + AI suggestion
# ---------------------------------------------------------------------------


def test_context_returns_factors_and_multipliers(client):
    r = client.get("/api/v1/context",
                   params={"store_id": "S0001", "date": "2026-04-26"})
    assert r.status_code == 200
    body = r.json()
    assert body["store_id"] == "S0001"
    assert body["day_of_week"] == "Sun"
    assert len(body["factors"]) >= 2  # at least weather + dow
    for chan in ("Delivery", "Dine-in", "Drive-Through"):
        assert chan in body["channel_multipliers"]


def test_forecast_staffing_returns_full_grid(client):
    r = client.post(
        "/api/v1/forecast/staffing",
        json={"store_id": "S0001", "date": "2026-04-26", "demo_mode": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["store_id"] == "S0001"
    assert body["model_used"].startswith("rules-only")
    # 6 stations × 3 shifts on S0001
    assert len(body["cells"]) == 18
    for cell in body["cells"]:
        assert cell["ai_recommended"] >= 0
        assert cell["confidence"] in {"high", "medium", "low"}
        assert len(cell["reason_rows"]) == 5
        labels = [r["label"] for r in cell["reason_rows"]]
        assert labels == ["Factors", "Rules", "Channel", "Crew", "Confidence"]


def test_forecast_staffing_unknown_store(client):
    r = client.post(
        "/api/v1/forecast/staffing",
        json={"store_id": "NOPE", "date": "2026-04-26", "demo_mode": True},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Screens 3/4/5: Deployments — end-to-end
# ---------------------------------------------------------------------------


def test_full_deployment_flow(client):
    # 1. Ask the AI for a grid
    sug = client.post("/api/v1/forecast/staffing",
                      json={"store_id": "S0002", "date": "2026-04-26",
                            "demo_mode": True}).json()

    # 2. Manager accepts it, assigning the first N certified crew
    crew = client.get("/api/v1/stores/S0002/crew").json()
    emp_pool = [c["employee_id"] for c in crew]

    cells_payload = []
    for cell in sug["cells"]:
        assigned = emp_pool[: max(0, cell["ai_recommended"] - 1)]  # under-staff by 1
        cells_payload.append({
            "station_id": cell["station_id"],
            "shift": cell["shift"],
            "ai_recommended": cell["ai_recommended"],
            "assigned_employee_ids": assigned,
            "manager_note": None,
        })

    create = client.post("/api/v1/deployments", json={
        "store_id": "S0002",
        "date": "2026-04-26",
        "cells": cells_payload,
        "source_staffing_model": sug["model_used"],
    })
    assert create.status_code == 201
    dep_id = create.json()["deployment_id"]

    # 3. Screen 5: list
    listed = client.get("/api/v1/deployments", params={"store_id": "S0002"})
    assert listed.status_code == 200
    assert any(d["deployment_id"] == dep_id for d in listed.json())

    # 4. Screen 4: summary
    summ = client.get(f"/api/v1/deployments/{dep_id}/summary")
    assert summ.status_code == 200
    body = summ.json()
    assert body["total_ai_recommended"] > 0
    assert body["gap"] <= 0  # we intentionally under-staffed
    assert body["coverage_pct"] <= 100

    # 5. Compare to past_deployments actuals (best-effort)
    comp = client.get(f"/api/v1/deployments/{dep_id}/comparison")
    assert comp.status_code == 200
    assert len(comp.json()["rows"]) == len(cells_payload)

    # 6. Patch to meet target and re-summarise
    full_cells = [{**c, "assigned_employee_ids": emp_pool[: c["ai_recommended"]]}
                  for c in cells_payload]
    patched = client.patch(f"/api/v1/deployments/{dep_id}",
                           json={"cells": full_cells})
    assert patched.status_code == 200

    # 7. Delete
    assert client.delete(f"/api/v1/deployments/{dep_id}").status_code == 204
    assert client.get(f"/api/v1/deployments/{dep_id}").status_code == 404
