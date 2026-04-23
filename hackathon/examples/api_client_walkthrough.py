"""End-to-end Python client walkthrough for the AI deployment chart API.

Exercises every screen of ``examples/ai_deployment_chart_userflow.html``
against a running FastAPI server (or an in-process ``TestClient``).

Usage — against a server you've already started with
``ai-forecast serve`` or ``docker compose up api``::

    python examples/api_client_walkthrough.py --base http://localhost:8000

Usage — entirely in-process, no server required::

    python examples/api_client_walkthrough.py --in-process
"""

from __future__ import annotations

import argparse
import json
from pprint import pprint
from typing import Any

try:
    import httpx
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install with: pip install httpx") from exc


def _hr(title: str) -> None:
    print(f"\n\033[1;36m── {title} ──\033[0m")


def _get_client(in_process: bool, base: str) -> httpx.Client:
    if in_process:
        # Lazy import so the script still works without the package installed
        # from a clone that just has httpx + fastapi available.
        from fastapi.testclient import TestClient

        from ai_forecaster.api import create_app

        app = create_app()
        return TestClient(app)
    return httpx.Client(base_url=base, timeout=30)


def main() -> None:
    p = argparse.ArgumentParser(description="API walkthrough.")
    p.add_argument("--base", default="http://localhost:8000",
                   help="Base URL of the running API.")
    p.add_argument("--in-process", action="store_true",
                   help="Use FastAPI TestClient instead of a real HTTP server.")
    p.add_argument("--store", default="S0001")
    p.add_argument("--date", default="2026-04-26")
    args = p.parse_args()

    with _get_client(args.in_process, args.base) as c:
        _hr("/health")
        print(c.get("/health").json())

        _hr("/api/v1/info")
        pprint(c.get("/api/v1/info").json())

        _hr("Screen 0 — stations")
        stations = c.get("/api/v1/stations").json()
        print(f"{len(stations)} stations:",
              [s["station_id"] for s in stations])

        _hr(f"Screen 1 — crew at {args.store}")
        crew = c.get(f"/api/v1/stores/{args.store}/crew").json()
        for emp in crew[:3]:
            print(f"  {emp['employee_id']:>7} · {emp['employee_name']:<20} "
                  f"· role={emp['role']:<8} · skills={emp['skills']}")

        _hr(f"Screen 2a — context for {args.store} on {args.date}")
        ctx = c.get("/api/v1/context",
                    params={"store_id": args.store, "date": args.date}).json()
        for f in ctx["factors"]:
            print(f"  [{f['source']:<18}] {f['label']:<28} "
                  f"Δdel={f['impact_delivery']:+.2f} "
                  f"Δdin={f['impact_dinein']:+.2f}")
        print("  channel_multipliers:", ctx["channel_multipliers"])

        _hr(f"Screen 2b — AI staffing for {args.store} on {args.date}")
        staffing = c.post("/api/v1/forecast/staffing",
                          json={"store_id": args.store,
                                "date": args.date,
                                "demo_mode": True}).json()
        print(f"  model={staffing['model_used']}  "
              f"gen_ms={staffing['generation_ms']}  "
              f"cells={len(staffing['cells'])}")
        print(f"  {'station':<16} {'shift':<10} {'rec':>4} {'conf':<7}  reason")
        for cell in staffing["cells"]:
            print(f"  {cell['station_name']:<16} {cell['shift']:<10} "
                  f"{cell['ai_recommended']:>4} {cell['confidence']:<7}  "
                  f"{cell['reason_short']}")

        _hr("Screen 3 — save a deployment (manager accepts AI grid as-is)")
        emp_ids = [e["employee_id"] for e in crew]
        cells_payload = [
            {"station_id": x["station_id"],
             "shift": x["shift"],
             "ai_recommended": x["ai_recommended"],
             "assigned_employee_ids": emp_ids[: x["ai_recommended"]]}
            for x in staffing["cells"]
        ]
        created = c.post("/api/v1/deployments",
                         json={"store_id": args.store, "date": args.date,
                               "cells": cells_payload,
                               "source_staffing_model": staffing["model_used"]}
                         ).json()
        dep_id = created["deployment_id"]
        print(f"  created {dep_id}  ({len(created['cells'])} cells)")

        _hr("Screen 4 — summary")
        summ = c.get(f"/api/v1/deployments/{dep_id}/summary").json()
        print(json.dumps(summ, indent=2, default=str))

        _hr("Screen 5 — list saved deployments")
        saved = c.get("/api/v1/deployments",
                      params={"store_id": args.store}).json()
        for d in saved:
            print(f"  {d['deployment_id']}  {d['date']}  "
                  f"cells={len(d['cells'])}")

        _hr("cleanup")
        r = c.delete(f"/api/v1/deployments/{dep_id}")
        print(f"  DELETE → HTTP {r.status_code}")

    print("\n\033[1;32m✓ Walkthrough complete.\033[0m")


if __name__ == "__main__":
    main()
